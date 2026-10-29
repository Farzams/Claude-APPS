"""Text helpers shared by the editor: TeX log parsing, outline, word count, typing aids."""
import re
from collections import namedtuple

TexError = namedtuple("TexError", "line message file")
OutlineItem = namedtuple("OutlineItem", "line level title")

_SECTION = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{(.*)\}")
_LEVELS = ["part", "chapter", "section", "subsection", "subsubsection", "paragraph"]
_OPEN = re.compile(r"\((\.?/?[^\s()]+\.(?:tex|bib|sty|cls))")
_LINE = re.compile(r"^l\.(\d+)")


def parse_errors(log):
    """TeX writes '! message' and a few lines later 'l.<number> ...'; the file comes from the '(./file.tex ... )' nesting."""
    lines = log.split("\n")
    stack = []
    file_at = [None] * len(lines)
    for i, l in enumerate(lines):
        k = 0
        while k < len(l):
            c = l[k]
            if c == "(":
                m = _OPEN.match(l, k)
                if m:
                    name = m.group(1)
                    stack.append(name[2:] if name.startswith("./") else name)
                    k += len(m.group(0))
                    continue
                stack.append(None)
            elif c == ")" and stack:
                stack.pop()
            k += 1
        file_at[i] = next((s for s in reversed(stack) if s is not None), None)
    out = []
    for i, l in enumerate(lines):
        if not l.startswith("! "):
            continue
        ln = None
        for j in range(i + 1, min(i + 10, len(lines) - 1) + 1):
            m = _LINE.match(lines[j])
            if m:
                ln = int(m.group(1))
                break
        msg = l[2:].strip()
        if out and out[-1].message == msg and out[-1].line == ln:
            continue
        out.append(TexError(ln, msg, file_at[i - 1] if i > 0 else file_at[i]))
    return out


def outline(text):
    raw = []
    for i, l in enumerate(text.split("\n")):
        if l.lstrip().startswith("%"):
            continue
        m = _SECTION.search(l)
        if m:
            raw.append(OutlineItem(i + 1, _LEVELS.index(m.group(1)), m.group(2).strip()))
    base = min((r.level for r in raw), default=0)
    return [OutlineItem(r.line, r.level - base, r.title) for r in raw]


def count_words(text):
    lines = []
    for l in text.split("\n"):
        m = re.search(r"(?<!\\)%", l)
        lines.append(l[:m.start()] if m else l)
    t = "\n".join(lines)
    if "\\begin{document}" in t:
        t = t.split("\\begin{document}", 1)[1]
    t = t.split("\\end{document}", 1)[0]
    t = re.sub(r"\$\$?[^$]*\$\$?", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}\[\]\\^_&~#$%]", " ", t)
    return sum(1 for w in re.split(r"\s+", t) if any(ch.isalnum() for ch in w))


_CLOSER = {"{": "}", "[": "]", "(": ")"}


def smart_type(text, pos, ch):
    """What to do when [ch] is typed at [pos] in [text].
    Returns None (plain insertion), ('skip',) to step over an existing closer, or ('insert', string, caret) where
    caret is the offset inside the string to put the cursor at."""
    nxt = text[pos] if pos < len(text) else None
    if ch in "}])" and nxt == ch:
        return ("skip",)
    if ch == "$" and nxt == "$":
        return ("skip",)
    if ch in "{[(" and (nxt is None or nxt.isspace() or nxt in "}])$"):
        return ("insert", ch + _CLOSER[ch], 1)
    if ch == "$" and (nxt is None or nxt.isspace()) and (pos < 1 or text[pos - 1] != "\\"):
        return ("insert", "$$", 1)
    if ch == "\n":
        return _enter(text, pos)
    return None


def _enter(text, pos):
    line_start = text.rfind("\n", 0, pos) + 1
    prev = text[line_start:pos]
    indent = prev[:len(prev) - len(prev.lstrip(" \t"))]
    begin = re.match(r"^\s*\\begin\{([^}]+)\}", prev)
    after = text[pos:]
    if begin and "\\end{" not in prev:
        env = begin.group(1)
        inner = indent + "  "
        if ("\\end{%s}" % env) not in after:
            s = "\n" + inner + "\n" + indent + "\\end{" + env + "}"
            return ("insert", s, 1 + len(inner))
        return ("insert", "\n" + inner, 1 + len(inner))
    return ("insert", "\n" + indent, 1 + len(indent))
