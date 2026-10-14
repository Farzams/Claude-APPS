"""Main window, sidebar, Home, Settings and Help."""
from __future__ import annotations

import html
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QProcess, QSize, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (QScrollArea, QLineEdit, QApplication, QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QListWidget, QMainWindow, QMessageBox, QProgressBar, QPlainTextEdit, QPushButton,
                               QStackedWidget, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

import art
import core
import helpdata
import i18n
import qt_style
import settings
import theme
from i18n import tr, trf
from qt_common import Card, JobRunner, Tool, hline, mkbutton, mkcheck, mkcombo, mklabel
from qt_pages import (CompressTool, ConvertTool, ImagesTool, MergeTool, PagesTool, SplitTool)
from qt_tools import (BackgroundTool, BatchTool, BlankTool, CropTool, RepairTool, ExportTool, HeaderFooterTool, HiddenTool,
                      SecurityTool, WatermarkTool)
from qt_pdfedit import CompareTool, EditTool, OrganizeTool, RedactTool
import qt_palette
from qt_settings import SettingsTool


def launch():
    """Start the program again (used after the language changes)."""
    args = [] if getattr(sys, "frozen", False) else [str(Path(__file__).with_name("app.py"))]
    QProcess.startDetached(sys.executable, args)


class NavButton(QPushButton):
    """Sidebar entry: icon always at the start edge, text next to it (works in both directions)."""

    def __init__(self, key: str, title: str, compact: bool = False, icon: str | None = None):
        super().__init__()
        self.setObjectName("nav")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        if compact:
            self.setToolTip(tr(title))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8 if compact else 12, 0, 8 if compact else 12, 0)
        lay.setSpacing(12)
        ic = qt_style.IconLabel(icon or key, 26, "nav")
        self.ic = ic
        self.text = QLabel(tr(title))
        self.text.setObjectName("navText")
        for w in (ic, self.text):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(ic)
        lay.addWidget(self.text, 1)
        if compact:
            self.text.hide()
        self.toggled.connect(self._sync)

    def _sync(self, on: bool):
        self.text.setProperty("active", on)
        self.text.style().unpolish(self.text)
        self.text.style().polish(self.text)
        self.ic.set_active(on)


