"""What can be completed after a backslash, inside \\begin{}, \\ref{}, \\cite{} and so on."""
import re

COMMANDS = """\\alpha \\beta \\gamma \\delta \\epsilon \\varepsilon \\zeta \\eta \\theta \\vartheta \\iota \\kappa \\lambda \\mu \\nu \\xi \\pi \\varpi \\rho \\varrho \\sigma \\varsigma \\tau \\upsilon \\phi \\varphi \\chi \\psi \\omega
\\Gamma \\Delta \\Theta \\Lambda \\Xi \\Pi \\Sigma \\Upsilon \\Phi \\Psi \\Omega
\\frac \\dfrac \\tfrac \\cfrac \\sqrt \\sum \\prod \\coprod \\int \\iint \\iiint \\oint \\lim \\limsup \\liminf \\sup \\inf \\max \\min \\arg \\det \\dim \\ker \\deg \\gcd \\hom \\exp \\log \\ln \\lg \\sin \\cos \\tan \\cot \\sec \\csc \\arcsin \\arccos \\arctan \\sinh \\cosh \\tanh \\coth \\Pr
\\partial \\nabla \\infty \\emptyset \\varnothing \\forall \\exists \\nexists \\neg \\wedge \\vee \\land \\lor \\implies \\impliedby \\iff \\to \\gets \\mapsto \\longmapsto \\rightarrow \\leftarrow \\leftrightarrow \\Rightarrow \\Leftarrow \\Leftrightarrow \\longrightarrow \\longleftarrow \\Longrightarrow \\Longleftarrow \\hookrightarrow \\rightharpoonup \\uparrow \\downarrow
\\in \\notin \\ni \\subset \\supset \\subseteq \\supseteq \\subsetneq \\supsetneq \\cup \\cap \\bigcup \\bigcap \\setminus \\sqcup \\uplus \\bigsqcup \\times \\cdot \\cdots \\ldots \\vdots \\ddots \\dots \\circ \\bullet \\star \\ast \\oplus \\otimes \\ominus \\odot \\pm \\mp \\div
\\leq \\geq \\le \\ge \\neq \\ne \\approx \\sim \\simeq \\cong \\equiv \\propto \\ll \\gg \\prec \\succ \\preceq \\succeq \\perp \\parallel \\mid \\nmid \\vdash \\models \\asymp \\doteq \\coloneqq
\\mathbb \\mathcal \\mathfrak \\mathbf \\mathrm \\mathit \\mathsf \\mathtt \\boldsymbol \\bm \\mathscr \\operatorname \\DeclareMathOperator \\text \\textbf \\textit \\texttt \\textsf \\textrm \\textsc \\textup \\emph \\underline \\overline \\overbrace \\underbrace \\hat \\widehat \\tilde \\widetilde \\bar \\vec \\dot \\ddot \\check \\breve \\acute \\grave \\overset \\underset \\stackrel \\xrightarrow \\xleftarrow
\\left \\right \\big \\Big \\bigg \\Bigg \\bigl \\bigr \\Bigl \\Bigr \\langle \\rangle \\lfloor \\rfloor \\lceil \\rceil \\lvert \\rvert \\lVert \\rVert \\| \\quad \\qquad \\hspace \\vspace \\hfill \\vfill \\newline \\linebreak \\pagebreak \\newpage \\clearpage \\noindent \\centering \\raggedright \\raggedleft
\\documentclass \\usepackage \\RequirePackage \\input \\include \\includeonly \\begin \\end \\title \\author \\date \\maketitle \\tableofcontents \\listoffigures \\listoftables \\appendix \\part \\chapter \\section \\subsection \\subsubsection \\paragraph \\subparagraph \\label \\ref \\eqref \\autoref \\cref \\Cref \\pageref \\nameref \\cite \\citep \\citet \\citeauthor \\citeyear \\nocite \\bibliography \\bibliographystyle \\printbibliography \\addbibresource \\footnote \\footnotemark \\footnotetext \\caption \\item \\newcommand \\renewcommand \\providecommand \\newenvironment \\renewenvironment \\newtheorem \\theoremstyle \\newcounter \\setcounter \\addtocounter \\stepcounter \\refstepcounter \\def \\let \\setlength \\addtolength \\setmainfont \\setsansfont \\setmonofont \\setmathfont \\setdefaultlanguage \\setotherlanguage \\settextfont
\\includegraphics \\graphicspath \\hline \\cline \\multicolumn \\multirow \\toprule \\midrule \\bottomrule \\cmidrule \\tabularnewline \\arraystretch \\tabcolsep \\rowcolors \\textcolor \\color \\colorbox \\fbox \\framebox \\mbox \\makebox \\parbox \\raisebox \\rule \\phantom \\hphantom \\vphantom \\smash \\not \\substack \\tag \\nonumber \\notag \\intertext \\shortintertext \\boxed \\binom \\dbinom \\tbinom \\choose \\pmod \\bmod \\mod \\displaystyle \\textstyle \\scriptstyle \\limits \\nolimits \\pagestyle \\thispagestyle \\pagenumbering \\fancyhead \\fancyfoot \\geometry \\hypersetup \\url \\href \\texorpdfstring \\today \\LaTeX \\TeX \\XeTeX \\ldots \\textbackslash \\textasciitilde \\ref \\lstinline \\lstset \\verb \\todo \\mathop \\mathrel \\mathbin \\mathord \\mathclose \\mathopen \\mathpunct \\vcenter \\tikz \\draw \\node \\fill \\coordinate \\addplot \\pgfplotsset \\ce \\si \\SI \\num \\qty \\unit \\ket \\bra \\braket \\expval \\dd \\dv \\pdv \\comm \\abs \\norm \\order \\vb \\grad \\curl \\divergence \\laplacian \\Re \\Im \\aleph \\hbar \\ell \\wp \\angle \\triangle \\square \\Box \\blacksquare \\therefore \\because \\checkmark \\dagger \\ddagger \\prime \\backslash \\lbrace \\rbrace \\lbrack \\rbrack \\mathbbm \\mathds \\bigoplus \\bigotimes \\bigwedge \\bigvee \\varinjlim \\varprojlim \\injlim \\projlim \\argmax \\argmin \\supp \\Var \\Cov \\Exp \\Prob""".split()
COMMANDS = sorted(set(COMMANDS))

