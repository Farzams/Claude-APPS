"""PDF Toolkit - read, OCR, extract, convert, split, merge, compress, images, page tools, LaTeX, formulas.

Qt interface: English and Persian (right-to-left), 9 colour themes, picture backdrop, colourful icons.
"""
from __future__ import annotations

import sys

import i18n
import settings
import theme


def main() -> int:
    import multiprocessing
    multiprocessing.freeze_support()      # the math calculator runs in a child process
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
