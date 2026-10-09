"""Core PDF operations (no GUI): split, compress, convert."""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import pymupdf

# ---------------------------------------------------------------- helpers

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def fmt_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{n} B"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def parse_ranges(spec: str, page_count: int) -> list[list[int]]:
    """'1-3, 5, 8-' -> [[0,1,2],[4],[7..end]] (0-based page indexes).

    Each comma-separated item becomes one output file. 'N-' means N to the end.
    """
    groups: list[list[int]] = []
    for part in filter(None, (p.strip() for p in spec.split(","))):
        m = re.fullmatch(r"(\d+)?\s*-\s*(\d+)?", part)
        if m and (m.group(1) or m.group(2)):
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else page_count
        elif part.isdigit():
            a = b = int(part)
        else:
            raise ValueError(f"Invalid range: '{part}'")
        if a < 1 or b > page_count or a > b:
            raise ValueError(f"Range '{part}' is outside 1-{page_count}")
        groups.append(list(range(a - 1, b)))
    if not groups:
        raise ValueError("No page ranges given")
    return groups


def groups_every_n(page_count: int, n: int) -> list[list[int]]:
    if n < 1:
        raise ValueError("Pages per file must be at least 1")
    return [list(range(i, min(i + n, page_count))) for i in range(0, page_count, n)]


def groups_into_parts(page_count: int, parts: int) -> list[list[int]]:
    if parts < 1 or parts > page_count:
        raise ValueError(f"Number of parts must be between 1 and {page_count}")
    base, extra = divmod(page_count, parts)
    groups, start = [], 0
    for i in range(parts):
        size = base + (1 if i < extra else 0)
        groups.append(list(range(start, start + size)))
        start += size
    return groups


# ---------------------------------------------------------------- split

def split_pdf(src: str, out_dir: str, groups: list[list[int]],
              progress: Callable[[int, int], None] | None = None) -> list[Path]:
    """Write one PDF per page-group. Returns the created files."""
    src_p = Path(src)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    with pymupdf.open(src) as doc:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        width = len(str(len(groups)))
        for i, pages in enumerate(groups, 1):
            first, last = pages[0] + 1, pages[-1] + 1
            name = f"{src_p.stem}_part{i:0{width}d}_p{first}-{last}.pdf"
            target = unique_path(out / name)
            with pymupdf.open() as part:
                for run in _runs(pages):
                    part.insert_pdf(doc, from_page=run[0], to_page=run[1])
                part.save(target, garbage=3, deflate=True)
            created.append(target)
            if progress:
                progress(i, len(groups))
    return created


def _runs(pages: list[int]) -> list[tuple[int, int]]:
    runs, start, prev = [], pages[0], pages[0]
    for p in pages[1:]:
        if p != prev + 1:
            runs.append((start, prev))
            start = p
        prev = p
    runs.append((start, prev))
    return runs


# ---------------------------------------------------------------- compress

# name -> (dpi_threshold, dpi_target, jpeg_quality); None = lossless only
COMPRESS_LEVELS: dict[str, tuple[int, int, int] | None] = {
    "Low (lossless, keeps quality)": None,
    "Medium (images 150 dpi, good quality)": (200, 150, 75),
    "High (images 110 dpi, smaller)": (150, 110, 60),
    "Extreme (images 72 dpi, smallest)": (100, 72, 40),
}


GS_PRESETS = {  # level -> Ghostscript -dPDFSETTINGS
    "Low (lossless, keeps quality)": "/prepress",
    "Medium (images 150 dpi, good quality)": "/printer",
    "High (images 110 dpi, smaller)": "/ebook",
    "Extreme (images 72 dpi, smallest)": "/screen",
}


def find_gs() -> str | None:
    return _find_tool(["gswin64c", "gswin32c", "gs"],
                      _gs_dirs())


def _gs_dirs() -> list[str]:
    out = [str(_app_dir() / "gs" / "bin")]  # bundled copy first
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root and Path(root, "gs").is_dir():
            for v in sorted(Path(root, "gs").iterdir(), reverse=True):
                out.append(str(v / "bin"))
    return out


