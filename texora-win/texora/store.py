"""Projects, saved versions and settings, all kept as plain files in the user's data folder."""
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile

TEXT_EXTENSIONS = {"tex", "bib", "sty", "cls", "bst", "txt", "md", "cfg", "def", "ltx"}
LAST_PDF = ".last.pdf"


def data_dir():
    d = os.environ.get("TEXORA_DATA")
    if not d:
        base = os.environ.get("APPDATA") if sys.platform == "win32" else None
        if not base:
            base = os.path.join(os.path.expanduser("~"), ".local", "share")
        d = os.path.join(base, "TeXora")
    os.makedirs(d, exist_ok=True)
    return d


def is_text_file(name):
    return name.rsplit(".", 1)[-1].lower() in TEXT_EXTENSIONS if "." in name else False


def _clean(name):
    n = re.sub(r'[\\/:*?"<>|]', " ", name).strip()
    return n or "Untitled"


class Project(object):
    def __init__(self, name, path, external=False):
        self.name = name
        self.path = path
        self.external = external      # a folder somewhere else on the disk, opened in place

    def modified(self):
        t = os.path.getmtime(self.path)
        for root, _, files in os.walk(self.path):
            for f in files:
                try:
                    t = max(t, os.path.getmtime(os.path.join(root, f)))
                except OSError:
                    pass
        return t

    def file_count(self):
        n = 0
        for _, _, files in os.walk(self.path):
            n += sum(1 for f in files if not f.startswith("."))
        return n


class Meta(object):
    def __init__(self, main="main.tex", engine="xetex"):
        self.main = main
        self.engine = engine


class ProjectStore(object):
    def __init__(self, root=None):
        self.root = root or os.path.join(data_dir(), "projects")
        os.makedirs(self.root, exist_ok=True)

    def list(self):
        out = [Project(n, os.path.join(self.root, n)) for n in os.listdir(self.root)
               if os.path.isdir(os.path.join(self.root, n))]
        return sorted(out, key=lambda p: p.modified(), reverse=True)

    def unique_name(self, base):
        b = _clean(base)
        n, i = b, 2
        while os.path.exists(os.path.join(self.root, n)):
            n = "%s %d" % (b, i)
            i += 1
        return n

    def create(self, name, template):
        n = self.unique_name(name)
        d = os.path.join(self.root, n)
        os.makedirs(d)
        for f, c in template["files"].items():
            p = os.path.join(d, f)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(c)
        p = Project(n, d)
        self.save_meta(p, Meta(template.get("main", "main.tex"), template.get("engine", "xetex")))
        return p

    def rename(self, p, new_name):
        n = p.name if _clean(new_name) == p.name else self.unique_name(new_name)
        if n != p.name:
            os.rename(p.path, os.path.join(self.root, n))
        return Project(n, os.path.join(self.root, n))

    def duplicate(self, p):
        n = self.unique_name(p.name + " copy")
        shutil.copytree(p.path, os.path.join(self.root, n))
        return Project(n, os.path.join(self.root, n))

    def delete(self, p):
        shutil.rmtree(p.path, ignore_errors=True)

    def meta(self, p):
        try:
            with io.open(os.path.join(p.path, ".texora.json"), encoding="utf-8") as f:
                o = json.load(f)
            return Meta(o.get("main", "main.tex"), o.get("engine", "xetex"))
        except Exception:
            return Meta()

    def save_meta(self, p, m):
        with io.open(os.path.join(p.path, ".texora.json"), "w", encoding="utf-8") as f:
            json.dump({"main": m.main, "engine": m.engine}, f)

    def files(self, p, main):
        out = []
        for root, _, files in os.walk(p.path):
            for f in files:
                if f.startswith("."):
                    continue
                out.append(os.path.relpath(os.path.join(root, f), p.path).replace("\\", "/"))
        return sorted(out, key=lambda n: (n != main, not is_text_file(n), n.lower()))

    def export_zip(self, p, target):
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(p.path):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, p.path).replace("\\", "/"))

    def import_zip(self, name, source):
        n = self.unique_name(re.sub(r"\.zip$", "", name))
        d = os.path.join(self.root, n)
        os.makedirs(d)
        with zipfile.ZipFile(source) as z:
            for info in z.infolist():
                target = os.path.realpath(os.path.join(d, info.filename))
                if info.is_dir() or not target.startswith(os.path.realpath(d) + os.sep):   # no "../" tricks
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        main = "main.tex"
        tex = []
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".tex"):
                    tex.append(os.path.relpath(os.path.join(root, f), d).replace("\\", "/"))
        for t in sorted(tex):
            with io.open(os.path.join(d, t), encoding="utf-8", errors="replace") as fh:
                if "\\documentclass" in fh.read():
                    main = t
                    break
        else:
            if tex:
                main = sorted(tex)[0]
        p = Project(n, d)
        self.save_meta(p, Meta(main))
        return p

    def import_file(self, p, name, data):
        n = re.sub(r'[\\:*?"<>|]', "_", name).replace("\\", "_")
        i = 2
        while os.path.exists(os.path.join(p.path, n)):
            base, dot, ext = name.rpartition(".")
            n = "%s_%d.%s" % (base, i, ext) if dot else "%s_%d" % (name, i)
            i += 1
        full = os.path.join(p.path, n)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        return n


class HistoryStore(object):
    """Earlier versions of every text file, kept outside the project so they are never compiled or exported."""

    def __init__(self, root=None):
        self.root = root or os.path.join(data_dir(), "history")
        os.makedirs(self.root, exist_ok=True)

    def _dir(self, project, file):
        return os.path.join(self.root, project, file.replace("/", "%"))

    def list(self, project, file):
        d = self._dir(project, file)
        out = []
        if os.path.isdir(d):
            for f in os.listdir(d):
                stem = f.rsplit(".", 1)[0]
                if stem.isdigit():
                    out.append((int(stem), os.path.join(d, f)))
        return sorted(out, reverse=True)

    def snapshot(self, project, file, text):
        d = self._dir(project, file)
        os.makedirs(d, exist_ok=True)
        versions = self.list(project, file)
        if versions and self.read(versions[0]) == text:
            return
        t = int(time.time() * 1000)
        if versions and versions[0][0] >= t:
            t = versions[0][0] + 1
        with io.open(os.path.join(d, "%d.txt" % t), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        for _, path in self.list(project, file)[15:]:
            try:
                os.remove(path)
            except OSError:
                pass

    def read(self, version):
        try:
            with io.open(version[1], encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def delete_project(self, project):
        shutil.rmtree(os.path.join(self.root, project), ignore_errors=True)

    def rename_project(self, old, new):
        if old != new and os.path.isdir(os.path.join(self.root, old)):
            os.rename(os.path.join(self.root, old), os.path.join(self.root, new))


class Prefs(object):
    DEFAULTS = {"theme": "qp_light", "accent": "", "lang": "en", "editor_size": 12, "line_numbers": True,
                "wrap": False, "auto_pairs": True, "symbol_bar": True, "snippets": [], "compile_ms": {},
                "recent": [], "external": [], "autosave_compile": True, "autotype_compile": False, "two_pages": False,
                "night_pdf": False, "preview_below": False, "layout_v2": "", "geometry": ""}

    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "settings.json")
        self.d = dict(self.DEFAULTS)
        try:
            with io.open(self.path, encoding="utf-8") as f:
                self.d.update(json.load(f))
        except Exception:
            pass

    def get(self, k):
        return self.d.get(k, self.DEFAULTS.get(k))

    def set(self, k, v):
        self.d[k] = v
        self.save()

    def save(self):
        try:
            with io.open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except OSError:
            pass
