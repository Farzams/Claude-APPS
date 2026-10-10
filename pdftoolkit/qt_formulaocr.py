"""Formula from a picture: photo, screenshot, clipboard or a region of a PDF page -> LaTeX (offline, models bundled)."""
from __future__ import annotations

import io
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QScrollArea, QSizePolicy, QStackedWidget,
                               QVBoxLayout, QWidget)

import core
import qt_style
import theme
from i18n import tr, trf
from qt_common import FileRow, Form, Tool, mkbutton, mkcombo, mklabel
from qt_pdfedit import PagePicker

_MODEL = None


def model_dir() -> Path:
    import os
    return Path(os.environ.get("PDFTK_FORMULA_MODELS") or core._app_dir() / "formula_models")


def get_model():
    global _MODEL
    if _MODEL is None:
        import formula_ocr
        _MODEL = formula_ocr.FormulaOCR(model_dir())
    return _MODEL


class _Sig(QObject):
    done = Signal(str, str)


class _Job(QRunnable):
    def __init__(self, image_bytes: bytes):
        super().__init__()
        self.data, self.s = image_bytes, _Sig()

    def run(self):
        try:
            self.s.done.emit(get_model().recognize(self.data), "")
        except Exception as e:
            self.s.done.emit("", str(e) or e.__class__.__name__)


def _png(qimg: QImage) -> bytes:
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    qimg.save(buf, "PNG")
    return bytes(buf.data())


