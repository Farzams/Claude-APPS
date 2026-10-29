"""The source editor: line numbers, LaTeX colours, find highlights and typing aids."""
import re

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QSize, QRect
from . import completion, textutil

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
    ctrl_clicked = Signal(int)

    def __init__(self, theme, parent=None):
        super(CodeEditor, self).__init__(parent)
        self.theme = theme
        self.auto_pairs = True
        self.show_numbers = True
        self.matches = []
        self.current_match = -1
        self.extra_cursors = []
        self.completion_provider = None      # callable(kind) -> list of labels, keys or file names of the project
        self.completer = QtWidgets.QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setModel(QtCore.QStringListModel(self.completer))
        self.completer.setMaxVisibleItems(10)
        self.completer.activated[str].connect(self._complete_with)
        self._completion_prefix = ""
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

    def set_matches(self, spans, current=-1):
        """spans: list of (start, length)."""
        self.matches, self.current_match = spans, current
        self._selections()

    def _selections(self):
        sels = []
        line = QtWidgets.QTextEdit.ExtraSelection()
        line.format.setBackground(QtGui.QColor(self.theme.pal.hover if self.theme.dark else self.theme.pal.hover))
        line.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        line.cursor = self.textCursor()
        line.cursor.clearSelection()
        sels.append(line)
        limit = self.document().characterCount() - 1
        for k, (at, length) in enumerate(self.matches):
            if at + length > limit:
                continue
            s = QtWidgets.QTextEdit.ExtraSelection()
            s.format.setBackground(QtGui.QColor("#FFA000" if k == self.current_match else "#FDE68A"))
            s.format.setForeground(QtGui.QColor("#111111"))
            c = QtGui.QTextCursor(self.document())
            c.setPosition(at)
            c.setPosition(at + length, QtGui.QTextCursor.KeepAnchor)
            s.cursor = c
            sels.append(s)
        for c in self.extra_cursors:
            if c.hasSelection():
                x = QtWidgets.QTextEdit.ExtraSelection()
                x.format.setBackground(QtGui.QColor(self.theme.accent))
                x.format.setForeground(QtGui.QColor(self.theme.on_accent))
                x.cursor = c
                sels.append(x)
        self.setExtraSelections(sels)

    # ------------------------------------------------------------ typing aids
    _NAV = (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown)

    def keyPressEvent(self, e):
        popup = self.completer.popup()
        if popup.isVisible():
            if e.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                if e.key() == Qt.Key_Tab and popup.currentIndex().isValid() is False:
                    popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
                if e.key() == Qt.Key_Tab:
                    self._complete_with(popup.currentIndex().data() or "")
                    popup.hide()
                    return
                e.ignore()
                return
        if self.extra_cursors:
            if e.key() == Qt.Key_Escape:
                self.extra_cursors = []
                self._selections()
                self.viewport().update()
                return
            if self._multi_key(e):
                return
            if e.key() in self._NAV or (e.modifiers() & Qt.ControlModifier and e.key() not in (Qt.Key_C, Qt.Key_D)):
                self.extra_cursors = []
                self._selections()
        mod = e.modifiers()
        if e.key() == Qt.Key_Space and mod & Qt.ControlModifier:
            self._update_completion(force=True)
            return
        t = e.text()
        if (self.auto_pairs and t and len(t) == 1 and not (mod & (Qt.ControlModifier | Qt.AltModifier))
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
                if t == "{":
                    QtCore.QTimer.singleShot(0, self._update_completion)
                return
        if e.key() == Qt.Key_Tab and not mod:
            if self.textCursor().hasSelection():
                self.indent(1)
            else:
                self.insertPlainText("  ")
            return
        if e.key() == Qt.Key_Backtab:
            self.indent(-1)
            return
        if e.key() == Qt.Key_Slash and mod & Qt.ControlModifier:
            self.toggle_comment()
            return
        super(CodeEditor, self).keyPressEvent(e)
        if t and t.isprintable() and not (mod & Qt.ControlModifier) or e.key() == Qt.Key_Backspace:
            self._update_completion()
        elif popup.isVisible():
            popup.hide()

    # ------------------------------------------------------------ completion
    def _update_completion(self, force=False):
        c = self.textCursor()
        before = c.block().text()[:c.positionInBlock()]
        ctx = completion.context(before)
        popup = self.completer.popup()
        if ctx is None:
            popup.hide()
            return
        kind, prefix = ctx
        if kind == "cmd" and len(prefix) < 2 and not force:
            popup.hide()
            return
        extra = self.completion_provider(kind) if (self.completion_provider and kind in ("ref", "cite", "file")) else []
        kw = {"labels": extra} if kind == "ref" else {"keys": extra} if kind == "cite" else {"files": extra}
        items = completion.candidates(kind, prefix, **(kw if kind in ("ref", "cite", "file") else {}))
        if not items or (len(items) == 1 and items[0] == (("\\" + prefix) if kind == "cmd" else prefix)):
            popup.hide()
            return
        self._completion_prefix = ("\\" + prefix) if kind == "cmd" else prefix
        self.completer.model().setStringList(items)
        self.completer.setCompletionPrefix("")
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        r = self.cursorRect()
        r.setWidth(max(260, popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() + 20))
        self.completer.complete(r)

    def _complete_with(self, text):
        if not text:
            return
        c = self.textCursor()
        c.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, len(self._completion_prefix))
        c.insertText(text)
        # inside \begin{...} / \usepackage{...}: close the brace when it is not there yet
        before = c.block().text()[:c.positionInBlock()]
        after = c.block().text()[c.positionInBlock():]
        if completion.context(before[:len(before) - len(text)] + "x") in (("env", "x"), ("pkg", "x")) and not after.startswith("}"):
            c.insertText("}")
        self.setTextCursor(c)

    # ------------------------------------------------------------ formatting
    def wrap_selection(self, before, after):
        """Puts [before] and [after] around the selection (or the cursor); doing it again takes them off."""
        c = self.textCursor()
        sel = c.selectedText().replace("\u2029", "\n")
        a, b = c.selectionStart(), c.selectionEnd()
        text = self.toPlainText()
        c.beginEditBlock()
        if sel.startswith(before) and sel.endswith(after) and len(sel) >= len(before) + len(after):
            inner = sel[len(before):len(sel) - len(after)]
            c.insertText(inner)
            c.setPosition(a)
            c.setPosition(a + len(inner), QtGui.QTextCursor.KeepAnchor)
        elif a >= len(before) and text[a - len(before):a] == before and text[b:b + len(after)] == after:
            c.setPosition(b)
            c.setPosition(b + len(after), QtGui.QTextCursor.KeepAnchor)
            c.removeSelectedText()
            c.setPosition(a - len(before))
            c.setPosition(a, QtGui.QTextCursor.KeepAnchor)
            c.removeSelectedText()
            c.setPosition(a - len(before))
            c.setPosition(a - len(before) + len(sel), QtGui.QTextCursor.KeepAnchor)
        else:
            c.insertText(before + sel + after)
            c.setPosition(a + len(before))
            if sel:
                c.setPosition(a + len(before) + len(sel), QtGui.QTextCursor.KeepAnchor)
        c.endEditBlock()
        self.setTextCursor(c)
        self.setFocus()

    def indent(self, direction):
        c = self.textCursor()
        doc = self.document()
        first = doc.findBlock(c.selectionStart()).blockNumber()
        last = doc.findBlock(max(c.selectionStart(), c.selectionEnd() - (1 if c.hasSelection() else 0))).blockNumber()
        c.beginEditBlock()
        for i in range(first, last + 1):
            b = doc.findBlockByNumber(i)
            cur = QtGui.QTextCursor(b)
            if direction > 0:
                cur.insertText("  ")
            else:
                n = len(b.text()) - len(b.text().lstrip(" "))
                k = min(2, n)
                if k:
                    cur.setPosition(b.position())
                    cur.setPosition(b.position() + k, QtGui.QTextCursor.KeepAnchor)
                    cur.removeSelectedText()
        c.endEditBlock()

    def word_at_caret(self):
        c = self.textCursor()
        c.select(QtGui.QTextCursor.WordUnderCursor)
        return c.selectedText()

    # ------------------------------------------------------------ several cursors
    def add_next_occurrence(self):
        c = self.textCursor()
        if not c.hasSelection():
            c.select(QtGui.QTextCursor.WordUnderCursor)
            self.setTextCursor(c)
            return
        needle = c.selectedText()
        start = max([c.selectionEnd()] + [x.selectionEnd() for x in self.extra_cursors])
        flags = QtGui.QTextDocument.FindCaseSensitively
        found = self.document().find(needle, start, flags)
        if found.isNull():
            found = self.document().find(needle, 0, flags)
        taken = [c.selectionStart()] + [x.selectionStart() for x in self.extra_cursors]
        if found.isNull() or found.selectionStart() in taken:
            return
        self.extra_cursors.append(QtGui.QTextCursor(c))
        self.setTextCursor(found)
        self.centerCursor()
        self._selections()
        self.viewport().update()

    def _multi_key(self, e):
        key, t, mod = e.key(), e.text(), e.modifiers()
        paste = key == Qt.Key_V and mod & Qt.ControlModifier
        printable = bool(t) and t.isprintable() and not (mod & (Qt.ControlModifier | Qt.AltModifier))
        if key not in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Return, Qt.Key_Enter) and not printable and not paste:
            return False
        text = QtWidgets.QApplication.clipboard().text() if paste else ("\n" if key in (Qt.Key_Return, Qt.Key_Enter) else t)
        cursors = [self.textCursor()] + self.extra_cursors
        cursors[0].beginEditBlock()
        for c in cursors:
            if key == Qt.Key_Backspace:
                c.removeSelectedText() if c.hasSelection() else c.deletePreviousChar()
            elif key == Qt.Key_Delete:
                c.removeSelectedText() if c.hasSelection() else c.deleteChar()
            else:
                c.insertText(text)
        cursors[0].endEditBlock()
        seen, extra = {cursors[0].position()}, []
        for c in cursors[1:]:
            if c.position() not in seen:
                seen.add(c.position())
                extra.append(c)
        self.extra_cursors = extra
        self.setTextCursor(cursors[0])
        self._selections()
        self.viewport().update()
        return True

    def mousePressEvent(self, e):
        mod = e.modifiers()
        if e.button() == Qt.LeftButton and mod & Qt.AltModifier:
            self.extra_cursors.append(QtGui.QTextCursor(self.textCursor()))
            self.setTextCursor(self.cursorForPosition(e.pos()))
            self._selections()
            self.viewport().update()
            return
        if e.button() == Qt.LeftButton and mod & Qt.ControlModifier:
            c = self.cursorForPosition(e.pos())
            self.setTextCursor(c)
            self.ctrl_clicked.emit(c.blockNumber() + 1)
            return
        if self.extra_cursors:
            self.extra_cursors = []
            self._selections()
        super(CodeEditor, self).mousePressEvent(e)

    def paintEvent(self, e):
        super(CodeEditor, self).paintEvent(e)
        if self.extra_cursors:
            p = QtGui.QPainter(self.viewport())
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor(self.theme.pal.text))
            for c in self.extra_cursors:
                r = self.cursorRect(c)
                p.drawRect(r.x(), r.y(), 2, r.height())
            p.end()

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
