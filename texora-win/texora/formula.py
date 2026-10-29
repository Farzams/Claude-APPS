"""Live formula preview: the formula under the cursor, drawn by KaTeX in a small web view."""
import json
import os

from .qt import QtWidgets, QUrl, QWebEngineProfile, QWebEngineView, QWebEnginePage, Qt
from . import strings

_HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="katex.min.css"><script src="katex.min.js"></script>
<style>
html,body{margin:0;height:100%%}
body{background:%(bg)s;color:%(fg)s;font-family:sans-serif;display:flex;align-items:center;justify-content:center;overflow:auto}
#out{padding:10px 16px;font-size:%(size)spx;max-width:100%%}
#msg{color:%(muted)s;font-size:14px;text-align:center;padding:12px;direction:%(dir)s}
</style></head><body><div id="out"></div><div id="msg"></div>
<script>
function show(tex, display, macros, errText){
  var out=document.getElementById('out'), msg=document.getElementById('msg');
  try { katex.render(tex, out, {displayMode:display, throwOnError:true, strict:'ignore', macros:macros||{}}); msg.textContent=''; }
  catch(e){ out.textContent=''; msg.textContent=errText+': '+String(e.message||e).replace(/^KaTeX parse error: /,''); }
}
function note(text){ document.getElementById('out').textContent=''; document.getElementById('msg').textContent=text; }
</script></body></html>"""


class FormulaPanel(QtWidgets.QWidget):
    def __init__(self, katex_dir, theme, parent=None):
        super(FormulaPanel, self).__init__(parent)
        self.dir = katex_dir
        self.theme = theme
        self.loaded = False
        self.pending = None
        self.last = None
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.view = None
        self.label = QtWidgets.QLabel(strings.t("formula.offline"))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("muted")
        lay.addWidget(self.label)
        self.available = os.path.isfile(os.path.join(katex_dir, "katex.min.js"))

    def _ensure_view(self):
        if self.view is not None or not self.available:
            return
        self.view = QWebEngineView(self)
        # off the record, like the TeX engine's page: nothing is stored on disk
        self.profile = QWebEngineProfile(self.view)
        self.view.setPage(QWebEnginePage(self.profile, self.view))
        self.layout().addWidget(self.view)
        self.label.hide()
        p, th = self.theme.pal, self.theme
        html = _HTML % dict(bg=p.field, fg=p.text, muted=p.muted, size=24, dir="rtl" if th.fa else "ltr")
        # a tiny local server: a page made in memory may not read files from the disk directly
        from .engine import start_server
        self.server = start_server(self.dir, "/katex/", {"/katex/formula.html": (html.encode("utf-8"), "text/html; charset=utf-8")})
        self.view.loadFinished.connect(self._ready)
        self.view.load(QUrl("http://127.0.0.1:%d/katex/formula.html" % self.server.server_address[1]))

    def _ready(self, ok):
        self.loaded = bool(ok)
        if self.pending:
            js, self.pending = self.pending, None
            self.view.page().runJavaScript(js)

    def _run(self, js):
        self._ensure_view()
        if self.view is None:
            return
        if self.loaded:
            self.view.page().runJavaScript(js)
        else:
            self.pending = js

    def show_formula(self, latex, display, macros):
        key = (latex, display, json.dumps(macros, sort_keys=True))
        if key == self.last:
            return
        self.last = key
        self._run("show(%s,%s,%s,%s)" % (json.dumps(latex), "true" if display else "false", json.dumps(macros),
                                         json.dumps(strings.t("formula.error"))))

    def show_note(self, text):
        if self.last == ("note", text):
            return
        self.last = ("note", text)
        self._run("note(%s)" % json.dumps(text))

    def shutdown(self):
        if self.view is not None:
            self.view.setPage(None) if hasattr(self.view, "setPage") else None
            self.view.deleteLater()
            self.view = None
        if getattr(self, "server", None) is not None:
            try:
                self.server.shutdown()
            except Exception:
                pass
            self.server = None
