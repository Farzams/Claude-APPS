"""The main window: menu bar, the start page, the editor and the settings, drag and drop, recent projects."""
import base64
import os

from .qt import Qt, QtCore, QtGui, QtWidgets, QAction, QTimer, run_dialog
from . import strings, theme as th
from .editor_page import EditorPage
from .icons import icon
from .pages import ProjectsPage, SettingsPage
from .store import HistoryStore, Meta, Prefs, Project, ProjectStore, is_text_file
from .strings import t

IMAGES = (".png", ".jpg", ".jpeg", ".pdf")

SHORTCUTS = [
    ("F5 / Ctrl+T", "a.compile"), ("Ctrl+S", "a.save"), ("Ctrl+F / Ctrl+H", "a.find"), ("F3 / Shift+F3", "a.find.next"),
    ("Ctrl+Shift+F", "a.find.project"), ("Ctrl+G", "a.goto"), ("Ctrl+/", "a.comment"), ("Ctrl+B / I / U / E", "a.format"),
    ("Ctrl+M / Ctrl+Shift+M", "a.math.inline"), ("Ctrl+D  ·  Alt+click", "a.next.occurrence"), ("Ctrl+Space", "Complete"),
    ("Ctrl+click (source)", "a.to.pdf"), ("Ctrl+click (PDF)", "a.to.source"), ("Ctrl+J", "a.to.pdf"), ("Ctrl+0 / 9", "a.fit.width"),
    ("Ctrl++ / Ctrl+-", "a.zoom.in"), ("Ctrl+P", "a.print"), ("Ctrl+W", "a.close.file"), ("Ctrl+Shift+W", "a.close.project"),
]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, engine, store=None, history=None, prefs=None):
        super(MainWindow, self).__init__()
        self.engine = engine
        self.prefs = prefs or Prefs()
        self.store = store or ProjectStore()
        self.history = history or HistoryStore()
        self.setWindowTitle("TeXora")
        self.resize(1360, 860)
        self.setAcceptDrops(True)
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
        self.screen_name = "projects"
        self.project = None
        self.editor_page = None
        self.page_menus = []
        g = self.prefs.get("geometry")
        if g:
            try:
                self.restoreGeometry(QtCore.QByteArray.fromBase64(g.encode("ascii")))
            except Exception:
                pass
        self.apply_theme()
        self._make_menus()
        self.rebuild()

    # ------------------------------------------------------------ theme
    def apply_theme(self):
        fa = self.prefs.get("lang") == "fa"
        strings.set_lang(self.prefs.get("lang"))
        self.theme = th.Theme(self.prefs.get("theme"), self.prefs.get("accent"), fa)
        app = QtWidgets.QApplication.instance()
        app.setLayoutDirection(Qt.RightToLeft if fa else Qt.LeftToRight)
        app.setStyleSheet(self.theme.qss(10))

    # ------------------------------------------------------------ menus
    def _act(self, text, keys, fn):
        a = QAction(text, self)
        if keys:
            a.setShortcut(QtGui.QKeySequence(keys))
        a.triggered.connect(lambda _=False, f=fn: f())
        self.addAction(a)
        return a

    def _make_menus(self):
        bar = self.menuBar()
        bar.clear()
        self.a_new = self._act(t("a.new.project"), "Ctrl+N", self.new_project)
        self.a_open_folder = self._act(t("a.open.folder"), "Ctrl+Shift+O", self.open_folder_dialog)
        self.a_open_file = self._act(t("a.open.file"), "Ctrl+O", self.open_file_dialog)
        self.a_import_zip = self._act(t("a.import.zip"), None, self.import_zip)
        self.a_settings = self._act(t("a.settings"), "Ctrl+,", lambda: self.show_screen("settings"))
        self.a_quit = self._act(t("a.quit"), "Ctrl+Q", self.close)
        self.a_full = self._act(t("a.fullscreen"), "F11", self.toggle_full)
        self.file_menu = bar.addMenu(t("m.file"))
        self.file_menu.aboutToShow.connect(self._fill_file_menu)
        self.help_menu = bar.addMenu(t("m.help"))
        self.help_menu.addAction(self.a_full)
        self.help_menu.addAction(t("a.shortcuts"), self.show_shortcuts)
        self.help_menu.addAction(t("a.about"), self.show_about)
        self._fill_file_menu()

    def _fill_file_menu(self):
        m = self.file_menu
        m.clear()
        for a in (self.a_new, self.a_open_folder, self.a_open_file, self.a_import_zip):
            m.addAction(a)
        rec = m.addMenu(t("a.recent"))
        recent = [r for r in (self.prefs.get("recent") or []) if os.path.isdir(r.get("path", ""))]
        for r in recent[:10]:
            rec.addAction(r["name"], lambda r=r: self.open_path(r["path"], r.get("external", False)))
        if recent:
            rec.addSeparator()
            rec.addAction(t("a.clear.recent"), lambda: self.prefs.set("recent", []))
        else:
            rec.addAction(t("a.no.recent")).setEnabled(False)
        if self.editor_page is not None:
            m.addSeparator()
            for a in self.editor_page.file_actions():
                m.addSeparator() if a is None else m.addAction(a)
        m.addSeparator()
        m.addAction(self.a_settings)
        m.addSeparator()
        m.addAction(self.a_quit)

    def _set_page_menus(self, page):
        bar = self.menuBar()
        for m in self.page_menus:
            bar.removeAction(m.menuAction())
        self.page_menus = []
        if page is not None:
            for m in page.menus():
                bar.insertMenu(self.help_menu.menuAction(), m)
                self.page_menus.append(m)

    def toggle_full(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def show_about(self):
        from . import __version__
        QtWidgets.QMessageBox.about(self, t("a.about"), "<b>TeXora %s</b><br><br>%s" % (__version__, t("about.text").replace("\n", "<br>")))

    def show_shortcuts(self):
        d = QtWidgets.QDialog(self)
        d.setWindowTitle(t("keys.title"))
        lay = QtWidgets.QGridLayout(d)
        for i, (k, key) in enumerate(SHORTCUTS):
            a = QtWidgets.QLabel("<b>%s</b>" % k)
            lay.addWidget(a, i, 0)
            lay.addWidget(QtWidgets.QLabel(t(key).replace("&", "")), i, 1)
        run_dialog(d)

    # ------------------------------------------------------------ screens
    def rebuild(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            if isinstance(w, EditorPage):
                w.shutdown()
            w.hide()
            w.setParent(None)
            w.deleteLater()
        self._set_page_menus(None)
        self._make_menus()
        self.projects = ProjectsPage(self.store, self.theme, self.prefs)
        self.projects.extras = self.external_projects
        self.projects.forget = self.forget_external
        self.projects.open_project.connect(self.open_project)
        self.projects.open_settings.connect(lambda: self.show_screen("settings"))
        self.stack.addWidget(self.projects)
        self.settings = SettingsPage(self.prefs, self.theme)
        self.settings.back.connect(lambda: self.show_screen("projects"))
        self.settings.changed.connect(self.on_settings)
        self.stack.addWidget(self.settings)
        self.editor_page = None
        if self.screen_name == "editor" and self.project is not None:
            self.open_project(self.project)
        else:
            self.show_screen(self.screen_name if self.screen_name in ("projects", "settings") else "projects")

    def show_screen(self, name):
        self.screen_name = name
        if self.editor_page is not None and name != "editor":
            self.stack.removeWidget(self.editor_page)
            self.editor_page.shutdown()
            self.editor_page.hide()
            self.editor_page.setParent(None)
            self.editor_page.deleteLater()
            self.editor_page = None
            self._set_page_menus(None)
            self.setWindowTitle("TeXora")
        if name == "projects":
            self.projects.refresh()
            self.stack.setCurrentWidget(self.projects)
        elif name == "settings":
            self.stack.setCurrentWidget(self.settings)
        self._fill_file_menu()

    def open_project(self, project):
        self.project = project
        if self.editor_page is not None:
            self.stack.removeWidget(self.editor_page)
            self.editor_page.shutdown()
            self.editor_page.setParent(None)
            self.editor_page.deleteLater()
        self.editor_page = EditorPage(project, self.store, self.history, self.prefs, self.theme, self.engine)
        self.editor_page.closed.connect(lambda: self.show_screen("projects"))
        self.stack.addWidget(self.editor_page)
        self.stack.setCurrentWidget(self.editor_page)
        self.screen_name = "editor"
        self._set_page_menus(self.editor_page)
        self.setWindowTitle("%s — TeXora" % project.name)
        self._remember(project)
        self._fill_file_menu()

    def on_settings(self):
        self.apply_theme()
        self.screen_name = "settings"
        QTimer.singleShot(0, self.rebuild)

    # ------------------------------------------------------------ projects: new, external, recent
    def new_project(self):
        self.show_screen("projects")
        self.projects.new_project()

    def external_projects(self):
        out = []
        for p in self.prefs.get("external") or []:
            if os.path.isdir(p):
                out.append(Project(os.path.basename(p.rstrip("/\\")) or p, p, True))
        return out

    def forget_external(self, project):
        self.prefs.set("external", [p for p in (self.prefs.get("external") or []) if p != project.path])
        self.projects.refresh()

    def _remember(self, project):
        rec = [r for r in (self.prefs.get("recent") or []) if r.get("path") != project.path]
        rec.insert(0, {"name": project.name, "path": project.path, "external": bool(project.external)})
        self.prefs.set("recent", rec[:12])

    def open_path(self, path, external):
        if not os.path.isdir(path):
            QtWidgets.QMessageBox.information(self, "TeXora", t("ext.badfolder"))
            return
        if external:
            self.open_folder(path)
        else:
            self.open_project(Project(os.path.basename(path), path))

    def open_folder(self, folder, main=None):
        """Opens a folder somewhere on the disk as a project, in place."""
        folder = os.path.normpath(folder)
        ext = list(self.prefs.get("external") or [])
        if folder not in ext and os.path.dirname(folder) != os.path.normpath(self.store.root):
            ext.append(folder)
            self.prefs.set("external", ext)
        p = Project(os.path.basename(folder) or folder, folder, os.path.dirname(folder) != os.path.normpath(self.store.root))
        meta = self.store.meta(p)
        texs = sorted(f for f in os.listdir(folder) if f.endswith(".tex"))
        if main is None and not os.path.isfile(os.path.join(folder, ".texora.json")):
            main = next((f for f in texs if self._is_main(os.path.join(folder, f))), texs[0] if texs else "main.tex")
        if main and (main != meta.main or not os.path.isfile(os.path.join(folder, ".texora.json"))):
            meta.main = main
            self.store.save_meta(p, meta)
        self.open_project(p)

    @staticmethod
    def _is_main(path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return "\\documentclass" in f.read(20000)
        except OSError:
            return False

    def open_folder_dialog(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, t("a.open.folder"))
        if d:
            self.open_folder(d)

    def open_file_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("a.open.file"), "", "LaTeX (*.tex);;All (*)")
        if path:
            self.open_folder(os.path.dirname(path), os.path.basename(path))

    def import_zip(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("import"), "", "ZIP (*.zip)")
        if path:
            self.open_project(self.store.import_zip(os.path.basename(path), path))

    # ------------------------------------------------------------ drag and drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if not paths:
            return
        e.acceptProposedAction()
        if self.editor_page is not None and self.screen_name == "editor":
            images = [p for p in paths if p.lower().endswith(IMAGES) and not p.lower().endswith(".pdf")]
            others = [p for p in paths if p not in images]
            for p in images:
                self.editor_page.insert_picture(p)
            if others:
                self.editor_page.import_paths(others)
            return
        first = paths[0]
        if os.path.isdir(first):
            self.open_folder(first)
        elif first.lower().endswith(".zip"):
            self.open_project(self.store.import_zip(os.path.basename(first), first))
        elif first.lower().endswith(".tex"):
            self.open_folder(os.path.dirname(first), os.path.basename(first))

    # ------------------------------------------------------------ closing
    def closeEvent(self, e):
        if self.editor_page is not None:
            self.editor_page.flush()
            self.editor_page.shutdown()
        try:
            self.prefs.d["geometry"] = bytes(self.saveGeometry().toBase64()).decode("ascii")
            self.prefs.save()
        except Exception:
            pass
        super(MainWindow, self).closeEvent(e)
