"""The source editor: line numbers, LaTeX colours, find highlights and typing aids."""
import re

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QSize, QRect
from . import textutil

_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
_COMMAND = re.compile(r"\\[A-Za-z@]+\*?|\\.")
_MATH = re.compile(r"(?<!\\)\$\$?[^$]*\$\$?")
_ENV = re.compile(r"\\(?:begin|end)\{[^}]*\}")


class LatexHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, doc, theme):
        super(LatexHighlighter, self).__init__(doc)
        self.set_theme(theme, rehighlight=False)

    def set_theme(self, theme, rehighlight=True):
        dark = theme.dark
        self.f_command = self._fmt(theme.accent if not dark else theme.accent)
        self.f_math = self._fmt("#5EEAD4" if dark else "#0F766E")
        self.f_env = self._fmt("#F0A27C" if dark else "#B4532A", bold=True)
        self.f_comment = self._fmt(theme.pal.muted, italic=True)
        if rehighlight:
            self.rehighlight()

    @staticmethod
    def _fmt(color, bold=False, italic=False):
        f = QtGui.QTextCharFormat()
        f.setForeground(QtGui.QColor(color))
        if bold:
            f.setFontWeight(QtGui.QFont.DemiBold)
        if italic:
            f.setFontItalic(True)
        return f

    def highlightBlock(self, text):
        for rx, fmt in ((_MATH, self.f_math), (_COMMAND, self.f_command), (_ENV, self.f_env), (_COMMENT, self.f_comment)):
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class _Gutter(QtWidgets.QWidget):
    def __init__(self, editor):
        super(_Gutter, self).__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, e):
        self.editor.paint_gutter(e)


class CodeEditor(QtWidgets.QPlainTextEdit):
    caret_info = Signal(int, int)

    def __init__(self, theme, parent=None):
        super(CodeEditor, self).__init__(parent)
        self.theme = theme
        self.auto_pairs = True
        self.show_numbers = True
        self.matches = []
        self.match_len = 0
        self.current_match = -1
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4) if hasattr(self.fontMetrics(), "horizontalAdvance") else None
        self.setLayoutDirection(Qt.LeftToRight)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._on_cursor)
        self._update_gutter_width()
        self.apply_theme(theme)

    # ------------------------------------------------------------ look
    def apply_theme(self, theme, size=12):
        self.theme = theme
        f = QtGui.QFont(theme.mono)
        f.setStyleHint(QtGui.QFont.Monospace)
        f.setPointSize(size)
        self.setFont(f)
        self.gutter.setFont(f)
        self._update_gutter_width()
        self._on_cursor()

    def set_font_size(self, size):
        f = self.font()
        f.setPointSize(size)
        self.setFont(f)
        self.gutter.setFont(f)
        self._update_gutter_width()

    def set_wrap(self, on):
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth if on else QtWidgets.QPlainTextEdit.NoWrap)

    def set_show_numbers(self, on):
        self.show_numbers = on
        self._update_gutter_width()

    # ------------------------------------------------------------ line numbers
    def gutter_width(self):
        if not self.show_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        return 18 + self.fontMetrics().horizontalAdvance("9") * max(3, digits)

    def _update_gutter_width(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)
        self.gutter.setVisible(self.show_numbers)

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, e):
        super(CodeEditor, self).resizeEvent(e)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        p = QtGui.QPainter(self.gutter)
        pal = self.theme.pal
        p.fillRect(event.rect(), QtGui.QColor(pal.hover if not self.theme.dark else pal.card))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        cur = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                p.setPen(QtGui.QColor(pal.text if n == cur else pal.muted))
                p.drawText(0, top, self.gutter.width() - 8, self.fontMetrics().height(), Qt.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    # ------------------------------------------------------------ highlights
    def _on_cursor(self):
        c = self.textCursor()
        self.caret_info.emit(c.blockNumber() + 1, c.positionInBlock() + 1)
        self._selections()
        self.gutter.update()

    def set_matches(self, matches, length, current):
        self.matches, self.match_len, self.current_match = matches, length, current
        self._selections()

    def _selections(self):
        sels = []
        line = QtWidgets.QTextEdit.ExtraSelection()
        line.format.setBackground(QtGui.QColor(self.theme.pal.hover if self.theme.dark else self.theme.pal.hover))
        line.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        line.cursor = self.textCursor()
        line.cursor.clearSelection()
        sels.append(line)
        for k, at in enumerate(self.matches):
            s = QtWidgets.QTextEdit.ExtraSelection()
            s.format.setBackground(QtGui.QColor("#FFA000" if k == self.current_match else "#FDE68A"))
            s.format.setForeground(QtGui.QColor("#111111"))
            c = QtGui.QTextCursor(self.document())
            c.setPosition(at)
            c.setPosition(at + self.match_len, QtGui.QTextCursor.KeepAnchor)
            s.cursor = c
            sels.append(s)
        self.setExtraSelections(sels)

    # ------------------------------------------------------------ typing aids
    def keyPressEvent(self, e):
        t = e.text()
        if (self.auto_pairs and t and len(t) == 1 and not (e.modifiers() & (Qt.ControlModifier | Qt.AltModifier))
                and not self.textCursor().hasSelection() and (t in "{[()}]$" or t in "\r\n")):
            if t == "\r":
                t = "\n"
            text = self.toPlainText()
            pos = self.textCursor().position()
            act = textutil.smart_type(text, pos, t)
            if act is not None:
                c = self.textCursor()
                c.beginEditBlock()
                if act[0] == "skip":
                    c.movePosition(QtGui.QTextCursor.Right)
                else:
                    c.insertText(act[1])
                    c.setPosition(pos + act[2])
                c.endEditBlock()
                self.setTextCursor(c)
                return
        if e.key() == Qt.Key_Tab and not e.modifiers():
            self.insertPlainText("  ")
            return
        if e.key() == Qt.Key_Slash and e.modifiers() & Qt.ControlModifier:
            self.toggle_comment()
            return
        super(CodeEditor, self).keyPressEvent(e)

    def insert_snippet(self, snippet):
        """The cursor goes to the ‸ mark of the snippet, or to its end."""
        caret = snippet.find("\u2038")
        s = snippet.replace("\u2038", "")
        c = self.textCursor()
        start = c.selectionStart()
        c.insertText(s)
        c.setPosition(start + (caret if caret >= 0 else len(s)))
        self.setTextCursor(c)
        self.setFocus()

    def toggle_comment(self):
        c = self.textCursor()
        doc = self.document()
        first = doc.findBlock(c.selectionStart()).blockNumber()
        last = doc.findBlock(max(c.selectionStart(), c.selectionEnd() - (1 if c.hasSelection() else 0))).blockNumber()
        blocks = [doc.findBlockByNumber(i) for i in range(first, last + 1)]
        all_comments = all(b.text().lstrip().startswith("%") or not b.text().strip() for b in blocks)
        c.beginEditBlock()
        for b in blocks:
            cur = QtGui.QTextCursor(b)
            text = b.text()
            if all_comments:
                m = re.match(r"^(\s*)% ?", text)
                if m:
                    cur.setPosition(b.position() + len(m.group(1)))
                    cur.setPosition(b.position() + m.end(), QtGui.QTextCursor.KeepAnchor)
                    cur.removeSelectedText()
            else:
                cur.insertText("% ")
        c.endEditBlock()

    def go_to_line(self, n):
        b = self.document().findBlockByNumber(max(0, n - 1))
        c = self.textCursor()
        c.setPosition(b.position())
        self.setTextCursor(c)
        self.centerCursor()
        self.setFocus()
