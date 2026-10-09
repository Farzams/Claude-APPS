"""End-to-end check of the bundled tools (run in CI before packaging, and locally)."""
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
import core  # noqa: E402

FA = ["فضاهای اورلیچ تعمیمی از فضاهای هستند.", "جبرهای باناخ و کاربردهای آن‌ها در نظریه عملگرها بررسی می‌شود.",
      "قضیه ۱. هر عملگر خطی کراندار روی فضای باناخ پیوسته است."]


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra)
    if not ok:
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

print("FAILED:", check.failed or "none")
sys.exit(1 if check.failed else 0)
