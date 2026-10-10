"""Starts the real Qt window (English or Persian), visits every page and switches theme/picture."""
import os
import sys
import tempfile
import time
from pathlib import Path

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
tmp = tempfile.mkdtemp()
os.environ["APPDATA"] = tmp
os.environ["LOCALAPPDATA"] = tmp
if sys.platform != "win32" and "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
Path(tmp, "PDFToolkit").mkdir()
Path(tmp, "PDFToolkit", "settings.json").write_text('{"lang": "%s", "theme": "indigo_night", "wallpaper": "aurora"}' % lang)
sys.path.insert(0, str(Path(__file__).parent))

import i18n  # noqa: E402
import settings  # noqa: E402
import theme  # noqa: E402

cfg = settings.load()
i18n.set_lang(cfg["lang"])
theme.set_theme(cfg["theme"])

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import qt_style  # noqa: E402

app = QApplication([])
app.setStyle("Fusion")
qt_style.load_fonts()
qt_style.apply_app_font(app)
if i18n.rtl():
    app.setLayoutDirection(Qt.RightToLeft)
from qt_main import PAGES, MainWindow  # noqa: E402

t0 = time.time()
win = MainWindow(cfg)
win.show()
for _ in range(30):
    app.processEvents()
    time.sleep(0.02)
for key, _title, _cls in PAGES:
    win.show_page(key)
    app.processEvents()
for th in ("daylight", "gold", "rose", "sunset"):
    win.set_theme(th)
    app.processEvents()
for wp in ("waves", "mountains", "lowpoly", "bokeh", "dots", "plain", "aurora"):
    win.set_wallpaper(wp)
    app.processEvents()
win.set_strength("vivid")
win.show_palette()
app.processEvents()
win._palette.show_cat("Analysis")
app.processEvents()
shot = win.grab()
assert not shot.isNull() and shot.width() > 500
print(f"PASS gui {lang}: {len(win.pages)} pages, theme+picture switching ok, {time.time() - t0:.1f}s")
