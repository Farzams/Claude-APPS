"""The offline TeX engine: BusyTeX (XeTeX and pdfTeX compiled to WebAssembly) running in a hidden Qt WebEngine page.
The page and the engine files are served to it from this program over 127.0.0.1; nothing is downloaded and nothing
leaves the computer."""
import base64
import json
import mimetypes
import os
import posixpath
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .qt import QObject, QUrl, Signal, Slot, QtCore, QtWebChannel, QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineView

TEXT_EXT = {"tex", "sty", "cls", "bib", "bst", "txt", "def", "cfg", "clo", "fd", "bbx", "cbx", "lbx", "dbx", "ltx", "md", "csv", "dat"}
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".wasm": "application/wasm"}


class _Handler(BaseHTTPRequestHandler):
    root = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = posixpath.normpath(self.path.split("?", 1)[0])
        prefix = "/assets/tex/"
        if not (path + "/").startswith(prefix) or ".." in path.split("/"):
            return self._send(404, b"not found", "text/plain")
        rel = path[len(prefix):] if path != prefix[:-1] else ""
        full = os.path.join(self.root, *[p for p in rel.split("/") if p])
        if not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext) or mimetypes.guess_type(full)[0] or "application/octet-stream"
        size = os.path.getsize(full)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        # the engine's memory is shared memory, which newer browsers only give to cross-origin isolated pages
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.end_headers()
        try:
            with open(full, "rb") as f:
                shutil.copyfileobj(f, self.wfile, 1 << 20)
        except (BrokenPipeError, ConnectionError):
            pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(root):
    handler = type("Handler", (_Handler,), {"root": root})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


class _Bridge(QObject):
    ready = Signal()
    log = Signal(str)
    status = Signal(str)
    pdf = Signal(str)
    done = Signal(str)

    @Slot()
    def onReady(self):
        self.ready.emit()

    @Slot(str)
    def onLog(self, s):
        self.log.emit(s)

    @Slot(str)
    def onStatus(self, s):
        self.status.emit(s)

    @Slot(str)
    def onPdf(self, b64):
        self.pdf.emit(b64)

    @Slot(str)
    def onDone(self, j):
        self.done.emit(j)


class _Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, *args):
        # (level, message, line, source) in both Qt 5 and Qt 6
        try:
            msg = args[1]
            if "error" in str(args[0]).lower() or "Error" in msg:
                print("tex page:", msg, "@", args[3] if len(args) > 3 else "", args[2] if len(args) > 2 else "")
        except Exception:
            pass


# Makes the page believe it runs in the Android app: the same page and scripts are used on both systems.
_SHIM = """
(function () {
  var queue = [], br = null;
  function send(m, a) { if (br) { if (a === undefined) br[m](); else br[m](a); } else queue.push([m, a]); }
  window.Android = {
    onReady: function () { send('onReady'); }, onLog: function (s) { send('onLog', String(s)); },
    onStatus: function (s) { send('onStatus', String(s)); }, onPdf: function (b) { send('onPdf', b); },
    onDone: function (j) { send('onDone', j); }
  };
  new QWebChannel(qt.webChannelTransport, function (ch) {
    br = ch.objects.bridge;
    queue.forEach(function (x) { if (x[1] === undefined) br[x[0]](); else br[x[0]](x[1]); });
    queue = [];
  });
})();
"""


class TexEngine(QObject):
    """compile() starts a compilation; finished(ok, exit_code, log, pdf_bytes) arrives when it is over."""
    status = Signal(str)
    log = Signal(str)
    finished = Signal(bool, int, str, object)
    ready = Signal()

    def __init__(self, asset_root, parent=None):
        super(TexEngine, self).__init__(parent)
        self.asset_root = asset_root
        self.server = None
        self.view = None
        self.is_ready = False
        self.busy = False
        self._pdf = None
        self._queued = None
        self.bridge = _Bridge()
        self.bridge.ready.connect(self._on_ready)
        self.bridge.log.connect(self.log)
        self.bridge.status.connect(self.status)
        self.bridge.pdf.connect(self._on_pdf)
        self.bridge.done.connect(self._on_done)

    def start(self):
        if self.view is not None:
            return
        self.server = start_server(self.asset_root)
        port = self.server.server_address[1]
        self.view = QWebEngineView()
        # off the record: no cached copy of the engine data that could go stale or break between Qt versions
        self.profile = QWebEngineProfile(self.view)
        page = _Page(self.profile, self.view)
        self.view.setPage(page)
        channel = QtWebChannel.QWebChannel(page)
        channel.registerObject("bridge", self.bridge)
        page.setWebChannel(channel)
        js = QtCore.QFile(":/qtwebchannel/qwebchannel.js")
        js.open(QtCore.QIODevice.ReadOnly)
        lib = bytes(js.readAll()).decode("utf-8")
        js.close()
        script = QWebEngineScript()
        script.setName("android-shim")
        script.setSourceCode(lib + "\n" + _SHIM)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        page.scripts().insert(script)
        page.renderProcessTerminated.connect(self._on_crash)
        self.view.resize(8, 8)
        self.view.load(QUrl("http://127.0.0.1:%d/assets/tex/tex_host.html" % port))

    def _on_ready(self):
        self.is_ready = True
        self.ready.emit()
        if self._queued:
            q, self._queued = self._queued, None
            self.compile(*q)

    def _on_crash(self, *args):
        self.is_ready = False
        if self.busy:
            self.busy = False
            self.finished.emit(False, -1, "The TeX engine stopped (not enough memory?).", None)
        self.status.emit("engine-crashed")

    def _on_pdf(self, b64):
        self._pdf = base64.b64decode(b64)

    def _on_done(self, j):
        o = json.loads(j)
        self.busy = False
        ok = bool(o.get("ok"))
        self.finished.emit(ok, int(o.get("exit", -1)), o.get("log", ""), self._pdf if ok else None)

    def compile(self, files, main, driver="xetex_bibtex8_dvipdfmx"):
        """files: list of (path, bytes)."""
        if not self.is_ready:
            self._queued = (files, main, driver)
            return
        if self.busy:
            self.finished.emit(False, -1, "A compilation is already running.", None)
            return
        self.busy = True
        self._pdf = None
        arr = []
        for path, data in files:
            o = {"path": path}
            if os.path.splitext(path)[1][1:].lower() in TEXT_EXT:
                o["text"] = data.decode("utf-8", "replace")
            else:
                o["b64"] = base64.b64encode(data).decode("ascii")
            arr.append(o)
        req = json.dumps({"main": main, "driver": driver, "files": arr})
        self.view.page().runJavaScript("compileProject(" + json.dumps(req) + ")")

    def shutdown(self):
        if self.view is not None:
            self.view.setPage(None) if hasattr(self.view, "setPage") else None
            self.view.deleteLater()
            self.view = None
        if self.server is not None:
            self.server.shutdown()
            self.server = None
