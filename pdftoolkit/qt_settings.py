"""Settings: one page, Appearance then General, each row a label with its control."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QScrollArea, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import art
import core
import i18n
import icons
import qt_style
import settings
import theme
from i18n import tr
from qt_common import FlowLayout, Tool, hline, mkbutton, mkcheck, mkcombo, mklabel

APP_VERSION = "6.1"
THEME_ORDER = ["qp_light", "qp_dark", "paper", "paper_dark", "daylight", "indigo_night", "ocean", "forest", "sunset",
               "rose", "lavender", "gold", "graphite"]
SAMPLE_ICONS = ["home", "split", "convert", "merge"]


def dir_size(p: Path) -> int:
    n = 0
    try:
        for f in p.rglob("*"):
            if f.is_file():
                n += f.stat().st_size
    except OSError:
        pass
    return n


def human(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}" if n < 10 * 1024 else f"{n:.0f} {u}"
        n /= 1024
    return ""


def flow(*widgets: QWidget, h: int = 8, v: int = 8) -> QWidget:
    box = QWidget()
    lay = FlowLayout(box, h, v)
    for w in widgets:
        lay.addWidget(w)
    return box


class Row(QWidget):
    """label + hint on the start side, the control(s) beside it."""

    def __init__(self, label: str, hint: str, *controls: QWidget, last: bool = False):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(hline())
        row = QHBoxLayout()
        row.setContentsMargins(0, 12, 0, 12)
        row.setSpacing(20)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = mklabel(label)
        f = t.font()
        f.setBold(True)
        t.setFont(f)
        col.addWidget(t)
        if hint:
            col.addWidget(mklabel(hint, "muted", wrap=True))
        col.addStretch(1)
        lw = QWidget()
        lw.setLayout(col)
        lw.setFixedWidth(220)
        row.addWidget(lw, 0, Qt.AlignTop)
        row.addWidget(flow(*controls), 1)
        lay.addLayout(row)


def pills(items: list[tuple[str, str]], current: str, on_pick) -> tuple[QWidget, dict]:
    """A row of exclusive pill buttons: items = [(value, label)]."""
    box = QWidget()
    lay = FlowLayout(box)
    grp = QButtonGroup(box)
    grp.setExclusive(True)
    btns = {}
    for val, label in items:
        b = QPushButton(tr(label))
        b.setProperty("pill", True)
        b.setCheckable(True)
        b.setChecked(val == current)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, v=val: on_pick(v))
        grp.addButton(b)
        lay.addWidget(b)
        btns[val] = b
    return box, btns


class Swatch(QPushButton):
    def __init__(self, color: str, on_pick):
        super().__init__()
        self.color = color
        self.setCheckable(True)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color if color else tr("Theme colour"))
        self.clicked.connect(lambda _=False: on_pick(color))
        self.restyle()

    def restyle(self):
        c = self.color
        if c:
            self.setStyleSheet(f"QPushButton {{ background: {c}; border: 2px solid transparent; border-radius: 16px; padding: 0; min-width: 0; }}"
                               f"QPushButton:checked {{ border: 3px solid {theme.STATE.pal['text']}; }}")
        else:
            self.setText("↺")
            self.setStyleSheet(f"QPushButton {{ background: {theme.STATE.pal['field']}; border: 1px solid {theme.STATE.pal['line']}; border-radius: 16px; padding: 0; min-width: 0; }}"
                               f"QPushButton:checked {{ border: 3px solid {theme.STATE.pal['text']}; }}")


class SettingsTool(Tool):
    key, icon, title = "settings", "settings", "Settings"
    subtitle = "Everything is saved automatically."

    def build(self):
        self.body.setContentsMargins(24, 10, 24, 14)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(6)
        lay.addWidget(mklabel("Appearance", "h"))
        self.sec_appearance(lay)
        lay.addSpacing(18)
        lay.addWidget(hline())
        lay.addSpacing(8)
        lay.addWidget(mklabel("General", "h"))
        self.sec_general(lay)
        lay.addStretch(1)
        sc.setWidget(page)
        self.body.addWidget(sc, 1)
        self.refresh()

    # ------------------------------------------------------------ Appearance
    def sec_appearance(self, lay):
        win = self.win
        P = theme.STATE.pal
        self.mode_box, self.mode_btns = pills([("light", "Light"), ("dark", "Dark"), ("auto", "Match Windows")], "light", self._pick_mode)
        self.style_box, self.style_btns = pills([("quiet", "Quiet Pro"), ("paper", "Paper"), ("classic", "Classic (picture backgrounds)")],
                                                "quiet", self._pick_style)
        lay.addWidget(Row("Mode", "Light, dark, or follow Windows", self.mode_box))
        lay.addWidget(Row("Design style", "How the whole app is drawn", self.style_box))
        self.swatches: list[Swatch] = [Swatch(c, self._pick_accent) for c in [""] + theme.ACCENTS]
        lay.addWidget(Row("Accent colour", "Buttons, selection and links. The first circle returns to the theme's own colour.", *self.swatches))

        lay.addSpacing(10)
        lay.addWidget(mklabel("Colour themes: all of them, pick any", "h"))
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_btns = {}
        for i, key in enumerate(THEME_ORDER):
            pal = theme.THEMES[key]
            b = QToolButton()
            b.setProperty("swatch", True)
            b.setCheckable(True)
            b.setText(tr(pal["name"]))
            b.setIcon(QIcon(qt_style.qpixmap(art.swatch(pal, (232, 124)), 2.0)))
            b.setIconSize(QSize(116, 62))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(138, 104)
            b.clicked.connect(lambda _=False, k=key: win.set_theme(k, follow=False))
            self.theme_group.addButton(b)
            self.theme_btns[key] = b
        lay.addWidget(flow(*self.theme_btns.values(), h=10, v=10))

        lay.addSpacing(10)
        self.icon_btns = {}
        self.icon_group = QButtonGroup(self)
        self.icon_group.setExclusive(True)
        for style, label in (("line", "Line"), ("soft", "Soft tile"), ("outlined", "Outlined tile"), ("gradient", "Gradient (classic)")):
            b = QToolButton()
            b.setProperty("swatch", True)
            b.setCheckable(True)
            b.setText(tr(label))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(QSize(150, 34))
            b.setFixedSize(168, 78)
            b.clicked.connect(lambda _=False, s=style: win.set_icon_style(s))
            self.icon_group.addButton(b)
            self.icon_btns[style] = b
        lay.addWidget(Row("Icon style", "The same drawings in four treatments", *self.icon_btns.values()))

        app_tiles = []
        for g, label in (("tools", "PDF Toolkit"),):
            tile = QWidget()
            col = QVBoxLayout(tile)
            col.setContentsMargins(0, 0, 8, 0)
            col.setSpacing(3)
            ic = QLabel()
            ic.setPixmap(icons.app_icon_pixmap(g, 44, 2.0))
            ic.setFixedSize(44, 44)
            col.addWidget(ic, 0, Qt.AlignHCenter)
            col.addWidget(mklabel(label, "muted"), 0, Qt.AlignHCenter)
            app_tiles.append(tile)
        lay.addWidget(Row("App icons", "Flat colour: Start menu, taskbar and shortcuts", *app_tiles))

        self.scale = mkcombo({"80 %": 0.8, "90 %": 0.9, "100 %": 1.0, "110 %": 1.1, "125 %": 1.25, "140 %": 1.4}, self.win.cfg.get("text_scale", 1.0))
        self.scale.activated.connect(lambda _i: win.set_text_scale(self.scale.currentData()))
        lay.addWidget(Row("Text size", "Everything scales together", self.scale))

    def _mode_theme(self, style: str, dark: bool) -> str:
        return theme.STYLES[style][1 if dark else 0]

    def _pick_mode(self, mode: str):
        style = theme.style_of(theme.STATE.name)
        if mode == "auto":
            self.win.cfg["follow_system"] = True
            self.win.sync_system_scheme()
            return
        self.win.set_theme(self._mode_theme(style, mode == "dark"), follow=False)

    def _pick_style(self, style: str):
        self.win.set_theme(self._mode_theme(style, bool(theme.STATE.pal["dark"])))

    def _pick_accent(self, color: str):
        self.win.set_accent(color)

    def _icon_preview(self, style: str) -> QPixmap:
        P = theme.STATE.pal
        acc = P["accent"]
        n, size, gap = len(SAMPLE_ICONS), 30, 8
        pm = QPixmap((n * size + (n - 1) * gap) * 2, size * 2)
        pm.setDevicePixelRatio(2.0)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        for i, g in enumerate(SAMPLE_ICONS):
            if style == "gradient":
                ic = icons.tile_pixmap(g, size, 2.0)
            elif style == "line":
                ic = icons.styled_pixmap(g, size, "line", acc, dpr=2.0)
            else:
                ic = icons.styled_pixmap(g, size, style, acc, qt_style.mix(acc, P["card"], 0.86), qt_style.mix(acc, P["card"], 0.60), 2.0)
            p.drawPixmap(i * (size + gap), 0, ic)
        p.end()
        return pm

    # ------------------------------------------------------------ General
    def sec_general(self, lay):
        win = self.win
        langs = []
        self.lg = QButtonGroup(self)
        for code, label in (("en", "English"), ("fa", "فارسی")):
            b = QPushButton(label)
            b.setFont(QFont("Vazirmatn" if code == "fa" else "Inter", 11))
            b.setProperty("pill", True)
            b.setCheckable(True)
            b.setChecked(win.cfg["lang"] == code)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: win.set_language(c))
            self.lg.addButton(b)
            langs.append(b)
        lay.addWidget(Row("Language", "The app restarts when you change it. Your files and settings are kept.", *langs))
        lay.addWidget(Row("Reset", "Back to the original look. The language stays.", mkbutton("Reset appearance", self._reset)))

    def _reset(self):
        d = settings.DEFAULTS
        for k in ("theme", "accent", "icon_style", "follow_system", "text_scale"):
            self.win.cfg[k] = d[k]
        qt_style.TEXT_SCALE["scale"] = 1.0
        qt_style.FA_FONT["name"] = "Vazirmatn"
        theme.set_theme(d["theme"], "")
        settings.save(self.win.cfg)
        qt_style.apply_app_font(QApplication.instance())
        self.win.apply_style()
        self.refresh()

    # ------------------------------------------------------------ state
    def refresh(self):
        P = theme.STATE.pal
        name = theme.STATE.name
        b = self.theme_btns.get(name)
        if b:
            b.setChecked(True)
        style = theme.style_of(name)
        if style in self.style_btns:
            self.style_btns[style].setChecked(True)
        mode = "auto" if self.win.cfg.get("follow_system") else ("dark" if P["dark"] else "light")
        self.mode_btns[mode].setChecked(True)
        for s in self.swatches:
            s.restyle()
            s.setChecked(s.color == self.win.cfg.get("accent", ""))
        eff = qt_style.ICON["style"]
        for style_, btn in self.icon_btns.items():
            btn.setIcon(QIcon(self._icon_preview(style_)))
            btn.setChecked(style_ == eff)

    def on_show(self):
        self.refresh()
