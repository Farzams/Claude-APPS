package app.pdftoolkit.mobile

/** More starting points: by subject, and layouts for journals, a thesis and a poster. */
object TemplatesMore {
    val PHYSICS = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{physics}
\usepackage{siunitx}
\usepackage[hidelinks]{hyperref}

\title{Title of the report}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
A short summary of the work.
\end{abstract}

\section{Quantum mechanics}
The state of a quantum system evolves according to the Schr\"odinger equation
\begin{equation}\label{eq:schrodinger}
  i\hbar \pdv{t}\ket{\psi(t)} = \hat{H}\ket{\psi(t)} .
\end{equation}
The expectation value of an observable ${'$'}\hat{A}${'$'} in the state ${'$'}\psi${'$'} is ${'$'}\expval{\hat{A}}{\psi}${'$'}, and two observables commute when ${'$'}\comm{\hat{A}}{\hat{B}} = 0${'$'}.

\section{Units}
A body falling from rest accelerates at \SI{9.81}{\meter\per\second\squared}, so after \SI{2}{\second} its speed is \SI{19.6}{\meter\per\second}. The energy of a photon is about \SI{2.5}{\electronvolt}.

\section{Fields}
Faraday's law and the absence of magnetic monopoles read
\begin{align}
  \curl{\vb{E}} &= -\pdv{\vb{B}}{t}, \\
  \div{\vb{B}} &= 0 .
\end{align}

\end{document}
"""

    val CHEM = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage[version=4]{mhchem}
\usepackage{siunitx}
\usepackage{booktabs}
\usepackage[hidelinks]{hyperref}

\title{Title of the report}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section{Reactions}
Combustion of methane:
\begin{equation}\label{eq:combustion}
  \ce{CH4 + 2O2 -> CO2 + 2H2O}
\end{equation}
Ammonia is made in an equilibrium, \ce{N2 + 3H2 <=> 2NH3}, and dissolves into \ce{NH4+} and \ce{OH-} ions. A sulfate ion is written \ce{SO4^2-}.

\section{Results}
\begin{table}[ht]
  \centering
  \caption{Molar masses.}
  \begin{tabular}{lS[table-format=2.2]}
    \toprule
    Compound & {${'$'}M${'$'} / \si{\gram\per\mole}} \\
    \midrule
    \ce{H2O} & 18.02 \\
    \ce{CO2} & 44.01 \\
    \ce{CH4} & 16.04 \\
    \bottomrule
  \end{tabular}
\end{table}
A solution of \SI{0.10}{\mole\per\liter} \ce{HCl} has a pH of 1.

\end{document}
"""

