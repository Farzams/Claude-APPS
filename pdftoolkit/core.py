"""Core PDF operations (no GUI): split, compress, convert."""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
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
                  ".markdown": "markdown", ".rst": "rst", ".tex": "latex",
                  ".epub": "epub", ".fb2": "fb2"}
PANDOC_OR_NATIVE = {".epub", ".fb2"}  # pandoc path gives correct Farsi; native is the fallback
MOBI_LIKE = {".azw", ".azw3"}  # tried natively first, Calibre as fallback
CALIBRE_FORMATS = {".azw", ".azw3", ".doc", ".lit", ".pdb", ".cbr", ".htmlz", ".txtz"}
DJVU_FORMATS = {".djvu", ".djv"}
ALL_FORMATS = sorted(NATIVE_FORMATS | set(PANDOC_FORMATS) | CALIBRE_FORMATS | DJVU_FORMATS)


def _find_tool(names: list[str], extra_dirs: list[str]) -> str | None:
    """Look in the given folders first (so bundled copies win), then on PATH."""
    for d in extra_dirs:
        for n in names:
            for ext in ("", ".exe"):
                cand = Path(d) / (n + ext)
                if cand.is_file():
                    return str(cand)
    for n in names:
        p = shutil.which(n)
        if p:
            return p
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
    """Pandoc from the pypandoc package (bundled), an app folder, or PATH."""
    cands: list[str] = []
    try:
        import pypandoc
        p = pypandoc.get_pandoc_path()
        if p:
            cands += [p, p + ".exe"]
        files = Path(pypandoc.__file__).parent / "files"
        cands += [str(files / "pandoc.exe"), str(files / "pandoc")]
    except Exception:
        pass
    cands += [str(_app_dir() / "pypandoc" / "files" / n) for n in ("pandoc.exe", "pandoc")]
    for c in cands:
        if Path(c).is_file():
            return c
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

    if ext in {".txt", ".html", ".htm", ".xhtml"}:
        if ext == ".txt":
            import html as _html
            body = "".join(f"<p>{_html.escape(l) or '&nbsp;'}</p>"
                           for l in read_text_file(src).splitlines())
            html_to_pdf(body, str(out), page_size, font_size)
        else:
            html_to_pdf(read_text_file(src), str(out), page_size, font_size,
                        base_dirs=[str(s.parent)])
        return out

    if ext in PANDOC_FORMATS:
        pandoc = find_pandoc()
        try:
            if not pandoc:
                raise RuntimeError("Pandoc is missing from this build.")
            with tempfile.TemporaryDirectory() as td:
                html = Path(td) / "doc.html"
                r = subprocess.run([pandoc, "-f", PANDOC_FORMATS[ext], "-t", "html5", "--standalone",
                                    f"--extract-media={td}", "-o", str(html), str(s)],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   cwd=td, creationflags=NO_WINDOW)
                if r.returncode != 0 or not html.exists():
                    raise RuntimeError(f"Pandoc failed: {r.stderr.strip()[-300:]}")
                text = html.read_text(encoding="utf-8")
                # make image paths relative to the extraction folder (works with Windows paths)
                text = re.sub(r'src="[^"]*?[\\/](media[\\/][^"]+)"',
                              lambda m: 'src="' + m.group(1).replace("\\", "/") + '"', text)
                html_to_pdf(text, str(out), page_size, font_size, base_dirs=[td])
            return out
        except Exception:
            if ext not in PANDOC_OR_NATIVE:
                raise

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


# ---------------------------------------------------------------- RTL / Farsi helpers

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
RTL_RE = re.compile(r"[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]")
LATIN_RE = re.compile(r"[A-Za-z]")
FONT_DIR_NAME = "fonts"


def fonts_dir() -> Path:
    return _app_dir() / FONT_DIR_NAME


def is_rtl_text(text: str, threshold: float = 0.4) -> bool:
    """True when most letters are Arabic-script (Farsi/Arabic/Urdu) or Hebrew."""
    ar = len(RTL_RE.findall(text))
    la = len(LATIN_RE.findall(text))
    return ar > 0 and ar / max(ar + la, 1) >= threshold


