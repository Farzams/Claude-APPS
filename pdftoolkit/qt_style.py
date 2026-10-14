"""Qt look: fonts, colour themes as a style sheet, and the background."""
from __future__ import annotations

import sys
import tempfile
import weakref
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

import art
import i18n
import theme

FONT_DIR = art.FONT_DIR
STRENGTHS = {"off": 1.0, "subtle": 0.92, "medium": 0.80, "vivid": 0.62}   # card opacity over the picture
OVERLAY = {"off": 1.0, "subtle": 0.78, "medium": 0.52, "vivid": 0.26}     # veil over the picture itself


# ---------------------------------------------------------------- fonts
def load_fonts() -> None:
    for f in ("Inter-Regular.otf", "Inter-Medium.otf", "Inter-SemiBold.otf", "Inter-Bold.otf",
              "Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf", "Vazirmatn-Bold.ttf", "NotoSansArabic-Regular.ttf", "NotoSansArabic-Bold.ttf",
              "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        p = FONT_DIR / f
        if p.is_file():
            QFontDatabase.addApplicationFont(str(p))


FA_FONT = {"name": "Vazirmatn"}            # Persian UI font chosen in Settings
FA_FONTS = {"Vazirmatn": "Vazirmatn", "Noto Sans Arabic": "Noto Sans Arabic", "Windows default": "Tahoma"}
TEXT_SCALE = {"scale": 1.0}


def ui_family() -> str:
    return FA_FONT["name"] if i18n.rtl() else "Inter"


def apply_app_font(app: QApplication, size: float = 9.5) -> None:
    f = QFont(ui_family())
    f.setFamilies([ui_family(), "Inter", "Vazirmatn", "Segoe UI", "Tahoma"])
    f.setPointSizeF((size + (0.5 if i18n.rtl() else 0)) * TEXT_SCALE["scale"])   # Persian letters need a little more size to stay crisp
    # Unhinted outlines and full anti-aliasing keep Persian curves smooth (hinting makes them jagged on Windows).
    f.setHintingPreference(QFont.PreferNoHinting)
    f.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(f)


def set_tooltip_palette(P: dict) -> None:
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QToolTip
    pal = QToolTip.palette()
    pal.setColor(QPalette.ToolTipBase, QColor(P["card"]))
    pal.setColor(QPalette.ToolTipText, QColor(P["text"]))
    QToolTip.setPalette(pal)


def mono_font(size: float = 9.5) -> QFont:
    for fam in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier New"):
        if fam in QFontDatabase.families():
            f = QFont(fam)
            f.setPointSizeF(size)
            return f
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSizeF(size)
    return f


def symbol_font(size: float = 13) -> QFont:
    for fam in ("Cambria Math", "Segoe UI Symbol", "DejaVu Sans"):
        if fam in QFontDatabase.families():
            f = QFont(fam)
            f.setPointSizeF(size)
            return f
    return QFont("sans-serif", int(size))


# ---------------------------------------------------------------- images <-> Qt
def qimage(img: Image.Image) -> QImage:
    img = img.convert("RGBA")
    return QImage(img.tobytes("raw", "RGBA"), img.width, img.height, 4 * img.width,
                  QImage.Format_RGBA8888).copy()


def qpixmap(img: Image.Image, dpr: float = 1.0) -> QPixmap:
    pm = QPixmap.fromImage(qimage(img))
    pm.setDevicePixelRatio(dpr)
    return pm


ICON = {"style": "gradient"}          # effective icon style, set by the main window


def effective_icon_style(choice: str, flat: bool) -> str:
    import icons
    return choice if choice in icons.STYLES else ("line" if flat else "gradient")


def icon_pixmap(name: str, px: int, kind: str = "tile", active: bool = False) -> QPixmap:
    """Tool icon in the chosen style (vector, rendered at 2x so it stays sharp on high-DPI screens).

    kind: "tile" (cards, on the page background), "nav" (sidebar), "hero" (on the coloured page header)."""
    import icons
    P = theme.STATE.pal
    style = ICON["style"]
    acc = P["accent"]
    if kind == "hero" and P["flat"]:      # flat header: a small tinted chip, whatever the icon style
        return icons.styled_pixmap(name, px, "soft", acc, mix(acc, P["card"], 0.86), "", 2.0)
    if style == "gradient":
        return icons.tile_pixmap(name, px, 2.0)
    acc = P["accent"]
    if kind == "hero":
        # the header is solid accent: white glyph on a translucent tile
        if style == "line":
            return icons.styled_pixmap(name, px, "line", P["on_accent"], dpr=2.0)
        return icons.styled_pixmap(name, px, "outlined", P["on_accent"], rgba(P["on_accent"], 0.14), rgba(P["on_accent"], 0.45), 2.0)
    if kind == "nav":
        col = acc if active and P["flat"] else (P["on_accent"] if active else P["muted"] if style == "line" else acc)
        if style == "line":
            return icons.styled_pixmap(name, px, "line", col, dpr=2.0)
        fill = mix(acc, P["card"], 0.86)
        return icons.styled_pixmap(name, px, style, acc, fill, mix(acc, P["card"], 0.62), 2.0)
    return icons.styled_pixmap(name, px, style, acc, mix(acc, P["card"], 0.88), mix(acc, P["card"], 0.60), 2.0)


class IconLabel(QLabel):
    """A tool icon that redraws itself when the theme, accent or icon style changes."""
    _all: "weakref.WeakSet[IconLabel]" = weakref.WeakSet()

    def __init__(self, name: str, px: int, kind: str = "tile"):
        super().__init__()
        self.name, self.px, self.kind, self.active = name, px, kind, False
        self.setFixedSize(px, px)
        self.setAttribute(Qt.WA_TranslucentBackground)
        IconLabel._all.add(self)
        self.refresh()

    def refresh(self):
        self.setPixmap(icon_pixmap(self.name, self.px, self.kind, self.active))

    def set_active(self, on: bool):
        self.active = on
        self.refresh()


def refresh_icons():
    for w in list(IconLabel._all):
        try:
            w.refresh()
        except RuntimeError:
            pass


# ---------------------------------------------------------------- style sheet
def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgba(h: str, a: float) -> str:
    r, g, b = _hex_rgb(h)
    return f"rgba({r},{g},{b},{int(a * 255)})"


def mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_rgb(a)
    br, bg, bb = _hex_rgb(b)
    return "#%02x%02x%02x" % (int(ar + (br - ar) * t), int(ag + (bg - ag) * t), int(ab + (bb - ab) * t))


def _glyph_png(kind: str, color: str, size: int = 24) -> str:
    """Tiny checkmark / chevron images for the style sheet (QSS cannot draw them)."""
    d = Path(tempfile.gettempdir()) / "pdftoolkit_qss"
    d.mkdir(exist_ok=True)
    p = d / f"{kind}_{color.lstrip('#')}.png"
    if not p.exists():
        S = 4
        im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        c = _hex_rgb(color) + (255,)
        if kind == "check":
            dr.line([(5 * S, 12.5 * S), (10 * S, 17 * S), (19 * S, 7 * S)], fill=c, width=int(2.6 * S), joint="curve")
        elif kind == "close":
            dr.line([(7 * S, 7 * S), (17 * S, 17 * S)], fill=c, width=int(2.2 * S))
            dr.line([(17 * S, 7 * S), (7 * S, 17 * S)], fill=c, width=int(2.2 * S))
        else:
            dr.line([(6 * S, 9 * S), (12 * S, 15 * S), (18 * S, 9 * S)], fill=c, width=int(2.4 * S), joint="curve")
        im.resize((size, size), Image.LANCZOS).save(p)
    return str(p).replace("\\", "/")


@lru_cache(maxsize=48)
def build_qss(theme_name: str, strength: str, rtl: bool, accent: str = "", fa_font: str = "Vazirmatn", scale: float = 1.0) -> str:
    def sz(x: float) -> str:          # font sizes in the style sheet follow the text-size setting
        return f"{x * 0.88 * scale:.1f}pt"
    P = theme.resolve(theme_name, accent)
    flat = P["flat"]
    fam = ui_family()
    card_a = 1.0 if flat else STRENGTHS.get(strength, 0.8)
    border = P["line"]
    field = P["field"]
    fb = mix(field, P["text"], 0.20 if P["dark"] else 0.34)      # visible outline for inputs on every theme
    chk = _glyph_png("check", P["on_accent"])
    arrow = _glyph_png("chev", P["text"])
    xclose = _glyph_png("close", P["text"])
    xclose_on = _glyph_png("close", P["on_accent"])
    align = "right" if rtl else "left"
    edge = "right" if not rtl else "left"
    if flat:
        sidebar_css = f"background: {P['sidebar']}; border: none; border-{edge}: 1px solid {border};"
        card_css = f"background: {P['card']}; border: 1px solid {border}; border-radius: 14px;"
        tile_css = f"background: {P['card']}; border: 1px solid {border}; border-radius: 14px;"
        tile_hover = f"background: {P['card']}; border: 1px solid {P['accent']};"
        hero_css = "background: transparent; border: none; border-radius: 0;"
        hero_title, hero_sub = P["text"], P["muted"]
        nav_on_bg, nav_on_text = rgba(P["accent"], 0.13), P["accent"]
    else:
        sidebar_css = f"background: {rgba(P['sidebar'], min(1.0, card_a + 0.06))}; border: none;"
        card_css = f"background: {rgba(P['card'], card_a)}; border-radius: 18px;"
        tile_css = f"background: {rgba(P['field'], min(1.0, card_a + 0.04))}; border: 1px solid {fb}; border-radius: 16px;"
        tile_hover = f"background: {rgba(P['hover'], 1.0)};"
        hero_css = (f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {rgba(mix(P['accent'], '#000000', 0.18), 0.96)}, "
                    f"stop:1 {rgba(mix(P['accent'], P['bg'], 0.30), 0.82)}); border-radius: 20px;")
        hero_title, hero_sub = P["on_accent"], rgba(P["on_accent"], 0.9)
        nav_on_bg, nav_on_text = P["accent"], P["on_accent"]
    return f"""
* {{ font-family: "{fam}", "Inter", "Vazirmatn", "Segoe UI"; color: {P['text']}; outline: 0; }}
QWidget#root, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame#sidebar {{ {sidebar_css} }}
QFrame#card {{ {card_css} }}
QFrame#tile {{ {tile_css} }}
QFrame#tile:hover {{ {tile_hover} }}
QFrame#hero {{ {hero_css} }}
QFrame#paper {{ background: #ffffff; border-radius: 12px; }}
QLabel {{ background: transparent; }}
QLabel#heroTitle {{ color: {hero_title}; font-size: {sz(19 if flat else 21)}; font-weight: 700; }}
QLabel#heroSub {{ color: {hero_sub}; font-size: {sz(10.5)}; }}
QLabel[role="muted"] {{ color: {P['muted']}; }}
QLabel[role="h"] {{ font-size: {sz(12)}; font-weight: 700; }}
QLabel[role="good"] {{ color: {P['good']}; }}
QLabel[role="tileTitle"] {{ font-size: {sz(11.5)}; font-weight: 700; }}
QPushButton#searchbar {{ background: {field}; border: 1px solid {fb}; border-radius: 12px; padding: 0 16px; text-align: {align}; color: {P['muted']}; font-weight: 400; }}
QPushButton#searchbar:hover {{ border-color: {P['accent']}; }}
QPushButton#recentrow {{ background: transparent; border: 1px solid {border}; border-radius: 10px; padding: 9px 14px; text-align: left; font-weight: 500; }}
QPushButton#recentrow:hover {{ background: {P['hover']}; }}
QLabel#logoText {{ font-size: {sz(15)}; font-weight: 700; }}

QPushButton {{ background: {field}; border: 1px solid {fb}; border-radius: 11px; padding: 8px 16px; font-weight: 500; }}
QPushButton:hover {{ background: {P['hover']}; }}
QPushButton:pressed {{ background: {mix(P['hover'], P['accent'], 0.25)}; }}
QPushButton[kind="primary"] {{ background: {P['accent']}; color: {P['on_accent']}; font-weight: 700; border: 1px solid {P['accent']}; }}
QPushButton[kind="primary"]:hover {{ background: {P['accent_hover']}; }}
QPushButton:disabled {{ background: {field}; color: {P['muted']}; }}
QPushButton[kind="primary"]:disabled {{ background: {field}; color: {P['muted']}; }}
QPushButton#nav {{ background: transparent; border: 1px solid transparent; text-align: {align}; padding: 10px 12px; border-radius: 13px;
                  font-size: {sz(10.5)}; font-weight: 500; }}
QPushButton#nav:hover {{ background: {P['hover']}; }}
QPushButton#nav:checked {{ background: {nav_on_bg}; }}
QLabel#navText {{ font-size: {sz(10.5)}; font-weight: 500; }}
QLabel#navText[active="true"] {{ color: {nav_on_text}; font-weight: 700; }}
QPushButton[pill="true"] {{ background: {field}; border: 1px solid {fb}; border-radius: 15px; padding: 7px 22px; min-width: 76px; }}
QPushButton[pill="true"]:checked {{ background: {P['accent']}; color: {P['on_accent']}; font-weight: 700; }}
QPushButton[pill="true"]:hover:!checked {{ background: {P['hover']}; }}
QToolButton {{ background: transparent; border: none; border-radius: 12px; padding: 6px; }}
QToolButton:hover {{ background: {P['hover']}; }}
QToolButton[tb="true"] {{ padding: 7px; border-radius: 10px; border: 1px solid transparent; }}
QToolButton[tb="true"]:hover {{ background: {P['hover']}; }}
QToolButton[tb="true"]:checked {{ background: {rgba(P['accent'], 0.24)}; border: 1px solid {P['accent']}; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: {field}; border: 1px solid {fb}; border-radius: 10px; padding: 7px 28px 7px 14px; margin: 0 6px 2px 0;
               min-width: 90px; max-width: 260px; }}
QTabBar::tab:hover:!selected {{ background: {P['hover']}; }}
QTabBar::tab:selected {{ background: {P['accent']}; color: {P['on_accent']}; border-color: {P['accent']}; }}
QTabBar::close-button {{ image: url({xclose}); subcontrol-position: right; margin: 0 6px 0 0; width: 14px; height: 14px; }}
QTabBar::close-button:selected {{ image: url({xclose_on}); }}
QToolButton[swatch="true"] {{ border: 2px solid transparent; background: {field}; }}
QToolButton[swatch="true"]:checked {{ border: 2px solid {P['accent']}; }}
QToolButton[sym="true"] {{ background: {field}; border: 1px solid {fb}; border-radius: 8px; padding: 4px; }}
QToolButton[sym="true"]:hover {{ background: {P['accent']}; color: {P['on_accent']}; }}

QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QListWidget, QTreeWidget {{
    background: {field}; border: 1.5px solid {fb}; border-radius: 11px; padding: 6px 10px;
    selection-background-color: {P['accent']}; selection-color: {P['on_accent']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border: 1.5px solid {P['accent']}; }}
QListWidget, QTreeWidget {{ padding: 4px; }}
QTreeWidget::item {{ padding: 5px 6px; border-radius: 7px; }}
QTreeWidget::item:hover {{ background: {P['hover']}; }}
QTreeWidget::item:selected {{ background: {P['accent']}; color: {P['on_accent']}; }}
QListWidget::item {{ padding: 7px 10px; border-radius: 8px; }}
QListWidget::item:hover {{ background: {P['hover']}; }}
QListWidget::item:selected {{ background: {P['accent']}; color: {P['on_accent']}; }}
QComboBox {{ background: {field}; border: 1.5px solid {fb}; border-radius: 11px; padding: 7px 14px; min-height: 22px; }}
QComboBox:hover {{ background: {P['hover']}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: url({arrow}); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{ background: {P['card']}; border: 1px solid {border}; border-radius: 10px; padding: 4px;
    selection-background-color: {P['accent']}; selection-color: {P['on_accent']}; outline: 0; }}
QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 7px; border: 2px solid {P['muted']}; background: transparent; }}
QCheckBox::indicator:hover {{ border-color: {P['accent']}; }}
QCheckBox::indicator:checked {{ background: {P['accent']}; border-color: {P['accent']}; image: url({chk}); }}
QProgressBar {{ background: {field}; border: 1px solid {fb}; border-radius: 5px; max-height: 10px; min-height: 10px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {P['accent']}; border-radius: 5px; }}
QScrollBar:vertical {{ width: 12px; background: transparent; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {P['hover']}; border-radius: 5px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: {P['accent']}; }}
QScrollBar:horizontal {{ height: 12px; background: transparent; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {P['hover']}; border-radius: 5px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: {P['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QToolTip {{ background: {P['card']}; color: {P['text']}; border: 1px solid {border}; padding: 5px; border-radius: 6px; }}
QDialog {{ background: {P['bg']}; }}
QFrame#sep {{ background: {P['hover']}; max-height: 1px; min-height: 1px; }}
QLabel#toast {{ background: {P['accent']}; color: {P['on_accent']}; border-radius: 12px; padding: 9px 18px; font-weight: 600; }}
"""


# ---------------------------------------------------------------- backdrop
class Backdrop(QWidget):
    """Window background: one solid colour (the theme's)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self._bg = QColor("#12141a")

    def set_color(self, bg: str):
        self._bg = QColor(bg)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg)
        p.end()
