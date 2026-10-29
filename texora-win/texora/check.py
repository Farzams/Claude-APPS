"""The project check: mistakes that are easy to find before compiling."""
import re
from collections import namedtuple

CheckIssue = namedtuple("CheckIssue", "kind detail file line")

LABEL = re.compile(r"\\label\{([^}]*)\}")
REF = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|pageref|nameref|vref)\*?\{([^}]*)\}")
CITE = re.compile(r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|nocite|parencite|textcite|footcite)\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
BEGIN = re.compile(r"\\begin\{([^}]+)\}")
END = re.compile(r"\\end\{([^}]+)\}")
INPUT = re.compile(r"\\(input|include)\{([^}]+)\}")
GRAPHIC = re.compile(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^}]+)\}")
BIBFILE = re.compile(r"\\bibliography\{([^}]+)\}")
OVERFULL = re.compile(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)")
BIBKEY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")


def bib_keys(text):
    return BIBKEY.findall(text)


def _code(line):
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "%":
            return line[:i]
        i += 1
    return line


def _split(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def run(tex, bib, all_files, main_file, log=""):
    """tex and bib map file names to their text; all_files is the set of every file name in the project."""
    out = []
    labels, refs, cites = [], [], []
    noncite_all = False
    uses_bib = False
    for fname, text in tex.items():
        stack = []
        for i, raw in enumerate(text.split("\n")):
            l = _code(raw)
            no = i + 1
            for m in LABEL.finditer(l):
                labels.append((m.group(1).strip(), fname, no))
            for m in REF.finditer(l):
                for k in _split(m.group(1)):
                    refs.append((k, fname, no))
            for m in CITE.finditer(l):
                for k in _split(m.group(1)):
                    if k == "*":
                        noncite_all = True
                    else:
                        cites.append((k, fname, no))
            if BIBFILE.search(l) or "\\addbibresource" in l:
                uses_bib = True
            marks = [(m.start(), True, m.group(1)) for m in BEGIN.finditer(l)] + \
                    [(m.start(), False, m.group(1)) for m in END.finditer(l)]
            for _, opening, name in sorted(marks):
                if name == "document" and not opening:
                    continue
                if opening:
                    stack.append((name, no))
                elif stack and stack[-1][0] == name:
                    stack.pop()
                else:
                    out.append(CheckIssue("check.end", "\\end{%s}" % name, fname, no))
            for m in INPUT.finditer(l):
                target = m.group(2).strip()
                if target not in all_files and target + ".tex" not in all_files:
                    out.append(CheckIssue("check.nofile", target, fname, no))
            for m in GRAPHIC.finditer(l):
                target = m.group(1).strip()
                if target not in all_files and not any(target + "." + e in all_files for e in ("png", "jpg", "jpeg", "pdf", "eps")):
                    out.append(CheckIssue("check.nofile", target, fname, no))
        for name, no in stack:
            if name != "document":
                out.append(CheckIssue("check.begin", "\\begin{%s}" % name, fname, no))

    label_keys = set(k for k, _, _ in labels)
    ref_keys = set(k for k, _, _ in refs)
    seen = set()
    for k, f, n in refs:
        if k not in label_keys and k not in seen:
            seen.add(k)
            out.append(CheckIssue("check.undef.ref", k, f, n))
    by_label = {}
    for k, f, n in labels:
        by_label.setdefault(k, []).append((f, n))
    for k, v in by_label.items():
        if len(v) > 1:
            out.append(CheckIssue("check.dup.label", k, v[1][0], v[1][1]))
    seen = set()
    for k, f, n in labels:
        if k not in ref_keys and k not in seen:
            seen.add(k)
            out.append(CheckIssue("check.unused.label", k, f, n))

    entries = []
    for f, text in bib.items():
        for i, line in enumerate(text.split("\n")):
            for k in bib_keys(line):
                entries.append((k, f, i + 1))
    entry_keys = set(k for k, _, _ in entries)
    seen = set()
    if uses_bib or entries:
        for k, f, n in cites:
            if k not in entry_keys and k not in seen:
                seen.add(k)
                out.append(CheckIssue("check.undef.cite", k, f, n))
        if not noncite_all:
            used = set(k for k, _, _ in cites)
            seen = set()
            for k, f, n in entries:
                if k not in used and k not in seen:
                    seen.add(k)
                    out.append(CheckIssue("check.unused.entry", k, f, n))
    else:
        for k, f, n in cites:
            if k not in seen:
                seen.add(k)
                out.append(CheckIssue("check.undef.cite", k, f, n))

    for m in OVERFULL.finditer(log):
        pt = float(m.group(1))
        if pt >= 10.0:
            after = log[m.end():m.end() + 160]
            lm = re.search(r"lines (\d+)", after)
            out.append(CheckIssue("check.wide", "%d pt" % int(pt), main_file, int(lm.group(1)) if lm else None))
    return out
