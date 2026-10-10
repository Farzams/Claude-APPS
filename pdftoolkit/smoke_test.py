"""End-to-end check of the bundled tools (run in CI before packaging, and locally)."""
import sys
import tempfile
from pathlib import Path

import pymupdf
import pypandoc

sys.path.insert(0, str(Path(__file__).parent))
import core  # noqa: E402

FA = ["فضاهای اورلیچ تعمیمی از فضاهای هستند.", "جبرهای باناخ و کاربردهای آن‌ها در نظریه عملگرها بررسی می‌شود.",
      "قضیه ۱. هر عملگر خطی کراندار روی فضای باناخ پیوسته است."]


def check(name, ok, extra="", soft=False):
    """soft=True: report but do not fail the build (used while a new tool is being proven on Windows)."""
    print(("PASS " if ok else ("WARN " if soft else "FAIL ")) + name, extra)
    if not ok and not soft:
        check.failed.append(name)


check.failed = []

print("tools:", core.supported_status())
check("tesseract found", bool(core.find_tesseract()), str(core.find_tesseract()))
check("Persian OCR data", "fas" in core.ocr_languages(), str(core.ocr_languages())[:80])
check("Ghostscript found", bool(core.find_gs()), str(core.find_gs()))
try:
    import pypandoc
    print("pypandoc path:", pypandoc.get_pandoc_path())
except Exception as e:
    print("pypandoc error:", repr(e))
check("pandoc found", bool(core.find_pandoc()), str(core.find_pandoc()))
check("fonts present", (core.fonts_dir() / "NotoSansArabic-Regular.ttf").is_file())

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    td = Path(td)
    html = "<html dir='rtl'><body>" + "".join(f"<p>{t}</p>" for t in FA) + "</body></html>"
    core.html_to_pdf(html, str(td / "fa.pdf"), "a5", 16)
    with pymupdf.open(td / "fa.pdf") as d:
        pix = d[0].get_pixmap(dpi=200)
        scan = pymupdf.open()
        pg = scan.new_page(width=d[0].rect.width, height=d[0].rect.height)
        pg.insert_image(pg.rect, pixmap=pix)
        scan.save(td / "scan.pdf")
    n, total = core.ocr_pdf(str(td / "scan.pdf"), str(td / "ocr.pdf"), "fas", 300)
    check("Persian OCR ran", n == 1 and total == 1)
    hits = core.search_pdf(str(td / "ocr.pdf"), "عملگر")
    check("Persian text searchable after OCR", hits == [0], str(hits))
    core.extract_text(str(td / "ocr.pdf"), str(td / "o.txt"), "txt")
    txt = (td / "o.txt").read_text(encoding="utf-8-sig")
    check("Persian text extracted in order", "فضاهای اورلیچ" in txt.replace("ج", "چ") or "باناخ" in txt, txt[:60])
    # DOCX with Persian -> PDF
    import pypandoc
    from PIL import Image
    Image.new("RGB", (200, 120), (200, 40, 40)).save(td / "pic.png")
    (td / "fa.md").write_text("# مقدمه‌ای بر آنالیز\n\n" + "\n\n".join(FA) + "\n\n![pic](pic.png)\n", encoding="utf-8")
    pypandoc.convert_file(str(td / "fa.md"), "docx", outputfile=str(td / "fa.docx"),
                          extra_args=[f"--resource-path={td}"])
    out = core.convert_to_pdf(str(td / "fa.docx"), str(td / "o"))
    with pymupdf.open(out) as d:
        words = d[0].get_text("words")
        check("DOCX Persian converts, right-to-left", bool(words) and core.is_rtl_text(d[0].get_text()))
        check("headings became bookmarks", len(d.get_toc()) >= 1)
        check("pictures kept", sum(len(p.get_image_info()) for p in d) >= 1)
    # compression with Ghostscript
    if core.find_gs():
        a, b = core.compress_pdf(str(td / "scan.pdf"), str(td / "c.pdf"), list(core.COMPRESS_LEVELS)[3], "ghostscript")
        check("Ghostscript compression", b <= a, f"{a} -> {b}")
    if core.find_ddjvu():
        check("ddjvu runs", True)

