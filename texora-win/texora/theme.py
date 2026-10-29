"""Colours, typefaces and shapes of the six themes, and the Qt style sheet built from them."""
import os

from .qt import QtGui

# key, name, dark, bg, card, field, hover, text, muted, accent, line
_P = [
    ("qp_light", False, "F6F7F9", "FFFFFF", "FFFFFF", "EEF0F4", "101828", "667085", "4F46E5", "E4E7EC"),
    ("qp_dark", True, "0D0F13", "14171C", "171A20", "1C2027", "E8EAEE", "8B93A1", "818CF8", "232830"),
    ("paper", False, "F3EEE4", "FBF8F2", "FFFDF8", "E9E2D2", "2B2620", "7A6F60", "B4532A", "DDD4C1"),
    ("paper_dark", True, "1C1814", "26211B", "2B251E", "322B23", "EADFCB", "A39881", "E08A5C", "3A3228"),
    ("ocean", False, "EDF5F8", "FFFFFF", "FFFFFF", "DDECF1", "0B2530", "58727E", "0E7490", "D0E2E9"),
    ("ocean_dark", True, "08171D", "0F232B", "112A33", "16313B", "E3F1F5", "8FAAB5", "2CC1D9", "1B3A46"),
    ("forest", False, "F0F6F0", "FFFFFF", "FFFFFF", "E1EDE2", "12261A", "5C7363", "15803D", "D3E3D6"),
    ("forest_dark", True, "0B1510", "121F18", "14251C", "1A2D22", "E4F1E7", "8FA898", "4ADE80", "213628"),
    ("sunset", False, "FFF3EC", "FFFFFF", "FFFFFF", "FFE5D8", "2D1A14", "86675B", "E4572E", "F2D8CB"),
    ("sunset_dark", True, "1C1210", "271A17", "2D1E1A", "35241F", "F8E8E1", "B79A8E", "FF7F5C", "41302A"),
    ("graphite", False, "F4F4F4", "FFFFFF", "FFFFFF", "EAEAEA", "111111", "6B6B6B", "111111", "DEDEDE"),
    ("graphite_dark", True, "000000", "0B0B0B", "121212", "1A1A1A", "F2F2F2", "8C8C8C", "FFFFFF", "262626"),
]


class Palette(object):
    def __init__(self, key, dark, bg, card, field, hover, text, muted, accent, line):
        self.key, self.dark = key, dark
        self.bg, self.card, self.field, self.hover = "#" + bg, "#" + card, "#" + field, "#" + hover
        self.text, self.muted, self.accent, self.line = "#" + text, "#" + muted, "#" + accent, "#" + line


PALETTES = [Palette(*p) for p in _P]
ACCENTS = ["#4F46E5", "#0F766E", "#BE185D", "#EA580C", "#16A34A", "#E11D48", "#475569", "#CA8A04", "#2563EB"]
STYLES = [("quiet", "qp_light", "qp_dark"), ("paper", "paper", "paper_dark"), ("ocean", "ocean", "ocean_dark"),
          ("forest", "forest", "forest_dark"), ("sunset", "sunset", "sunset_dark"), ("graphite", "graphite", "graphite_dark")]
APP_ACCENT = "#4450D8"          # the colour of TeXora; only the Studio theme takes it, the others bring their own

# typeface file, corner radius of small / medium / large shapes, border width, how strongly borders show (0..1), header look
STYLE_SPECS = {
    "quiet": dict(font="plusjakarta.ttf", r=(8, 12, 18), border=1, strength=0.0, header="plain"),
    "paper": dict(font="lora.ttf", r=(2, 3, 5), border=1, strength=0.45, header="center"),
    "ocean": dict(font="outfit.ttf", r=(12, 18, 26), border=1, strength=0.0, header="plain"),
    "forest": dict(font="nunito.ttf", r=(12, 20, 26), border=0, strength=0.0, header="banner"),
    "sunset": dict(font="poppins_regular.ttf", r=(10, 16, 24), border=0, strength=0.0, header="hero"),
    "graphite": dict(font="jetbrainsmono.ttf", r=(2, 2, 2), border=1, strength=0.8, header="upper"),
}


