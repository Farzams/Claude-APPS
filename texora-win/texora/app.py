"""Entry point: python -m texora"""
import os
import sys


def asset_root():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "tex"), os.path.join(here, "..", "assets", "tex"),
              os.path.join(os.path.dirname(sys.executable), "assets", "tex")):
        if os.path.isfile(os.path.join(p, "tex_host.html")):
            return os.path.normpath(p)
    return os.path.normpath(os.path.join(here, "..", "assets", "tex"))


def main(argv=None):
    # the engine page needs no graphics card: this also helps on old Windows machines
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")      # the formula preview then needs no OpenGL driver at all
    from .qt import QtWidgets, QtGui, run_app, prepare
    from . import theme as th
    from .engine import TexEngine
    from .window import MainWindow
    from . import __version__

    prepare()
    app = QtWidgets.QApplication(list(argv if argv is not None else sys.argv))
    app.setApplicationName("TeXora")
    app.setApplicationVersion(__version__)
    th.load_fonts()
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.isfile(icon):
        app.setWindowIcon(QtGui.QIcon(icon))
    engine = TexEngine(asset_root())
    if "--selftest" in sys.argv:
        return selftest(app, engine, sys.argv[sys.argv.index("--selftest") + 1])
    win = MainWindow(engine)
    win.show()
    engine.start()
    args = [x for x in sys.argv[1:] if not x.startswith("-")]
    if args and os.path.isfile(args[0]) and args[0].lower().endswith(".tex"):      # "Open with TeXora" from Explorer
        win.open_folder(os.path.dirname(os.path.abspath(args[0])), os.path.basename(args[0]))
    elif args and os.path.isdir(args[0]):
        win.open_folder(os.path.abspath(args[0]))
    code = run_app(app)
    engine.shutdown()
    return code


def selftest(app, engine, out):
    """Starts the engine, compiles a Persian page, renders it and writes a JSON report; used by the build."""
    import json
    import time
    from .qt import QTimer
    from . import templates
    from .window import MainWindow
    res = {"steps": []}
    win = MainWindow(engine)
    win.show()
    for key in ("projects", "settings"):
        win.show_screen(key)
        app.processEvents()
        res["steps"].append("screen " + key)
    tpl = next(x for x in templates.all_templates() if x["key"] == "tpl.persian")
    t0 = time.time()

    def done(ok, code, log, pdf):
        res["compile_ok"], res["seconds"] = bool(ok), round(time.time() - t0, 1)
        res["log_tail"] = log[-1500:]
        if ok and pdf:
            import fitz
            doc = fitz.open(stream=pdf, filetype="pdf")
            res["pages"] = doc.page_count
            res["text_chars"] = len(doc[0].get_text())
        finish()

    def finish():
        res["ok"] = bool(res.get("compile_ok")) and res.get("pages", 0) >= 1
        with open(out, "w") as f:
            json.dump(res, f, indent=1)
        sys.stdout.flush()
        os._exit(0 if res["ok"] else 1)      # WebEngine can crash while the process shuts down: the report is already written

    engine.finished.connect(done)
    engine.ready.connect(lambda: engine.compile([(n, c.encode("utf-8")) for n, c in tpl["files"].items()], tpl["main"]))
    QTimer.singleShot(420000, lambda: (res.update(error="timeout"), finish()))
    engine.start()
    code = app.exec_() if hasattr(app, "exec_") else app.exec()
    engine.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
