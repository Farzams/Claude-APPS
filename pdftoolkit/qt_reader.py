"""Reader: tabs, continuous scrolling, spreads, thumbnails / outline / bookmarks / search, reading modes."""
from __future__ import annotations

import bisect
import os
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import (QObject, QPoint, QPointF, QRectF, QRunnable, QSize, Qt, QThreadPool, QTimer, QUrl, Signal)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QGuiApplication, QImage, QKeySequence, QPainter, QPen,
                           QPixmap, QShortcut)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QSplitter, QStackedWidget,
                               QTabBar, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QLineEdit)

import core
import i18n
import icons
import reader_core as rc
import theme
from i18n import tr, trf
from qt_common import Card, Tool, mkbutton, mklabel

PAPER = {"light": QColor(255, 255, 255), "sepia": QColor(244, 232, 208), "dark": QColor(26, 27, 31)}
DESK = {"light": QColor(206, 210, 222), "sepia": QColor(205, 190, 160), "dark": QColor(14, 15, 18)}
MARGIN, GAP = 20, 14


# ---------------------------------------------------------------- page canvas
class _RenderJob(QRunnable):
    def __init__(self, canvas: "Canvas", key: tuple, book: rc.Book):
        super().__init__()
        self.canvas, self.key, self.book = canvas, key, book

    def run(self):
        page, zoom, mode = self.key
        if self.key not in self.canvas._want or self.canvas.book is not self.book:
            self.canvas._skipped.emit(self.key)
            return
        try:
            data, w, h = self.book.render(page, zoom)
            img = QImage(data, w, h, 3 * w, QImage.Format_RGB888).copy()
            if mode == "dark":
                img.invertPixels()
                p = QPainter(img)                      # lift pure black to a soft charcoal
                p.setCompositionMode(QPainter.CompositionMode_Lighten)
                p.fillRect(img.rect(), QColor(30, 31, 36))
                p.end()
            elif mode == "sepia":
                p = QPainter(img)
                p.setCompositionMode(QPainter.CompositionMode_Multiply)
                p.fillRect(img.rect(), PAPER["sepia"])
                p.end()
            self.canvas._ready.emit(self.key, img)
        except Exception:
            self.canvas._failed.emit(self.key)