    val CS = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{listings}
\usepackage[hidelinks]{hyperref}
\lstset{basicstyle=\ttfamily\small, frame=single, numbers=left, numberstyle=\tiny, breaklines=true}

\title{Title of the paper}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section{Algorithm}
\begin{algorithm}
  \caption{Binary search}\label{alg:bsearch}
  \begin{algorithmic}[1]
    \Require sorted array ${'$'}A[1..n]${'$'} and a key ${'$'}k${'$'}
    \Ensure index of ${'$'}k${'$'} in ${'$'}A${'$'}, or ${'$'}0${'$'}
    \State ${'$'}lo \gets 1${'$'}, ${'$'}hi \gets n${'$'}
    \While{${'$'}lo \le hi${'$'}}
      \State ${'$'}mid \gets \lfloor (lo+hi)/2 \rfloor${'$'}
      \If{${'$'}A[mid] = k${'$'}}
        \State \Return ${'$'}mid${'$'}
      \ElsIf{${'$'}A[mid] < k${'$'}}
        \State ${'$'}lo \gets mid + 1${'$'}
      \Else
        \State ${'$'}hi \gets mid - 1${'$'}
      \EndIf
    \EndWhile
    \State \Return ${'$'}0${'$'}
  \end{algorithmic}
\end{algorithm}
Algorithm~\ref{alg:bsearch} runs in ${'$'}\mathcal{O}(\log n)${'$'} time.

\section{Code}
\begin{lstlisting}[language=Python]
def bsearch(a, k):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == k:
            return mid
        lo, hi = (mid + 1, hi) if a[mid] < k else (lo, mid - 1)
    return -1
\end{lstlisting}

\end{document}
"""

    val ENG = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{siunitx}
\usepackage{booktabs}
\usepackage{circuitikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\usepackage[hidelinks]{hyperref}

\title{Title of the report}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section{Circuit}
\begin{figure}[ht]
  \centering
  \begin{circuitikz}
    \draw (0,0) to[battery1, l=${'$'}V_s${'$'}] (0,3) to[R, l=${'$'}R${'$'}] (3,3) to[C, l=${'$'}C${'$'}] (3,0) -- (0,0);
  \end{circuitikz}
  \caption{A series RC circuit.}
\end{figure}
With \SI{1}{\kilo\ohm} and \SI{1}{\micro\farad} the time constant is ${'$'}\tau = RC = \SI{1}{\milli\second}${'$'}.

\section{Step response}
\begin{figure}[ht]
  \centering
  \begin{tikzpicture}
    \begin{axis}[width=0.8\linewidth, height=6cm, grid=major, xlabel={${'$'}t/\tau${'$'}}, ylabel={${'$'}v_C/V_s${'$'}}]
      \addplot[thick, domain=0:5, samples=80] {1-exp(-x)};
    \end{axis}
  \end{tikzpicture}
  \caption{Capacitor voltage after the switch closes.}
\end{figure}

\section{Components}
\begin{table}[ht]
  \centering
  \caption{Values used.}
  \begin{tabular}{llr}
    \toprule
    Part & Symbol & Value \\
    \midrule
    Resistor & ${'$'}R${'$'} & \SI{1}{\kilo\ohm} \\
    Capacitor & ${'$'}C${'$'} & \SI{1}{\micro\farad} \\
    Supply & ${'$'}V_s${'$'} & \SI{5}{\volt} \\
    \bottomrule
  \end{tabular}
\end{table}

\end{document}
"""

    val BIO = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage[numbers]{natbib}
\usepackage[hidelinks]{hyperref}

\title{Title of the lab report}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
One paragraph: the question, the method, the main result.
\end{abstract}

\section{Introduction}
State the question and why it matters~\citep{knuth84}.

\section{Methods}
Describe the samples, the protocol and the measurements, so that someone else could repeat them.

\section{Results}
\begin{table}[ht]
  \centering
  \caption{Colony counts after 24 hours.}
  \begin{tabular}{lrr}
    \toprule
    Sample & Count & Mean size (mm) \\
    \midrule
    Control & 120 & 2.1 \\
    Treated & 64 & 1.4 \\
    \bottomrule
  \end{tabular}
\end{table}

\section{Discussion}
Interpret the results and name the limits of the experiment.

\bibliographystyle{plain}
\bibliography{refs}

\end{document}
"""

    val PLOTS = """\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\usepackage[hidelinks]{hyperref}

\title{Data and plots}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

Use the menu, \emph{Insert and check}, then \emph{Table or plot from CSV} to turn a spreadsheet into code like this.

\section{A line graph}
\begin{figure}[ht]
  \centering
  \begin{tikzpicture}
    \begin{axis}[width=0.9\linewidth, height=6.5cm, grid=major, xlabel={time (s)}, ylabel={signal}, legend pos=north west]
      \addplot[thick, mark=none] coordinates {(0,0) (1,1.2) (2,1.9) (3,2.4) (4,2.7) (5,2.9)};
      \addlegendentry{measured}
      \addplot[thick, dashed, domain=0:5, samples=60] {3*(1-exp(-0.8*x))};
      \addlegendentry{model}
    \end{axis}
  \end{tikzpicture}
  \caption{Measurement and fitted model.}
\end{figure}

\section{A scatter plot}
\begin{figure}[ht]
  \centering
  \begin{tikzpicture}
    \begin{axis}[width=0.9\linewidth, height=6.5cm, grid=major, xlabel={${'$'}x${'$'}}, ylabel={${'$'}y${'$'}}]
      \addplot[only marks, mark=*, mark size=1.8pt] coordinates {(1,2.1) (2,3.9) (3,6.2) (4,7.8) (5,10.1) (6,12.2)};
    \end{axis}
  \end{tikzpicture}
  \caption{Points that follow roughly ${'$'}y = 2x${'$'}.}
\end{figure}

\section{A table}
\begin{table}[ht]
  \centering
  \caption{The same data.}
  \begin{tabular}{rr}
    \toprule
    ${'$'}x${'$'} & ${'$'}y${'$'} \\
    \midrule
    1 & 2.1 \\
    2 & 3.9 \\
    3 & 6.2 \\
    \bottomrule
  \end{tabular}
\end{table}

\end{document}
"""

    val IEEE = """\documentclass[conference]{IEEEtran}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}

