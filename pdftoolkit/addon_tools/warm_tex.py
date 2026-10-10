"""Fills a Tectonic package cache by compiling small documents that load many packages (used by the add-on build).

usage: python warm_tex.py <cache_dir> base|full [report.json]
`full` assumes the cache already holds the `base` set and adds many more packages, classes, fonts and styles.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

cache, which = sys.argv[1], sys.argv[2]
report = sys.argv[3] if len(sys.argv) > 3 else "warm-report.json"
os.environ["PDFTK_TEX_CACHE"] = cache
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import texengine  # noqa: E402

BASE = ["amsmath", "amssymb", "amsthm", "mathtools", "bm", "physics", "siunitx", "mhchem", "chemfig", "tikz", "pgfplots",
        "xcolor", "graphicx", "hyperref", "booktabs", "enumitem", "cleveref", "cancel", "mathrsfs", "stmaryrd", "tcolorbox",
        "subcaption", "float", "multirow", "longtable", "geometry", "fancyhdr", "titlesec", "microtype", "setspace",
        "listings", "natbib", "algorithm2e", "tikz-cd", "braket", "esdiff", "chemmacros", "units", "fontspec"]

FULL = """
amsfonts amscd amsopn amsbsy amstext amsxtra thmtools ntheorem mdframed framed todonotes csquotes babel polyglossia bidi
xepersian unicode-math lmodern newtxtext newtxmath mathpazo palatino times tgpagella tgtermes tgheros tgcursor stix2 libertine
fouriernc kpfonts ccfonts eulervm euler bbm dsfont mathabx yhmath extarrows nicefrac xfrac esint bigints tensor empheq nccmath
breqn upgreek wasysym marvosym pifont bbding fontawesome5 tipa textcomp fontenc inputenc eurosym gensymb mathdesign
caption subfig wrapfig epsfig url xspace etoolbox xparse xpatch array tabularx makecell diagbox colortbl hhline ulem soul
tabu threeparttable threeparttablex rotating sidecap afterpage placeins textpos eso-pic background xifthen ifthen calc
ifpdf iftex kvoptions pdftexcmds bookmark pdfpages pdflscape lscape rotating fancyvrb verbatim comment listings lstautogobble
algpseudocode algorithmicx algorithmic algorithm authblk abstract appendix titling tocloft tocbibind multicol paracol
balance changepage chngcntr cite biblatex natbib apalike harvard cleveref varioref hyperxmp xurl nameref
pgf pgfmath circuitikz tikz-3dplot pgfplotstable tikz-qtree forest qtree bussproofs prooftrees proof ebproof
mathrsfs calligra ccicons wasysym stackrel stackengine relsize scalerel mleftright mathtools cases nicematrix
blkarray arydshln hvfloat adjustbox trimclip tcolorbox tasks exsheets exercise answers multienum paralist enumerate
fullpage a4wide anysize vmargin lipsum blindtext kantlipsum zref zref-user refcount lastpage totcount tabularray
siunitx chemformula chemgreek chemnum modiagram bohr rsphrase chemscheme xymtex tikzorbital
physics2 diffcoeff derivative commath cool coolstr xfp pgfmath siunitx numprint
xcolor colortbl tcolorbox tikzfill pgfopts
glossaries acro nomencl makeidx imakeidx index
algorithm2e algpseudocodex
epigraph quotchap fncychap titlesec titletoc sectsty
datetime2 datetime
cmap microtype letterspace
""".split()
CLASSES = ["amsart", "amsbook", "amsproc", "report", "book", "memoir", "scrartcl", "scrreprt", "scrbook", "beamer", "standalone",
           "IEEEtran", "elsarticle", "revtex4-2", "llncs", "svjour3", "article", "letter", "minimal", "extarticle", "extreport"]
BEAMER = ["Madrid", "Warsaw", "CambridgeUS", "Berlin", "Boadilla", "Frankfurt", "Singapore", "metropolis", "Copenhagen"]
FONTS = ["Latin Modern Roman", "Latin Modern Sans", "Latin Modern Mono", "TeX Gyre Termes", "TeX Gyre Pagella",
         "TeX Gyre Heros", "TeX Gyre Bonum", "TeX Gyre Schola", "TeX Gyre Cursor", "XITS", "Libertinus Serif"]
BIB = ["plain", "alpha", "abbrv", "unsrt", "amsplain", "amsalpha", "ieeetr", "siam", "acm", "apalike", "plainnat", "abbrvnat", "unsrtnat"]
TIKZLIBS = "arrows.meta calc positioning shapes.geometric decorations.pathmorphing patterns fit backgrounds intersections matrix mindmap trees through quotes angles babel graphs automata shadows".split()
PGFPLOTSLIBS = "fillbetween statistics groupplots colormaps polar dateplot".split()


def doc(pre: str, body: str = "x") -> str:
    return pre + "\n\\begin{document}\n" + body + "\n\\end{document}\n"


jobs: list[tuple[str, str]] = []      # (label, tex source)
if which == "base":
    for p in BASE:
        jobs.append((p, doc("\\documentclass{article}\\usepackage{%s}" % p)))
else:
    for p in dict.fromkeys(FULL):
        jobs.append((p, doc("\\documentclass{article}\\usepackage{%s}" % p)))
    for c in CLASSES:
        jobs.append(("class " + c, doc("\\documentclass{%s}" % c)))
    for t in BEAMER:
        jobs.append(("beamer " + t, doc("\\documentclass{beamer}\\usetheme{%s}" % t, "\\begin{frame}x\\end{frame}")))
    for f in FONTS:
        jobs.append(("font " + f, doc("\\documentclass{article}\\usepackage{fontspec}\\setmainfont{%s}" % f, "Hello $x$")))
    for b in BIB:
        jobs.append(("bibtex " + b, doc("\\documentclass{article}\\bibliographystyle{%s}" % b,
                                       "\\nocite{*}\\bibliography{refs}")))
    jobs.append(("tikz libraries", doc("\\documentclass{article}\\usepackage{tikz}" + "".join("\\usetikzlibrary{%s}" % l for l in TIKZLIBS))))
    jobs.append(("pgfplots libraries", doc("\\documentclass{article}\\usepackage{pgfplots}" + "".join("\\usepgfplotslibrary{%s}" % l for l in PGFPLOTSLIBS))))
    jobs.append(("amsthm + thmtools", doc("\\documentclass{article}\\usepackage{amsthm,thmtools}\\newtheorem{thm}{Theorem}", "\\begin{thm}x\\end{thm}")))
    jobs.append(("orlicz-style article", doc("\\documentclass[11pt]{amsart}\\usepackage{amsmath,amssymb,mathtools,bm,mathrsfs,enumitem,hyperref,cleveref}",
                                           "$\\|f\\|_{\\Phi}=\\inf\\{k>0:\\int\\Phi(|f|/k)\\le1\\}$")))

eng = texengine.find_engine("tectonic")
print("engine:", eng.label if eng else None, "cache:", texengine.cache_dir())
ok, bad = [], []
td = Path(tempfile.mkdtemp(prefix="warm_"))
(td / "refs.bib").write_text("@book{k,author={A. Author},title={T},publisher={P},year={2000}}\n")
for label, src in jobs:
    f = td / "w.tex"
    f.write_text(src, encoding="utf-8")
    r = texengine.compile_tex(str(f), str(td / "out"), engine=eng, timeout=300)
    (ok if r.ok else bad).append(label)
    print(("PASS " if r.ok else "FAIL ") + label + ("" if r.ok else "  " + (r.errors[0].message if r.errors else "")[:100]), flush=True)
json.dump({"ok": ok, "failed": bad}, open(report, "w"), indent=1)
print(f"{len(ok)} compiled, {len(bad)} failed (failures are packages Tectonic's bundle does not have)")