def compress_pdf(src: str, dst: str, level: str, engine: str = "builtin") -> tuple[int, int]:
    """Compress src into dst. Returns (original_size, new_size).

    engine: 'builtin' (PyMuPDF) or 'ghostscript'. If compression would make the
    file bigger, the original is copied instead.
    """
    orig = os.path.getsize(src)
    if engine == "ghostscript":
        gs = find_gs()
        if not gs:
            raise RuntimeError("Ghostscript not found. Install it from https://ghostscript.com")
        tmp = str(dst) + ".tmp"
        r = subprocess.run([gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5",
                            f"-dPDFSETTINGS={GS_PRESETS[level]}", "-dNOPAUSE", "-dBATCH",
                            "-dQUIET", f"-sOutputFile={tmp}", src],
                           capture_output=True, text=True, creationflags=NO_WINDOW)
        if r.returncode != 0 or not os.path.exists(tmp):
            raise RuntimeError(f"Ghostscript failed: {r.stderr.strip()[-300:]}")
        return _keep_smaller(src, tmp, dst, orig)
    params = COMPRESS_LEVELS[level]
    with pymupdf.open(src) as doc:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        if params:
            thr, target, quality = params
            doc.rewrite_images(dpi_threshold=thr, dpi_target=target,
                               quality=quality, lossy=True, lossless=True,
                               bitonal=True, color=True, gray=True)
        tmp = str(dst) + ".tmp"
        doc.save(tmp, garbage=4, deflate=True, deflate_images=True,
                 deflate_fonts=True, clean=True, use_objstms=True)
    return _keep_smaller(src, tmp, dst, orig)


def _keep_smaller(src: str, tmp: str, dst: str, orig: int) -> tuple[int, int]:
    new = os.path.getsize(tmp)
    if new >= orig:
        os.remove(tmp)
        shutil.copyfile(src, dst)
        new = orig
    else:
        os.replace(tmp, dst)
    return orig, new


# ---------------------------------------------------------------- convert

NATIVE_FORMATS = {".epub", ".mobi", ".fb2", ".xps", ".oxps", ".cbz", ".svg",
                  ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif",
                  ".tiff", ".webp", ".html", ".htm", ".xhtml"}
PANDOC_FORMATS = {".docx": "docx", ".odt": "odt", ".rtf": "rtf", ".md": "markdown",
                  ".markdown": "markdown", ".rst": "rst", ".tex": "latex"}
MOBI_LIKE = {".azw", ".azw3"}  # tried natively first, Calibre as fallback
CALIBRE_FORMATS = {".azw", ".azw3", ".doc", ".lit", ".pdb", ".cbr", ".htmlz", ".txtz"}
DJVU_FORMATS = {".djvu", ".djv"}
ALL_FORMATS = sorted(NATIVE_FORMATS | set(PANDOC_FORMATS) | CALIBRE_FORMATS | DJVU_FORMATS)


def _find_tool(names: list[str], extra_dirs: list[str]) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for d in extra_dirs:
        for n in names:
            for ext in ("", ".exe"):
                cand = Path(d) / (n + ext)
                if cand.is_file():
                    return str(cand)
    return None


def _app_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def _program_dirs(*subdirs: str) -> list[str]:
    roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
    base = [Path(r) for r in roots if r]
    here = _app_dir()
    out = [str(here / "djvu"), str(here), str(here / "bin")]  # bundled copy first
    for r in base:
        for s in subdirs:
            out.append(str(r / s))
    return out


def find_ddjvu() -> str | None:
    return _find_tool(["ddjvu"], _program_dirs("DjVuLibre", "DjVuLibre/bin"))


def find_calibre() -> str | None:
    return _find_tool(["ebook-convert"], _program_dirs("Calibre2", "Calibre2/bin"))


def find_pandoc() -> str | None:
    try:
        import pypandoc
        p = pypandoc.get_pandoc_path()
        if p and Path(p).is_file():
            return p
    except Exception:
        pass
    return _find_tool(["pandoc"], [])


def supported_status() -> str:
    def st(ok): return "built in" if ok else "missing"
    return (f"DjVu: {st(find_ddjvu())}  |  DOCX/ODT/RTF: {st(find_pandoc())}  |  "
            f"OCR: {st(find_tessdata())}  |  Ghostscript: {st(find_gs())}")


