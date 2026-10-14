"""Form-style tools: crop, blank pages, header/footer, watermark, background, PDF to…, security, hidden data, batch."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QDoubleSpinBox, QHBoxLayout, QLineEdit, QSlider, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

import core
import pdftools
from i18n import tr, trf
from qt_common import FileList, FileRow, Form, Tool, mkbutton, mkcheck, mkcombo, mklabel


def _suffix_path(src: str, suffix: str, ext: str = ".pdf") -> str:
    return str(Path(src).with_name(Path(src).stem + suffix + ext))


def _folder(p: str) -> str:
    return str(Path(p).parent)


COLORS = {"Black": "#000000", "Dark grey": "#444444", "Grey": "#999999", "White": "#ffffff", "Red": "#d62828",
          "Blue": "#1d4ed8", "Green": "#15803d", "Orange": "#ea580c", "Yellow": "#facc15"}


def color_combo(default="#444444"):
    return mkcombo({tr(k): v for k, v in COLORS.items()}, default)


class PdfInOut(Tool):
    """Base for the simple 'open a PDF, save a PDF' tools."""
    suffix = "_edited"

    def pdf_rows(self, f: Form):
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("save")
        f.row("PDF file", self.src)
        f.row("Save as", self.out)
        self.info = mklabel("", "muted", translate=False)
        f.row("", self.info, span=True)

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_suffix_path(p, self.suffix))
        try:
            self.info.setText(trf("{n} pages", n=core.page_count(p)))
        except Exception as e:
            self.info.setText(str(e))

    def check_paths(self) -> tuple[str, str] | None:
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return None
        if Path(src).resolve() == Path(out).resolve():
            self.win.warn(tr("Choose another file"), tr("Save to a different file than the original."))
            return None
        return src, out


# ---------------------------------------------------------------- crop
class CropTool(PdfInOut):
    key, icon, title = "crop", "crop", "Crop pages"
    subtitle = "Trim white margins automatically, or cut a fixed amount from every side."
    suffix = "_cropped"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.mode = mkcombo({tr("Trim white margins automatically"): "auto", tr("Cut a fixed margin from each side"): "fixed"})
        self.mode.currentIndexChanged.connect(self._mode)
        f.row("Method", self.mode)
        self.unit = mkcombo({"mm": "mm", "pt": "pt", "%": "percent"})
        f.row("Unit", self.unit)
        self.sp = {}
        for name in ("Left", "Top", "Right", "Bottom"):
            s = QDoubleSpinBox()
            s.setRange(0, 500)
            s.setDecimals(1)
            s.setValue(10)
            self.sp[name] = s
            f.row(name, s)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
        f.row("Pages", self.pages)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Crop", self.run)
        self._mode()

    def _mode(self):
        fixed = self.mode.currentData() == "fixed"
        self.unit.setEnabled(fixed)
        for s in self.sp.values():
            s.setEnabled(fixed)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        auto, unit = self.mode.currentData() == "auto", self.unit.currentData()
        m = tuple(self.sp[k].value() for k in ("Left", "Top", "Right", "Bottom"))
        spec = self.pages.text()

        def job(log, prog):
            n = pdftools.crop_pdf(src, out, m, spec, auto, 8, unit)
            log(trf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- blank pages
class BlankTool(PdfInOut):
    key, icon, title = "blank", "blank", "Delete blank pages"
    subtitle = "Find empty pages (also nearly-white scans) and remove them."
    suffix = "_noblank"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.level = mkcombo({tr("Strict — only perfectly empty pages"): 0.0004,
                              tr("Normal — ignores tiny specks"): 0.002,
                              tr("Lenient — scans with noise or stains"): 0.01}, 0.002)
        f.row("Sensitivity", self.level)
        self.body.addLayout(f)
        self.body.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(mkbutton("Only show which pages are blank", self.scan))
        row.addStretch(1)
        self.body.addLayout(row)
        self.run_button("Remove blank pages", self.run)

    def scan(self):
        src = self.src.get()
        if not self.need(src):
            return
        tol = self.level.currentData()

        def job(log, prog):
            b = pdftools.find_blank_pages(src, tol)
            log(trf("Blank pages: {pages}", pages=", ".join(str(i + 1) for i in b) or tr("none")))
        self.win.run(job)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        tol = self.level.currentData()

        def job(log, prog):
            b = pdftools.delete_blank_pages(src, out, tol)
            log(trf("✔ Removed {n} blank page(s): {pages}", n=len(b), pages=", ".join(str(i + 1) for i in b) or "—"))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- header / footer / Bates
class HeaderFooterTool(PdfInOut):
    key, icon, title = "headerfooter", "headerfooter", "Header, footer & Bates"
    subtitle = "Add page numbers, dates, file names or Bates numbers to every page."
    suffix = "_numbered"
    PRESETS = {"Page X of Y (centre)": ("", "{page} / {pages}", ""),
               "Page number (right)": ("", "", "{page}"),
               "File name left, page right": ("{file}", "", "{page}"),
               "Date left, page right": ("{date}", "", "{page}"),
               "Bates number (right)": ("", "", "{bates}")}

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.preset = mkcombo({tr(k): k for k in self.PRESETS})
        self.preset.currentIndexChanged.connect(self._preset)
        f.row("Preset", self.preset)
        self.where = mkcombo({tr("Bottom of the page"): "bottom", tr("Top of the page"): "top"})
        f.row("Position", self.where)
        self.left, self.center, self.right = QLineEdit(), QLineEdit(), QLineEdit()
        for e in (self.left, self.center, self.right):
            e.setLayoutDirection(Qt.LeftToRight)
        f.row("Left text", self.left)
        f.row("Centre text", self.center)
        f.row("Right text", self.right)
        f.row("", mklabel("Tokens: {page}  {pages}  {file}  {date}  {bates}", "muted", translate=False), span=True)
        self.size = QSpinBox()
        self.size.setRange(6, 40)
        self.size.setValue(10)
        f.row("Font size", self.size)
        self.color = color_combo()
        f.row("Colour", self.color)
        self.first = QSpinBox()
        self.first.setRange(0, 99999)
        self.first.setValue(1)
        f.row("First page number", self.first)
        self.bprefix = QLineEdit("DOC-")
        self.bstart = QSpinBox()
        self.bstart.setRange(0, 99999999)
        self.bstart.setValue(1)
        self.bdigits = QSpinBox()
        self.bdigits.setRange(1, 12)
        self.bdigits.setValue(6)
        brow = QHBoxLayout()
        for w in (self.bprefix, self.bstart, self.bdigits):
            brow.addWidget(w)
        f.row("Bates: prefix, start, digits", brow)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
        f.row("Pages", self.pages)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Apply", self.run)
        self._preset()

    def _preset(self):
        l, c, r = self.PRESETS[self.preset.currentData()]
        self.left.setText(l)
        self.center.setText(c)
        self.right.setText(r)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        a = dict(left=self.left.text(), center=self.center.text(), right=self.right.text(),
                 where=self.where.currentData(), size=self.size.value(), color=self.color.currentData(),
                 pages=self.pages.text(), first_number=self.first.value(),
                 bates=(self.bprefix.text(), self.bstart.value(), self.bdigits.value()))
        if not any((a["left"].strip(), a["center"].strip(), a["right"].strip())):
            return self.win.warn(tr("Missing information"), tr("Enter some text for at least one position."))

        def job(log, prog):
            n = pdftools.header_footer(src, out, **a)
            log(trf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- watermark
class WatermarkTool(PdfInOut):
    key, icon, title = "watermark", "watermark", "Watermark"
    subtitle = "Stamp text (Persian works too) or a picture across the pages."
    suffix = "_watermark"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.kind = mkcombo({tr("Text"): "text", tr("Picture"): "image"})
        self.kind.currentIndexChanged.connect(self._kind)
        f.row("Watermark", self.kind)
        self.text = QLineEdit("CONFIDENTIAL")
        f.row("Text", self.text)
        self.image = FileRow("open", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        f.row("Picture", self.image)
        self.size = QSpinBox()
        self.size.setRange(10, 300)
        self.size.setValue(72)
        f.row("Text size", self.size)
        self.color = color_combo("#999999")
        f.row("Colour", self.color)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(5, 100)
        self.opacity.setValue(30)
        self.op_lb = mklabel("30%", translate=False)
        self.opacity.valueChanged.connect(lambda v: self.op_lb.setText(f"{v}%"))
        orow = QHBoxLayout()
        orow.addWidget(self.opacity, 1)
        orow.addWidget(self.op_lb)
        f.row("Opacity", orow)
        self.angle = QSpinBox()
        self.angle.setRange(-180, 180)
        self.angle.setValue(45)
        f.row("Angle (degrees)", self.angle)
        self.layout_ = mkcombo({tr("One in the middle"): False, tr("Repeated across the page"): True})
        f.row("Layout", self.layout_)
        self.behind = mkcheck("Put it behind the page content", False)
        f.row("", self.behind, span=True)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
        f.row("Pages", self.pages)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Apply", self.run)
        self._kind()

    def _kind(self):
        t = self.kind.currentData() == "text"
        for w in (self.text, self.size, self.color):
            w.setEnabled(t)
        self.image.setEnabled(not t)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        img = self.image.get() if self.kind.currentData() == "image" else ""
        if not (self.text.text().strip() if not img else img) and not img:
            return self.win.warn(tr("Missing information"), tr("Enter watermark text or choose an image"))
        a = dict(text=self.text.text() if not img else "", image=img, size=self.size.value(),
                 color=self.color.currentData(), opacity=self.opacity.value() / 100, angle=self.angle.value(),
                 pages=self.pages.text(), tile=self.layout_.currentData(), behind=self.behind.isChecked())

        def job(log, prog):
            n = pdftools.watermark(src, out, **a)
            log(trf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- background
class BackgroundTool(PdfInOut):
    key, icon, title = "background", "background", "Page background"
    subtitle = "Give every page a colour or a picture behind its content (e.g. a soft cream for reading)."
    suffix = "_background"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.kind = mkcombo({tr("Colour"): "color", tr("Picture"): "image"})
        self.kind.currentIndexChanged.connect(self._kind)
        f.row("Background", self.kind)
        self.presets = {tr("Cream"): "#f6efdc", tr("Light grey"): "#eceff4", tr("Light blue"): "#e6f0fb",
                        tr("Light green"): "#e7f5e8", tr("Dark"): "#202124", tr("White"): "#ffffff"}
        self.color = mkcombo(self.presets)
        f.row("Colour", self.color)
        self.pick = mkbutton("Other colour…", self._pick)
        self.custom = ""
        f.row("", self.pick, span=True)
        self.image = FileRow("open", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        f.row("Picture", self.image)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
        f.row("Pages", self.pages)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Apply", self.run)
        self._kind()

    def _kind(self):
        c = self.kind.currentData() == "color"
        self.color.setEnabled(c)
        self.pick.setEnabled(c)
        self.image.setEnabled(not c)

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.custom or "#f6efdc"), self)
        if c.isValid():
            self.custom = c.name()
            self.pick.setText(trf("Colour: {c}", c=self.custom))

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        kind = self.kind.currentData()
        color = (self.custom or self.color.currentData()) if kind == "color" else ""
        image = self.image.get() if kind == "image" else ""
        pages = self.pages.text()
        if not (color or image):
            return self.win.warn(tr("Missing information"), tr("Choose a colour or a picture"))

        def job(log, prog):
            n = pdftools.background(src, out, color, image, pages)
            log(trf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- PDF to ...
class ExportTool(Tool):
    key, icon, title = "export", "export", "PDF to…"
    subtitle = "Turn a PDF into pictures, Word, Excel, HTML or plain text."
    FORMATS = {"Pictures — PNG": ("png", "img"), "Pictures — JPEG": ("jpg", "img"), "Pictures — TIFF": ("tiff", "img"),
               "Word (.docx)": ("docx", "docx"), "Excel (.xlsx) — tables": ("xlsx", "xlsx"),
               "Web page (.html)": ("html", "txt"), "Plain text (.txt)": ("txt", "txt")}

    def build(self):
        f = Form()
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("dir")
        f.row("PDF file", self.src)
        f.row("Output folder", self.out)
        self.info = mklabel("", "muted", translate=False)
        f.row("", self.info, span=True)
        self.fmt = mkcombo({tr(k): k for k in self.FORMATS})
        self.fmt.currentIndexChanged.connect(self._fmt)
        f.row("Convert to", self.fmt)
        self.dpi = mkcombo({"72": 72, "100": 100, "150": 150, "200": 200, "300": 300, "600": 600}, 150)
        f.row("Picture resolution (dpi)", self.dpi)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
        f.row("Pages", self.pages)
        self.body.addLayout(f)
        self.note_lb = self.note("")
        self.body.addStretch(1)
        self.run_button("Convert", self.run)
        self._fmt()

    NOTES = {"docx": "Text, pictures and right-to-left direction are kept; the exact page layout is simplified.",
             "xlsx": "Every table found becomes its own sheet. PDFs without tables cannot be converted.",
             "img": "One picture per page, saved in a new folder next to the other files.",
             "txt": ""}

    def _fmt(self):
        kind = self.FORMATS[self.fmt.currentData()][1]
        self.dpi.setEnabled(kind == "img")
        self.note_lb.setText(tr(self.NOTES.get(kind, "")))

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_folder(p))
        try:
            self.info.setText(trf("{n} pages", n=core.page_count(p)))
        except Exception as e:
            self.info.setText(str(e))

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        name = self.fmt.currentData()
        ext, kind = self.FORMATS[name]
        pages, dpi = self.pages.text(), self.dpi.currentData()

        def job(log, prog):
            work = src
            try:
                if kind == "img":
                    d = Path(out) / (Path(src).stem + "_pages")
                    files = pdftools.to_images(work, str(d), ext, dpi, pages, lambda i, t, n: prog(i, t))
                    log(trf("✔ Saved {n} pictures in {folder}", n=len(files), folder=str(d)))
                    return str(d)
                dst = str(core.unique_path(Path(out) / f"{Path(src).stem}.{ext}"))
                if ext == "docx":
                    pdftools.to_docx(work, dst, pages, True, lambda i, t, n: prog(i, t))
                elif ext == "xlsx":
                    n = pdftools.to_xlsx(work, dst, pages)
                    log(trf("{n} table(s) found", n=n))
                else:
                    pdftools.export_text_format(work, dst, ext, pages)
                log(trf("✔ Saved {name}", name=Path(dst).name))
                return out
            finally:
                pass
        self.win.run(job)


# ---------------------------------------------------------------- security
class SecurityTool(PdfInOut):
    key, icon, title = "security", "security", "Password & permissions"
    subtitle = "Lock a PDF with a password (AES-256), limit printing and copying, or remove a password."
    suffix = "_locked"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.action = mkcombo({tr("Protect with a password"): "protect", tr("Remove the password"): "unlock"})
        self.action.currentIndexChanged.connect(self._action)
        f.row("Action", self.action)
        self.user = QLineEdit()
        self.user.setEchoMode(QLineEdit.Password)
        self.user.setLayoutDirection(Qt.LeftToRight)
        self.owner = QLineEdit()
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setLayoutDirection(Qt.LeftToRight)
        self.cur = QLineEdit()
        self.cur.setEchoMode(QLineEdit.Password)
        self.cur.setLayoutDirection(Qt.LeftToRight)
        self.rows = {}
        f.row("Password to open the file", self.user)
        f.row("Owner password (to change permissions)", self.owner)
        f.row("Current password of this file", self.cur)
        self.perm = {k: mkcheck(lbl, True) for k, lbl in (("print", "Allow printing"), ("copy", "Allow copying text"),
                                                           ("edit", "Allow editing and page changes"),
                                                           ("annotate", "Allow comments and form filling"))}
        for c in self.perm.values():
            f.row("", c, span=True)
        self.body.addLayout(f)
        self.note("Keep the password safe: a forgotten password cannot be recovered.")
        self.body.addStretch(1)
        self.run_button("Apply", self.run)
        self._action()

    def _action(self):
        prot = self.action.currentData() == "protect"
        self.suffix = "_locked" if prot else "_unlocked"
        for w in (self.user, self.owner, *self.perm.values()):
            w.setEnabled(prot)
        self.cur.setEnabled(True)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        act, cur = self.action.currentData(), self.cur.text()

        def job(log, prog):
            if act == "protect":
                pdftools.protect(src, out, self.user.text(), self.owner.text(),
                                 {k: c.isChecked() for k, c in self.perm.items()}, cur)
                log(trf("✔ Saved {name} (AES-256)", name=Path(out).name))
            else:
                pdftools.unlock(src, out, cur)
                log(trf("✔ Saved {name} (no password)", name=Path(out).name))
            return _folder(out)
        if act == "protect" and not (self.user.text() or self.owner.text()):
            return self.win.warn(tr("Missing information"), tr("Enter a password"))
        self.win.run(job)


# ---------------------------------------------------------------- hidden data
class HiddenTool(PdfInOut):
    key, icon, title = "hidden", "hidden", "Remove hidden data"
    subtitle = "Clean author names, comments, attachments, scripts and other things you may not want to share."
    suffix = "_clean"
    LABELS = {"metadata": "Document properties (author, title, software, dates)",
              "comments": "Comments and annotations", "attachments": "Attached and embedded files",
              "javascript": "JavaScript and actions", "links": "Links", "bookmarks": "Bookmarks",
              "form_data": "Entered form data", "thumbnails": "Page thumbnails",
              "hidden_text": "Invisible text (also deletes the hidden text layer of scanned books)"}

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.checks = {}
        for k in pdftools.HIDDEN_OPTIONS:
            c = mkcheck(self.LABELS[k], k != "hidden_text")
            self.checks[k] = c
            f.row("", c, span=True)
        self.body.addLayout(f)
        self.body.addStretch(1)
        self.run_button("Clean", self.run)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        opts = {k: c.isChecked() for k, c in self.checks.items()}

        def job(log, prog):
            done = pdftools.remove_hidden(src, out, opts)
            log(trf("✔ Saved {name}. Removed: {what}", name=Path(out).name,
                    what=", ".join(tr(self.LABELS[k]) for k in done if k in self.LABELS) or "—"))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- repair
class RepairTool(PdfInOut):
    key, icon, title = "repair", "repair", "Repair & optimize"
    subtitle = "Rebuild a damaged PDF that will not open, and store it more compactly."
    suffix = "_fixed"

    def build(self):
        f = Form()
        self.pdf_rows(f)
        self.fast = mkcheck("Prepare for fast web viewing (linearize)", False)
        f.row("", self.fast, span=True)
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setLayoutDirection(Qt.LeftToRight)
        f.row("Password (if the file has one)", self.pw)
        self.body.addLayout(f)
        self.body.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(mkbutton("Only check the file for problems", self.check))
        row.addStretch(1)
        self.body.addLayout(row)
        self.run_button("Repair", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_suffix_path(p, self.suffix))
        self.info.setText("")

    def check(self):
        src = self.src.get()
        if not self.need(src):
            return

        def job(log, prog):
            problems = pdftools.check_pdf(src)
            log(tr("No problems found.") if not problems else trf("{n} problem(s):", n=len(problems)))
            for p in problems[:15]:
                log("• " + p)
        self.win.run(job)

    def run(self):
        paths = self.check_paths()
        if not paths:
            return
        src, out = paths
        fast, pw = self.fast.isChecked(), self.pw.text()

        def job(log, prog):
            old, new, problems = pdftools.repair_pdf(src, out, fast, pw)
            log(trf("✔ Saved {name}: {old} → {new}", name=Path(out).name, old=core.fmt_size(old), new=core.fmt_size(new)))
            for p in problems[:8]:
                log("• " + p)
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- batch
class BatchTool(Tool):
    key, icon, title = "batch", "batch", "Batch process"
    subtitle = "Run one operation on many files at once — a whole folder of PDFs or books."
    OPS = {"Compress": "compress", "Convert to PDF": "convert",
           "Password protect": "protect", "Remove password": "unlock", "Crop": "crop",
           "Delete blank pages": "delete_blank", "Watermark": "watermark", "Header / footer / Bates": "header_footer",
           "Page background": "background", "Remove hidden data": "remove_hidden", "PDF to pictures": "to_images",
           "Repair & optimize": "repair", "PDF to Word": "to_docx", "PDF to Excel": "to_xlsx", "PDF to HTML": "to_html", "PDF to text": "to_text"}

    def build(self):
        self.files = FileList("PDF and documents (*.*)", 5)
        self.body.addWidget(self.files, 1)
        f = Form()
        self.out = FileRow("dir")
        f.row("Output folder", self.out)
        self.op = mkcombo({tr(k): v for k, v in self.OPS.items()})
        self.op.currentIndexChanged.connect(self._op)
        f.row("Operation", self.op)
        self.body.addLayout(f)
        # option panels (one per operation that needs settings)
        self.panels = QStackedWidget()
        self.opt: dict[str, dict] = {}
        self.panel_index: dict[str, int] = {}

        def panel(name: str, builder):
            w = QWidget()
            lay = Form()
            w.setLayout(lay)
            self.opt[name] = builder(lay)
            self.panel_index[name] = self.panels.addWidget(w)

        empty = QWidget()
        self.empty_idx = self.panels.addWidget(empty)
        panel("compress", lambda l: {"level": self._row(l, "Level", mkcombo({tr("Light"): "light", tr("Medium"): "medium", tr("Strong"): "strong"}, "medium"))})
        panel("protect", lambda l: {"user": self._row(l, "Password to open the file", self._pw()),
                                    "owner": self._row(l, "Owner password", self._pw())})
        panel("unlock", lambda l: {"password": self._row(l, "Current password", self._pw())})
        panel("crop", lambda l: {"auto": self._row(l, "Method", mkcombo({tr("Trim white margins automatically"): True}))})
        panel("delete_blank", lambda l: {"tolerance": self._row(l, "Sensitivity", mkcombo({tr("Normal"): 0.002, tr("Lenient"): 0.01, tr("Strict"): 0.0004}, 0.002))})
        panel("watermark", lambda l: {"text": self._row(l, "Text", QLineEdit("CONFIDENTIAL")),
                                      "opacity": self._row(l, "Opacity", mkcombo({"20%": 0.2, "30%": 0.3, "50%": 0.5}, 0.3))})
        panel("header_footer", lambda l: {"left": self._row(l, "Left text", QLineEdit()),
                                          "center": self._row(l, "Centre text", QLineEdit("{page} / {pages}")),
                                          "right": self._row(l, "Right text", QLineEdit())})
        panel("background", lambda l: {"color": self._row(l, "Colour", mkcombo({tr("Cream"): "#f6efdc", tr("Light grey"): "#eceff4", tr("Light blue"): "#e6f0fb"}))})
        panel("to_images", lambda l: {"fmt": self._row(l, "Format", mkcombo({"PNG": "png", "JPEG": "jpg", "TIFF": "tiff"})),
                                      "dpi": self._row(l, "Resolution (dpi)", mkcombo({"100": 100, "150": 150, "200": 200, "300": 300}, 150))})
        panel("convert", lambda l: {"page_size": self._row(l, "Page size", mkcombo({"A5": "a5", "A4": "a4", "Letter": "letter"}))})
        self.body.addWidget(self.panels)
        self.body.addStretch(0)
        self.run_button("Start", self.run)
        self._op()

    def _pw(self):
        e = QLineEdit()
        e.setEchoMode(QLineEdit.Password)
        e.setLayoutDirection(Qt.LeftToRight)
        return e

    def _row(self, form: Form, label: str, w):
        form.row(label, w)
        return w

    def _op(self):
        op = self.op.currentData()
        self.panels.setCurrentIndex(self.panel_index.get(op, self.empty_idx))

    def _params(self, op: str) -> dict:
        o = self.opt.get(op, {})

        def val(w):
            return w.currentData() if hasattr(w, "currentData") else w.text()

        v = {k: val(w) for k, w in o.items()}
        if op == "compress":
            return {"level": v["level"]}
        if op == "protect":
            return {"user_pw": v["user"], "owner_pw": v["owner"]}
        if op == "crop":
            return {"auto": True}
        if op == "watermark":
            return {"text": v["text"], "opacity": v["opacity"]}
        if op == "background":
            return {"color": v["color"]}
        return v

    def run(self):
        files, out = self.files.files, self.out.get()
        if not files:
            return self.win.warn(tr("Missing information"), tr("Add files first."))
        if not self.need(out):
            return
        op = self.op.currentData()
        params = self._params(op)
        if op == "protect" and not (params.get("user_pw") or params.get("owner_pw")):
            return self.win.warn(tr("Missing information"), tr("Enter a password"))

        def job(log, prog):
            res = pdftools.batch_run(files, out, op, params, lambda i, t, n: (prog(i, t), n and log(f"… {n}")))
            ok = sum(1 for _f, good, _m in res if good)
            for f, good, msg in res:
                log(f"{'✔' if good else '✘'} {Path(f).name}" + (f" — {msg}" if not good else ""))
            log(trf("Finished: {ok} of {n} file(s) done.", ok=ok, n=len(res)))
            return out
        self.win.run(job)
