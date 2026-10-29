"""The main window: start page, editor and settings, and the theme that dresses them."""
import os

from .qt import Qt, QtCore, QtGui, QtWidgets, QTimer
from . import strings, theme as th
from .editor_page import EditorPage
from .pages import ProjectsPage, SettingsPage
from .store import HistoryStore, Prefs, ProjectStore


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, engine, store=None, history=None, prefs=None):
        super(MainWindow, self).__init__()
        self.engine = engine
        self.prefs = prefs or Prefs()
        self.store = store or ProjectStore()
        self.history = history or HistoryStore()
        self.setWindowTitle("TeXora")
        self.resize(1280, 820)
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
        self.screen_name = "projects"
        self.project = None
        self.apply_theme()
        self.rebuild()

    def apply_theme(self):
        fa = self.prefs.get("lang") == "fa"
        strings.set_lang(self.prefs.get("lang"))
        self.theme = th.Theme(self.prefs.get("theme"), self.prefs.get("accent"), fa)
        app = QtWidgets.QApplication.instance()
        app.setLayoutDirection(Qt.RightToLeft if fa else Qt.LeftToRight)
        app.setStyleSheet(self.theme.qss(10))

    def rebuild(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            if isinstance(w, EditorPage):
                w.shutdown()
            w.deleteLater()
        self.projects = ProjectsPage(self.store, self.theme, self.prefs)
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
        if name == "projects":
            self.projects.refresh()
            self.stack.setCurrentWidget(self.projects)
        elif name == "settings":
            self.stack.setCurrentWidget(self.settings)

    def open_project(self, project):
        self.project = project
        if self.editor_page is not None:
            self.stack.removeWidget(self.editor_page)
            self.editor_page.shutdown()
            self.editor_page.deleteLater()
        self.editor_page = EditorPage(project, self.store, self.history, self.prefs, self.theme, self.engine)
        self.editor_page.closed.connect(lambda: self.show_screen("projects"))
        self.stack.addWidget(self.editor_page)
        self.stack.setCurrentWidget(self.editor_page)
        self.screen_name = "editor"

    def on_settings(self):
        keep = "settings"
        self.apply_theme()
        self.screen_name = keep
        QTimer.singleShot(0, self.rebuild)

    def closeEvent(self, e):
        if self.editor_page is not None:
            self.editor_page.flush()
        super(MainWindow, self).closeEvent(e)
