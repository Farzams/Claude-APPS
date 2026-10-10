"""LaTeX editor/compiler page, formula-to-image page and the symbol palette."""
from __future__ import annotations

import io
import re
from pathlib import Path

from PySide6.QtCore import QObject, QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QPixmap, QSyntaxHighlighter, QTextCharFormat, QTextCursor,
                           QTextFormat)
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QSplitter, QTextEdit, QToolButton,
                               QVBoxLayout, QWidget)

import core
import i18n
import qt_style
import spell
import symbols
import templates
import texengine
import theme
from i18n import tr, trf
import settings
from qt_common import Form, Tool, mkbutton, mkcheck, mkcombo, mklabel
from qt_read import PdfView


class TexHighlighter(QSyntaxHighlighter):
    """Colours commands, $math$ and % comments."""

    def __init__(self, doc):
        super().__init__(doc)
        self.rules: list = []
        self.recolor()

    def recolor(self):
        P = theme.STATE.pal

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f
        self.rules = [
            (QRegularExpression(r"\$[^$\n]*\$"), fmt(P["good"])),
            (QRegularExpression(r"\\[A-Za-z@]+|\\[^A-Za-z]"), fmt(P["accent_hover"] if P["dark"] else P["accent"], True)),
            (QRegularExpression(r"%[^\n]*"), fmt(P["muted"])),
        ]
        self.rehighlight()

    spell_on = False

    def highlightBlock(self, text):
        for rx, f in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), f)
        state = max(self.previousBlockState(), 0)
        if self.spell_on and spell.CHECKER.ready:
            words, state = spell.scan(text, state)
            for start, length, w in words:
                if not spell.CHECKER.check(w):
                    f = self.format(start)
                    f.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
                    f.setUnderlineColor(QColor("#e5484d"))
                    self.setFormat(start, length, f)
        elif self.spell_on:
            _w, state = spell.scan(text, state)
        self.setCurrentBlockState(state)


class _SpellSignals(QObject):
    loaded = Signal()


class SpellEditor(QPlainTextEdit):
    """Plain-text editor with a right-click menu that offers spelling suggestions."""

    changed_dictionary = None      # set by the page: called after "Add to dictionary"

    def _word_at(self, pos):
        cur = self.cursorForPosition(pos)
        block = cur.block()
        text, col = block.text(), cur.positionInBlock()
        state = max(block.previous().userState(), 0) if block.previous().isValid() else 0
        words, _s = spell.scan(text, state)
        for start, length, w in words:
            if start <= col <= start + length:
                return block.position() + start, length, w
        return None

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        hit = self._word_at(e.pos()) if (self.document().findBlockByNumber(0).isValid() and spell.CHECKER.ready
                                         and TexHighlighter.spell_on) else None
        if hit and not spell.CHECKER.check(hit[2]):
            pos, length, word = hit
            first = menu.actions()[0] if menu.actions() else None
            sugg = spell.CHECKER.suggest(word)
            acts = []
            for s in sugg:
                a = menu.addAction(s)
                a.triggered.connect(lambda _=False, s=s, pos=pos, length=length: self._replace(pos, length, s))
                acts.append(a)
            if not sugg:
                n = menu.addAction(tr("(no suggestions)"))
                n.setEnabled(False)
                acts.append(n)
            add = menu.addAction(tr("Add to dictionary"))
            add.triggered.connect(lambda _=False: self._learn(word))
            ign = menu.addAction(tr("Ignore this word"))
            ign.triggered.connect(lambda _=False: self._ignore(word))
            acts += [add, ign, menu.addSeparator()]
            for a in acts:
                menu.removeAction(a)
                menu.insertAction(first, a)
        menu.exec(e.globalPos())

    def _replace(self, pos, length, text):
        c = self.textCursor()
        c.setPosition(pos)
        c.setPosition(pos + length, QTextCursor.KeepAnchor)
        c.insertText(text)

    def _learn(self, word):
        spell.CHECKER.add(word)
        if self.changed_dictionary:
            self.changed_dictionary()

    def _ignore(self, word):
        spell.CHECKER.ignore_word(word)
        if self.changed_dictionary:
            self.changed_dictionary()


def insert_snippet(widget: QPlainTextEdit, tex: str):
    """Insert LaTeX at the cursor; a '▢' marks where the cursor ends up."""
    pos = tex.find("▢")
    text = tex.replace("▢", "")
    cur = widget.textCursor()
    start = cur.position()
    cur.insertText(text)
    if pos >= 0:
        cur.setPosition(start + pos)
        widget.setTextCursor(cur)
    widget.setFocus()


