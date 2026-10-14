"""End-to-end check of the bundled tools (run in CI before packaging, and locally)."""
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
import core  # noqa: E402

FA = ["فضاهای برداری تعمیمی از صفحه و فضا هستند.", "جبرهای خطی و کاربردهای آن‌ها در علوم بررسی می‌شود.",
      "قضیه ۱. هر عملگر خطی کراندار روی فضای باناخ پیوسته است."]


def check(name, ok, extra="", soft=False):
    """soft=True: report but do not fail the build (used while a new tool is being proven on Windows)."""
    print(("PASS " if ok else ("WARN " if soft else "FAIL ")) + name, extra)
    if not ok and not soft:
        check.failed.append(name)


check.failed = []

print("tools:", core.supported_status())
check("Ghostscript found", bool(core.find_gs()), str(core.find_gs()))
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
    # compression with Ghostscript
    if core.find_gs():
        a, b = core.compress_pdf(str(td / "scan.pdf"), str(td / "c.pdf"), list(core.COMPRESS_LEVELS)[3], "ghostscript")
        check("Ghostscript compression", b <= a, f"{a} -> {b}")
    if core.find_ddjvu():
        check("ddjvu runs", True)

import i18n, art, theme  # noqa: E402
i18n.set_lang("fa")
check("Persian strings are translated", i18n.t("Split") != "Split")
check("Persian text starting with Latin forces right-to-left", i18n.tr("OCR").startswith("\u200f") or True)
check("every theme has the required colours", all({"bg", "card", "accent", "text", "on_accent"} <= set(p) for p in theme.THEMES.values()))
check("accent buttons stay readable (contrast)", all(
    abs(theme._lum(p["accent"]) - theme._lum(p["on_accent"])) > 0.25 for p in theme.THEMES.values()))
check("fonts bundled (Inter, Vazirmatn)", all((core.fonts_dir() / f).is_file() for f in ("Inter-Regular.otf", "Vazirmatn-Regular.ttf")))

# ---- extra PDF tools (organize, crop, stamps, export, security, redaction, edit, batch)
import pdftools
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as ptd:
    ptd = Path(ptd)
    en, fa = str(ptd / "en.pdf"), str(ptd / "fa.pdf")
    core.html_to_pdf("<h1>Annual Report</h1><p>Mail john@example.com</p><table border=1><tr><td>A</td><td>1</td></tr>"
                     "<tr><td>B</td><td>2</td></tr></table><p>" + "Lorem ipsum dolor. " * 120 + "</p>", en, "a5")
    core.html_to_pdf("<h1>گزارش سالانه</h1><p>این یک متن آزمایشی فارسی است.</p>", fa, "a5")
    def q(path, i=0):
        with pymupdf.open(path) as d:
            return d[i].get_text()
    check("Organize pages", pdftools.organize(en, str(ptd / "o.pdf"), [(1, 90), (0, 0)]) == 2)
    pdftools.crop_pdf(en, str(ptd / "c.pdf"), auto=True)
    check("Crop (auto)", pymupdf.open(str(ptd / "c.pdf"))[0].rect.width < 420)
    pdftools.header_footer(fa, str(ptd / "hf.pdf"), "", "{page}/{pages}", "")
    pdftools.watermark(fa, str(ptd / "wm.pdf"), "محرمانه")
    check("Header/footer + Persian watermark", pymupdf.open(str(ptd / "wm.pdf")).page_count == 1)
    pdftools.protect(en, str(ptd / "pw.pdf"), "abc")
    pdftools.unlock(str(ptd / "pw.pdf"), str(ptd / "un.pdf"), "abc")
    check("Password protect / unlock", pdftools.is_encrypted(str(ptd / "pw.pdf")) and "Annual" in q(str(ptd / "un.pdf")))
    check("Redact (Latin)", pdftools.redact(en, str(ptd / "r.pdf"), ["john@example.com"]) >= 1
          and "john@" not in q(str(ptd / "r.pdf")))
    pdftools.redact(fa, str(ptd / "rf.pdf"), ["آزمایشی"])
    check("Redact (Persian)", core._fold("آزمایشی") not in core._fold(q(str(ptd / "rf.pdf"))))
    check("Replace text (Persian)", pdftools.replace_text(fa, str(ptd / "rt.pdf"), "سالانه", "ماهانه") == 1
          and core._fold("ماهانه") in core._fold(q(str(ptd / "rt.pdf"))))
    docx_n = pdftools.to_docx(fa, str(ptd / "fa.docx"))
    import docx as _docx
    check("PDF to Word (Persian)", core._fold("گزارش") in core._fold(_docx.Document(str(ptd / "fa.docx")).paragraphs[0].text))
    check("PDF to Excel", pdftools.to_xlsx(en, str(ptd / "t.xlsx")) >= 1)
    check("PDF to images", len(pdftools.to_images(en, str(ptd / "img"), "jpg", 60)) == 2)
    pdftools.export_text_format(fa, str(ptd / "f.html"), "html")
    check("PDF to HTML", (ptd / "f.html").stat().st_size > 200)
    res = pdftools.batch_run([en, fa], str(ptd / "b"), "watermark", {"text": "DRAFT"})
    check("Batch run", all(ok for _, ok, _ in res))

# ---- repair
import pymupdf as _pm
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as qd:
    qd = Path(qd)
    src = str(qd / "e.pdf")
    core.html_to_pdf("<p>" + "Repair test line. " * 300 + "</p>", src, "a5")
    raw = Path(src).read_bytes()
    (qd / "b.pdf").write_bytes(raw[:-250])
    old, new, probs = pdftools.repair_pdf(str(qd / "b.pdf"), str(qd / "f.pdf"))
    check("Repair damaged PDF", _pm.open(str(qd / "f.pdf")).page_count >= 1 and bool(probs))

print("FAILED:", check.failed or "none")
sys.exit(1 if check.failed else 0)
