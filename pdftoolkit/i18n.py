"""Interface language (English / Persian). Qt does the shaping and right-to-left layout itself."""
from __future__ import annotations

import re

LANG = "en"
FA: dict[str, str] = {}  # English text -> Persian (filled from translations_fa.py)
_LATIN_START = re.compile(r"^[\s\W]*[A-Za-z]")
RLM = "‏"


def set_lang(lang: str) -> None:
    global LANG
    LANG = lang if lang in ("en", "fa") else "en"
    if LANG == "fa":
        from translations_fa import FA as table
        FA.update(table)


def rtl() -> bool:
    return LANG == "fa"


def t(text: str) -> str:
    """Translate an English UI string."""
    return FA.get(text, text) if LANG == "fa" else text


def tr(text: str) -> str:
    """Translate for display: Persian strings that start with Latin letters get an RLM so Qt
    lays the whole line out right-to-left."""
    s = t(text)
    if LANG == "fa" and s and _LATIN_START.match(s):
        return RLM + s
    return s


def trf(template: str, **kw) -> str:
    return tr(template).format(**kw)
