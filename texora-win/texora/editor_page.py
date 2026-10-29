"""The editor screen, laid out like a desktop LaTeX editor: tool bar, files and structure on the side, source and PDF
side by side, messages and formula preview below, status bar."""
import base64
import io
import math
import os
import re
import shutil
import subprocess
import sys
import time

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QTimer, QShortcut, QAction, run_dialog
from . import check as check_mod
from . import csvtool, textutil
from . import dialogs as dlg
from . import templates as tpl_mod
from .editor import CodeEditor, LatexHighlighter
from .findbar import FindBar, PdfSearchBar, project_hits
from .formula import FormulaPanel
from .icons import icon
from .preview import PdfView
from .store import is_text_file
from .strings import t

_LABEL = re.compile(r"\\label\{([^}]*)\}")


def _pdf_name(meta):
    return os.path.splitext(os.path.basename(meta.main))[0] + ".pdf"


class EditorPage(QtWidgets.QMainWindow):
    closed = Signal()
    title_changed = Signal(str)

    def __init__(self, project, store, history, prefs, theme, engine, parent=None):
        super(EditorPage, self).__init__(parent, Qt.Widget)
        self.setObjectName("page")
        self.setLayoutDirection(Qt.LeftToRight)      # source and PDF keep their usual sides, also with a Persian interface
        self.project, self.store, self.history, self.prefs, self.theme, self.engine = project, store, history, prefs, theme, engine
        self.meta = store.meta(project)
        self.docs = {}
        self.open_names = []
        self.current = ""
        self.files = []
        self.errors = []
        self.log_text = ""
        self.compiling = False
        self.compile_start = 0.0
        self.dirty_since_compile = False
        self.snippets = list(prefs.get("snippets") or [])
        self.group_key = "sym.math"
        self.pdf_path = None
        self.ic = theme.pal.text
        self._labels_cache = (0, [])

        self._make_central()
        self._make_docks()
        self._make_actions()
        self._make_toolbar()
        self._make_statusbar()
        self.setDockNestingEnabled(True)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.flush)
        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self._typing_compile)
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._tick)
        self.struct_timer = QTimer(self)
        self.struct_timer.setSingleShot(True)
        self.struct_timer.timeout.connect(self.update_structure)
        self.formula_timer = QTimer(self)
        self.formula_timer.setSingleShot(True)
        self.formula_timer.timeout.connect(self.update_formula)
        self.editor.caret_info.connect(self._caret)
        self.editor.ctrl_clicked.connect(self.to_pdf)
        self.editor.completion_provider = self._completion_data
        self.preview.page_clicked.connect(self.to_source)
        self.preview.document_loaded.connect(self.fill_pages)
        self.engine.finished.connect(self._compiled)
        self.engine.status.connect(self._engine_status)

        self._apply_prefs()
        self.refresh_files()
        self.open_file(self.meta.main if self.meta.main in self.files else next((f for f in self.files if is_text_file(f)), ""))
        pdf = os.path.join(project.path, _pdf_name(self.meta))
        if os.path.isfile(pdf):
            self.pdf_path = pdf
            self.preview.load(pdf)
        self._restore_layout()
        self.setAcceptDrops(False)

    # ------------------------------------------------------------ central widget: tabs, source and PDF
    def _make_central(self):
        self.editor = CodeEditor(self.theme)
        self.findbar = FindBar(self)
        self.tabbar = QtWidgets.QTabBar()
        self.tabbar.setDocumentMode(True)
        self.tabbar.setTabsClosable(True)
        self.tabbar.setMovable(True)
        self.tabbar.setExpanding(False)
        self.tabbar.setDrawBase(False)
        self.tabbar.currentChanged.connect(self._tab_changed)
        self.tabbar.tabCloseRequested.connect(self._tab_close)
        self.symbol_bar = self._symbol_bar()
        left = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        ll.addWidget(self.tabbar)
        ll.addWidget(self.findbar)
        ll.addWidget(self.symbol_bar)
        ll.addWidget(self.editor, 1)
        self.preview = PdfView(self.theme)
        self.pdf_search = PdfSearchBar(self.preview)
        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self.pdf_search)
        rl.addWidget(self.preview, 1)
        self.split = QtWidgets.QSplitter(Qt.Horizontal)
        self.split.addWidget(left)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setChildrenCollapsible(False)
        self.setCentralWidget(self.split)

    def _symbol_bar(self):
        w = QtWidgets.QFrame()
        w.setObjectName("bar")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(6, 3, 6, 3)
        v.setSpacing(3)
        self.groups = tpl_mod.symbol_groups()
        row = QtWidgets.QScrollArea()
        row.setFixedHeight(34)
        row.setWidgetResizable(True)
        row.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        row.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(host)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(3)
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
        self.sym_scroll.setFixedHeight(48)
        self.sym_scroll.setWidgetResizable(True)
        self.sym_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sym_host = QtWidgets.QWidget()
        self.sym_lay = QtWidgets.QHBoxLayout(self.sym_host)
        self.sym_lay.setContentsMargins(0, 0, 0, 0)
        self.sym_lay.setSpacing(3)
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
                b.customContextMenuRequested.connect(lambda pos, lbl=label: self._snippet_menu(lbl))
            self.sym_lay.addWidget(b)
        self.sym_lay.addStretch(1)

    def _snippet_menu(self, label):
        m = QtWidgets.QMenu(self)
        m.addAction(t("delete"), lambda: self._delete_snippet(label))
        self._popup(m)

    def _delete_snippet(self, label):
        if dlg.confirm(self, t("snippet.delete")):
            self.snippets = [s for s in self.snippets if s[0] != label]
            self.prefs.set("snippets", self.snippets)
            self.show_group("sym.mine")

    @staticmethod
    def _popup(menu):
        pos = QtGui.QCursor.pos()
        menu.exec_(pos) if hasattr(menu, "exec_") else menu.exec(pos)

    # ------------------------------------------------------------ docks
    def _dock(self, key, title, widget, area):
        d = QtWidgets.QDockWidget(title, self)
        d.setObjectName("dock_" + key)
        d.setWidget(widget)
        d.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(area, d)
        return d

    def _make_docks(self):
        # files
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemDoubleClicked.connect(self._tree_open)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.dock_files = self._dock("files", t("p.files"), self.tree, Qt.LeftDockWidgetArea)
        # structure
        self.struct = QtWidgets.QTreeWidget()
        self.struct.setHeaderHidden(True)
        self.struct.setIndentation(12)
        self.struct.itemActivated.connect(lambda it, c: self.editor.go_to_line(it.data(0, Qt.UserRole)))
        self.struct.itemClicked.connect(lambda it, c: self.editor.go_to_line(it.data(0, Qt.UserRole)))
        self.dock_struct = self._dock("structure", t("p.structure"), self.struct, Qt.LeftDockWidgetArea)
        # pages
        self.pages = QtWidgets.QListWidget()
        self.pages.setIconSize(QtCore.QSize(110, 150))
        self.pages.setSpacing(4)
        self.pages.setViewMode(QtWidgets.QListView.ListMode)
        self.pages.itemClicked.connect(lambda it: self.preview.go_to_page(it.data(Qt.UserRole)))
        self.dock_pages = self._dock("pages", t("p.pages"), self.pages, Qt.LeftDockWidgetArea)
        self.tabifyDockWidget(self.dock_files, self.dock_struct)
        self.tabifyDockWidget(self.dock_struct, self.dock_pages)
        self.dock_files.raise_()
        # messages: errors, log, search results
        self.msgs = QtWidgets.QTabWidget()
        self.msgs.setDocumentMode(True)
        self.err_list = QtWidgets.QListWidget()
        self.err_list.itemActivated.connect(self._error_activated)
        self.err_list.itemClicked.connect(self._error_activated)
        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.search_list = QtWidgets.QTreeWidget()
        self.search_list.setHeaderHidden(True)
        self.search_list.itemActivated.connect(self._search_activated)
        self.search_list.itemClicked.connect(self._search_activated)
        self.msgs.addTab(self.err_list, t("p.errors"))
        self.msgs.addTab(self.log_box, t("p.rawlog"))
        self.msgs.addTab(self.search_list, t("p.search"))
        self.dock_msgs = self._dock("messages", t("p.log"), self.msgs, Qt.BottomDockWidgetArea)
        # formula
        self.formula = FormulaPanel(self.katex_dir_for(), self.theme)
        self.dock_formula = self._dock("formula", t("p.formula"), self.formula, Qt.BottomDockWidgetArea)
        self.tabifyDockWidget(self.dock_msgs, self.dock_formula)
        self.dock_formula.raise_()
        self.dock_formula.visibilityChanged.connect(lambda v: v and self.update_formula())
        self.dock_msgs.hide()
        self.resizeDocks([self.dock_files, self.dock_formula], [230, 150], Qt.Horizontal)
        self.resizeDocks([self.dock_formula], [150], Qt.Vertical)

    def katex_dir_for(self):
        from .app import asset_root
        return os.path.join(os.path.dirname(asset_root()), "katex")

    # ------------------------------------------------------------ actions
    def _act(self, text, ic=None, keys=None, fn=None, checkable=False, checked=False, tip=None):
        a = QAction(text, self)
        if ic:
            a.setIcon(icon(ic, self.ic))
        if keys:
            a.setShortcuts([QtGui.QKeySequence(k) for k in (keys if isinstance(keys, (list, tuple)) else [keys])])
            a.setToolTip("%s  (%s)" % (tip or text.replace("&", "").rstrip("\u2026"), a.shortcut().toString(QtGui.QKeySequence.NativeText)))
        else:
            a.setToolTip(tip or text.replace("&", "").rstrip("\u2026"))
        if checkable:
            a.setCheckable(True)
            a.setChecked(checked)
            if fn:
                a.toggled.connect(fn)
        elif fn:
            a.triggered.connect(lambda _=False, f=fn: f())
        self.addAction(a)
        return a

    def _make_actions(self):
        ed, p = self.editor, self.prefs
        A = self._act
        self.a_new_file = A(t("a.new.file"), "new", "Ctrl+Shift+N", self.new_file)
        self.a_new_folder = A(t("a.new.folder"), "folder", None, self.new_folder)
        self.a_import = A(t("import.file"), "open", None, self.add_file_from_disk)
        self.a_save = A(t("a.save"), "save", "Ctrl+S", self.save_current)
        self.a_save_all = A(t("a.save.all"), "save", "Ctrl+Shift+S", self.save_current)
        self.a_close_file = A(t("a.close.file"), None, "Ctrl+W", lambda: self._tab_close(self.tabbar.currentIndex()))
        self.a_export = A(t("export.project"), None, None, self.export_zip)
        self.a_save_pdf = A(t("a.save.pdf"), "pdf", None, self.save_pdf)
        self.a_open_pdf = A(t("a.open.pdf"), "pdf", None, self.open_pdf)
        self.a_print = A(t("a.print"), "print", "Ctrl+P", self.print_pdf)
        self.a_folder = A(t("a.reveal"), "folder", None, self.open_folder)
        self.a_close = A(t("a.close.project"), None, "Ctrl+Shift+W", self.close_project)
        self.a_undo = A(t("a.undo"), "undo", "Ctrl+Z", ed.undo)
        self.a_redo = A(t("a.redo"), "redo", ["Ctrl+Y", "Ctrl+Shift+Z"], ed.redo)
        self.a_cut = A(t("a.cut"), None, "Ctrl+X", ed.cut)
        self.a_copy = A(t("a.copy"), None, "Ctrl+C", ed.copy)
        self.a_paste = A(t("a.paste"), None, "Ctrl+V", ed.paste)
        self.a_all = A(t("a.select.all"), None, "Ctrl+A", ed.selectAll)
        self.a_find = A(t("a.find"), "find", "Ctrl+F", lambda: self.findbar.open())
        self.a_replace = A(t("a.replace"), None, "Ctrl+H", lambda: self.findbar.open(replace=True))
        self.a_next = A(t("a.find.next"), "down", "F3", lambda: self.findbar.step(1))
        self.a_prev = A(t("a.find.prev"), "up", "Shift+F3", lambda: self.findbar.step(-1))
        self.a_find_project = A(t("a.find.project"), None, "Ctrl+Shift+F", self.find_in_project)
        self.a_goto = A(t("a.goto"), None, "Ctrl+G", self.goto_line)
        self.a_comment = A(t("a.comment"), "comment", "Ctrl+/", ed.toggle_comment)
        self.a_indent = A(t("a.indent"), None, None, lambda: ed.indent(1))
        self.a_dedent = A(t("a.dedent"), None, None, lambda: ed.indent(-1))
        self.a_multi = A(t("a.next.occurrence"), None, "Ctrl+D", ed.add_next_occurrence)
        self.a_bold = A(t("a.bold"), "bold", "Ctrl+B", lambda: ed.wrap_selection("\\textbf{", "}"))
        self.a_italic = A(t("a.italic"), "italic", "Ctrl+I", lambda: ed.wrap_selection("\\textit{", "}"))
        self.a_underline = A(t("a.underline"), "underline", "Ctrl+U", lambda: ed.wrap_selection("\\underline{", "}"))
        self.a_emph = A(t("a.emph"), None, "Ctrl+E", lambda: ed.wrap_selection("\\emph{", "}"))
        self.a_math = A(t("a.math.inline"), "math", "Ctrl+M", lambda: ed.wrap_selection("$", "$"))
        self.a_dmath = A(t("a.math.display"), "sigma", "Ctrl+Shift+M", lambda: ed.wrap_selection("\\[ ", " \\]"))
        self.a_env = A(t("a.env"), None, "Ctrl+Shift+E", self.wrap_env)
        self.a_symbolbar = A(t("a.symbolbar"), None, None, self._toggle_symbols, True, bool(p.get("symbol_bar")))
        self.a_zoom_in = A(t("a.zoom.in"), "zoomin", ["Ctrl++", "Ctrl+="], lambda: self.preview.set_zoom(self.preview.zoom * 1.2))
        self.a_zoom_out = A(t("a.zoom.out"), "zoomout", "Ctrl+-", lambda: self.preview.set_zoom(self.preview.zoom / 1.2))
        self.a_fit_width = A(t("a.fit.width"), "fitwidth", "Ctrl+0", lambda: self.preview.set_fit("width"))
        self.a_fit_page = A(t("a.fit.page"), "fitpage", "Ctrl+9", lambda: self.preview.set_fit("page"))
        self.a_two = A(t("a.two.pages"), "twopages", None, self._toggle_two, True, bool(p.get("two_pages")))
        self.a_night = A(t("a.night"), None, None, self.preview.set_night, True, bool(p.get("night_pdf")))
        self.a_below = A(t("a.horizontal"), None, None, self._toggle_below, True, bool(p.get("preview_below")))
        self.a_pdf_search = A(t("a.search.pdf"), None, "Ctrl+Alt+F", lambda: self.pdf_search.open())
        self.a_compile = A(t("a.compile"), "play", ["F5", "Ctrl+T", "Ctrl+Return"], self.compile)
        self.a_auto_save = A(t("a.autosave.compile"), None, None, lambda on: self.prefs.set("autosave_compile", on), True, bool(p.get("autosave_compile")))
        self.a_auto_type = A(t("a.autotype.compile"), None, None, lambda on: self.prefs.set("autotype_compile", on), True, bool(p.get("autotype_compile")))
        self.a_engine_x = A("XeLaTeX", None, None, lambda: self.set_engine("xetex"), True, self.meta.engine == "xetex")
        self.a_engine_p = A("pdfLaTeX", None, None, lambda: self.set_engine("pdftex"), True, self.meta.engine == "pdftex")
        self.engine_group = QtWidgets.QActionGroup(self)
        for a in (self.a_engine_x, self.a_engine_p):
            self.engine_group.addAction(a)
        self.a_to_pdf = A(t("a.to.pdf"), None, "Ctrl+J", lambda: self.to_pdf(self.editor.textCursor().blockNumber() + 1))
        self.a_check = A(t("tool.check"), "check", None, self.tool_check)
        self.a_set_main = A(t("a.set.main"), None, None, lambda: self.set_main(self.current))
        self.a_csv = A(t("tool.csv"), None, None, self.tool_csv)
        self.a_picture = A(t("tool.picture"), "image", None, self.tool_picture)
        self.a_doi = A(t("tool.doi"), "bib", None, self.tool_doi)
        self.a_style = A(t("tool.style"), None, None, self.tool_style)
        self.a_cite = A(t("insert.citation"), "tag", "Ctrl+Shift+C", self.cite_dialog)
        self.a_snippet = A(t("snippet.save"), None, None, self.save_snippet)
        self.a_outline = A(t("outline"), "list", None, self.outline_dialog)
        self.a_history = A(t("history"), None, None, self.history_dialog)
        self.a_view = A(t("view.options"), "settings", None, self.view_dialog)

    def file_actions(self):
        return [self.a_new_file, self.a_new_folder, self.a_import, None, self.a_save, self.a_save_all, self.a_close_file, None,
                self.a_export, self.a_save_pdf, self.a_open_pdf, self.a_print, None, self.a_folder, None, self.a_close]

    def menus(self):
        """The menus this page adds to the menu bar: (title, QMenu)."""
        edit = QtWidgets.QMenu(t("m.edit"))
        for a in (self.a_undo, self.a_redo, None, self.a_cut, self.a_copy, self.a_paste, self.a_all, None, self.a_find, self.a_replace,
                  self.a_next, self.a_prev, self.a_find_project, self.a_goto, None, self.a_comment, self.a_indent, self.a_dedent,
                  self.a_multi):
            edit.addSeparator() if a is None else edit.addAction(a)
        fmt = edit.addMenu(t("a.format"))
        for a in (self.a_bold, self.a_italic, self.a_underline, self.a_emph, None, self.a_math, self.a_dmath, self.a_env):
            fmt.addSeparator() if a is None else fmt.addAction(a)
        view = QtWidgets.QMenu(t("m.view"))
        panels = view.addMenu(t("a.panels"))
        for d in (self.dock_files, self.dock_struct, self.dock_pages, self.dock_msgs, self.dock_formula):
            panels.addAction(d.toggleViewAction())
        view.addAction(self.a_symbolbar)
        view.addSeparator()
        for a in (self.a_zoom_in, self.a_zoom_out, self.a_fit_width, self.a_fit_page, self.a_two, self.a_night, self.a_pdf_search):
            view.addAction(a)
        view.addSeparator()
        view.addAction(self.a_below)
        view.addAction(self.a_view)
        build = QtWidgets.QMenu(t("m.build"))
        for a in (self.a_compile, self.a_auto_save, self.a_auto_type):
            build.addAction(a)
        eng = build.addMenu(t("a.engine"))
        eng.addAction(self.a_engine_x)
        eng.addAction(self.a_engine_p)
        build.addAction(self.a_set_main)
        build.addSeparator()
        build.addAction(self.a_to_pdf)
        build.addAction(self.a_check)
        tools = QtWidgets.QMenu(t("m.tools"))
        for a in (self.a_cite, self.a_csv, self.a_picture, self.a_doi, self.a_style, None, self.a_snippet, self.a_outline, self.a_history):
            tools.addSeparator() if a is None else tools.addAction(a)
        return [edit, view, build, tools]

    # ------------------------------------------------------------ tool bar and status bar
    def _make_toolbar(self):
        tb = QtWidgets.QToolBar(t("a.compile"))
        tb.setObjectName("maintoolbar")
        tb.setMovable(False)
        tb.setIconSize(QtCore.QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        for a in (self.a_new_file, self.a_import, self.a_save, None, self.a_undo, self.a_redo, None, self.a_bold, self.a_italic,
                  self.a_math, self.a_dmath, self.a_comment, None, self.a_find, self.a_picture, self.a_cite):
            tb.addSeparator() if a is None else tb.addAction(a)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        tb.addWidget(spacer)
        for a in (self.a_zoom_out, self.a_zoom_in, self.a_fit_width, self.a_fit_page, self.a_two, None, self.a_print):
            tb.addSeparator() if a is None else tb.addAction(a)
        tb.addSeparator()
        self.compile_btn = QtWidgets.QPushButton("  " + t("compile"))
        self.compile_btn.setIcon(icon("play", self.theme.on_accent))
        self.compile_btn.setObjectName("primary")
        self.compile_btn.setToolTip(self.a_compile.toolTip())
        self.compile_btn.clicked.connect(self.compile)
        tb.addWidget(self.compile_btn)
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.toolbar = tb

    def _make_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.sb_msg = QtWidgets.QLabel(t("s.ready"))
        sb.addWidget(self.sb_msg, 1)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(150, 6)
        self.progress.hide()
        sb.addPermanentWidget(self.progress)
        self.sb_auto = QtWidgets.QLabel("")
        self.sb_auto.setObjectName("muted")
        self.sb_engine = QtWidgets.QLabel("")
        self.sb_file = QtWidgets.QLabel("")
        self.sb_words = QtWidgets.QLabel("")
        self.sb_pos = QtWidgets.QLabel("%s 1, %s 1" % (t("s.line"), t("s.col")))
        for w in (self.sb_auto, self.sb_engine, self.sb_file, self.sb_words, self.sb_pos):
            w.setContentsMargins(10, 0, 10, 0)
            sb.addPermanentWidget(w)
        self._update_status_labels()

    def _update_status_labels(self):
        self.sb_engine.setText("XeLaTeX" if self.meta.engine == "xetex" else "pdfLaTeX")
        self.sb_file.setText("%s  \u00b7  UTF-8" % (self.current or ""))
        mode = []
        if self.prefs.get("autosave_compile"):
            mode.append("\u21b5 " + t("s.autoc"))
        if self.prefs.get("autotype_compile"):
            mode.append("\u2328 " + t("s.autoc"))
        self.sb_auto.setText("  ".join(mode))

    def say(self, text):
        self.sb_msg.setText(text)

    # ------------------------------------------------------------ preferences and layout
    def _apply_prefs(self):
        p = self.prefs
        self.editor.apply_theme(self.theme, int(p.get("editor_size")))
        self.editor.set_show_numbers(bool(p.get("line_numbers")))
        self.editor.set_wrap(bool(p.get("wrap")))
        self.editor.auto_pairs = bool(p.get("auto_pairs"))
        self.symbol_bar.setVisible(bool(p.get("symbol_bar")))
        if p.get("two_pages"):
            self.preview.set_columns(2)
        if p.get("night_pdf"):
            self.preview.set_night(True)
        if p.get("preview_below"):
            self.split.setOrientation(Qt.Vertical)

    def _restore_layout(self):
        st = self.prefs.get("layout_v2")
        if st:
            try:
                self.restoreState(QtCore.QByteArray.fromBase64(st.encode("ascii")), 2)
            except Exception:
                pass
        self.split.setSizes([620, 560])

    def _save_layout(self):
        try:
            self.prefs.d["layout_v2"] = bytes(self.saveState(2).toBase64()).decode("ascii")
            self.prefs.save()
        except Exception:
            pass

    def _toggle_symbols(self, on):
        self.prefs.set("symbol_bar", bool(on))
        self.symbol_bar.setVisible(bool(on))

    def _toggle_two(self, on):
        self.prefs.set("two_pages", bool(on))
        self.preview.set_columns(2 if on else 1)

    def _toggle_below(self, on):
        self.prefs.set("preview_below", bool(on))
        self.split.setOrientation(Qt.Vertical if on else Qt.Horizontal)

    def set_engine(self, e):
        self.meta.engine = e
        self.store.save_meta(self.project, self.meta)
        self._update_status_labels()

    # ------------------------------------------------------------ the file tree and the open tabs
    def refresh_files(self):
        self.files = self.store.files(self.project, self.meta.main)
        self.tree.clear()
        folders = {"": self.tree.invisibleRootItem()}
        for f in sorted(self.files, key=lambda n: (os.path.dirname(n), n != self.meta.main, n.lower())):
            parent = os.path.dirname(f)
            node = folders[""]
            built = ""
            for part in [p for p in parent.split("/") if p]:
                built = (built + "/" + part) if built else part
                if built not in folders:
                    it = QtWidgets.QTreeWidgetItem(folders[os.path.dirname(built)], [part])
                    it.setIcon(0, icon("folder", self.ic, 16))
                    it.setData(0, Qt.UserRole, "")
                    folders[built] = it
                node = folders[built]
            name = os.path.basename(f)
            it = QtWidgets.QTreeWidgetItem(node, [("\u2605 " if f == self.meta.main else "") + name])
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            it.setIcon(0, icon("tex" if ext == "tex" else "bib" if ext == "bib" else "image" if ext in ("png", "jpg", "jpeg") else "pdf" if ext == "pdf" else "file", self.ic, 16))
            it.setData(0, Qt.UserRole, f)
            if f == self.meta.main:
                fnt = it.font(0)
                fnt.setBold(True)
                it.setFont(0, fnt)
        self.tree.expandAll()

    def _tree_open(self, item, col=0):
        f = item.data(0, Qt.UserRole)
        if f:
            self.open_file(f)

    def _tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        f = item.data(0, Qt.UserRole) if item else ""
        m = QtWidgets.QMenu(self)
        if f:
            m.addAction(t("open") if t("open") != "open" else "Open", lambda: self.open_file(f))
            if f.endswith(".tex") and f != self.meta.main:
                m.addAction(t("a.set.main"), lambda: self.set_main(f))
            m.addAction(t("a.rename"), lambda: self.rename_file(f))
            if f != self.meta.main:
                m.addAction(t("a.delete"), lambda: self.delete_file(f))
            m.addSeparator()
        m.addAction(t("a.new.file"), self.new_file)
        m.addAction(t("a.new.folder"), self.new_folder)
        m.addAction(t("import.file"), self.add_file_from_disk)
        self._popup(m)

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
        if name not in self.open_names:
            self.open_names.append(name)
            self.tabbar.blockSignals(True)
            self.tabbar.addTab(("\u2605 " if name == self.meta.main else "") + os.path.basename(name))
            self.tabbar.setTabToolTip(self.tabbar.count() - 1, name)
            self.tabbar.blockSignals(False)
        self.tabbar.blockSignals(True)
        self.tabbar.setCurrentIndex(self.open_names.index(name))
        self.tabbar.blockSignals(False)
        self._show_doc(name)

    def _show_doc(self, name):
        self.current = name
        d = self._doc_for(name)
        self.editor.extra_cursors = []
        self.editor.setDocument(d)
        self.editor.apply_theme(self.theme, int(self.prefs.get("editor_size")))
        self.editor._update_gutter_width()
        self._update_status_labels()
        self.update_structure()
        self._words()
        self.editor.setFocus()

    def _tab_changed(self, i):
        if 0 <= i < len(self.open_names):
            self._show_doc(self.open_names[i])

    def _tab_close(self, i):
        if not (0 <= i < len(self.open_names)) or len(self.open_names) <= 1:
            return
        self.flush()
        self.open_names.pop(i)
        self.tabbar.blockSignals(True)
        self.tabbar.removeTab(i)
        self.tabbar.blockSignals(False)
        self._show_doc(self.open_names[min(i, len(self.open_names) - 1)])
        self.tabbar.setCurrentIndex(self.open_names.index(self.current))

    def _rebuild_tabs(self):
        self.tabbar.blockSignals(True)
        while self.tabbar.count():
            self.tabbar.removeTab(0)
        self.open_names = [n for n in self.open_names if os.path.isfile(os.path.join(self.project.path, n))]
        for n in self.open_names:
            self.tabbar.addTab(("\u2605 " if n == self.meta.main else "") + os.path.basename(n))
            self.tabbar.setTabToolTip(self.tabbar.count() - 1, n)
        if self.current in self.open_names:
            self.tabbar.setCurrentIndex(self.open_names.index(self.current))
        self.tabbar.blockSignals(False)

    def _open_external(self, name):
        path = os.path.join(self.project.path, name)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: B018 - opens the picture or PDF in the program Windows uses for it
        else:
            subprocess.Popen(["xdg-open", path])

    # ------------------------------------------------------------ typing, saving, words, structure, formula
    def _changed(self):
        self.save_timer.start(700)
        self.struct_timer.start(600)
        self.dirty_since_compile = True
        QTimer.singleShot(400, self._words)
        if self.prefs.get("autotype_compile"):
            self.typing_timer.start(3500)

    def _typing_compile(self):
        if self.dirty_since_compile and not self.compiling and self.engine.is_ready:
            self.compile(quiet=True)

    def _words(self):
        if self.current:
            self.sb_words.setText("%d %s" % (textutil.count_words(self.editor.toPlainText()), t("s.words")))

    def _caret(self, line, col):
        self.sb_pos.setText("%s %d, %s %d" % (t("s.line"), line, t("s.col"), col))
        self.formula_timer.start(250)

    def flush(self):
        for name, (d, _) in self.docs.items():
            if d.isModified():
                with io.open(os.path.join(self.project.path, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(d.toPlainText())
                d.setModified(False)

    def save_current(self):
        self.flush()
        self.say(t("s.saved"))
        if self.prefs.get("autosave_compile") and not self.compiling and self.engine.is_ready:
            self.compile(quiet=True)

    def text_of(self, name):
        if name in self.docs:
            return self.docs[name][0].toPlainText()
        try:
            with io.open(os.path.join(self.project.path, name), encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    def update_structure(self):
        if not self.current:
            return
        self.struct.clear()
        stack = []
        for it in textutil.outline(self.editor.toPlainText()):
            node = QtWidgets.QTreeWidgetItem([it.title])
            node.setData(0, Qt.UserRole, it.line)
            while stack and stack[-1][0] >= it.level:
                stack.pop()
            (stack[-1][1] if stack else self.struct.invisibleRootItem()).addChild(node)
            stack.append((it.level, node))
        self.struct.expandAll()

    def update_formula(self):
        if not self.dock_formula.isVisible() or not self.dock_formula.widget().isVisible():
            return
        text = self.editor.toPlainText()
        hit = textutil.math_at(text, self.editor.textCursor().position())
        if hit is None:
            self.formula.show_note(t("formula.none"))
        else:
            self.formula.show_formula(hit[2], hit[3], textutil.user_macros(self.text_of(self.meta.main) if self.meta.main != self.current else text))

    def _completion_data(self, kind):
        if kind == "ref":
            out = []
            for f in self.files:
                if f.endswith(".tex"):
                    out += _LABEL.findall(self.text_of(f))
            return sorted(set(out))
        if kind == "cite":
            return self.bib_keys()
        if kind == "file":
            return [f for f in self.files if not f.startswith(".")]
        return []

    # ------------------------------------------------------------ file operations
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

    def new_folder(self):
        n = dlg.ask_text(self, t("a.new.folder"), t("file.name"), "figures")
        if n:
            os.makedirs(os.path.join(self.project.path, n), exist_ok=True)
            self.refresh_files()

    def add_file_from_disk(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, t("import.file"))
        self.import_paths(paths)

    def import_paths(self, paths):
        """Copies files (dropped or chosen) into the project; text files open in the editor."""
        last = None
        for path in paths:
            if os.path.isdir(path):
                continue
            with open(path, "rb") as f:
                last = self.store.import_file(self.project, os.path.basename(path), f.read())
        self.refresh_files()
        if last and is_text_file(last):
            self.open_file(last)
        if last:
            self.say(t("drop.import"))

    def rename_file(self, name):
        n = dlg.ask_text(self, t("rename"), t("file.name"), name)
        if not n or n == name or os.path.exists(os.path.join(self.project.path, n)):
            return
        self.flush()
        os.makedirs(os.path.dirname(os.path.join(self.project.path, n)), exist_ok=True)
        os.rename(os.path.join(self.project.path, name), os.path.join(self.project.path, n))
        self.docs.pop(name, None)
        self.open_names = [n if x == name else x for x in self.open_names]
        if self.meta.main == name:
            self.meta.main = n
            self.store.save_meta(self.project, self.meta)
        if self.current == name:
            self.current = n
        self.refresh_files()
        self._rebuild_tabs()
        if self.current == n:
            self.open_file(n)

    def delete_file(self, name):
        if not dlg.confirm(self, "%s \"%s\"?" % (t("delete"), name)):
            return
        os.remove(os.path.join(self.project.path, name))
        self.docs.pop(name, None)
        self.open_names = [x for x in self.open_names if x != name]
        self.refresh_files()
        if not self.open_names:
            self.open_names = [self.meta.main]
        self._rebuild_tabs()
        if self.current == name:
            self.open_file(self.open_names[0])

    def set_main(self, name):
        if not name or not name.endswith(".tex"):
            return
        self.meta.main = name
        self.store.save_meta(self.project, self.meta)
        self.refresh_files()
        self._rebuild_tabs()

    # ------------------------------------------------------------ menu actions
    def bib_keys(self):
        keys = []
        for f in self.files:
            if f.endswith(".bib"):
                keys += check_mod.bib_keys(self.text_of(f))
        return keys

    def cite_dialog(self):
        keys = self.bib_keys()
        if not keys:
            return
        item, ok = QtWidgets.QInputDialog.getItem(self, t("insert.citation"), t("insert.citation"), keys, 0, False)
        if ok:
            self.editor.insert_snippet("\\cite{%s}" % item)

    def goto_line(self):
        n, ok = QtWidgets.QInputDialog.getInt(self, t("a.goto"), t("s.line"), self.editor.textCursor().blockNumber() + 1, 1, self.editor.blockCount())
        if ok:
            self.editor.go_to_line(n)

    def wrap_env(self):
        env = dlg.ask_text(self, t("a.env"), "\\begin{\u2026}", "itemize")
        if env:
            sel = self.editor.textCursor().selectedText().replace("\u2029", "\n")
            self.editor.insert_snippet("\\begin{%s}\n  %s\n\\end{%s}\n" % (env, sel or "\u2038", env))

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
            self.a_symbolbar.setChecked(bool(p.get("symbol_bar")))
            self._apply_prefs()

    def save_pdf(self):
        if not self.pdf_path:
            return self.say(t("print.fail"))
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, t("a.save.pdf"), _pdf_name(self.meta), "PDF (*.pdf)")
        if path:
            shutil.copyfile(self.pdf_path, path)

    def open_pdf(self):
        if self.pdf_path:
            self._open_external(os.path.basename(self.pdf_path))

    def print_pdf(self):
        if self.preview.doc is None:
            return self.say(t("print.fail"))
        from .qt import QtPrintSupport
        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
        if run_dialog(QtPrintSupport.QPrintDialog(printer, self)) != QtWidgets.QDialog.Accepted:
            return
        import fitz
        painter = QtGui.QPainter(printer)
        doc = self.preview.doc
        for i in range(doc.page_count):
            if i:
                printer.newPage()
            rect = painter.viewport()
            page = doc[i]
            s = min(rect.width() / page.rect.width, rect.height() / page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
            img = QtGui.QImage(pix.samples, pix.width, pix.height, pix.stride, QtGui.QImage.Format_RGB888)
            painter.drawImage(0, 0, img)
        painter.end()

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

    # ------------------------------------------------------------ find in the project
    def find_in_project(self):
        self.findbar.open()
        self.findbar.project.setChecked(True)

    def search_project(self, bar):
        p = bar.pattern()
        self.flush()
        self.search_list.clear()
        if not p:
            return
        hits = project_hits(self.project.path, self.files, p)
        per_file = {}
        for f, ln, text in hits:
            per_file.setdefault(f, []).append((ln, text))
        for f, items in per_file.items():
            top = QtWidgets.QTreeWidgetItem(self.search_list, ["%s  (%d)" % (f, len(items))])
            for ln, text in items[:300]:
                it = QtWidgets.QTreeWidgetItem(top, ["%d:  %s" % (ln, text[:200])])
                it.setData(0, Qt.UserRole, (f, ln))
        self.search_list.expandAll()
        bar.count.setText("%d %s" % (len(hits), t("f.results")) if hits else t("f.none"))
        self.msgs.setCurrentWidget(self.search_list)
        self.dock_msgs.show()
        self.dock_msgs.raise_()

    def _search_activated(self, item, col=0):
        d = item.data(0, Qt.UserRole)
        if d:
            self.go_to(d[0], d[1])

    def replace_in_project(self, pattern, repl, regex):
        hits = project_hits(self.project.path, self.files, pattern, read=self.text_of)
        if not hits or not dlg.confirm(self, "%s: %d %s" % (t("replace.all"), len(hits), t("f.results"))):
            return
        for f in sorted(set(h[0] for h in hits)):
            new = pattern.sub(repl if regex else (lambda m: repl), self.text_of(f))
            self._replace_text(f, new)
        self.flush()
        self.say(t("s.saved"))

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
            c = QtGui.QTextCursor(self.docs[main][0])
            c.setPosition(at)
            c.insertText(added)
        else:
            with io.open(os.path.join(self.project.path, main), "w", encoding="utf-8", newline="\n") as f:
                f.write(text[:at] + added + text[at:])

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
        if path:
            self.insert_picture(path)

    def insert_picture(self, path):
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
            existing = self.text_of(bib) if os.path.exists(path) else ""
            key = re.match(r"^@\w+\{([^,]+),", d.entry).group(1)
            entry = d.entry
            keys = check_mod.bib_keys(existing)
            if key in keys:
                n = 0
                while key + chr(ord("a") + n) in keys:
                    n += 1
                entry = re.sub(r"^(@\w+\{)[^,]+,", lambda m: m.group(1) + key + chr(ord("a") + n) + ",", d.entry)
                key = key + chr(ord("a") + n)
            add = ("\n" if existing and not existing.endswith("\n\n") else "") + entry
            if bib in self.docs:
                c = QtGui.QTextCursor(self.docs[bib][0])
                c.movePosition(QtGui.QTextCursor.End)
                c.insertText(add)
            else:
                with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(existing + add)
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
            c = QtGui.QTextCursor(self.docs[name][0])
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

    # ------------------------------------------------------------ jumping between the source and the PDF
    def to_pdf(self, line):
        """Source -> PDF: finds the words of this line (or the nearest line with words) in the PDF.  Matching is by text."""
        if self.preview.doc is None:
            return self.say(t("print.fail"))
        lines = self.editor.toPlainText().split("\n")
        order = [line - 1] + [x for k in range(1, 12) for x in (line - 1 + k, line - 1 - k)]
        for i in order:
            if not (0 <= i < len(lines)):
                continue
            words = textutil.plain_words(lines[i])
            for n in (min(5, len(words)), 3, 2, 1):
                if n and len(words) >= n:
                    for start in range(0, len(words) - n + 1):
                        hit = self.preview.locate(" ".join(words[start:start + n]))
                        if hit and (n > 1 or len(words[start]) > 3):
                            self.preview.flash(*hit)
                            return
        self.say(t("pdf.jump.fail"))

    def to_source(self, page, x, y):
        """PDF -> source: finds the words around a Ctrl+click in the source files."""
        phrase = self.preview.phrase_at(page, x, y).split()
        if not phrase:
            return
        index = []
        for f in self.files:
            if f.endswith(".tex"):
                for i, line in enumerate(self.text_of(f).split("\n")):
                    w = textutil.plain_words(line)
                    if w:
                        index.append((f, i + 1, " ".join(w)))
        for n in (min(3, len(phrase)), 2, 1):
            key = " ".join(phrase[:n])
            if n == 1 and len(key) < 4:
                break
            for f, ln, text in index:
                if key in text:
                    self.go_to(f, ln)
                    return
        self.say(t("pdf.src.fail"))

    # ------------------------------------------------------------ pages dock
    def fill_pages(self):
        self.pages.clear()
        doc = self.preview.doc
        if doc is None:
            return
        self._thumb_i = 0
        for i in range(doc.page_count):
            it = QtWidgets.QListWidgetItem(str(i + 1))
            it.setData(Qt.UserRole, i + 1)
            self.pages.addItem(it)
        QTimer.singleShot(30, self._thumb_step)

    def _thumb_step(self):
        doc = self.preview.doc
        if doc is None or self._thumb_i >= min(doc.page_count, self.pages.count()):
            return
        for _ in range(3):
            i = self._thumb_i
            if i >= min(doc.page_count, self.pages.count(), 80):
                return
            self.pages.item(i).setIcon(QtGui.QIcon(self.preview.thumb(i, 110)))
            self._thumb_i += 1
        QTimer.singleShot(10, self._thumb_step)

    # ------------------------------------------------------------ compiling
    def compile(self, quiet=False):
        if self.compiling:
            return
        self.flush()
        out_name = _pdf_name(self.meta)
        files = []
        for root, dirs, names in os.walk(self.project.path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in names:
                if n.startswith(".") or (os.path.relpath(os.path.join(root, n), self.project.path).replace("\\", "/") == out_name):
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
        self.dirty_since_compile = False
        self.compile_start = time.time()
        self.compile_btn.setEnabled(False)
        self.a_compile.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.say(t("s.compiling"))
        self.progress_timer.start(500)
        driver = "pdftex_bibtex8" if self.meta.engine == "pdftex" else "xetex_bibtex8_dvipdfmx"
        self.engine.compile(files, self.meta.main, driver)

    def _expected_ms(self):
        return min(240000, max(5000, int((self.prefs.get("compile_ms") or {}).get(self.meta.engine, 40000))))

    def _tick(self):
        x = (time.time() - self.compile_start) * 1000.0 / self._expected_ms()
        p = min(0.95, 1 - math.exp(-1.6 * x))
        self.progress.setValue(int(p * 1000))
        self.say("%s %d%%" % (t("s.compiling").rstrip("\u2026"), int(p * 100)))

    def _engine_status(self, s):
        if not self.compiling and s == "starting":
            self.say(t("engine.start"))

    def _compiled(self, ok, code, log, pdf):
        if not self.compiling:
            return
        self.compiling = False
        self.progress_timer.stop()
        self.progress.hide()
        self.compile_btn.setEnabled(True)
        self.a_compile.setEnabled(True)
        self.log_text = log
        self.errors = textutil.parse_errors(log)
        self.err_list.clear()
        for e in self.errors:
            it = QtWidgets.QListWidgetItem("%s%s   %s" % (e.file + ":" if e.file else "", e.line or "?", e.message))
            it.setData(Qt.UserRole, (e.file, e.line))
            it.setIcon(icon("close", "#D32F2F", 16))
            self.err_list.addItem(it)
        self.log_box.setPlainText(log[-20000:])
        if ok and pdf:
            ms = int((time.time() - self.compile_start) * 1000)
            d = dict(self.prefs.get("compile_ms") or {})
            d[self.meta.engine] = ms
            self.prefs.set("compile_ms", d)
            path = os.path.join(self.project.path, _pdf_name(self.meta))
            with open(path, "wb") as f:
                f.write(pdf)
            self.pdf_path = path
            self.preview.load(path)
            self.refresh_files()
            self.say("%s  \u00b7  %.1f s" % (t("ok"), ms / 1000.0))
        else:
            self.say(t("failed") + (" \u00b7 %d %s" % (len(self.errors), t("errors")) if self.errors else ""))
            self.msgs.setCurrentWidget(self.err_list if self.errors else self.log_box)
            self.dock_msgs.show()
            self.dock_msgs.raise_()
            if self.errors:
                e = self.errors[0]
                self.go_to(e.file, e.line)

    def _error_activated(self, item):
        d = item.data(0 + Qt.UserRole)
        if d:
            self.go_to(d[0], d[1])

    # ------------------------------------------------------------ leaving
    def close_project(self):
        self.flush()
        self.closed.emit()

    def shutdown(self):
        self.flush()
        self._save_layout()
        try:
            self.engine.finished.disconnect(self._compiled)
        except Exception:
            pass
        try:
            self.engine.status.disconnect(self._engine_status)
        except Exception:
            pass
        self.formula.shutdown()
