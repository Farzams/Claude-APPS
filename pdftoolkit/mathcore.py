"""Math engine (no GUI): SymPy calculator and plots.

Every operation returns a Result with a plain-text answer, LaTeX and (for plots) a PNG.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field


@dataclass
class Result:
    text: str = ""
    latex: str = ""
    png: bytes | None = None
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- parsing
def _sympy():
    import sympy
    return sympy


_ODE = re.compile(r"\b([A-Za-z]\w*)('+)(?!\w)")


def parse(text: str, local: dict | None = None):
    """Parse typed math (x^2, 2x, sin(x)/x, pi, oo, e) or LaTeX (starts with a backslash or contains \\frac)."""
    import sympy as sp
    from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application, parse_expr,
                                            standard_transformations)
    t = text.strip()
    if not t:
        raise ValueError("Empty expression")
    if "\\" in t:
        from sympy.parsing.latex import parse_latex
        return parse_latex(t, backend="lark")
    # y'' -> Derivative(y(x), (x, 2))   (only for names followed by primes)
    def ode_(m):
        return f"Derivative({m.group(1)}, (x, {len(m.group(2))}))"
    t = _ODE.sub(ode_, t)
    t = re.sub(r"\bln\(", "log(", t)
    ns = {"e": sp.E, "pi": sp.pi, "oo": sp.oo, "inf": sp.oo, "I": sp.I, "i": sp.I, "Abs": sp.Abs, "abs": sp.Abs,
          "Derivative": sp.Derivative, "sign": sp.sign, "Max": sp.Max, "Min": sp.Min, "gamma": sp.gamma,
          "Gamma": sp.gamma, "beta": sp.beta, "erf": sp.erf, "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh}
    if local:
        ns.update(local)
    tr = standard_transformations + (convert_xor, implicit_multiplication_application)
    return parse_expr(t, local_dict=ns, transformations=tr, evaluate=True)


def _eq(text: str):
    """'a = b' -> Eq(a, b); otherwise the expression (meaning expr = 0)."""
    import sympy as sp
    if "=" in text and "==" not in text and "<=" not in text and ">=" not in text:
        lhs, rhs = text.split("=", 1)
        return sp.Eq(parse(lhs), parse(rhs))
    return parse(text)


def _sym(name: str):
    import sympy as sp
    return sp.Symbol(name.strip() or "x")


def _fmt(sp, obj):
    return sp.pretty(obj, use_unicode=True, wrap_line=False) if not isinstance(obj, (int, float)) else str(obj)


def _res(obj, prefix: str = "") -> Result:
    import sympy as sp
    try:
        latex = sp.latex(obj)
    except Exception:
        latex = str(obj)
    return Result(text=prefix + str(obj), latex=(prefix and "") + latex)


def _lim_value(text: str):
    import sympy as sp
    t = text.strip().lower()
    if t in ("oo", "inf", "infinity", "∞", "+oo", "+inf"):
        return sp.oo
    if t in ("-oo", "-inf", "-infinity", "-∞"):
        return -sp.oo
    return parse(text)


# ---------------------------------------------------------------- plain operations
def evaluate(expr: str, digits: int = 15) -> Result:
    import sympy as sp
    e = parse(expr)
    exact = sp.simplify(e)
    num = sp.N(e, int(digits))
    r = Result(text=f"{exact}\n≈ {num}", latex=sp.latex(exact) + (r" \approx " + sp.latex(num) if exact != num else ""))
    return r


def simplify(expr: str) -> Result:
    import sympy as sp
    return _res(sp.simplify(parse(expr)))


def expand(expr: str) -> Result:
    import sympy as sp
    return _res(sp.expand(parse(expr)))


def factor(expr: str) -> Result:
    import sympy as sp
    return _res(sp.factor(parse(expr)))


def apart(expr: str, var: str = "x") -> Result:
    import sympy as sp
    return _res(sp.apart(parse(expr), _sym(var)))


def diff(expr: str, var: str = "x", order: int = 1) -> Result:
    import sympy as sp
    v = _sym(var)
    e = parse(expr)
    d = sp.diff(e, v, int(order))
    r = _res(sp.simplify(d))
    r.latex = r"\frac{d" + (f"^{{{order}}}" if int(order) > 1 else "") + "}{d" + sp.latex(v) + (f"^{{{order}}}" if int(order) > 1 else "") + "}\\left(" + sp.latex(e) + r"\right) = " + r.latex
    return r


def integrate(expr: str, var: str = "x", lower: str = "", upper: str = "") -> Result:
    import sympy as sp
    v = _sym(var)
    e = parse(expr)
    if lower.strip() and upper.strip():
        a, b = _lim_value(lower), _lim_value(upper)
        val = sp.integrate(e, (v, a, b))
        r = _res(val)
        r.latex = r"\int_{" + sp.latex(a) + "}^{" + sp.latex(b) + "} " + sp.latex(e) + r"\,d" + sp.latex(v) + " = " + r.latex
        if isinstance(val, sp.Integral) or val.has(sp.Integral):
            try:
                r.notes.append("Numerical value: " + str(sp.N(sp.Integral(e, (v, a, b)))))
            except Exception:
                pass
        else:
            try:
                r.text += f"\n≈ {sp.N(val)}"
            except Exception:
                pass
        return r
    val = sp.integrate(e, v)
    r = _res(val)
    r.text += "  + C"
    r.latex = r"\int " + sp.latex(e) + r"\,d" + sp.latex(v) + " = " + r.latex + " + C"
    if isinstance(val, sp.Integral):
        r.notes.append("No closed form was found.")
    return r


def limit(expr: str, var: str = "x", point: str = "0", direction: str = "+-") -> Result:
    import sympy as sp
    v = _sym(var)
    p = _lim_value(point)
    d = {"+": "+", "-": "-"}.get(direction, "+-")
    val = sp.limit(parse(expr), v, p, d)
    r = _res(val)
    sign = {"+": "^{+}", "-": "^{-}"}.get(d, "")
    r.latex = r"\lim_{" + sp.latex(v) + r"\to " + sp.latex(p) + sign + "} " + sp.latex(parse(expr)) + " = " + r.latex
    return r


def series(expr: str, var: str = "x", point: str = "0", order: int = 6) -> Result:
    import sympy as sp
    v = _sym(var)
    s = sp.series(parse(expr), v, _lim_value(point), int(order))
    return _res(s)


def summation(expr: str, var: str = "n", lower: str = "1", upper: str = "oo") -> Result:
    import sympy as sp
    v = _sym(var)
    a, b = _lim_value(lower), _lim_value(upper)
    e = parse(expr)
    val = sp.summation(e, (v, a, b))
    r = _res(val)
    r.latex = r"\sum_{" + sp.latex(v) + "=" + sp.latex(a) + "}^{" + sp.latex(b) + "} " + sp.latex(e) + " = " + r.latex
    return r


def solve(eqs: str, vars_: str = "") -> Result:
    import sympy as sp
    lines = [l.strip() for l in re.split(r"[\n;]", eqs) if l.strip()]
    system = [_eq(l) for l in lines]
    syms = [_sym(v) for v in vars_.split(",") if v.strip()]
    target = system if len(system) > 1 else system[0]
    sol = sp.solve(target, *syms, dict=True) if syms else sp.solve(target, dict=True)
    if not sol:
        return Result(text="No solution found.", latex=r"\text{no solution found}")
    out_t, out_l = [], []
    for s in sol:
        out_t.append(", ".join(f"{k} = {v}" for k, v in s.items()))
        out_l.append(r",\ ".join(f"{sp.latex(k)} = {sp.latex(v)}" for k, v in s.items()))
    return Result(text="\n".join(out_t), latex=r"\\ ".join(out_l) if len(out_l) > 1 else out_l[0])


def ode(eq: str, func: str = "y", var: str = "x") -> Result:
    import sympy as sp
    x = _sym(var)
    y = sp.Function(func)
    text = re.sub(rf"\b{re.escape(func)}\(\s*{re.escape(var)}\s*\)", func, eq)      # y(x) -> y
    text = text.replace(f"{func}'", f"{func}'")
    lines = text.split("=", 1)
    local = {func: y(x)}
    if len(lines) == 2:
        e = sp.Eq(parse(lines[0], local), parse(lines[1], local))
    else:
        e = sp.Eq(parse(lines[0], local), 0)
    return _res(sp.dsolve(e, y(x)))


def matrix_op(text: str, op: str = "det") -> Result:
    import sympy as sp
    m = sp.Matrix(parse(text) if not text.strip().startswith("[[") else sp.sympify(text.strip()))
    if op == "det":
        r = sp.simplify(m.det())
    elif op == "inverse":
        r = m.inv()
    elif op == "rank":
        r = m.rank()
    elif op == "transpose":
        r = m.T
    elif op == "rref":
        r = m.rref()[0]
    elif op == "eigen":
        ev = m.eigenvects()
        lines = [f"λ = {v}  (multiplicity {mult}),  vectors: {[list(x) for x in vecs]}" for v, mult, vecs in ev]
        lat = r",\quad ".join(r"\lambda = " + sp.latex(v) for v, _m, _x in ev)
        return Result(text="\n".join(lines), latex=lat)
    elif op == "nullspace":
        r = m.nullspace()
        return Result(text=str([list(v) for v in r]), latex=r",\ ".join(sp.latex(v) for v in r))
    elif op == "charpoly":
        r = m.charpoly().as_expr()
    else:
        raise ValueError(op)
    return Result(text=str(r), latex=sp.latex(r))


# ---------------------------------------------------------------- plots
def plot(exprs: str, var: str = "x", lo: float = -10, hi: float = 10, title: str = "", dark: bool = False) -> Result:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import sympy as sp
    v = _sym(var)
    lines = [l.strip() for l in exprs.splitlines() if l.strip()]
    if not lines:
        raise ValueError("Enter at least one function")
    xs = np.linspace(float(lo), float(hi), 1600)
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=130)
    if dark:
        fig.patch.set_facecolor("#1d212b")
        ax.set_facecolor("#1d212b")
        for sp_ in ax.spines.values():
            sp_.set_color("#9aa3b2")
        ax.tick_params(colors="#c9d1e0")
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for k, l in enumerate(lines):
        e = parse(l.split("=", 1)[1] if re.match(r"^\s*[A-Za-z]\w*(\(\w\))?\s*=", l) else l)
        f = sp.lambdify(v, e, modules=["numpy"])
        with np.errstate(all="ignore"):
            ys = np.asarray(f(xs), dtype=float) if not np.isscalar(f(xs)) else np.full_like(xs, float(f(xs)))
        ys = np.where(np.isfinite(ys), ys, np.nan)
        cap = np.nanpercentile(np.abs(ys), 98) * 3 if np.isfinite(ys).any() else 1
        ys = np.where(np.abs(ys) > max(cap, 1e-9) * 5, np.nan, ys)      # cut vertical asymptotes
        ax.plot(xs, ys, color=colors[k % len(colors)], lw=1.8, label=f"${sp.latex(e)}$")
    ax.axhline(0, color="#888", lw=0.8)
    ax.axvline(0, color="#888", lw=0.8)
    ax.grid(alpha=0.25)
    ax.set_xlabel(f"${sp.latex(v)}$")
    if title:
        ax.set_title(title)
    leg = ax.legend(loc="best", framealpha=0.6)
    if dark:
        for t in leg.get_texts():
            t.set_color("#e6e9f0")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return Result(text=f"{len(lines)} curve(s) on [{lo}, {hi}]", latex="", png=buf.getvalue())


# ---------------------------------------------------------------- rendering
def _mathtext_safe(latex: str) -> str:
    """Rewrite common LaTeX that Matplotlib's math engine does not know."""
    t = re.sub(r"\\(textstyle|displaystyle|scriptstyle|scriptscriptstyle|limits|nolimits)\b", "", latex)
    t = re.sub(r"\\operatorname\*?\s*\{([^{}]*)\}", r"\\mathrm{\1}", t)
    t = re.sub(r"\\(mathbbm|mathds)\b", r"\\mathbb", t)
    t = t.replace("\\;", " ").replace("\\!", "").replace("\\:", " ")
    return t