def palette_of(key):
    return next((p for p in PALETTES if p.key == key), PALETTES[0])


def style_of(key):
    return next((s[0] for s in STYLES if key in (s[1], s[2])), "quiet")


def lerp(a, b, t):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return QtGui.QColor(int(ca.red() + (cb.red() - ca.red()) * t), int(ca.green() + (cb.green() - ca.green()) * t),
                        int(ca.blue() + (cb.blue() - ca.blue()) * t)).name()


def on_color(hex_color):
    c = QtGui.QColor(hex_color)
    lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
    return "#14110A" if lum > 0.62 else "#FFFFFF"


_families = {}


def load_fonts():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    for f in sorted(os.listdir(d)):
        if f.endswith(".ttf"):
            i = QtGui.QFontDatabase.addApplicationFont(os.path.join(d, f))
            fam = QtGui.QFontDatabase.applicationFontFamilies(i)
            if fam:
                _families[f] = fam[0]


def family(file):
    return _families.get(file, "Segoe UI")


class Theme(object):
    """Everything the widgets need to look right: colours, fonts, radii and the style sheet."""

    def __init__(self, key, accent_hex="", fa=False):
        self.pal = palette_of(key)
        self.style = style_of(key)
        self.spec = STYLE_SPECS[self.style]
        self.fa = fa
        acc = accent_hex or (APP_ACCENT if self.pal.key.startswith("qp_") else self.pal.accent)
        self.accent = acc
        self.on_accent = on_color(acc)
        self.font = family("vazirmatn_regular.ttf") if fa else family(self.spec["font"])
        self.r_small, self.r_medium, self.r_large = self.spec["r"]
        self.border_width = self.spec["border"]
        self.border = lerp(self.pal.line, self.pal.text, self.spec["strength"])
        self.dark = self.pal.dark
        self.mono = "Consolas" if os.name == "nt" else "DejaVu Sans Mono"

    def qss(self, size=10):
        p, a = self.pal, self.accent
        b = "%dpx solid %s" % (self.border_width, self.border) if self.border_width else "1px solid %s" % p.line
        soft = lerp(p.card, a, 0.14)
        rs, rm, rl = self.r_small, self.r_medium, self.r_large
        return """
* { font-family: "%(font)s"; font-size: %(size)dpt; }
QWidget { color: %(text)s; }
QMainWindow, QDialog, QStackedWidget, #page { background: %(bg)s; }
QLabel { background: transparent; }
QToolTip { background: %(card)s; color: %(text)s; border: %(b)s; padding: 4px; }
QFrame#card, QWidget#card { background: %(card)s; border: %(b)s; border-radius: %(rl)dpx; }
QFrame#card:hover { border: 1px solid %(accent)s; }
QFrame#bar, QWidget#bar { background: %(card)s; border-bottom: 1px solid %(line)s; }
QFrame#bottombar { background: %(card)s; border-top: 1px solid %(line)s; }
QLabel#muted { color: %(muted)s; }
QLabel#title { font-size: %(tsize)dpt; font-weight: 700; }
QLabel#h2 { font-size: %(h2)dpt; font-weight: 700; }
QPushButton { background: %(card)s; border: %(b)s; border-radius: %(rs)dpx; padding: 6px 14px; }
QPushButton:hover { background: %(hover)s; }
QPushButton:disabled { color: %(muted)s; }
QPushButton#primary { background: %(accent)s; color: %(onacc)s; border: none; border-radius: %(rm)dpx; padding: 8px 20px; font-weight: 600; }
QPushButton#primary:hover { background: %(accent2)s; }
QPushButton#primary:disabled { background: %(hover)s; color: %(muted)s; }
QPushButton#chip { background: transparent; border: 1px solid %(line)s; border-radius: %(rl)dpx; padding: 4px 12px; }
QPushButton#chip:checked { background: %(accent)s; color: %(onacc)s; border: 1px solid %(accent)s; }
QPushButton#chip:hover:!checked { background: %(hover)s; }
QPushButton#sym { background: %(field)s; border: 1px solid %(line)s; border-radius: %(rs)dpx; padding: 3px 9px; min-width: 22px; font-family: "%(mono)s"; }
QPushButton#sym:hover { background: %(soft)s; border: 1px solid %(accent)s; }
QToolButton { background: transparent; border: none; border-radius: %(rs)dpx; padding: 5px; }
QToolButton:hover { background: %(hover)s; }
QToolButton:checked { background: %(soft)s; }
QToolButton::menu-indicator { image: none; width: 0; }
QLineEdit, QSpinBox, QComboBox { background: %(field)s; border: 1px solid %(line)s; border-radius: %(rs)dpx; padding: 6px 8px; selection-background-color: %(accent)s; selection-color: %(onacc)s; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid %(accent)s; }
QComboBox QAbstractItemView { background: %(card)s; border: %(b)s; selection-background-color: %(soft)s; selection-color: %(text)s; }
QPlainTextEdit, QTextEdit { background: %(field)s; border: none; selection-background-color: %(accent)s; selection-color: %(onacc)s; }
QListWidget, QTreeWidget { background: transparent; border: none; outline: 0; }
QListWidget::item { padding: 8px; border-radius: %(rs)dpx; }
QListWidget::item:hover { background: %(hover)s; }
QListWidget::item:selected { background: %(soft)s; color: %(text)s; }
QMenu { background: %(card)s; border: %(b)s; padding: 4px; }
QMenu::item { padding: 7px 24px; border-radius: %(rs)dpx; }
QMenu::item:selected { background: %(soft)s; }
QMenu::separator { height: 1px; background: %(line)s; margin: 4px 8px; }
QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: %(line)s; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 0; }
QScrollBar::handle:horizontal { background: %(line)s; border-radius: 5px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: %(muted)s; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QProgressBar { background: %(hover)s; border: none; border-radius: 2px; max-height: 4px; text-align: center; }
QProgressBar::chunk { background: %(accent)s; border-radius: 2px; }
QSplitter::handle { background: %(line)s; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QGroupBox { border: %(b)s; border-radius: %(rl)dpx; margin-top: 14px; padding: 12px; background: %(card)s; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; font-weight: 700; }
QMenuBar { background: %(card)s; border-bottom: 1px solid %(line)s; padding: 2px 6px; }
QMenuBar::item { padding: 5px 10px; border-radius: %(rs)dpx; background: transparent; }
QMenuBar::item:selected { background: %(soft)s; }
QToolBar { background: %(card)s; border: none; border-bottom: 1px solid %(line)s; spacing: 2px; padding: 3px 6px; }
QToolBar::separator { background: %(line)s; width: 1px; margin: 4px 6px; }
QStatusBar { background: %(card)s; border-top: 1px solid %(line)s; }
QStatusBar::item { border: none; }
QDockWidget { font-weight: 600; }
QDockWidget::title { background: %(card)s; padding: 6px 10px; border-bottom: 1px solid %(line)s; }
QMainWindow::separator { background: %(line)s; width: 1px; height: 1px; }
QTabBar { background: transparent; }
QTabBar::tab { background: transparent; padding: 6px 14px; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:hover { background: %(hover)s; }
QTabBar::tab:selected { border-bottom: 2px solid %(accent)s; }
QTabWidget::pane { border: none; border-top: 1px solid %(line)s; }
QTreeWidget::item { padding: 3px 2px; border-radius: %(rs)dpx; }
QTreeWidget::item:hover { background: %(hover)s; }
QTreeWidget::item:selected { background: %(soft)s; color: %(text)s; }
QCompleter QAbstractItemView, QListView { background: %(card)s; }
""" % dict(font=self.font, size=size, text=p.text, bg=p.bg, card=p.card, b=b, rl=rl, rm=rm, rs=rs, accent=a, line=p.line,
           muted=p.muted, hover=p.hover, field=p.field, soft=soft, onacc=self.on_accent, mono=self.mono,
           accent2=lerp(a, "#FFFFFF" if not self.dark else "#000000", 0.12), tsize=size + 8, h2=size + 3)