class Canvas(QAbstractScrollArea):
    pageChanged = Signal(int)
    zoomChanged = Signal(float)
    selectionMade = Signal(str)
    menuRequested = Signal(QPoint)
    _ready = Signal(object, object)
    _skipped = Signal(object)
    _failed = Signal(object)

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setLayoutDirection(Qt.LeftToRight)          # page geometry never mirrors, even in Persian
        self.viewport().setMouseTracking(True)
        self.verticalScrollBar().setSingleStep(70)
        self.horizontalScrollBar().setSingleStep(50)
        self.book: rc.Book | None = None
        self.zoom, self.fit = 1.0, "width"
        self.spread, self.rtl_spread, self.tool = False, False, "select"
        self.mode = "light"
        self.query, self.hit_pages = "", set()
        self.rows: list[list[int]] = []
        self.pos: dict[int, QRectF] = {}
        self.tops: list[float] = []
        self.content = QPointF(0, 0)
        self.cache: OrderedDict[tuple, QPixmap] = OrderedDict()
        self.latest: dict[int, tuple] = {}
        self.pending: set[tuple] = set()
        self._want: set[tuple] = set()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.failed: set[tuple] = set()
        self._ready.connect(self._got)
        self._skipped.connect(self._drop_pending)
        self._failed.connect(self._mark_failed)
        self.sel: tuple[int, QRectF] | None = None
        self._press: QPoint | None = None
        self._drag_from: tuple[int, QPointF] | None = None
        self._pan: QPoint | None = None
        self._page = -1
        self.verticalScrollBar().valueChanged.connect(self._scrolled)
        self.horizontalScrollBar().valueChanged.connect(lambda _v: self.viewport().update())

    # ---- document
    def set_book(self, book: "rc.Book | None", page=0, zoom=1.0, fit="width", spread=False, rtl=False):
        self.book, self.zoom, self.fit, self.spread, self.rtl_spread = book, zoom, fit, spread, rtl
        self.cache.clear()
        self.latest.clear()
        self.pending.clear()
        self.failed.clear()
        self.sel = None
        self.hit_pages = set()
        self.relayout(anchor=None)
        if book:
            self.go(page)
        self.viewport().update()

    def _rows(self) -> list[list[int]]:
        n = self.book.page_count if self.book else 0
        if not self.spread:
            return [[i] for i in range(n)]
        rows, i = [[0]] if n else [], 1
        while i < n:
            rows.append([i, i + 1] if i + 1 < n else [i])
            i += 2
        return rows

    def relayout(self, anchor="keep"):
        if not self.book:
            self.rows, self.pos, self.tops = [], {}, []
            self.verticalScrollBar().setRange(0, 0)
            self.horizontalScrollBar().setRange(0, 0)
            return
        keep = self._anchor() if anchor == "keep" else None
        vw, vh = self.viewport().width(), self.viewport().height()
        self.rows = self._rows()
        sizes = self.book.sizes

        def row_w(row):
            return sum(sizes[i][0] for i in row) + (GAP / max(self.zoom, 0.05)) * (len(row) - 1)

        if self.fit in ("width", "page") and vw > 50:
            widest = max(row_w(r) for r in self.rows)
            z = (vw - 2 * MARGIN) / widest
            if self.fit == "page":
                tallest = max(sizes[i][1] for i in range(len(sizes)))
                z = min(z, (vh - 2 * MARGIN) / tallest)
            self.zoom = max(0.1, min(z, 6.0))
            self.zoomChanged.emit(self.zoom)
        z = self.zoom
        y = MARGIN
        self.pos, self.tops = {}, []
        maxw = 0.0
        for row in self.rows:
            order = list(reversed(row)) if self.rtl_spread else row
            w = sum(sizes[i][0] * z for i in row) + GAP * (len(row) - 1)
            h = max(sizes[i][1] * z for i in row)
            maxw = max(maxw, w)
            x0 = max((vw - w) / 2, MARGIN)
            x = x0
            for i in order:
                pw, ph = sizes[i][0] * z, sizes[i][1] * z
                self.pos[i] = QRectF(x, y + (h - ph) / 2, pw, ph)
                x += pw + GAP
            self.tops.append(y)
            y += h + GAP
        self.content = QPointF(max(maxw + 2 * MARGIN, vw), y + MARGIN - GAP)
        self.verticalScrollBar().setPageStep(vh)
        self.horizontalScrollBar().setPageStep(vw)
        self.verticalScrollBar().setRange(0, max(0, int(self.content.y() - vh)))
        self.horizontalScrollBar().setRange(0, max(0, int(self.content.x() - vw)))
        if keep:
            self._restore(keep)
        self.viewport().update()

    def _anchor(self):
        if not self.rows:
            return None
        r = self._row_at(self.verticalScrollBar().value() + 4)
        top = self.tops[r]
        h = self._row_h(r)
        return r, (self.verticalScrollBar().value() - top) / max(h, 1)

    def _restore(self, a):
        r, f = a
        r = min(r, len(self.rows) - 1)
        self.verticalScrollBar().setValue(int(self.tops[r] + f * self._row_h(r) - 0))

    def _row_h(self, r: int) -> float:
        return max(self.pos[i].height() for i in self.rows[r])

    def _row_at(self, y: float) -> int:
        r = bisect.bisect_right(self.tops, y - GAP / 2) - 1
        return max(0, min(r, len(self.rows) - 1))

    # ---- navigation
    def row_of_page(self, page: int) -> int:
        for r, row in enumerate(self.rows):
            if page in row:
                return r
        return 0

    def go(self, page: int, frac: float = 0.0):
        if not self.book or not self.rows:
            return
        page = max(0, min(page, self.book.page_count - 1))
        r = self.row_of_page(page)
        self.verticalScrollBar().setValue(int(self.tops[r] - MARGIN / 2 + frac * self._row_h(r)))
        self._scrolled()

    def current_page(self) -> int:
        if not self.rows:
            return 0
        r = self._row_at(self.verticalScrollBar().value() + self.viewport().height() * 0.30)
        return min(self.rows[r])

    def _scrolled(self, _v=None):
        self.viewport().update()
        p = self.current_page() if self.rows else 0
        if p != self._page:
            self._page = p
            self.pageChanged.emit(p)

    def set_zoom(self, z: float, fit="custom"):
        self.fit, self.zoom = fit, max(0.1, min(z, 6.0))
        self.relayout(anchor="keep")
        self.zoomChanged.emit(self.zoom)

    def set_fit(self, fit: str):
        self.fit = fit
        self.relayout(anchor="keep")

    def set_spread(self, on: bool, rtl: bool | None = None):
        self.spread = on
        if rtl is not None:
            self.rtl_spread = rtl
        self.relayout(anchor="keep")

    def set_mode(self, mode: str):
        self.mode = mode
        self.cache.clear()
        self.latest.clear()
        self.pending.clear()
        self.failed.clear()
        self.viewport().update()

    def set_query(self, q: str, pages=()):
        self.query, self.hit_pages = q, set(pages)
        self.viewport().update()

    def reload(self):
        """Pages changed (font size): rebuild everything but keep the reading position."""
        frac = self._page / max(self.book.page_count, 1) if self.book else 0
        self.cache.clear()
        self.latest.clear()
        self.pending.clear()
        self.sel = None
        self.relayout(anchor=None)
        if self.book:
            self.go(int(frac * self.book.page_count))

    # ---- painting
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayout(anchor="keep")

    def _drop_pending(self, key):
        self.pending.discard(key)
        if key in self._want:                    # still needed (e.g. skipped during a quick zoom): ask again
            self.viewport().update()

    def _mark_failed(self, key):
        self.pending.discard(key)
        self.failed.add(key)

    def _got(self, key, img: QImage):
        self.pending.discard(key)
        page, zoom, mode = key
        if mode != self.mode or self.book is None:
            return
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(self.devicePixelRatioF())
        self.cache[key] = pm
        self.cache.move_to_end(key)
        self.latest[page] = key
        while len(self.cache) > 40:
            old, _ = self.cache.popitem(last=False)
            if self.latest.get(old[0]) == old:
                self.latest.pop(old[0], None)
        self.viewport().update()

    def paintEvent(self, _e):
        p = QPainter(self.viewport())
        p.fillRect(self.viewport().rect(), DESK[self.mode])
        if not self.book or not self.rows:
            return
        vx, vy = self.horizontalScrollBar().value(), self.verticalScrollBar().value()
        vh = self.viewport().height()
        first = self._row_at(vy)
        last = self._row_at(vy + vh)
        dpr = self.devicePixelRatioF()
        want: set[tuple] = set()
        order: list[int] = []
        for r in range(max(first - 1, 0), min(last + 2, len(self.rows))):
            for i in self.rows[r]:
                order.append(i)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        for i in order:
            rect = self.pos[i].translated(-vx, -vy)
            key = (i, round(self.zoom * dpr, 3), self.mode)
            visible = rect.bottom() > 0 and rect.top() < vh
            want.add(key)
            if not visible:
                if key not in self.cache and key not in self.pending and key not in self.failed:
                    self._request(key)
                continue
            p.fillRect(rect.translated(3, 4), QColor(0, 0, 0, 55))          # soft shadow
            pm = self.cache.get(key)
            if pm is not None:
                self.cache.move_to_end(key)
                p.drawPixmap(rect.toRect(), pm)
            else:
                old = self.cache.get(self.latest.get(i)) if i in self.latest else None
                p.fillRect(rect, PAPER[self.mode])
                if old is not None:
                    p.drawPixmap(rect.toRect(), old)
                if key not in self.pending and key not in self.failed:
                    self._request(key)
            if self.query and (i in self.hit_pages):
                self._draw_hits(p, i, rect)
            if self.sel and self.sel[0] == i:
                s = self._pdf_to_view(i, self.sel[1], rect)
                p.fillRect(s, QColor(70, 120, 255, 70))
                p.setPen(QPen(QColor(70, 120, 255, 200), 1))
                p.drawRect(s)
        self._want = want
        p.end()

    def _request(self, key):
        self.pending.add(key)
        self._want.add(key)
        self.pool.start(_RenderJob(self, key, self.book))

    def _pdf_to_view(self, i: int, r: QRectF, rect: QRectF) -> QRectF:
        sx = rect.width() / self.book.sizes[i][0]
        sy = rect.height() / self.book.sizes[i][1]
        return QRectF(rect.x() + r.x() * sx, rect.y() + r.y() * sy, r.width() * sx, r.height() * sy)

    def _draw_hits(self, p: QPainter, i: int, rect: QRectF):
        for x0, y0, x1, y1 in self.book.find_rects(i, self.query):
            p.fillRect(self._pdf_to_view(i, QRectF(x0, y0, x1 - x0, y1 - y0), rect), QColor(255, 200, 0, 110))

    # ---- mouse and keys
    def page_at(self, pos: QPoint):
        vx, vy = self.horizontalScrollBar().value(), self.verticalScrollBar().value()
        for i, r in self.pos.items():
            rr = r.translated(-vx, -vy)
            if rr.contains(QPointF(pos)):
                return i, rr
        return None

    def _to_pdf(self, i: int, rect: QRectF, pos) -> QPointF:
        return QPointF((pos.x() - rect.x()) * self.book.sizes[i][0] / rect.width(),
                       (pos.y() - rect.y()) * self.book.sizes[i][1] / rect.height())

    def _link_at(self, pos: QPoint):
        hit = self.page_at(pos)
        if not hit or not self.book:
            return None
        i, rect = hit
        pt = self._to_pdf(i, rect, pos)
        for ln in self.book.links(i):
            r = ln.get("from")
            if r is not None and r.x0 <= pt.x() <= r.x1 and r.y0 <= pt.y() <= r.y1:
                return ln
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.menuRequested.emit(e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton or not self.book:
            return
        self._press = e.position().toPoint()
        if self.tool == "hand":
            self._pan = e.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            return
        hit = self.page_at(self._press)
        self._drag_from = None
        if hit:
            i, rect = hit
            self._drag_from = (i, self._to_pdf(i, rect, self._press))
        self.sel = None
        self.viewport().update()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._pan is not None:
            d = pos - self._pan
            self._pan = pos
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            return
        if self._drag_from and (e.buttons() & Qt.LeftButton) and self._press and \
                (pos - self._press).manhattanLength() > 5:
            i, start = self._drag_from
            r = self.pos[i].translated(-self.horizontalScrollBar().value(), -self.verticalScrollBar().value())
            cur = self._to_pdf(i, r, pos)
            w, h = self.book.sizes[i]
            cur = QPointF(max(0, min(cur.x(), w)), max(0, min(cur.y(), h)))
            self.sel = (i, QRectF(start, cur).normalized())
            self.viewport().update()
            return
        if self._link_at(pos):
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.OpenHandCursor if self.tool == "hand" else Qt.IBeamCursor)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        pos = e.position().toPoint()
        if self._pan is not None:
            self._pan = None
            self.setCursor(Qt.OpenHandCursor)
        if self._press is not None and (pos - self._press).manhattanLength() <= 5:
            ln = self._link_at(pos)
            if ln:
                self._follow(ln)
        elif self.sel and self.book:
            txt = self.book.text_in(self.sel[0], (self.sel[1].x(), self.sel[1].y(),
                                                  self.sel[1].right(), self.sel[1].bottom()))
            if txt:
                self.selectionMade.emit(txt)
        self._press = None
        self._drag_from = None

    def _follow(self, ln: dict):
        if ln.get("kind") == 2 and ln.get("uri"):          # LINK_URI
            QDesktopServices.openUrl(QUrl(ln["uri"]))
        elif ln.get("kind") in (1, 5) and ln.get("page", -1) >= 0:   # LINK_GOTO / LINK_NAMED
            to = ln.get("to")
            frac = 0.0
            if to is not None and self.book:
                frac = max(0.0, min(float(to.y) / self.book.sizes[ln["page"]][1], 1.0))
            self.go(ln["page"], frac)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            steps = e.angleDelta().y() / 120
            self.set_zoom(self.zoom * (1.12 ** steps))
            e.accept()
            return
        super().wheelEvent(e)

    def keyPressEvent(self, e):
        k, sb = e.key(), self.verticalScrollBar()
        mod = e.modifiers()
        if k in (Qt.Key_PageDown, Qt.Key_Space) and not (mod & Qt.ShiftModifier):
            sb.setValue(sb.value() + int(self.viewport().height() * 0.9))
        elif k in (Qt.Key_PageUp,) or (k == Qt.Key_Space and mod & Qt.ShiftModifier):
            sb.setValue(sb.value() - int(self.viewport().height() * 0.9))
        elif k == Qt.Key_Home:
            self.go(0)
        elif k == Qt.Key_End and self.book:
            self.go(self.book.page_count - 1)
        elif k == Qt.Key_Down:
            sb.setValue(sb.value() + 90)
        elif k == Qt.Key_Up:
            sb.setValue(sb.value() - 90)
        elif k == Qt.Key_Right:
            if self.horizontalScrollBar().maximum() > 0:
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + 90)
            else:
                self.go(self.current_page() + (1 if not self.spread else 2))
        elif k == Qt.Key_Left:
            if self.horizontalScrollBar().maximum() > 0:
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - 90)
            else:
                self.go(self.current_page() - (1 if not self.spread else 2))
        else:
            super().keyPressEvent(e)


