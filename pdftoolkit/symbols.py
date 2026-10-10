"""Symbol palette data: (glyph shown on the button, LaTeX to insert, search words, needs package).

A '▢' in the LaTeX marks where the cursor goes after inserting a template.
"""
from __future__ import annotations

G = "Greek letters"
OP = "Operators"
REL = "Relations"
ARR = "Arrows"
SETS = "Sets & logic"
AN = "Analysis"
ALG = "Algebra"
GEO = "Geometry"
TPL = "Templates"
FONTS = "Fonts & accents"
PHY = "Physics"
CHEM = "Chemistry"
UNITS = "Units"


def _greek():
    low = "α β γ δ ε ζ η θ ι κ λ μ ν ξ π ρ σ τ υ φ χ ψ ω".split()
    low_n = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon phi chi psi omega".split()
    var = [("ϵ", "varepsilon"), ("ϑ", "vartheta"), ("ϰ", "varkappa"), ("ϖ", "varpi"), ("ϱ", "varrho"),
           ("ς", "varsigma"), ("ϕ", "varphi")]
    up = [("Γ", "Gamma"), ("Δ", "Delta"), ("Θ", "Theta"), ("Λ", "Lambda"), ("Ξ", "Xi"), ("Π", "Pi"),
          ("Σ", "Sigma"), ("Υ", "Upsilon"), ("Φ", "Phi"), ("Ψ", "Psi"), ("Ω", "Omega")]
    out = [(g, "\\" + n, f"greek {n}", "") for g, n in zip(low, low_n)]
    out += [(g, "\\" + n, f"greek {n} variant", "") for g, n in var]
    out += [(g, "\\" + n, f"greek {n.lower()} capital", "") for g, n in up]
    return out


