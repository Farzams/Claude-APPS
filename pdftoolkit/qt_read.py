"""Small single-page PDF view (used for the LaTeX preview)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget)

import core
import i18n
from i18n import tr, trf
from qt_common import mkbutton, mklabel


class PdfView(QWidget):
    """Scrollable page view with prev/next, zoom and fit-to-width."""

    def __init__(self, with_zoom=True):
        super().__init__()
        self.reader: core.PdfReader | None = None
        self.page, self.zoom, self.fit, self.query = 0, 1.2, True, ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.bar = QHBoxLayout()
        self.bar.setSpacing(6)
        self.prev = mkbutton("◀" if not i18n.rtl() else "▶", lambda: self.go(self.page - 1), translate=False)
        self.next = mkbutton("▶" if not i18n.rtl() else "◀", lambda: self.go(self.page + 1), translate=False)
        for b in (self.prev, self.next):
            b.setFixedWidth(44)
        self.pg = QLineEdit("1")
        self.pg.setFixedWidth(56)
        self.pg.setAlignment(Qt.AlignCenter)
        self.pg.returnPressed.connect(self._goto)
        self.total = mklabel("/ 0", translate=False)
        self.bar.addWidget(self.prev)
        self.bar.addWidget(self.pg)
        self.bar.addWidget(self.total)
        self.bar.addWidget(self.next)
        if with_zoom:
            for txt, cb in (("−", lambda: self.set_zoom(self.zoom / 1.2)), ("+", lambda: self.set_zoom(self.zoom * 1.2))):
                b = mkbutton(txt, cb, translate=False)
                b.setFixedWidth(40)
                self.bar.addWidget(b)
            self.bar.addWidget(mkbutton("Fit", self.fit_width))
        self.bar.addStretch(1)
        lay.addLayout(self.bar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.scroll.setStyleSheet("QScrollArea { background: rgba(127,127,127,40); border-radius: 12px; border: none; }")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.label)
        lay.addWidget(self.scroll, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._refit)

    # ---- document
    def open(self, path: str) -> bool:
        try:
            r = core.PdfReader(path)
        except Exception as e:
            self.error = str(e)
            return False
        if self.reader:
            self.reader.close()
        self.reader, self.page = r, 0
        self.total.setText(f"/ {r.page_count}")
        self.fit_width()
        return True

    def load_keep_page(self, path: str):
        keep = self.page
        try:
            r = core.PdfReader(path)
        except Exception:
            return
        if self.reader:
            self.reader.close()
        self.reader = r
        self.page = min(keep, r.page_count - 1)
        self.total.setText(f"/ {r.page_count}")
        self.show_page()

    def go(self, i: int):
        if self.reader and 0 <= i < self.reader.page_count:
            self.page = i
            self.show_page()
            self.scroll.verticalScrollBar().setValue(0)

    def _goto(self):
        try:
            self.go(int(self.pg.text()) - 1)
        except ValueError:
            pass

    def fit_width(self):
        if not self.reader:
            return
        w = max(self.scroll.viewport().width() - 26, 160)
        self.zoom = max(0.2, min(w / self.reader.page_size(self.page)[0], 4))
        self.fit = True
        self.show_page()

    def set_zoom(self, z: float):
        self.zoom, self.fit = max(0.2, min(z, 5)), False
        self.show_page()

    def show_page(self) -> int:
        if not self.reader:
            return 0
        dpr = self.devicePixelRatioF()
        png, hits = self.reader.render(self.page, self.zoom * dpr, self.query)
        pm = QPixmap()
        pm.loadFromData(png)
        pm.setDevicePixelRatio(dpr)
        self.label.setPixmap(pm)
        self.label.resize(pm.size() / dpr)
        self.pg.setText(str(self.page + 1))
        return hits

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.fit and self.reader:
            self._timer.start(160)

    def _refit(self):
        if self.fit and self.reader:
            self.fit_width()