# ---------------------------------------------------------------- opening in the background
class _OpenSignals(QObject):
    done = Signal(object, str, bool)      # book, error, needs_password
    say = Signal(str)


class _OpenJob(QRunnable):
    def __init__(self, path: str, password: str):
        super().__init__()
        self.path, self.password = path, password
        self.s = _OpenSignals()

    def run(self):
        try:
            b = rc.open_book(self.path, self.password, self.s.say.emit)
            self.s.done.emit(b, "", False)
        except rc.PasswordNeeded:
            self.s.done.emit(None, "", True)
        except Exception as e:
            self.s.done.emit(None, str(e) or e.__class__.__name__, False)


class _SearchSignals(QObject):
    hit = Signal(int, str, int)           # page, snippet, generation
    done = Signal(int)


class _SearchJob(QRunnable):
    def __init__(self, book: rc.Book, q: str, gen: int, alive):
        super().__init__()
        self.book, self.q, self.gen, self.alive = book, q, gen, alive
        self.s = _SearchSignals()

    def run(self):
        self.book.search(self.q, cancel=lambda: not self.alive(self.gen),
                         on_hit=lambda p, s: self.s.hit.emit(p, s, self.gen))
        self.s.done.emit(self.gen)


class _Doc:
    """One open tab."""

    def __init__(self, book: rc.Book):
        self.book = book
        self.page, self.zoom, self.fit = 0, 1.0, "width"
        self.spread, self.rtl = False, False
        self.hits: list[tuple[int, str]] = []
        self.query = ""
        self.bookmarks: list[dict] = []


