"""Starts the real Qt window (English or Persian), visits every page and switches theme/picture."""
import os
import sys
import tempfile
import time
from pathlib import Path

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
mode = sys.argv[2] if len(sys.argv) > 2 else "full"
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
win = MainWindow(cfg, mode)
win.show()
for _ in range(30):
    app.processEvents()
    time.sleep(0.02)
for key, _title, _cls in PAGES:
    if mode != "full" and key not in win.keys:
        continue
    win.show_page(key)
    app.processEvents()
for th in ("daylight", "gold", "rose", "sunset", "qp_light", "qp_dark", "paper", "paper_dark"):
    win.set_theme(th)
    app.processEvents()
for acc in ("#be185d", ""):
    win.set_accent(acc)
    app.processEvents()
for st in ("line", "soft", "outlined", "gradient", "auto"):
    win.set_icon_style(st)
    app.processEvents()
win.set_text_scale(1.1)
win.set_text_scale(1.0)
win.show_page("settings")
for sec in win.page("settings").sections:
    win.page("settings").show_section(sec)
    app.processEvents()
win.palette_box.open()
win.palette_box.edit.setText("water" if mode == "full" else "settings")
app.processEvents()
assert win.palette_box.list.count() >= 1, "palette search found nothing"
win.palette_box.close()
win.set_theme("indigo_night")
for wp in ("waves", "mountains", "lowpoly", "bokeh", "dots", "plain", "aurora"):
    win.set_wallpaper(wp)
    app.processEvents()
win.set_strength("vivid")
win.show_palette()
app.processEvents()
win._palette.show_cat("Analysis")
app.processEvents()
# reader: open a PDF, an EPUB-like text file and a Persian search, then close
import core  # noqa: E402
win.show_page("read")
rd = win.page("read")
pdf = str(Path(tmp, "r.pdf"))
core.html_to_pdf("<h1>Reader test</h1><p>Hello سلام دنیا</p>", pdf, "a5")
txt = Path(tmp, "r.txt")
txt.write_text("سلام دنیا\nhello\n", encoding="utf-8")
for f in (pdf, str(txt)):
    n = len(rd.docs)
    rd.open_path(f)
    for _ in range(300):
        app.processEvents()
        time.sleep(0.02)
        if len(rd.docs) > n:
            break
    assert len(rd.docs) > n, f"reader did not open {f}"
rd.q.setText("دنیا")
rd.start_search()
for _ in range(100):
    app.processEvents()
    time.sleep(0.02)
assert rd.cur.hits, "Persian search found nothing"
rd.cycle_mode()
for _ in range(20):
    app.processEvents()
    time.sleep(0.02)
for i in range(len(rd.docs) - 1, -1, -1):
    rd.close_tab(i)
shot = win.grab()
assert not shot.isNull() and shot.width() > 500
print(f"PASS gui {lang} {mode}: {len(win.pages)} pages, theme+picture switching ok, {time.time() - t0:.1f}s")
