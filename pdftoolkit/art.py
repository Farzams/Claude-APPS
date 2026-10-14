"""Procedural artwork: theme previews and icons (Pillow only)."""
from __future__ import annotations

import math
import random
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


FONT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "fonts"
ICON_COLORS = {
    "home": ("#6366f1", "#06b6d4"), "read": ("#6366f1", "#8b5cf6"), "ocr": ("#ec4899", "#f43f5e"),
    "extract": ("#14b8a6", "#06b6d4"), "convert": ("#f59e0b", "#f97316"), "split": ("#ef4444", "#f97316"),
    "merge": ("#22c55e", "#10b981"), "compress": ("#0ea5e9", "#6366f1"), "images": ("#a855f7", "#ec4899"),
    "pages": ("#84cc16", "#22c55e"), "settings": ("#64748b", "#94a3b8"), "help": ("#3b82f6", "#06b6d4"),
    "latex": ("#0ea5e9", "#2563eb"), "formula": ("#f59e0b", "#ef4444"),
}


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(size, c1, c2, vertical=True) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, 256))
    px = base.load()
    for i in range(256):
        px[0, i] = _mix(c1, c2, i / 255)
    base = base.resize((w, h) if vertical else (h, w))
    return base if vertical else base.rotate(90, expand=True).resize((w, h))


def _font(size: int, bold=False, arabic=False) -> ImageFont.FreeTypeFont:
    names = (["NotoSansArabic-Bold.ttf"] if bold else ["NotoSansArabic-Regular.ttf"]) if arabic else \
        (["segoeuib.ttf", "DejaVuSans-Bold.ttf"] if bold else ["segoeui.ttf", "DejaVuSans.ttf"])
    for n in names:
        for d in (FONT_DIR, Path("C:/Windows/Fonts")):
            p = d / n
            if p.is_file():
                try:
                    # BASIC layout: we already pass shaped, visual-order text; no second shaping/bidi pass
                    return ImageFont.truetype(str(p), size, layout_engine=ImageFont.Layout.BASIC)
                except Exception:
                    pass
    return ImageFont.load_default()


def _runs(visual: str):
    """Split a visual-order string into (text, is_arabic_font) runs."""
    runs, cur, cur_ar = [], "", None
    for ch in visual:
        o = ord(ch)
        ar = 0x590 <= o <= 0x8FF or 0xFB1D <= o <= 0xFEFF
        if ch == " " and cur_ar is not None:
            ar = cur_ar          # spaces stay with the current run; ASCII punctuation uses the Latin font
        if cur_ar is None or ar == cur_ar:
            cur += ch
            cur_ar = ar
        else:
            runs.append((cur, cur_ar))
            cur, cur_ar = ch, ar
    if cur:
        runs.append((cur, cur_ar))
    return runs


