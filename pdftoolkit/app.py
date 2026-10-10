"""PDF Toolkit - read, OCR, extract, convert, split, merge, compress, images, page tools, LaTeX, formulas.

Qt interface: English and Persian (right-to-left), 9 colour themes, picture backdrop, colourful icons.
"""
from __future__ import annotations

import sys

import i18n
import settings
import theme


def main() -> int:
    cfg = settings.load()
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
    win = MainWindow(cfg)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
