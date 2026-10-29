"""Exercises the editor page the way a person would (offscreen): completion, formatting, several cursors, find, project search,
jumping between source and PDF, tabs, files, drag and drop.  Usage: python tests/test_page.py"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
tmp = tempfile.mkdtemp()
os.environ["TEXORA_DATA"] = tmp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from texora.qt import QtWidgets, QtGui, Qt, prepare  # noqa: E402
try:
    from PySide2 import QtTest
except ImportError:
    from PySide6 import QtTest  # noqa: E402
from texora import theme as th, templates  # noqa: E402

prepare()
app = QtWidgets.QApplication([])
th.load_fonts()
from texora.engine import TexEngine  # noqa: E402
from texora.window import MainWindow  # noqa: E402

failures = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))
    if not cond:
        failures.append(name)


def pump(n=8):
    for _ in range(n):
        app.processEvents()


win = MainWindow(TexEngine("/nonexistent"))
if not os.environ.get("CI"):
    win.show()
tpl = next(x for x in templates.all_templates() if x["key"] == "tpl.physics")
p = win.store.create("Test paper", tpl)
win.open_project(p)
page = win.editor_page
ed = page.editor
pump()

# --- menus
titles = [a.text().replace("&", "") for a in win.menuBar().actions()]
check("menu bar has File/Edit/View/Build/Tools/Help", titles == ["File", "Edit", "View", "Build", "Tools", "Help"], titles)

# --- formatting
ed.setPlainText("hello world")
c = ed.textCursor(); c.select(QtGui.QTextCursor.Document); ed.setTextCursor(c)
page.a_bold.trigger()
check("Ctrl+B wraps in \\textbf", ed.toPlainText() == "\\textbf{hello world}", ed.toPlainText())
page.a_bold.trigger()
check("Ctrl+B again unwraps", ed.toPlainText() == "hello world", ed.toPlainText())
ed.setPlainText("x")
c = ed.textCursor(); c.select(QtGui.QTextCursor.Document); ed.setTextCursor(c)
page.a_math.trigger()
check("math wrap", ed.toPlainText() == "$x$", ed.toPlainText())

# --- completion
ed.setPlainText("")
ed.setFocus()
QtTest.QTest.keyClicks(ed, "\\fra")
pump()
check("completion popup for \\fra", ed.completer.popup().isVisible())
QtTest.QTest.keyClick(ed.completer.popup(), Qt.Key_Tab)
pump()
check("Tab completes the command", ed.toPlainText().startswith("\\frac"), ed.toPlainText())
ed.setPlainText("")
QtTest.QTest.keyClicks(ed, "\\begin{alig")
pump()
check("completion popup in \\begin{", ed.completer.popup().isVisible())
ed.completer.popup().hide()

# --- several cursors
ed.setPlainText("foo bar foo baz foo")
c = ed.textCursor(); c.setPosition(1); ed.setTextCursor(c)
ed.add_next_occurrence()      # selects the word
ed.add_next_occurrence()
ed.add_next_occurrence()
check("three cursors", len(ed.extra_cursors) == 2, len(ed.extra_cursors))
QtTest.QTest.keyClicks(ed, "X")
check("typing goes to all cursors", ed.toPlainText() == "X bar X baz X", ed.toPlainText())

# --- find
ed.extra_cursors = []
ed.setPlainText("alpha beta Alpha\nalpha2 ALPHA")
fb = page.findbar
fb.open()
fb.find.setText("alpha")
check("find (ignore case) counts 4", len(fb.spans()) == 4, fb.spans())
fb.case.setChecked(True)
check("find (match case) counts 2", len(fb.spans()) == 2, fb.spans())
fb.case.setChecked(False); fb.word.setChecked(True)
check("whole word counts 3", len(fb.spans()) == 3, fb.spans())
fb.word.setChecked(False); fb.regex.setChecked(True)
fb.find.setText(r"alpha\d")
check("regex", len(fb.spans()) == 1, fb.spans())
fb.find.setText("(")
check("invalid regex gives no matches", fb.spans() == [])
fb.find.setText(r"(a)l(p)")
fb.repl.setText(r"\2\1")
fb.replace_all()
check("regex replace with groups", ed.toPlainText().startswith("pla") or "pa" in ed.toPlainText(), ed.toPlainText())
fb.hide()

# --- project search
page.new_file() if False else None
os.makedirs(os.path.join(p.path, "sub"), exist_ok=True)
with open(os.path.join(p.path, "sub", "extra.tex"), "w") as f:
    f.write("one\nneedle here\nthree\n")
page.refresh_files()
fb.regex.setChecked(False)
fb.find.setText("needle")
fb.project.setChecked(True)
page.search_project(fb)
check("project search finds the file", page.search_list.topLevelItemCount() == 1)
page._search_activated(page.search_list.topLevelItem(0).child(0))
check("search result opens the file at the line", page.current == "sub/extra.tex" and ed.textCursor().blockNumber() == 1, (page.current, ed.textCursor().blockNumber()))
check("file tree shows folders", page.tree.topLevelItemCount() >= 2)

# --- tabs
check("two tabs open", len(page.open_names) == 2, page.open_names)
page._tab_close(page.open_names.index("sub/extra.tex"))
check("tab closes", page.open_names == [p and page.meta.main], page.open_names)

# --- structure
page.open_file(page.meta.main)
ed.setPlainText(tpl["files"][tpl["main"]])
page.update_structure()
check("structure lists sections", page.struct.topLevelItemCount() >= 1)

# --- PDF jumping
import fitz  # noqa: E402
pdf = os.path.join(tmp, "t.pdf")
d = fitz.open(); pg = d.new_page(); pg.insert_text((72, 100), "The state of a quantum system evolves according to"); pg.insert_text((72, 140), "Units and fields appear here"); d.save(pdf)
page.pdf_path = pdf
page.preview.load(pdf)
pump(20)
check("preview loaded", page.preview.doc is not None and page.pages.count() == 1)
page.open_file(page.meta.main)
text = ed.toPlainText()
line = [i for i, l in enumerate(text.split("\n")) if "quantum system" in l][0] + 1
page.to_pdf(line)
check("source -> PDF flashes a hit", len(page.preview.hits) == 1, page.preview.hits)
page.to_source(0, 100.0, 96.0)
check("PDF -> source goes to the line", ed.textCursor().blockNumber() + 1 == line, ed.textCursor().blockNumber() + 1)
page.preview.set_fit("page"); pump()
page.preview.set_columns(2); pump()
check("two columns", page.preview.columns == 2)
check("pdf search", page.preview.search("quantum") == 1)

# --- formula
from texora import textutil  # noqa: E402
ed.setPlainText("text $a^2 + b^2$ more")
c = ed.textCursor(); c.setPosition(8); ed.setTextCursor(c)
if os.environ.get("CI"):
    print("skip formula view: the CI session has no Windows text services (Chromium aborts there)")
else:
    page.dock_formula.show(); pump()
    page.update_formula()
    check("formula panel available", page.formula.available)

# --- drag and drop: files into the project, images into figures
src = os.path.join(tmp, "drop.tex")
with open(src, "w") as f:
    f.write("dropped\n")
page.import_paths([src])
check("dropped file imported and opened", page.current == "drop.tex", page.current)

# --- external folder in place
ext = os.path.join(tmp, "elsewhere")
os.makedirs(ext)
with open(os.path.join(ext, "paper.tex"), "w") as f:
    f.write("\\documentclass{article}\\begin{document}Hi\\end{document}\n")
win.open_folder(ext, "paper.tex")
check("external folder opens in place", win.editor_page.project.path == os.path.normpath(ext) and win.editor_page.meta.main == "paper.tex")
check("remembered as recent", win.prefs.get("recent")[0]["path"] == os.path.normpath(ext))
win.show_screen("projects")
check("external project listed", any(x.external for x in win.external_projects()))

print("RESULT", "ALL OK" if not failures else "FAILED: " + ", ".join(failures))
sys.stdout.flush()
os._exit(1 if failures else 0)
