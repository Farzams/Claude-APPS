"""Turns a CSV file into a LaTeX table or a pgfplots graph."""
import math
from decimal import Decimal, Context, ROUND_HALF_EVEN


class CsvData(object):
    def __init__(self, header, rows):
        self.header = header
        self.rows = rows

    def is_numeric(self, col):
        if not self.rows:
            return False
        for r in self.rows:
            try:
                float(r[col].strip().replace(",", "."))
            except (IndexError, ValueError):
                return False
        return True


def _split(line, sep):
    out, cur, quoted, i = [], [], False, 0
    while i < len(line):
        c = line[i]
        if quoted and c == '"' and i + 1 < len(line) and line[i + 1] == '"':
            cur.append('"')
            i += 1
        elif c == '"':
            quoted = not quoted
        elif c == sep and not quoted:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


def _is_num(s):
    try:
        float(s.strip().replace(",", "."))
        return True
    except ValueError:
        return False


def parse(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = [l for l in text.split("\n") if l.strip()][:2000]
    lines = [l.rstrip("\r") for l in lines]
    if not lines:
        return CsvData([], [])
    first = lines[0]
    sep = max([",", ";", "\t"], key=lambda c: first.count(c))
    if first.count(sep) == 0:
        sep = ","
    table = [_split(l, sep) for l in lines]
    width = max(len(r) for r in table)
    padded = [r + [""] * (width - len(r)) for r in table]
    if all(_is_num(c) for c in padded[0]):
        header = [chr(ord("A") + i % 26) + (str(i // 26) if i >= 26 else "") for i in range(width)]
        return CsvData(header, padded)
    return CsvData([c.strip() for c in padded[0]], padded[1:])


_ESC = {"&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#", "_": "\\_", "{": "\\{", "}": "\\}",
        "~": "\\textasciitilde{}", "^": "\\textasciicircum{}", "\\": "\\textbackslash{}"}


def esc(s):
    return "".join(_ESC.get(c, c) for c in s.strip())


def table(d, caption, max_rows=60):
    cols = len(d.header)
    spec = "".join("r" if d.is_numeric(i) else "l" for i in range(cols))
    sb = ["\\begin{table}[ht]\n  \\centering\n"]
    if caption.strip():
        sb.append("  \\caption{%s}\n" % esc(caption))
    sb.append("  \\begin{tabular}{%s}\n    \\toprule\n" % spec)
    sb.append("    " + " & ".join(esc(h) for h in d.header) + " \\\\\n    \\midrule\n")
    for r in d.rows[:max_rows]:
        sb.append("    " + " & ".join(esc(r[i] if i < len(r) else "") for i in range(cols)) + " \\\\\n")
    sb.append("    \\bottomrule\n  \\end{tabular}\n\\end{table}\n")
    return "".join(sb)


def _fmt(v):
    if v == math.floor(v) and abs(v) < 1e9:
        return str(int(v))
    d = Context(prec=6, rounding=ROUND_HALF_EVEN).create_decimal(repr(v))
    s = format(d.normalize(), "f")
    return s


def plot(d, x, ys, caption, points, max_points=400):
    sb = ["\\begin{figure}[ht]\n  \\centering\n  \\begin{tikzpicture}\n"]
    xl = esc(d.header[x]) if x < len(d.header) else "x"
    sb.append("    \\begin{axis}[width=0.9\\linewidth, height=6.5cm, grid=major, xlabel={%s}" % xl)
    if len(ys) == 1:
        sb.append(", ylabel={%s}" % esc(d.header[ys[0]]))
    if len(ys) > 1:
        sb.append(", legend pos=north west")
    sb.append("]\n")
    step = max(1, len(d.rows) // max_points)
    for y in ys:
        pts = []
        for i, r in enumerate(d.rows):
            if i % step:
                continue
            try:
                a = float(r[x].strip().replace(",", "."))
                b = float(r[y].strip().replace(",", "."))
            except (IndexError, ValueError):
                continue
            pts.append("(%s,%s)" % (_fmt(a), _fmt(b)))
        style = "only marks, mark=*, mark size=1.5pt" if points else "thick, mark=none"
        sb.append("      \\addplot[%s] coordinates {\n        " % style)
        sb.append("\n        ".join(" ".join(pts[i:i + 6]) for i in range(0, len(pts), 6)))
        sb.append("\n      };\n")
        if len(ys) > 1:
            sb.append("      \\addlegendentry{%s}\n" % esc(d.header[y]))
    sb.append("    \\end{axis}\n  \\end{tikzpicture}\n")
    if caption.strip():
        sb.append("  \\caption{%s}\n" % esc(caption))
    sb.append("\\end{figure}\n")
    return "".join(sb)