\begin{document}

\title{Paper Title}

\author{\IEEEauthorblockN{First Author}
\IEEEauthorblockA{Department, University\\
City, Country\\
first.author@example.com}
\and
\IEEEauthorblockN{Second Author}
\IEEEauthorblockA{Department, University\\
City, Country\\
second.author@example.com}}

\maketitle

\begin{abstract}
A short summary of the work in about two hundred words.
\end{abstract}

\begin{IEEEkeywords}
first keyword, second keyword, third keyword
\end{IEEEkeywords}

\section{Introduction}
Introduce the problem and cite earlier work~\cite{knuth84}. The layout, fonts and spacing follow the IEEE conference style.

\section{Method}
Describe the method. Equations are numbered automatically:
\begin{equation}
  E = mc^2 .
\end{equation}

\section{Conclusion}
Summarise the result~\cite{lamport94}.

\bibliographystyle{IEEEtran}
\bibliography{refs}

\end{document}
"""

    val ELSEVIER = """\documentclass[preprint,12pt]{elsarticle}
\usepackage{amsmath,amssymb}
\journal{Journal Name}

\begin{document}

\begin{frontmatter}

\title{Title of the paper}

\author{Author Name}
\address{Department, University, Country}

\begin{abstract}
A short summary of the work.
\end{abstract}

\begin{keyword}
first keyword \sep second keyword
\end{keyword}

\end{frontmatter}

\section{Introduction}
Introduce the problem and cite earlier work~\cite{knuth84}.

\section{Results}
Present the results~\cite{lamport94}.

\bibliographystyle{elsarticle-num}
\bibliography{refs}

\end{document}
"""

    val SPRINGER = """\documentclass[twocolumn]{svjour3}
\smartqed
\usepackage{graphicx}
\usepackage{amsmath}

\begin{document}

\title{Title of the paper}

\author{First Author \and Second Author}

\institute{F. Author \at Department, University, Country \\ \email{first.author@example.com} \and S. Author \at Department, University, Country}

\date{Received: date / Accepted: date}

\maketitle

\begin{abstract}
A short summary of the work.
\keywords{first keyword \and second keyword}
\end{abstract}

\section{Introduction}
\label{intro}
Introduce the problem and cite earlier work~\cite{knuth84}.

\section{Results}
\label{sec:1}
Present the results~\cite{lamport94}.

\begin{acknowledgements}
Thank the people and institutions that helped.
\end{acknowledgements}

\bibliographystyle{spmpsci}
\bibliography{refs}

\end{document}
"""

    val APA = """\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.54cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{amsmath}
\usepackage{setspace}
\usepackage[hidelinks]{hyperref}
\doublespacing
\setlength{\parindent}{0.5in}

\begin{document}

