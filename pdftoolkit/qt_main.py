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
import texengine
import theme
from i18n import tr, trf
from qt_common import Card, JobRunner, Tool, hline, mkbutton, mkcheck, mkcombo, mklabel
from qt_pages import (CompressTool, ConvertTool, ExtractTool, ImagesTool, MergeTool, OcrTool, PagesTool, SplitTool)
from qt_reader import ReaderTool
from qt_tools import (BackgroundTool, BatchTool, BlankTool, CleanScanTool, CropTool, RepairTool, ExportTool, HeaderFooterTool, HiddenTool,
                      SecurityTool, WatermarkTool)
from qt_formulaocr import FormulaOcrTool
from qt_math import MathTool
from qt_pdfedit import CompareTool, EditTool, OrganizeTool, RedactTool
from qt_science import FormulaTool, LatexTool, SymbolPalette, insert_snippet


# One program, several windows: the same files, started with --mode, give separate "apps" (own shortcut, icon,
# taskbar entry) that show only what that job needs.
from modes import MODES  # noqa: E402


def launch(mode: str = "full", files=()):
    """Start another window of the program (a different mode, or more files in the reader)."""
    args = [] if getattr(sys, "frozen", False) else [str(Path(__file__).with_name("app.py"))]
    if mode != "full":
        args += ["--mode", mode]
    args += [str(f) for f in files]
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
        ic = QLabel()
        ic.setPixmap(qt_style.icon_pixmap(icon or key, 26))
        ic.setFixedSize(26, 26)
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
        ic = QLabel()
        ic.setPixmap(qt_style.icon_pixmap(icon or key, 48))
        ic.setFixedSize(48, 48)
        lay.addWidget(ic, 0, Qt.AlignTop)
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