def normalize_persian(text: str) -> str:
    """Undo presentation forms (ﻣﻘﺪﻣﻪ -> مقدمه) and unify Arabic/Persian letter variants."""
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")


def read_text_file(path: str) -> str:
    """Read a text file, guessing UTF-8 / UTF-16 / Windows-1256 (old Farsi files)."""
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def html_to_pdf(html: str, dst: str, page_size: str = "a5", font_size: int = 11,
                base_dirs: list[str] | None = None, rtl: bool | None = None,
                margin: float = 40) -> int:
    """Render HTML to a PDF with proper Persian/Arabic shaping and right-to-left layout.

    Headings become PDF bookmarks. Returns the page count.
    """
    text_only = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", html)
    text_only = re.sub(r"<[^>]+>", " ", text_only)
    if rtl is None:
        rtl = is_rtl_text(text_only)
    has_arabic = bool(ARABIC_RE.search(text_only))
    css = ""
    fam = "sans-serif"
    if has_arabic:
        css += (f"@font-face{{font-family:ArabicUI;src:url(NotoSansArabic-Regular.ttf)}}"
                f"@font-face{{font-family:ArabicUI;font-weight:bold;src:url(NotoSansArabic-Bold.ttf)}}")
        fam = "ArabicUI, sans-serif"
    css += (f"html,body{{max-width:none;margin:0;padding:0}}"
            f"body{{font-family:{fam};line-height:1.5}}img{{max-width:100%}}")
    if rtl:
        css += ("body,p,div,li,td,th,h1,h2,h3,h4,h5,h6,blockquote{direction:rtl;text-align:right}"
                "ul,ol{margin-right:1.4em;margin-left:0}")
    if rtl and "<html" not in html[:200].lower():
        html = f'<html dir="rtl"><body>{html}</body></html>'
    elif rtl:
        html = re.sub(r"<html(?![^>]*\bdir=)", '<html dir="rtl"', html, count=1, flags=re.I)
    arch = pymupdf.Archive(str(fonts_dir())) if fonts_dir().is_dir() else pymupdf.Archive()
    for d in base_dirs or []:
        arch.add(pymupdf.Archive(d))
    story = pymupdf.Story(html=html, user_css=css, em=font_size, archive=arch)
    mediabox = pymupdf.paper_rect(page_size)
    where = mediabox + (margin, margin, -margin, -margin)
    toc: list[list] = []
    page_no = [1]

    def on_pos(pos):
        if pos.heading and (pos.open_close & 1) and pos.text.strip():
            toc.append([min(pos.heading, 6), pos.text.strip()[:120], page_no[0]])

    # Write to a scratch file first: Windows keeps the writer's file locked for a moment,
    # so the final PDF (with bookmarks) is saved as a new file instead of replacing in place.
    raw = os.path.join(tempfile.gettempdir(), f"pdftk_{os.getpid()}_{id(story)}.pdf")
    writer = pymupdf.DocumentWriter(raw)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.element_positions(on_pos, {})
        story.draw(dev)
        writer.end_page()
        page_no[0] += 1
    writer.close()
    del writer, story
    import gc
    gc.collect()
    with pymupdf.open(raw) as pdf:
        n = pdf.page_count
        if toc:
            fixed, last = [], 0
            for lvl, title, pg in toc:  # bookmark levels may not skip a level
                lvl = 1 if not fixed else min(lvl, last + 1)
                fixed.append([lvl, title, min(pg, n)])
                last = lvl
            try:
                pdf.set_toc(fixed)
            except Exception:
                pass
        pdf.save(str(dst), garbage=3, deflate=True)
    try:
        os.remove(raw)
    except OSError:
        pass
    return n


# ---------------------------------------------------------------- OCR (Tesseract)

def find_tesseract() -> str | None:
    here = _app_dir()
    cands = [str(here / "tesseract"), str(here)] + _program_dirs("Tesseract-OCR", "Programs/Tesseract-OCR")
    return _find_tool(["tesseract"], cands)


