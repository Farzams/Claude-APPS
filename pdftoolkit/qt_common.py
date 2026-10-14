"""Shared Qt building blocks: cards, rows, file lists, job runner, page base class."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRect, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QLayout, QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
                               QWidget)

import core
import i18n
import qt_style
from i18n import tr, trf

PDF_FILTER = "PDF (*.pdf)"


# ---------------------------------------------------------------- small factories
def mklabel(text="", role=None, wrap=False, translate=True) -> QLabel:
    lb = QLabel(tr(text) if translate else text)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.NoTextInteraction)
    return lb


def mkbutton(text, cb=None, kind="field", width=0, translate=True) -> QPushButton:
    b = QPushButton(tr(text) if translate else text)
    b.setProperty("kind", kind)
    b.setCursor(Qt.PointingHandCursor)
    if width:
        b.setMinimumWidth(width)
    if cb:
        b.clicked.connect(lambda _=False: cb())
    return b


def mkcombo(items: dict | list, current=None) -> QComboBox:
    """items: {display: value} or [display]; currentData() gives the value."""
    c = QComboBox()
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(14)
    popup = c.view().window()                     # the drop-down list: no square black frame or system shadow around it
    popup.setWindowFlag(Qt.NoDropShadowWindowHint, True)
    popup.setAutoFillBackground(True)
    pairs = items.items() if isinstance(items, dict) else [(i, i) for i in items]
    for disp, val in pairs:
        c.addItem(disp, val)
    if current is not None:
        i = c.findData(current)
        if i >= 0:
            c.setCurrentIndex(i)
    return c


def mkcheck(text, checked=True) -> QCheckBox:
    c = QCheckBox(tr(text))
    c.setChecked(checked)
    c.setCursor(Qt.PointingHandCursor)
    return c


def hline() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.NoFrame)
    return f


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


# ---------------------------------------------------------------- background jobs
class _Signals(QObject):
    log = Signal(str)
    prog = Signal(float)
    done = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.s = _Signals()

    def run(self):
        result = None
        try:
            result = self.fn(self.s.log.emit, lambda i, t: self.s.prog.emit(i / max(t, 1)))
        except Exception as e:  # shown in the log, never crashes the app
            self.s.log.emit(f"✘ {tr('Error')}: {e}")
        self.s.done.emit(result)


class JobRunner(QObject):
    log = Signal(str)
    prog = Signal(float)
    started = Signal()
    finished = Signal(object)

    def __init__(self):
        super().__init__()
        self.busy = False
        self._keep = None
        self._cb = None

    def run(self, fn, done=None) -> bool:
        if self.busy:
            return False
        self.busy = True
        self._cb = done
        job = _Job(fn)
        job.s.log.connect(self.log)
        job.s.prog.connect(self.prog)
        job.s.done.connect(self._finish)
        self._keep = job
        self.started.emit()
        QThreadPool.globalInstance().start(job)
        return True

    def _finish(self, result):
        self.busy = False
        cb, self._cb = self._cb, None
        self.finished.emit(result)
        if cb:
            cb()


# ---------------------------------------------------------------- form rows
class Form(QGridLayout):
    """Label + widget rows; Qt flips the whole thing for right-to-left languages."""

    def __init__(self, label_width: int = 130):
        super().__init__()
        self.label_width = label_width
        self.setHorizontalSpacing(14)
        self.setVerticalSpacing(10)
        self.setColumnStretch(1, 1)
        self._r = 0

    def row(self, text: str, widget: QWidget | QHBoxLayout | None = None, span=False):
        if span:
            if isinstance(widget, QWidget):
                self.addWidget(widget, self._r, 0, 1, 2)
            else:
                self.addLayout(widget, self._r, 0, 1, 2)
        else:
            lab = mklabel(text, "form")
            lab.setMinimumWidth(self.label_width)
            lab.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            self.addWidget(lab, self._r, 0)
            if isinstance(widget, QWidget):
                self.addWidget(widget, self._r, 1)
            else:
                self.addLayout(widget, self._r, 1)
        self._r += 1


RECENT_HOOK = [None]          # the main window registers itself here to remember the files you pick


def note_recent(paths):
    if RECENT_HOOK[0]:
        for p in paths:
            if p and Path(p).is_file():
                RECENT_HOOK[0](p)


class FileRow(QWidget):
    """Entry + Browse button (file to open, file to save, or folder)."""

    def __init__(self, kind="open", filt=PDF_FILTER, on_pick=None, save_ext=".pdf"):
        super().__init__()
        self.kind, self.filt, self.on_pick, self.save_ext = kind, filt, on_pick, save_ext
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.edit = QLineEdit()
        self.edit.setLayoutDirection(Qt.LeftToRight)      # paths read left-to-right
        self.edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.edit, 1)
        lay.addWidget(mkbutton("Browse…", self._browse))

    def _browse(self):
        if self.kind == "open":
            p, _ = QFileDialog.getOpenFileName(self, "", "", self.filt)
        elif self.kind == "save":
            p, _ = QFileDialog.getSaveFileName(self, "", "", self.filt)
            if p and not Path(p).suffix:
                p += self.save_ext
        else:
            p = QFileDialog.getExistingDirectory(self)
        if p:
            self.set(p)

    def set(self, p: str):
        self.edit.setText(p)
        if self.kind == "open":
            note_recent([p])
        if self.on_pick:
            self.on_pick(p)

    def get(self) -> str:
        return self.edit.text().strip()


class FileList(QWidget):
    """Reorderable multi-file list."""

    def __init__(self, filt="All files (*.*)", min_rows=5):
        super().__init__()
        self.filt = filt
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.lb = QListWidget()
        self.lb.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lb.setDragDropMode(QAbstractItemView.InternalMove)
        self.lb.setLayoutDirection(Qt.LeftToRight)
        self.lb.setMinimumHeight(30 * min_rows)
        lay.addWidget(self.lb, 1)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.addWidget(mkbutton("＋ Add files", self.add_dialog, "primary"))
        bar.addWidget(mkbutton("▲ Up", lambda: self.move(-1)))
        bar.addWidget(mkbutton("▼ Down", lambda: self.move(1)))
        bar.addWidget(mkbutton("Remove", self.remove))
        bar.addWidget(mkbutton("Clear", self.clear))
        bar.addStretch(1)
        self.count = mklabel("", "muted", translate=False)
        bar.addWidget(self.count)
        lay.addLayout(bar)
        self._update()

    @property
    def files(self) -> list[str]:
        return [self.lb.item(i).data(Qt.UserRole) for i in range(self.lb.count())]

    def add_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "", "", self.filt)
        self.add_paths(paths)

    def add_paths(self, paths):
        note_recent(paths)
        have = set(self.files)
        for p in paths:
            if p not in have:
                it = self.lb.addItem(f"{Path(p).name}    —    {Path(p).parent}")
                item = self.lb.item(self.lb.count() - 1)
                item.setData(Qt.UserRole, p)
                have.add(p)
        self._update()

    def remove(self):
        for it in self.lb.selectedItems():
            self.lb.takeItem(self.lb.row(it))
        self._update()

    def clear(self):
        self.lb.clear()
        self._update()

    def move(self, d):
        rows = sorted(self.lb.row(i) for i in self.lb.selectedItems())
        if not rows or (d < 0 and rows[0] == 0) or (d > 0 and rows[-1] == self.lb.count() - 1):
            return
        for r in (rows if d < 0 else rows[::-1]):
            it = self.lb.takeItem(r)
            self.lb.insertItem(r + d, it)
            it.setSelected(True)

    def _update(self):
        self.count.setText(trf("{n} file(s)", n=self.lb.count()))


# ---------------------------------------------------------------- page base
class Hero(QFrame):
    """Page header: colourful icon, title and subtitle over the picture."""

    def __init__(self, icon: str, title: str, subtitle: str):
        super().__init__()
        self.setObjectName("hero")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(16)
        lay.addWidget(qt_style.IconLabel(icon, 60, "hero"))
        col = QVBoxLayout()
        col.setSpacing(2)
        self.title = QLabel(tr(title))
        self.title.setObjectName("heroTitle")
        self.sub = QLabel(tr(subtitle))
        self.sub.setObjectName("heroSub")
        self.sub.setWordWrap(True)
        col.addWidget(self.title)
        col.addWidget(self.sub)
        lay.addLayout(col, 1)


class Tool(QWidget):
    """A page: hero on top, one card below."""

    key = ""
    icon = "read"
    title = ""
    subtitle = ""

    def __init__(self, win):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        outer.addWidget(Hero(self.icon, self.title, self.subtitle))
        self.card = Card()
        outer.addWidget(self.card, 1)
        # the content scrolls when the window is too short, instead of squeezing the fields
        shell = QVBoxLayout(self.card)
        shell.setContentsMargins(0, 6, 0, 6)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        inner = QWidget()
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(24, 14, 24, 14)
        self.body.setSpacing(12)
        self.scroll.setWidget(inner)
        shell.addWidget(self.scroll)
        self.build()

    def build(self): ...

    def on_show(self): ...

    def drop(self, paths: list[str]):
        for w in self.card.findChildren(QWidget):
            if isinstance(w, FileList):
                w.add_paths(paths)
                return
            if isinstance(w, FileRow) and w.kind == "open":
                w.set(paths[0])
                return

    def need(self, *vals) -> bool:
        if not all(vals):
            self.win.warn(tr("Missing information"), tr("Please fill in all the fields above."))
            return False
        return True

    def run_button(self, text, cb):
        b = mkbutton(text, cb, "primary")
        b.setMinimumHeight(40)
        b.setMinimumWidth(190)
        self.body.addSpacing(6)
        row = QHBoxLayout()
        row.addWidget(b)
        row.addStretch(1)
        self.body.addLayout(row)
        return b

    def note(self, text: str) -> QLabel:
        lb = mklabel(text, "muted", wrap=True)
        self.body.addWidget(lb)
        return lb


class FlowLayout(QLayout):
    """Lays widgets out left to right and wraps them to the next line when the row is full."""

    def __init__(self, parent=None, hspace: int = 8, vspace: int = 8):
        super().__init__(parent)
        self._items: list = []
        self._h, self._v = hspace, vspace
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do(QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do(rect, False)

    def sizeHint(self):
        w = h = 0
        for it in self._items:
            sz = it.sizeHint()
            w += sz.width() + self._h
            h = max(h, sz.height())
        return QSize(max(0, w - self._h), h)

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do(self, rect, test):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = r.x(), r.y(), 0
        rtl = self.parentWidget() is not None and self.parentWidget().layoutDirection() == Qt.RightToLeft
        for it in self._items:
            sz = it.sizeHint()
            if x + sz.width() > r.right() + 1 and line_h > 0:
                x, y, line_h = r.x(), y + line_h + self._v, 0
            if not test:
                px = (r.right() + 1 - (x - r.x()) - sz.width()) if rtl else x
                it.setGeometry(QRect(QPoint(px, y), sz))
            x += sz.width() + self._h
            line_h = max(line_h, sz.height())
        return y + line_h - r.y() + m.top() + m.bottom()