def convert_to_pdf(src: str, out_dir: str, page_size: str = "a5",
                   font_size: int = 11) -> Path:
    """Convert a document/ebook to PDF; returns the output path."""
    s = Path(src)
    ext = s.suffix.lower()
    out = unique_path(Path(out_dir) / (s.stem + ".pdf"))
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    if ext in DJVU_FORMATS:
        tool = find_ddjvu()
        if not tool:
            raise RuntimeError("DjVu conversion needs DjVuLibre (ddjvu). "
                               "Install it from https://djvu.sourceforge.net and retry.")
        r = subprocess.run([tool, "-format=pdf", "-quality=85", str(s), str(out)],
                           capture_output=True, text=True, creationflags=NO_WINDOW)
        if r.returncode != 0 or not out.exists():
            raise RuntimeError(f"ddjvu failed: {r.stderr.strip() or r.stdout.strip()}")
        return out

    if ext in NATIVE_FORMATS:
        with pymupdf.open(str(s)) as doc:
            if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}:
                pdf_bytes = doc.convert_to_pdf()
                with pymupdf.open("pdf", pdf_bytes) as pdf:
                    pdf.save(out, garbage=3, deflate=True)
                return out
            if doc.is_reflowable:
                doc.layout(rect=pymupdf.paper_rect(page_size), fontsize=font_size)
            toc = doc.get_toc()
            pdf_bytes = doc.convert_to_pdf()
        with pymupdf.open("pdf", pdf_bytes) as pdf:
            if toc:
                try:
                    pdf.set_toc(toc)
                except Exception:
                    pass
            pdf.save(out, garbage=3, deflate=True)
        return out

    if ext in PANDOC_FORMATS:
        pandoc = find_pandoc()
        if not pandoc:
            raise RuntimeError("Pandoc is missing from this build.")
        with tempfile.TemporaryDirectory() as td:
            html = Path(td) / "doc.html"
            r = subprocess.run([pandoc, "-f", PANDOC_FORMATS[ext], "-t", "html5", "--standalone",
                                "--embed-resources", "-o", str(html), str(s)],
                               capture_output=True, text=True, cwd=td, creationflags=NO_WINDOW)
            if r.returncode != 0 or not html.exists():
                raise RuntimeError(f"Pandoc failed: {r.stderr.strip()[-300:]}")
            with pymupdf.open(str(html)) as doc:
                doc.layout(rect=pymupdf.paper_rect(page_size), fontsize=font_size)
                pdf_bytes = doc.convert_to_pdf()
            with pymupdf.open("pdf", pdf_bytes) as pdf:
                pdf.save(out, garbage=3, deflate=True)
        return out

    if ext in MOBI_LIKE:  # KF8/AZW3 often opens as MOBI; fall through to Calibre if not
        try:
            with pymupdf.open(str(s), filetype="mobi") as doc:
                doc.layout(rect=pymupdf.paper_rect(page_size), fontsize=font_size)
                pdf_bytes = doc.convert_to_pdf()
            with pymupdf.open("pdf", pdf_bytes) as pdf:
                pdf.save(out, garbage=3, deflate=True)
            return out
        except Exception:
            pass

    if ext in CALIBRE_FORMATS:
        tool = find_calibre()
        if not tool:
            raise RuntimeError(f"'{ext}' conversion needs Calibre (ebook-convert). "
                               "Install it from https://calibre-ebook.com and retry.")
        r = subprocess.run([tool, str(s), str(out)], capture_output=True,
                           text=True, creationflags=NO_WINDOW)
        if r.returncode != 0 or not out.exists():
            raise RuntimeError(f"Calibre failed: {(r.stderr or r.stdout).strip()[-400:]}")
        return out

    raise ValueError(f"Unsupported format: {ext}")


def page_count(path: str) -> int:
    with pymupdf.open(path) as d:
        return d.page_count


# ---------------------------------------------------------------- merge

def merge_pdfs(files: list[str], dst: str,
               progress: Callable[[int, int], None] | None = None) -> int:
    """Merge PDFs in order; keeps bookmarks. Returns total page count."""
    with pymupdf.open() as out:
        for i, f in enumerate(files, 1):
            with pymupdf.open(f) as d:
                if d.needs_pass:
                    raise ValueError(f"{Path(f).name} is password protected")
                out.insert_pdf(d)
            if progress:
                progress(i, len(files))
        out.save(dst, garbage=3, deflate=True)
        return out.page_count


