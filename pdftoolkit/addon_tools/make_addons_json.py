"""addons.json for the release: python make_addons_json.py <out.json> <base_url> id=file ... (sizes and SHA-256 are measured)."""
import hashlib
import json
import sys
from pathlib import Path

out, base = sys.argv[1], sys.argv[2].rstrip("/")
META = {
    "formula-ocr": dict(
        title="Formula OCR (picture to LaTeX)", title_fa="OCR فرمول (تصویر به لاتک)", kind="libs",
        desc="Turns a photo, screenshot or PDF region of a printed formula into LaTeX, offline. Check every result.",
        desc_fa="عکس، اسکرین‌شات یا ناحیه‌ای از PDF را که فرمول چاپی دارد به لاتک تبدیل می‌کند، بدون اینترنت. هر نتیجه را بررسی کنید."),
    "tex-full": dict(
        title="More LaTeX packages (offline)", title_fa="بسته‌های بیشتر لاتک (آفلاین)", kind="texcache",
        desc="Hundreds more packages, classes, fonts and bibliography styles, so more documents compile without internet.",
        desc_fa="صدها بسته، کلاس، قلم و سبک کتاب‌نامهٔ بیشتر، تا اسناد بیشتری بدون اینترنت کامپایل شوند."),
}
items = []
for arg in sys.argv[3:]:
    aid, fname = arg.split("=", 1)
    p = Path(fname)
    items.append({"id": aid, **META[aid], "size_mb": max(1, p.stat().st_size // 1048576), "url": f"{base}/{p.name}",
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "version": "1"})
Path(out).write_text(json.dumps({"version": 1, "addons": items}, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(items, indent=1, ensure_ascii=False))