def latex_png(latex: str, fontsize: int = 18, color: str = "#111111", dpi: int = 200) -> bytes | None:
    """Render a LaTeX formula to PNG: Matplotlib's built-in math engine first, the real LaTeX engine as a fallback."""
    png = _mathtext_png(_mathtext_safe(latex), fontsize, color, dpi)
    if png:
        return png
    try:
        import texengine
        imgs, _log = texengine.render_formulas([(latex, True)], dpi=dpi, color=color)
        if imgs and imgs[0].ok:
            return imgs[0].png
    except Exception:
        pass
    return None


def _mathtext_png(latex: str, fontsize: int = 18, color: str = "#111111", dpi: int = 200) -> bytes | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if not latex.strip():
        return None
    parts = [p for p in re.split(r"\\\\\s*|\n", latex) if p.strip()]
    fig = plt.figure(figsize=(0.1, 0.1), dpi=dpi)
    try:
        y = 0.0
        texts = []
        for p in parts:
            texts.append(fig.text(0, 0, f"${p.strip()}$", fontsize=fontsize, color=color))
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        boxes = [t.get_window_extent(r) for t in texts]
        w = max(b.width for b in boxes) + 20
        h = sum(b.height for b in boxes) + 14 * len(boxes) + 10
        fig.set_size_inches(w / dpi, h / dpi)
        cur = h - 8
        for t, b in zip(texts, boxes):
            cur -= b.height
            t.set_position((10 / w, cur / h))
            cur -= 14
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        return buf.getvalue()
    except Exception:
        return None
    finally:
        plt.close(fig)


# ---------------------------------------------------------------- dispatcher
OPS = {
    "evaluate": evaluate, "simplify": simplify, "expand": expand, "factor": factor, "apart": apart, "diff": diff,
    "integrate": integrate, "limit": limit, "series": series, "sum": summation, "solve": solve, "ode": ode,
    "matrix": matrix_op, "plot": plot,
}


def run(name: str, /, **kw) -> Result:
    """Run one operation; adds a rendered picture of the LaTeX when the operation did not make one."""
    color = kw.pop("_color", "#111111")
    res = OPS[name](**kw)
    if res.png is None and res.latex:
        res.png = latex_png(res.latex, color=color)
    return res
