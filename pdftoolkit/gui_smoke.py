"""Starts the real window (English or Persian), visits every page and switches theme/picture."""
import os
import sys
import tempfile
import time
from pathlib import Path

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
tmp = tempfile.mkdtemp()
os.environ["APPDATA"] = tmp
Path(tmp, "PDFToolkit").mkdir()
Path(tmp, "PDFToolkit", "settings.json").write_text('{"lang": "%s", "theme": "indigo_night"}' % lang)
sys.path.insert(0, str(Path(__file__).parent))

import app  # noqa: E402

a = app.App()
t0 = time.time()
for _ in range(30):
    a.update()
    time.sleep(0.02)
for key, _, _ in a.TOOLS + a.EXTRA:
    a.show(key)
    for _ in range(4):
        a.update()
for th in ("daylight", "gold", "rose"):
    a.set_theme(th)
    a.update()
for wp in ("waves", "mountains", "lowpoly", "bokeh", "dots", "plain", "aurora"):
    a.set_wallpaper(wp)
    a.update()
a.show_palette()
for _ in range(6):
    a.update()
a._palette.show_cat("Analysis")
a.update()
a._palette.destroy()
a._palette = None
print(f"PASS gui {lang}: {len(a.pages)} pages, theme+picture switching ok, {time.time() - t0:.1f}s")
a.destroy()
