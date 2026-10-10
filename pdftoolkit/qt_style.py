"""Qt look: fonts, colour themes as a style sheet, and the wallpaper behind everything."""
from __future__ import annotations

import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

import art
import i18n
import theme

FONT_DIR = art.FONT_DIR
STRENGTHS = {"off": 1.0, "subtle": 0.92, "medium": 0.80, "vivid": 0.62}   # card opacity over the picture
OVERLAY = {"off": 1.0, "subtle": 0.78, "medium": 0.52, "vivid": 0.26}     # veil over the picture itself


# ---------------------------------------------------------------- fonts
def load_fonts() -> None:
    for f in ("Inter-Regular.otf", "Inter-Medium.otf", "Inter-SemiBold.otf", "Inter-Bold.otf",
              "Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf", "Vazirmatn-Bold.ttf",
              "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        p = FONT_DIR / f
        if p.is_file():
            QFontDatabase.addApplicationFont(str(p))


def ui_family() -> str:
    return "Vazirmatn" if i18n.rtl() else "Inter"


def apply_app_font(app: QApplication, size: float = 10.5) -> None:
    f = QFont(ui_family())
    f.setFamilies([ui_family(), "Inter", "Vazirmatn", "Segoe UI", "Tahoma"])
    f.setPointSizeF(size)
    app.setFont(f)


def set_tooltip_palette(P: dict) -> None:
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QToolTip
    pal = QToolTip.palette()
    pal.setColor(QPalette.ToolTipBase, QColor(P["card"]))
    pal.setColor(QPalette.ToolTipText, QColor(P["text"]))
    QToolTip.setPalette(pal)


def mono_font(size: float = 10.5) -> QFont:
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


@lru_cache(maxsize=96)
def icon_pixmap(name: str, px: int) -> QPixmap:
    """Colourful tool icon, rendered at 2x so it stays sharp on high-DPI screens."""
    return qpixmap(art.icon(name, px * 2), 2.0)


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
        else:
            dr.line([(6 * S, 9 * S), (12 * S, 15 * S), (18 * S, 9 * S)], fill=c, width=int(2.4 * S), joint="curve")
        im.resize((size, size), Image.LANCZOS).save(p)
    return str(p).replace("\\", "/")


@lru_cache(maxsize=48)
def build_qss(theme_name: str, strength: str, rtl: bool) -> str:
    P = theme.THEMES[theme_name]
    fam = ui_family()
    card_a = STRENGTHS.get(strength, 0.8)
    border = mix(P["card"], P["text"], 0.14)
    field = P["field"]
    chk = _glyph_png("check", P["on_accent"])
    arrow = _glyph_png("chev", P["text"])
    align = "right" if rtl else "left"
    return f"""
* {{ font-family: "{fam}", "Inter", "Vazirmatn", "Segoe UI"; color: {P['text']}; outline: 0; }}
QWidget#root, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame#sidebar {{ background: {rgba(P['sidebar'], min(1.0, card_a + 0.06))}; border: none; }}
QFrame#card {{ background: {rgba(P['card'], card_a)}; border-radius: 18px; }}
QFrame#tile {{ background: {rgba(P['field'], min(1.0, card_a + 0.04))}; border-radius: 16px; }}
QFrame#tile:hover {{ background: {rgba(P['hover'], 1.0)}; }}
QFrame#hero {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {rgba(mix(P['accent'], '#000000', 0.18), 0.96)},
              stop:1 {rgba(mix(P['accent'], P['bg'], 0.30), 0.82)}); border-radius: 20px; }}
QFrame#paper {{ background: #ffffff; border-radius: 12px; }}
QLabel {{ background: transparent; }}
QLabel#heroTitle {{ color: {P['on_accent']}; font-size: 21pt; font-weight: 700; }}
QLabel#heroSub {{ color: {rgba(P['on_accent'], 0.9)}; font-size: 10.5pt; }}
QLabel[role="muted"] {{ color: {P['muted']}; }}
QLabel[role="h"] {{ font-size: 12pt; font-weight: 700; }}
QLabel[role="good"] {{ color: {P['good']}; }}
QLabel[role="tileTitle"] {{ font-size: 11.5pt; font-weight: 700; }}
QLabel#logoText {{ font-size: 15pt; font-weight: 700; }}

QPushButton {{ background: {field}; border: none; border-radius: 11px; padding: 8px 16px; font-weight: 500; }}
QPushButton:hover {{ background: {P['hover']}; }}
QPushButton:pressed {{ background: {mix(P['hover'], P['accent'], 0.25)}; }}
QPushButton[kind="primary"] {{ background: {P['accent']}; color: {P['on_accent']}; font-weight: 700; }}
QPushButton[kind="primary"]:hover {{ background: {P['accent_hover']}; }}
QPushButton:disabled {{ background: {field}; color: {P['muted']}; }}
QPushButton[kind="primary"]:disabled {{ background: {field}; color: {P['muted']}; }}
QPushButton#nav {{ background: transparent; text-align: {align}; padding: 10px 12px; border-radius: 13px;
                  font-size: 10.5pt; font-weight: 500; }}
QPushButton#nav:hover {{ background: {P['hover']}; }}
QPushButton#nav:checked {{ background: {P['accent']}; }}
QLabel#navText {{ font-size: 10.5pt; font-weight: 500; }}
QLabel#navText[active="true"] {{ color: {P['on_accent']}; font-weight: 700; }}
QPushButton[pill="true"] {{ background: {field}; border-radius: 15px; padding: 7px 22px; min-width: 76px; }}
QPushButton[pill="true"]:checked {{ background: {P['accent']}; color: {P['on_accent']}; font-weight: 700; }}
QPushButton[pill="true"]:hover:!checked {{ background: {P['hover']}; }}
QToolButton {{ background: transparent; border: none; border-radius: 12px; padding: 6px; }}
QToolButton:hover {{ background: {P['hover']}; }}
QToolButton[swatch="true"] {{ border: 2px solid transparent; background: {field}; }}
QToolButton[swatch="true"]:checked {{ border: 2px solid {P['accent']}; }}
QToolButton[sym="true"] {{ background: {field}; border-radius: 8px; padding: 4px; }}
QToolButton[sym="true"]:hover {{ background: {P['accent']}; color: {P['on_accent']}; }}

QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QListWidget {{
    background: {field}; border: 1.5px solid transparent; border-radius: 11px; padding: 6px 10px;
    selection-background-color: {P['accent']}; selection-color: {P['on_accent']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border: 1.5px solid {P['accent']}; }}
QListWidget {{ padding: 4px; }}
QListWidget::item {{ padding: 7px 10px; border-radius: 8px; }}
QListWidget::item:hover {{ background: {P['hover']}; }}
QListWidget::item:selected {{ background: {P['accent']}; color: {P['on_accent']}; }}
QComboBox {{ background: {field}; border: none; border-radius: 11px; padding: 7px 14px; min-height: 22px; }}
QComboBox:hover {{ background: {P['hover']}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: url({arrow}); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{ background: {P['card']}; border: 1px solid {border}; border-radius: 10px; padding: 4px;
    selection-background-color: {P['accent']}; selection-color: {P['on_accent']}; outline: 0; }}
QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 7px; border: 2px solid {P['muted']}; background: transparent; }}
QCheckBox::indicator:hover {{ border-color: {P['accent']}; }}
QCheckBox::indicator:checked {{ background: {P['accent']}; border-color: {P['accent']}; image: url({chk}); }}
QProgressBar {{ background: {field}; border: none; border-radius: 5px; max-height: 10px; min-height: 10px; text-align: center; color: transparent; }}
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


# ---------------------------------------------------------------- wallpaper
class Backdrop(QWidget):
    """Window background: the chosen picture under a veil, so cards and text stay readable."""

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self._img: QImage | None = None
        self._bg = QColor("#12141a")
        self._veil = 0.7
        self._cache: tuple[QSize, QPixmap] | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._rescale)
        self._sharp = True

    def set_picture(self, img: QImage | None, bg: str, veil: float):
        self._img, self._bg, self._veil = img, QColor(bg), veil
        self._cache = None
        self._sharp = True
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sharp = False
        self._timer.start(120)

    def _rescale(self):
        self._sharp = True
        self._cache = None
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg)
        if self._img is not None and not self._img.isNull():
            size = self.size() * self.devicePixelRatioF()
            if self._cache is None or self._cache[0] != size:
                mode = Qt.SmoothTransformation if self._sharp else Qt.FastTransformation
                scaled = QPixmap.fromImage(self._img).scaled(size, Qt.KeepAspectRatioByExpanding, mode)
                x, y = (scaled.width() - size.width()) // 2, (scaled.height() - size.height()) // 2
                scaled = scaled.copy(x, y, size.width(), size.height())
                scaled.setDevicePixelRatio(self.devicePixelRatioF())
                self._cache = (size, scaled)
            p.drawPixmap(0, 0, self._cache[1])
            veil = QColor(self._bg)
            veil.setAlphaF(self._veil)
            p.fillRect(self.rect(), veil)
        p.end()


def wallpaper_image(style: str, pal: dict, custom: str = "") -> QImage | None:
    """The picture for the chosen style (None = plain colour)."""
    try:
        if style == "custom" and custom and Path(custom).is_file():
            return qimage(art._custom_cover(custom, (1600, 900)))
        return qimage(art._wall_cached(style if style in art.WALLPAPERS else "aurora", 1280, 720,
                                       pal["accent"], pal["bg"], pal["dark"], "", 7))
    except Exception:
        return None
