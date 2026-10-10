"""Modern vector icons: line glyphs (24x24 grid, round caps) drawn as SVG, on gradient tiles or alone.

Everything is rendered by Qt's SVG engine at device resolution, so icons stay sharp at any scale.
"""
from __future__ import annotations

from functools import lru_cache

# stroke-only glyphs (24 x 24). "f:" prefix marks a filled sub-shape.
GLYPHS: dict[str, list[str]] = {
    "home": ["M3 11.5 12 4l9 7.5", "M5.5 10v9.5h13V10", "M10 19.5v-5.5h4v5.5"],
    "read": ["M12 6.5v13", "M12 6.5C10 4.8 6.5 4.4 3 5.4v13.2c3.5-1 7-.6 9 1 2-1.6 5.5-2 9-1V5.4c-3.5-1-7-.6-9 1.1z"],
    "ocr": ["M4 8.5V6a2 2 0 0 1 2-2h2.5", "M15.5 4H18a2 2 0 0 1 2 2v2.5", "M20 15.5V18a2 2 0 0 1-2 2h-2.5",
            "M8.5 20H6a2 2 0 0 1-2-2v-2.5", "M8 9.5h8", "M8 12.5h8", "M8 15.5h5"],
    "extract": ["M6.5 3.5h7.5l4 4v13H6.5z", "M14 3.5v4h4", "M9.5 12h5", "M9.5 15.5h5"],
    "convert": ["M4 8h13.5", "M14 4.5 17.5 8 14 11.5", "M20 16H6.5", "M10 12.5 6.5 16l3.5 3.5"],
    "split": ["M5 3.5h14v7H5z", "M5 13.5h14v7H5z", "M2.5 12h2", "M8 12h2", "M14 12h2", "M19.5 12h2"],
    "merge": ["M5 4l7 7", "M19 4l-7 7", "M12 11v9", "M8.5 16.5 12 20l3.5-3.5"],
    "compress": ["M4 14h6v6", "M20 10h-6V4", "M14 10l7-7", "M3 21l7-7"],
    "images": ["M3.5 5h17v14h-17z", "c:9 10 1.6", "M3.5 17l5-5 4 4 3-3 5 5"],
    "pages": ["M4 4h7v7H4z", "M13 4h7v7h-7z", "M4 13h7v7H4z", "M13 13h7v7h-7z"],
    "crop": ["M6 2.5v14a2 2 0 0 0 2 2h13.5", "M18 21.5V8a2 2 0 0 0-2-2H2.5"],
    "blank": ["M6.5 3.5h7.5l4 4v13H6.5z", "M14 3.5v4h4", "M3 3l18 18"],
    "headerfooter": ["M4 4.5h16v15H4z", "M4 9h16", "M4 15h16"],
    "watermark": ["M12 3.5s6 6.3 6 10.5a6 6 0 0 1-12 0c0-4.2 6-10.5 6-10.5z", "M9.5 14.5a2.6 2.6 0 0 0 2.5 2.5"],
    "background": ["M12 3.5 21 8.5 12 13.5 3 8.5z", "M3 12.5l9 5 9-5", "M3 16.5l9 5 9-5"],
    "compare": ["M3.5 4.5h7.5v15H3.5z", "M13 4.5h7.5v15H13z", "M6 9h2.5", "M6 12.5h2.5", "M15.5 9H18", "M15.5 12.5H18"],
    "export": ["M12 3.5v11", "M8 10.5l4 4 4-4", "M4.5 17v3h15v-3"],
    "security": ["M6 11h12v9.5H6z", "M8.5 11V7.5a3.5 3.5 0 0 1 7 0V11", "M12 14.5v2.5"],
    "hidden": ["M3 12s3.6-6.5 9-6.5 9 6.5 9 6.5-3.6 6.5-9 6.5S3 12 3 12z", "c:12 12 2.6", "M4 4l16 16"],
    "redact": ["M4 6.5h16", "M4 17.5h16", "M4 12h5", "f:M11.5 9.5h8.5v5h-8.5z"],
    "edit": ["M4 20l1-4.5L16.5 4a2.1 2.1 0 0 1 3 3L8 18.5z", "M14.5 6l3.5 3.5"],
    "batch": ["M8.5 6.5H20", "M8.5 12H20", "M8.5 17.5H20", "M4 6.5h.01", "M4 12h.01", "M4 17.5h.01"],
    "settings": ["M4 7h9", "M17 7h3", "M4 12h3", "M11 12h9", "M4 17h11", "M19 17h1", "c:15 7 2", "c:9 12 2", "c:17 17 2"],
    "help": ["c:12 12 8.5", "M9.6 9.5a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.2 1-1.2 1.8", "M12 16.8h.01"],
    "latex": ["M8.5 4C6.5 4 5.5 5 5.5 7v2c0 1.2-.9 2.4-2 3 1.1.6 2 1.8 2 3v2c0 2 1 3 3 3",
              "M15.5 4c2 0 3 1 3 3v2c0 1.2.9 2.4 2 3-1.1.6-2 1.8-2 3v2c0 2-1 3-3 3"],
    "formula": ["M18 4.5H6.5l6 7.5-6 7.5H18"],
    "search": ["c:10.5 10.5 6.5", "M15.5 15.5 21 21"],
    "clean": ["M10 3l1.7 4.8L16.5 9.5l-4.8 1.7L10 16l-1.7-4.8L3.5 9.5l4.8-1.7z", "M18 14v5", "M15.5 16.5h5", "M18.5 4v3", "M17 5.5h3"],
    "repair": ["M12 3.5l7 2.8v5.2c0 4.6-3 7.8-7 9.5-4-1.7-7-4.9-7-9.5V6.3z", "M9 12l2.2 2.2L15.5 10"],
    "math": ["M5 4.5h14", "M5 19.5h14", "M8 8l8 8", "M16 8l-8 8"],
    "formulaocr": ["M4 8.5V6a2 2 0 0 1 2-2h2.5", "M15.5 4H18a2 2 0 0 1 2 2v2.5", "M20 15.5V18a2 2 0 0 1-2 2h-2.5",
                   "M8.5 20H6a2 2 0 0 1-2-2v-2.5", "M15 8.5H9.5l2.5 3.5-2.5 3.5H15"],
    "tools": ["M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3z", "M14.5 6.5 17 9"],
    # reader / toolbar glyphs
    "open": ["M3.5 7.5v11a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1V9.5a1 1 0 0 0-1-1h-7.5l-2-2.5H4.5a1 1 0 0 0-1 1z"],
    "close": ["M6 6l12 12", "M18 6 6 18"],
    "plus": ["M12 5v14", "M5 12h14"],
    "minus": ["M5 12h14"],
    "prev": ["M14.5 6 8.5 12l6 6"],
    "next": ["M9.5 6l6 6-6 6"],
    "up": ["M6 14.5l6-6 6 6"],
    "down": ["M6 9.5l6 6 6-6"],
    "sidebar": ["M3.5 5h17v14h-17z", "M9.5 5v14"],
    "thumbs": ["M4 4h6.5v6.5H4z", "M13.5 4H20v6.5h-6.5z", "M4 13.5h6.5V20H4z", "M13.5 13.5H20V20h-6.5z"],
    "outline": ["M9 6.5h11", "M9 12h11", "M9 17.5h11", "M4 6.5h1.5", "M4 12h1.5", "M4 17.5h1.5"],
    "bookmark": ["M6.5 3.5h11v17L12 16.5l-5.5 4z"],
    "sun": ["c:12 12 3.8", "M12 2.5v2.2", "M12 19.3v2.2", "M2.5 12h2.2", "M19.3 12h2.2", "M5.3 5.3l1.6 1.6",
            "M17.1 17.1l1.6 1.6", "M5.3 18.7l1.6-1.6", "M17.1 6.9l1.6-1.6"],
    "moon": ["M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"],
    "page": ["M6.5 3.5h7.5l4 4v13H6.5z", "M14 3.5v4h4"],
    "spread": ["M3 5.5h8.5v13H3z", "M12.5 5.5H21v13h-8.5z"],
    "fit": ["M4 9V5h4", "M16 5h4v4", "M20 15v4h-4", "M8 19H4v-4"],
    "fullscreen": ["M4 9V4h5", "M15 4h5v5", "M20 15v5h-5", "M9 20H4v-5"],
    "copy": ["M8.5 8.5h11v11h-11z", "M5.5 15.5h-1v-11h11v1"],
    "text": ["M5 6.5V5h14v1.5", "M12 5v14", "M9.5 19h5"],
    "folder": ["M3.5 7.5v11a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1V9.5a1 1 0 0 0-1-1h-7.5l-2-2.5H4.5a1 1 0 0 0-1 1z"],
    "rotate": ["M20 11a8 8 0 1 0-2.3 5.7", "M20 4.5V11h-6.5"],
    "trash": ["M4.5 6.5h15", "M9.5 6.5V4h5v2.5", "M6.5 6.5l1 13.5h9l1-13.5", "M10 10.5v6", "M14 10.5v6"],
    "check": ["M5 12.5l4.5 4.5L19 7.5"],
    "star": ["M12 3.8l2.5 5.2 5.7.8-4.1 4 1 5.7-5.1-2.7-5.1 2.7 1-5.7-4.1-4 5.7-.8z"],
    "history": ["M3.5 12a8.5 8.5 0 1 0 2.6-6.1", "M3.5 4.5v4h4", "M12 7.5V12l3 2"],
    "book": ["M5.5 4h10.5a2 2 0 0 1 2 2v14H7.5a2 2 0 0 1-2-2z", "M5.5 18a2 2 0 0 1 2-2H18"],
}