SYMBOLS: dict[str, list[tuple[str, str, str, str]]] = {
    G: _greek(),
    OP: [
        ("±", r"\pm", "plus minus", ""), ("∓", r"\mp", "minus plus", ""), ("×", r"\times", "times cross", ""),
        ("÷", r"\div", "divide", ""), ("·", r"\cdot", "dot product", ""), ("∗", r"\ast", "asterisk convolution", ""),
        ("⋆", r"\star", "star", ""), ("∘", r"\circ", "composition circle", ""), ("⊕", r"\oplus", "direct sum", ""),
        ("⊗", r"\otimes", "tensor product", ""), ("⊙", r"\odot", "hadamard", ""), ("∑", r"\sum_{▢}^{}", "sum series", ""),
        ("∏", r"\prod_{▢}^{}", "product", ""), ("∐", r"\coprod", "coproduct", ""), ("∫", r"\int_{▢}^{}", "integral", ""),
        ("∬", r"\iint", "double integral", ""), ("∭", r"\iiint", "triple integral", ""), ("∮", r"\oint", "contour integral", ""),
        ("⋃", r"\bigcup_{▢}", "big union", ""), ("⋂", r"\bigcap_{▢}", "big intersection", ""),
        ("⨁", r"\bigoplus", "big direct sum", ""), ("⨂", r"\bigotimes", "big tensor", ""),
        ("√", r"\sqrt{▢}", "square root", ""), ("∜", r"\sqrt[▢]{}", "nth root", ""),
        ("lim", r"\lim_{▢}", "limit", ""), ("sup", r"\sup_{▢}", "supremum", ""), ("inf", r"\inf_{▢}", "infimum", ""),
        ("max", r"\max", "maximum", ""), ("min", r"\min", "minimum", ""), ("limsup", r"\limsup", "limit superior", ""),
        ("liminf", r"\liminf", "limit inferior", ""), ("det", r"\det", "determinant", ""), ("ker", r"\ker", "kernel", ""),
        ("dim", r"\dim", "dimension", ""), ("tr", r"\operatorname{tr}", "trace", ""), ("Re", r"\operatorname{Re}", "real part", ""),
        ("Im", r"\operatorname{Im}", "imaginary part", ""), ("sin", r"\sin", "sine", ""), ("cos", r"\cos", "cosine", ""),
        ("tan", r"\tan", "tangent", ""), ("log", r"\log", "logarithm", ""), ("ln", r"\ln", "natural log", ""),
        ("exp", r"\exp", "exponential", ""), ("!", r"!", "factorial", ""), ("⌊x⌋", r"\lfloor ▢ \rfloor", "floor", ""),
        ("⌈x⌉", r"\lceil ▢ \rceil", "ceiling", ""),
    ],
    REL: [
        ("≤", r"\le", "less equal", ""), ("≥", r"\ge", "greater equal", ""), ("≠", r"\ne", "not equal", ""),
        ("≈", r"\approx", "approximately", ""), ("≃", r"\simeq", "similar equal", ""), ("≅", r"\cong", "congruent isomorphic", ""),
        ("≡", r"\equiv", "equivalent", ""), ("∼", r"\sim", "similar", ""), ("∝", r"\propto", "proportional", ""),
        ("≪", r"\ll", "much less", ""), ("≫", r"\gg", "much greater", ""), ("≺", r"\prec", "precedes", ""),
        ("≻", r"\succ", "succeeds", ""), ("⪯", r"\preceq", "precedes equal", ""), ("⪰", r"\succeq", "succeeds equal", ""),
        ("⊂", r"\subset", "subset", ""), ("⊆", r"\subseteq", "subset equal", ""), ("⊃", r"\supset", "superset", ""),
        ("⊇", r"\supseteq", "superset equal", ""), ("∈", r"\in", "element of", ""), ("∉", r"\notin", "not element", ""),
        ("∋", r"\ni", "contains", ""), ("∣", r"\mid", "divides", ""), ("∥", r"\parallel", "parallel", ""),
        ("⊥", r"\perp", "perpendicular orthogonal", ""), ("≜", r"\triangleq", "defined as", "amssymb"),
        ("≔", r"\coloneqq", "defined colon equals", "mathtools"), ("⊲", r"\lhd", "normal subgroup", ""),
        ("⊴", r"\trianglelefteq", "normal subgroup equal", "amssymb"),
    ],
    ARR: [
        ("→", r"\to", "right arrow tends", ""), ("←", r"\leftarrow", "left arrow", ""), ("↔", r"\leftrightarrow", "both arrows", ""),
        ("⇒", r"\Rightarrow", "implies", ""), ("⇐", r"\Leftarrow", "implied by", ""), ("⇔", r"\Leftrightarrow", "iff equivalent", ""),
        ("↦", r"\mapsto", "maps to", ""), ("↪", r"\hookrightarrow", "inclusion embedding", ""), ("↠", r"\twoheadrightarrow", "surjection", "amssymb"),
        ("⟶", r"\longrightarrow", "long arrow", ""), ("⟼", r"\longmapsto", "long maps to", ""), ("⟹", r"\Longrightarrow", "long implies", ""),
        ("⟺", r"\iff", "if and only if", ""), ("↑", r"\uparrow", "up", ""), ("↓", r"\downarrow", "down", ""),
        ("↗", r"\nearrow", "north east", ""), ("⇀", r"\rightharpoonup", "weak convergence", ""), ("⇌", r"\rightleftharpoons", "equilibrium", ""),
        ("→x", r"\xrightarrow{▢}", "arrow with label", "amsmath"), ("↝", r"\rightsquigarrow", "squiggle", "amssymb"),
    ],
    SETS: [
        ("∅", r"\emptyset", "empty set", ""), ("∪", r"\cup", "union", ""), ("∩", r"\cap", "intersection", ""),
        ("∖", r"\setminus", "set minus", ""), ("△", r"\triangle", "symmetric difference triangle", ""), ("∀", r"\forall", "for all", ""),
        ("∃", r"\exists", "exists", ""), ("∄", r"\nexists", "not exists", "amssymb"), ("¬", r"\neg", "not", ""),
        ("∧", r"\land", "and wedge", ""), ("∨", r"\lor", "or vee", ""), ("⊢", r"\vdash", "proves", ""),
        ("⊨", r"\models", "models", ""), ("∎", r"\blacksquare", "end of proof qed", "amssymb"), ("ℕ", r"\mathbb{N}", "natural numbers", "amssymb"),
        ("ℤ", r"\mathbb{Z}", "integers", "amssymb"), ("ℚ", r"\mathbb{Q}", "rationals", "amssymb"), ("ℝ", r"\mathbb{R}", "reals", "amssymb"),
        ("ℂ", r"\mathbb{C}", "complex numbers", "amssymb"), ("𝔽", r"\mathbb{F}", "field", "amssymb"), ("𝕋", r"\mathbb{T}", "circle group", "amssymb"),
        ("𝒫", r"\mathcal{P}", "power set", ""), ("|S|", r"\lvert ▢ \rvert", "cardinality", "amsmath"),
    ],
    AN: [
        ("∂", r"\partial", "partial derivative", ""), ("∇", r"\nabla", "nabla gradient", ""), ("∞", r"\infty", "infinity", ""),
        ("‖x‖", r"\left\lVert ▢ \right\rVert", "norm", "amsmath"), ("|x|", r"\left\lvert ▢ \right\rvert", "absolute value", "amsmath"),
        ("⟨x,y⟩", r"\langle ▢ , \rangle", "inner product", ""), ("f′", r"f'", "derivative prime", ""), ("dx", r"\,dx", "differential", ""),
        ("∫f dμ", r"\int_{\Omega} ▢ \,d\mu", "integral measure", ""), ("df/dx", r"\frac{d▢}{dx}", "derivative", ""),
        ("∂f/∂x", r"\frac{\partial ▢}{\partial x}", "partial derivative", ""), ("Lᵖ", r"L^{p}(▢)", "lp space", ""),
        ("ℓᵖ", r"\ell^{p}", "sequence space lp", ""), ("Lᶲ", r"L^{\Phi}(▢)", "orlicz space", ""), ("‖f‖₍Φ₎", r"\norm{▢}_{(\Phi)}", "luxemburg norm orlicz (needs \\norm macro)", "template"),
        ("Δ₂", r"\Delta_2", "delta two condition orlicz", ""), ("∇₂", r"\nabla_2", "nabla two condition", ""),
        ("ρ_Φ", r"\rho_{\Phi}(▢)", "modular", ""), ("C₀", r"C_0(▢)", "continuous vanishing at infinity", ""),
        ("𝒟", r"\mathcal{D}", "test functions", ""), ("𝒮", r"\mathcal{S}", "schwartz space", ""), ("ℱ", r"\mathcal{F}", "fourier transform", ""),
        ("f̂", r"\widehat{▢}", "fourier transform hat", ""), ("f*g", r"f \ast g", "convolution", ""), ("supp", r"\operatorname{supp}", "support", ""),
        ("ess sup", r"\operatorname{ess\,sup}", "essential supremum", ""), ("a.e.", r"\text{ a.e.}", "almost everywhere", ""),
        ("→ₒ", r"\xrightarrow{\;\mu\;}", "convergence in measure", "amsmath"), ("⇀", r"\rightharpoonup", "weak convergence", ""),
        ("B(X)", r"\mathcal{B}(▢)", "bounded operators", ""), ("σ(T)", r"\sigma(▢)", "spectrum", ""), ("T*", r"T^{*}", "adjoint", ""),
        ("𝔄", r"\mathfrak{A}", "algebra fraktur", "amssymb"), ("𝔤", r"\mathfrak{g}", "lie algebra", "amssymb"),
    ],
    ALG: [
        ("⊗", r"\otimes", "tensor", ""), ("∘", r"\circ", "composition", ""), ("⋊", r"\rtimes", "semidirect product", "amssymb"),
        ("≀", r"\wr", "wreath", ""), ("ker", r"\ker", "kernel", ""), ("im", r"\operatorname{im}", "image", ""),
        ("Hom", r"\operatorname{Hom}", "homomorphisms", ""), ("End", r"\operatorname{End}", "endomorphisms", ""),
        ("Aut", r"\operatorname{Aut}", "automorphisms", ""), ("GL", r"\operatorname{GL}", "general linear", ""),
        ("⟨g⟩", r"\langle ▢ \rangle", "generated by", ""), ("𝔪", r"\mathfrak{m}", "maximal ideal", "amssymb"),
        ("◁", r"\triangleleft", "normal subgroup", ""), ("∼", r"\sim", "equivalence", ""), ("A⁻¹", r"A^{-1}", "inverse", ""),
        ("Aᵀ", r"A^{\mathsf{T}}", "transpose", ""), ("(a b; c d)", r"\begin{pmatrix} ▢ & \\ & \end{pmatrix}", "matrix", "amsmath"),
        ("[a b; c d]", r"\begin{bmatrix} ▢ & \\ & \end{bmatrix}", "matrix brackets", "amsmath"),
        ("det", r"\begin{vmatrix} ▢ & \\ & \end{vmatrix}", "determinant matrix", "amsmath"),
        ("(n k)", r"\binom{▢}{}", "binomial", "amsmath"), ("mod", r"\pmod{▢}", "modulo", "amsmath"),
    ],
    GEO: [
        ("∠", r"\angle", "angle", ""), ("∡", r"\measuredangle", "measured angle", "amssymb"), ("△", r"\triangle", "triangle", ""),
        ("□", r"\square", "square", "amssymb"), ("◇", r"\diamond", "diamond", ""), ("°", r"^\circ", "degree", ""),
        ("∥", r"\parallel", "parallel", ""), ("⊥", r"\perp", "perpendicular", ""), ("≅", r"\cong", "congruent", ""),
        ("∼", r"\sim", "similar", ""), ("⌢", r"\frown", "arc", ""), ("→AB", r"\overrightarrow{▢}", "vector", ""),
        ("AB̅", r"\overline{▢}", "segment overline", ""), ("⋅⋅⋅", r"\cdots", "dots centered", ""), ("⋮", r"\vdots", "vertical dots", ""),
        ("⋱", r"\ddots", "diagonal dots", ""), ("…", r"\ldots", "dots", ""),
    ],
    TPL: [
        ("a/b", r"\frac{▢}{}", "fraction", ""), ("a^b", r"^{▢}", "superscript power", ""), ("a_b", r"_{▢}", "subscript index", ""),
        ("x̄", r"\overline{▢}", "overline bar closure", ""), ("x̲", r"\underline{▢}", "underline", ""), ("x̂", r"\hat{▢}", "hat", ""),
        ("x̃", r"\tilde{▢}", "tilde", ""), ("x⃗", r"\vec{▢}", "vector arrow", ""), ("ẋ", r"\dot{▢}", "dot derivative", ""),
        ("ẍ", r"\ddot{▢}", "double dot", ""), ("{ }", r"\left\{ ▢ \right\}", "braces", ""), ("( )", r"\left( ▢ \right)", "parentheses", ""),
        ("[ ]", r"\left[ ▢ \right]", "brackets", ""), ("cases", r"\begin{cases} ▢ & \text{if } \\ & \text{otherwise} \end{cases}", "piecewise cases", "amsmath"),
        ("align", r"\begin{align*} ▢ &= \\ &= \end{align*}", "aligned equations", "amsmath"),
        ("equation", r"\begin{equation} ▢ \end{equation}", "numbered equation", "amsmath"),
        ("thm", r"\begin{theorem} ▢ \end{theorem}", "theorem environment", "amsthm"),
        ("proof", r"\begin{proof} ▢ \end{proof}", "proof environment", "amsthm"),
        ("Σᵢ", r"\sum_{i=1}^{n} ▢", "sum from 1 to n", ""), ("∫ₐᵇ", r"\int_{a}^{b} ▢ \,dx", "definite integral", ""),
        ("lim→∞", r"\lim_{n\to\infty} ▢", "limit n to infinity", ""), ("sup over", r"\sup_{\|x\|\le 1} ▢", "supremum unit ball", ""),
        ("underbrace", r"\underbrace{▢}_{}", "underbrace", ""), ("overbrace", r"\overbrace{▢}^{}", "overbrace", ""),
        ("text", r"\text{▢}", "text in math", "amsmath"), ("boxed", r"\boxed{▢}", "boxed result", "amsmath"),
    ],
    FONTS: [
        ("𝔸", r"\mathbb{▢}", "blackboard bold", "amssymb"), ("𝒜", r"\mathcal{▢}", "calligraphic", ""), ("𝔄", r"\mathfrak{▢}", "fraktur", "amssymb"),
        ("𝓐", r"\mathscr{▢}", "script", "mathrsfs"), ("𝐀", r"\mathbf{▢}", "bold roman", ""), ("𝑨", r"\boldsymbol{▢}", "bold italic", "amsmath"),
        ("A", r"\mathrm{▢}", "roman upright", ""), ("A", r"\mathsf{▢}", "sans serif", ""), ("A", r"\mathtt{▢}", "typewriter", ""),
    ],
    PHY: [
        ("ħ", r"\hbar", "hbar planck", ""), ("ℓ", r"\ell", "ell", ""), ("℘", r"\wp", "weierstrass", ""), ("°C", r"\,^\circ\mathrm{C}", "celsius", ""),
        ("∇·E", r"\nabla\cdot\mathbf{E}", "divergence", ""), ("∇×B", r"\nabla\times\mathbf{B}", "curl", ""), ("∇²", r"\nabla^{2}", "laplacian", ""),
        ("□", r"\Box", "d'alembertian", "amssymb"), ("|ψ⟩", r"\ket{▢}", "ket", "physics"), ("⟨ψ|", r"\bra{▢}", "bra", "physics"),
        ("⟨ψ|φ⟩", r"\braket{▢}{}", "bra-ket", "physics"), ("∂f/∂t", r"\pdv{▢}{t}", "partial derivative (physics)", "physics"),
        ("df/dt", r"\dv{▢}{t}", "derivative (physics)", "physics"), ("Ĥ", r"\hat{H}", "hamiltonian", ""), ("vec", r"\vb{▢}", "bold vector", "physics"),
        ("≪", r"\ll", "much less", ""), ("∝", r"\propto", "proportional", ""), ("Å", r"\text{\AA}", "angstrom", ""),
        ("E=mc²", r"E=mc^{2}", "einstein", ""), ("𝔼", r"\mathbb{E}", "expectation", "amssymb"), ("Tr", r"\operatorname{Tr}", "trace", ""),
    ],
    CHEM: [
        ("H₂O", r"\ce{H2O}", "water formula", "mhchem"), ("→", r"\ce{A -> B}", "reaction arrow", "mhchem"), ("⇌", r"\ce{A <=> B}", "equilibrium", "mhchem"),
        ("Fe³⁺", r"\ce{Fe^{3+}}", "ion charge", "mhchem"), ("SO₄²⁻", r"\ce{SO4^{2-}}", "sulfate ion", "mhchem"), ("↓", r"\ce{AgCl v}", "precipitate", "mhchem"),
        ("↑", r"\ce{CO2 ^}", "gas evolves", "mhchem"), ("¹⁴C", r"\ce{^{14}C}", "isotope", "mhchem"), ("2H₂+O₂", r"\ce{2H2 + O2 -> 2H2O}", "reaction", "mhchem"),
        ("[A]", r"\ce{[▢]}", "concentration", "mhchem"), ("ΔH°", r"\Delta H^\circ", "enthalpy standard", ""), ("ΔG", r"\Delta G", "gibbs energy", ""),
        ("K_eq", r"K_{\mathrm{eq}}", "equilibrium constant", ""), ("pH", r"\mathrm{pH}", "pH", ""), ("pK_a", r"\mathrm{p}K_{\mathrm{a}}", "pka", ""),
        ("C₆H₆", r"\chemfig{*6(=-=-=-)}", "benzene ring (chemfig)", "chemfig"), ("H₃C–OH", r"\chemfig{H_3C-OH}", "methanol structure", "chemfig"),
        ("C=O", r"\chemfig{R-C(=[:60]O)-OH}", "carboxylic acid", "chemfig"), ("N_A", r"N_{\mathrm{A}}", "avogadro", ""), ("e⁻", r"\ce{e-}", "electron", "mhchem"),
        ("Nernst", r"E = E^\circ - \frac{RT}{nF}\ln Q", "nernst equation", ""),
    ],
    UNITS: [
        ("m/s", r"\SI{▢}{m/s}", "metres per second", "siunitx"), ("kg", r"\si{kg}", "kilogram", "siunitx"), ("N", r"\si{N}", "newton", "siunitx"),
        ("J", r"\si{J}", "joule", "siunitx"), ("W", r"\si{W}", "watt", "siunitx"), ("Pa", r"\si{Pa}", "pascal", "siunitx"),
        ("K", r"\si{K}", "kelvin", "siunitx"), ("mol/L", r"\si{mol.L^{-1}}", "molar", "siunitx"), ("Hz", r"\si{Hz}", "hertz", "siunitx"),
        ("eV", r"\si{eV}", "electron volt", "siunitx"), ("×10ⁿ", r"\num{▢e-3}", "scientific notation", "siunitx"),
        ("μm", r"\si{\micro\metre}", "micrometre", "siunitx"), ("Ω", r"\si{\ohm}", "ohm", "siunitx"), ("°C", r"\si{\celsius}", "celsius", "siunitx"),
    ],
}

CATEGORIES = list(SYMBOLS)


def search(query: str):
    q = query.lower().strip()
    if not q:
        return []
    out = []
    for cat, items in SYMBOLS.items():
        for g, tex, words, pkg in items:
            if q in words or q in tex.lower() or q == g:
                out.append((g, tex, words, pkg, cat))
    return out


def package_for(tex: str) -> str:
    """Packages a snippet needs (for the hint line)."""
    for items in SYMBOLS.values():
        for g, t, w, pkg in items:
            if t == tex:
                return pkg
    return ""
