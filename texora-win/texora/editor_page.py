"""The editor screen: files, symbol bar, source, PDF preview, compile button and the tools menu."""
import io
import math
import os
import re
import subprocess
import sys
import time

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QTimer, QShortcut, run_dialog
from . import check as check_mod
from . import csvtool, textutil
from . import dialogs as dlg
from . import templates as tpl_mod
from .editor import CodeEditor, LatexHighlighter
from .preview import PdfView
from .store import LAST_PDF, is_text_file
from .strings import t

TEXT_EXT_IMG = ("png", "jpg", "jpeg", "pdf")


class FindBar(QtWidgets.QFrame):
    def __init__(self, page):
        super(FindBar, self).__init__()
        self.page = page
        self.setObjectName("bar")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        self.find = QtWidgets.QLineEdit()
        self.find.setPlaceholderText(t("find"))
        self.repl = QtWidgets.QLineEdit()
        self.repl.setPlaceholderText(t("replace"))
        self.case = QtWidgets.QCheckBox(t("match.case"))
        self.count = QtWidgets.QLabel("")
        self.count.setObjectName("muted")
        prev = QtWidgets.QToolButton()
        prev.setText("\u2191")
        nxt = QtWidgets.QToolButton()
        nxt.setText("\u2193")
        one = QtWidgets.QPushButton(t("replace"))
        allb = QtWidgets.QPushButton(t("replace.all"))
        close = QtWidgets.QToolButton()
        close.setText("\u2715")
        for w in (self.find, self.repl, self.case, self.count, prev, nxt, one, allb, close):
            lay.addWidget(w)
        self.index = 0
        self.find.textChanged.connect(self._changed)
        self.case.toggled.connect(self._changed)
        self.find.returnPressed.connect(lambda: self.step(1))
        prev.clicked.connect(lambda: self.step(-1))
        nxt.clicked.connect(lambda: self.step(1))
        one.clicked.connect(self.replace_one)
        allb.clicked.connect(self.replace_all)
        close.clicked.connect(self.hide)
        self.hide()

    def matches(self):
        q = self.find.text()
        if not q:
            return []
        text = self.page.editor.toPlainText()
        flags = 0 if self.case.isChecked() else re.IGNORECASE
        return [m.start() for m in re.finditer(re.escape(q), text, flags)]

    def _changed(self, *_):
        self.index = 0
        self._show()

    def _show(self):
        ms = self.matches()
        self.count.setText("%d / %d" % (min(self.index + 1, len(ms)), len(ms)) if ms else "0")
        self.page.editor.set_matches(ms, len(self.find.text()), self.index if ms else -1)
        if ms:
            c = self.page.editor.textCursor()
            c.setPosition(ms[self.index % len(ms)])
            self.page.editor.setTextCursor(c)
            self.page.editor.centerCursor()

    def step(self, d):
        ms = self.matches()
        if ms:
            self.index = (self.index + d) % len(ms)
            self._show()

    def replace_one(self):
        ms = self.matches()
        if not ms:
            return
        at = ms[self.index % len(ms)]
        c = self.page.editor.textCursor()
        c.setPosition(at)
        c.setPosition(at + len(self.find.text()), QtGui.QTextCursor.KeepAnchor)
        c.insertText(self.repl.text())
        self._show()

    def replace_all(self):
        q = self.find.text()
        if not q:
            return
        flags = 0 if self.case.isChecked() else re.IGNORECASE
        text = self.page.editor.toPlainText()
        new = re.sub(re.escape(q), lambda m: self.repl.text(), text, flags=flags)
        c = self.page.editor.textCursor()
        c.beginEditBlock()
        c.select(QtGui.QTextCursor.Document)
        c.insertText(new)
        c.endEditBlock()
        self._show()

    def open(self):
        self.show()
        self.find.setFocus()
        self.find.selectAll()
        sel = self.page.editor.textCursor().selectedText()
        if sel and "\u2029" not in sel:
            self.find.setText(sel)

    def hideEvent(self, e):
        super(FindBar, self).hideEvent(e)
        self.page.editor.set_matches([], 0, -1)


