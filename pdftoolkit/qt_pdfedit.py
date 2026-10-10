"""Tools that work on the page itself: page picker widget, Organize pages, Redact, Edit PDF, Compare."""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pymupdf
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QScrollArea, QSpinBox, QStackedWidget, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

import core
import icons
import pdftools
import theme
from i18n import tr, trf
from qt_common import FileRow, Form, Tool, mkbutton, mkcheck, mkcombo, mklabel
from qt_tools import COLORS, color_combo, _folder, _suffix_path

_TMP_DIRS: list[str] = []


def scratch_dir() -> str:
    d = tempfile.mkdtemp(prefix="pdftk_work_")
    _TMP_DIRS.append(d)
    return d


@atexit.register
def _cleanup():
    for d in _TMP_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def tool_button(icon_name: str, tip: str, cb=None, checkable=False) -> QToolButton:
    b = QToolButton()
    b.setProperty("tb", True)
    b.setCheckable(checkable)
    b.setToolTip(tr(tip))
    b.setCursor(Qt.PointingHandCursor)
    b.setIconSize(QSize(20, 20))
    b.setProperty("glyph", icon_name)
    b.setIcon(icons.glyph_icon(icon_name, theme.STATE.pal["text"]))
    if cb:
        b.clicked.connect(lambda _=False: cb())
    return b


def refresh_tool_icons(root: QWidget):
    col = theme.STATE.pal["text"]
    for b in root.findChildren(QToolButton):
        g = b.property("glyph")
        if g:
            b.setIcon(icons.glyph_icon(g, col))


def stacked(label: str, widget: QWidget) -> QVBoxLayout:
    """Label above a field (for narrow side panels)."""
    lay = QVBoxLayout()
    lay.setSpacing(3)
    lay.addWidget(mklabel(label, "muted"))
    lay.addWidget(widget)
    return lay


# ---------------------------------------------------------------- page picker
class _Surface(QWidget):
    def __init__(self, owner: "PagePicker"):
        super().__init__()
        self.o = owner
        self.setMouseTracking(True)
        self._start: QPoint | None = None
        self._cur: QPoint | None = None

    def paintEvent(self, _e):
        o = self.o
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        if o.pm is not None:
            p.drawPixmap(0, 0, o.pm)
        s = o.scale
        for idx, r in enumerate(o.rects.get(o.page, [])):
            v = QRectF(r.x() * s, r.y() * s, r.width() * s, r.height() * s)
            last = o.single or idx == len(o.rects[o.page]) - 1
            col = QColor(30, 100, 255) if o.single else QColor(220, 30, 30)
            p.fillRect(v, QColor(col.red(), col.green(), col.blue(), 70))
            p.setPen(QPen(col, 2))
            p.drawRect(v)
        for key, r in o.overlays:
            v = QRectF(r.x() * s, r.y() * s, r.width() * s, r.height() * s)
            on = key == o.selected
            p.setPen(QPen(QColor(20, 150, 70), 3 if on else 1.5, Qt.SolidLine if on else Qt.DashLine))
            if on:
                p.fillRect(v, QColor(20, 150, 70, 70))
            p.drawRect(v)
        if self._start and self._cur:
            p.setPen(QPen(QColor(30, 100, 255), 1.5, Qt.DashLine))
            p.drawRect(QRectF(self._start, self._cur).normalized())
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.o.remove_at(e.position())
        elif e.button() == Qt.LeftButton:
            self._start = e.position().toPoint()
            self._cur = self._start

    def mouseMoveEvent(self, e):
        if self._start:
            self._cur = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not self._start:
            return
        a, b = self._start, e.position().toPoint()
        self._start = self._cur = None
        self.o.released(a, b)
        self.update()


