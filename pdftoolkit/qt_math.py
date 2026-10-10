"""Math page: exact calculator (SymPy) and plots (Matplotlib)."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (QGridLayout, QSizePolicy, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

import mathproc
import qt_style
import theme
from i18n import tr, trf
from qt_common import Form, Tool, mkbutton, mkcombo, mklabel

# (title, op, main kwarg, main label, placeholder, [(kwarg, label, default, choices|None)], examples)
GROUPS = [
    ("Calculate", [
        ("Evaluate (exact and numeric)", "evaluate", "expr", "Expression", "sqrt(2)*pi + e^2",
         [("digits", "Digits", "15", None)], ["sqrt(2)*pi", "sin(pi/7)", "(1+sqrt(5))/2", "2^100"]),
        ("Simplify", "simplify", "expr", "Expression", "(x^2-1)/(x-1)", [], ["(x^2-1)/(x-1)", "sin(x)^2+cos(x)^2", "log(x^2)-2*log(x)"]),
        ("Expand", "expand", "expr", "Expression", "(x+y)^5", [], ["(x+y)^5", "(a+b)*(a-b)"]),
        ("Factor", "factor", "expr", "Expression", "x^4-1", [], ["x^4-1", "x^3-6x^2+11x-6"]),
        ("Partial fractions", "apart", "expr", "Expression", "1/(x^2-1)", [("var", "Variable", "x", None)], ["1/(x^2-1)", "(2x+3)/(x^2+3x+2)"]),
    ]),
    ("Calculus", [
        ("Derivative", "diff", "expr", "Function", "x^3*sin(x)",
         [("var", "Variable", "x", None), ("order", "Order", "1", None)], ["x^3*sin(x)", "exp(-x^2)", "x^x"]),
        ("Integral", "integrate", "expr", "Function", "x*exp(-x)",
         [("var", "Variable", "x", None), ("lower", "From (empty = indefinite)", "", None), ("upper", "To", "", None)],
         ["x*exp(-x)", "exp(-x^2)", "1/(1+x^2)", "log(x)"]),
        ("Limit", "limit", "expr", "Function", "sin(x)/x",
         [("var", "Variable", "x", None), ("point", "Approaches (e.g. 0, oo)", "0", None),
          ("direction", "From", "+-", {"both sides": "+-", "right (+)": "+", "left (−)": "-"})],
         ["sin(x)/x", "(1+1/x)^x", "(exp(x)-1)/x"]),
        ("Taylor series", "series", "expr", "Function", "exp(x)",
         [("var", "Variable", "x", None), ("point", "Around", "0", None), ("order", "Terms", "6", None)], ["exp(x)", "sin(x)", "1/(1-x)"]),
        ("Sum", "sum", "expr", "Term", "1/n^2",
         [("var", "Variable", "n", None), ("lower", "From", "1", None), ("upper", "To (e.g. oo)", "oo", None)], ["1/n^2", "1/2^n", "n^2"]),
    ]),
    ("Equations", [
        ("Solve equation or system", "solve", "eqs", "Equation(s), one per line", "x^2 - 5x + 6 = 0",
         [("vars_", "Unknowns (comma, optional)", "", None)], ["x^2 - 5x + 6 = 0", "x + y = 3\nx - y = 1", "exp(x) = 5"]),
        ("Differential equation", "ode", "eq", "Equation (use y', y'')", "y'' + y = 0",
         [("func", "Function", "y", None), ("var", "Variable", "x", None)], ["y'' + y = 0", "y' = y", "y' + 2*y = exp(-x)"]),
    ]),
    ("Matrices", [
        ("Matrix operation", "matrix", "text", "Matrix, e.g. [[1,2],[3,4]]", "[[1,2],[3,4]]",
         [("op", "Operation", "det", {"determinant": "det", "inverse": "inverse", "rank": "rank", "transpose": "transpose",
                                      "row-reduced form": "rref", "eigenvalues and vectors": "eigen",
                                      "null space": "nullspace", "characteristic polynomial": "charpoly"})],
         ["[[1,2],[3,4]]", "[[2,0],[0,3]]", "[[1,2,3],[4,5,6],[7,8,10]]"]),
    ]),
    ("Plot", [
        ("Plot functions", "plot", "exprs", "Function(s), one per line", "sin(x)\nx^2/10",
         [("var", "Variable", "x", None), ("lo", "x from", "-6", None), ("hi", "x to", "6", None)], ["sin(x)\ncos(x)", "x^3 - 3x", "exp(-x^2)"]),
    ]),
]
NUMERIC = {"digits": int, "order": int, "lo": float, "hi": float}
DARK_OPS = {"plot"}


class _Sig(QObject):
    done = Signal(object, str)


class _Job(QRunnable):
    def __init__(self, op: str, kw: dict):
        super().__init__()
        self.op, self.kw, self.s = op, kw, _Sig()

    def run(self):
        try:
            res = mathproc.WORKER.run(self.op, self.kw, 90.0)
            self.s.done.emit(res, "")
        except Exception as e:
            self.s.done.emit(None, str(e))


class MathTool(Tool):
    key, icon, title = "math", "math", "Math"
    subtitle = "Algebra, calculus, equations, matrices and plots. Results as LaTeX."

    def build(self):
        self._busy = False
        self.specs = {}
        self.op = mkcombo({})
        for gname, items in GROUPS:
            self.op.addItem(f"— {tr(gname)} —")
            self.op.model().item(self.op.count() - 1).setEnabled(False)
            for spec in items:
                self.op.addItem(tr(spec[0]), spec[1])
                self.specs[spec[1]] = spec
        self.op.setCurrentIndex(1)
        self.op.currentIndexChanged.connect(self._op)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(mklabel("What to do", "muted"))
        left.addWidget(self.op)
        self.main_lbl = mklabel("Expression", "muted")
        left.addWidget(self.main_lbl)
        self.main = QPlainTextEdit()
        self.main.setMinimumHeight(74)
        self.main.setMaximumHeight(120)
        self.main.setLayoutDirection(Qt.LeftToRight)
        self.main.setFont(qt_style.mono_font(11.5))
        left.addWidget(self.main)
        row = QHBoxLayout()
        self.ex = mkcombo({})
        self.ex.setMinimumContentsLength(18)
        self.ex.activated.connect(self._example)
        row.addWidget(mklabel("Examples", "muted"))
        row.addWidget(self.ex)
        row.addStretch(1)
        left.addLayout(row)
        self.panels = QStackedWidget()
        self.fields: dict[str, dict] = {}
        self.pidx = {}
        for _g, items in GROUPS:
            for spec in items:
                w = QWidget()
                f = Form(120)
                w.setLayout(f)
                d = {}
                for kw, label, default, choices in spec[5]:
                    if not kw:
                        continue
                    if choices:
                        c = mkcombo({tr(k): v for k, v in choices.items()}, default)
                    else:
                        c = QLineEdit(default)
                        c.setLayoutDirection(Qt.LeftToRight)
                    f.row(label, c)
                    d[kw] = c
                self.fields[spec[1]] = d
                self.pidx[spec[1]] = self.panels.addWidget(w)
        left.addWidget(self.panels)
        btns = QHBoxLayout()
        self.go = mkbutton("Calculate", self.run, "primary", 160)
        btns.addWidget(self.go)
        self.state = mklabel("", "muted", translate=False)
        btns.addWidget(self.state, 1)
        left.addLayout(btns)
        self.main.installEventFilter(self)
        # result
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignCenter)
        self.pic.setMinimumSize(1, 90)
        self.pic.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)       # the picture adapts to the space
        self._pm = None
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.pic)
        sc.setMinimumHeight(260)
        sc.setLayoutDirection(Qt.LeftToRight)
        right.addWidget(sc, 1)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setMinimumHeight(110)
        self.out.setMaximumHeight(170)
        self.out.setLayoutDirection(Qt.LeftToRight)
        self.out.setFont(qt_style.mono_font(10.5))
        right.addWidget(self.out)
        acts = QGridLayout()
        acts.setSpacing(6)
        acts.addWidget(mkbutton("Copy LaTeX", self.copy_latex), 0, 0)
        acts.addWidget(mkbutton("Copy answer", self.copy_text), 0, 1)
        acts.addWidget(mkbutton("Insert into the LaTeX page", self.insert), 1, 0)
        acts.addWidget(mkbutton("Save picture…", self.save_png), 1, 1)
        right.addLayout(acts)
        left.addStretch(1)
        cols = QHBoxLayout()
        cols.setSpacing(18)
        cols.addLayout(left, 5)
        cols.addLayout(right, 6)
        self.body.addLayout(cols, 1)
        self.result = None
        self._op()

    def eventFilter(self, obj, ev):                      # Ctrl+Enter calculates
        from PySide6.QtCore import QEvent
        if obj is self.main and ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter) \
                and ev.modifiers() & Qt.ControlModifier:
            self.run()
            return True
        return super().eventFilter(obj, ev)

    def on_show(self):
        try:                       # start the calculation process in the background so the first answer is quick
            QThreadPool.globalInstance().start(_Warm())
        except Exception:
            pass

    def _cur(self):
        return self.specs[self.op.currentData()]

    def _op(self):
        data = self.op.currentData()
        if not data:
            return
        spec = self._cur()
        self.main_lbl.setText(tr(spec[3]))
        self.main.setPlainText(spec[4])
        self.panels.setCurrentIndex(self.pidx[data])
        for i in range(self.panels.count()):                 # only the visible panel decides the height
            self.panels.widget(i).setSizePolicy(QSizePolicy.Preferred if i == self.pidx[data] else QSizePolicy.Ignored,
                                                QSizePolicy.Preferred if i == self.pidx[data] else QSizePolicy.Ignored)
        self.ex.clear()
        self.ex.addItem(tr("Choose an example…"), "")
        for e in spec[6]:
            self.ex.addItem(e.replace("\n", "  ⏎  "), e)

    def _example(self, i):
        v = self.ex.itemData(i)
        if v:
            self.main.setPlainText(v)

    def run(self):
        if self._busy:
            return
        spec = self._cur()
        op, main_kw = spec[1], spec[2]
        text = self.main.toPlainText().strip()
        if not text:
            return self.win.warn(tr("Missing information"), tr("Type an expression first."))
        kw = {main_kw: text}
        try:
            for k, w in self.fields[op].items():
                v = w.currentData() if hasattr(w, "currentData") else w.text().strip()
                if k in NUMERIC:
                    v = NUMERIC[k](v)
                kw[k] = v
        except ValueError:
            return self.win.warn(tr("Missing information"), tr("A number is not valid."))
        kw["_color"] = theme.STATE.pal["text"]
        if op in DARK_OPS:
            kw["dark"] = bool(theme.STATE.pal["dark"])
        self._busy = True
        self.go.setEnabled(False)
        self.state.setText(tr("Working…"))
        job = _Job(op, kw)
        job.s.done.connect(self._done)
        self._keep = job
        QThreadPool.globalInstance().start(job)

    def _done(self, res, err):
        self._busy = False
        self.go.setEnabled(True)
        self.state.setText("")
        if err:
            self.result = None
            self.pic.clear()
            self.out.setPlainText("✘ " + err)
            return
        self.result = res
        self.out.setPlainText(res.text + ("\n\n" + "\n".join("ℹ " + n for n in res.notes) if res.notes else ""))
        if res.png:
            pm = QPixmap()
            pm.loadFromData(res.png)
            self._pm, self._natural = pm, (res.latex != "")
            self._show_pm()
        else:
            self._pm = None
            self.pic.setText(res.latex)

    def _show_pm(self):
        if self._pm is None:
            return
        dpr = self.devicePixelRatioF()
        avail = max(self.pic.width() - 12, 120)
        w = self._pm.width()
        target = min(w, avail * dpr) if not self._natural else min(w * 0.8 * dpr, avail * dpr)
        pm = self._pm.scaledToWidth(max(int(target), 40), Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        self.pic.setPixmap(pm)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._show_pm()

    # ---- actions
    def copy_latex(self):
        if self.result and self.result.latex:
            QGuiApplication.clipboard().setText(self.result.latex)
            self.win.toast("LaTeX copied")

    def copy_text(self):
        if self.result:
            QGuiApplication.clipboard().setText(self.result.text)
            self.win.toast("Copied")

    def insert(self):
        if self.result and self.result.latex:
            self.win.insert_snippet("$" + self.result.latex + "$")

    def save_png(self):
        if not (self.result and self.result.png):
            return
        p, _ = QFileDialog.getSaveFileName(self, "", "result.png", "PNG (*.png)")
        if p:
            with open(p, "wb") as f:
                f.write(self.result.png)
            self.win.toast("Saved")


class _Warm(QRunnable):
    def run(self):
        try:
            mathproc.WORKER.start()
        except Exception:
            pass