class LatexTool(Tool):
    key, icon, title = "latex", "latex", "LaTeX"
    subtitle = "Write or open a .tex file, compile it to PDF and see errors explained in plain words."

    def build(self):
        self.path: str | None = None
        self._saved = ""
        self._result = None
        self._imported = None
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.tpl_names = {tr(n): n for n in templates.TEMPLATES}
        self.tpl = mkcombo([tr("New from template…")] + list(self.tpl_names))
        self.tpl.activated.connect(self._new_template)
        bar.addWidget(self.tpl)
        bar.addWidget(mkbutton("Open…", self.open_dialog))
        bar.addWidget(mkbutton("Save", self.save))
        bar.addWidget(mkbutton("Import…", self.import_dialog))
        bar.addWidget(mkbutton("Symbols", self.win.show_palette))
        bar.addStretch(1)
        eng = texengine.find_engine()
        self.engine_lbl = mklabel(eng.label if eng else "No LaTeX engine", "muted")
        bar.addWidget(self.engine_lbl)
        self.compile_btn = mkbutton("Compile ▶", self.compile, "primary")
        self.compile_btn.setMinimumWidth(120)
        bar.addWidget(self.compile_btn)
        self.body.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        self.editor = SpellEditor()
        self.editor.setFont(qt_style.mono_font(10.5))
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setLayoutDirection(Qt.LeftToRight)
        self.editor.setTabStopDistance(28)
        self.hl = TexHighlighter(self.editor.document())
        self.editor.changed_dictionary = self.hl.rehighlight
        self.editor.focusInEvent_orig = self.editor.focusInEvent
        self.editor.focusInEvent = self._focus_in
        self.preview = PdfView(with_zoom=False)
        split.addWidget(self.editor)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        self.body.addWidget(split, 1)

        self.status = mklabel("Write LaTeX, press Compile (Ctrl+Enter).", "muted")
        srow = QHBoxLayout()
        srow.addWidget(self.status, 1)
        self.spell_cb = mkcheck("Spell-check", bool(self.win.cfg.get("spell", True)))
        self.spell_cb.setToolTip(tr("Underlines misspelled English and Persian words (math, commands and labels are skipped)"))
        self.spell_cb.toggled.connect(self._spell_toggled)
        self._sp_sig = _SpellSignals()
        self._sp_sig.loaded.connect(self._spell_loaded)
        srow.addWidget(self.spell_cb)
        self.body.addLayout(srow)
        self.errs = QListWidget()
        self.errs.setMaximumHeight(112)
        self.errs.setLayoutDirection(Qt.LeftToRight)
        self.errs.currentRowChanged.connect(self._jump)
        self.body.addWidget(self.errs)
        self._errors: list = []
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence("Ctrl+Return"), self.editor, activated=self.compile)
        QShortcut(QKeySequence("Ctrl+S"), self.editor, activated=self.save)

    def _spell_toggled(self, on: bool):
        self.win.cfg["spell"] = on
        settings.save(self.win.cfg)
        self._apply_spell()

    def _apply_spell(self):
        on = self.spell_cb.isChecked()
        TexHighlighter.spell_on = on
        if on and not spell.CHECKER.ready and not spell.CHECKER.loading:
            import threading
            self.status.setText(tr("Loading dictionaries…"))
            threading.Thread(target=spell.CHECKER.load, args=(self._sp_sig.loaded.emit,), daemon=True).start()
        else:
            self.hl.rehighlight()

    def _spell_loaded(self):
        self.status.setText(tr("Write LaTeX, press Compile (Ctrl+Enter)."))
        self.hl.rehighlight()

    def _focus_in(self, e):
        self.win.insert_target = self.editor
        self.editor.focusInEvent_orig(e)

    def on_show(self):
        self.hl.recolor()
        if not getattr(self, "_spell_started", False):
            self._spell_started = True
            QTimer.singleShot(400, self._apply_spell)

    # ---- files
    def _confirm_discard(self) -> bool:
        txt = self.editor.toPlainText()
        if txt != self._saved and txt.strip():
            r = QMessageBox.question(self, tr("Unsaved changes"),
                                     tr("Replace the text in the editor? Unsaved changes will be lost."))
            return r == QMessageBox.Yes
        return True

    def _set_text(self, text):
        self.editor.setPlainText(text)
        self._saved = text

    def _new_template(self, idx):
        name = self.tpl_names.get(self.tpl.itemText(idx))
        self.tpl.setCurrentIndex(0)
        if not name or not self._confirm_discard():
            return
        self._set_text(templates.get(name, texengine.fonts_dir()))
        self.path = None
        self.status.setText(tr("Template loaded. Press Compile — you will be asked where to save it."))

    def open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "", "", "LaTeX (*.tex *.ltx);;All files (*.*)")
        if p:
            self.open_file(p)

    def open_file(self, p: str):
        if not self._confirm_discard():
            return
        self._set_text(Path(p).read_text(encoding="utf-8", errors="replace"))
        self.path = p
        self.status.setText(p)
        pdf = Path(p).with_suffix(".pdf")
        if pdf.exists():
            self.preview.open(str(pdf))

    def drop(self, paths):
        p = paths[0]
        if p.lower().endswith((".tex", ".ltx")):
            self.open_file(p)
        elif p.lower().endswith(".pdf"):
            self.preview.open(p)

    def save(self) -> bool:
        if not self.path:
            p, _ = QFileDialog.getSaveFileName(self, "", "", "LaTeX (*.tex)")
            if not p:
                return False
            self.path = p if Path(p).suffix else p + ".tex"
        Path(self.path).write_text(self.editor.toPlainText(), encoding="utf-8")
        self._saved = self.editor.toPlainText()
        self.status.setText(trf("Saved {name}", name=Path(self.path).name))
        return True

    def import_dialog(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "", "", "Word, Markdown, ODT, EPUB, HTML (*.docx *.odt *.rtf *.md *.markdown *.epub *.html *.htm);;All files (*.*)")
        if not p or self.win.jobs.busy:
            return
        self._imported = None

        def job(log, prog):
            prog(1, 3)
            self._imported = texengine.import_to_latex(p, str(Path(p).parent))
            log(trf("✔ Imported {name} → {out}", name=Path(p).name, out=Path(self._imported).name))
            return str(Path(p).parent)
        self.win.run(job, done=lambda: self._imported and self.open_file(self._imported))

    # ---- compile
    def compile(self):
        if self.win.jobs.busy or not self.save():
            return
        path = self.path
        self.status.setText(tr("Compiling…"))
        self.errs.clear()

        def job(log, prog):
            prog(1, 4)
            res = texengine.compile_tex(path)
            self._result = res
            if res.ok:
                log(trf("✔ {name} compiled with {engine} in {sec} s", name=Path(path).name, engine=res.engine,
                        sec=f"{res.seconds:.1f}"))
            else:
                log(trf("✘ {n} error(s) in {name}", n=len(res.errors), name=Path(path).name))
            prog(1, 1)
            return str(Path(path).parent)
        self.win.run(job, done=self._after)

    def _after(self):
        res = self._result
        if not res:
            return
        self.errs.clear()
        self._errors = res.errors
        sels = []
        for e in res.errors:
            hint = f"   —   {tr(e.hint)}" if e.hint else ""
            self.errs.addItem(f"{e.line:>4}   {e.message}{hint}" if e.line else f"       {e.message}{hint}")
            if e.line:
                cur = QTextCursor(self.editor.document().findBlockByNumber(e.line - 1))
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cur
                sel.format.setBackground(QColor(theme.STATE.pal["hover"]))
                sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                sels.append(sel)
        self.editor.setExtraSelections(sels)
        if res.ok:
            self.status.setText(trf("✔ {name} compiled with {engine} in {sec} s", name=Path(self.path).name,
                                    engine=res.engine, sec=f"{res.seconds:.1f}"))
            self.engine_lbl.setText(res.engine)
            if res.pdf:
                self.preview.load_keep_page(res.pdf) if self.preview.reader else self.preview.open(res.pdf)
        else:
            self.status.setText(trf("✘ {n} error(s) in {name}", n=len(res.errors), name=Path(self.path).name))

    def _jump(self, row):
        if row < 0 or row >= len(self._errors):
            return
        e = self._errors[row]
        if e.line:
            cur = QTextCursor(self.editor.document().findBlockByNumber(e.line - 1))
            self.editor.setTextCursor(cur)
            self.editor.centerCursor()
        if e.hint:
            self.status.setText(tr(e.hint))


