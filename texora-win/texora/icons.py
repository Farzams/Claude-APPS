"""Small line icons (24x24, stroke only) drawn from SVG strings in the colour of the theme."""
from .qt import QtCore, QtGui, QtSvg

_P = {
    "new": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M12 11v6M9 14h6"/>',
    "open": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "save": '<path d="M5 3h11l4 4v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M8 3v5h7V3M8 21v-7h8v7"/>',
    "undo": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "redo": '<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1"/>',
    "find": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.5-4.5"/>',
    "bold": '<path d="M7 5h6a3.5 3.5 0 0 1 0 7H7zM7 12h7a3.5 3.5 0 0 1 0 7H7z"/>',
    "italic": '<path d="M19 4h-9M14 20H5M15 4L9 20"/>',
    "underline": '<path d="M7 4v7a5 5 0 0 0 10 0V4M5 21h14"/>',
    "math": '<path d="M18 6H8l5 6-5 6h10"/>',
    "zoomin": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.5-4.5M11 8v6M8 11h6"/>',
    "zoomout": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.5-4.5M8 11h6"/>',
    "fitwidth": '<path d="M3 12h18M7 8l-4 4 4 4M17 8l4 4-4 4"/>',
    "fitpage": '<rect x="6" y="3" width="12" height="18" rx="1"/>',
    "twopages": '<rect x="3" y="4" width="8" height="16" rx="1"/><rect x="13" y="4" width="8" height="16" rx="1"/>',
    "print": '<path d="M6 9V3h12v6M6 18H4a1 1 0 0 1-1-1v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1h-2"/><rect x="6" y="14" width="12" height="7"/>',
    "pdf": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M8 14h2a1.5 1.5 0 0 0 0-3H8v6M14 17v-6h1.5a2.5 2.5 0 0 1 0 6z"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "tex": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M8 13h6M11 13v5"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="M21 16l-5-5-8 8"/>',
    "bib": '<path d="M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h10"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "check": '<path d="M5 12l5 5L20 7"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "pages": '<rect x="5" y="3" width="11" height="14" rx="1"/><path d="M8 21h11a1 1 0 0 0 1-1V7"/>',
    "log": '<path d="M4 4h16v16H4zM8 9l3 3-3 3M13 15h4"/>',
    "sigma": '<path d="M18 5H6l6 7-6 7h12"/>',
    "tools": '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 13l-8 8-4-4 8-8zM3 21l5-5"/>',
    "up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "comment": '<path d="M4 5h16v11H9l-5 4z"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1"/>',
}
_cache = {}


def icon(name, color="#333333", size=20):
    key = (name, color, size)
    if key in _cache:
        return _cache[key]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.8" '
           'stroke-linecap="round" stroke-linejoin="round">%s</svg>') % (color, _P.get(name, _P["file"]))
    r = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    ratio = 2
    pm = QtGui.QPixmap(size * ratio, size * ratio)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    r.render(p)
    p.end()
    pm.setDevicePixelRatio(ratio)
    ic = QtGui.QIcon(pm)
    _cache[key] = ic
    return ic
