"""Starter LaTeX documents. @FONTDIR@ is replaced with the folder holding the bundled Persian fonts."""
from __future__ import annotations

from pathlib import Path

THEOREMS = r"""\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{example}[theorem]{Example}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}
"""

ARTICLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm}
\usepackage[hidelinks]{hyperref}
""" + THEOREMS + r"""
\title{Title of the paper}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
A short summary of the paper.
\end{abstract}

\section{Introduction}
Let $X$ be a Banach space and $f\colon X\to\mathbb{R}$ a continuous function. For $x\in X$ we write
\[
  \|x\| = \sup_{\|\varphi\|\le 1} |\varphi(x)| .
\]

\begin{theorem}\label{thm:main}
Every bounded linear operator $T$ on a Hilbert space $H$ satisfies $\|T\| = \|T^*\|$.
\end{theorem}
\begin{proof}
Use the identity $\langle Tx, y\rangle = \langle x, T^*y\rangle$ and take suprema.
\end{proof}

\section{Results}
By Theorem~\ref{thm:main} we obtain
\begin{equation}\label{eq:one}
  \int_0^1 x^2\,dx = \frac{1}{3}.
\end{equation}

\end{document}
"""


REPORT = r"""\documentclass[12pt,a4paper]{report}
\usepackage[margin=3cm]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}
""" + THEOREMS + r"""
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
We write $\mathbb{N}=\{1,2,3,\dots\}$.

\chapter{Main results}
\begin{theorem}
Statement of the main theorem.
\end{theorem}

\begin{thebibliography}{9}
\bibitem{knuth} D.~E. Knuth, \emph{The \TeX book}, Addison-Wesley, 1984.
\end{thebibliography}

\end{document}
"""

BEAMER = r"""\documentclass{beamer}
\usetheme{Madrid}
\usepackage{amsmath,amssymb,mathtools}
\title{Presentation Title}
\author{Author Name}
\institute{University}
\date{\today}

\begin{document}
\frame{\titlepage}

\begin{frame}{Outline}
  \tableofcontents
\end{frame}

\section{Main idea}
\begin{frame}{A theorem}
  \begin{theorem}
    For every $\varepsilon>0$ there is $\delta>0$ such that $|x-y|<\delta \Rightarrow |f(x)-f(y)|<\varepsilon$.
  \end{theorem}
  \[ \int_a^b f'(x)\,dx = f(b)-f(a) \]
\end{frame}

\end{document}
"""

PERSIAN = r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{xepersian}
\settextfont[Path=fonts/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold]{NotoSansArabic}% fonts/ is created next to this file when you compile
\setlatintextfont{Latin Modern Roman}
\newtheorem{theorem}{قضیه}[section]
\theoremstyle{definition}
\newtheorem{definition}[theorem]{تعریف}

\title{عنوان مقاله}
\author{نام نویسنده}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
چکیدهٔ کوتاه مقاله در اینجا نوشته می‌شود.
\end{abstract}

\section{مقدمه}
فضاهای اورلیچ تعمیمی از فضاهای $L^p$ هستند. نرم لوکزامبورگ تابع $f$ برابر است با
\[
  \|f\|_{(\Phi)}=\inf\Bigl\{k>0:\int_\Omega \Phi\Bigl(\tfrac{|f|}{k}\Bigr)\,d\mu\le 1\Bigr\}.
\]

\begin{theorem}
هر عملگر خطی کراندار روی فضای هیلبرت هم‌نرم با الحاقی خود است.
\end{theorem}

\end{document}
"""

CHEMISTRY = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[version=4]{mhchem}
\usepackage{chemfig}
\usepackage{siunitx}
\usepackage{amsmath}

\title{Chemistry notes}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section*{Reactions}
Formulas and reactions with \texttt{mhchem}:
\begin{align*}
  &\ce{2H2 + O2 -> 2H2O} \\
  &\ce{CH3COOH + H2O <=> CH3COO- + H3O+} \\
  &\ce{Fe^{3+} + 3OH- -> Fe(OH)3 v}
\end{align*}
Concentration: $\ce{[H3O+]} = \SI{1.0e-7}{mol.L^{-1}}$, so $\mathrm{pH}=7$.

\section*{Structures}
Benzene: \chemfig{*6(=-=-=-)} \qquad Acetic acid: \chemfig{H_3C-C(=[:60]O)-OH}

\section*{Thermodynamics}
\[
  \Delta G = \Delta H - T\,\Delta S, \qquad
  E = E^\circ - \frac{RT}{nF}\ln Q .
\]

\end{document}
"""

PHYSICS = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{physics}
\usepackage{siunitx}
\usepackage{tikz}
\usepackage{pgfplots}\pgfplotsset{compat=1.16}

\title{Physics notes}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section*{Equations}
Maxwell's equations:
\begin{align}
  \div \vb{E} &= \frac{\rho}{\varepsilon_0}, & \curl \vb{E} &= -\pdv{\vb{B}}{t},\\
  \div \vb{B} &= 0, & \curl \vb{B} &= \mu_0\vb{J}+\mu_0\varepsilon_0\pdv{\vb{E}}{t}.
\end{align}
Schr\"odinger equation: $i\hbar\pdv{t}\ket{\psi} = \hat H\ket{\psi}$, \quad $\expval{\hat H}{\psi}=E$.

\section*{Units}
The speed of light is $c=\SI{2.998e8}{m.s^{-1}}$ and $g=\SI{9.81}{m/s^2}$.

\section*{A plot}
\begin{tikzpicture}
  \begin{axis}[xlabel=$t$ (\si{s}), ylabel=$x$ (\si{m}), width=8cm, height=5cm, grid=major]
    \addplot[domain=0:6.28, samples=100, thick] {sin(deg(x))};
  \end{axis}
\end{tikzpicture}

\end{document}
"""

BLANK = r"""\documentclass{article}
\usepackage{amsmath,amssymb}
\begin{document}
Hello, $e^{i\pi}+1=0$.
\end{document}
"""

TEMPLATES = {
    "Article (theorems, math)": ARTICLE,
    "Thesis / report": REPORT,
    "Slides (Beamer)": BEAMER,
    "Persian + English article (XeLaTeX)": PERSIAN,
    "Chemistry (mhchem, chemfig)": CHEMISTRY,
    "Physics (siunitx, physics, plots)": PHYSICS,
    "Blank": BLANK,
}


def get(name: str, fonts_dir: Path | str) -> str:
    return TEMPLATES[name].replace("@FONTDIR@", str(fonts_dir).replace("\\", "/"))