class PagePicker(QWidget):
    """Shows one PDF page; the user draws rectangles (or clicks pictures). Coordinates are PDF points."""
    changed = Signal()
    pageChanged = Signal(int)
    picked = Signal(object)

    def __init__(self, single: bool = False):
        super().__init__()
        self.single = single
        self.doc: pymupdf.Document | None = None
        self.page, self.scale = 0, 1.0
        self.pm: QPixmap | None = None
        self.rects: dict[int, list[QRectF]] = {}
        self.overlays: list[tuple] = []
        self.selected = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        bar = QHBoxLayout()
        bar.setSpacing(4)
        self.prev = tool_button("prev", "Previous page", lambda: self.go(self.page - 1))
        self.next = tool_button("next", "Next page", lambda: self.go(self.page + 1))
        self.lbl = mklabel("— / —", translate=False)
        self.clear_btn = mkbutton("Clear boxes on this page", self.clear_page)
        bar.addWidget(self.prev)
        bar.addWidget(self.lbl)
        bar.addWidget(self.next)
        bar.addStretch(1)
        bar.addWidget(self.clear_btn)
        lay.addLayout(bar)
        self.scroll = QScrollArea()
        self.scroll.setLayoutDirection(Qt.LeftToRight)
        self.scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.scroll.setStyleSheet("QScrollArea { border-radius: 12px; }")
        self.surface = _Surface(self)
        self.scroll.setWidget(self.surface)
        lay.addWidget(self.scroll, 1)
        self.hint = mklabel("", "muted", wrap=True)
        lay.addWidget(self.hint)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.timeout.connect(self._render)

    def set_hint(self, text: str):
        self.hint.setText(tr(text))

    def set_pdf(self, path: str) -> bool:
        try:
            doc = pymupdf.open(path)
            if doc.needs_pass:
                doc.close()
                return False
        except Exception:
            return False
        if self.doc:
            self.doc.close()
        self.doc, self.page, self.rects, self.overlays, self.selected = doc, 0, {}, [], None
        self._render()
        self.pageChanged.emit(0)
        return True

    @property
    def page_count(self) -> int:
        return self.doc.page_count if self.doc else 0

    def go(self, i: int):
        if self.doc and 0 <= i < self.doc.page_count:
            self.page = i
            self.selected = None
            self.overlays = []
            self._render()
            self.pageChanged.emit(i)

    def set_overlays(self, items: list[tuple]):
        self.overlays = [(k, QRectF(*r)) if not isinstance(r, QRectF) else (k, r) for k, r in items]
        self.surface.update()

    def _render(self):
        if not self.doc:
            return
        pg = self.doc[self.page]
        w = max(self.scroll.viewport().width() - 4, 240)
        self.scale = min(w / pg.rect.width, 3.0)
        dpr = self.devicePixelRatioF()
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(self.scale * dpr, self.scale * dpr), alpha=False)
        img = QImage(bytes(pix.samples), pix.width, pix.height, 3 * pix.width, QImage.Format_RGB888).copy()
        self.pm = QPixmap.fromImage(img)
        self.pm.setDevicePixelRatio(dpr)
        self.surface.setFixedSize(int(pg.rect.width * self.scale), int(pg.rect.height * self.scale))
        self.lbl.setText(f"{self.page + 1} / {self.doc.page_count}")
        self.surface.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._t.start(120)

    # ---- rectangles
    def released(self, a: QPoint, b: QPoint):
        if not self.doc:
            return
        s = self.scale
        if (a - b).manhattanLength() < 6:                      # a click
            pt = QPointF(b.x() / s, b.y() / s)
            for key, r in reversed(self.overlays):
                if r.contains(pt):
                    self.selected = key
                    self.surface.update()
                    self.picked.emit(key)
                    return
            return
        r = QRectF(QPointF(a.x() / s, a.y() / s), QPointF(b.x() / s, b.y() / s)).normalized()
        size = self.doc[self.page].rect
        r = r.intersected(QRectF(0, 0, size.width, size.height))
        if r.width() < 3 or r.height() < 3:
            return
        lst = self.rects.setdefault(self.page, [])
        if self.single:
            lst.clear()
        lst.append(r)
        self.changed.emit()

    def remove_at(self, pos: QPointF):
        s = self.scale
        pt = QPointF(pos.x() / s, pos.y() / s)
        lst = self.rects.get(self.page, [])
        for r in reversed(lst):
            if r.contains(pt):
                lst.remove(r)
                self.changed.emit()
                self.surface.update()
                return

    def clear_page(self):
        self.rects.pop(self.page, None)
        self.changed.emit()
        self.surface.update()

    def clear_all(self):
        self.rects.clear()
        self.changed.emit()
        self.surface.update()

    def areas(self) -> dict[int, list[tuple]]:
        return {p: [(r.x(), r.y(), r.right(), r.bottom()) for r in lst] for p, lst in self.rects.items() if lst}

    def current_rect(self) -> tuple | None:
        lst = self.rects.get(self.page)
        if not lst:
            return None
        r = lst[-1]
        return (r.x(), r.y(), r.right(), r.bottom())


