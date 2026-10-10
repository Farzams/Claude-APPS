"""PDF Toolkit - read, OCR, extract, convert, split, merge, compress, images, page tools, LaTeX, formulas.

Qt interface: English and Persian (right-to-left), 9 colour themes, picture backdrop, colourful icons.
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

    def math_worker():
        import mathproc
        r = mathproc.WORKER.run("simplify", {"expr": "(x^2-1)/(x-1)"}, 120)
        mathproc.WORKER.stop()
        assert r.text == "x + 1", r.text
        return r.text

    def latex_parse():
        import mathcore
        return mathcore.simplify(r"\frac{x^2-1}{x-1}").text

    def plot():
        import mathcore
        return len(mathcore.plot("sin(x)", "x", -3, 3).png)

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

    def spell_():
        import spell
        spell.CHECKER.load()
        assert spell.CHECKER.ready, "dictionaries did not load: " + spell.CHECKER.error[-600:]
        assert not spell.CHECKER.check("algbra") and spell.CHECKER.check("algebra"), "wrong spell-check answers"
        return "en+fa dictionaries"

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

    def addons_():
        import addons
        return str(addons.addons_dir())

    for name, fn in (("math worker (child process)", math_worker), ("sympy latex parser", latex_parse),
                     ("matplotlib plot", plot), ("opencv", opencv), ("pikepdf", pikepdf_), ("pdf2docx", pdf2docx_),
                     ("spell dictionaries", spell_), ("openpyxl", openpyxl_), ("svg icons", icons_),
                     ("add-ons folder", addons_)):
        t(name, fn)
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
    except OSError:
        pass
    return 1 if any(v.startswith("FAIL") for v in res.values()) else 0


def main() -> int:
    import multiprocessing
    multiprocessing.freeze_support()      # the math calculator runs in a child process
    if "--selftest" in sys.argv:           # used by the build to check the frozen program itself
        i = sys.argv.index("--selftest")
        return selftest(sys.argv[i + 1] if i + 1 < len(sys.argv) else "selftest.json")
    mode, files = "full", []
    argv = sys.argv[1:]
    while argv:
        a = argv.pop(0)
        if a == "--mode" and argv:
            mode = argv.pop(0)
        elif not a.startswith("--"):
            files.append(a)
    from modes import MODES
    mode = mode if mode in MODES else "full"
    if sys.platform == "win32":            # own taskbar entry per mode
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MODES[mode]["aumid"])
        except Exception:
            pass
    cfg = settings.load()
    try:
        import addons
        addons.activate()                 # installed add-ons become importable
    except Exception:
        pass
    cfg.setdefault("strength", "medium")
    i18n.set_lang(cfg["lang"])
    theme.set_theme(cfg["theme"])

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
    win = MainWindow(cfg, mode)
    win.show()
    if files:
        from PySide6.QtCore import QTimer
        def open_files():
            if mode == "full":
                win.show_page("read")
            for f in files:
                win.page("read").open_path(f)
        QTimer.singleShot(200, open_files)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