class Tile(QFrame):
    """Clickable card on the Home page."""

    def __init__(self, win, key, name, desc, icon=None):
        super().__init__()
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.win, self.key = win, key
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)
        lay.addWidget(qt_style.IconLabel(icon or key, 48), 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(mklabel(name, "tileTitle"))
        d = mklabel(desc, "muted", wrap=True)
        col.addWidget(d)
        col.addStretch(1)
        lay.addLayout(col, 1)
        self.setMinimumHeight(92)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.win.show_page(self.key)


class TaskTile(QFrame):
    """Big clickable action on the Home page: icon, verb, one line of help."""

    def __init__(self, name, desc, icon, cb):
        super().__init__()
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.cb = cb
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        lay.addWidget(qt_style.IconLabel(icon, 44), 0, Qt.AlignLeft)
        lay.addWidget(mklabel(name, "tileTitle"))
        lay.addWidget(mklabel(desc, "muted", wrap=True))
        lay.addStretch(1)
        self.setMinimumHeight(138)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.cb()


class HomeTool(Tool):
    key, icon, title = "home", "home", "PDF Toolkit"
    subtitle = "What do you want to do?"

    def build(self):
        win = self.win
        self.search = QPushButton("  " + tr("Search tools and settings…"))
        self.search.setObjectName("searchbar")
        self.search.setCursor(Qt.PointingHandCursor)
        self.search.setMinimumHeight(44)
        self.search.setText(tr("Search tools and settings…") + "        Ctrl K")
        self.search.clicked.connect(lambda: win.palette_box.open())
        self.body.addWidget(self.search)
        self.body.addSpacing(4)
        grid = QGridLayout()
        grid.setSpacing(12)
        tasks = [("Organize pages", "Reorder, rotate, delete or insert pages", "pages", lambda: win.show_page("organize")),
                 ("Combine PDFs", "Join files in any order, then reorder pages", "merge", lambda: win.show_page("merge")),
                 ("Make smaller", "Shrink a PDF for email or upload", "compress", lambda: win.show_page("compress")),
                 ("Convert", "PDF to Word, Excel, pictures, HTML or text", "convert", lambda: win.show_page("export")),
                 ("Split a PDF", "Cut a PDF into parts or ranges", "split", lambda: win.show_page("split")),
                 ("Edit and protect", "Change text, add a watermark, set a password", "edit", lambda: win.show_page("edit"))]
        for i, (name, desc, icon, cb) in enumerate(tasks):
            grid.addWidget(TaskTile(name, desc, icon, cb), i // 3, i % 3)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        self.body.addLayout(grid)
        more = QHBoxLayout()
        more.addStretch(1)
        more.addWidget(mkbutton("All tools", lambda: win.show_page("tools")))
        self.body.addLayout(more)
        self.body.addStretch(1)
        status = [("DjVu", bool(core.find_ddjvu())), ("Ghostscript", bool(core.find_gs()))]
        chips = QHBoxLayout()
        chips.setSpacing(18)
        for n, ok in status:
            lb = mklabel(("●  " if ok else "○  ") + tr(n), "good" if ok else "muted", translate=False)
            chips.addWidget(lb)
        chips.addStretch(1)
        self.body.addLayout(chips)
        self.body.addWidget(mklabel("Tip: drag & drop files onto the window to use them in the open tool.", "muted"))


class ToolsTool(Tool):
    key, icon, title = "tools", "tools", "All tools"
    subtitle = "Every tool in one place — type to search."
    GROUPS = [
        ("Organize", [("organize", "pages", "Organize pages", "Drag to reorder, rotate, delete, duplicate, insert"),
                      ("pages", "pages", "Page tools", "Delete, extract, rotate or reverse by page number"),
                      ("split", "split", "Split", "Cut a PDF into parts or ranges"),
                      ("merge", "merge", "Merge", "Join PDFs in any order"),
                      ("crop", "crop", "Crop pages", "Trim white margins or cut fixed margins"),
                      ("blank", "blank", "Delete blank pages", "Remove empty pages, even from scans"),
                      ("repair", "repair", "Repair & optimize", "Fix a damaged PDF and store it compactly")]),
        ("Convert", [("convert", "convert", "Convert to PDF", "EPUB, DjVu, DOCX, MOBI, TXT, HTML…"),
                     ("images", "images", "Images to PDF", "Many pictures into one PDF"),
                     ("export", "export", "PDF to…", "Pictures, Word, Excel, HTML, RTF, EPUB, text"),
                     ("compress", "compress", "Compress", "Four levels, up to Ghostscript power")]),
        ("Edit and stamp", [("edit", "edit", "Edit PDF", "Replace text, add text and pictures, change pictures"),
                            ("headerfooter", "headerfooter", "Header, footer & Bates", "Page numbers, dates and Bates numbers"),
                            ("watermark", "watermark", "Watermark", "Text or picture across the pages"),
                            ("background", "background", "Page background", "A colour or picture behind the content")]),
        ("Protect and review", [("security", "security", "Password & permissions", "Encrypt with AES-256 or remove a password"),
                                ("redact", "redact", "Redact (black out)", "Permanently remove words and areas"),
                                ("hidden", "hidden", "Remove hidden data", "Clean metadata, comments, attachments"),
                                ("compare", "compare", "Compare PDFs", "See what changed between two versions")]),
        ("Automate", [("batch", "batch", "Batch process", "Run one operation on a whole folder of files")]),
    ]

    def build(self):
        self.q = QLineEdit()
        self.q.setPlaceholderText(tr("Search tools…"))
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self._filter)
        self.body.addWidget(self.q)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self.vl = QVBoxLayout(inner)
        self.vl.setContentsMargins(0, 4, 8, 4)
        self.vl.setSpacing(10)
        self.groups = []
        for gname, items in self.GROUPS:
            head = mklabel(gname, "h")
            grid = QGridLayout()
            grid.setSpacing(10)
            tiles = []
            for key, icon, name, desc in items:
                t = Tile(self.win, key, name, desc, icon)
                t.setParent(inner)          # never leave a tile without a parent: it would pop up as its own window
                t._search = (tr(name) + " " + tr(desc) + " " + name + " " + desc).lower()
                tiles.append(t)
            self.vl.addWidget(head)
            self.vl.addLayout(grid)
            self.groups.append((head, grid, tiles))
        self.vl.addStretch(1)
        sc.setWidget(inner)
        self.body.addWidget(sc, 1)
        self._filter("")

    def _filter(self, text: str):
        q = text.strip().lower()
        for head, grid, tiles in self.groups:
            while grid.count():
                grid.takeAt(0)
            shown = [t for t in tiles if not q or q in t._search]
            for i, t in enumerate(shown):
                grid.addWidget(t, i // 3, i % 3)
            for t in tiles:
                t.setVisible(t in shown)
            head.setVisible(bool(shown))
        for c in range(3):
            for _h, grid, _t in self.groups:
                grid.setColumnStretch(c, 1)

    def on_show(self):
        self.q.setFocus()


class HelpTool(Tool):
    key, icon, title = "help", "help", "Help"
    subtitle = "How to use every tool, tips for Persian documents, and answers to common questions."

    def build(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        self.topics = helpdata.TOPICS[i18n.LANG]
        self.list = QListWidget()
        self.list.setFixedWidth(250)
        for title, _ in self.topics:
            self.list.addItem(title)
        self.list.currentRowChanged.connect(self.show_topic)
        row.addWidget(self.list)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        row.addWidget(self.view, 1)
        self.body.addLayout(row, 1)
        self.list.setCurrentRow(0)

    def show_topic(self, i):
        if i < 0:
            return
        title, body = self.topics[i]
        P = theme.STATE.pal
        d = "rtl" if i18n.rtl() else "ltr"
        align = "right" if i18n.rtl() else "left"
        paras = "".join(f"<p>{html.escape(' '.join(p.split()))}</p>" for p in body.strip().split("\n\n"))
        self.view.setHtml(
            f'<div dir="{d}" style="text-align:{align}; line-height:155%">'
            f'<h2 style="margin-top:2px">{html.escape(title)}</h2>{paras}</div>')


# ------------------------------------------------------------------ main window
PAGES = [("home", "Home", HomeTool), ("tools", "All tools", ToolsTool),
         ("convert", "Convert to PDF", ConvertTool),
         ("split", "Split", SplitTool), ("merge", "Merge", MergeTool), ("compress", "Compress", CompressTool),
         ("images", "Images to PDF", ImagesTool), ("pages", "Page tools", PagesTool),
         ("organize", "Organize pages", OrganizeTool), ("crop", "Crop pages", CropTool),
         ("blank", "Delete blank pages", BlankTool), ("headerfooter", "Header, footer & Bates", HeaderFooterTool),
         ("watermark", "Watermark", WatermarkTool), ("background", "Page background", BackgroundTool),
         ("export", "PDF to…", ExportTool), ("security", "Password & permissions", SecurityTool),
         ("hidden", "Remove hidden data", HiddenTool), ("redact", "Redact (black out)", RedactTool),
         ("repair", "Repair & optimize", RepairTool),
         ("edit", "Edit PDF", EditTool), ("compare", "Compare PDFs", CompareTool), ("batch", "Batch process", BatchTool),
         ("settings", "Settings", SettingsTool), ("help", "Help", HelpTool)]
# pages shown in the sidebar; every other tool opens from "All tools" or the Home page
SIDEBAR = ["home", "tools", "convert", "split", "merge", "compress", "images", "pages", "settings", "help"]


class MainWindow(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(tr("PDF Toolkit"))
        self.resize(1180, 840)
        self.setMinimumSize(1100, 720)
        ico = core._app_dir() / "icon.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.setAcceptDrops(True)
        self.pages: dict[str, Tool] = {}
        self.current = None
        self.qss = ""
        self._stamp = 0
        self.last_dir = None
        self._job_seen = False

        self.backdrop = qt_style.Backdrop()
        self.setCentralWidget(self.backdrop)
        root = QHBoxLayout(self.backdrop)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        side = QFrame()
        self.side = side
        side.setObjectName("sidebar")
        compact = False
        side.setFixedWidth(68 if compact else 238)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 20, 14, 14)
        sl.setSpacing(2)
        logo = QHBoxLayout()
        logo.setSpacing(10)
        import icons
        li = QLabel()
        li.setPixmap(icons.app_icon_pixmap("tools", 36, 2.0))
        li.setFixedSize(36, 36)
        lt = QLabel(tr("PDF Toolkit"))
        lt.setObjectName("logoText")
        logo.addWidget(li)
        logo.addWidget(lt, 1)
        if compact:
            lt.hide()
        sl.addLayout(logo)
        sl.addSpacing(14)
        self.nav: dict[str, QPushButton] = {}
        self.navgroup = QButtonGroup(self)
        self.navgroup.setExclusive(True)
        navbox = QWidget()
        navbox.setObjectName("navbox")
        nl = QVBoxLayout(navbox)
        nl.setContentsMargins(0, 0, 4, 0)
        nl.setSpacing(2)
        titles = {k: t for k, t, _c in PAGES}
        keys = SIDEBAR
        self.keys = keys
        for key in keys:
            if key in ("settings", "help"):
                continue
            b = NavButton(key, titles[key], compact)
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self.navgroup.addButton(b)
            self.nav[key] = b
            nl.addWidget(b)
        nl.addStretch(1)
        navscroll = QScrollArea()
        navscroll.setWidgetResizable(True)
        navscroll.setFrameShape(QFrame.NoFrame)
        navscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        navscroll.setWidget(navbox)
        sl.addWidget(navscroll, 1)
        sl.addSpacing(6)
        sl.addWidget(hline())
        sl.addSpacing(6)
        for key in ("settings", "help"):
            b = NavButton(key, titles[key], compact)
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self.navgroup.addButton(b)
            self.nav[key] = b
            sl.addWidget(b)

        # content: pages + footer
        content = QWidget()
        content.setObjectName("root")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(26, 22, 26, 18)
        cl.setSpacing(12)
        self.stack = QStackedWidget()
        cl.addWidget(self.stack, 1)
        foot = Card()
        self.foot = foot
        fl = QVBoxLayout(foot)
        fl.setContentsMargins(18, 14, 18, 14)
        fl.setSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        row.addWidget(self.bar, 1)
        self.open_btn = mkbutton("Open folder", self.open_folder)
        self.open_btn.setEnabled(False)
        row.addWidget(self.open_btn)
        fl.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(76)
        fl.addWidget(self.log)
        cl.addWidget(foot)
        root.addWidget(side)
        root.addWidget(content, 1)

        self.toast_lbl = QLabel("", self.backdrop)
        self.toast_lbl.setObjectName("toast")
        self.toast_lbl.hide()

        self.jobs = JobRunner()
        self.jobs.log.connect(self._log)
        self.jobs.prog.connect(lambda v: self.bar.setValue(int(v * 1000)))
        self.jobs.started.connect(self._job_started)
        self.jobs.finished.connect(self._job_finished)

        if self.cfg.get("follow_system"):
            self.sync_system_scheme(save=False)
            try:
                QApplication.styleHints().colorSchemeChanged.connect(lambda _s: self.sync_system_scheme(save=False))
            except Exception:
                pass
        self.palette_box = qt_palette.install(self)
        self.apply_style()
        start = "home"
        if self.cfg.get("start_page") in {k for k, _t, _c in PAGES}:
            start = self.cfg["start_page"]
        self.show_page(start)
        QTimer.singleShot(250, self._prebuild)

    # ---- pages
    def page(self, key) -> Tool:
        if key not in self.pages:
            cls = {k: c for k, _t, c in PAGES}[key]
            pg = cls(self)
            pg.setStyleSheet(self.qss)
            pg._stamp = self._stamp
            self.pages[key] = pg
            self.stack.addWidget(pg)
        return self.pages[key]

    def _prebuild(self):
        for key in self.keys:
            if key not in self.pages:
                self.page(key)
                QTimer.singleShot(40, self._prebuild)
                return

    def show_page(self, key):
        pg = self.page(key)
        if getattr(pg, "_stamp", -1) != self._stamp:      # theme changed while this page was hidden
            pg.setStyleSheet(self.qss)
            pg._stamp = self._stamp
        self.stack.setCurrentWidget(pg)
        self.current = key
        (self.nav.get(key) or self.nav.get("tools") or next(iter(self.nav.values()))).setChecked(True)
        self.foot.setVisible(self._job_seen and key not in ("settings", "help", "home", "tools"))   # progress card appears after the first job
        pg.on_show()

    def palette_entries(self):
        """Everything Ctrl+K can reach in this window."""
        from qt_palette import Entry
        out = []
        have = {k for k, _t, _c in PAGES}
        seen = set()
        for _g, items in ToolsTool.GROUPS:
            for key, icon, title, desc in items:
                if key in have and key not in seen:
                    seen.add(key)
                    out.append(Entry(title, desc, icon, "Tool", lambda k=key: self.show_page(k)))
        titles = {k: t for k, t, _c in PAGES}
        for key in ("home", "tools", "settings", "help"):
            if key in have and key not in seen:
                seen.add(key)
                out.append(Entry(titles[key], "", key, "Tool", lambda k=key: self.show_page(k)))
        for key, t in titles.items():
            if key in have and key not in seen:
                seen.add(key)
                out.append(Entry(t, "", key, "Tool", lambda k=key: self.show_page(k)))
        # settings
        light_dark = theme.STYLES[theme.style_of(theme.STATE.name)]
        out.append(Entry("Dark mode", "Switch to the dark theme", "settings", "Setting", lambda: self.set_theme(light_dark[1], follow=False), "night black"))
        out.append(Entry("Light mode", "Switch to the light theme", "settings", "Setting", lambda: self.set_theme(light_dark[0], follow=False), "day bright"))
        for key, pal in theme.THEMES.items():
            out.append(Entry("Theme: " + pal["name"], "Colour theme", "settings", "Setting", lambda k=key: self.set_theme(k, follow=False), "colour color appearance"))
        for style, label in (("line", "Line"), ("soft", "Soft tile"), ("outlined", "Outlined tile"), ("gradient", "Gradient")):
            out.append(Entry("Icons: " + label, "Icon style", "settings", "Setting", lambda s=style: self.set_icon_style(s), "icon style appearance"))
        out.append(Entry("Language: English", "Restarts the app", "settings", "Setting", lambda: self.set_language("en")))
        out.append(Entry("زبان: فارسی  (Language: Persian)", "Restarts the app", "settings", "Setting", lambda: self.set_language("fa"), "persian farsi", raw=True))
        for sec, icon, label in SettingsTool.SECTIONS:
            out.append(Entry("Settings: " + label, "", icon, "Setting", lambda s=sec: (self.show_page("settings"), self.page("settings").show_section(s))))
        return out

    def current_page(self) -> Tool | None:
        return self.pages.get(self.current)

    # ---- look
    def apply_style(self):
        P = theme.STATE.pal
        strength = "off"                                                           # solid colours, no picture
        qt_style.ICON["style"] = qt_style.effective_icon_style(self.cfg.get("icon_style", "auto"), P["flat"])
        # Only the visible parts are restyled now; hidden pages catch up when shown (keeps theme changes fast).
        self.qss = qt_style.build_qss(theme.STATE.name, strength, i18n.rtl(), theme.STATE.accent, qt_style.FA_FONT["name"], qt_style.TEXT_SCALE["scale"])
        self._stamp += 1
        for w in (self.side, self.foot, self.toast_lbl):
            w.setStyleSheet(self.qss)
        cur = self.current_page()
        if cur is not None:
            cur.setStyleSheet(self.qss)
            cur._stamp = self._stamp
        qt_style.set_tooltip_palette(P)
        qt_style.refresh_icons()
        self.backdrop.set_color(P["bg"])

    def set_theme(self, key, follow=None):
        theme.set_theme(key)
        self.cfg["theme"] = key
        if follow is not None:
            self.cfg["follow_system"] = follow
        settings.save(self.cfg)
        self.apply_style()
        if self.current_page():
            self.current_page().on_show()

    def sync_system_scheme(self, save: bool = True):
        """"Match Windows": pick the light or dark theme of the current design style."""
        try:
            dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            dark = False
        self.cfg["follow_system"] = True
        key = theme.STYLES[theme.style_of(theme.STATE.name)][1 if dark else 0]
        if key != theme.STATE.name:
            theme.set_theme(key)
            self.cfg["theme"] = key
        if save:
            settings.save(self.cfg)
            self.apply_style()
            if self.current_page():
                self.current_page().on_show()

    def set_accent(self, color: str):
        self.cfg["accent"] = color
        theme.set_theme(theme.STATE.name, color)
        settings.save(self.cfg)
        self.apply_style()
        if self.current_page():
            self.current_page().on_show()

    def set_icon_style(self, style: str):
        self.cfg["icon_style"] = style
        settings.save(self.cfg)
        self.apply_style()

    def set_text_scale(self, scale: float):
        self.cfg["text_scale"] = scale
        qt_style.TEXT_SCALE["scale"] = scale
        settings.save(self.cfg)
        qt_style.apply_app_font(QApplication.instance())
        self.apply_style()

    def set_fa_font(self, name: str):
        self.cfg["fa_font"] = name
        qt_style.FA_FONT["name"] = name
        settings.save(self.cfg)
        qt_style.apply_app_font(QApplication.instance())
        self.apply_style()

    def set_language(self, code):
        if code == self.cfg["lang"]:
            return
        self.cfg["lang"] = code
        settings.save(self.cfg)
        launch()
        QApplication.quit()

    # ---- jobs / log
    def run(self, job, done=None):
        return self.jobs.run(job, done)

    def _job_started(self):
        self._job_seen = True
        self.foot.setVisible(self.current not in ("settings", "help", "home", "tools"))
        self.bar.setValue(0)
        self.open_btn.setEnabled(False)

    def _job_finished(self, result):
        if result:
            self.last_dir = result
            self.open_btn.setEnabled(True)
        self.bar.setValue(1000)

    def _log(self, text):
        self.log.appendPlainText(text)

    def open_folder(self):
        if not self.last_dir:
            return
        if sys.platform == "win32":
            os.startfile(self.last_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", self.last_dir])
        else:
            subprocess.run(["xdg-open", self.last_dir])

    # ---- small helpers
    def warn(self, title, text):
        box = QMessageBox(QMessageBox.Warning, title, text, QMessageBox.Ok, self)
        box.setStyleSheet(self.qss)
        box.exec()

    def toast(self, text):
        self.toast_lbl.setText(tr(text))
        self.toast_lbl.adjustSize()
        self.toast_lbl.move((self.backdrop.width() - self.toast_lbl.width()) // 2, 18)
        self.toast_lbl.show()
        self.toast_lbl.raise_()
        QTimer.singleShot(1600, self.toast_lbl.hide)

    # ---- drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths and self.current_page():
            self.current_page().drop(paths)
