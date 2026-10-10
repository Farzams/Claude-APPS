"""Reader engine (no GUI): open any book/document format, render pages, search, select text, remember position."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

import pymupdf

import core

NATIVE_PAGED = {".pdf", ".xps", ".oxps", ".cbz", ".svg", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
NATIVE_REFLOW = {".epub", ".mobi", ".fb2", ".txt"}
CONVERTED = ({".djvu", ".djv", ".docx", ".odt", ".rtf", ".md", ".html", ".htm", ".xhtml", ".tex", ".ltx",
              ".azw", ".azw3", ".doc", ".lit", ".pdb", ".cbr", ".htmlz", ".txtz"})
EXTENSIONS = sorted(NATIVE_PAGED | NATIVE_REFLOW | CONVERTED)
FILTER = "Books and documents (" + " ".join("*" + e for e in EXTENSIONS) + ");;All files (*.*)"
REFLOW_SIZE = (470.0, 680.0)


class PasswordNeeded(Exception):
    pass


def cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    d = Path(base) / "PDFToolkit" / "reader-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(path: str) -> str:
    st = os.stat(path)
    return hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:20]


def prune_cache(max_mb: int = 600) -> None:
    """Keep the converted-book cache from growing without limit (oldest files go first)."""
    try:
        files = sorted(cache_dir().glob("*.pdf"), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        while files and total > max_mb * 1024 * 1024:
            p = files.pop(0)
            total -= p.stat().st_size
            p.unlink(missing_ok=True)
    except OSError:
        pass


class Book:
    """An opened document. All access to `doc` goes through `lock` (MuPDF is not thread safe)."""

    def __init__(self, source: str, doc: pymupdf.Document, reflow: bool, converted: bool):
        self.source = source                    # the file the user opened
        self.doc = doc
        self.reflow = reflow
        self.converted = converted
        self.lock = threading.RLock()
        self.fontsize = 12.0
        self.title = Path(source).stem
        self.sizes: list[tuple[float, float]] = []
        self._rects: dict[tuple, list] = {}
        self._links: dict[int, list] = {}
        self.refresh()

    # ---- structure
    def refresh(self):
        with self.lock:
            if self.reflow:
                self.doc.layout(width=REFLOW_SIZE[0], height=REFLOW_SIZE[1], fontsize=self.fontsize)
            self.sizes = [(p.rect.width, p.rect.height) for p in self.doc]
            md = self.doc.metadata or {}
            t = (md.get("title") or "").strip()
            if t and len(t) > 1:
                self.title = t
            self.author = (md.get("author") or "").strip()
        self._rects.clear()
        self._links.clear()

    @property
    def page_count(self) -> int:
        return len(self.sizes)

    def toc(self) -> list[tuple[int, str, int]]:
        with self.lock:
            try:
                return [(lvl, core.normalize_persian(t) if core.is_rtl_text(t) else t, max(p - 1, 0))
                        for lvl, t, p in self.doc.get_toc(simple=True) if p and p > 0]
            except Exception:
                return []

    def is_rtl(self) -> bool:
        with self.lock:
            sample = " ".join(self.doc[i].get_text()[:600] for i in range(min(self.page_count, 4)))
        return core.is_rtl_text(sample)

    def set_fontsize(self, size: float):
        self.fontsize = max(7.0, min(size, 32.0))
        self.refresh()

    # ---- pictures
    def render(self, index: int, zoom: float, mode: str = "light") -> tuple[bytes, int, int]:
        """RGB bytes of a page. mode: light | sepia | dark."""
        with self.lock:
            pix = self.doc[index].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            return bytes(pix.samples), pix.width, pix.height

    # ---- text
    def page_text(self, index: int) -> str:
        with self.lock:
            return core.normalize_persian(core._page_text(self.doc[index])).replace("‎", "").replace("‏", "")

    def text_in(self, index: int, rect: tuple) -> str:
        with self.lock:
            page = self.doc[index]
            r = pymupdf.Rect(rect)
            txt = page.get_text("text", clip=r, sort=True)
            if not txt.strip():
                return ""
            return core.normalize_persian(txt).replace("‎", "").replace("‏", "").strip()

    def find_rects(self, index: int, query: str) -> list[tuple]:
        key = (index, query)
        if key not in self._rects:
            import pdftools
            with self.lock:
                try:
                    self._rects[key] = [tuple(r) for r in pdftools.find_rects(self.doc[index], query)]
                except Exception:
                    self._rects[key] = []
        return self._rects[key]

    def search(self, query: str, cancel=None, on_hit=None) -> list[tuple[int, str]]:
        """[(page, snippet)] for pages containing the query (Persian-aware: ignores spaces, half-spaces, forms)."""
        target = core._fold(query)
        hits = []
        if not target:
            return hits
        for i in range(self.page_count):
            if cancel and cancel():
                break
            with self.lock:
                text = self.doc[i].get_text()
            if target in core._fold(text) or target[::-1] in core._fold(text):
                snippet = ""
                for line in text.splitlines():
                    if target in core._fold(line) or target[::-1] in core._fold(line):
                        snippet = core.normalize_persian(line).strip()[:110]
                        break
                hits.append((i, snippet))
                if on_hit:
                    on_hit(i, snippet)
        return hits

    def links(self, index: int) -> list[dict]:
        if index not in self._links:
            with self.lock:
                try:
                    self._links[index] = self.doc[index].get_links()
                except Exception:
                    self._links[index] = []
        return self._links[index]

    def close(self):
        with self.lock:
            try:
                self.doc.close()
            except Exception:
                pass


def open_book(path: str, password: str = "", progress=None) -> Book:
    """Open any supported file. Formats MuPDF cannot show directly are converted to PDF once and cached."""
    ext = Path(path).suffix.lower()
    say = progress or (lambda _m: None)
    if ext == ".pdf":
        doc = pymupdf.open(path)
        if doc.needs_pass and not doc.authenticate(password):
            doc.close()
            raise PasswordNeeded()
        return Book(path, doc, False, False)
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}:
        return Book(path, pymupdf.open(path), False, False)
    if ext in {".xps", ".oxps", ".cbz", ".svg"}:
        return Book(path, pymupdf.open(path), False, False)
    if ext in {".epub", ".mobi", ".fb2"}:
        return Book(path, pymupdf.open(path), True, False)
    if ext == ".txt":
        say("Preparing…")
        text = core.read_text_file(path)
        import html as _h
        rtl = core.is_rtl_text(text)
        body = "".join(f"<p>{_h.escape(l) or '&nbsp;'}</p>" for l in text.splitlines())
        html = f'<html dir="{"rtl" if rtl else "ltr"}"><body>{body}</body></html>'
        return Book(path, pymupdf.open(stream=html.encode("utf-8"), filetype="html"), True, False)
    if ext in CONVERTED:
        cached = cache_dir() / f"{_cache_key(path)}.pdf"
        if not cached.exists():
            say("Converting…")
            tmp = Path(tempfile.mkdtemp(prefix="pdftk_rd_"))
            try:
                out = core.convert_to_pdf(path, str(tmp), "a5", 11)
                cached.write_bytes(Path(out).read_bytes())
            finally:
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)
            prune_cache()
        else:
            os.utime(cached, None)
        b = Book(path, pymupdf.open(str(cached)), False, True)
        return b
    # unknown extension: let MuPDF try
    return Book(path, pymupdf.open(path), pymupdf.open(path).is_reflowable, False)


# ---------------------------------------------------------------- remembered state
def _state_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "PDFToolkit" / "reader.json"


def load_state() -> dict:
    try:
        d = json.loads(_state_path().read_text(encoding="utf-8"))
        d.setdefault("books", {})
        d.setdefault("recent", [])
        return d
    except Exception:
        return {"books": {}, "recent": []}


def save_state(state: dict) -> None:
    try:
        p = _state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def remember(state: dict, book: Book, **info) -> None:
    key = os.path.abspath(book.source)
    entry = state["books"].setdefault(key, {})
    entry.update(info)
    entry["title"] = book.title
    entry["pages"] = book.page_count
    entry["time"] = time.time()
    rec = [r for r in state["recent"] if r != key]
    state["recent"] = ([key] + rec)[:24]
    for k in list(state["books"]):             # forget books that no longer exist and are not recent
        if k not in state["recent"]:
            state["books"].pop(k, None)
