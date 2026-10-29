import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def all_templates():
    with open(os.path.join(_DIR, "templates.json"), encoding="utf-8") as f:
        return json.load(f)


def symbol_groups():
    with open(os.path.join(_DIR, "symbols.json"), encoding="utf-8") as f:
        return json.load(f)
