"""PDF preview: pages on a grey desk with a border, zoom around the pointer, drag to pan, night mode."""
from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QTimer
from . import strings

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


class _Page(QtWidgets.QLabel):
    def __init__(self, w, h):
        super(_Page, self).__init__()
        self.setFixedSize(w, h)
        self.rendered_key = None
        self.setStyleSheet("background: white; border: 1px solid rgba(0,0,0,0.25);")


class PdfView(QtWidgets.QWidget):
    page_changed = Signal(int, int)

    def __init__(self, theme, parent=None):
        super(PdfView, self).__init__(parent)
        self.theme = theme
        self.doc = None
        self.path = None
        self.zoom = 1.0           # 1.0 = pages as wide as the view
        self.night = False
        self.pages = []
        self._cache = {}
        self._drag = None
        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.holder = QtWidgets.QWidget()
        self.col = QtWidgets.QVBoxLayout(self.holder)
        self.col.setContentsMargins(10, 10, 10, 10)
        self.col.setSpacing(10)
        self.col.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.scroll.setWidget(self.holder)
        self.scroll.viewport().installEventFilter(self)
        self.scroll.verticalScrollBar().valueChanged.connect(self._schedule_render)
        self.empty = QtWidgets.QLabel(strings.t("nopdf"), self)
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setObjectName("muted")
        # floating controls
        self.bar = QtWidgets.QFrame(self)
        self.bar.setObjectName("card")
        lay = QtWidgets.QHBoxLayout(self.bar)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        self.percent = QtWidgets.QToolButton()
        self.percent.setToolTip("100%")
        self.percent.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(self.percent)
        for p in (100, 150, 200, 300, 400):
            menu.addAction("%d%%" % p, lambda p=p: self.set_zoom(p / 100.0))
        self.percent.setMenu(menu)
        lay.addWidget(self.percent)
        for text, tip, fn in (("\u2212", "Zoom out", lambda: self.set_zoom(self.zoom / 1.25)),
                              ("+", "Zoom in", lambda: self.set_zoom(self.zoom * 1.25)),
                              ("\u25a1", "Fit", lambda: self.set_zoom(1.0))):
            b = QtWidgets.QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            lay.addWidget(b)
        self.night_btn = QtWidgets.QToolButton()
        self.night_btn.setText("\u263e")
        self.night_btn.setCheckable(True)
        self.night_btn.toggled.connect(self.set_night)
        lay.addWidget(self.night_btn)
        self.indicator = QtWidgets.QLabel("", self)
        self.indicator.setObjectName("card")
        self.indicator.setContentsMargins(12, 4, 12, 4)
        self.bar.hide()
        self.indicator.hide()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_visible)
        self.apply_theme(theme)
        self._update_percent()

    def apply_theme(self, theme):
        self.theme = theme
        desk = "#111317" if self.night else (theme.pal.hover if not theme.dark else "#2A2E35")
        self.scroll.setStyleSheet("QScrollArea { background: %s; } QWidget#holder { background: %s; }" % (desk, desk))
        self.holder.setObjectName("holder")
        self.holder.setStyleSheet("QWidget#holder { background: %s; }" % desk)

    # ------------------------------------------------------------ loading
    def load(self, path):
        self.close_doc()
        if fitz is None or not path:
            self._update_visibility()
            return
        try:
            self.doc = fitz.open(path)
        except Exception:
            self.doc = None
        self.path = path
        self._cache.clear()
        self._build_pages()
        self._update_visibility()

    def close_doc(self):
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                pass
        self.doc = None
        self._clear_pages()

    def _clear_pages(self):
        for p in self.pages:
            self.col.removeWidget(p)
            p.deleteLater()
        self.pages = []

    def _scale(self):
        w = max(200, self.scroll.viewport().width() - 40)
        return w * self.zoom

    def _build_pages(self):
        self._clear_pages()
        if self.doc is None:
            return
        width = self._scale()
        for i in range(self.doc.page_count):
            r = self.doc[i].rect
            h = int(width * r.height / r.width)
            pg = _Page(int(width), h)
            self.pages.append(pg)
            self.col.addWidget(pg, 0, Qt.AlignHCenter)
        self.holder.adjustSize()
        self._schedule_render()

    def _update_visibility(self):
        has = self.doc is not None and self.doc.page_count > 0
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        self.bar.setVisible(has)
        self.indicator.setVisible(has)
        self._layout_overlays()

    # ------------------------------------------------------------ zoom and night
    def set_zoom(self, z, anchor=None):
        z = max(1.0, min(5.0, z))
        if abs(z - self.zoom) < 1e-3 or self.doc is None:
            return
        sb = self.scroll.verticalScrollBar()
        hb = self.scroll.horizontalScrollBar()
        # keep the spot under the pointer (or the view's centre) where it is
        vp = self.scroll.viewport()
        ax, ay = (anchor.x(), anchor.y()) if anchor is not None else (vp.width() / 2.0, vp.height() / 2.0)
        fy = (sb.value() + ay) / max(1, self.holder.height())
        fx = (hb.value() + ax) / max(1, self.holder.width())
        self.zoom = z
        self._build_pages()
        self.holder.adjustSize()
        sb.setValue(int(fy * self.holder.height() - ay))
        hb.setValue(int(fx * self.holder.width() - ax))
        self._update_percent()

    def _update_percent(self):
        self.percent.setText("%d%%" % round(self.zoom * 100))

    def set_night(self, on):
        self.night = on
        self._cache.clear()
        for p in self.pages:
            p.rendered_key = None
        self.apply_theme(self.theme)
        self._schedule_render()

    # ------------------------------------------------------------ drawing the pages
    def _schedule_render(self, *_):
        self._render_timer.start(30)

    def _render_visible(self):
        if self.doc is None:
            return
        sb = self.scroll.verticalScrollBar()
        top, bottom = sb.value(), sb.value() + self.scroll.viewport().height()
        first_visible = None
        dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
        for i, pg in enumerate(self.pages):
            y = pg.y()
            if y + pg.height() < top - 400 or y > bottom + 400:
                continue
            if first_visible is None and y + pg.height() > top:
                first_visible = i
            key = (pg.width(), self.night)
            if pg.rendered_key == key:
                continue
            pg.setPixmap(self._pixmap(i, pg.width(), dpr))
            pg.rendered_key = key
        if first_visible is not None:
            self.indicator.setText("%d / %d" % (first_visible + 1, len(self.pages)))
            self.indicator.adjustSize()
            self._layout_overlays()
            self.page_changed.emit(first_visible + 1, len(self.pages))

    def _pixmap(self, index, width, dpr):
        key = (index, width, self.night)
        if key in self._cache:
            return self._cache[key]
        page = self.doc[index]
        s = width * dpr / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        img = QtGui.QImage(pix.samples, pix.width, pix.height, pix.stride, QtGui.QImage.Format_RGB888).copy()
        if self.night:
            img.invertPixels()
        pm = QtGui.QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)
        if len(self._cache) > 40:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = pm
        return pm

    def go_to_page(self, n):
        if 1 <= n <= len(self.pages):
            self.scroll.verticalScrollBar().setValue(self.pages[n - 1].y() - 6)

    # ------------------------------------------------------------ events
    def resizeEvent(self, e):
        super(PdfView, self).resizeEvent(e)
        self.scroll.setGeometry(self.rect())
        self.empty.setGeometry(self.rect())
        self._layout_overlays()
        if self.doc is not None and self.pages and abs(self.pages[0].width() - int(self._scale())) > 8:
            self._build_pages()

    def _layout_overlays(self):
        self.bar.adjustSize()
        self.bar.move(self.width() - self.bar.width() - 18, 10)
        self.indicator.adjustSize()
        self.indicator.move((self.width() - self.indicator.width()) // 2, self.height() - self.indicator.height() - 12)
        self.bar.raise_()
        self.indicator.raise_()

    def eventFilter(self, obj, ev):
        if obj is self.scroll.viewport():
            t = ev.type()
            if t == QtCore.QEvent.Wheel and ev.modifiers() & Qt.ControlModifier:
                d = ev.angleDelta().y()
                pos = ev.pos() if hasattr(ev, "pos") else None
                self.set_zoom(self.zoom * (1.15 if d > 0 else 1 / 1.15), pos)
                return True
            if t == QtCore.QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                self._drag = ev.pos()
                return False
            if t == QtCore.QEvent.MouseMove and self._drag is not None:
                d = ev.pos() - self._drag
                self._drag = ev.pos()
                self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().value() - d.y())
                self.scroll.horizontalScrollBar().setValue(self.scroll.horizontalScrollBar().value() - d.x())
                return True
            if t == QtCore.QEvent.MouseButtonRelease:
                self._drag = None
            if t == QtCore.QEvent.MouseButtonDblClick:
                self.set_zoom(1.0 if self.zoom > 1.2 else 2.5, ev.pos())
                return True
        return super(PdfView, self).eventFilter(obj, ev)