\begin{titlepage}
  \centering
  \vspace*{4cm}
  {\bfseries Title of the Paper\par}
  \vspace{1cm}
  Author Name\par
  Department, University\par
  Course Name\par
  Instructor Name\par
  \today
\end{titlepage}

\section*{\centering Abstract}
\noindent A single paragraph of 150 to 250 words that summarises the question, the method and the findings.

\newpage
\section*{\centering\bfseries Title of the Paper}
Start the introduction here. Cite in the text as (Knuth, 1984) or as Knuth (1984) says.

\subsection*{\bfseries Method}
Level 2 headings are bold and flush left.

\subsubsection*{\bfseries\itshape Participants}
Level 3 headings are bold italic and flush left.

\newpage
\section*{\centering\bfseries References}
\begin{list}{}{\setlength{\leftmargin}{0.5in}\setlength{\itemindent}{-0.5in}\setlength{\itemsep}{0pt}\setlength{\parsep}{0pt}}
\item Knuth, D. E. (1984). \textit{The \TeX book}. Addison-Wesley.
\item Lamport, L. (1994). \textit{\LaTeX: A document preparation system} (2nd ed.). Addison-Wesley.
\end{list}

\end{document}
"""

    val THESIS = """\documentclass[12pt,a4paper,oneside]{report}
\usepackage[margin=3cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{graphicx}
\usepackage{setspace}
\usepackage[hidelinks]{hyperref}
\onehalfspacing
\newtheorem{theorem}{Theorem}[chapter]

\begin{document}

\begin{titlepage}
  \centering
  \vspace*{3cm}
  {\Huge\bfseries Title of the Thesis\par}
  \vspace{2cm}
  {\Large Author Name\par}
  \vspace{1cm}
  A thesis submitted for the degree of\\ Doctor of Philosophy\par
  \vfill
  Department, University\par
  \today
\end{titlepage}

\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}
A summary of the thesis in one page.

\tableofcontents
\listoffigures

\chapter{Introduction}
Motivation, aims and an outline of the chapters~\cite{knuth84}.

\chapter{Background}
\section{Earlier work}
Review the literature~\cite{lamport94}.

\chapter{Results}
\begin{theorem}
Every statement of this kind is numbered inside its chapter.
\end{theorem}

\chapter{Conclusion}
Summarise the findings and suggest further work.

\appendix
\chapter{Additional material}
Long proofs, data tables and code go here.

\bibliographystyle{plain}
\bibliography{refs}

\end{document}
"""

    val POSTER = """\documentclass[a0,landscape]{a0poster}
\usepackage[T1]{fontenc}
\usepackage[paperwidth=118.9cm,paperheight=84.1cm,margin=3cm]{geometry}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{tcolorbox}
\pagestyle{empty}
\setlength{\columnsep}{3cm}

\begin{document}

\begin{center}
  {\VeryHuge\bfseries Title of the Poster\par}
  \vspace{1.5cm}
  {\huge Author One, Author Two\par}
  \vspace{0.5cm}
  {\LARGE Department, University\par}
\end{center}
\vspace{2cm}

\begin{multicols}{3}
\begin{tcolorbox}[title={\Large Introduction}, fonttitle=\bfseries]
\large State the question and why it matters. Keep sentences short and readable from two metres away.
\end{tcolorbox}

\begin{tcolorbox}[title={\Large Method}, fonttitle=\bfseries]
\large Describe what was done in a few steps.
\begin{equation*}
  \hat{\beta} = (X^\top X)^{-1} X^\top y
\end{equation*}
\end{tcolorbox}

\begin{tcolorbox}[title={\Large Results}, fonttitle=\bfseries]
\large Put the main figure here with \texttt{\textbackslash includegraphics}.
\end{tcolorbox}

\begin{tcolorbox}[title={\Large Conclusion}, fonttitle=\bfseries]
\large One or two sentences that someone should remember.
\end{tcolorbox}
\end{multicols}

\end{document}
"""

}
