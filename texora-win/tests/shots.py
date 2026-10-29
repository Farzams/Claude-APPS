"""Offscreen screenshots of the main screens (development aid)."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from texora.qt import QtWidgets, QTimer
from texora import theme as th

class FakeEngine(object):
    from texora.qt import Signal
def main(out):
    app = QtWidgets.QApplication(sys.argv)
    th.load_fonts()
    from texora.engine import TexEngine
    from texora.window import MainWindow
    from texora.store import ProjectStore, HistoryStore, Prefs
    eng = TexEngine("/nonexistent")
    win = MainWindow(eng)
    win.show()
    def snap(n): win.grab().save(os.path.join(out, n + ".png"))
    app.processEvents(); snap("projects")
    st = win.store
    from texora import templates
    tpls = templates.all_templates()
    if not st.list():
        st.create("Demo paper", tpls[0]); st.create("Persian note", next(x for x in tpls if "persian" in x["key"]))
    p = st.list()[0]
    win.open_project(p); app.processEvents(); snap("editor")
    win.show_screen("settings"); app.processEvents(); snap("settings")
    print("shots ok")
main(sys.argv[1] if len(sys.argv) > 1 else "tests/out")
