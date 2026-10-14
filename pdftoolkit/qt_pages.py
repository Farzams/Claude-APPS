"""The everyday tools: split, merge, compress, convert, images, page tools, OCR, extract text."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLineEdit

import core
from i18n import rtl, t, tr, trf
from qt_common import (FileList, FileRow, Form, Tool, mkcheck, mkcombo, mklabel)

LANG_NAMES = {"fas": "Persian (Farsi)", "eng": "English", "ara": "Arabic", "deu": "German", "fra": "French",
              "spa": "Spanish", "ita": "Italian", "rus": "Russian", "tur": "Turkish", "nld": "Dutch",
              "por": "Portuguese", "heb": "Hebrew", "ell": "Greek", "chi_sim": "Chinese (Simplified)",
              "jpn": "Japanese", "kor": "Korean", "urd": "Urdu", "pus": "Pashto", "hin": "Hindi", "ukr": "Ukrainian",
              "pol": "Polish", "ces": "Czech", "swe": "Swedish", "dan": "Danish", "fin": "Finnish", "hun": "Hungarian",
              "ron": "Romanian", "bul": "Bulgarian", "lat": "Latin", "aze": "Azerbaijani", "uzb": "Uzbek"}
FA_LANG_NAMES = {"fas": "فارسی", "eng": "انگلیسی", "ara": "عربی", "deu": "آلمانی", "fra": "فرانسوی",
                 "spa": "اسپانیایی", "ita": "ایتالیایی", "rus": "روسی", "tur": "ترکی", "nld": "هلندی",
                 "por": "پرتغالی", "heb": "عبری", "ell": "یونانی", "chi_sim": "چینی", "jpn": "ژاپنی",
                 "kor": "کره‌ای", "urd": "اردو", "pus": "پشتو", "hin": "هندی", "ukr": "اوکراینی", "pol": "لهستانی",
                 "ces": "چکی", "swe": "سوئدی", "dan": "دانمارکی", "fin": "فنلاندی", "hun": "مجاری", "ron": "رومانیایی",
                 "bul": "بلغاری", "lat": "لاتین", "aze": "آذربایجانی", "uzb": "ازبکی"}
LANG_ORDER = ["fas", "eng", "ara"]


def lang_choices() -> dict[str, str]:
    """{label: code}, Persian first."""
    codes = core.ocr_languages()
    codes.sort(key=lambda c: (LANG_ORDER.index(c) if c in LANG_ORDER else 99, LANG_NAMES.get(c, c)))
    names = FA_LANG_NAMES if rtl() else LANG_NAMES
    return {f"{names.get(c, c)}  ({c})": c for c in codes}


def tess_lang(code: str, also_english: bool) -> str:
    if also_english and code != "eng" and "eng" in core.ocr_languages():
        return f"{code}+eng"
    return code


def missing_tools() -> str:
    names = [n for n, ok in [("DjVu", core.find_ddjvu()),
                             ("OCR", core.find_tesseract()), ("Ghostscript", core.find_gs())] if not ok]
    return ", ".join(names)


def _stem_dir(p: str) -> str:
    return str(Path(p).parent)


class SplitTool(Tool):
    key, icon, title = "split", "split", "Split"
    subtitle = "Cut a PDF into several smaller files."

    def build(self):
        f = Form()
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("dir")
        f.row("PDF file", self.src)
        f.row("Output folder", self.out)
        self.info = mklabel("", "muted", translate=False)
        f.row("", self.info, span=True)
        self.mode = mkcombo({tr("Custom ranges (one file per range)"): "ranges", tr("Every N pages"): "every",
                             tr("Into N equal parts"): "parts", tr("Every page separately"): "single"})
        f.row("Split by", self.mode)
        self.val = QLineEdit("1-5, 6-10")
        self.val.setPlaceholderText(tr("e.g. 1-3, 5, 8-   or   10"))
        f.row("Value", self.val)
        self.body.addLayout(f)
        self.note("Ranges: '1-3, 5, 8-' makes three files (pages 1-3, page 5, page 8 to the end). "
                  "For 'Every N pages' / 'Into N equal parts' type just the number.")
        self.body.addStretch(1)
        self.run_button("Split", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_stem_dir(p))
        try:
            self.info.setText(trf("{n} pages", n=core.page_count(p)) + f"  ·  {core.fmt_size(Path(p).stat().st_size)}")
        except Exception as e:
            self.info.setText(str(e))

    def run(self):
        src, out, mode, val = self.src.get(), self.out.get(), self.mode.currentData(), self.val.text().strip()
        if not self.need(src, out):
            return

        def job(log, prog):
            n = core.page_count(src)
            if mode == "ranges":
                groups = core.parse_ranges(val, n)
            elif mode == "every":
                groups = core.groups_every_n(n, int(val))
            elif mode == "parts":
                groups = core.groups_into_parts(n, int(val))
            else:
                groups = core.groups_every_n(n, 1)
            files = core.split_pdf(src, out, groups, prog)
            log(trf("✔ Created {n} file(s)", n=len(files)))
            return out
        self.win.run(job)


class MergeTool(Tool):
    key, icon, title = "merge", "merge", "Merge"
    subtitle = "Combine several PDF files into one, in the order shown."

    def build(self):
        self.files = FileList("PDF (*.pdf)", 8)
        self.body.addWidget(self.files, 1)
        f = Form()
        self.out = FileRow("save")
        f.row("Save as", self.out)
        self.body.addLayout(f)
        self.run_button("Merge", self.run)

    def run(self):
        files, out = self.files.files, self.out.get()
        if len(files) < 2 or not out:
            return self.win.warn(tr("Missing information"), tr("Add at least two PDFs and choose where to save."))

        def job(log, prog):
            n = core.merge_pdfs(files, out, prog)
            log(trf("✔ Merged {n} files → {name} ({pages} pages)", n=len(files), name=Path(out).name, pages=n))
            return _stem_dir(out)
        self.win.run(job)


class CompressTool(Tool):
    key, icon, title = "compress", "compress", "Compress"
    subtitle = "Make PDFs smaller by reducing image size and cleaning up the file."

    def build(self):
        f = Form()
        self.src = FileRow(on_pick=lambda p: None if self.out.get() else self.out.edit.setText(_stem_dir(p)))
        self.out = FileRow("dir")
        f.row("PDF file", self.src)
        f.row("Output folder", self.out)
        self.level = mkcombo({tr(k): k for k in core.COMPRESS_LEVELS}, list(core.COMPRESS_LEVELS)[1])
        f.row("Level", self.level)
        gs = core.find_gs()
        engines = ({tr("Ghostscript (stronger)"): "ghostscript"} if gs else {}) | {tr("Built-in"): "builtin"}
        self.engine = mkcombo(engines)
        f.row("Engine", self.engine)
        self.body.addLayout(f)
        self.note("Ghostscript is built in — it gives the strongest compression for scanned books." if gs
                  else "Ghostscript is not available in this build; using the built-in engine.")
        self.note("Saved as <name>_compressed.pdf. If a file can't be made smaller, the original is kept.")
        self.body.addStretch(1)
        self.run_button("Compress", self.run)

    def run(self):
        src, out = self.src.get(), self.out.get()
        level, engine = self.level.currentData(), self.engine.currentData()
        if not self.need(src, out):
            return

        def job(log, prog):
            prog(0, 1)
            dst = core.unique_path(Path(out) / (Path(src).stem + "_compressed.pdf"))
            a, b = core.compress_pdf(src, str(dst), level, engine)
            prog(1, 1)
            log(f"✔ {dst.name}: {core.fmt_size(a)} → {core.fmt_size(b)}  (−{(1 - b / a) * 100:.1f}%)")
            return out
        self.win.run(job)


class ConvertTool(Tool):
    key, icon, title = "convert", "convert", "Convert to PDF"
    subtitle = "EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT, DOCX, TEX and more."

    def build(self):
        ex = " ".join("*" + e for e in core.ALL_FORMATS)
        self.files = FileList(f"Supported ({ex});;All files (*.*)", 4)
        self.body.addWidget(self.files, 1)
        f = Form()
        self.out = FileRow("dir")
        f.row("Output folder", self.out)
        self.size = mkcombo(["A5", "A4", "A6", "Letter"])
        f.row("Ebook page size", self.size)
        self.font = mkcombo([str(i) for i in range(8, 21)], "11")
        self.font.setCurrentText("11")
        f.row("Ebook font size", self.font)
        self.body.addLayout(f)
        miss = missing_tools()
        if miss:
            self.note(trf("Not available in this build: {names}", names=miss))
        self.note("Persian / Arabic / Hebrew documents are shaped and laid out right-to-left automatically.")
        self.run_button("Convert", self.run)

    def run(self):
        files, out = self.files.files, self.out.get()
        if not files or not out:
            return self.win.warn(tr("Missing information"), tr("Add files and choose an output folder."))
        size, font = self.size.currentText().lower(), int(self.font.currentText())

        def job(log, prog):
            for i, fpath in enumerate(files, 1):
                try:
                    p = core.convert_to_pdf(fpath, out, size, font)
                    log(f"✔ {Path(fpath).name} → {p.name}")
                except Exception as e:
                    log(f"✘ {Path(fpath).name}: {e}")
                prog(i, len(files))
            return out
        self.win.run(job)


class ImagesTool(Tool):
    key, icon, title = "images", "images", "Images to PDF"
    subtitle = "Pick several pictures, put them in order and turn them into one PDF."

    def build(self):
        ex = " ".join("*" + e for e in core.IMAGE_EXTS)
        self.files = FileList(f"Images ({ex});;All files (*.*)", 6)
        self.body.addWidget(self.files, 1)
        f = Form()
        self.out = FileRow("save")
        f.row("Save as", self.out)
        self.size = mkcombo({tr("Fit to image"): "Fit to image", "A4": "A4", "A5": "A5", "Letter": "Letter"}, "A4")
        f.row("Page size", self.size)
        self.margin = mkcombo({tr("None"): 0, tr("Small"): 18, tr("Normal"): 36}, 18)
        f.row("Margin", self.margin)
        self.body.addLayout(f)
        self.run_button("Create PDF", self.run)

    def run(self):
        files, out = self.files.files, self.out.get()
        if not files or not out:
            return self.win.warn(tr("Missing information"), tr("Add pictures and choose where to save."))
        size, margin = self.size.currentData(), self.margin.currentData()

        def job(log, prog):
            n = core.images_to_pdf(files, out, size, margin, prog)
            log(trf("✔ {n} picture(s) → {name}", n=n, name=Path(out).name))
            return _stem_dir(out)
        self.win.run(job)


class PagesTool(Tool):
    key, icon, title = "pages", "pages", "Page tools"
    subtitle = "Delete, extract, rotate or reverse pages."

    def build(self):
        f = Form()
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("save")
        f.row("PDF file", self.src)
        f.row("Save as", self.out)
        self.info = mklabel("", "muted", translate=False)
        f.row("", self.info, span=True)
        self.action = mkcombo({tr("Delete pages"): "delete", tr("Keep only (extract) pages"): "keep",
                               tr("Rotate pages"): "rotate", tr("Reverse page order"): "reverse"})
        f.row("Action", self.action)
        self.pages = QLineEdit("1-3, 7")
        self.pages.setPlaceholderText(tr("e.g. 1-3, 7, 10-"))
        f.row("Pages", self.pages)
        self.angle = mkcombo({tr("90° clockwise"): 90, tr("180°"): 180, tr("90° counter-clockwise"): 270})
        f.row("Rotate by", self.angle)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Apply", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(str(Path(p).with_name(Path(p).stem + "_edited.pdf")))
        try:
            self.info.setText(trf("{n} pages", n=core.page_count(p)))
        except Exception as e:
            self.info.setText(str(e))

    def run(self):
        src, out, action = self.src.get(), self.out.get(), self.action.currentData()
        if not self.need(src, out):
            return
        if Path(src).resolve() == Path(out).resolve():
            return self.win.warn(tr("Choose another file"), tr("Save to a different file than the original."))
        angle, spec = self.angle.currentData(), self.pages.text().strip()

        def job(log, prog):
            n = core.edit_pages(src, out, action, spec, angle)
            log(trf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return _stem_dir(out)
        self.win.run(job)


class OcrTool(Tool):
    key, icon, title = "ocr", "ocr", "OCR"
    subtitle = ("Turn scanned books and documents into PDFs whose text can be searched and copied. "
                "Persian (Farsi) and Arabic are fully supported.")

    def build(self):
        f = Form()
        self.src = FileRow(on_pick=lambda p: None if self.out.get() else
                           self.out.edit.setText(str(Path(p).with_name(Path(p).stem + "_ocr.pdf"))))
        self.out = FileRow("save")
        f.row("PDF file", self.src)
        f.row("Save as", self.out)
        self.langs = lang_choices()
        self.lang = mkcombo(self.langs or {"English  (eng)": "eng"})
        f.row("Language", self.lang)
        self.eng = mkcheck("Also recognise English words (recommended for mixed text)", True)
        f.row("", self.eng, span=True)
        self.dpi = mkcombo({tr("200 dpi (fast)"): 200, tr("300 dpi (recommended)"): 300, tr("400 dpi (small print)"): 400}, 300)
        f.row("Scan quality", self.dpi)
        self.skip = mkcheck("Skip pages that already contain text", True)
        f.row("", self.skip, span=True)
        self.body.addLayout(f)
        self.note("The original page images stay untouched — only an invisible text layer is added, "
                  "so the file keeps its quality." if self.langs else "OCR engine is missing from this build.")
        self.body.addStretch(1)
        self.run_button("Run OCR", self.run)

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        lang = tess_lang(self.lang.currentData(), self.eng.isChecked())
        dpi, skip = self.dpi.currentData(), self.skip.isChecked()

        def job(log, prog):
            n, total = core.ocr_pdf(src, out, lang, dpi, skip, 3, prog)
            log(trf("✔ OCR finished: {n} of {total} pages → {name}", n=n, total=total, name=Path(out).name))
            return _stem_dir(out)
        self.win.run(job)
