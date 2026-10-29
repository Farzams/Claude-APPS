"""English and Persian texts, shared with the Android app (extracted from its sources at build time)."""
import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_table = {"en": {}, "fa": {}}
lang = "en"


def load():
    with open(os.path.join(_DIR, "strings.json"), encoding="utf-8") as f:
        _table.update(json.load(f))


def set_lang(l):
    global lang
    lang = l if l in ("en", "fa") else "en"


def t(key):
    if not _table["en"]:
        load()
    return _table.get(lang, {}).get(key) or _table["en"].get(key) or key