# ---------------------------------------------------------------- the tool
class ReaderTool(Tool):
    key, icon, title = "read", "read", "Read"
    subtitle = ""

    def __init__(self, win):                       # custom layout: no hero, the whole page is the reader
        QWidget.__init__(self)
        self.win = win
        self.state = rc.load_state()
        self.docs: list[_Doc] = []
        self.cur: _Doc | None = None
        self._search_gen = 0
        self._icon_theme = ""
        self._thumb_book = None
        self._busy = False
        self._ready = False
        self._buttons: list[tuple[QToolButton, str]] = []
        self.build()
        QApplication.instance().aboutToQuit.connect(self.save_all)

    # ---- construction
    def tbtn(self, icon_name: str, tip: str, cb=None, checkable=False) -> QToolButton:
        b = QToolButton()
        b.setProperty("tb", True)
        b.setCheckable(checkable)
        b.setToolTip(tr(tip))
        b.setCursor(Qt.PointingHandCursor)
        b.setAutoRaise(True)
        b.setIconSize(QSize(20, 20))
        self._buttons.append((b, icon_name))
        if cb:
            (b.toggled if checkable else b.clicked).connect(
                lambda *_a: self._ready and cb(*([b.isChecked()] if checkable else [])))
        return b

    def build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        # toolbar card
        bar = self.bar = Card()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 8, 12, 8)
        bl.setSpacing(4)
        self.b_side = self.tbtn("sidebar", "Sidebar", self.toggle_sidebar, True)
        self.b_side.setChecked(True)
        bl.addWidget(self.b_side)
        self.b_open = self.tbtn("open", "Open a book or document… (Ctrl+O)", self.open_dialog)
        bl.addWidget(self.b_open)
        bl.addSpacing(8)
        bl.addWidget(self.tbtn("prev", "Previous page", lambda: self.step(-1)))
        self.pg = QLineEdit("1")
        self.pg.setFixedWidth(54)
        self.pg.setAlignment(Qt.AlignCenter)
        self.pg.setLayoutDirection(Qt.LeftToRight)
        self.pg.returnPressed.connect(self.goto_typed)
        bl.addWidget(self.pg)
        self.total = mklabel("/ 0", translate=False)
        bl.addWidget(self.total)
        bl.addWidget(self.tbtn("next", "Next page", lambda: self.step(1)))
        bl.addSpacing(8)
        bl.addWidget(self.tbtn("minus", "Zoom out (Ctrl+−)", lambda: self.zoom_by(1 / 1.2)))
        self.zoom_lb = mklabel("100%", translate=False)
        self.zoom_lb.setMinimumWidth(48)
        self.zoom_lb.setAlignment(Qt.AlignCenter)
        bl.addWidget(self.zoom_lb)
        bl.addWidget(self.tbtn("plus", "Zoom in (Ctrl++)", lambda: self.zoom_by(1.2)))
        bl.addWidget(self.tbtn("fit", "Fit width", lambda: self.canvas.set_fit("width")))
        bl.addWidget(self.tbtn("page", "Fit whole page", lambda: self.canvas.set_fit("page")))
        bl.addSpacing(8)
        self.b_spread = self.tbtn("spread", "Two pages side by side", self.toggle_spread, True)
        bl.addWidget(self.b_spread)
        self.b_rtl = self.tbtn("prev", "Right-to-left book (manga, Persian)", self.toggle_rtl, True)
        bl.addWidget(self.b_rtl)
        self.b_hand = self.tbtn("text", "Select text (off = drag to scroll)", self.toggle_tool, True)
        self.b_hand.setChecked(True)
        bl.addWidget(self.b_hand)
        self.b_mode = self.tbtn("sun", "Reading colours: light / sepia / night", self.cycle_mode)
        bl.addWidget(self.b_mode)
        self.b_fa = self.tbtn("minus", "Smaller text", lambda: self.font_by(-1))
        self.b_fb = self.tbtn("plus", "Larger text", lambda: self.font_by(1))
        self.fl = mklabel("Aa", translate=False)
        for w in (self.b_fa, self.fl, self.b_fb):
            bl.addWidget(w)
        bl.addStretch(1)
        self.status = mklabel("", "muted", translate=False)
        bl.addWidget(self.status)
        bl.addWidget(self.tbtn("bookmark", "Add bookmark (Ctrl+D)", self.add_bookmark))
        bl.addWidget(self.tbtn("fullscreen", "Full screen (F11)", self.fullscreen))
        self._ro = [bl.itemAt(i).widget() for i in range(bl.count())
                    if bl.itemAt(i).widget() not in (None, self.b_open, self.status)]
        outer.addWidget(bar)

        # tabs
        self.tabs = QTabBar()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setExpanding(False)
        self.tabs.setElideMode(Qt.ElideMiddle)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setDrawBase(False)
        self.tabs.currentChanged.connect(self.switch_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabMoved.connect(self._tab_moved)
        self.tabs.hide()
        outer.addWidget(self.tabs)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        # start page
        self.start = Card()
        sl = QVBoxLayout(self.start)
        sl.setContentsMargins(40, 30, 40, 30)
        sl.setSpacing(12)
        sl.addStretch(1)
        ic = QLabel()
        ic.setPixmap(icons.tile_pixmap("read", 84))
        ic.setAlignment(Qt.AlignCenter)
        sl.addWidget(ic)
        t = mklabel("Open a book or document", "h")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:17pt;")
        sl.addWidget(t)
        s = mklabel("PDF · DjVu · EPUB · MOBI/AZW · FB2 · CBZ · XPS · DOCX · ODT · RTF · Markdown · HTML · TXT · TeX · images",
                    "muted", wrap=True, translate=False)
        s.setAlignment(Qt.AlignCenter)
        sl.addWidget(s)
        d = mklabel("Drop a file here, or press Ctrl+O. Persian, Arabic and English text can be searched and copied.",
                    "muted", wrap=True)
        d.setAlignment(Qt.AlignCenter)
        sl.addWidget(d)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(mkbutton("Open…", self.open_dialog, "primary", 160))
        row.addStretch(1)
        sl.addLayout(row)
        self.recent_title = mklabel("Recent", "h")
        self.recent_title.setAlignment(Qt.AlignCenter)
        sl.addSpacing(10)
        sl.addWidget(self.recent_title)
        self.recent = QListWidget()
        self.recent.setLayoutDirection(Qt.LeftToRight)
        self.recent.setMaximumWidth(620)
        self.recent.setMaximumHeight(240)
        self.recent.itemActivated.connect(lambda it: self.open_path(it.data(Qt.UserRole)))
        self.recent.itemClicked.connect(lambda it: self.open_path(it.data(Qt.UserRole)))
        rw = QHBoxLayout()
        rw.addStretch(1)
        rw.addWidget(self.recent, 1)
        rw.addStretch(1)
        sl.addLayout(rw)
        sl.addStretch(2)
        self.stack.addWidget(self.start)

        # reader body: sidebar | canvas
        body = QWidget()
        bh = QHBoxLayout(body)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(10)
        self.split = QSplitter(Qt.Horizontal)
        self.split.setChildrenCollapsible(False)
        self.side = Card()
        sv = QVBoxLayout(self.side)
        sv.setContentsMargins(8, 8, 8, 8)
        sv.setSpacing(6)
        seg = QHBoxLayout()
        seg.setSpacing(2)
        self.seg_btns: list[QToolButton] = []
        for k, (ico, tip) in enumerate((("thumbs", "Pages"), ("outline", "Contents"), ("bookmark", "Bookmarks"),
                                        ("search", "Search results"))):
            b = self.tbtn(ico, tip, None, True)
            b.setAutoExclusive(True)
            b.clicked.connect(lambda _=False, k=k: self.side_stack.setCurrentIndex(k))
            seg.addWidget(b)
            self.seg_btns.append(b)
        self.seg_btns[0].setChecked(True)
        seg.addStretch(1)
        sv.addLayout(seg)
        self.side_stack = QStackedWidget()
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListWidget.IconMode)
        self.thumbs.setResizeMode(QListWidget.Adjust)
        self.thumbs.setMovement(QListWidget.Static)
        self.thumbs.setIconSize(QSize(118, 160))
        self.thumbs.setGridSize(QSize(136, 196))
        self.thumbs.setWordWrap(False)
        self.thumbs.setLayoutDirection(Qt.LeftToRight)
        self.thumbs.currentRowChanged.connect(lambda r: r >= 0 and self.canvas.go(r))
        self.thumbs.verticalScrollBar().valueChanged.connect(lambda _v: self._thumb_timer.start(60))
        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.itemClicked.connect(lambda it, _c: self.canvas.go(it.data(0, Qt.UserRole)))
        self.marks = QListWidget()
        self.marks.itemClicked.connect(lambda it: self.canvas.go(it.data(Qt.UserRole)))
        self.marks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.marks.customContextMenuRequested.connect(self._mark_menu)
        self.results = QListWidget()
        self.results.itemClicked.connect(lambda it: self.canvas.go(it.data(Qt.UserRole)))
        self.search_pane = QWidget()
        spl = QVBoxLayout(self.search_pane)
        spl.setContentsMargins(0, 0, 0, 0)
        spl.setSpacing(6)
        qrow = QHBoxLayout()
        qrow.setSpacing(2)
        self.q = QLineEdit()
        self.q.setPlaceholderText(tr("Search"))
        self.q.setClearButtonEnabled(True)
        self.q.returnPressed.connect(self.start_search)
        qrow.addWidget(self.q, 1)
        qrow.addWidget(self.tbtn("up", "Previous result (Shift+F3)", lambda: self.hit_step(-1)))
        qrow.addWidget(self.tbtn("down", "Next result (F3)", lambda: self.hit_step(1)))
        spl.addLayout(qrow)
        spl.addWidget(self.results, 1)
        for w in (self.thumbs, self.outline, self.marks, self.search_pane):
            self.side_stack.addWidget(w)
        sv.addWidget(self.side_stack, 1)
        self.res_lb = mklabel("", "muted", translate=False)
        sv.addWidget(self.res_lb)
        self.split.addWidget(self.side)

        self.canvas = Canvas()
        wrap = QFrame()
        wrap.setObjectName("card")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(6, 6, 6, 6)
        wl.addWidget(self.canvas)
        self.canvas.setStyleSheet("QAbstractScrollArea { border-radius: 14px; }")
        self.canvas.pageChanged.connect(self._page_changed)
        self.canvas.zoomChanged.connect(lambda z: self.zoom_lb.setText(f"{int(z * 100)}%"))
        self.canvas.selectionMade.connect(self._selected)
        self.canvas.menuRequested.connect(self._context_menu)
        self.canvas.setCursor(Qt.IBeamCursor)
        self.split.addWidget(wrap)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([260, 900])
        bh.addWidget(self.split)
        self.stack.addWidget(body)

        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.timeout.connect(self._load_thumbs)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._remember)
        self._selected_text = ""

        for seq, cb in (("Ctrl+O", self.open_dialog), ("Ctrl+F", self.focus_search), ("Ctrl+G", lambda: self._focus_page()),
                        ("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex())), ("F3", lambda: self.hit_step(1)),
                        ("Shift+F3", lambda: self.hit_step(-1)), ("Ctrl+D", self.add_bookmark),
                        ("F11", self.fullscreen), ("Ctrl+=", lambda: self.zoom_by(1.2)), ("Ctrl++", lambda: self.zoom_by(1.2)),
                        ("Ctrl+-", lambda: self.zoom_by(1 / 1.2)), ("Ctrl+0", lambda: self.canvas.set_fit("width")),
                        ("Ctrl+C", self.copy_selection), ("Ctrl+Tab", lambda: self._cycle(1)),
                        ("Ctrl+Shift+Tab", lambda: self._cycle(-1))):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(cb)
        self.set_chrome(False)
        self.refresh_recent()
        self.refresh_icons()
        self._ready = True

    # ---- theme / icons
    def refresh_icons(self):
        col = theme.STATE.pal["text"]
        for b, name in self._buttons:
            if b is self.b_rtl:
                name = "next" if self.b_rtl.isChecked() else "prev"
            if b is self.b_mode:
                name = {"light": "sun", "sepia": "book", "dark": "moon"}[self.canvas.mode]
            if i18n.rtl() and name in ("prev", "next"):      # arrows point the other way in right-to-left layouts
                name = "next" if name == "prev" else "prev"
            b.setIcon(icons.glyph_icon(name, col))
        self._icon_theme = theme.STATE.name

    def on_show(self):
        if self._icon_theme != theme.STATE.name:
            self.refresh_icons()
        self.canvas.setFocus()

    def set_chrome(self, reading: bool):
        self.bar.setVisible(reading)
        for w in self._ro:
            w.setVisible(reading)
        self._update_reflow_ui()

    def _update_reflow_ui(self):
        r = bool(self.cur and self.cur.book.reflow)
        for w in (self.b_fa, self.b_fb, self.fl):
            w.setVisible(r)

    # ---- opening
    def refresh_recent(self):
        self.recent.clear()
        for path in self.state["recent"]:
            if not os.path.exists(path):
                continue
            e = self.state["books"].get(path, {})
            pct = f"   ·   {int((e.get('page', 0) + 1) * 100 / max(e.get('pages', 1), 1))}%" if e.get("pages") else ""
            it = QListWidgetItem(f"{e.get('title') or Path(path).stem}{pct}")
            it.setToolTip(path)
            it.setData(Qt.UserRole, path)
            self.recent.addItem(it)
        self.recent_title.setVisible(self.recent.count() > 0)
        self.recent.setVisible(self.recent.count() > 0)

    def drop(self, paths):
        for p in paths:
            self.open_path(p)

    def open_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "", "", rc.FILTER)
        for p in paths:
            self.open_path(p)

    open_pdf = lambda self, p: self.open_path(p)

    def open_path(self, path: str, password: str = ""):
        path = os.path.abspath(path)
        for i, d in enumerate(self.docs):
            if os.path.abspath(d.book.source) == path:
                self.tabs.setCurrentIndex(i)
                return
        if self._busy:
            self.win.toast("Still opening the previous file…")
            return
        self._busy = True
        self.status.setText(tr("Opening…"))
        QApplication.setOverrideCursor(Qt.BusyCursor)
        job = _OpenJob(path, password)
        job.s.say.connect(lambda m: self.status.setText(tr(m)))
        job.s.done.connect(lambda b, err, pw, path=path: self._opened(path, b, err, pw))
        self._keep_job = job
        QThreadPool.globalInstance().start(job)

    def _opened(self, path, book, err, needs_pw):
        self._busy = False
        self.status.setText("")
        QApplication.restoreOverrideCursor()
        if needs_pw:
            pw, ok = QInputDialog.getText(self, tr("Password"), tr("This file is password protected. Password:"),
                                          QLineEdit.Password)
            if ok and pw:
                self.open_path(path, pw)
            return
        if book is None:
            self.win.warn(tr("Cannot open"), err or tr("Unsupported file"))
            return
        doc = _Doc(book)
        saved = self.state["books"].get(os.path.abspath(path), {})
        doc.page = int(saved.get("page", 0))
        doc.zoom = float(saved.get("zoom", 1.0))
        doc.fit = saved.get("fit", "width")
        doc.spread = bool(saved.get("spread", False))
        doc.rtl = bool(saved.get("rtl", book.is_rtl() if book.page_count else False))
        doc.bookmarks = list(saved.get("bookmarks", []))
        if saved.get("fontsize") and book.reflow:
            book.fontsize = float(saved["fontsize"])
            book.refresh()
        if saved.get("mode") in PAPER:
            self.canvas.mode = saved["mode"]
        self.docs.append(doc)
        idx = self.tabs.addTab(book.title)
        self.tabs.setTabToolTip(idx, path)
        self.tabs.setCurrentIndex(idx)
        self.tabs.setVisible(True)
        self.stack.setCurrentIndex(1)
        self.set_chrome(True)
        self.refresh_icons()
        rc.remember(self.state, book, page=doc.page)
        self.refresh_recent()

    # ---- tabs
    def _tab_moved(self, a, b):
        self.docs[a], self.docs[b] = self.docs[b], self.docs[a]

    def _cycle(self, d):
        n = self.tabs.count()
        if n:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + d) % n)

    def switch_tab(self, i: int):
        self._store_view()
        if i < 0 or i >= len(self.docs):
            self.cur = None
            return
        d = self.cur = self.docs[i]
        self._search_gen += 1
        self.b_spread.blockSignals(True)
        self.b_spread.setChecked(d.spread)
        self.b_spread.blockSignals(False)
        self.b_rtl.blockSignals(True)
        self.b_rtl.setChecked(d.rtl)
        self.b_rtl.blockSignals(False)
        self.canvas.set_book(d.book, d.page, d.zoom, d.fit, d.spread, d.rtl)
        self.canvas.set_mode(self.canvas.mode)
        self.total.setText(f"/ {d.book.page_count}")
        self.fl.setText(f"{d.book.fontsize:g}pt")
        self.q.setText(d.query)
        self.canvas.set_query(d.query, [p for p, _s in d.hits])
        self._fill_sidebar()
        self._update_reflow_ui()
        self.refresh_icons()
        self.win.setWindowTitle(f"{d.book.title} — {tr('PDF Toolkit')}")
        self.canvas.setFocus()

    def _store_view(self):
        d = self.cur
        if d is not None and d in self.docs:
            d.page, d.zoom, d.fit = self.canvas.current_page(), self.canvas.zoom, self.canvas.fit
            d.spread, d.rtl = self.canvas.spread, self.canvas.rtl_spread

    def close_tab(self, i: int):
        if i < 0 or i >= len(self.docs):
            return
        self._store_view()
        d = self.docs.pop(i)
        self._remember(d)
        was_current = self.cur is d
        if was_current:
            self.canvas.set_book(None)
            self.cur = None
        self.tabs.blockSignals(True)
        self.tabs.removeTab(i)
        self.tabs.blockSignals(False)
        d.book.close()
        if self.docs:
            self.tabs.setCurrentIndex(min(i, len(self.docs) - 1))
            self.switch_tab(self.tabs.currentIndex())
        else:
            self.stack.setCurrentIndex(0)
            self.tabs.hide()
            self.set_chrome(False)
            self.thumbs.clear()
            self.outline.clear()
            self.marks.clear()
            self.results.clear()
            self.win.setWindowTitle(tr("PDF Toolkit"))
            self.refresh_recent()

    # ---- sidebar content
    def _fill_sidebar(self):
        d = self.cur
        if not d:
            return
        b = d.book
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        blank = QPixmap(118, 160)
        blank.fill(QColor(255, 255, 255, 40))
        from PySide6.QtGui import QIcon
        for i in range(b.page_count):
            it = QListWidgetItem(QIcon(blank), str(i + 1))
            it.setTextAlignment(Qt.AlignHCenter)
            it.setSizeHint(QSize(136, 196))
            self.thumbs.addItem(it)
        self.thumbs.blockSignals(False)
        self._thumb_done = set()
        self._thumb_timer.start(80)
        self.outline.clear()
        stack: list[tuple[int, QTreeWidgetItem]] = []
        toc = b.toc()
        for lvl, title, page in toc:
            it = QTreeWidgetItem([title])
            it.setData(0, Qt.UserRole, page)
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            (stack[-1][1].addChild(it) if stack else self.outline.addTopLevelItem(it))
            stack.append((lvl, it))
        self.outline.expandToDepth(0)
        self._fill_marks()
        self.results.clear()
        for p, s in d.hits:
            self._add_result(p, s)
        self.res_lb.setText(trf("{n} page(s) found", n=len(d.hits)) if d.hits else "")
        self.seg_btns[1].setVisible(bool(toc))

    def _load_thumbs(self):
        d = self.cur
        if not d or not self.side.isVisible() or self.side_stack.currentIndex() != 0:
            return
        n = self.thumbs.count()
        if not n:
            return
        vp = self.thumbs.viewport().rect()
        a = self.thumbs.indexAt(vp.topLeft() + QPoint(8, 8))
        z = self.thumbs.indexAt(vp.bottomRight() - QPoint(8, 8))
        lo = a.row() if a.isValid() else 0
        hi = z.row() if z.isValid() else min(n - 1, lo + 24)
        from PySide6.QtGui import QIcon
        count = 0
        for r in range(max(lo - 4, 0), min(hi + 6, n)):
            if r in self._thumb_done:
                continue
            w, h = d.book.sizes[r]
            zoom = min(118 / w, 160 / h) * self.devicePixelRatioF()
            data, pw, ph = d.book.render(r, zoom)
            img = QImage(data, pw, ph, 3 * pw, QImage.Format_RGB888).copy()
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(self.devicePixelRatioF())
            self.thumbs.item(r).setIcon(QIcon(pm))
            self._thumb_done.add(r)
            count += 1
            if count >= 6:
                self._thumb_timer.start(15)
                return

    # ---- navigation actions
    def _page_changed(self, p: int):
        self.pg.setText(str(p + 1))
        if self.cur:
            self.cur.page = p
            self.thumbs.blockSignals(True)
            self.thumbs.setCurrentRow(p)
            self.thumbs.blockSignals(False)
        self._save_timer.start(900)
        self._thumb_timer.start(120)

    def step(self, d: int):
        if self.cur:
            self.canvas.go(self.canvas.current_page() + d * (2 if self.canvas.spread else 1))

    def goto_typed(self):
        try:
            self.canvas.go(int(self.pg.text()) - 1)
            self.canvas.setFocus()
        except ValueError:
            pass

    def _focus_page(self):
        self.pg.setFocus()
        self.pg.selectAll()

    def zoom_by(self, f: float):
        if self.cur:
            self.canvas.set_zoom(self.canvas.zoom * f)

    def toggle_sidebar(self, on: bool):
        self.side.setVisible(on)
        if on:
            self._thumb_timer.start(60)

    def toggle_spread(self, on: bool):
        self.canvas.set_spread(on)

    def toggle_rtl(self, on: bool):
        self.canvas.set_spread(self.canvas.spread, on)
        self.refresh_icons()

    def toggle_tool(self, select: bool):
        self.canvas.tool = "select" if select else "hand"
        self.canvas.setCursor(Qt.IBeamCursor if select else Qt.OpenHandCursor)

    def cycle_mode(self):
        nxt = {"light": "sepia", "sepia": "dark", "dark": "light"}[self.canvas.mode]
        self.canvas.set_mode(nxt)
        self.refresh_icons()
        self._save_timer.start(300)

    def font_by(self, d: int):
        if not (self.cur and self.cur.book.reflow):
            return
        QApplication.setOverrideCursor(Qt.BusyCursor)
        try:
            self.cur.book.set_fontsize(self.cur.book.fontsize + d)
        finally:
            QApplication.restoreOverrideCursor()
        self.total.setText(f"/ {self.cur.book.page_count}")
        self.fl.setText(f"{self.cur.book.fontsize:g}pt")
        self.canvas.reload()
        self._fill_sidebar()
        self._save_timer.start(300)

    def fullscreen(self):
        w = self.win
        w.showNormal() if w.isFullScreen() else w.showFullScreen()

    # ---- search
    def focus_search(self):
        if self.docs:
            self.side.setVisible(True)
            self.b_side.setChecked(True)
            self.seg_btns[3].setChecked(True)
            self.side_stack.setCurrentIndex(3)
        self.q.setFocus()
        self.q.selectAll()

    def start_search(self):
        d = self.cur
        q = self.q.text().strip()
        if not d:
            return
        self._search_gen += 1
        d.query, d.hits = q, []
        self.results.clear()
        self.canvas.set_query(q, [])
        if not q:
            self.res_lb.setText("")
            return
        self.side.setVisible(True)
        self.b_side.setChecked(True)
        self.seg_btns[3].setChecked(True)
        self.side_stack.setCurrentIndex(3)
        self.res_lb.setText(tr("Searching…"))
        job = _SearchJob(d.book, q, self._search_gen, lambda g: g == self._search_gen)
        job.s.hit.connect(self._hit)
        job.s.done.connect(self._search_done)
        self._sjob = job
        QThreadPool.globalInstance().start(job)

    def _hit(self, page: int, snippet: str, gen: int):
        if gen != self._search_gen or not self.cur:
            return
        self.cur.hits.append((page, snippet))
        self._add_result(page, snippet)
        self.canvas.set_query(self.cur.query, [p for p, _s in self.cur.hits])
        if len(self.cur.hits) == 1:
            self.canvas.go(page)
        self.res_lb.setText(trf("{n} page(s) found", n=len(self.cur.hits)))

    def _add_result(self, page: int, snippet: str):
        it = QListWidgetItem(f"{page + 1}   {snippet}")
        it.setData(Qt.UserRole, page)
        self.results.addItem(it)

    def _search_done(self, gen: int):
        if gen == self._search_gen and self.cur and not self.cur.hits:
            self.res_lb.setText(tr("not found"))

    def hit_step(self, d: int):
        c = self.cur
        if not c or not c.hits:
            return
        pages = [p for p, _s in c.hits]
        here = self.canvas.current_page()
        if d > 0:
            nxt = [p for p in pages if p > here]
            target = nxt[0] if nxt else pages[0]
        else:
            prv = [p for p in pages if p < here]
            target = prv[-1] if prv else pages[-1]
        self.canvas.go(target)
        self.results.setCurrentRow(pages.index(target))

    # ---- selection / menu
    def _selected(self, text: str):
        self._selected_text = text
        QGuiApplication.clipboard().setText(text)
        self.win.toast("Text copied")

    def copy_selection(self):
        if self._selected_text:
            QGuiApplication.clipboard().setText(self._selected_text)
            self.win.toast("Text copied")

    def _context_menu(self, pos: QPoint):
        if not self.cur:
            return
        m = QMenu(self)
        m.setStyleSheet(self.win.qss)
        m.addAction(tr("Copy selected text"), self.copy_selection).setEnabled(bool(self._selected_text))
        m.addAction(tr("Copy page text"), lambda: (QGuiApplication.clipboard().setText(
            self.cur.book.page_text(self.canvas.current_page())), self.win.toast("Page text copied")))
        m.addAction(tr("Add bookmark"), self.add_bookmark)
        m.addSeparator()
        m.addAction(tr("Open the folder"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(
            str(Path(self.cur.book.source).parent))))
        m.exec(pos)

    # ---- bookmarks
    def add_bookmark(self):
        d = self.cur
        if not d:
            return
        p = self.canvas.current_page()
        if any(b["page"] == p for b in d.bookmarks):
            return
        txt = d.book.page_text(p).strip().splitlines()
        d.bookmarks.append({"page": p, "label": (txt[0][:50] if txt else "")})
        d.bookmarks.sort(key=lambda b: b["page"])
        self._fill_marks()
        self.seg_btns[2].setChecked(True)
        self.side_stack.setCurrentIndex(2)
        self._save_timer.start(300)
        self.win.toast("Bookmark added")

    def _fill_marks(self):
        self.marks.clear()
        for b in (self.cur.bookmarks if self.cur else []):
            it = QListWidgetItem(f"{b['page'] + 1}   {b['label']}")
            it.setData(Qt.UserRole, b["page"])
            self.marks.addItem(it)

    def _mark_menu(self, pos):
        it = self.marks.itemAt(pos)
        if not it or not self.cur:
            return
        m = QMenu(self)
        m.setStyleSheet(self.win.qss)
        m.addAction(tr("Remove"), lambda: (self.cur.bookmarks.__setitem__(slice(None), [
            b for b in self.cur.bookmarks if b["page"] != it.data(Qt.UserRole)]), self._fill_marks(),
            self._save_timer.start(300)))
        m.exec(self.marks.mapToGlobal(pos))

    # ---- remembering
    def _remember(self, doc: _Doc | None = None):
        d = doc or self.cur
        if not d:
            return
        if d is self.cur:
            self._store_view()
        rc.remember(self.state, d.book, page=d.page, zoom=round(d.zoom, 3), fit=d.fit, spread=d.spread, rtl=d.rtl,
                    mode=self.canvas.mode, fontsize=d.book.fontsize, bookmarks=d.bookmarks)
        rc.save_state(self.state)

    def save_all(self):
        try:
            self._store_view()
            for d in self.docs:
                self._remember(d)
        except Exception:
            pass
