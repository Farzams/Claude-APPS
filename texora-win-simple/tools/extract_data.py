"""Reads the Android sources of TeXora and writes the data the desktop app shares with it as JSON:
strings (English and Persian), project templates and the symbol bar.  Runs on Python 3.8."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
ANDROID = os.path.join(ROOT, "android", "app", "src")
OUT = os.path.join(HERE, "..", "texora", "data")

LIT = r'"((?:[^"\\]|\\.)*)"'


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "u" and i + 5 < len(s) + 0:
                out.append(chr(int(s[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def read(*parts):
    with open(os.path.join(ANDROID, *parts), encoding="utf-8") as f:
        return f.read()


def strings():
    text = read("main", "java", "app", "pdftoolkit", "mobile", "Strings.kt")
    rx = re.compile(LIT + r'\s+to\s+\(\s*' + LIT + r'\s+to\s+' + LIT + r'\s*\)')
    en, fa = {}, {}
    for m in rx.finditer(text):
        k, a, b = (unescape(g) for g in m.groups())
        en[k] = a
        fa[k] = b
    return {"en": en, "fa": fa}


def raw_vals(text):
    vals = {}
    for m in re.finditer(r'val ([A-Z_]+) = """(.*?)"""', text, re.S):
        vals[m.group(1)] = m.group(2).replace("${'$'}", "$")
    return vals


def templates():
    base = ("latex", "java", "app", "pdftoolkit", "mobile")
    v = raw_vals(read(*base, "Templates.kt"))
    v.update(raw_vals(read(*base, "TemplatesMore.kt")))
    refs = v["REFS"]

    def t(key, files, engine="xetex", group="general"):
        return {"key": key, "files": files, "main": "main.tex", "engine": engine, "group": group}

    def sci(key, name, bib=False):
        files = {"main.tex": v[name]}
        if bib:
            files["refs.bib"] = refs
        return t(key, files, "pdftex", "science")

    def journal(key, name):
        return t(key, {"main.tex": v[name], "refs.bib": refs}, "pdftex", "journal")

    return [
        t("tpl.article", {"main.tex": v["ARTICLE"]}),
        t("tpl.bib", {"main.tex": v["ARTICLE_BIB"], "refs.bib": refs}),
        t("tpl.persian", {"main.tex": v["PERSIAN"]}),
        t("tpl.report", {"main.tex": v["REPORT"]}),
        t("tpl.beamer", {"main.tex": v["BEAMER"]}),
        t("tpl.letter", {"main.tex": v["LETTER"]}),
        t("tpl.blank", {"main.tex": v["BLANK"]}),
        sci("tpl.physics", "PHYSICS"), sci("tpl.chem", "CHEM"), sci("tpl.cs", "CS"), sci("tpl.eng", "ENG"),
        sci("tpl.bio", "BIO", True), sci("tpl.plots", "PLOTS"),
        journal("tpl.elsevier", "ELSEVIER"),
        t("tpl.apa", {"main.tex": v["APA"]}, "pdftex", "journal"),
        t("tpl.thesis", {"main.tex": v["THESIS"], "refs.bib": refs}, "pdftex", "journal"),
        t("tpl.poster", {"main.tex": v["POSTER"]}, "pdftex", "journal"),
    ]


def symbols():
    text = read("latex", "java", "app", "pdftoolkit", "mobile", "Symbols.kt")
    text = text[text.index("SYMBOL_GROUPS"):]
    groups = []
    toks = [(m.start(), m.end(), unescape(m.group(1))) for m in re.finditer(LIT, text)]
    cur = None
    i = 0
    while i < len(toks):
        s, e, val = toks[i]
        if val.startswith("sym.") and re.match(r'\s*to\s+listOf\(', text[e:e + 20]):
            cur = {"key": val, "items": []}
            groups.append(cur)
            i += 1
            continue
        if cur is not None and i + 1 < len(toks):
            cur["items"].append([val, toks[i + 1][2]])
            i += 2
            continue
        i += 1
    return groups


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {"strings.json": strings(), "templates.json": templates(), "symbols.json": symbols()}
    for name, obj in data.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    s = data["strings.json"]
    print("strings en=%d fa=%d, templates=%d, symbol groups=%d (%d symbols)" % (
        len(s["en"]), len(s["fa"]), len(data["templates.json"]), len(data["symbols.json"]),
        sum(len(g["items"]) for g in data["symbols.json"])))


if __name__ == "__main__":
    sys.exit(main())