class FormulaTool(Tool):
    key, icon, title = "formula", "formula", "Formula"
    subtitle = "Type a formula in LaTeX and get a crisp image (PNG, SVG or PDF) for slides, Word or papers."
    EXAMPLES = {
        "Luxemburg norm (Orlicz)": r"\|f\|_{(\Phi)}=\inf\Bigl\{k>0:\int_\Omega \Phi\Bigl(\frac{|f|}{k}\Bigr)\,d\mu\le 1\Bigr\}",
        "Quadratic formula": r"x=\frac{-b\pm\sqrt{b^{2}-4ac}}{2a}",
        "Fourier transform": r"\widehat{f}(\xi)=\int_{\mathbb{R}^{n}} f(x)\,e^{-2\pi i\,x\cdot\xi}\,dx",
        "Cauchy–Schwarz inequality": r"\left|\langle x,y\rangle\right|\le\|x\|\,\|y\|",
        "Schrödinger equation": r"i\hbar\,\frac{\partial}{\partial t}\Psi(\mathbf{r},t)=\hat H\,\Psi(\mathbf{r},t)",
        "Maxwell: Gauss's law": r"\nabla\cdot\mathbf{E}=\frac{\rho}{\varepsilon_{0}}",
        "Nernst equation": r"E=E^{\circ}-\frac{RT}{nF}\ln Q",
        "Methane combustion": r"\ce{CH4 + 2O2 -> CO2 + 2H2O}",
        "Ammonia equilibrium": r"\ce{N2 + 3H2 <=> 2NH3}",
    }
    COLORS = {"Black": None, "White": "#ffffff", "Dark blue": "#1e3a8a", "Red": "#b91c1c", "Green": "#166534"}

    def build(self):
        self._last = None
        f = Form()
        self.ex = mkcombo([tr("Examples…")] + [tr(k) for k in self.EXAMPLES])
        self.ex.activated.connect(self._example)
        f.row("Example", self.ex)
        self.body.addLayout(f)
        self.body.addWidget(mklabel("LaTeX", "h"))
        self.box = QPlainTextEdit(r"\int_{0}^{1} x^{2}\,dx=\frac{1}{3}")
        self.box.setFont(qt_style.mono_font(11))
        self.box.setLayoutDirection(Qt.LeftToRight)
        self.box.setFixedHeight(84)
        self.box.focusInEvent_orig = self.box.focusInEvent
        self.box.focusInEvent = self._focus_in
        self.body.addWidget(self.box)
        opts = QHBoxLayout()
        opts.setSpacing(8)
        self.mode = mkcombo({tr("Display (large)"): True, tr("Inline (small)"): False})
        self.size = mkcombo({tr("Normal (300 dpi)"): 300, tr("Large (450 dpi)"): 450, tr("Huge (600 dpi)"): 600})
        self.color = mkcombo({tr(k): v for k, v in self.COLORS.items()})
        for w in (self.mode, self.size, self.color):
            opts.addWidget(w, 1)
        self.body.addLayout(opts)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(mkbutton("Render", self.render, "primary", 120))
        bar.addWidget(mkbutton("Save…", self.save))
        bar.addWidget(mkbutton("Copy LaTeX", self.copy))
        bar.addWidget(mkbutton("Symbols", self.win.show_palette))
        bar.addStretch(1)
        self.transp = mkcheck("Transparent background", True)
        bar.addWidget(self.transp)
        self.body.addLayout(bar)
        self.paper = QFrame()
        self.paper.setObjectName("paper")
        self.paper.setMinimumHeight(150)
        pl = QVBoxLayout(self.paper)
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.pic)
        self.body.addWidget(self.paper, 1)
        self.msg = mklabel("", "muted")
        self.body.addWidget(self.msg)

    def _focus_in(self, e):
        self.win.insert_target = self.box
        self.box.focusInEvent_orig(e)

    def _example(self, idx):
        if idx <= 0:
            return
        tex = list(self.EXAMPLES.values())[idx - 1]
        self.ex.setCurrentIndex(0)
        self.box.setPlainText(tex)
        self.render()

    def _params(self):
        return (self.box.toPlainText().strip(), self.mode.currentData(), self.color.currentData(),
                self.transp.isChecked())

    def copy(self):
        QApplication.clipboard().setText(self.box.toPlainText().strip())
        self.win.toast("LaTeX copied")

    def render(self):
        tex, disp, color, _tr = self._params()
        if not tex or self.win.jobs.busy:
            return
        self.msg.setText(tr("Rendering…"))
        self._last = None

        def job(log, prog):
            prog(1, 3)
            imgs, logtxt = texengine.render_formulas([(tex, disp)], dpi=300, color=color, transparent=True)
            if imgs[0].ok:
                self._last = imgs[0]
            else:
                errs = texengine.parse_errors(logtxt)
                raise RuntimeError(errs[0].message if errs else "could not render")
            prog(1, 1)
        self.win.run(job, done=self._shown)

    def _shown(self):
        im = self._last
        if not im:
            self.msg.setText(tr("Could not render this formula. See the log below."))
            return
        dark_paper = (self.color.currentData() or "").lower() == "#ffffff"
        self.paper.setStyleSheet(f"QFrame#paper {{ background: {'#1b1b1b' if dark_paper else '#ffffff'}; border-radius: 12px; }}")
        pm = QPixmap()
        pm.loadFromData(im.png)
        dpr = self.devicePixelRatioF()
        scale = min(1.0, (self.paper.width() - 40) * dpr / max(pm.width(), 1), (self.paper.height() - 24) * dpr / max(pm.height(), 1))
        pm = pm.scaled(int(pm.width() * scale), int(pm.height() * scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        self.pic.setPixmap(pm)
        self.msg.setText(tr("Rendered. Use Save… for PNG, SVG or PDF."))

    def save(self):
        tex, disp, color, transp = self._params()
        if not tex or self.win.jobs.busy:
            return
        p, _ = QFileDialog.getSaveFileName(self, "", "", "PNG image (*.png);;SVG vector (*.svg);;PDF (*.pdf)")
        if not p:
            return
        fmt = Path(p).suffix.lower().lstrip(".")
        if fmt not in ("png", "svg", "pdf"):
            fmt, p = "png", p + ".png"
        dpi = self.size.currentData()
        base = str(Path(p).with_suffix(""))

        def job(log, prog):
            prog(1, 3)
            files = texengine.formula_files(tex, disp, base, (fmt,), dpi, color, transp)
            log(trf("✔ Saved {name}", name=Path(files[0]).name))
            return str(Path(p).parent)
        self.win.run(job)


class SymbolPalette(QDialog):
    """Floating window: click a symbol to insert its LaTeX at the cursor."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(tr("Symbols"))
        self.setWindowFlag(Qt.Tool, True)
        self.resize(720, 540)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        self.q = QLineEdit()
        self.q.setPlaceholderText(tr("Search: integral, alpha, ∂, norm…"))
        self.q.textChanged.connect(self._search)
        lay.addWidget(self.q)
        mid = QHBoxLayout()
        self.cats = QListWidget()
        self.cats.setFixedWidth(190)
        for c in symbols.CATEGORIES:
            self.cats.addItem(tr(c))
        self.cats.currentRowChanged.connect(lambda r: self.show_cat(symbols.CATEGORIES[r]) if r >= 0 else None)
        mid.addWidget(self.cats)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(6)
        self.grid.setAlignment(Qt.AlignTop)
        mid.addWidget(self.grid_host, 1)
        lay.addLayout(mid, 1)
        self.info = QLabel("")
        self.info.setFont(qt_style.mono_font(10))
        self.info.setProperty("role", "muted")
        self.info.setLayoutDirection(Qt.LeftToRight)
        lay.addWidget(self.info)
        self.cats.setCurrentRow(0)

    def show_cat(self, cat):
        self._fill([(g, tex, w, pkg) for g, tex, w, pkg in symbols.SYMBOLS[cat]])

    def _search(self, text):
        if not text.strip():
            return self.show_cat(symbols.CATEGORIES[max(self.cats.currentRow(), 0)])
        self._fill([(g, tex, w, pkg) for g, tex, w, pkg, _c in symbols.search(text)])

    def _fill(self, items):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        cols = 8
        for i, (g, tex, words, pkg) in enumerate(items[:96]):
            b = QToolButton()
            b.setText(g)
            b.setProperty("sym", True)
            b.setFont(qt_style.symbol_font(13))
            b.setFixedSize(66, 46)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(f"{tex.replace('▢', '')}\n{words}" + (f"\n[{pkg}]" if pkg else ""))
            b.clicked.connect(lambda _=False, tex=tex: self.win.insert_snippet(tex))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, tex=tex: self.win.copy_snippet(tex))
            b.enterEvent = (lambda e, tex=tex, words=words, pkg=pkg, orig=b.enterEvent:
                            (self.info.setText(f"{tex.replace('▢', '')}     {words}" + (f"     [{pkg}]" if pkg else "")),
                             orig(e))[1])
            self.grid.addWidget(b, i // cols, i % cols)
        if not items:
            self.grid.addWidget(mklabel("Nothing found.", "muted"), 0, 0)
