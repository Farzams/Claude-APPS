package app.pdftoolkit.mobile

object Templates {
    val ARTICLE = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm}
\usepackage[hidelinks]{hyperref}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}

\title{Title of the paper}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
A short summary of the paper.
\end{abstract}

\section{Introduction}
Let ${'$'}X${'$'} be a Banach space and ${'$'}f\colon X\to\mathbb{R}${'$'} a continuous function. For ${'$'}x\in X${'$'} we write
\[
  \|x\| = \sup_{\|\varphi\|\le 1} |\varphi(x)| .
\]

\begin{theorem}\label{thm:main}
Every bounded linear operator ${'$'}T${'$'} on a Hilbert space ${'$'}H${'$'} satisfies ${'$'}\|T\| = \|T^*\|${'$'}.
\end{theorem}
\begin{proof}
Use the identity ${'$'}\langle Tx, y\rangle = \langle x, T^*y\rangle${'$'} and take suprema.
\end{proof}

\end{document}
"""

    val PERSIAN = """\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{xepersian}
\settextfont[Path=fonts/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold]{Vazirmatn}
\newtheorem{theorem}{قضیه}[section]

\title{عنوان مقاله}
\author{نام نویسنده}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
چکیدهٔ کوتاه مقاله در اینجا نوشته می‌شود.
\end{abstract}

\section{مقدمه}
فضاهای ${'$'}L^p${'$'} مجموعهٔ تابع‌هایی هستند که نرم زیر برایشان متناهی است:
\[
  \|f\|_{p}=\Bigl(\int_\Omega |f|^{p}\,d\mu\Bigr)^{1/p}.
\]

\begin{theorem}
هر عملگر خطی کراندار روی فضای هیلبرت هم‌نرم با الحاقی خود است.
\end{theorem}

\end{document}
"""

    val REPORT = """\documentclass[12pt,a4paper]{report}
\usepackage[margin=3cm]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}

\title{Thesis Title}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle
\tableofcontents

\chapter{Introduction}
Motivation and overview.

\chapter{Preliminaries}
\section{Notation}
We write ${'$'}\mathbb{N}=\{1,2,3,\dots\}${'$'}.

\begin{thebibliography}{9}
\bibitem{knuth} D.~E. Knuth, \emph{The \TeX book}, Addison-Wesley, 1984.
\end{thebibliography}

\end{document}
"""

    val BEAMER = """\documentclass{beamer}
\usetheme{Madrid}
\usepackage{amsmath,amssymb,mathtools}
\title{Presentation Title}
\author{Author Name}
\date{\today}

\begin{document}
\frame{\titlepage}

\begin{frame}{A theorem}
  For every ${'$'}\varepsilon>0${'$'} there is ${'$'}\delta>0${'$'} such that ${'$'}|x-y|<\delta \Rightarrow |f(x)-f(y)|<\varepsilon${'$'}.
  \[ \int_a^b f'(x)\,dx = f(b)-f(a) \]
\end{frame}

\end{document}
"""

    val BLANK = """\documentclass{article}
\usepackage{amsmath,amssymb}
\begin{document}
Hello, ${'$'}e^{i\pi}+1=0${'$'}.
\end{document}
"""

    val ALL = listOf("tpl.article" to ARTICLE, "tpl.persian" to PERSIAN, "tpl.report" to REPORT, "tpl.beamer" to BEAMER, "tpl.blank" to BLANK)
}

/** Symbol bar: label to snippet. `‸` marks where the cursor goes. */
val SNIPPETS = listOf(
    "\$ \$" to "\$‸\$", "\\[ \\]" to "\\[\n  ‸\n\\]", "\\frac" to "\\frac{‸}{}", "\\sqrt" to "\\sqrt{‸}", "x²" to "^{‸}", "xᵢ" to "_{‸}",
    "∫" to "\\int_{‸}^{}", "∑" to "\\sum_{‸}^{}", "lim" to "\\lim_{‸}", "{ }" to "{‸}", "( )" to "\\left(‸\\right)",
    "α" to "\\alpha ", "β" to "\\beta ", "γ" to "\\gamma ", "δ" to "\\delta ", "ε" to "\\varepsilon ", "θ" to "\\theta ", "λ" to "\\lambda ",
    "μ" to "\\mu ", "π" to "\\pi ", "σ" to "\\sigma ", "φ" to "\\varphi ", "ω" to "\\omega ", "Ω" to "\\Omega ", "∞" to "\\infty ",
    "≤" to "\\le ", "≥" to "\\ge ", "≠" to "\\ne ", "≈" to "\\approx ", "→" to "\\to ", "⇒" to "\\Rightarrow ", "∈" to "\\in ", "⊂" to "\\subset ",
    "∀" to "\\forall ", "∃" to "\\exists ", "ℝ" to "\\mathbb{R}", "ℕ" to "\\mathbb{N}", "‖‖" to "\\|‸\\|", "∂" to "\\partial ",
    "equation" to "\\begin{equation}\n  ‸\n\\end{equation}", "align" to "\\begin{align}\n  ‸\n\\end{align}",
    "itemize" to "\\begin{itemize}\n  \\item ‸\n\\end{itemize}", "theorem" to "\\begin{theorem}\n  ‸\n\\end{theorem}",
    "proof" to "\\begin{proof}\n  ‸\n\\end{proof}", "section" to "\\section{‸}", "\\cite" to "\\cite{‸}", "\\label" to "\\label{‸}",
)
