"""PDF Toolkit - OCR, convert, split, merge, compress, images, page tools and more.

Qt interface: English and Persian (right-to-left), colour themes, icon styles.
"""
from __future__ import annotations

import sys

import i18n
import settings
import theme


def selftest(outfile: str) -> int:
    """Exercise the parts that most often break in a packaged build; write the results as JSON."""
    import json
    import traceback
    res: dict[str, str] = {}

    def t(name, fn):
        try:
            res[name] = "ok: " + str(fn())[:80]
        except BaseException:
            res[name] = "FAIL: " + traceback.format_exc()[-400:]

    def opencv():
        import cv2
        import numpy as np
        return cv2.fastNlMeansDenoising(np.zeros((40, 40), np.uint8)).shape

    def pikepdf_():
        import pikepdf
        import pymupdf
        with pymupdf.open() as d:
            d.new_page()
            data = d.tobytes()
        import io
        with pikepdf.open(io.BytesIO(data)) as p:
            return len(p.pages)

    def pdf2docx_():
        import pdf2docx  # noqa: F401
        return "import"

    def openpyxl_():
        import openpyxl
        return openpyxl.__version__

    def icons_():
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.instance() or QGuiApplication([])
        import icons
        pm = icons.tile_pixmap("read", 48, 2.0)
        assert not pm.isNull()
        return pm.width()

    def ocr_():
        import core
        langs = core.ocr_languages()
        assert {"eng", "fas", "ara"} <= set(langs), "OCR languages missing: " + str(langs)
        return ",".join(sorted(langs))

    for name, fn in (("opencv", opencv), ("pikepdf", pikepdf_), ("pdf2docx", pdf2docx_), ("openpyxl", openpyxl_),
                     ("svg icons", icons_), ("OCR languages", ocr_)):
        t(name, fn)
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
    except OSError:
        pass
    return 1 if any(v.startswith("FAIL") for v in res.values()) else 0


def main() -> int:
    if "--selftest" in sys.argv:           # used by the build to check the frozen program itself
        i = sys.argv.index("--selftest")
        return selftest(sys.argv[i + 1] if i + 1 < len(sys.argv) else "selftest.json")
    cfg = settings.load()
    i18n.set_lang(cfg["lang"])
    import qt_style as _qs
    _qs.TEXT_SCALE["scale"] = float(cfg.get("text_scale", 1.0))
    _qs.FA_FONT["name"] = cfg.get("fa_font", "Vazirmatn")
    theme.set_theme(cfg["theme"], cfg.get("accent", ""))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    import qt_style
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qt_style.load_fonts()
    qt_style.apply_app_font(app)
    if i18n.rtl():
        app.setLayoutDirection(Qt.RightToLeft)
    from qt_main import MainWindow
    win = MainWindow(cfg)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
