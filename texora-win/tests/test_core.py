"""Tests of the logic that needs no screen. Run with: python tests/test_core.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from texora import check, csvtool, doi, store, textutil, strings, templates  # noqa: E402


def test_check():
    tex = {"main.tex": "\\documentclass{article}\n\\begin{document}\nSee \\ref{fig:missing} and \\cite{known,unknown}.\n"
                       "\\begin{figure}\n  \\label{fig:unused}\n\\end{figure}\n\\begin{itemize}\n\\item one\n% \\ref{commented}\n"
                       "\\input{chapter}\n\\end{document}\n"}
    bib = {"refs.bib": "@book{known, title={T}}\n@book{lonely, title={U}}\n"}
    kinds = [(i.kind, i.detail) for i in check.run(tex, bib, {"main.tex", "refs.bib"}, "main.tex")]
    assert ("check.undef.ref", "fig:missing") in kinds, kinds
    assert ("check.undef.cite", "unknown") in kinds
    assert ("check.unused.label", "fig:unused") in kinds
    assert ("check.unused.entry", "lonely") in kinds
    assert ("check.begin", "\\begin{itemize}") in kinds
    assert ("check.nofile", "chapter") in kinds
    assert not [k for k in kinds if k[1] == "commented"]
    clean = check.run({"main.tex": "\\begin{document}\n\\label{a} \\ref{a}\n\\end{document}\n"}, {}, {"main.tex"}, "main.tex")
    assert clean == [], clean
    wide = check.run({"main.tex": ""}, {}, {"main.tex"}, "main.tex", "Overfull \\hbox (23.5pt too wide) in paragraph at lines 12--14")
    assert wide[0].line == 12


def test_csv():
    d = csvtool.parse("x;y;label\n1;2,5;a_b\n2;3,5;c&d\n3;4;e\n")
    assert d.header == ["x", "y", "label"] and len(d.rows) == 3
    assert d.is_numeric(0) and d.is_numeric(1) and not d.is_numeric(2)
    t = csvtool.table(d, "Measured")
    assert "\\begin{tabular}{rrl}" in t and "a\\_b" in t and "c\\&d" in t and "\\toprule" in t, t
    p = csvtool.plot(d, 0, [1], "Curve", False)
    assert "(1,2.5)" in p and "\\begin{axis}" in p and "\\caption{Curve}" in p, p
    q = csvtool.parse('name,note\n"Smith, J.","said ""hi"""\n')
    assert q.rows[0] == ["Smith, J.", 'said "hi"']
    assert len(csvtool.parse("1,2\n3,4\n").rows) == 2


def test_doi():
    assert doi.clean(" https://doi.org/10.1038/nature14539 ") == "10.1038/nature14539"
    assert doi.clean("doi:10.1000/xyz123") == "10.1000/xyz123"
    assert doi.clean("hello") is None
    e = doi.tidy("@article{Smith_2020, title={A {Nice} Title}, volume={3}, author={Smith, John and Doe, Jane}, year={2020}, journal={Journal}}")
    assert e.startswith("@article{smith2020,") and "A {Nice} Title" in e, e


def test_textutil():
    assert textutil.count_words("\\begin{document}\nHello $x^2$ world % no\n\\end{document}") == 2
    items = textutil.outline("\\section{A}\n\\subsection{B}\n% \\section{no}\n")
    assert [(i.line, i.level, i.title) for i in items] == [(1, 0, "A"), (2, 1, "B")]
    assert textutil.smart_type("a ", 2, "{") == ("insert", "{}", 1)
    assert textutil.smart_type("{}", 1, "}") == ("skip",)
    assert textutil.smart_type("\\begin{itemize}", 15, "\n")[1].endswith("\\end{itemize}")
    errs = textutil.parse_errors("(./main.tex\n! Undefined control sequence.\nl.7 \\foo\n)")
    assert errs[0].line == 7 and errs[0].file == "main.tex", errs


def test_store_and_data():
    with tempfile.TemporaryDirectory() as tmp:
        s = store.ProjectStore(os.path.join(tmp, "p"))
        tpls = templates.all_templates()
        assert len(tpls) == 17
        p = s.create("Test", tpls[1])
        assert s.meta(p).main == "main.tex" and "refs.bib" in s.files(p, "main.tex")
        z = os.path.join(tmp, "a.zip")
        s.export_zip(p, z)
        q = s.import_zip("a.zip", z)
        assert q.name == "a" and s.meta(q).main == "main.tex"
        h = store.HistoryStore(os.path.join(tmp, "h"))
        h.snapshot("Test", "main.tex", "one")
        h.snapshot("Test", "main.tex", "one")
        h.snapshot("Test", "main.tex", "two")
        v = h.list("Test", "main.tex")
        assert len(v) == 2 and h.read(v[0]) == "two"
    strings.set_lang("fa")
    assert strings.t("compile") == "کامپایل"
    strings.set_lang("en")
    assert strings.t("compile") == "Compile"
    assert len(templates.symbol_groups()) == 12


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