class HomeTool(Tool):
    key, icon, title = "home", "home", "PDF Toolkit"
    subtitle = "Everything for your PDFs in one place — with first-class Persian (Farsi) support."
    CARDS = [("read", "Read", "Open and search PDFs, including Farsi"),
             ("tools", "All tools", "Organize, edit, protect, compare, batch…"),
             ("ocr", "OCR", "Make scanned books searchable (Farsi, Arabic…)"),
             ("extract", "Extract text", "PDF to clean TXT / Word, with OCR"),
             ("convert", "Convert to PDF", "EPUB, DjVu, DOCX, MOBI, TXT, HTML…"),
             ("split", "Split", "Cut a PDF into parts or ranges"),
             ("merge", "Merge", "Join PDFs in any order"),
             ("compress", "Compress", "Four levels, up to Ghostscript power"),
             ("images", "Images to PDF", "Many pictures into one PDF"),
             ("pages", "Page tools", "Delete, extract, rotate, reverse"),
             ("latex", "LaTeX", "Write and compile .tex to PDF, with templates"),
             ("formula", "Formula", "LaTeX formula to PNG / SVG / PDF")]

    def build(self):
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (key, name, desc) in enumerate(self.CARDS):
            grid.addWidget(Tile(self.win, key, name, desc), i // 3, i % 3)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        self.body.addLayout(grid)
        self.body.addStretch(1)
        langs = core.ocr_languages()
        status = [("Persian OCR", "fas" in langs), ("Arabic OCR", "ara" in langs), ("DjVu", bool(core.find_ddjvu())),
                  ("DOCX / ODT / RTF", bool(core.find_pandoc())), ("Ghostscript", bool(core.find_gs())),
                  ("LaTeX", bool(texengine.find_engine()))]
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
        ("Read and view", [("read", "read", "Read", "Books and documents in any format, with tabs and search")]),
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
                     ("clean", "clean", "Clean scans", "Straighten, denoise and sharpen scanned pages"),
                     ("ocr", "ocr", "OCR", "Make scanned books searchable (Farsi, Arabic…)"),
                     ("extract", "extract", "Extract text", "PDF to clean TXT / Word, with OCR"),
                     ("compress", "compress", "Compress", "Four levels, up to Ghostscript power")]),
        ("Edit and stamp", [("edit", "edit", "Edit PDF", "Replace text, add text and pictures, change pictures"),
                            ("headerfooter", "headerfooter", "Header, footer & Bates", "Page numbers, dates and Bates numbers"),
                            ("watermark", "watermark", "Watermark", "Text or picture across the pages"),
                            ("background", "background", "Page background", "A colour or picture behind the content")]),
        ("Protect and review", [("security", "security", "Password & permissions", "Encrypt with AES-256 or remove a password"),
                                ("redact", "redact", "Redact (black out)", "Permanently remove words and areas"),
                                ("hidden", "hidden", "Remove hidden data", "Clean metadata, comments, attachments"),
                                ("compare", "compare", "Compare PDFs", "See what changed between two versions")]),
        ("Science", [("math", "math", "Math", "Calculator, plots and Orlicz-space helpers (SymPy)"),
                     ("formulaocr", "formulaocr", "Formula from picture", "Photo or screenshot of a formula to LaTeX (add-on)"),
                     ("latex", "latex", "LaTeX", "Write and compile .tex to PDF, with templates"),
                     ("formula", "formula", "Formula", "LaTeX formula to PNG / SVG / PDF")]),
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
            for t in tiles:
                t.setVisible(t in shown)
            for i, t in enumerate(shown):
                grid.addWidget(t, i // 3, i % 3)
            head.setVisible(bool(shown))
        for c in range(3):
            for _h, grid, _t in self.groups:
                grid.setColumnStretch(c, 1)

    def on_show(self):
        self.q.setFocus()


class SettingsTool(Tool):
    key, icon, title = "settings", "settings", "Settings"
    subtitle = "Choose a theme and picture, and switch the language."

    def build(self):
        self.body.addWidget(mklabel("Theme", "h"))
        grid = QGridLayout()
        grid.setSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.btns = {}
        for i, (key, pal) in enumerate(theme.THEMES.items()):
            b = QToolButton()
            b.setProperty("swatch", True)
            b.setCheckable(True)
            b.setText(tr(pal["name"]))
            b.setIcon(QIcon(qt_style.qpixmap(art.swatch(pal, (232, 124)), 2.0)))
            b.setIconSize(QSize(116, 62))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(138, 104)
            b.clicked.connect(lambda _=False, k=key: self.win.set_theme(k))
            self.group.addButton(b)
            self.btns[key] = b
            grid.addWidget(b, i // 5, i % 5)
        grid.setColumnStretch(5, 1)
        self.body.addLayout(grid)
        self.body.addWidget(mklabel("Picture", "h"))
        row = QHBoxLayout()
        row.setSpacing(10)
        styles = {tr(art.WALLPAPER_NAMES[k]): k for k in art.WALLPAPERS}
        styles[tr(art.WALLPAPER_NAMES["custom"])] = "custom"
        self.wp = mkcombo(styles, self.win.cfg["wallpaper"])
        self.wp.activated.connect(self._wp_changed)
        row.addWidget(self.wp)
        self.strength = mkcombo({tr("No picture"): "off", tr("Subtle"): "subtle", tr("Medium"): "medium",
                                 tr("Vivid"): "vivid"}, self.win.cfg.get("strength", "medium"))
        self.strength.activated.connect(lambda _i: self.win.set_strength(self.strength.currentData()))
        row.addWidget(self.strength)
        row.addWidget(mkbutton("Choose my picture…", self._pick))
        row.addStretch(1)
        self.body.addLayout(row)
        self.body.addWidget(mklabel("Language", "h"))
        lrow = QHBoxLayout()
        lrow.setSpacing(8)
        self.lg = QButtonGroup(self)
        for code, label in (("en", "English"), ("fa", "فارسی")):
            b = QPushButton(label)
            b.setFont(QFont("Vazirmatn" if code == "fa" else "Inter", 11))
            b.setProperty("pill", True)
            b.setCheckable(True)
            b.setChecked(self.win.cfg["lang"] == code)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: self.win.set_language(c))
            self.lg.addButton(b)
            lrow.addWidget(b)
        lrow.addStretch(1)
        self.body.addLayout(lrow)
        self.note("Changing the language restarts the app (your files and settings are kept).")
        from qt_addons import AddonsPanel
        self.body.addSpacing(10)
        self.addons_panel = AddonsPanel(self.win)
        self.body.addWidget(self.addons_panel)
        self.body.addStretch(1)
        self.refresh()

    def refresh(self):
        b = self.btns.get(theme.STATE.name)
        if b:
            b.setChecked(True)

    def on_show(self):
        self.refresh()
        self.addons_panel.on_show()

    def _wp_changed(self, _i):
        key = self.wp.currentData()
        if key == "custom" and not self.win.cfg.get("custom_picture"):
            return self._pick()
        self.win.set_wallpaper(key)

    def _pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if p:
            self.win.set_wallpaper("custom", p)
            self.wp.setCurrentIndex(self.wp.findData("custom"))


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
PAGES = [("home", "Home", HomeTool), ("read", "Read", ReaderTool), ("tools", "All tools", ToolsTool),
         ("ocr", "OCR", OcrTool), ("extract", "Extract text", ExtractTool), ("convert", "Convert to PDF", ConvertTool),
         ("split", "Split", SplitTool), ("merge", "Merge", MergeTool), ("compress", "Compress", CompressTool),
         ("images", "Images to PDF", ImagesTool), ("pages", "Page tools", PagesTool),
         ("organize", "Organize pages", OrganizeTool), ("crop", "Crop pages", CropTool),
         ("blank", "Delete blank pages", BlankTool), ("headerfooter", "Header, footer & Bates", HeaderFooterTool),
         ("watermark", "Watermark", WatermarkTool), ("background", "Page background", BackgroundTool),
         ("export", "PDF to…", ExportTool), ("security", "Password & permissions", SecurityTool),
         ("hidden", "Remove hidden data", HiddenTool), ("redact", "Redact (black out)", RedactTool),
         ("clean", "Clean scans", CleanScanTool), ("repair", "Repair & optimize", RepairTool),
         ("edit", "Edit PDF", EditTool), ("compare", "Compare PDFs", CompareTool), ("batch", "Batch process", BatchTool),
         ("math", "Math", MathTool), ("formulaocr", "Formula from picture", FormulaOcrTool), ("latex", "LaTeX", LatexTool), ("formula", "Formula", FormulaTool),
         ("settings", "Settings", SettingsTool), ("help", "Help", HelpTool)]
# pages shown in the sidebar; every other tool opens from "All tools" or the Home page
SIDEBAR = ["home", "read", "tools", "ocr", "extract", "convert", "split", "merge", "compress", "images", "pages",
           "math", "latex", "formula", "settings", "help"]


class MainWindow(QMainWindow):
    def __init__(self, cfg: dict, mode: str = "full"):
        super().__init__()
        self.cfg = cfg
        self.mode = mode if mode in MODES else "full"
        self.mcfg = MODES[self.mode]
        self.setWindowTitle(tr(self.mcfg["title"]))
        self.resize(1180, 840)
        self.setMinimumSize(1100, 720)
        ico = core._app_dir() / "icon.ico"
        if self.mcfg["icon"]:
            import icons
            self.setWindowIcon(QIcon(icons.tile_pixmap(self.mcfg["icon"], 256, 1.0)))
        elif ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.setAcceptDrops(True)
        self.insert_target = None
        self._palette = None
        self.pages: dict[str, Tool] = {}
        self.current = None
        self.qss = ""
        self._stamp = 0
        self.last_dir = None
        self._wall_cache: dict = {}

        self.backdrop = qt_style.Backdrop()
        self.setCentralWidget(self.backdrop)
        root = QHBoxLayout(self.backdrop)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        side = QFrame()
        self.side = side
        side.setObjectName("sidebar")
        compact = self.mcfg["compact"]
        side.setFixedWidth(68 if compact else 238)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 20, 14, 14)
        sl.setSpacing(2)
        logo = QHBoxLayout()
        logo.setSpacing(10)
        li = QLabel()
        li.setPixmap(qt_style.icon_pixmap("home", 40))
        li.setFixedSize(40, 40)
        lt = QLabel(tr("PDF Toolkit" if self.mode == "full" else "Math Studio" if self.mode == "math" else "Reader"))
        lt.setObjectName("logoText")
        logo.addWidget(li)
        logo.addWidget(lt, 1)
        if compact:
            lt.hide()
            li.setPixmap(qt_style.icon_pixmap(self.mcfg["icon"] or "home", 40))
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
        keys = self.mcfg["sidebar"] or SIDEBAR
        self.keys = keys
        for key in keys:
            if key in ("settings", "help"):
                continue
            if key == "math" and self.mode == "full":
                nl.addSpacing(6)
                nl.addWidget(hline())
                nl.addSpacing(6)
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
        if self.mode != "full":
            fb = QPushButton()
            fb.setObjectName("nav")
            fb.setCursor(Qt.PointingHandCursor)
            fb.setMinimumHeight(44)
            fl_ = QHBoxLayout(fb)
            fl_.setContentsMargins(8 if compact else 12, 0, 8 if compact else 12, 0)
            fl_.setSpacing(12)
            fi = QLabel()
            fi.setPixmap(qt_style.icon_pixmap("tools", 26))
            fi.setFixedSize(26, 26)
            fl_.addWidget(fi)
            ft = QLabel(tr("Open the full toolkit"))
            ft.setObjectName("navText")
            fl_.addWidget(ft, 1)
            for w in (fi, ft):
                w.setAttribute(Qt.WA_TransparentForMouseEvents)
            if compact:
                ft.hide()
            fb.setToolTip(tr("Open the full toolkit"))
            fb.clicked.connect(lambda _=False: launch("full"))
            sl.addWidget(fb)
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

        self.apply_style()
        self.show_page(self.mcfg["start"])
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
        self.foot.setVisible(key not in ("read", "math"))        # these pages want the full height
        pg.on_show()

    def current_page(self) -> Tool | None:
        return self.pages.get(self.current)

    # ---- look
    def apply_style(self):
        P = theme.STATE.pal
        strength = self.cfg.get("strength", "medium")
        # Only the visible parts are restyled now; hidden pages catch up when shown (keeps theme changes fast).
        self.qss = qt_style.build_qss(theme.STATE.name, strength, i18n.rtl())
        self._stamp += 1
        for w in (self.side, self.foot, self.toast_lbl):
            w.setStyleSheet(self.qss)
        cur = self.current_page()
        if cur is not None:
            cur.setStyleSheet(self.qss)
            cur._stamp = self._stamp
        qt_style.set_tooltip_palette(P)
        style = self.cfg.get("wallpaper", "aurora")
        key = (style, theme.STATE.name, self.cfg.get("custom_picture", ""))
        if key not in self._wall_cache:
            self._wall_cache = {key: qt_style.wallpaper_image(style, P, self.cfg.get("custom_picture", ""))}
        img = None if strength == "off" else self._wall_cache[key]
        self.backdrop.set_picture(img, P["bg"], qt_style.OVERLAY.get(strength, 0.66))

    def set_theme(self, key):
        theme.set_theme(key)
        self.cfg["theme"] = key
        settings.save(self.cfg)
        self.apply_style()
        if self.current_page():
            self.current_page().on_show()
        if self._palette is not None:
            self._palette.close()
            self._palette = None

    def set_wallpaper(self, style, custom=None):
        self.cfg["wallpaper"] = style
        if custom:
            self.cfg["custom_picture"] = custom
        settings.save(self.cfg)
        self.apply_style()

    def set_strength(self, s):
        self.cfg["strength"] = s
        settings.save(self.cfg)
        self.apply_style()

    def set_language(self, code):
        if code == self.cfg["lang"]:
            return
        self.cfg["lang"] = code
        settings.save(self.cfg)
        launch(self.mode)
        QApplication.quit()

    # ---- jobs / log
    def run(self, job, done=None):
        return self.jobs.run(job, done)

    def _job_started(self):
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

    def show_palette(self):
        if self._palette is None:
            self._palette = SymbolPalette(self)
            self._palette.setStyleSheet(self.qss)
        self._palette.show()
        self._palette.raise_()

    def insert_snippet(self, tex):
        tgt = self.insert_target
        if tgt is not None:
            try:
                insert_snippet(tgt, tex)
                return
            except RuntimeError:
                self.insert_target = None
        self.copy_snippet(tex)

    def copy_snippet(self, tex):
        QApplication.clipboard().setText(tex.replace("▢", ""))
        self.toast("LaTeX copied")

    # ---- drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths and self.current_page():
            self.current_page().drop(paths)
