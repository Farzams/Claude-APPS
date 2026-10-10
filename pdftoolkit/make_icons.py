"""Writes icon.ico, reader.ico and math.ico from the vector tiles (run once; the .ico files are committed)."""
import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

import icons

app = QApplication([])


def tile_image(name: str, px: int) -> Image.Image:
    pm = icons.tile_pixmap(name, px, 1.0)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    pm.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


for name, glyph in (("icon", "tools"), ("reader", "read"), ("math", "math")):
    big = tile_image(glyph, 256)
    big.save(Path(__file__).with_name(name + ".ico"), format="ICO",
             sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    print("wrote", name + ".ico")