# gradient pairs for tile icons (start, end)
COLORS: dict[str, tuple[str, str]] = {
    "home": ("#6366f1", "#22d3ee"), "read": ("#6366f1", "#a855f7"), "ocr": ("#ec4899", "#f97316"),
    "extract": ("#14b8a6", "#22d3ee"), "convert": ("#f59e0b", "#f97316"), "split": ("#ef4444", "#f97316"),
    "merge": ("#22c55e", "#14b8a6"), "compress": ("#0ea5e9", "#6366f1"), "images": ("#a855f7", "#ec4899"),
    "pages": ("#84cc16", "#22c55e"), "settings": ("#64748b", "#94a3b8"), "help": ("#3b82f6", "#22d3ee"),
    "latex": ("#0ea5e9", "#2563eb"), "formula": ("#f59e0b", "#ef4444"), "crop": ("#06b6d4", "#3b82f6"),
    "blank": ("#94a3b8", "#64748b"), "headerfooter": ("#8b5cf6", "#6366f1"), "watermark": ("#0ea5e9", "#14b8a6"),
    "background": ("#f472b6", "#a855f7"), "compare": ("#f97316", "#ef4444"), "export": ("#10b981", "#06b6d4"),
    "security": ("#475569", "#0ea5e9"), "hidden": ("#7c3aed", "#db2777"), "redact": ("#1f2937", "#6b7280"),
    "edit": ("#f59e0b", "#ec4899"), "batch": ("#6366f1", "#06b6d4"), "tools": ("#6366f1", "#8b5cf6"),
    "search": ("#3b82f6", "#6366f1"), "clean": ("#8b5cf6", "#22d3ee"), "repair": ("#22c55e", "#0ea5e9"),
    "math": ("#6366f1", "#ec4899"), "formulaocr": ("#f59e0b", "#ec4899"),
}