# ---------------------------------------------------------------- organize pages
class OrganizeTool(Tool):
    key, icon, title = "organize", "pages", "Organize pages"
    subtitle = "Drag pages to reorder them; rotate, delete, duplicate, extract or insert — then save."

    def build(self):
        self.hist: list[str] = []
        self.src_name = ""
        self.doc: pymupdf.Document | None = None
        self.done: set[int] = set()
        self._icon_theme = theme.STATE.name

        top = QHBoxLayout()
        top.setSpacing(4)
        top.addWidget(mkbutton("Open PDF…", self.open_dialog, "primary"))
        self.name = mklabel("No file open — or drop a PDF here", "muted")
        from PySide6.QtWidgets import QSizePolicy
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.name, 1)
        for ico, tip, cb in (("rotate", "Rotate selected pages to the right", lambda: self.rotate(90)),
                             ("prev", "Rotate selected pages to the left", lambda: self.rotate(270)),
                             ("trash", "Delete selected pages", self.delete),
                             ("copy", "Duplicate selected pages", self.duplicate),
                             ("export", "Save selected pages as a new PDF…", self.extract),
                             ("plus", "Insert pages from a PDF or picture…", self.insert),
                             ("spread", "Reverse the order", self.reverse),
                             ("history", "Undo the last change", self.undo)):
            b = tool_button(ico, tip, cb)
            if ico == "prev":
                b.setProperty("glyph", "rotate")
                b.setIcon(icons.glyph_icon("rotate", theme.STATE.pal["text"]))
                b.setLayoutDirection(Qt.RightToLeft)
            top.addWidget(b)
        top.addWidget(mkbutton("Select all", lambda: self.grid.selectAll()))
        self.body.addLayout(top)

        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.IconMode)
        self.grid.setResizeMode(QListWidget.Adjust)
        self.grid.setMovement(QListWidget.Snap)
        self.grid.setDragDropMode(QListWidget.InternalMove)
        self.grid.setSelectionMode(QListWidget.ExtendedSelection)
        self.grid.setIconSize(QSize(120, 164))
        self.grid.setGridSize(QSize(146, 206))
        self.grid.setSpacing(4)
        self.grid.setLayoutDirection(Qt.LeftToRight)
        self.grid.setWordWrap(False)
        self.grid.model().rowsMoved.connect(lambda *_a: QTimer.singleShot(0, self._moved))
        self.grid.verticalScrollBar().valueChanged.connect(lambda _v: self._tt.start(50))
        self.body.addWidget(self.grid, 1)
        self.info = mklabel("", "muted", translate=False)
        row = QHBoxLayout()
        row.addWidget(self.info, 1)
        row.addWidget(mkbutton("Save as…", self.save, "primary", 150))
        self.body.addLayout(row)
        self._tt = QTimer(self)
        self._tt.setSingleShot(True)
        self._tt.timeout.connect(self._thumbs)

    def on_show(self):
        if self._icon_theme != theme.STATE.name:
            refresh_tool_icons(self)
            self._icon_theme = theme.STATE.name

    # ---- document handling
    @property
    def cur(self) -> str | None:
        return self.hist[-1] if self.hist else None

    def drop(self, paths):
        self.load(paths[0])

    def open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "", "", "PDF (*.pdf)")
        if p:
            self.load(p)

    def load(self, path: str):
        try:
            with pymupdf.open(path) as d:
                if d.needs_pass:
                    return self.win.warn(tr("Cannot open"), tr("The PDF is password protected"))
        except Exception as e:
            return self.win.warn(tr("Cannot open"), str(e))
        w = scratch_dir()
        first = os.path.join(w, "v0.pdf")
        shutil.copyfile(path, first)
        self.hist = [first]
        self.src_name = Path(path).stem
        self.name.setText(Path(path).name)
        self._reload()

    def _reload(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        if not self.cur:
            return
        self.doc = pymupdf.open(self.cur)
        self.done = set()
        self.grid.clear()
        blank = QPixmap(120, 164)
        blank.fill(QColor(255, 255, 255, 60))
        for i in range(self.doc.page_count):
            it = QListWidgetItem(QIcon(blank), str(i + 1))
            it.setTextAlignment(Qt.AlignHCenter)
            it.setData(Qt.UserRole, i)
            it.setSizeHint(QSize(146, 206))
            self.grid.addItem(it)
        self.info.setText(trf("{n} pages", n=self.doc.page_count) + (f"  ·  {tr('changed')}" if len(self.hist) > 1 else ""))
        self._tt.start(30)

    def _thumbs(self):
        if not self.doc:
            return
        n = self.grid.count()
        vp = self.grid.viewport().rect()
        a = self.grid.indexAt(vp.topLeft() + QPoint(8, 8))
        z = self.grid.indexAt(vp.bottomRight() - QPoint(8, 8))
        lo = a.row() if a.isValid() else 0
        hi = z.row() if z.isValid() else min(n - 1, lo + 30)
        count = 0
        dpr = self.devicePixelRatioF()
        for r in range(max(lo - 3, 0), min(hi + 8, n)):
            page = self.grid.item(r).data(Qt.UserRole)
            if page in self.done:
                continue
            rect = self.doc[page].rect
            z_ = min(120 / rect.width, 164 / rect.height) * dpr
            pix = self.doc[page].get_pixmap(matrix=pymupdf.Matrix(z_, z_), alpha=False)
            img = QImage(bytes(pix.samples), pix.width, pix.height, 3 * pix.width, QImage.Format_RGB888).copy()
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self.grid.item(r).setIcon(QIcon(pm))
            self.done.add(page)
            count += 1
            if count >= 8:
                self._tt.start(10)
                return

    def _push(self, plan: list[tuple[int, int]]):
        w = os.path.dirname(self.cur)
        new = os.path.join(w, f"v{len(self.hist)}.pdf")
        pdftools.organize(self.cur, new, plan)
        self.hist.append(new)
        self._reload()

    def _selected_rows(self) -> list[int]:
        return sorted(self.grid.row(i) for i in self.grid.selectedItems())

    def _order(self) -> list[int]:
        return [self.grid.item(r).data(Qt.UserRole) for r in range(self.grid.count())]

    def _need_doc(self) -> bool:
        if not self.doc:
            self.win.warn(tr("Missing information"), tr("Open a PDF first."))
            return False
        return True

    # ---- operations
    def _moved(self):
        if not self.doc:
            return
        order = self._order()
        if order != sorted(order):
            self._push([(p, 0) for p in order])

    def rotate(self, deg: int):
        if not self._need_doc():
            return
        sel = set(self._selected_rows())
        if not sel:
            return self.win.toast("Select pages first")
        self._push([(p, deg if r in sel else 0) for r, p in enumerate(self._order())])

    def delete(self):
        if not self._need_doc():
            return
        sel = set(self._selected_rows())
        if not sel:
            return self.win.toast("Select pages first")
        plan = [(p, 0) for r, p in enumerate(self._order()) if r not in sel]
        if not plan:
            return self.win.warn(tr("Cannot do that"), tr("That would delete every page"))
        self._push(plan)

    def duplicate(self):
        if not self._need_doc():
            return
        sel = set(self._selected_rows())
        if not sel:
            return self.win.toast("Select pages first")
        plan = []
        for r, p in enumerate(self._order()):
            plan.append((p, 0))
            if r in sel:
                plan.append((p, 0))
        self._push(plan)

    def reverse(self):
        if self._need_doc():
            self._push([(p, 0) for p in reversed(self._order())])

    def undo(self):
        if len(self.hist) > 1:
            try:
                os.remove(self.hist.pop())
            except OSError:
                pass
            self._reload()

    def insert(self):
        if not self._need_doc():
            return
        p, _ = QFileDialog.getOpenFileName(self, "", "", "PDF and pictures (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)")
        if not p:
            return
        rows = self._selected_rows()
        at = (rows[-1] + 1) if rows else self.grid.count()
        new = os.path.join(os.path.dirname(self.cur), f"v{len(self.hist)}.pdf")
        try:
            pdftools.insert_pages(self.cur, new, p, at)
        except Exception as e:
            return self.win.warn(tr("Error"), str(e))
        self.hist.append(new)
        self._reload()

    def extract(self):
        if not self._need_doc():
            return
        rows = self._selected_rows()
        if not rows:
            return self.win.toast("Select pages first")
        out, _ = QFileDialog.getSaveFileName(self, "", f"{self.src_name}_extract.pdf", "PDF (*.pdf)")
        if not out:
            return
        spec = ",".join(str(r + 1) for r in rows)
        pdftools.extract_pages(self.cur, out, spec)
        self.win.toast("Saved")

    def save(self):
        if not self._need_doc():
            return
        out, _ = QFileDialog.getSaveFileName(self, "", f"{self.src_name}_organized.pdf", "PDF (*.pdf)")
        if not out:
            return
        try:
            with pymupdf.open(self.cur) as d:
                d.save(out, garbage=3, deflate=True)
        except Exception as e:
            return self.win.warn(tr("Error"), str(e))
        self.win.log.appendPlainText(trf("✔ Saved {name}", name=Path(out).name))
        self.win.last_dir = _folder(out)
        self.win.open_btn.setEnabled(True)
        self.win.toast("Saved")


# ---------------------------------------------------------------- redact
class RedactTool(Tool):
    key, icon, title = "redact", "redact", "Redact (black out)"
    subtitle = "Permanently remove words, patterns or areas — the text underneath is deleted, not just covered."
    PATTERNS = [("E-mail addresses", "email"), ("Phone numbers", "phone"), ("Web addresses", "url"),
                ("Card numbers", "card"), ("IBAN", "iban"), ("Persian digit sequences", "digits_fa")]

    def build(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        self.picker = PagePicker()
        self.picker.set_hint("Drag on the page to draw a black box. Right-click a box to remove it.")
        row.addWidget(self.picker, 3)
        side = QVBoxLayout()
        side.setSpacing(8)
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("save")
        side.addLayout(stacked("PDF file", self.src))
        side.addLayout(stacked("Save as", self.out))
        side.addWidget(mklabel("Words or phrases to black out (one per line)"))
        self.terms = QPlainTextEdit()
        self.terms.setMinimumHeight(110)
        self.terms.setLayoutDirection(Qt.LeftToRight)
        side.addWidget(self.terms, 1)
        side.addWidget(mklabel("Find automatically:", "muted"))
        self.pat = {}
        for label, key in self.PATTERNS:
            c = mkcheck(label, False)
            self.pat[key] = c
            side.addWidget(c)
        side.addWidget(mkbutton("Find matches and add them to the list", self.find))
        self.fill = color_combo("#000000")
        side.addWidget(self.fill)
        self.count = mklabel("", "muted", translate=False)
        side.addWidget(self.count)
        self.picker.changed.connect(self._count)
        row.addLayout(side, 2)
        row.setStretch(0, 5)
        self.body.addLayout(row, 1)
        self.run_button("Redact permanently", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_suffix_path(p, "_redacted"))
        if not self.picker.set_pdf(p):
            self.win.warn(tr("Cannot open"), tr("The PDF is password protected"))

    def _count(self):
        n = sum(len(v) for v in self.picker.rects.values())
        self.count.setText(trf("{n} box(es) drawn", n=n) if n else "")

    def find(self):
        src = self.src.get()
        if not self.need(src):
            return
        keys = [k for k, c in self.pat.items() if c.isChecked()]
        if not keys:
            return self.win.toast("Tick at least one pattern")
        have = {t.strip() for t in self.terms.toPlainText().splitlines()}
        found = []
        for k in keys:
            for t in pdftools.find_terms(src, k):
                if t not in have:
                    found.append(t)
                    have.add(t)
        if found:
            cur = self.terms.toPlainText().rstrip()
            self.terms.setPlainText((cur + "\n" if cur else "") + "\n".join(found))
        self.win.toast(trf("{n} found", n=len(found)))

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        if Path(src).resolve() == Path(out).resolve():
            return self.win.warn(tr("Choose another file"), tr("Save to a different file than the original."))
        terms = [t.strip() for t in self.terms.toPlainText().splitlines() if t.strip()]
        areas, fill = self.picker.areas(), self.fill.currentData()
        if not terms and not areas:
            return self.win.warn(tr("Missing information"), tr("Type words to remove or draw boxes on the page."))

        def job(log, prog):
            n = pdftools.redact(src, out, terms, areas, fill)
            log(trf("✔ Saved {name}: {n} area(s) redacted", name=Path(out).name, n=n))
            return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- edit
class EditTool(Tool):
    key, icon, title = "edit", "edit", "Edit PDF"
    subtitle = "Replace text, add text or pictures where you draw a box, and replace or remove pictures."
    MODES = {"Replace text": "replace_text", "Add text": "add_text", "Add a picture": "add_image",
             "Replace a picture": "replace_image", "Remove a picture": "delete_image"}

    def build(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        self.picker = PagePicker(single=True)
        row.addWidget(self.picker, 3)
        self.picker.pageChanged.connect(self._refresh_overlays)
        side = QVBoxLayout()
        side.setSpacing(8)
        self.src = FileRow(on_pick=self._picked)
        self.out = FileRow("save")
        self.mode = mkcombo({tr(k): v for k, v in self.MODES.items()})
        self.mode.currentIndexChanged.connect(self._mode)
        side.addLayout(stacked("PDF file", self.src))
        side.addLayout(stacked("Save as", self.out))
        side.addLayout(stacked("What to do", self.mode))
        self.opts = QStackedWidget()
        self.idx = {}

        def page_(name, builder):
            w = QWidget()
            lay = Form(95)
            w.setLayout(lay)
            self.idx[name] = self.opts.addWidget(w)
            return builder(lay)

        def rep(l):
            self.find_ = QLineEdit()
            self.with_ = QLineEdit()
            self.rep_pages = QLineEdit()
            self.rep_pages.setPlaceholderText(tr("all pages, or e.g. 1-3, 7"))
            l.row("Find", self.find_)
            l.row("Replace with", self.with_)
            l.row("Pages", self.rep_pages)
        page_("replace_text", rep)

        def addt(l):
            self.text = QPlainTextEdit()
            self.text.setMinimumHeight(90)
            l.row("Text", self.text)
            self.size = QSpinBox()
            self.size.setRange(6, 120)
            self.size.setValue(14)
            l.row("Font size", self.size)
            self.tcolor = color_combo("#000000")
            l.row("Colour", self.tcolor)
            self.bold = mkcheck("Bold", False)
            l.row("", self.bold, True)
        page_("add_text", addt)

        def addi(l):
            self.image = FileRow("open", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
            l.row("Picture", self.image)
        page_("add_image", addi)

        def repi(l):
            self.image2 = FileRow("open", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
            l.row("New picture", self.image2)
            self.pic_info = mklabel("", "muted", wrap=True, translate=False)
            l.row("", self.pic_info, True)
        page_("replace_image", repi)

        def deli(l):
            self.pic_info2 = mklabel("", "muted", wrap=True, translate=False)
            l.row("", self.pic_info2, True)
        page_("delete_image", deli)
        side.addWidget(self.opts)
        self.hint = mklabel("", "muted", wrap=True)
        side.addWidget(self.hint)
        side.addStretch(1)
        row.addLayout(side, 2)
        row.setStretch(0, 5)
        self.body.addLayout(row, 1)
        self.run_button("Apply", self.run)
        self._mode()

    HINTS = {"replace_text": "Type the text to find and what should replace it. Persian works too.",
             "add_text": "Draw a box on the page where the text should go, then type the text.",
             "add_image": "Draw a box on the page where the picture should go.",
             "replace_image": "Click a picture on the page (green outline), then choose the new picture.",
             "delete_image": "Click the picture you want to remove (green outline)."}

    def _picked(self, p):
        if not self.out.get():
            self.out.edit.setText(_suffix_path(p, "_edited"))
        if not self.picker.set_pdf(p):
            self.win.warn(tr("Cannot open"), tr("The PDF is password protected"))

    def _mode(self):
        m = self.mode.currentData()
        self.opts.setCurrentIndex(self.idx[m])
        self.picker.set_hint(self.HINTS[m] if m != "replace_text" else "")
        self.picker.setVisible(m != "replace_text")
        self.hint.setText(tr(self.HINTS[m]))
        self.hint.setVisible(m == "replace_text")
        self.picker.clear_btn.setVisible(m in ("add_text", "add_image"))
        self._refresh_overlays()

    def _refresh_overlays(self, *_a):
        m = self.mode.currentData()
        src = self.src.get()
        if m in ("replace_image", "delete_image") and src and self.picker.doc:
            try:
                imgs = pdftools.list_images(src, self.picker.page)
            except Exception:
                imgs = []
            self.picker.set_overlays([(i["xref"], i["rect"]) for i in imgs])
            txt = trf("{n} picture(s) on this page", n=len(imgs))
            self.pic_info.setText(txt)
            self.pic_info2.setText(txt)
        else:
            self.picker.set_overlays([])

    def run(self):
        src, out, m = self.src.get(), self.out.get(), self.mode.currentData()
        if not self.need(src, out):
            return
        if Path(src).resolve() == Path(out).resolve():
            return self.win.warn(tr("Choose another file"), tr("Save to a different file than the original."))
        page = self.picker.page
        rect = self.picker.current_rect()
        sel = self.picker.selected

        if m == "replace_text":
            old, new, pages = self.find_.text(), self.with_.text(), self.rep_pages.text()
            if not self.need(old):
                return

            def job(log, prog):
                n = pdftools.replace_text(src, out, old, new, pages)
                log(trf("✔ Saved {name}: {n} replacement(s)", name=Path(out).name, n=n))
                return _folder(out)
        elif m == "add_text":
            text = self.text.toPlainText()
            if not self.need(text):
                return
            if rect is None:
                return self.win.warn(tr("Missing information"), tr("Draw a box on the page first."))
            size, color, bold = self.size.value(), self.tcolor.currentData(), self.bold.isChecked()

            def job(log, prog):
                ok = pdftools.add_text(src, out, page, rect, text, size, color, bold)
                log(trf("✔ Saved {name}", name=Path(out).name) + ("" if ok else " — " + tr("the text did not fit the box completely")))
                return _folder(out)
        elif m == "add_image":
            img = self.image.get()
            if not self.need(img):
                return
            if rect is None:
                return self.win.warn(tr("Missing information"), tr("Draw a box on the page first."))

            def job(log, prog):
                pdftools.add_image(src, out, page, rect, img)
                log(trf("✔ Saved {name}", name=Path(out).name))
                return _folder(out)
        elif m == "replace_image":
            img = self.image2.get()
            if not self.need(img):
                return
            if sel is None:
                return self.win.warn(tr("Missing information"), tr("Click a picture on the page first."))

            def job(log, prog):
                pdftools.replace_image(src, out, page, sel, img)
                log(trf("✔ Saved {name}", name=Path(out).name))
                return _folder(out)
        else:
            if sel is None:
                return self.win.warn(tr("Missing information"), tr("Click a picture on the page first."))

            def job(log, prog):
                pdftools.delete_image(src, out, page, sel)
                log(trf("✔ Saved {name}", name=Path(out).name))
                return _folder(out)
        self.win.run(job)


# ---------------------------------------------------------------- compare
class CompareTool(Tool):
    key, icon, title = "compare", "compare", "Compare PDFs"
    subtitle = "Find what changed between two versions — by text and by looking at the pages."

    def build(self):
        f = Form()
        self.a = FileRow()
        self.b = FileRow()
        f.row("Original", self.a)
        f.row("New version", self.b)
        self.body.addLayout(f)
        top = QHBoxLayout()
        top.addWidget(mkbutton("Compare", self.compare, "primary", 140))
        top.addWidget(mkbutton("Save report as PDF…", self.report))
        self.summary = mklabel("", "muted", translate=False)
        top.addWidget(self.summary, 1)
        self.body.addLayout(top)
        split = QHBoxLayout()
        split.setSpacing(10)
        self.pages = QListWidget()
        self.pages.setMaximumWidth(230)
        self.pages.setLayoutDirection(Qt.LeftToRight)
        self.pages.currentRowChanged.connect(self._show)
        split.addWidget(self.pages)
        self.view = QStackedWidget()
        self.visual = QScrollArea()
        self.visual.setWidgetResizable(True)
        self.visual.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.vlabel = QLabel()
        self.vlabel.setAlignment(Qt.AlignCenter)
        self.visual.setWidget(self.vlabel)
        self.text = QTextBrowser()
        self.view.addWidget(self.visual)
        self.view.addWidget(self.text)
        col = QVBoxLayout()
        seg = QHBoxLayout()
        self.b_vis = mkbutton("Visual differences", lambda: self._tab(0))
        self.b_txt = mkbutton("Text differences", lambda: self._tab(1))
        for b in (self.b_vis, self.b_txt):
            b.setProperty("pill", True)
            b.setCheckable(True)
            seg.addWidget(b)
        seg.addStretch(1)
        self.b_vis.setChecked(True)
        col.addLayout(seg)
        col.addWidget(self.view, 1)
        split.addLayout(col, 1)
        self.body.addLayout(split, 1)
        self.rows: list[dict] = []

    def _tab(self, i: int):
        self.view.setCurrentIndex(i)
        self.b_vis.setChecked(i == 0)
        self.b_txt.setChecked(i == 1)

    def compare(self):
        a, b = self.a.get(), self.b.get()
        if not self.need(a, b):
            return
        self.pages.clear()
        self.summary.setText(tr("Comparing…"))
        box = {}

        def job(log, prog):
            box["rows"] = pdftools.compare_text(a, b)
            log(trf("Compared {n} page(s).", n=len(box["rows"])))

        def done():
            self.rows = box.get("rows", [])
            diff = 0
            for r in self.rows:
                it = QListWidgetItem(("● " if not r["same"] else "   ") + trf("Page {n} — {p}% similar", n=r["page"] + 1, p=int(r["ratio"] * 100)))
                it.setData(Qt.UserRole, r["page"])
                if not r["same"]:
                    diff += 1
                self.pages.addItem(it)
            self.summary.setText(trf("{d} of {n} page(s) differ", d=diff, n=len(self.rows)))
            for i, r in enumerate(self.rows):
                if not r["same"]:
                    self.pages.setCurrentRow(i)
                    break
        self.win.run(job, done)

    def _show(self, row: int):
        if row < 0 or row >= len(self.rows):
            return
        r = self.rows[row]
        self.text.setHtml(f'<div dir="auto" style="font-size:12pt;line-height:1.6">{r["html"] or tr("(no text on this page)")}</div>')
        try:
            png, share = pdftools.compare_visual(self.a.get(), self.b.get(), r["page"])
            pm = QPixmap()
            pm.loadFromData(png)
            w = max(self.visual.viewport().width() - 20, 300)
            self.vlabel.setPixmap(pm.scaledToWidth(w, Qt.SmoothTransformation))
        except Exception as e:
            self.vlabel.setText(str(e))

    def report(self):
        a, b = self.a.get(), self.b.get()
        if not self.need(a, b):
            return
        out, _ = QFileDialog.getSaveFileName(self, "", "comparison.pdf", "PDF (*.pdf)")
        if not out:
            return

        def job(log, prog):
            n, d = pdftools.compare_report(a, b, out)
            log(trf("✔ Saved {name}: {d} of {n} page(s) differ", name=Path(out).name, d=d, n=n))
            return _folder(out)
        self.win.run(job)
