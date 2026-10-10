"""Optional add-on packs (Settings > Add-ons): download once, keep, remove any time.

A pack is a zip file published in the GitHub release `pdftoolkit-addons`, listed in `addons.json` there:
  {"version": 1, "addons": [{"id", "title", "desc", "title_fa", "desc_fa", "size_mb", "url", "sha256",
                              "kind": "libs" | "texcache", "version"}]}
kind "libs"     -> unpacked to %LOCALAPPDATA%/PDFToolkit/addons/<id>/ ; its lib/ folder joins the import path
kind "texcache" -> unpacked into the LaTeX package cache (more packages available offline)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

DEFAULT_URL = "https://github.com/Farzams/Claude-APPS/releases/download/pdftoolkit-addons/addons.json"
UA = {"User-Agent": "PDFToolkit-addons/1"}


def manifest_url() -> str:
    return os.environ.get("PDFTK_ADDONS_URL", DEFAULT_URL)


def addons_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    d = Path(base) / "PDFToolkit" / "addons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def path(addon_id: str) -> Path:
    return addons_dir() / addon_id


def info(addon_id: str) -> dict | None:
    try:
        return json.loads((path(addon_id) / "addon.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def installed() -> dict[str, dict]:
    out = {}
    for d in addons_dir().iterdir():
        meta = info(d.name) if d.is_dir() else None
        if meta:
            out[d.name] = meta
    return out


def is_installed(addon_id: str) -> bool:
    return info(addon_id) is not None


def activate() -> None:
    """Make installed packs importable (call once at start-up)."""
    for addon_id in installed():
        lib = path(addon_id) / "lib"
        if lib.is_dir() and str(lib) not in sys.path:
            sys.path.append(str(lib))          # after the program's own libraries: never shadows them


def fetch_manifest(timeout: float = 12.0) -> list[dict]:
    req = urllib.request.Request(manifest_url(), headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return list(data.get("addons", []))


def _safe_extract(zf: zipfile.ZipFile, dest: Path, progress=None) -> list[str]:
    """Unpack, refusing paths that escape `dest`. Returns the files that did not exist before."""
    root = dest.resolve()
    members = zf.infolist()
    created = []
    for i, m in enumerate(members):
        target = (dest / m.filename).resolve()
        if root != target and root not in target.parents:
            raise RuntimeError("The add-on contains an unsafe path")
        if not m.is_dir() and not target.exists():
            created.append(m.filename)
        zf.extract(m, dest)
        if progress and i % 50 == 0:
            progress(i, len(members))
    return created


def install(entry: dict, progress: Callable[[str, int, int], None] | None = None,
            cancel: Callable[[], bool] | None = None) -> None:
    """Download, verify (SHA-256) and unpack one add-on. progress(stage, done, total)."""
    say = progress or (lambda *_a: None)
    addon_id, url = entry["id"], entry["url"]
    tmpdir = Path(tempfile.mkdtemp(prefix="pdftk_addon_"))
    zpath = tmpdir / "pack.zip"
    try:
        req = urllib.request.Request(url, headers=UA)
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=30) as r, open(zpath, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0) or int(entry.get("size_mb", 0) * 1024 * 1024)
            done = 0
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                if cancel and cancel():
                    raise RuntimeError("Cancelled")
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                say("download", done, total)
        want = (entry.get("sha256") or "").lower()
        if want and h.hexdigest() != want:
            raise RuntimeError("The download is damaged (checksum does not match). Try again.")
        say("unpack", 0, 1)
        kind = entry.get("kind", "libs")
        final = path(addon_id)
        stage = addons_dir() / (addon_id + ".new")
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        created: list[str] = []
        with zipfile.ZipFile(zpath) as zf:
            if kind == "texcache":
                import texengine
                created = _safe_extract(zf, texengine.cache_dir(), lambda i, n: say("unpack", i, n))
            else:
                _safe_extract(zf, stage, lambda i, n: say("unpack", i, n))
        meta = {"id": addon_id, "version": entry.get("version", "1"), "kind": kind, "title": entry.get("title", addon_id),
                "size_mb": entry.get("size_mb", 0)}
        if kind == "texcache":
            meta["files"] = created               # only files this pack added are removed again
        (stage / "addon.json").write_text(json.dumps(meta), encoding="utf-8")
        shutil.rmtree(final, ignore_errors=True)
        stage.rename(final)
        activate()
        say("done", 1, 1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        shutil.rmtree(addons_dir() / (addon_id + ".new"), ignore_errors=True)


def remove(addon_id: str) -> None:
    meta = info(addon_id) or {}
    lib = str(path(addon_id) / "lib")
    if lib in sys.path:
        sys.path.remove(lib)
    if meta.get("kind") == "texcache":
        import texengine
        root = texengine.cache_dir()
        for rel in meta.get("files", []):
            try:
                (root / rel).unlink()
            except OSError:
                pass
    shutil.rmtree(path(addon_id), ignore_errors=True)


def lang_text(entry: dict, key: str, lang: str) -> str:
    return entry.get(f"{key}_{lang}") or entry.get(key) or ""