class FormulaOcrTool(Tool):
    key, icon, title = "formulaocr", "formulaocr", "Formula from picture"
    subtitle = "Turn a picture of a formula — photo, screenshot or part of a PDF page — into LaTeX. Always check the result."
    SOURCES = {"A picture file": "file", "The clipboard (screenshot)": "clip", "A region of a PDF page": "pdf"}

    def build(self):
        # not installed: explain
        self.need_box = QWidget()
        nb = QVBoxLayout(self.need_box)
        nb.addStretch(1)
        t = mklabel("The formula model files were not found. Reinstall the app to get them back.", "h", wrap=True)
        t.setAlignment(Qt.AlignCenter)
        nb.addWidget(t)
        nb.addStretch(2)
        self.main = QWidget()
        cols = QHBoxLayout(self.main)
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(18)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(mklabel("Source", "muted"))
        self.src = mkcombo({tr(k): v for k, v in self.SOURCES.items()})
        self.src.currentIndexChanged.connect(self._src)
        left.addWidget(self.src)
        self.stack = QStackedWidget()
        # file
        fw = QWidget()
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(0, 0, 0, 0)
        self.file = FileRow("open", "Pictures (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)", self._file_picked)
        fl.addWidget(self.file)
        self.prev = QLabel()
        self.prev.setAlignment(Qt.AlignCenter)
        self.prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.prev.setMinimumHeight(120)
        fl.addWidget(self.prev, 1)
        # clipboard
        cw = QWidget()
        cl = QVBoxLayout(cw)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(mklabel("Copy a formula as a picture (for example with Win+Shift+S), then press the button.", "muted", wrap=True))
        cl.addWidget(mkbutton("Take the picture from the clipboard", self._clip))
        self.clip_prev = QLabel()
        self.clip_prev.setAlignment(Qt.AlignCenter)
        self.clip_prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        cl.addWidget(self.clip_prev, 1)
        # pdf
        pw = QWidget()
        pl = QVBoxLayout(pw)
        pl.setContentsMargins(0, 0, 0, 0)
        self.pdf = FileRow(on_pick=self._pdf_picked)
        pl.addWidget(self.pdf)
        self.picker = PagePicker(single=True)
        self.picker.set_hint("Draw a box around one formula.")
        pl.addWidget(self.picker, 1)
        for w in (fw, cw, pw):
            self.stack.addWidget(w)
        left.addWidget(self.stack, 1)
        self.go = mkbutton("Recognise the formula", self.run, "primary")
        self.go.setMinimumHeight(42)
        left.addWidget(self.go)
        right.addWidget(mklabel("LaTeX (you can edit it)", "muted"))
        self.out = QPlainTextEdit()
        self.out.setLayoutDirection(Qt.LeftToRight)
        self.out.setFont(qt_style.mono_font(11))
        self.out.setMinimumHeight(110)
        self.out.setMaximumHeight(180)
        right.addWidget(self.out)
        right.addWidget(mklabel("Preview", "muted"))
        self.render = QLabel()
        self.render.setAlignment(Qt.AlignCenter)
        self.render.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.render.setMinimumHeight(110)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.render)
        sc.setLayoutDirection(Qt.LeftToRight)
        right.addWidget(sc, 1)
        self.state = mklabel("", "muted", wrap=True, translate=False)
        right.addWidget(self.state)
        acts = QHBoxLayout()
        acts.addWidget(mkbutton("Preview", self.preview))
        acts.addWidget(mkbutton("Copy LaTeX", self.copy))
        acts.addWidget(mkbutton("Insert into the LaTeX page", self.insert))
        right.addLayout(acts)
        cols.addLayout(left, 5)
        cols.addLayout(right, 5)
        self.body.addWidget(self.need_box)
        self.body.addWidget(self.main, 1)
        self._qimage: QImage | None = None
        self._busy = False
        self._pm = None
        self.models_changed()

    def models_changed(self):
        import formula_ocr
        ok = formula_ocr.available(model_dir())
        self.need_box.setVisible(not ok)
        self.main.setVisible(ok)

    def on_show(self):
        self.models_changed()

    def _src(self):
        self.stack.setCurrentIndex(["file", "clip", "pdf"].index(self.src.currentData()))

    def _scaled(self, label: QLabel, img: QImage):
        pm = QPixmap.fromImage(img)
        w = max(label.width() - 8, 160)
        label.setPixmap(pm.scaled(w, max(label.height() - 8, 100), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _file_picked(self, p: str):
        img = QImage(p)
        if not img.isNull():
            self._scaled(self.prev, img)

    def _clip(self):
        img = QGuiApplication.clipboard().image()
        if img.isNull():
            return self.win.warn(tr("Missing information"), tr("The clipboard has no picture."))
        self._qimage = img
        self._scaled(self.clip_prev, img)

    def _pdf_picked(self, p: str):
        if not self.picker.set_pdf(p):
            self.win.warn(tr("Cannot open"), tr("The PDF is password protected"))

    def _source_image(self) -> bytes | None:
        kind = self.src.currentData()
        if kind == "file":
            p = self.file.get()
            return Path(p).read_bytes() if p and Path(p).is_file() else None
        if kind == "clip":
            return _png(self._qimage) if self._qimage is not None and not self._qimage.isNull() else None
        rect = self.picker.current_rect()
        if rect is None or not self.picker.doc:
            return None
        import pymupdf
        pix = self.picker.doc[self.picker.page].get_pixmap(dpi=300, clip=pymupdf.Rect(rect), alpha=False)
        return pix.tobytes("png")

    def run(self):
        if self._busy:
            return
        data = self._source_image()
        if not data:
            return self.win.warn(tr("Missing information"), tr("Choose a picture first (or draw a box on the PDF page)."))
        self._busy = True
        self.go.setEnabled(False)
        self.state.setText(tr("Recognising…"))
        job = _Job(data)
        job.s.done.connect(self._done)
        self._keep = job
        QThreadPool.globalInstance().start(job)

    def _done(self, latex: str, err: str):
        self._busy = False
        self.go.setEnabled(True)
        if err:
            self.state.setText("✘ " + err)
            return
        self.out.setPlainText(latex)
        self.state.setText(tr("Done. Neural recognition can make mistakes (for example n and π, ≤ and ≅): compare with the picture."))
        self.preview()

    def preview(self):
        latex = self.out.toPlainText().strip()
        if not latex:
            return
        import mathcore
        png = mathcore.latex_png(latex, color=theme.STATE.pal["text"])
        if not png:
            self.render.setText(tr("The preview could not draw this formula; the LaTeX text is still copied correctly."))
            return
        pm = QPixmap()
        pm.loadFromData(png)
        w = max(self.render.width() - 12, 200)
        pm = pm.scaledToWidth(min(pm.width(), w), Qt.SmoothTransformation)
        self.render.setPixmap(pm)

    def copy(self):
        QGuiApplication.clipboard().setText(self.out.toPlainText())
        self.win.toast("LaTeX copied")

    def insert(self):
        t = self.out.toPlainText().strip()
        if t:
            self.win.insert_snippet("\\[ " + t + " \\]")