def find_tessdata() -> str | None:
    exe = find_tesseract()
    cands = []
    if os.environ.get("TESSDATA_PREFIX"):
        cands.append(os.environ["TESSDATA_PREFIX"])
    if exe:
        cands.append(str(Path(exe).parent / "tessdata"))
    cands += ["/usr/share/tesseract-ocr/5/tessdata", "/usr/share/tessdata",
              "/usr/share/tesseract-ocr/4.00/tessdata"]
    for c in cands:
        if c and Path(c).is_dir() and any(Path(c).glob("*.traineddata")):
            return c
    return None


def ocr_languages() -> list[str]:
    td = find_tessdata()
    if not (td and find_tesseract()):
        return []
    return sorted(p.stem for p in Path(td).glob("*.traineddata") if p.stem not in ("osd", "equ"))


_CJK_RE = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uac00-\ud7af\uff00-\uffef]")


def _tess_words(exe: str, tessdata: str, png: str, lang: str, dpi: int, psm: int):
    r = subprocess.run([exe, png, "stdout", "-l", lang, "--dpi", str(dpi), "--psm", str(psm),
                        "--tessdata-dir", tessdata, "tsv"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
                       env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    if r.returncode != 0:
        raise RuntimeError(f"Tesseract failed: {r.stderr.strip()[-300:]}")
    words = []
    for ln in r.stdout.splitlines()[1:]:
        c = ln.split("\t", 11)
        if len(c) == 12 and c[0] == "5" and c[11].strip():
            words.append((int(c[6]), int(c[7]), int(c[8]), int(c[9]), c[11].strip()))
    return words


def ocr_pdf(src: str, dst: str, lang: str = "eng", dpi: int = 300, skip_text: bool = True,
            psm: int = 3, progress: Callable[[int, int], None] | None = None) -> tuple[int, int]:
    """Make a scanned PDF searchable by adding an invisible, correctly ordered text layer.

    Works for right-to-left scripts (Farsi/Arabic/Hebrew): the text can be searched and
    copied in logical order. Returns (pages_ocrd, total_pages).
    """
    from concurrent.futures import ThreadPoolExecutor

    exe, td = find_tesseract(), find_tessdata()
    if not exe or not td:
        raise RuntimeError("OCR engine (Tesseract) is missing from this build.")
    try:
        from bidi import get_display
    except Exception:
        def get_display(x): return x
    font_path = fonts_dir() / "DejaVuSans.ttf"
    use_font = font_path.is_file()
    font = pymupdf.Font(fontfile=str(font_path)) if use_font else pymupdf.Font("helv")
    cjk_name = "china-s" if "chi_sim" in lang else "china-t" if "chi_tra" in lang else \
        "japan" if "jpn" in lang else "korea" if "kor" in lang else "china-s"

    done = 0
    with pymupdf.open(src) as doc, tempfile.TemporaryDirectory() as tmp:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        total = doc.page_count
        todo = [i for i in range(total)
                if not (skip_text and len(doc[i].get_text().strip()) > 20)]
        if not todo:
            raise ValueError("Every page already contains text. Untick 'skip pages with text' to force OCR.")

        # render serially (PyMuPDF is not thread-safe), run tesseract in parallel
        workers = max(1, min(os.cpu_count() or 2, 6))
        results = {}
        with ThreadPoolExecutor(workers) as pool:
            futs = []
            for i in todo:
                png = os.path.join(tmp, f"p{i}.png")
                doc[i].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY).save(png)
                futs.append(pool.submit(_tess_words, exe, td, png, lang, dpi, psm))
            for i, f in zip(todo, futs):
                results[i] = f.result()
                done += 1
                if progress:
                    progress(done, len(todo))

        k = 72 / dpi
        for i in todo:
            page = doc[i]
            if use_font:
                page.insert_font(fontname="ocrf", fontfile=str(font_path))
            for l, t, w, h, txt in results[i]:
                fs = max(h * k * 0.85, 4)
                parts = [(txt, l, w)]
                m = re.match(r"^(.*?)([\.,;:!?\u060c\u061b\u061f\u00bb)]+)$", txt)
                if m and m.group(1) and RTL_RE.search(m.group(1)):
                    core_t, punc = m.groups()
                    pw = w * len(punc) / len(txt)
                    parts = [(core_t, l + pw, w - pw), (punc, l, pw)]  # punctuation sits at the left
                for tx, pl, pwid in parts:
                    if RTL_RE.search(tx):
                        tx = get_display(tx)  # visual order, so extraction returns logical order
                    if _CJK_RE.search(tx):
                        fname, tl = cjk_name, pymupdf.get_text_length(tx, fontname=cjk_name, fontsize=fs)
                    else:
                        fname = "ocrf" if use_font else "helv"
                        tl = font.text_length(tx, fontsize=fs)
                    if tl <= 0:
                        continue
                    pt = pymupdf.Point(pl * k, (t + h) * k - h * k * 0.2) * page.derotation_matrix
                    try:
                        page.insert_text(pt, tx, fontname=fname, fontsize=fs, render_mode=3,
                                         morph=(pt, pymupdf.Matrix(pwid * k / tl, 1)),
                                         rotate=page.rotation)
                    except Exception:
                        continue
        try:
            doc.subset_fonts()
        except Exception:
            pass
        doc.save(dst, garbage=3, deflate=True)
    return len(todo), total


# ---------------------------------------------------------------- text extraction

def _tess_text(exe, td, png, lang, dpi):
    r = subprocess.run([exe, png, "stdout", "-l", lang, "--dpi", str(dpi), "--psm", "3",
                        "--tessdata-dir", td], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=NO_WINDOW)
    return r.stdout


_PUNCT_ONLY = re.compile(r"^[.,;:!?\u060c\u061b\u061f\u00bb)\]]+$")


def _page_text(page) -> str:
    """Page text in reading order. OCR'd pages store one word per box, so rebuild real lines."""
    txt = page.get_text("text")  # stream order keeps Farsi in reading order
    words = page.get_text("words")
    lines = [l for l in txt.splitlines() if l.strip()]
    if len(words) < 8 or not lines:
        return txt
    words = sorted(words, key=lambda w: (w[1] + w[3]) / 2)
    heights = sorted(w[3] - w[1] for w in words)
    tol = max(heights[len(heights) // 2] * 0.5, 2)
    rows, cur, cy = [], [], None
    for w in words:
        yc = (w[1] + w[3]) / 2
        if cy is None or abs(yc - cy) <= tol:
            cur.append(w)
            cy = yc if cy is None else (cy * (len(cur) - 1) + yc) / len(cur)
        else:
            rows.append(cur)
            cur, cy = [w], yc
    rows.append(cur)
    single = sum(1 for l in lines if sum(1 for t in l.split() if not _PUNCT_ONLY.match(t)) <= 1)
    if single < 0.7 * len(lines) or len(rows) > 0.7 * len(lines):
        return txt  # normal text: MuPDF's own lines are already right
    out = []
    for row in rows:
        rtl = sum(1 for w in row if RTL_RE.search(w[4])) * 2 >= len(row)
        row.sort(key=lambda w: w[0], reverse=rtl)
        toks: list[str] = []
        for w in row:
            if toks and _PUNCT_ONLY.match(w[4]):
                toks[-1] += w[4]
            else:
                toks.append(w[4])
        out.append(" ".join(toks))
    return "\n".join(out)


def extract_text(src: str, dst: str, fmt: str = "txt", ocr_lang: str | None = None,
                 fix_reversed: bool = False,
                 progress: Callable[[int, int], None] | None = None) -> tuple[int, int]:
    """PDF -> .txt/.docx. Pages without text are OCR'd when ocr_lang is given.

    Returns (chars, ocr_pages). Farsi presentation forms are normalised so the text
    is searchable/copyable; fix_reversed repairs PDFs whose Farsi comes out backwards.
    """
    exe, td = find_tesseract(), find_tessdata()
    try:
        from bidi import get_display
    except Exception:
        def get_display(x): return x
    pages_text, ocr_pages = [], 0
    with pymupdf.open(src) as doc, tempfile.TemporaryDirectory() as tmp:
        if doc.needs_pass:
            raise ValueError("The PDF is password protected")
        for i, page in enumerate(doc, 1):
            txt = _page_text(page)
            if len(txt.strip()) < 15 and ocr_lang and exe and td:
                png = os.path.join(tmp, "p.png")
                page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY).save(png)
                txt = _tess_text(exe, td, png, ocr_lang, 300)
                ocr_pages += 1
            elif fix_reversed:
                txt = "\n".join(get_display(l) if RTL_RE.search(l) else l for l in txt.splitlines())
            pages_text.append(normalize_persian(txt).replace("\u200e", "").replace("\u200f", "").strip())
            if progress:
                progress(i, doc.page_count)
    full = "\n\n".join(pages_text)
    if fmt == "txt":
        Path(dst).write_text(full, encoding="utf-8-sig")  # BOM so Notepad shows Farsi correctly
    else:
        from docx import Document
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        d = Document()
        for pi, ptxt in enumerate(pages_text):
            for para in [p for p in re.split(r"\n\s*\n|\n", ptxt) if p.strip()]:
                p = d.add_paragraph()
                run = p.add_run(para.strip())
                if is_rtl_text(para, 0.3):
                    ppr = p._p.get_or_add_pPr()
                    ppr.append(OxmlElement("w:bidi"))
                    rpr = run._r.get_or_add_rPr()
                    rpr.append(OxmlElement("w:rtl"))
                    rfonts = OxmlElement("w:rFonts")
                    rfonts.set(qn("w:cs"), "Tahoma")
                    rpr.append(rfonts)
            if pi < len(pages_text) - 1:
                d.add_page_break()
        d.save(dst)
    return len(full), ocr_pages


# ---------------------------------------------------------------- viewer

def _search_variants(q: str) -> list[str]:
    return [q, q.replace("\u200c", ""), q.replace("\u200c", " ")]


def _fold(t: str) -> str:  # ignore half-spaces, spaces, presentation forms, case
    t = normalize_persian(t).replace("\u200c", "").replace("\u200f", "").replace("\u200e", "")
    return "".join(t.split()).lower()


class PdfReader:
    """Open PDF for the Read tab: render pages (with search highlights), text, search."""

    def __init__(self, path: str):
        self.path = path
        self.doc = pymupdf.open(path)
        if self.doc.needs_pass:
            self.doc.close()
            raise ValueError("The PDF is password protected")

    @property
    def page_count(self) -> int:
        return self.doc.page_count

    def page_size(self, index: int) -> tuple[float, float]:
        r = self.doc[index].rect
        return r.width, r.height

    def render(self, index: int, zoom: float = 1.3, query: str = "") -> tuple[bytes, int]:
        """PNG bytes of a page; search matches are highlighted. Returns (png, match_count)."""
        page = self.doc[index]
        annots, hits = [], 0
        if query.strip():
            for v in _search_variants(query.strip()):
                rects = page.search_for(v)
                if rects:
                    hits = len(rects)
                    for r in rects:
                        a = page.add_highlight_annot(r)
                        if a:
                            annots.append(a)
                    break
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        png = pix.tobytes("png")
        for a in annots:
            page.delete_annot(a)
        return png, hits

    def text(self, index: int) -> str:
        return normalize_persian(_page_text(self.doc[index])).replace("\u200e", "").replace("\u200f", "")

    def search(self, query: str) -> list[int]:
        q = _fold(query)
        if not q:
            return []
        hits = []
        for i, page in enumerate(self.doc):
            if any(page.search_for(v) for v in _search_variants(query.strip())) or q in _fold(page.get_text()):
                hits.append(i)
        return hits

    def close(self):
        self.doc.close()


def search_pdf(path: str, query: str) -> list[int]:
    """0-based page numbers containing query (Persian-normalised)."""
    r = PdfReader(path)
    try:
        return r.search(query)
    finally:
        r.close()