def _glyph_svg(name: str, stroke: str, width: float) -> str:
    out = []
    for d in GLYPHS.get(name, GLYPHS["page"]):
        if d.startswith("c:"):
            cx, cy, r = d[2:].split()
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>')
        elif d.startswith("f:"):
            out.append(f'<path d="{d[2:]}" fill="{stroke}" stroke="none"/>')
        else:
            out.append(f'<path d="{d}"/>')
    return (f'<g fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round">{"".join(out)}</g>')


def tile_svg(name: str) -> str:
    """Rounded gradient tile with a white glyph, soft highlight and shadow."""
    c1, c2 = COLORS.get(name, ("#6366f1", "#22d3ee"))
    glyph = _glyph_svg(name, "#ffffff", 1.9)
    shadow = _glyph_svg(name, "#000000", 1.9).replace('<g ', '<g opacity="0.22" transform="translate(0 .7)" ')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>
<linearGradient id="h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="46" height="46" rx="13" fill="url(#g)"/>
<rect x="1" y="1" width="46" height="46" rx="13" fill="url(#h)"/>
<rect x="1.5" y="1.5" width="45" height="45" rx="12.5" fill="none" stroke="#fff" stroke-opacity=".22"/>
<g transform="translate(10 10) scale(1.1667)">{shadow}{glyph}</g>
</svg>'''


def glyph_svg(name: str, color: str, width: float = 1.9) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{_glyph_svg(name, color, width)}</svg>')


@lru_cache(maxsize=256)
def _render(svg: str, px: int, dpr: float):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer
    r = QSvgRenderer(QByteArray(svg.encode()))
    size = int(px * dpr)
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    r.render(p)
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    return pm


def tile_pixmap(name: str, px: int, dpr: float = 2.0):
    return _render(tile_svg(name), px, dpr)


def glyph_pixmap(name: str, px: int, color: str, dpr: float = 2.0, width: float = 1.9):
    return _render(glyph_svg(name, color, width), px, dpr)


def glyph_icon(name: str, color: str, px: int = 20):
    from PySide6.QtGui import QIcon
    return QIcon(glyph_pixmap(name, px, color))


# ---------------------------------------------------------------- icon styles
STYLES = ("line", "soft", "outlined", "gradient")


def styled_svg(name: str, style: str, color: str, fill: str = "", edge: str = "", width: float = 1.8) -> str:
    """The same glyph drawn as plain line, on a soft tinted tile, or on an outlined tile (gradient = classic tile)."""
    if style == "gradient":
        return tile_svg(name)
    g = _glyph_svg(name, color, width)
    if style == "line":
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{g}</svg>'
    bg = f'<rect x="0.75" y="0.75" width="46.5" height="46.5" rx="13" fill="{fill or "none"}"'
    bg += f' stroke="{edge}" stroke-width="1.5"/>' if style == "outlined" else ' stroke="none"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">{bg}<g transform="translate(11 11) scale(1.0833)">{g}</g></svg>'


def styled_pixmap(name: str, px: int, style: str, color: str, fill: str = "", edge: str = "", dpr: float = 2.0):
    return _render(styled_svg(name, style, color, fill, edge), px, dpr)


def flat_tile_svg(color: str, name: str) -> str:
    """Flat-colour app icon: one solid rounded square with a white glyph."""
    g = _glyph_svg(name, "#ffffff", 1.9)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect x="1" y="1" width="46" height="46" rx="12" fill="{color}"/>'
            f'<g transform="translate(10 10) scale(1.1667)">{g}</g></svg>')


APP_COLORS = {"tools": "#4f46e5", "read": "#0f766e", "math": "#be185d"}


def app_icon_pixmap(name: str, px: int, dpr: float = 1.0):
    return _render(flat_tile_svg(APP_COLORS.get(name, "#4f46e5"), name), px, dpr)