def _glyph(name: str, d: ImageDraw.ImageDraw, s: int):
    """White pictograms on an s x s tile."""
    W = (255, 255, 255, 255)
    u = s / 100
    def R(x0, y0, x1, y1, r=0, fill=W, outline=None, width=0):
        d.rounded_rectangle((x0 * u, y0 * u, x1 * u, y1 * u), r * u, fill=fill, outline=outline, width=int(width * u))
    def L(pts, width=6, fill=W):
        d.line([(x * u, y * u) for x, y in pts], fill=fill, width=int(width * u), joint="curve")
    def P(pts, fill=W):
        d.polygon([(x * u, y * u) for x, y in pts], fill=fill)
    if name == "home":
        P([(50, 22), (82, 50), (74, 50), (74, 76), (26, 76), (26, 50), (18, 50)]); R(43, 56, 57, 76, 2, fill=(0, 0, 0, 70))
    elif name == "read":
        P([(50, 30), (50, 78), (22, 70), (22, 24)]); P([(50, 30), (50, 78), (78, 70), (78, 24)], fill=(255, 255, 255, 215))
        L([(30, 38), (44, 41)], 3, (0, 0, 0, 60)); L([(30, 48), (44, 51)], 3, (0, 0, 0, 60))
    elif name == "ocr":
        for (x, y, dx, dy) in [(22, 22, 1, 1), (78, 22, -1, 1), (22, 78, 1, -1), (78, 78, -1, -1)]:
            L([(x + dx * 14, y), (x, y), (x, y + dy * 14)], 5)
        d.ellipse((38 * u, 36 * u, 58 * u, 56 * u), outline=W, width=int(5 * u)); L([(56, 54), (66, 66)], 6)
    elif name == "extract":
        R(26, 18, 70, 82, 5); P([(70, 18), (70, 36), (52, 36)], fill=(0, 0, 0, 60))
        for y in (48, 58, 68): L([(34, y), (62, y)], 4, (0, 0, 0, 80))
    elif name == "convert":
        L([(22, 38), (72, 38)], 7); P([(72, 26), (88, 38), (72, 50)])
        L([(78, 64), (28, 64)], 7); P([(28, 52), (12, 64), (28, 76)])
    elif name == "split":
        R(22, 18, 78, 46, 4); R(22, 54, 78, 82, 4, fill=(255, 255, 255, 200))
        for x in range(20, 82, 12): L([(x, 50), (x + 6, 50)], 3)
    elif name == "merge":
        R(14, 18, 44, 42, 4); R(56, 18, 86, 42, 4); L([(29, 46), (50, 62)], 5); L([(71, 46), (50, 62)], 5)
        R(32, 64, 68, 86, 4)
    elif name == "compress":
        R(30, 44, 70, 56, 3); P([(50, 34), (36, 14), (64, 14)]); P([(50, 66), (36, 86), (64, 86)])
        P([(14, 50), (28, 40), (28, 60)]); P([(86, 50), (72, 40), (72, 60)])
    elif name == "images":
        R(16, 22, 84, 78, 8, fill=None, outline=W, width=6)
        d.ellipse((60 * u, 32 * u, 72 * u, 44 * u), fill=W); P([(20, 74), (40, 46), (54, 62), (64, 52), (80, 74)])
    elif name == "pages":
        R(30, 14, 78, 66, 5, fill=(255, 255, 255, 140)); R(22, 24, 70, 76, 5, fill=(255, 255, 255, 200))
        R(14, 34, 62, 86, 5); L([(24, 52), (52, 52)], 4, (0, 0, 0, 80)); L([(24, 64), (44, 64)], 4, (0, 0, 0, 80))
    elif name == "settings":
        cx = cy = 50 * u
        for k in range(8):
            a = k * math.pi / 4
            d.polygon([(cx + math.cos(a - .22) * 26 * u, cy + math.sin(a - .22) * 26 * u),
                       (cx + math.cos(a - .15) * 40 * u, cy + math.sin(a - .15) * 40 * u),
                       (cx + math.cos(a + .15) * 40 * u, cy + math.sin(a + .15) * 40 * u),
                       (cx + math.cos(a + .22) * 26 * u, cy + math.sin(a + .22) * 26 * u)], fill=W)
        d.ellipse((cx - 30 * u, cy - 30 * u, cx + 30 * u, cy + 30 * u), fill=W)
        d.ellipse((cx - 13 * u, cy - 13 * u, cx + 13 * u, cy + 13 * u), fill=(0, 0, 0, 90))
    elif name == "latex":
        f = _font(int(36 * u), True)
        tw = d.textlength("TeX", font=f)
        d.text(((s - tw) / 2, 30 * u), "TeX", font=f, fill=W)
        L([(24, 76), (76, 76)], 5)
    elif name == "formula":
        f = _font(int(76 * u), True)
        tw = d.textlength("∑", font=f)
        d.text(((s - tw) / 2, 4 * u), "∑", font=f, fill=W)
    elif name == "help":
        f = _font(int(66 * u), True)
        tw = d.textlength("?", font=f)
        d.text(((s - tw) / 2, 8 * u), "?", font=f, fill=W)


@lru_cache(maxsize=64)
def icon(name: str, px: int = 64, round_: float = 0.26) -> Image.Image:
    S = 4
    s = px * S
    c1, c2 = (_hex(c) for c in ICON_COLORS.get(name, ("#6366f1", "#06b6d4")))
    tile = _gradient((s, s), c1, c2, vertical=False).convert("RGBA")
    gl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    _glyph(name, ImageDraw.Draw(gl, "RGBA"), s)
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 70), (0, int(s * .02)), gl.split()[3])
    tile = Image.alpha_composite(Image.alpha_composite(tile, shadow.filter(ImageFilter.GaussianBlur(s * .02))), gl)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), s * round_, fill=255)
    tile.putalpha(mask)
    return tile.resize((px, px), Image.LANCZOS)


def swatch(pal: dict, size=(120, 64)) -> Image.Image:
    """Preview chip of a theme (background, card, accent, text)."""
    w, h = size
    S = 3
    img = Image.new("RGBA", (w * S, h * S), _hex(pal["bg"]) + (255,))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8 * S, 8 * S, (w - 8) * S, (h - 8) * S), 8 * S, fill=_hex(pal["card"]))
    d.rounded_rectangle((8 * S, 8 * S, 30 * S, (h - 8) * S), 8 * S, fill=_hex(pal["sidebar"]))
    d.rounded_rectangle((38 * S, 16 * S, (w - 16) * S, 26 * S), 5 * S, fill=_hex(pal["accent"]))
    d.rounded_rectangle((38 * S, 34 * S, (w - 30) * S, 40 * S), 3 * S, fill=_hex(pal["muted"]))
    d.rounded_rectangle((38 * S, 46 * S, (w - 50) * S, 52 * S), 3 * S, fill=_hex(pal["field"]))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), 12 * S, fill=255)
    img.putalpha(mask)
    return img.resize((w, h), Image.LANCZOS)
