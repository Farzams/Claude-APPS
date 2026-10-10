"""Settings > Add-ons: list, install and remove optional packs."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

import addons
import i18n
from i18n import tr, trf
from qt_common import mkbutton, mklabel


class _Sig(QObject):
    manifest = Signal(object, str)
    progress = Signal(str, int, int)
    finished = Signal(str)


class _FetchJob(QRunnable):
    def __init__(self, s: _Sig):
        super().__init__()
        self.s = s

    def run(self):
        try:
            self.s.manifest.emit(addons.fetch_manifest(), "")
        except Exception as e:
            self.s.manifest.emit([], str(e) or e.__class__.__name__)


class _InstallJob(QRunnable):
    def __init__(self, s: _Sig, entry: dict):
        super().__init__()
        self.s, self.entry = s, entry

    def run(self):
        err = ""
        try:
            addons.install(self.entry, lambda stage, d, t: self.s.progress.emit(stage, d, t))
        except Exception as e:
            err = str(e) or e.__class__.__name__
        self.s.finished.emit(err)


class AddonsPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.sig = _Sig()
        self.sig.manifest.connect(self._manifest)
        self.sig.progress.connect(self._progress)
        self.sig.finished.connect(self._finished)
        self.entries: list[dict] = []
        self.rows: dict[str, dict] = {}
        self.busy = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(mklabel("Add-ons", "h"))
        lay.addWidget(mklabel("Optional extras. Download one when you need it; it stays on this computer, works offline "
                              "and can be removed again.", "muted", wrap=True))
        self.status = mklabel("", "muted", wrap=True, translate=False)
        lay.addWidget(self.status)
        self.box = QVBoxLayout()
        self.box.setSpacing(8)
        lay.addLayout(self.box)
        row = QHBoxLayout()
        row.addWidget(mkbutton("Refresh the list", self.refresh))
        row.addStretch(1)
        lay.addLayout(row)
        self.loaded = False

    def on_show(self):
        if not self.loaded:
            self.refresh()

    def refresh(self):
        self.loaded = True
        self.status.setText(tr("Loading the list…"))
        QThreadPool.globalInstance().start(_FetchJob(self.sig))

    def _manifest(self, entries, err):
        local = addons.installed()
        self.entries = list(entries)
        known = {e["id"] for e in entries}
        for aid, meta in local.items():                    # installed packs stay visible when offline
            if aid not in known:
                self.entries.append({"id": aid, "title": meta.get("title", aid), "desc": "", "size_mb": meta.get("size_mb", 0)})
        self.status.setText(trf("Could not reach the add-on list ({err}). Check your internet connection.", err=err) if err and not entries else "")
        self._build()

    def _build(self):
        while self.box.count():
            it = self.box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.rows = {}
        lang = i18n.LANG
        for e in self.entries:
            f = QFrame()
            f.setObjectName("tile")
            hl = QHBoxLayout(f)
            hl.setContentsMargins(16, 12, 16, 12)
            col = QVBoxLayout()
            col.setSpacing(3)
            col.addWidget(mklabel(addons.lang_text(e, "title", lang), "tileTitle", translate=False))
            d = addons.lang_text(e, "desc", lang)
            if d:
                col.addWidget(mklabel(d, "muted", wrap=True, translate=False))
            size = e.get("size_mb")
            st = mklabel("", "muted", translate=False)
            col.addWidget(st)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            bar.hide()
            col.addWidget(bar)
            hl.addLayout(col, 1)
            btn = mkbutton("Install", lambda e=e: self._toggle(e), "primary", 120)
            hl.addWidget(btn, 0, Qt.AlignVCenter)
            self.box.addWidget(f)
            self.rows[e["id"]] = dict(btn=btn, bar=bar, st=st, size=size)
        self._sync()

    def _sync(self):
        inst = addons.installed()
        for aid, r in self.rows.items():
            on = aid in inst
            size = f"~{int(r['size'])} MB" if r["size"] else ""
            r["st"].setText((tr("Installed") + ("   ·   " + size if size else "")) if on else size)
            r["btn"].setText(tr("Remove") if on else tr("Install"))
            r["btn"].setProperty("kind", "field" if on else "primary")
            r["btn"].style().unpolish(r["btn"])
            r["btn"].style().polish(r["btn"])
            r["btn"].setEnabled(self.busy is None)

    def _toggle(self, entry: dict):
        if self.busy:
            return
        aid = entry["id"]
        if addons.is_installed(aid):
            addons.remove(aid)
            self.win.toast("Removed")
            self._sync()
            self._notify()
            return
        if not entry.get("url"):
            return self.win.warn(tr("Cannot install"), tr("This add-on cannot be downloaded right now."))
        self.busy = aid
        r = self.rows[aid]
        r["bar"].show()
        r["bar"].setValue(0)
        r["st"].setText(tr("Downloading…"))
        self._sync()
        QThreadPool.globalInstance().start(_InstallJob(self.sig, entry))

    def _progress(self, stage: str, done: int, total: int):
        r = self.rows.get(self.busy or "")
        if not r:
            return
        if stage == "download":
            r["bar"].setValue(int(done * 1000 / max(total, 1)))
            r["st"].setText(trf("Downloading… {a} of {b} MB", a=done // 1048576, b=max(total // 1048576, 1)))
        elif stage == "unpack":
            r["bar"].setValue(1000)
            r["st"].setText(tr("Unpacking…"))

    def _finished(self, err: str):
        aid, self.busy = self.busy, None
        r = self.rows.get(aid or "")
        if r:
            r["bar"].hide()
        self._sync()
        if err:
            self.win.warn(tr("Cannot install"), err)
        else:
            self.win.toast("Installed")
            self._notify()

    def _notify(self):
        for pg in self.win.pages.values():
            fn = getattr(pg, "addons_changed", None)
            if fn:
                fn()
