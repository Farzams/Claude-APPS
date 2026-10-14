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
)
