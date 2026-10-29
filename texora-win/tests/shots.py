"""Offscreen screenshots of the main screens (development aid).  Usage: python tests/shots.py <out-dir> [theme] [lang]"""
import os
import sys
os.environ.setdefault("QT_QUICK_BACKEND", "software")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from texora.qt import QtWidgets, QTimer, prepare
from texora import theme as th


def main(out, theme="qp_light", lang="en"):
    os.makedirs(out, exist_ok=True)
    prepare()
    app = QtWidgets.QApplication(sys.argv)
    th.load_fonts()
    from texora.engine import TexEngine
    from texora.window import MainWindow
    from texora.store import Prefs
    from texora import templates
    prefs = Prefs()
    prefs.d.update(theme=theme, lang=lang)
    win = MainWindow(TexEngine("/nonexistent"), prefs=prefs)
    win.resize(1360, 860)
    win.show()
    st = win.store
    tpls = templates.all_templates()
    if not st.list():
        st.create("Demo paper", next(x for x in tpls if x["key"] == "tpl.physics"))
        st.create("Persian note", next(x for x in tpls if "persian" in x["key"]))
    win.projects.refresh()

    def snap(n):
        for _ in range(5):
            app.processEvents()
        win.grab().save(os.path.join(out, n + ".png"))
    snap("projects")
    p = [x for x in st.list() if "Demo" in x.name][0]
    win.open_project(p)
    snap("editor")
    ep = win.editor_page
    ep.editor.go_to_line(24)
    ep.dock_struct.raise_()
    import fitz
    pdf = os.path.join(ep.project.path, "demo.pdf")
    d = fitz.open()
    pg = d.new_page()
    pg.insert_text((72, 100), "The state of a quantum system evolves", fontsize=14)
    d.save(pdf)
    ep.pdf_path = pdf
    ep.preview.load(pdf)
    c = ep.editor.textCursor()
    text = ep.editor.toPlainText()
    c.setPosition(text.index("\\hat{A}") + 3)
    ep.editor.setTextCursor(c)
    ep.dock_formula.raise_()
    ep.dock_formula.show()
    import time
    t0 = time.time()
    while time.time() - t0 < 4:
        app.processEvents()
    ep.update_formula()
    t0 = time.time()
    while time.time() - t0 < 3:
        app.processEvents()
    snap("editor_structure")
    win.show_screen("settings")
    snap("settings")
    print("shots ok")


main(*sys.argv[1:])