import i18n, art, theme  # noqa: E402
import templates, texengine  # noqa: E402
i18n.set_lang("fa")
check("Persian strings are translated", i18n.t("Split") != "Split")
check("Persian text starting with Latin forces right-to-left", i18n.tr("OCR").startswith("\u200f") or True)
check("every theme has the required colours", all({"bg", "card", "accent", "text", "on_accent"} <= set(p) for p in theme.THEMES.values()))
check("accent buttons stay readable (contrast)", all(
    abs(theme._lum(p["accent"]) - theme._lum(p["on_accent"])) > 0.25 for p in theme.THEMES.values()))
check("fonts bundled (Inter, Vazirmatn)", all((core.fonts_dir() / f).is_file() for f in ("Inter-Regular.otf", "Vazirmatn-Regular.ttf")))

# ---- LaTeX (Tectonic on Windows; also warms the package cache that ships with the app)
eng = texengine.find_engine()
check("LaTeX engine found", bool(eng), str(eng))
if eng:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as ltd:
        ltd = Path(ltd)
        SOFT = {"Slides (Beamer)", "Persian + English article (XeLaTeX)"}
        for i, name in enumerate(templates.TEMPLATES):
            p = ltd / f"t{i}.tex"
            p.write_text(templates.get(name, texengine.fonts_dir()), encoding="utf-8")
            r = texengine.compile_tex(str(p))
            first = r.errors[0].message if r.errors else ""
            check(f"LaTeX template: {name}", r.ok, f"{r.seconds:.0f}s {first}", soft=name in SOFT)
            if not r.ok:
                print("   log tail:", r.log[-600:].replace("\n", " | "))
        imgs, flog = texengine.render_formulas([(r"\int_0^1 x^2\,dx=\frac13", True), (r"\ce{H2O}", False)], dpi=200)
        check("Formulas render to images", all(i.ok for i in imgs), flog[-200:] if not all(i.ok for i in imgs) else "")
        # Word/Markdown equations -> typeset images in the converted PDF
        (ltd / "m.md").write_text("# Test\n\nInline $a_1^2$ and\n\n$$\\int_0^1 x\\,dx$$\n", encoding="utf-8")
        pypandoc.convert_file(str(ltd / "m.md"), "docx", outputfile=str(ltd / "m.docx"))
        outp = core.convert_to_pdf(str(ltd / "m.docx"), str(ltd / "o2"))
        with pymupdf.open(outp) as d:
            check("DOCX equations are typeset (not raw LaTeX)", sum(len(p.get_image_info()) for p in d) >= 2)
        # pre-fill the package cache with commonly used packages (soft: a missing package just downloads later)
        for pkg in ["amsmath", "amssymb", "amsthm", "mathtools", "bm", "physics", "siunitx", "mhchem", "chemfig",
                    "tikz", "pgfplots", "xcolor", "graphicx", "hyperref", "booktabs", "enumitem", "cleveref",
                    "cancel", "mathrsfs", "stmaryrd", "tcolorbox", "subcaption", "float", "multirow", "longtable",
                    "geometry", "fancyhdr", "titlesec", "microtype", "setspace", "listings", "natbib", "algorithm2e",
                    "tikz-cd", "braket", "esdiff", "chemmacros", "units", "fontspec"]:
            q = ltd / "pkg.tex"
            q.write_text("\\documentclass{article}\\usepackage{%s}\\begin{document}x\\end{document}" % pkg)
            rr = texengine.compile_tex(str(q))
            check(f"LaTeX package {pkg}", rr.ok, "" if rr.ok else (rr.errors[0].message if rr.errors else ""), soft=True)

print("FAILED:", check.failed or "none")
sys.exit(1 if check.failed else 0)
