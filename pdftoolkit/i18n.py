"""Interface language (English / Persian): translation, Arabic-script shaping, wrapping."""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import arabic_reshaper
    try:
        from bidi.algorithm import get_display  # mirrors brackets correctly
    except Exception:
        from bidi import get_display
except Exception:  # pragma: no cover - the app still works in English
    arabic_reshaper = None
    get_display = None

LANG = "en"
FA: dict[str, str] = {}  # English text -> Persian (filled by translations_fa.py)
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_reshaper = None


def set_lang(lang: str) -> None:
    global LANG
    LANG = lang if lang in ("en", "fa") else "en"
    if LANG == "fa":
        from translations_fa import FA as table
        FA.update(table)


def rtl() -> bool:
    return LANG == "fa"


def t(text: str) -> str:
    """Translate an English UI string (logical order, not yet shaped)."""
    return FA.get(text, text) if LANG == "fa" else text


def shape(line: str) -> str:
    """Logical Persian text -> text that Tk (no bidi/shaping support) draws correctly."""
    global _reshaper
    if not (arabic_reshaper and get_display) or not _ARABIC.search(line):
        return line
    if _reshaper is None:
        _reshaper = arabic_reshaper.ArabicReshaper(
            configuration={"delete_harakat": False, "support_ligatures": True})
    return get_display(_reshaper.reshape(line), base_dir="R")


def wrap(text: str, measure, max_w: int) -> list[str]:
    """Wrap logical text into lines no wider than max_w (measure() gets the *shaped* line)."""
    out: list[str] = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            cand = (cur + " " + w).strip()
            if cur and measure(shape(cand)) > max_w:
                out.append(cur)
                cur = w
            else:
                cur = cand
        out.append(cur)
    return out


def display(text: str, measure=None, max_w: int = 0) -> str:
    """Final string for a Tk widget: translated, wrapped (if asked) and shaped."""
    s = t(text)
    if LANG != "fa":
        return s
    lines = wrap(s, measure, max_w) if (measure and max_w) else s.split("\n")
    return "\n".join(shape(l) for l in lines)


def register_font(path: Path) -> bool:
    """Make a bundled TTF usable by Tk on Windows (no install needed)."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0))
    except Exception:
        return False
