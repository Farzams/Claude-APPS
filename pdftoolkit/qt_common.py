"""Shared Qt building blocks: cards, rows, file lists, job runner, page base class."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QSizePolicy, QVBoxLayout,
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

    def __init__(self):
        super().__init__()
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
            lab = mklabel(text)
            lab.setMinimumWidth(130)
            lab.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            self.addWidget(lab, self._r, 0)
            if isinstance(widget, QWidget):
                self.addWidget(widget, self._r, 1)
            else:
                self.addLayout(widget, self._r, 1)
        self._r += 1


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
        ic = QLabel()
        ic.setPixmap(qt_style.icon_pixmap(icon, 60))
        ic.setFixedSize(60, 60)
        lay.addWidget(ic)
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
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(24, 20, 24, 20)
        self.body.setSpacing(12)
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
        b.setMinimumHeight(46)
        self.body.addSpacing(6)
        self.body.addWidget(b)
        return b

    def note(self, text: str) -> QLabel:
        lb = mklabel(text, "muted", wrap=True)
        self.body.addWidget(lb)
        return lb
