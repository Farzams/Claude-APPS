"""Tiny JSON settings store (theme, picture, language)."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {"theme": "indigo_night", "wallpaper": "aurora", "custom_picture": "", "lang": "en", "strength": "medium"}


def _path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "PDFToolkit" / "settings.json"


def load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    except Exception:
        return dict(DEFAULTS)


def save(settings: dict) -> None:
    try:
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
