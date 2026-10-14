package app.pdftoolkit.mobile

/**
 * The symbol bar: groups of (label, text to insert). `‸` marks where the cursor goes afterwards.
 * Group keys double as string keys for the group names.
 */
val SYMBOL_GROUPS: List<Pair<String, List<Pair<String, String>>>> = listOf(
    "sym.math" to listOf(
        "\$ \$" to "\$‸\$", "\\[ \\]" to "\\[\n  ‸\n\\]", "frac" to "\\frac{‸}{}", "√" to "\\sqrt{‸}", "xⁿ" to "^{‸}", "xᵢ" to "_{‸}",
        "∫" to "\\int_{‸}^{}", "∑" to "\\sum_{i=1}^{‸}", "∏" to "\\prod_{‸}^{}", "lim" to "\\lim_{‸ \\to \\infty}", "( )" to "\\left(‸\\right)",
        "[ ]" to "\\left[‸\\right]", "{ }" to "\\{‸\\}", "| |" to "\\left|‸\\right|", "‖ ‖" to "\\|‸\\|", "x̄" to "\\overline{‸}", "x̂" to "\\hat{‸}",
        "vec" to "\\vec{‸}", "∂" to "\\partial ", "∇" to "\\nabla ", "sin" to "\\sin ", "cos" to "\\cos ", "log" to "\\log ", "exp" to "\\exp ",
        "max" to "\\max_{‸}", "sup" to "\\sup_{‸}", "inf" to "\\inf_{‸}", "ℝ" to "\\mathbb{R}", "ℕ" to "\\mathbb{N}", "ℤ" to "\\mathbb{Z}",
        "ℚ" to "\\mathbb{Q}", "ℂ" to "\\mathbb{C}", "𝔼" to "\\mathbb{E}", "𝒜" to "\\mathcal{A}", "binom" to "\\binom{‸}{}", "text" to "\\text{‸}",
    ),
    "sym.greek" to listOf(
        "α" to "\\alpha ", "β" to "\\beta ", "γ" to "\\gamma ", "δ" to "\\delta ", "ε" to "\\varepsilon ", "ζ" to "\\zeta ", "η" to "\\eta ",
        "θ" to "\\theta ", "ι" to "\\iota ", "κ" to "\\kappa ", "λ" to "\\lambda ", "μ" to "\\mu ", "ν" to "\\nu ", "ξ" to "\\xi ", "π" to "\\pi ",
        "ρ" to "\\rho ", "σ" to "\\sigma ", "τ" to "\\tau ", "υ" to "\\upsilon ", "φ" to "\\varphi ", "χ" to "\\chi ", "ψ" to "\\psi ", "ω" to "\\omega ",
        "Γ" to "\\Gamma ", "Δ" to "\\Delta ", "Θ" to "\\Theta ", "Λ" to "\\Lambda ", "Ξ" to "\\Xi ", "Π" to "\\Pi ", "Σ" to "\\Sigma ",
        "Φ" to "\\Phi ", "Ψ" to "\\Psi ", "Ω" to "\\Omega ",
    ),
    "sym.rel" to listOf(
        "≤" to "\\le ", "≥" to "\\ge ", "≠" to "\\ne ", "≈" to "\\approx ", "≡" to "\\equiv ", "∼" to "\\sim ", "≃" to "\\simeq ", "∝" to "\\propto ",
        "≪" to "\\ll ", "≫" to "\\gg ", "∈" to "\\in ", "∉" to "\\notin ", "⊂" to "\\subset ", "⊆" to "\\subseteq ", "⊃" to "\\supset ", "⊇" to "\\supseteq ",
        "∪" to "\\cup ", "∩" to "\\cap ", "∅" to "\\emptyset ", "∖" to "\\setminus ", "∀" to "\\forall ", "∃" to "\\exists ", "¬" to "\\neg ",
        "∧" to "\\wedge ", "∨" to "\\vee ", "±" to "\\pm ", "×" to "\\times ", "·" to "\\cdot ", "∘" to "\\circ ", "⊕" to "\\oplus ", "⊗" to "\\otimes ",
        "∞" to "\\infty ", "…" to "\\ldots ", "⋯" to "\\cdots ", "⟨ ⟩" to "\\langle ‸\\rangle ",
    ),
    "sym.arrow" to listOf(
        "→" to "\\to ", "←" to "\\leftarrow ", "↔" to "\\leftrightarrow ", "⇒" to "\\Rightarrow ", "⇐" to "\\Leftarrow ", "⇔" to "\\Leftrightarrow ",
        "↦" to "\\mapsto ", "↪" to "\\hookrightarrow ", "↠" to "\\twoheadrightarrow ", "⇀" to "\\rightharpoonup ", "⟶" to "\\longrightarrow ",
        "⟹" to "\\Longrightarrow ", "⟺" to "\\iff ", "↑" to "\\uparrow ", "↓" to "\\downarrow ",
    ),
    "sym.env" to listOf(
        "equation" to "\\begin{equation}\n  ‸\n\\end{equation}", "align" to "\\begin{align}\n  ‸\n\\end{align}", "align*" to "\\begin{align*}\n  ‸\n\\end{align*}",
        "gather" to "\\begin{gather}\n  ‸\n\\end{gather}", "cases" to "\\begin{cases}\n  ‸ & \\text{if } \\\\\n   & \\text{otherwise}\n\\end{cases}",
        "matrix" to "\\begin{pmatrix}\n  ‸ & \\\\\n   & \n\\end{pmatrix}", "itemize" to "\\begin{itemize}\n  \\item ‸\n\\end{itemize}",
        "enumerate" to "\\begin{enumerate}\n  \\item ‸\n\\end{enumerate}", "theorem" to "\\begin{theorem}\n  ‸\n\\end{theorem}",
        "lemma" to "\\begin{lemma}\n  ‸\n\\end{lemma}", "definition" to "\\begin{definition}\n  ‸\n\\end{definition}", "proof" to "\\begin{proof}\n  ‸\n\\end{proof}",
        "remark" to "\\begin{remark}\n  ‸\n\\end{remark}", "figure" to "\\begin{figure}[ht]\n  \\centering\n  \\includegraphics[width=0.8\\linewidth]{‸}\n  \\caption{}\n\\end{figure}",
        "table" to "\\begin{table}[ht]\n  \\centering\n  \\begin{tabular}{ll}\n    ‸ & \\\\\n  \\end{tabular}\n  \\caption{}\n\\end{table}",
        "abstract" to "\\begin{abstract}\n  ‸\n\\end{abstract}", "verbatim" to "\\begin{verbatim}\n‸\n\\end{verbatim}",
    ),
    "sym.text" to listOf(
        "section" to "\\section{‸}", "subsection" to "\\subsection{‸}", "subsubsection" to "\\subsubsection{‸}", "paragraph" to "\\paragraph{‸}",
        "bold" to "\\textbf{‸}", "italic" to "\\textit{‸}", "emph" to "\\emph{‸}", "mono" to "\\texttt{‸}", "underline" to "\\underline{‸}",
        "footnote" to "\\footnote{‸}", "item" to "\\item ", "newline" to "\\\\\n", "newpage" to "\\newpage\n", "vspace" to "\\vspace{‸cm}",
        "center" to "\\begin{center}\n  ‸\n\\end{center}", "url" to "\\url{‸}", "href" to "\\href{‸}{}", "–" to "--", "—" to "---", "“ ”" to "``‸''",
    ),
    "sym.ref" to listOf(
        "cite" to "\\cite{‸}", "label" to "\\label{‸}", "ref" to "\\ref{‸}", "eqref" to "\\eqref{‸}", "bibliography" to "\\bibliographystyle{plain}\n\\bibliography{‸}",
        "include" to "\\input{‸}", "package" to "\\usepackage{‸}", "newcommand" to "\\newcommand{\\‸}[1]{}", "tableofcontents" to "\\tableofcontents\n",
        "maketitle" to "\\maketitle\n", "geometry" to "\\usepackage[margin=2.5cm]{geometry}", "hyperref" to "\\usepackage[hidelinks]{hyperref}",
        "graphicx" to "\\usepackage{graphicx}", "amsmath" to "\\usepackage{amsmath,amssymb,amsthm}",
    ),
    "sym.thm" to listOf(
        "theorem" to "\\begin{theorem}\\label{thm:‸}\n  \n\\end{theorem}", "lemma" to "\\begin{lemma}\\label{lem:‸}\n  \n\\end{lemma}",
        "proposition" to "\\begin{proposition}\\label{prop:‸}\n  \n\\end{proposition}", "corollary" to "\\begin{corollary}\\label{cor:‸}\n  \n\\end{corollary}",
        "definition" to "\\begin{definition}\\label{def:‸}\n  \n\\end{definition}", "example" to "\\begin{example}\n  ‸\n\\end{example}",
        "remark" to "\\begin{remark}\n  ‸\n\\end{remark}", "conjecture" to "\\begin{conjecture}\n  ‸\n\\end{conjecture}",
        "proof" to "\\begin{proof}\n  ‸\n\\end{proof}", "proof ⇔" to "\\begin{proof}\n  ($\\Rightarrow$) ‸\n\n  ($\\Leftarrow$) \n\\end{proof}",
        "cases" to "\\begin{proof}\n  \\textit{Case 1.} ‸\n\n  \\textit{Case 2.} \n\\end{proof}",
        "induction" to "\\begin{proof}\n  We argue by induction on \$n\$. \\emph{Base case.} ‸\n\n  \\emph{Inductive step.} \n\\end{proof}",
        "qed" to "\\qedhere", "newtheorem" to "\\usepackage{amsthm}\n\\theoremstyle{plain}\n\\newtheorem{theorem}{Theorem}[section]\n\\newtheorem{lemma}[theorem]{Lemma}\n\\newtheorem{proposition}[theorem]{Proposition}\n\\newtheorem{corollary}[theorem]{Corollary}\n\\newtheorem{conjecture}[theorem]{Conjecture}\n\\theoremstyle{definition}\n\\newtheorem{definition}[theorem]{Definition}\n\\newtheorem{example}[theorem]{Example}\n\\theoremstyle{remark}\n\\newtheorem{remark}[theorem]{Remark}\n‸",
    ),
    "sym.phys" to listOf(
        "ħ" to "\\hbar ", "ket" to "\\ket{‸}", "bra" to "\\bra{‸}", "⟨a|b⟩" to "\\braket{‸}{}", "⟨A⟩" to "\\expval{‸}", "d/dt" to "\\dv{‸}{t}",
        "∂/∂x" to "\\pdv{‸}{x}", "dx" to "\\dd{‸}", "∇" to "\\nabla ", "∇×" to "\\curl{‸}", "∇·" to "\\div{‸}", "Δ" to "\\Delta ", "[A,B]" to "\\comm{‸}{}",
        "Tr" to "\\Tr ", "e" to "\\mathrm{e}", "i" to "\\mathrm{i}", "vec" to "\\vb{‸}", "unit" to "\\si{‸}", "SI" to "\\SI{‸}{}", "num" to "\\num{‸}",
        "m/s" to "\\si{\\meter\\per\\second}", "°C" to "\\SI{‸}{\\celsius}", "N" to "\\si{\\newton}", "J" to "\\si{\\joule}", "eV" to "\\si{\\electronvolt}",
        "packages" to "\\usepackage{physics}\n\\usepackage{siunitx}",
    ),
    "sym.chem" to listOf(
        "ce" to "\\ce{‸}", "H₂O" to "\\ce{H2O}", "CO₂" to "\\ce{CO2}", "reaction" to "\\ce{‸ + -> }", "⇌" to "\\ce{‸ <=> }", "yield" to "\\ce{A ->[\\Delta] B}",
        "ion" to "\\ce{Na+}", "ion²" to "\\ce{SO4^2-}", "(aq)" to "(aq)", "(s)" to "(s)", "(l)" to "(l)", "(g)" to "(g)", "↑" to "\\ce{^}",
        "mol/L" to "\\SI{‸}{\\mole\\per\\liter}", "g/mol" to "\\SI{‸}{\\gram\\per\\mole}", "K" to "\\SI{‸}{\\kelvin}", "kJ/mol" to "\\SI{‸}{\\kilo\\joule\\per\\mole}",
        "equation" to "\\begin{equation}\n  \\ce{‸ <=> }\n\\end{equation}", "packages" to "\\usepackage[version=4]{mhchem}\n\\usepackage{siunitx}",
    ),
    "sym.cs" to listOf(
        "algorithm" to "\\begin{algorithm}\n  \\caption{‸}\n  \\begin{algorithmic}[1]\n    \\Require input\n    \\Ensure output\n    \\State step\n  \\end{algorithmic}\n\\end{algorithm}",
        "if" to "\\If{‸}\n  \\State \n\\EndIf", "for" to "\\For{‸}\n  \\State \n\\EndFor", "while" to "\\While{‸}\n  \\State \n\\EndWhile",
        "function" to "\\Function{‸}{args}\n  \\State \n\\EndFunction", "state" to "\\State ‸", "return" to "\\State \\Return ‸",
        "code" to "\\begin{lstlisting}[language=Python]\n‸\n\\end{lstlisting}", "inline" to "\\lstinline|‸|", "O( )" to "\\mathcal{O}(‸)", "Θ( )" to "\\Theta(‸)",
        "Ω( )" to "\\Omega(‸)", "mod" to "\\bmod ", "⌊ ⌋" to "\\lfloor ‸ \\rfloor", "⌈ ⌉" to "\\lceil ‸ \\rceil", "log₂" to "\\log_2 ",
        "packages" to "\\usepackage{algorithm}\n\\usepackage{algpseudocode}\n\\usepackage{listings}",
    ),
    "sym.fig" to listOf(
        "tikz" to "\\begin{tikzpicture}\n  ‸\n\\end{tikzpicture}", "node" to "\\node[draw, rounded corners] (a) at (0,0) {‸};", "arrow" to "\\draw[->, thick] (0,0) -- (‸2,0);",
        "line" to "\\draw (0,0) -- (‸2,1);", "circle" to "\\draw (0,0) circle (‸1);", "rect" to "\\draw (0,0) rectangle (‸2,1);",
        "plot" to "\\begin{tikzpicture}\n  \\begin{axis}[xlabel={\$x\$}, ylabel={\$y\$}, grid=major]\n    \\addplot[thick, domain=0:6, samples=100] {‸sin(deg(x))};\n  \\end{axis}\n\\end{tikzpicture}",
        "circuit" to "\\begin{circuitikz}\n  \\draw (0,0) to[battery1, l=\$V\$] (0,3) to[R, l=\$R\$] (3,3) to[C, l=\$C\$] (3,0) -- (0,0);\n\\end{circuitikz}",
        "table" to "\\begin{tabular}{lrr}\n  \\toprule\n  ‸ & A & B \\\\\n  \\midrule\n   &  &  \\\\\n  \\bottomrule\n\\end{tabular}",
        "subfigure" to "\\begin{figure}[ht]\n  \\centering\n  \\begin{subfigure}{0.48\\linewidth}\n    \\includegraphics[width=\\linewidth]{‸}\n    \\caption{}\n  \\end{subfigure}\n  \\hfill\n  \\begin{subfigure}{0.48\\linewidth}\n    \\includegraphics[width=\\linewidth]{}\n    \\caption{}\n  \\end{subfigure}\n  \\caption{}\n\\end{figure}",
        "box" to "\\begin{tcolorbox}[title={‸}]\n  \n\\end{tcolorbox}",
        "packages" to "\\usepackage{tikz}\n\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.17}\n\\usepackage{booktabs}\n\\usepackage{subcaption}",
    ),
)