ENVIRONMENTS = """document abstract equation equation* align align* aligned alignat gather gather* gathered multline multline* split cases array matrix pmatrix bmatrix Bmatrix vmatrix Vmatrix smallmatrix subequations
itemize enumerate description theorem lemma proposition corollary definition remark example proof claim conjecture notation assumption
figure figure* table table* tabular tabular* tabularx longtable center flushleft flushright minipage quote quotation verse verbatim lstlisting
tikzpicture axis frame columns block thebibliography appendix titlepage""".split()

PACKAGES = """amsmath amssymb amsthm amsfonts mathtools mathrsfs bm physics siunitx chemformula mhchem graphicx xcolor color hyperref cleveref geometry fancyhdr setspace enumitem booktabs multirow multicol longtable tabularx array caption subcaption float wrapfig tikz pgfplots pgf tikz-cd listings minted algorithm algorithm2e algorithmicx algpseudocode natbib biblatex babel polyglossia fontspec xepersian unicode-math microtype csquotes url footmisc titlesec tocloft appendix etoolbox xparse ifthen calc lipsum comment verbatim soul ulem cancel stmaryrd mathdots esint bbm dsfont upgreek textcomp inputenc fontenc lmodern times palatino helvet newtxtext newtxmath tcolorbox mdframed framed authblk epigraph imakeidx makeidx glossaries nomencl todonotes pdfpages rotating lscape pdflscape adjustbox changepage standalone braket diffcoeff derivative commath thmtools aliascnt cases empheq nccmath leftidx tensor yhmath wasysym marvosym pifont""".split()
PACKAGES = sorted(set(PACKAGES))

ENV_SNIPPETS = {
    "itemize": "\\begin{itemize}\n  \\item \u2038\n\\end{itemize}", "enumerate": "\\begin{enumerate}\n  \\item \u2038\n\\end{enumerate}",
    "figure": "\\begin{figure}[ht]\n  \\centering\n  \u2038\n  \\caption{}\n  \\label{fig:}\n\\end{figure}",
    "table": "\\begin{table}[ht]\n  \\centering\n  \\begin{tabular}{\u2038}\n  \\end{tabular}\n  \\caption{}\n  \\label{tab:}\n\\end{table}",
}

_CMD = re.compile(r"\\([A-Za-z@]*)$")
_ARG = re.compile(r"\\(begin|end|ref|eqref|autoref|cref|Cref|pageref|nameref|vref|cite[a-z]*|nocite|parencite|textcite|footcite|usepackage|RequirePackage|input|include|includegraphics|bibliography|addbibresource)\*?(?:\[[^\]]*\]){0,2}\{([^{}]*)$")


def context(before):
    """(kind, prefix) for the text in front of the cursor, or None.  kind is cmd, env, ref, cite, pkg or file."""
    m = _ARG.search(before)
    if m:
        name, prefix = m.group(1), m.group(2)
        if "," in prefix and name not in ("begin", "end"):
            prefix = prefix.rsplit(",", 1)[1].strip()
        kind = {"begin": "env", "end": "env", "usepackage": "pkg", "RequirePackage": "pkg"}.get(name)
        if kind is None:
            kind = "ref" if name in ("ref", "eqref", "autoref", "cref", "Cref", "pageref", "nameref", "vref") else (
                "cite" if name.startswith("cite") or name in ("nocite", "parencite", "textcite", "footcite") else "file")
        return kind, prefix
    m = _CMD.search(before)
    if m and (len(before) - len(m.group(0)) == 0 or before[len(before) - len(m.group(0)) - 1:len(before) - len(m.group(0))] != "\\"):
        return "cmd", m.group(1)
    return None


def candidates(kind, prefix, labels=(), keys=(), files=()):
    if kind == "cmd":
        pool = ["\\" + c[1:] for c in COMMANDS]
        pool = [c for c in pool if c.startswith("\\" + prefix)]
        return pool[:80] if prefix else []
    pool = {"env": ENVIRONMENTS, "pkg": PACKAGES, "ref": labels, "cite": keys, "file": files}.get(kind, [])
    low = prefix.lower()
    starts = [p for p in pool if p.lower().startswith(low)]
    inside = [p for p in pool if low in p.lower() and p not in starts]
    return (starts + inside)[:80]