# ---------------------------------------------------------------- images -> pdf

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
PAGE_SIZES = ["Fit to image", "A4", "A5", "Letter"]


def images_to_pdf(files: list[str], dst: str, page_size: str = "A4",
                  margin: float = 18, progress: Callable[[int, int], None] | None = None) -> int:
    """One image per page. 'Fit to image' makes each page exactly image-sized."""
    from PIL import Image, ImageOps

    with pymupdf.open() as out:
        for i, f in enumerate(files, 1):
            with Image.open(f) as im:
                im = ImageOps.exif_transpose(im)  # honour phone-camera rotation
                if im.mode in ("RGBA", "LA", "P"):  # flatten transparency onto white
                    im = im.convert("RGBA")
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.getchannel("A"))
                    im = bg
                elif im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                px_w, px_h = im.size
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=92)
                data = buf.getvalue()
            if page_size == "Fit to image":
                w, h = px_w * 72 / 96, px_h * 72 / 96
                page = out.new_page(width=w, height=h)
                rect = page.rect
            else:
                pw, ph = pymupdf.paper_size(page_size.lower())
                if px_w > px_h:  # landscape image -> landscape page
                    pw, ph = ph, pw
                page = out.new_page(width=pw, height=ph)
                rect = page.rect + (margin, margin, -margin, -margin)
            page.insert_image(rect, stream=data, keep_proportion=True)
            if progress:
                progress(i, len(files))
        out.save(dst, garbage=3, deflate=True)
        return out.page_count


# ---------------------------------------------------------------- page tools

def parse_pages(spec: str, page_count: int) -> list[int]:
    """'1-3, 7, 10-' -> sorted unique 0-based indexes."""
    pages: set[int] = set()
    for g in parse_ranges(spec, page_count):
        pages.update(g)
    return sorted(pages)


def edit_pages(src: str, dst: str, action: str, spec: str = "", angle: int = 90) -> int:
    """action: delete | keep | rotate | reverse. Returns resulting page count."""
    with pymupdf.open(src) as doc:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        n = doc.page_count
        if action == "reverse":
            doc.select(list(range(n - 1, -1, -1)))
        else:
            pages = parse_pages(spec, n)
            if action == "delete":
                if len(pages) >= n:
                    raise ValueError("That would delete every page")
                doc.delete_pages(pages)
            elif action == "keep":
                doc.select(pages)
            elif action == "rotate":
                for p in pages:
                    pg = doc[p]
                    pg.set_rotation((pg.rotation + angle) % 360)
            else:
                raise ValueError(f"Unknown action {action}")
        doc.save(dst, garbage=3, deflate=True)
        return doc.page_count


# ---------------------------------------------------------------- OCR

def find_tessdata() -> str | None:
    env = os.environ.get("TESSDATA_PREFIX")
    cands = [str(_app_dir() / "tessdata")] + ([env] if env else [])  # bundled copy first
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA")):
        if root:
            cands += [str(Path(root, "Tesseract-OCR", "tessdata")),
                      str(Path(root, "Programs", "Tesseract-OCR", "tessdata"))]
    cands += ["/usr/share/tesseract-ocr/5/tessdata", "/usr/share/tessdata",
              "/usr/share/tesseract-ocr/4.00/tessdata"]
    for c in cands:
        if c and Path(c).is_dir() and any(Path(c).glob("*.traineddata")):
            return c
    return None


def ocr_languages() -> list[str]:
    td = find_tessdata()
    if not td:
        return []
    return sorted(p.stem for p in Path(td).glob("*.traineddata") if p.stem != "osd")


def ocr_pdf(src: str, dst: str, lang: str = "eng", dpi: int = 200,
            progress: Callable[[int, int], None] | None = None) -> int:
    """Make a scanned PDF searchable (adds an invisible text layer)."""
    td = find_tessdata()
    if not td:
        raise RuntimeError("Tesseract OCR not found. Install it from "
                           "https://github.com/UB-Mannheim/tesseract/wiki and retry.")
    with pymupdf.open(src) as doc, pymupdf.open() as out:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=dpi)
            pdf = pymupdf.open("pdf", pix.pdfocr_tobytes(language=lang, tessdata=td))
            out.insert_pdf(pdf)
            if progress:
                progress(i, doc.page_count)
        out.save(dst, garbage=3, deflate=True)
        return out.page_count
