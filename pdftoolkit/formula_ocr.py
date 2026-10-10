"""Picture of a formula -> LaTeX, with the ONNX models of the "Formula OCR" add-on (offline, CPU).

The inference code follows RapidLaTeXOCR (Apache-2.0, https://github.com/RapidAI/RapidLaTeXOCR), which runs the
LaTeX-OCR / pix2tex model (MIT, https://github.com/lukas-blecher/LaTeX-OCR) through ONNX Runtime. Greedy decoding.
Results are good for clean printed formulas and need checking for long or complex ones.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image

MAX_W, MAX_H, MIN_W, MIN_H = 672, 192, 32, 32
BOS, EOS, MAX_LEN = 1, 2, 512
MEAN, STD = 0.7931 * 255.0, 0.1738 * 255.0


def available(model_dir: Path) -> bool:
    return all((Path(model_dir) / f).is_file() for f in ("image_resizer.onnx", "encoder.onnx", "decoder.onnx",
                                                          "tokenizer.json"))


def _pad_to_content(img: Image.Image, divable: int = 32) -> Image.Image:
    """Crop to the ink, make it dark-on-light, pad to a multiple of 32."""
    import cv2
    data = np.array(img.convert("LA"))
    if data[..., -1].var() == 0:
        data = data[..., 0].astype(np.uint8)
    else:
        data = (255 - data[..., -1]).astype(np.uint8)
    rng = float(data.max()) - float(data.min())
    data = (data - data.min()) / (rng if rng else 1.0) * 255
    if data.mean() > 128:
        gray = 255 * (data < 128).astype(np.uint8)
    else:
        gray = 255 * (data > 128).astype(np.uint8)
        data = 255 - data
    coords = cv2.findNonZero(gray)
    if coords is None:
        raise ValueError("The picture has no visible formula")
    a, b, w, h = cv2.boundingRect(coords)
    rect = Image.fromarray(data[b:b + h, a:a + w]).convert("L")
    dims = [divable * (-(-x // divable)) for x in (w, h)]
    padded = Image.new("L", tuple(dims), 255)
    padded.paste(rect, (0, 0, rect.size[0], rect.size[1]))
    return padded


def _minmax(img: Image.Image) -> Image.Image:
    ratios = [a / b for a, b in zip(img.size, (MAX_W, MAX_H))]
    if any(r > 1 for r in ratios):
        size = np.maximum(np.array(img.size) // max(ratios), 1)
        img = img.resize(tuple(size.astype(int)), Image.BILINEAR)
    padded = [max(d, m) for d, m in zip(img.size, (MIN_W, MIN_H))]
    if tuple(padded) != img.size:
        canvas = Image.new("L", tuple(padded), 255)
        canvas.paste(img, img.getbbox())
        img = canvas
    return img


def _tensor(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("L")).astype(np.float32)
    arr = (arr - MEAN) / STD
    return arr[None, None, :, :]


def _clean(s: str) -> str:
    """Remove the spaces the tokenizer leaves between symbols."""
    text_reg = r"(\\(operatorname|mathrm|text|mathbf)\s?\*? {.*?})"
    letter, noletter = "[a-zA-Z]", r"[\W_^\d]"
    names = [x[0].replace(" ", "") for x in re.findall(text_reg, s)]
    s = re.sub(text_reg, lambda m: names.pop(0), s)
    while True:
        news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, noletter), r"\1\2", s)
        news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, letter), r"\1\2", news)
        news = re.sub(r"(%s)\s+?(%s)" % (letter, noletter), r"\1\2", news)
        if news == s:
            return s
        s = news


class FormulaOCR:
    def __init__(self, model_dir: str | Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        d = Path(model_dir)
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        make = lambda n: ort.InferenceSession(str(d / n), opts, providers=["CPUExecutionProvider"])
        self.resizer, self.encoder, self.decoder = make("image_resizer.onnx"), make("encoder.onnx"), make("decoder.onnx")
        self.tokenizer = Tokenizer.from_file(str(d / "tokenizer.json"))

    def _run(self, session, inputs: list):
        names = [i.name for i in session.get_inputs()]
        return session.run(None, dict(zip(names, inputs)))[0]

    def _prepare(self, img: Image.Image) -> np.ndarray:
        src = _minmax(_pad_to_content(img)).convert("RGB")
        r, w, h = 1.0, src.size[0], src.size[1]
        final = None
        for _ in range(10):                     # let the resizer network choose a width the model likes
            h = int(h * r)
            resample = Image.Resampling.BILINEAR if r > 1 else Image.Resampling.LANCZOS
            padded = _minmax(src.resize((w, h), resample))
            padded = _pad_to_content(padded)
            final = _tensor(padded)
            res = self._run(self.resizer, [final])
            w2 = (int(np.argmax(res, axis=-1).reshape(-1)[0]) + 1) * 32
            if w2 == padded.size[0]:
                break
            r = w2 / padded.size[0]
            w = w2
        return final

    def recognize(self, image: "Image.Image | str | Path | bytes") -> str:
        import io
        if isinstance(image, (str, Path)):
            image = Image.open(image)
        elif isinstance(image, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image))
        x = self._prepare(image.convert("RGBA") if image.mode in ("P", "LA") else image)
        context = self._run(self.encoder, [x])
        out = np.array([[BOS]], dtype=np.int64)
        mask = np.ones_like(out, dtype=bool)
        for _ in range(MAX_LEN):
            logits = self._run(self.decoder, [out[:, -MAX_LEN:], mask[:, -MAX_LEN:], context])
            nxt = int(np.argmax(logits[0, -1, :]))
            out = np.concatenate([out, [[nxt]]], axis=1)
            mask = np.pad(mask, [(0, 0), (0, 1)], constant_values=True)
            if nxt == EOS:
                break
        text = self.tokenizer.decode(out[0, 1:].tolist())
        text = "".join(text.split(" ")).replace("Ġ", " ").replace("[EOS]", "").replace("[BOS]", "").replace("[PAD]", "")
        return _clean(text.strip())