class EditorPage(QtWidgets.QWidget):
    closed = Signal()

    def __init__(self, project, store, history, prefs, theme, engine, parent=None):
        super(EditorPage, self).__init__(parent)
        self.setObjectName("page")
        self.project, self.store, self.history, self.prefs, self.theme, self.engine = project, store, history, prefs, theme, engine
        self.meta = store.meta(project)
        self.docs = {}
        self.current = ""
        self.files = []
        self.errors = []
        self.log_text = ""
        self.compiling = False
        self.compile_start = 0.0
        self.snippets = list(prefs.get("snippets") or [])
        self.group_key = "sym.math"
        self.pdf_path = None

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._top_bar())
        self.tabs_area = QtWidgets.QScrollArea()
        self.tabs_area.setFixedHeight(46)
        self.tabs_area.setWidgetResizable(True)
        self.tabs_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabs_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabs_host = QtWidgets.QWidget()
        self.tabs_lay = QtWidgets.QHBoxLayout(self.tabs_host)
        self.tabs_lay.setContentsMargins(10, 6, 10, 6)
        self.tabs_lay.setSpacing(6)
        self.tabs_area.setWidget(self.tabs_host)
        outer.addWidget(self.tabs_area)
        self.editor = CodeEditor(theme)
        self.findbar = FindBar(self)
        outer.addWidget(self.findbar)
        self.symbol_bar = self._symbol_bar()
        outer.addWidget(self.symbol_bar)

        self.split = QtWidgets.QSplitter(Qt.Horizontal)
        left = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        ll.addWidget(self.editor, 1)
        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(170)
        self.log_box.hide()
        ll.addWidget(self.log_box)
        self.split.addWidget(left)
        self.preview = PdfView(theme)
        self.split.addWidget(self.preview)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        outer.addWidget(self.split, 1)
        outer.addWidget(self._bottom_bar())

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.flush)
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._tick)
        self.editor.caret_info.connect(self._caret)
        self.engine.finished.connect(self._compiled)
        self.engine.status.connect(self._engine_status)
        self._apply_prefs()
        self.refresh_files()
        self.open_file(self.meta.main if self.meta.main in self.files else (self.files[0] if self.files else ""))
        last = os.path.join(project.path, LAST_PDF)
        if os.path.isfile(last):
            self.pdf_path = last
            self.preview.load(last)
        QShortcut(QtGui.QKeySequence("Ctrl+B"), self, activated=self.compile)
        QShortcut(QtGui.QKeySequence("F5"), self, activated=self.compile)
        QShortcut(QtGui.QKeySequence("Ctrl+F"), self, activated=self.findbar.open)
        QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.flush)

    # ------------------------------------------------------------ building the screen
    def _top_bar(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("bar")
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)
        back = QtWidgets.QToolButton()
        back.setText("\u2190")
        back.setToolTip(t("back"))
        back.clicked.connect(self.close_project)
        lay.addWidget(back)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(0)
        self.title = QtWidgets.QLabel(self.project.name)
        self.title.setObjectName("h2")
        self.status = QtWidgets.QLabel("")
        self.status.setObjectName("muted")
        col.addWidget(self.title)
        col.addWidget(self.status)
        lay.addLayout(col, 1)
        find = QtWidgets.QToolButton()
        find.setText("\u2315")
        find.setToolTip(t("find") + "  (Ctrl+F)")
        find.clicked.connect(lambda: self.findbar.open())
        lay.addWidget(find)
        more = QtWidgets.QToolButton()
        more.setText("\u22ee")
        more.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.menu = QtWidgets.QMenu(more)
        self.menu.aboutToShow.connect(self._fill_menu)
        more.setMenu(self.menu)
        lay.addWidget(more)
        return bar

    def _fill_menu(self):
        m = self.menu
        m.clear()
        m.addAction(t("comment"), self.editor.toggle_comment)
        m.addAction(t("insert.tools"), self.tools)
        if self.bib_keys():
            m.addAction(t("insert.citation"), self.cite_dialog)
        m.addAction(t("new.file"), self.new_file)
        m.addAction(t("import.file"), self.add_file_from_disk)
        m.addSeparator()
        m.addAction(t("engine.pdftex") if self.meta.engine == "xetex" else t("engine.xetex"), self.toggle_engine)
        m.addAction(t("outline"), self.outline_dialog)
        m.addAction(t("history"), self.history_dialog)
        m.addAction(t("snippet.save"), self.save_snippet)
        m.addAction(t("view.options"), self.view_dialog)
        m.addSeparator()
        a = m.addAction(t("save.pdf"), self.save_pdf)
        a.setEnabled(bool(self.pdf_path))
        b = m.addAction(t("share.pdf"), self.open_pdf)
        b.setEnabled(bool(self.pdf_path))
        m.addAction(t("export.project"), self.export_zip)
        m.addAction("Open project folder", self.open_folder)

    def _symbol_bar(self):
        w = QtWidgets.QFrame()
        w.setObjectName("bar")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(4)
        self.groups = tpl_mod.symbol_groups()
        row = QtWidgets.QScrollArea()
        row.setFixedHeight(38)
        row.setWidgetResizable(True)
        row.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        row.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(host)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        self.group_buttons = {}
        for g in self.groups + [{"key": "sym.mine", "items": []}]:
            b = QtWidgets.QPushButton(t(g["key"]))
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(g["key"] == self.group_key)
            b.clicked.connect(lambda _=False, k=g["key"]: self.show_group(k))
            self.group_buttons[g["key"]] = b
            hl.addWidget(b)
        hl.addStretch(1)
        row.setWidget(host)
        v.addWidget(row)
        self.sym_scroll = QtWidgets.QScrollArea()
        self.sym_scroll.setFixedHeight(56)
        self.sym_scroll.setWidgetResizable(True)
        self.sym_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sym_host = QtWidgets.QWidget()
        self.sym_lay = QtWidgets.QHBoxLayout(self.sym_host)
        self.sym_lay.setContentsMargins(0, 0, 0, 0)
        self.sym_lay.setSpacing(4)
        self.sym_scroll.setWidget(self.sym_host)
        v.addWidget(self.sym_scroll)
        self.show_group(self.group_key)
        return w

    def show_group(self, key):
        self.group_key = key
        for k, b in self.group_buttons.items():
            b.setChecked(k == key)
        while self.sym_lay.count():
            w = self.sym_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        if key == "sym.mine":
            items = self.snippets
            if not items:
                lab = QtWidgets.QLabel(t("snippet.empty"))
                lab.setObjectName("muted")
                self.sym_lay.addWidget(lab)
        else:
            items = next((g["items"] for g in self.groups if g["key"] == key), [])
        for label, text in items:
            b = QtWidgets.QPushButton(label if len(label) < 16 else label[:15] + "\u2026")
            b.setObjectName("sym")
            b.setToolTip(text.replace("\u2038", ""))
            b.clicked.connect(lambda _=False, s=text: self.editor.insert_snippet(s))
            if key == "sym.mine":
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(lambda pos, i=len(self.sym_lay) , lbl=label: self._snippet_menu(lbl))
            self.sym_lay.addWidget(b)
        self.sym_lay.addStretch(1)

    def _snippet_menu(self, label):
        m = QtWidgets.QMenu(self)
        m.addAction(t("delete"), lambda: self._delete_snippet(label))
        m.exec_(QtGui.QCursor.pos()) if hasattr(m, "exec_") else m.exec(QtGui.QCursor.pos())

    def _delete_snippet(self, label):
        if dlg.confirm(self, t("snippet.delete")):
            self.snippets = [s for s in self.snippets if s[0] != label]
            self.prefs.set("snippets", self.snippets)
            self.show_group("sym.mine")

    def _bottom_bar(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("bottombar")
        v = QtWidgets.QVBoxLayout(bar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        v.addWidget(self.progress)
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(12, 6, 12, 6)
        self.caret = QtWidgets.QLabel("Ln 1, Col 1")
        self.caret.setObjectName("muted")
        row.addWidget(self.caret)
        self.words = QtWidgets.QLabel("")
        self.words.setObjectName("muted")
        row.addWidget(self.words)
        row.addStretch(1)
        self.log_btn = QtWidgets.QPushButton(t("log"))
        self.log_btn.setCheckable(True)
        self.log_btn.toggled.connect(self.log_box.setVisible)
        row.addWidget(self.log_btn)
        undo = QtWidgets.QToolButton()
        undo.setText("\u21b6")
        undo.setToolTip(t("undo"))
        undo.clicked.connect(lambda: self.editor.undo())
        redo = QtWidgets.QToolButton()
        redo.setText("\u21b7")
        redo.setToolTip(t("redo"))
        redo.clicked.connect(lambda: self.editor.redo())
        row.addWidget(undo)
        row.addWidget(redo)
        self.compile_btn = QtWidgets.QPushButton("\u25b6  " + t("compile") + "   Ctrl+B")
        self.compile_btn.setObjectName("primary")
        self.compile_btn.clicked.connect(self.compile)
        row.addWidget(self.compile_btn)
        v.addLayout(row)
        return bar

    def _apply_prefs(self):
        p = self.prefs
        self.editor.apply_theme(self.theme, int(p.get("editor_size")))
        self.editor.set_show_numbers(bool(p.get("line_numbers")))
        self.editor.set_wrap(bool(p.get("wrap")))
        self.editor.auto_pairs = bool(p.get("auto_pairs"))
        self.symbol_bar.setVisible(bool(p.get("symbol_bar")))

    # ------------------------------------------------------------ files
    def refresh_files(self):
        self.files = self.store.files(self.project, self.meta.main)
        while self.tabs_lay.count():
            w = self.tabs_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for f in self.files:
            b = QtWidgets.QPushButton(("\u2605 " if f == self.meta.main else "") + f)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(f == self.current)
            b.clicked.connect(lambda _=False, n=f: self.open_file(n))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda pos, n=f: self._file_menu(n))
            self.tabs_lay.addWidget(b)
        add = QtWidgets.QToolButton()
        add.setText("+")
        add.setToolTip(t("new.file"))
        add.clicked.connect(self.new_file)
        self.tabs_lay.addWidget(add)
        self.tabs_lay.addStretch(1)

    def _file_menu(self, name):
        m = QtWidgets.QMenu(self)
        if is_text_file(name) and name != self.meta.main and name.endswith(".tex"):
            m.addAction(t("set.main"), lambda: self.set_main(name))
        m.addAction(t("rename"), lambda: self.rename_file(name))
        if name != self.meta.main:
            m.addAction(t("delete"), lambda: self.delete_file(name))
        m.exec_(QtGui.QCursor.pos()) if hasattr(m, "exec_") else m.exec(QtGui.QCursor.pos())

    def _doc_for(self, name):
        if name not in self.docs:
            d = QtGui.QTextDocument()
            d.setDocumentLayout(QtWidgets.QPlainTextDocumentLayout(d))
            try:
                with io.open(os.path.join(self.project.path, name), encoding="utf-8", errors="replace") as f:
                    d.setPlainText(f.read())
            except OSError:
                d.setPlainText("")
            d.setModified(False)
            d.setUndoRedoEnabled(True)
            hl = LatexHighlighter(d, self.theme)
            d.contentsChanged.connect(self._changed)
            self.docs[name] = (d, hl)
        return self.docs[name][0]

    def open_file(self, name):
        if not name:
            return
        if not is_text_file(name):
            self._open_external(name)
            return
        self.current = name
        d = self._doc_for(name)
        self.editor.setDocument(d)
        self.editor.apply_theme(self.theme, int(self.prefs.get("editor_size")))
        self.editor._update_gutter_width()
        for i in range(self.tabs_lay.count()):
            w = self.tabs_lay.itemAt(i).widget()
            if isinstance(w, QtWidgets.QPushButton):
                w.setChecked(w.text().replace("\u2605 ", "") == name)
        self.status.setText(name)
        self._words()
        self.editor.setFocus()

    def _open_external(self, name):
        path = os.path.join(self.project.path, name)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: B018 - opens the picture or PDF in the program Windows uses for it
        else:
            subprocess.Popen(["xdg-open", path])

    def _changed(self):
        self.save_timer.start(700)
        self._words_timer()

    def _words_timer(self):
        QTimer.singleShot(400, self._words)

    def _words(self):
        if self.current:
            self.words.setText("%d %s" % (textutil.count_words(self.editor.toPlainText()), t("words")))

    def _caret(self, line, col):
        self.caret.setText("Ln %d, Col %d" % (line, col))

    def flush(self):
        for name, (d, _) in self.docs.items():
            if d.isModified():
                with io.open(os.path.join(self.project.path, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(d.toPlainText())
                d.setModified(False)

    def text_of(self, name):
        if name in self.docs:
            return self.docs[name][0].toPlainText()
        try:
            with io.open(os.path.join(self.project.path, name), encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    def new_file(self):
        n = dlg.ask_text(self, t("new.file"), t("file.name"), "chapter1.tex")
        if not n:
            return
        if "." not in n:
            n += ".tex"
        p = os.path.join(self.project.path, n)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p):
            body = "@article{key2024,\n  author  = {Author},\n  title   = {Title},\n  journal = {Journal},\n  year    = {2024}\n}\n" if n.endswith(".bib") else ""
            with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
        self.refresh_files()
        self.open_file(n)

    def add_file_from_disk(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("import.file"))
        if path:
            with open(path, "rb") as f:
                n = self.store.import_file(self.project, os.path.basename(path), f.read())
            self.refresh_files()
            if is_text_file(n):
                self.open_file(n)

    def rename_file(self, name):
        n = dlg.ask_text(self, t("rename"), t("file.name"), name)
        if not n or n == name or os.path.exists(os.path.join(self.project.path, n)):
            return
        self.flush()
        os.makedirs(os.path.dirname(os.path.join(self.project.path, n)), exist_ok=True)
        os.rename(os.path.join(self.project.path, name), os.path.join(self.project.path, n))
        self.docs.pop(name, None)
        if self.meta.main == name:
            self.meta.main = n
            self.store.save_meta(self.project, self.meta)
        self.refresh_files()
        if self.current == name:
            self.open_file(n)

    def delete_file(self, name):
        if not dlg.confirm(self, "%s \"%s\"?" % (t("delete"), name)):
            return
        os.remove(os.path.join(self.project.path, name))
        self.docs.pop(name, None)
        self.refresh_files()
        if self.current == name:
            self.open_file(self.meta.main)

    def set_main(self, name):
        self.meta.main = name
        self.store.save_meta(self.project, self.meta)
        self.refresh_files()

    def toggle_engine(self):
        self.meta.engine = "pdftex" if self.meta.engine == "xetex" else "xetex"
        self.store.save_meta(self.project, self.meta)

    # ------------------------------------------------------------ menu actions
    def bib_keys(self):
        keys = []
        for f in self.files:
            if f.endswith(".bib"):
                keys += check_mod.bib_keys(self.text_of(f))
        return keys

    def cite_dialog(self):
        keys = self.bib_keys()
        item, ok = QtWidgets.QInputDialog.getItem(self, t("insert.citation"), t("insert.citation"), keys, 0, False)
        if ok:
            self.editor.insert_snippet("\\cite{%s}" % item)

    def outline_dialog(self):
        stats = ["%d %s  \u00b7  %s" % (textutil.count_words(self.editor.toPlainText()), t("words"), self.current),
                 "%s: %d" % (t("words.all"), sum(textutil.count_words(self.text_of(f)) for f in self.files if f.endswith(".tex")))]
        if self.pdf_path and self.preview.doc is not None:
            stats.append("%s: %d" % (t("pdf.pages"), self.preview.doc.page_count))
        run_dialog(dlg.OutlineDialog(self, textutil.outline(self.editor.toPlainText()), stats, self.editor.go_to_line))

    def history_dialog(self):
        versions = self.history.list(self.project.name, self.current)

        def restore(v):
            c = self.editor.textCursor()
            c.beginEditBlock()
            c.select(QtGui.QTextCursor.Document)
            c.insertText(self.history.read(v))
            c.endEditBlock()
        run_dialog(dlg.HistoryDialog(self, versions, self.history.read, restore))

    def save_snippet(self):
        d = dlg.SnippetDialog(self, self.editor.textCursor().selectedText().replace("\u2029", "\n"))
        if run_dialog(d) and d.label.text().strip() and d.body.toPlainText():
            self.snippets.append([d.label.text().strip(), d.body.toPlainText()])
            self.prefs.set("snippets", self.snippets)
            self.show_group("sym.mine")

    def view_dialog(self):
        p = self.prefs
        d = dlg.ViewDialog(self, int(p.get("editor_size")), bool(p.get("line_numbers")), bool(p.get("wrap")),
                           bool(p.get("auto_pairs")), bool(p.get("symbol_bar")))
        if run_dialog(d):
            for k, v in (("editor_size", d.size.value()), ("line_numbers", d.numbers.isChecked()), ("wrap", d.wrap.isChecked()),
                         ("auto_pairs", d.pairs.isChecked()), ("symbol_bar", d.bar.isChecked())):
                p.d[k] = v
            p.save()
            self._apply_prefs()

    def save_pdf(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, t("save.pdf"), self.project.name + ".pdf", "PDF (*.pdf)")
        if path and self.pdf_path:
            import shutil
            shutil.copyfile(self.pdf_path, path)

    def open_pdf(self):
        if self.pdf_path:
            self._open_external(LAST_PDF)

    def export_zip(self):
        self.flush()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, t("export.project"), self.project.name + ".zip", "ZIP (*.zip)")
        if path:
            self.store.export_zip(self.project, path)

    def open_folder(self):
        if sys.platform == "win32":
            os.startfile(self.project.path)  # noqa: B018
        else:
            subprocess.Popen(["xdg-open", self.project.path])

    # ------------------------------------------------------------ insert and check
    def ensure_package(self, pkg, line=None):
        line = line or "\\usepackage{%s}" % pkg
        main = self.meta.main
        text = self.text_of(main)
        if re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b%s\b[^}]*\}" % re.escape(pkg), text):
            return
        dc = text.find("\\documentclass")
        if dc < 0:
            return
        eol = text.find("\n", dc)
        at = len(text) if eol < 0 else eol + 1
        added = ("\n" if eol < 0 else "") + line + "\n"
        if main in self.docs:
            d = self.docs[main][0]
            c = QtGui.QTextCursor(d)
            c.setPosition(at)
            c.insertText(added)
        else:
            with io.open(os.path.join(self.project.path, main), "w", encoding="utf-8", newline="\n") as f:
                f.write(text[:at] + added + text[at:])

    def tools(self):
        d = dlg.ToolsDialog(self)
        if not run_dialog(d) or not d.chosen:
            return
        {"csv": self.tool_csv, "picture": self.tool_picture, "doi": self.tool_doi, "style": self.tool_style,
         "check": self.tool_check}[d.chosen]()

    def tool_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("tool.csv"), "", "CSV (*.csv *.txt *.tsv);;All (*)")
        if not path:
            return
        with open(path, "rb") as f:
            data = csvtool.parse(f.read(1000000).decode("utf-8", "replace"))
        if not data.header:
            QtWidgets.QMessageBox.information(self, "TeXora", t("csv.bad"))
            return
        d = dlg.CsvDialog(self, data)
        if run_dialog(d) and d.result_code:
            if d.needs_plot:
                self.ensure_package("pgfplots", "\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.17}")
            else:
                self.ensure_package("booktabs")
            self.editor.insert_snippet(d.result_code)

    def tool_picture(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("tool.picture"), "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.pdf)")
        if not path:
            return
        name, data = self._prepare_picture(path)
        if data is None:
            QtWidgets.QMessageBox.information(self, "TeXora", t("picture.bad"))
            return
        stored = self.store.import_file(self.project, "figures/" + name, data)
        self.refresh_files()
        self.ensure_package("graphicx")
        label = os.path.splitext(os.path.basename(stored))[0]
        self.editor.insert_snippet("\\begin{figure}[ht]\n  \\centering\n  \\includegraphics[width=0.8\\linewidth]{%s}\n  \\caption{\u2038}\n  \\label{fig:%s}\n\\end{figure}\n" % (stored, label))

    @staticmethod
    def _prepare_picture(path):
        ext = os.path.splitext(path)[1][1:].lower()
        base = re.sub(r"[^A-Za-z0-9_-]", "_", os.path.splitext(os.path.basename(path))[0]) or "picture"
        with open(path, "rb") as f:
            raw = f.read()
        if ext == "pdf":
            return base + ".pdf", raw
        img = QtGui.QImage()
        if not img.loadFromData(raw):
            return None, None
        big = max(img.width(), img.height()) > 2600 or len(raw) > 3000000
        if ext in ("png", "jpg", "jpeg") and not big:
            return base + "." + ("jpg" if ext == "jpeg" else ext), raw
        if max(img.width(), img.height()) > 2600:
            img = img.scaled(2600, 2600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        png = ext == "png"
        img.save(buf, "PNG" if png else "JPG", -1 if png else 90)
        return base + (".png" if png else ".jpg"), bytes(buf.data())

    def tool_doi(self):
        d = dlg.DoiDialog(self)
        if run_dialog(d) and d.entry:
            bib = next((f for f in self.files if f.endswith(".bib")), "refs.bib")
            path = os.path.join(self.project.path, bib)
            existing = ""
            if os.path.exists(path):
                existing = self.text_of(bib)
            key = re.match(r"^@\w+\{([^,]+),", d.entry).group(1)
            entry = d.entry
            keys = check_mod.bib_keys(existing)
            if key in keys:
                n = 0
                while key + chr(ord("a") + n) in keys:
                    n += 1
                entry = re.sub(r"^(@\w+\{)[^,]+,", lambda m: m.group(1) + key + chr(ord("a") + n) + ",", d.entry)
                key = key + chr(ord("a") + n)
            if bib in self.docs:
                doc = self.docs[bib][0]
                c = QtGui.QTextCursor(doc)
                c.movePosition(QtGui.QTextCursor.End)
                c.insertText(("\n" if existing and not existing.endswith("\n\n") else "") + entry)
            else:
                with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(existing + ("\n" if existing and not existing.endswith("\n\n") else "") + entry)
            self.refresh_files()
            self.editor.insert_snippet("\\cite{%s}" % key)

    def tool_style(self):
        d = dlg.StyleDialog(self)
        if run_dialog(d) and d.chosen:
            main = self.meta.main
            text = self.text_of(main)
            rx = re.compile(r"\\bibliographystyle\{[^}]*\}")
            if rx.search(text):
                new = rx.sub(lambda m: "\\bibliographystyle{%s}" % d.chosen, text)
            elif "\\bibliography{" in text:
                new = text.replace("\\bibliography{", "\\bibliographystyle{%s}\n\\bibliography{" % d.chosen, 1)
            else:
                return
            self._replace_text(main, new)

    def _replace_text(self, name, new):
        if name in self.docs:
            doc = self.docs[name][0]
            c = QtGui.QTextCursor(doc)
            c.beginEditBlock()
            c.select(QtGui.QTextCursor.Document)
            c.insertText(new)
            c.endEditBlock()
        else:
            with io.open(os.path.join(self.project.path, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(new)

    def tool_check(self):
        self.flush()
        tex = dict((f, self.text_of(f)) for f in self.files if f.endswith(".tex"))
        bib = dict((f, self.text_of(f)) for f in self.files if f.endswith(".bib"))
        issues = check_mod.run(tex, bib, set(self.files), self.meta.main, self.log_text)
        run_dialog(dlg.CheckDialog(self, issues, self.go_to))

    def go_to(self, file, line):
        if file and file != self.current and file in self.files and is_text_file(file):
            self.open_file(file)
        if line:
            self.editor.go_to_line(line)

    # ------------------------------------------------------------ compiling
    def compile(self):
        if self.compiling:
            return
        self.flush()
        files = []
        for root, _, names in os.walk(self.project.path):
            for n in names:
                if n.startswith("."):
                    continue
                full = os.path.join(root, n)
                with open(full, "rb") as f:
                    files.append((os.path.relpath(full, self.project.path).replace("\\", "/"), f.read()))
        for n, data in files:
            if is_text_file(n):
                try:
                    self.history.snapshot(self.project.name, n, data.decode("utf-8"))
                except Exception:
                    pass
        self.compiling = True
        self.compile_start = time.time()
        self.compile_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.status.setText(t("compiling"))
        self.progress_timer.start(500)
        driver = "pdftex_bibtex8" if self.meta.engine == "pdftex" else "xetex_bibtex8_dvipdfmx"
        self.engine.compile(files, self.meta.main, driver)

    def _expected_ms(self):
        return min(240000, max(5000, int((self.prefs.get("compile_ms") or {}).get(self.meta.engine, 40000))))

    def _tick(self):
        x = (time.time() - self.compile_start) * 1000.0 / self._expected_ms()
        p = min(0.95, 1 - math.exp(-1.6 * x))
        self.progress.setValue(int(p * 1000))
        self.status.setText("%s %d%%" % (t("compiling").rstrip("\u2026"), int(p * 100)))

    def _engine_status(self, s):
        if not self.compiling and s == "starting":
            self.status.setText(t("engine.start"))

    def _compiled(self, ok, code, log, pdf):
        if not self.compiling:
            return
        self.compiling = False
        self.progress_timer.stop()
        self.progress.hide()
        self.compile_btn.setEnabled(True)
        self.log_text = log
        self.errors = textutil.parse_errors(log)
        self.log_box.setPlainText("\n".join(["%s%s: %s" % (e.file + ":" if e.file else "", e.line or "?", e.message) for e in self.errors] + ["", log[-6000:]]))
        if ok and pdf:
            ms = int((time.time() - self.compile_start) * 1000)
            d = dict(self.prefs.get("compile_ms") or {})
            d[self.meta.engine] = ms
            self.prefs.set("compile_ms", d)
            path = os.path.join(self.project.path, LAST_PDF)
            with open(path, "wb") as f:
                f.write(pdf)
            self.pdf_path = path
            self.preview.load(path)
            self.status.setText(t("ok"))
        else:
            self.status.setText(t("failed") + (" \u00b7 %d %s" % (len(self.errors), t("errors")) if self.errors else ""))
            self.log_btn.setChecked(True)
            if self.errors:
                e = self.errors[0]
                self.go_to(e.file, e.line)

    # ------------------------------------------------------------ leaving
    def close_project(self):
        self.flush()
        self.closed.emit()

    def shutdown(self):
        self.flush()
        try:
            self.engine.finished.disconnect(self._compiled)
        except Exception:
            pass
