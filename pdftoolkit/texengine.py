"""LaTeX support: compile .tex to PDF (Tectonic or an installed XeLaTeX), explain errors,
render formulas to images, import Word/Markdown as LaTeX."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _app_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def fonts_dir() -> Path:
    return _app_dir() / "fonts"


# ---------------------------------------------------------------- engines
@dataclass
class Engine:
    kind: str   # "tectonic" | "xelatex" | "pdflatex"
    path: str

    @property
    def label(self) -> str:
        return {"tectonic": "Tectonic", "xelatex": "XeLaTeX", "pdflatex": "pdfLaTeX"}[self.kind]


def _candidates(name: str) -> list[str]:
    here = _app_dir()
    dirs = [here / "tectonic", here / "tex", here]
    out = []
    for d in dirs:
        for ext in ("", ".exe"):
            p = d / (name + ext)
            if p.is_file():
                out.append(str(p))
    w = shutil.which(name)
    if w:
        out.append(w)
    return out


def find_engine(prefer: str | None = None) -> Engine | None:
    """Bundled Tectonic first, then an installed XeLaTeX (MiKTeX / TeX Live), then pdfLaTeX."""
    order = ["tectonic", "xelatex", "pdflatex"]
    if prefer in order:
        order.remove(prefer)
        order.insert(0, prefer)
    for kind in order:
        c = _candidates(kind)
        if c:
            return Engine(kind, c[0])
    return None


def cache_dir() -> Path:
    """Writable Tectonic package cache. A pre-filled copy shipped with the app is copied here once."""
    override = os.environ.get("PDFTK_TEX_CACHE")  # used by the build to pre-fill the cache that ships with the app
    if override:
        p = Path(override).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    user = Path(base) / "PDFToolkit" / "tectonic-cache"
    bundled = _app_dir() / "tex-cache"
    if bundled.is_dir() and not (user / ".seeded").exists():
        try:
            user.mkdir(parents=True, exist_ok=True)
            shutil.copytree(bundled, user, dirs_exist_ok=True)
            (user / ".seeded").write_text("1")
        except Exception:
            pass
    user.mkdir(parents=True, exist_ok=True)
    return user


def _env() -> dict:
    env = dict(os.environ)
    env["TECTONIC_CACHE_DIR"] = str(cache_dir())
    return env


# ---------------------------------------------------------------- errors
@dataclass
class TexError:
    file: str
    line: int
    message: str
    hint: str = ""


HINTS = [
    (r"Undefined control sequence", "Unknown command. Check the spelling, or load the package that defines it."),
    (r"Missing \$ inserted", "A math symbol or ^ _ was used outside math mode. Wrap it in $ … $."),
    (r"File `([^']+)' not found", "A file or package is missing. Check its name; the first compile may need internet."),
    (r"Missing \\begin\{document\}", "Text appeared before \\begin{document}. Check the preamble."),
    (r"Extra \}|Too many \}'s", "There is an extra closing brace }."),
    (r"Missing \} inserted|Runaway argument|Paragraph ended before", "A brace { is not closed."),
    (r"Environment (.+) undefined", "That environment is not defined. Load the package or fix the name."),
    (r"\\begin\{(.+?)\} on input line \d+ ended by", "A \\begin{…} and \\end{…} do not match."),
    (r"Illegal parameter number|Argument of .* has an extra", "Check the arguments of the command (#1, #2…)."),
    (r"Unicode character|Invalid UTF-8|not set up for use with LaTeX", "A special character is not supported by the font."),
    (r"Font .* not found|cannot find font|Cannot load|font .* not loadable", "The font could not be found."),
]


def explain(message: str) -> str:
    for pat, hint in HINTS:
        if re.search(pat, message):
            return hint
    return ""


_ERR_LINE = re.compile(r"^(?:error: )?(?:\./)?([^\s:][^:\n]*\.(?:tex|sty|cls|bib|ltx)):(\d+):\s*(.*)$")
_BANG = re.compile(r"^! (.*)$")
_LREF = re.compile(r"^l\.(\d+)\s")


def parse_errors(log: str) -> list[TexError]:
    """Pick file/line/message triples out of a TeX or Tectonic log."""
    errs: list[TexError] = []
    seen = set()
    lines = log.splitlines()
    for i, ln in enumerate(lines):
        m = _ERR_LINE.match(ln.strip())
        if m:
            f, n, msg = m.group(1), int(m.group(2)), m.group(3).strip()
            key = (f, n, msg)
            if key not in seen and not msg.lower().startswith(("warning", "overfull", "underfull")):
                seen.add(key)
                errs.append(TexError(f, n, msg, explain(msg)))
            continue
        b = _BANG.match(ln)
        if b:
            msg = b.group(1).strip()
            line_no = 0
            for nxt in lines[i + 1:i + 8]:
                lr = _LREF.match(nxt)
                if lr:
                    line_no = int(lr.group(1))
                    break
            key = ("", line_no, msg)
            if key not in seen and not any(e.message == msg and e.line == line_no for e in errs):
                seen.add(key)
                errs.append(TexError("", line_no, msg, explain(msg)))
    return errs


@dataclass
class CompileResult:
    ok: bool
    pdf: str | None = None
    log: str = ""
    errors: list[TexError] = field(default_factory=list)
    seconds: float = 0.0
    engine: str = ""


# ---------------------------------------------------------------- compile
def _run(cmd, cwd, timeout, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=NO_WINDOW, env=env or _env())


def ensure_bundled_fonts(src: Path) -> None:
    """Documents that load the bundled Persian fonts via Path=fonts/ get a fonts/ folder next to them.

    (Absolute Windows paths such as D:/... break XeTeX's font loader, a relative path does not.)
    """
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if not re.search(r"Path=\.?/?fonts/", text):
        return
    dest = src.parent / "fonts"
    for f in fonts_dir().glob("*.[to]tf"):
        if f.stem.split("-")[0] in text and not (dest / f.name).exists():
            dest.mkdir(exist_ok=True)
            try:
                shutil.copyfile(f, dest / f.name)
            except OSError:
                pass


def compile_tex(tex: str, out_dir: str | None = None, engine: Engine | None = None,
                timeout: int = 600) -> CompileResult:
    """Compile a .tex file. The PDF is written to out_dir (default: next to the source)."""
    t0 = time.time()
    eng = engine or find_engine()
    src = Path(tex).resolve()
    if not eng:
        return CompileResult(False, log="No LaTeX engine found.", seconds=0,
                             errors=[TexError("", 0, "No LaTeX engine (Tectonic, XeLaTeX) was found.")])
    out = Path(out_dir) if out_dir else src.parent
    out.mkdir(parents=True, exist_ok=True)
    ensure_bundled_fonts(src)
    build = Path(tempfile.mkdtemp(prefix="pdftk_tex_"))
    log = ""
    try:
        if eng.kind == "tectonic":
            r = _run([eng.path, "-X", "compile", src.name, "--outdir", str(build), "--keep-logs"],
                     str(src.parent), timeout)
            log = (r.stdout or "") + "\n" + (r.stderr or "")
            lf = build / (src.stem + ".log")
            if lf.exists():
                log += "\n" + lf.read_text(encoding="utf-8", errors="replace")
        else:
            args = [eng.path, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
                    "-output-directory", str(build)]
            args = args + [src.name]
            env = _env()
            env["BIBINPUTS"] = str(src.parent) + os.pathsep + env.get("BIBINPUTS", "")
            env["TEXINPUTS"] = str(src.parent) + os.pathsep + env.get("TEXINPUTS", "")
            r = _run(args, str(src.parent), timeout, env)
            log = (r.stdout or "") + (r.stderr or "")
            aux = build / (src.stem + ".aux")
            if r.returncode == 0 and aux.exists() and "\\bibdata" in aux.read_text(errors="replace"):
                bib = shutil.which("bibtex")
                if bib:
                    b = _run([bib, src.stem], str(build), 120, env)
                    log += "\n" + (b.stdout or "")
            for _ in range(2):  # references / table of contents settle after two more passes
                if r.returncode != 0:
                    break
                r = _run(args, str(src.parent), timeout, env)
                log += "\n" + (r.stdout or "")
                if "Rerun to get" not in (r.stdout or "") and "Rerun" not in (r.stdout or ""):
                    break
        pdf_built = build / (src.stem + ".pdf")
        ok = pdf_built.exists()
        errs = parse_errors(log)
        if not ok and not errs:
            errs = [TexError("", 0, "The compile failed. See the log for details.")]
        dest = None
        if ok:
            dest = out / (src.stem + ".pdf")
            try:
                shutil.copyfile(pdf_built, dest)
            except PermissionError:  # PDF is open in a viewer
                dest = out / (src.stem + "_new.pdf")
                shutil.copyfile(pdf_built, dest)
        return CompileResult(ok, str(dest) if dest else None, log, errs, time.time() - t0, eng.label)
    except subprocess.TimeoutExpired:
        return CompileResult(False, log=log, seconds=time.time() - t0, engine=eng.label,
                             errors=[TexError("", 0, "The compile took too long and was stopped.")])
    finally:
        shutil.rmtree(build, ignore_errors=True)


# ---------------------------------------------------------------- formulas
PREAMBLE = r"""\documentclass[multi=mathpage,border=1.5pt]{standalone}
\usepackage{amsmath,amssymb,amsfonts,mathtools,bm,cancel,xcolor}
\usepackage[version=4]{mhchem}
\usepackage{siunitx}
\providecommand{\R}{\mathbb{R}}\providecommand{\C}{\mathbb{C}}\providecommand{\N}{\mathbb{N}}
\providecommand{\Z}{\mathbb{Z}}\providecommand{\Q}{\mathbb{Q}}
\newsavebox{\pdftkbox}
"""


_AUTO_PACKAGES = [
    (r"\\(ket|bra|braket|expval|pdv|dv|vb|va|vu|grad|curl|div|laplacian|ev|mel)\b", "\\usepackage{physics}"),
    (r"\\mathscr\b", "\\usepackage{mathrsfs}"),
    (r"\\chemfig\b", "\\usepackage{chemfig}"),
    (r"\\(tikz|draw)\b|\\begin\{tikzpicture", "\\usepackage{tikz}"),
]


def extra_packages(snippets) -> str:
    """\\usepackage lines for rarely needed packages, added only when a formula uses them."""
    text = "\n".join(snippets)
    return "\n".join(pkg for pat, pkg in _AUTO_PACKAGES if re.search(pat, text))


@dataclass
class FormulaImage:
    png: bytes | None
    width_px: int = 0
    height_px: int = 0
    depth_pt: float = 0.0     # how far the baseline sits above the bottom edge
    pdf_page: int = 0
    tex: str = ""
    ok: bool = False


def _color_cmd(color: str | None) -> str:
    if not color:
        return ""
    c = color.lstrip("#")
    if len(c) == 6:
        return "\\color[HTML]{%s}" % c.upper()
    return ""


def render_formulas(items: list[tuple[str, bool]], dpi: int = 300, color: str | None = None,
                    engine: Engine | None = None, transparent: bool = True
                    ) -> tuple[list[FormulaImage], str]:
    """Render [(latex, is_display)] to images. Returns (images, log). Bad formulas get ok=False."""
    eng = engine or find_engine()
    if not eng:
        return [FormulaImage(None, tex=t) for t, _ in items], "No LaTeX engine"
    bad: set[int] = set()
    log_all = ""
    td = Path(tempfile.mkdtemp(prefix="pdftk_math_"))
    try:
        for attempt in range(4):
            lines = [PREAMBLE + extra_packages(t for t, _ in items), "\\begin{document}"]
            line_of: dict[int, int] = {}
            for i, (tex, disp) in enumerate(items):
                body = r"\textbf{?}" if i in bad else tex
                style = r"\displaystyle " if disp else ""
                lines.append("\\begin{mathpage}\\sbox{\\pdftkbox}{%s\\strut$%s%s$}\\typeout{PDFTKDP:%d:\\the\\dp\\pdftkbox}"
                             "\\usebox{\\pdftkbox}\\end{mathpage}" % (_color_cmd(color), style, body, i))
                line_of[len(lines)] = i
            lines.append("\\end{document}")
            src = td / "f.tex"
            src.write_text("\n".join(lines), encoding="utf-8")
            res = compile_tex(str(src), str(td), eng, timeout=300)
            log_all += res.log
            if res.ok:
                break
            # remove the formulas named in the errors and try again
            new_bad = {line_of[e.line] for e in res.errors if e.line in line_of}
            if not new_bad or new_bad <= bad:
                break
            bad |= new_bad
        pdf = td / "f.pdf"
        out: list[FormulaImage] = []
        if not pdf.exists():
            return [FormulaImage(None, tex=t) for t, _ in items], log_all
        depths = {int(m.group(1)): m.group(2) for m in re.finditer(r"PDFTKDP:(\d+):\s*([0-9.\-]+)pt", log_all)}
        doc = pymupdf.open(str(pdf))
        zoom = dpi / 72
        for i, (tex, _d) in enumerate(items):
            if i in bad or i >= doc.page_count:
                out.append(FormulaImage(None, tex=tex))
                continue
            pix = doc[i].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=transparent)
            try:
                dp = float(depths.get(i, "3.5"))
            except ValueError:
                dp = 3.5
            out.append(FormulaImage(pix.tobytes("png"), pix.width, pix.height, dp + 1.5, i, tex, True))
        doc.close()
        return out, log_all
    finally:
        shutil.rmtree(td, ignore_errors=True)


def formula_files(tex: str, display: bool, base: str, formats=("png", "svg", "pdf"), dpi: int = 400,
                  color: str | None = None, transparent: bool = True) -> list[str]:
    """Render one formula and write base.png / base.svg / base.pdf. Returns the written paths."""
    eng = find_engine()
    if not eng:
        raise RuntimeError("No LaTeX engine found.")
    td = Path(tempfile.mkdtemp(prefix="pdftk_one_"))
    try:
        body = (r"\displaystyle " if display else "") + tex
        src = td / "one.tex"
        src.write_text(PREAMBLE.replace("multi=mathpage,", "") + extra_packages([tex]) + "\n\\begin{document}\n"
                       + "{%s$%s$}\n\\end{document}\n" % (_color_cmd(color), body), encoding="utf-8")
        res = compile_tex(str(src), str(td), eng, timeout=300)
        if not res.ok:
            msg = res.errors[0].message if res.errors else "compile failed"
            raise RuntimeError(msg)
        written = []
        doc = pymupdf.open(str(td / "one.pdf"))
        page = doc[0]
        if "png" in formats:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), alpha=transparent)
            pix.save(base + ".png")
            written.append(base + ".png")
        if "svg" in formats:
            Path(base + ".svg").write_text(page.get_svg_image(text_as_path=True), encoding="utf-8")
            written.append(base + ".svg")
        if "pdf" in formats:
            shutil.copyfile(td / "one.pdf", base + ".pdf")
            written.append(base + ".pdf")
        doc.close()
        return written
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---------------------------------------------------------------- import
def import_to_latex(src: str, dest_dir: str) -> str:
    """Word / ODT / Markdown / EPUB / HTML -> standalone .tex (equations stay as LaTeX)."""
    import core
    pandoc = core.find_pandoc()
    if not pandoc:
        raise RuntimeError("Pandoc is missing from this build.")
    s = Path(src)
    fmt = core.PANDOC_FORMATS.get(s.suffix.lower()) or {".html": "html", ".htm": "html"}.get(s.suffix.lower())
    if not fmt or fmt == "latex":
        raise ValueError("Choose a Word, ODT, RTF, Markdown, EPUB or HTML file.")
    d = Path(dest_dir)
    d.mkdir(parents=True, exist_ok=True)
    out = core.unique_path(d / (s.stem + ".tex"))
    r = subprocess.run([pandoc, "-f", fmt, "-t", "latex", "--standalone", "--extract-media=media",
                        "-o", str(out), str(s)], cwd=str(d), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=NO_WINDOW)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"Pandoc failed: {r.stderr.strip()[-300:]}")
    return str(out)
