"""Ctrl+K: one search box for every tool, setting and recent file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout)

import i18n
import qt_style
import theme
from i18n import tr


@dataclass
class Entry:
    title: str                      # English title (translated for display)
    hint: str = ""
    icon: str = "page"
    kind: str = "Tool"              # Tool / Setting / Recent
    action: Callable[[], None] | None = None
    keywords: str = ""
    raw: bool = False               # title is already display text (file names)
    haystack: str = field(default="", init=False)

    def __post_init__(self):
        shown = self.title if self.raw else tr(self.title)
        hint = self.hint if self.raw else tr(self.hint) if self.hint else ""
        self.haystack = f"{self.title} {shown} {hint} {self.keywords}".lower()

    def display(self) -> str:
        return self.title if self.raw else tr(self.title)


def score(entry: Entry, tokens: list[str]) -> int | None:
    """Lower is better; None when a word of the query is missing."""
    s = 0
    title = entry.display().lower()
    for t in tokens:
        i = entry.haystack.find(t)
        if i < 0:
            return None
        s += 0 if title.startswith(t) else 1 if t in title else 3
    return s


class CommandPalette(QDialog):
    MAX = 9

    def __init__(self, win):
        super().__init__(win, Qt.Popup | Qt.FramelessWindowHint)
        self.win = win
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.entries: list[Entry] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        box = QFrame()
        box.setObjectName("palettebox")
        outer.addWidget(box)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 12, 12, 10)
        lay.setSpacing(8)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("Search tools, settings and recent files…"))
        self.edit.setMinimumHeight(40)
        self.edit.textChanged.connect(self.refresh)
        self.edit.installEventFilter(self)
        lay.addWidget(self.edit)
        self.list = QListWidget()
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemActivated.connect(self.run_item)
        self.list.itemClicked.connect(self.run_item)
        lay.addWidget(self.list)
        self.empty = QLabel(tr("Nothing matches."))
        self.empty.setProperty("role", "muted")
        self.empty.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.empty)
        foot = QLabel(tr("↑ ↓ to choose   ·   Enter to open   ·   Esc to close"))
        foot.setProperty("role", "muted")
        lay.addWidget(foot)
        self.setFixedWidth(620)

    def eventFilter(self, obj, ev):
        if obj is self.edit and ev.type() == QEvent.KeyPress:
            k = ev.key()
            if k in (Qt.Key_Down, Qt.Key_Up):
                n = self.list.count()
                if n:
                    self.list.setCurrentRow((self.list.currentRow() + (1 if k == Qt.Key_Down else -1)) % n)
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                if self.list.currentItem():
                    self.run_item(self.list.currentItem())
                return True
        return super().eventFilter(obj, ev)

    def open(self):
        P = theme.STATE.pal
        flat = P["flat"]
        self.entries = self.win.palette_entries()
        extra = (f"QFrame#palettebox {{ background: {P['card']}; border: 1px solid {P['line']}; border-radius: 16px; }}"
                 f"QListWidget {{ background: transparent; border: none; padding: 0; }}"
                 f"QListWidget::item {{ border-radius: 9px; padding: 0; }}"
                 f"QListWidget::item:selected {{ background: {qt_style.rgba(P['accent'], 0.16)}; }}"
                 f"QListWidget::item:hover {{ background: {P['hover']}; }}")
        self.setStyleSheet(self.win.qss + extra)
        self.edit.clear()
        self.refresh()
        w = self.win
        self.adjustSize()
        self.move(w.mapToGlobal(w.rect().center()).x() - self.width() // 2, w.mapToGlobal(w.rect().topLeft()).y() + 90)
        self.show()
        self.edit.setFocus()

    def refresh(self, *_):
        q = self.edit.text().strip().lower()
        tokens = q.split()
        ranked = []
        for i, e in enumerate(self.entries):
            if not tokens:
                if e.kind == "Recent" or (e.kind == "Tool" and i < 40):
                    ranked.append((0 if e.kind == "Recent" else 1, i, e))
                continue
            s = score(e, tokens)
            if s is not None:
                ranked.append((s, i, e))
        ranked.sort(key=lambda r: (r[0], r[1]))
        self.list.clear()
        for _s, _i, e in ranked[:self.MAX]:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, e)
            row = self._row(e)
            it.setSizeHint(row.sizeHint())
            self.list.addItem(it)
            self.list.setItemWidget(it, row)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.empty.setVisible(self.list.count() == 0)
        self.list.setVisible(self.list.count() > 0)
        self.list.setFixedHeight(min(self.list.count(), self.MAX) * 48 + 4)
        self.adjustSize()

    def _row(self, e: Entry) -> QFrame:
        row = QFrame()
        row.setAttribute(Qt.WA_TransparentForMouseEvents)
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(12)
        h.addWidget(qt_style.IconLabel(e.icon, 28, "nav"))
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(e.display())
        t.setStyleSheet("font-weight: 600; background: transparent;")
        col.addWidget(t)
        if e.hint:
            hint = QLabel(e.hint if e.raw else tr(e.hint))
            hint.setProperty("role", "muted")
            hint.setStyleSheet("background: transparent;")
            col.addWidget(hint)
        h.addLayout(col, 1)
        k = QLabel(tr(e.kind))
        k.setProperty("role", "muted")
        k.setStyleSheet("background: transparent;")
        h.addWidget(k)
        row.setFixedHeight(48)
        return row

    def run_item(self, item: QListWidgetItem):
        e: Entry = item.data(Qt.UserRole)
        self.close()
        if e.action:
            e.action()


def install(win) -> CommandPalette:
    pal = CommandPalette(win)
    QShortcut(QKeySequence("Ctrl+K"), win, activated=pal.open)
    return pal
