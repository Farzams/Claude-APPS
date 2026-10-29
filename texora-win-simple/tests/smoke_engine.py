"""Compiles the Welcome template and an English/Persian one through the real engine; renders page 1 of the PDF.
Needs the TeX assets (tools/fetch_assets.py) and a Qt binding with WebEngine.  Usage: python tests/smoke_engine.py <assets/tex>"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from texora.qt import QtWidgets, QTimer, run_app  # noqa: E402
from texora.engine import TexEngine  # noqa: E402
from texora import templates  # noqa: E402

assets = sys.argv[1]
app = QtWidgets.QApplication([])
engine = TexEngine(assets)
tpls = {t["key"]: t for t in templates.all_templates()}
jobs = [("tpl.article", "xetex_bibtex8_dvipdfmx"), ("tpl.persian", "xetex_bibtex8_dvipdfmx"), ("tpl.physics", "pdftex_bibtex8")]
state = {"i": 0, "t0": 0.0, "failed": []}


def next_job():
    if state["i"] >= len(jobs):
        print("RESULT", "FAILED " + ",".join(state["failed"]) if state["failed"] else "ALL OK")
        app.quit()
        return
    key, driver = jobs[state["i"]]
    t = tpls[key]
    files = [(n, c.encode("utf-8")) for n, c in t["files"].items()]
    if key == "tpl.persian":      # the fonts come with the engine files, as in the Android app
        pass
    state["t0"] = time.time()
    engine.compile(files, t["main"], driver)


def on_done(ok, code, log, pdf):
    key = jobs[state["i"]][0]
    print("compile", key, "ok=%s exit=%s pdf=%s in %.0fs" % (ok, code, len(pdf) if pdf else 0, time.time() - state["t0"]), flush=True)
    if not ok:
        print(log[-2500:])
        state["failed"].append(key)
    state["i"] += 1
    QTimer.singleShot(100, next_job)


engine.finished.connect(on_done)
engine.log.connect(lambda s: print("tex:", s[:160]) if os.environ.get("TEX_VERBOSE") else None)
engine.start()
QTimer.singleShot(8 * 60 * 1000, lambda: (print("RESULT TIMEOUT"), app.quit()))
engine.ready.connect(next_job)
run_app(app)
sys.exit(1 if state["failed"] else 0)
