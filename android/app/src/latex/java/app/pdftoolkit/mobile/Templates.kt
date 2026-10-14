package app.pdftoolkit.mobile

/** A starting point for a new project: its files, which one is compiled, and the engine. */
data class Template(val key: String, val files: Map<String, String>, val main: String = "main.tex", val engine: String = "xetex", val group: String = "general")

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

    val ARTICLE_BIB = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage[hidelinks]{hyperref}

\title{An article with references}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section{Introduction}
Typesetting is both an art and a science~\cite{knuth84}. A good introduction to the system is given in~\cite{lamport94}.

\bibliographystyle{plain}
\bibliography{refs}

\end{document}
"""

    val REFS = """@book{knuth84,
  author    = {Donald E. Knuth},
  title     = {The {\TeX}book},
  publisher = {Addison-Wesley},
  year      = {1984}
}

@book{lamport94,
  author    = {Leslie Lamport},
  title     = {{\LaTeX}: A Document Preparation System},
  publisher = {Addison-Wesley},
  edition   = {2},
  year      = {1994}
}
"""

    val LETTER = """\documentclass[11pt,a4paper]{letter}
\usepackage[margin=2.5cm]{geometry}
\signature{Your Name}
\address{Your Street \\ Your City}

\begin{document}
\begin{letter}{Recipient Name \\ Street \\ City}
\opening{Dear Sir or Madam,}

Write the body of the letter here.

\closing{Yours sincerely,}
\end{letter}
\end{document}
"""

    private fun sci(key: String, tex: String, bib: Boolean = false) =
        Template(key, mapOf("main.tex" to tex) + if (bib) mapOf("refs.bib" to REFS) else emptyMap(), engine = "pdftex", group = "science")

    private fun journal(key: String, tex: String) =
        Template(key, mapOf("main.tex" to tex, "refs.bib" to REFS), engine = "pdftex", group = "journal")

    val ALL = listOf(
        Template("tpl.article", mapOf("main.tex" to ARTICLE)),
        Template("tpl.bib", mapOf("main.tex" to ARTICLE_BIB, "refs.bib" to REFS)),
        Template("tpl.persian", mapOf("main.tex" to PERSIAN)),
        Template("tpl.report", mapOf("main.tex" to REPORT)),
        Template("tpl.beamer", mapOf("main.tex" to BEAMER)),
        Template("tpl.letter", mapOf("main.tex" to LETTER)),
        Template("tpl.blank", mapOf("main.tex" to BLANK)),
        sci("tpl.physics", TemplatesMore.PHYSICS),
        sci("tpl.chem", TemplatesMore.CHEM),
        sci("tpl.cs", TemplatesMore.CS),
        sci("tpl.eng", TemplatesMore.ENG),
        sci("tpl.bio", TemplatesMore.BIO, bib = true),
        sci("tpl.plots", TemplatesMore.PLOTS),
        journal("tpl.ieee", TemplatesMore.IEEE),
        journal("tpl.elsevier", TemplatesMore.ELSEVIER),
        journal("tpl.springer", TemplatesMore.SPRINGER),
        Template("tpl.apa", mapOf("main.tex" to TemplatesMore.APA), engine = "pdftex", group = "journal"),
        Template("tpl.thesis", mapOf("main.tex" to TemplatesMore.THESIS, "refs.bib" to REFS), engine = "pdftex", group = "journal"),
        Template("tpl.poster", mapOf("main.tex" to TemplatesMore.POSTER), engine = "pdftex", group = "journal"),
    )
}
