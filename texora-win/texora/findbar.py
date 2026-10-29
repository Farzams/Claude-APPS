"""Find and replace bar for the source (case, whole word, regular expression, whole project) and the PDF search bar."""
import io
import os
import re

from .qt import Qt, QtGui, QtWidgets
from .store import is_text_file
from .strings import t


def build_regex(text, case, word, regex):
    """A compiled pattern, or None when the text is empty or not a valid regular expression."""
    if not text:
        return None
    pat = text if regex else re.escape(text)
    if word:
        pat = r"\b(?:%s)\b" % pat
    try:
        return re.compile(pat, 0 if case else re.IGNORECASE | re.MULTILINE) if not case else re.compile(pat, re.MULTILINE)
    except re.error:
        return False


class FindBar(QtWidgets.QFrame):
    def __init__(self, page):
        super(FindBar, self).__init__()
        self.page = page
        self.setObjectName("bar")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(4)
        row = QtWidgets.QHBoxLayout()
        self.find = QtWidgets.QLineEdit()
        self.find.setPlaceholderText(t("f.find"))
        self.count = QtWidgets.QLabel("")
        self.count.setObjectName("muted")
        self.case = QtWidgets.QCheckBox(t("match.case"))
        self.word = QtWidgets.QCheckBox(t("f.word"))
        self.regex = QtWidgets.QCheckBox(t("f.regex"))
        self.project = QtWidgets.QCheckBox(t("f.in.project"))
        prev = QtWidgets.QToolButton()
        prev.setText("↑")
        nxt = QtWidgets.QToolButton()
        nxt.setText("↓")
        close = QtWidgets.QToolButton()
        close.setText("✕")
        for w in (self.find, self.count, prev, nxt, self.case, self.word, self.regex, self.project, close):
            row.addWidget(w)
        row.setStretch(0, 1)
        lay.addLayout(row)
        row2 = QtWidgets.QHBoxLayout()
        self.repl = QtWidgets.QLineEdit()
        self.repl.setPlaceholderText(t("f.replace.with"))
        one = QtWidgets.QPushButton(t("replace"))
        allb = QtWidgets.QPushButton(t("replace.all"))
        row2.addWidget(self.repl, 1)
        row2.addWidget(one)
        row2.addWidget(allb)
        self.row2 = QtWidgets.QWidget()
        self.row2.setLayout(row2)
        row2.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.row2)
        self.index = 0
        for w in (self.case, self.word, self.regex):
            w.toggled.connect(self._changed)
        self.find.textChanged.connect(self._changed)
        self.find.returnPressed.connect(self._enter)
        prev.clicked.connect(lambda: self.step(-1))
        nxt.clicked.connect(lambda: self.step(1))
        one.clicked.connect(self.replace_one)
        allb.clicked.connect(self.replace_all)
        close.clicked.connect(self.hide)
        self.hide()

    # ------------------------------------------------------------ the source
    def pattern(self):
        p = build_regex(self.find.text(), self.case.isChecked(), self.word.isChecked(), self.regex.isChecked())
        self.find.setStyleSheet("border: 1px solid #D32F2F;" if p is False else "")
        return p or None

    def spans(self):
        p = self.pattern()
        if not p:
            return []
        text = self.page.editor.toPlainText()
        return [(m.start(), m.end() - m.start()) for m in p.finditer(text) if m.end() > m.start()]

    def _changed(self, *_):
        self.index = 0
        if self.project.isChecked():
            self.count.setText("")
            self.page.editor.set_matches([], -1)
        else:
            self._show(move=False)

    def _show(self, move=True):
        sp = self.spans()
        self.count.setText("%d / %d" % (min(self.index + 1, len(sp)), len(sp)) if sp else ("0" if self.find.text() else ""))
        self.page.editor.set_matches(sp, self.index if sp else -1)
        if sp and move:
            c = self.page.editor.textCursor()
            c.setPosition(sp[self.index % len(sp)][0])
            self.page.editor.setTextCursor(c)
            self.page.editor.centerCursor()

    def _enter(self):
        if self.project.isChecked():
            self.page.search_project(self)
        else:
            self.step(1)

    def step(self, d):
        sp = self.spans()
        if sp:
            if self.index >= len(sp):
                self.index = 0
            else:
                self.index = (self.index + d) % len(sp)
            self._show()

    def replace_one(self):
        sp = self.spans()
        if not sp:
            return
        at, ln = sp[self.index % len(sp)]
        text = self.page.editor.toPlainText()
        p = self.pattern()
        m = p.match(text, at)
        rep = m.expand(self.repl.text()) if (m and self.regex.isChecked()) else self.repl.text()
        c = self.page.editor.textCursor()
        c.setPosition(at)
        c.setPosition(at + ln, QtGui.QTextCursor.KeepAnchor)
        c.insertText(rep)
        self._show()

    def replace_all(self):
        p = self.pattern()
        if not p:
            return
        if self.project.isChecked():
            self.page.replace_in_project(p, self.repl.text(), self.regex.isChecked())
            return
        text = self.page.editor.toPlainText()
        rep = self.repl.text()
        new = p.sub(rep if self.regex.isChecked() else (lambda m: rep), text)
        if new != text:
            c = self.page.editor.textCursor()
            c.beginEditBlock()
            c.select(QtGui.QTextCursor.Document)
            c.insertText(new)
            c.endEditBlock()
        self._show(move=False)

    def open(self, replace=False):
        self.show()
        self.row2.setVisible(True)
        self.find.setFocus()
        self.find.selectAll()
        sel = self.page.editor.textCursor().selectedText()
        if sel and " " not in sel:
            self.find.setText(sel)
        if replace:
            self.repl.setFocus()

    def hideEvent(self, e):
        super(FindBar, self).hideEvent(e)
        self.page.editor.set_matches([], -1)


class PdfSearchBar(QtWidgets.QFrame):
    def __init__(self, view):
        super(PdfSearchBar, self).__init__()
        self.view = view
        self.setObjectName("bar")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        self.edit = QtWidgets.QLineEdit()
        self.edit.setPlaceholderText(t("pdf.search"))
        self.count = QtWidgets.QLabel("")
        self.count.setObjectName("muted")
        prev = QtWidgets.QToolButton()
        prev.setText("↑")
        nxt = QtWidgets.QToolButton()
        nxt.setText("↓")
        close = QtWidgets.QToolButton()
        close.setText("✕")
        for w in (self.edit, self.count, prev, nxt, close):
            lay.addWidget(w)
        lay.setStretch(0, 1)
        self.edit.returnPressed.connect(self.go)
        prev.clicked.connect(lambda: self.view.step_hit(-1))
        nxt.clicked.connect(lambda: self.view.step_hit(1))
        close.clicked.connect(self.hide)
        self.hide()

    def go(self):
        n = self.view.search(self.edit.text())
        self.count.setText(str(n) if n else t("pdf.nohit"))

    def open(self):
        self.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def hideEvent(self, e):
        super(PdfSearchBar, self).hideEvent(e)
        self.view.search("")


def project_hits(root, files, pattern, read=None):
    """[(file, line number, line text)] for every match in the text files of the project."""
    out = []
    for f in files:
        if not is_text_file(f):
            continue
        text = read(f) if read else None
        if text is None:
            try:
                with io.open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
        for i, line in enumerate(text.split("\n")):
            if pattern.search(line):
                out.append((f, i + 1, line.strip()))
    return out
