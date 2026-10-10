"""Spell-checking for English and Persian text inside LaTeX source (Hunspell dictionaries via `spylls`)."""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path

import core

WORD = re.compile(r"(?:[^\W\d_]|‌)+(?:['’\-](?:[^\W\d_]|‌)+)*")
ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
DIACRITICS = re.compile(r"[ً-ٰٟـ]")
TOKEN = re.compile(r"""
    (?P<comment>(?<!\\)%.*)                                 # % comment to end of line
  | (?P<dd>\$\$)                                            # display math toggle
  | (?P<dollar>(?<!\\)\$)                                   # inline math toggle
  | (?P<open>\\\[|\\\()                                     # \[  \(
  | (?P<close>\\\]|\\\))                                    # \]  \)
  | (?P<env>\\(?:begin|end)\s*\{(?P<envname>[^}]*)\})       # \begin{name}
  | (?P<cmd>\\[A-Za-z@]+\*?)                                # \command
  | (?P<esc>\\.)                                            # \% \& \{ ...
  | (?P<word>(?:[^\W\d_]|‌)+(?:['’\-](?:[^\W\d_]|‌)+)*)
""", re.X)

MATH_ENVS = {"equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*", "eqnarray",
             "eqnarray*", "displaymath", "math", "flalign", "flalign*", "split", "alignat", "alignat*", "array",
             "tikzpicture", "lstlisting", "verbatim", "minted", "tabular", "chemfig", "pgfplots", "axis",
             "thebibliography", "filecontents", "filecontents*", "comment"}
SKIP_ARG = {"label", "ref", "eqref", "pageref", "autoref", "cref", "Cref", "cite", "citep", "citet", "citealp", "nocite",
            "usepackage", "RequirePackage", "documentclass", "input", "include", "includegraphics", "bibliography",
            "bibliographystyle", "url", "href", "newcommand", "renewcommand", "providecommand", "DeclareMathOperator",
            "newtheorem", "theoremstyle", "setlength", "addtolength", "setcounter", "usetikzlibrary", "pgfplotsset",
            "hypersetup", "geometry", "setmainfont", "setsansfont", "setmonofont", "settextfont", "setmathfont",
            "newenvironment", "def", "let", "color", "textcolor", "definecolor", "bibitem", "mhchemoptions", "ce",
            "includepdf", "graphicspath", "lstset", "newlength", "pagestyle", "thispagestyle", "numberwithin",
            "newfontfamily", "setlatin", "setarab", "texttt", "verb", "lstinline", "mintinline", "vspace", "hspace",
            "tag", "intertext"}


def _dict_dir() -> Path:
    return core._app_dir() / "dicts"


def user_dict_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "PDFToolkit" / "userdict.txt"


def _normalise_line_endings(d: Path) -> None:
    """Hunspell files must use plain newlines; repair them in a cache copy if a checkout turned them into CRLF."""
    for f in list(d.rglob("*.aff")) + list(d.rglob("*.dic")):
        try:
            raw = f.read_bytes()
        except OSError:
            continue
        if b"\r\n" in raw:
            fixed = raw.replace(b"\r\n", b"\n")
            try:
                f.write_bytes(fixed)
            except OSError:
                pass


def scan(text: str, state: int = 0) -> tuple[list[tuple[int, int, str]], int]:
    """Words to check in one line of LaTeX. state: 0 normal, 1 inside a math/verbatim environment.

    Returns ([(start, length, word)], new_state)."""
    out: list[tuple[int, int, str]] = []
    pos = 0
    inline = False
    skip_group_until = -1
    while pos < len(text):
        m = TOKEN.search(text, pos)
        if not m:
            break
        pos = m.end()
        kind = m.lastgroup if m.lastgroup not in ("envname",) else "env"
        if m.group("comment"):
            break
        if m.group("dd"):
            state = 0 if state == 1 else 1
            continue
        if m.group("dollar"):
            if state == 0:
                inline = not inline
            continue
        if m.group("open"):
            state = 1
            continue
        if m.group("close"):
            state = 0
            continue
        if m.group("env") is not None:
            name = m.group("envname")
            if name in MATH_ENVS:
                state = 1 if text[m.start():].startswith("\\begin") else 0
            continue
        if m.group("cmd"):
            name = m.group("cmd")[1:].rstrip("*")
            if name in SKIP_ARG:
                # jump over [optional] and the {argument}
                j = pos
                while j < len(text) and text[j] in " \t":
                    j += 1
                if j < len(text) and text[j] == "[":
                    k = text.find("]", j)
                    j = k + 1 if k >= 0 else len(text)
                if j < len(text) and text[j] == "{":
                    depth, k = 0, j
                    while k < len(text):
                        if text[k] == "{":
                            depth += 1
                        elif text[k] == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    pos = k + 1
            continue
        if m.group("esc"):
            continue
        if m.group("word") and state == 0 and not inline:
            w = m.group("word")
            out.append((m.start("word"), len(w), w))
    return out, state


class SpellChecker:
    """Loads the two dictionaries in the background; `check` is cheap afterwards."""

    def __init__(self):
        self.en = self.fa = None
        self.ready = False
        self.error = ""
        self.loading = False
        self._cache: dict[str, bool] = {}
        self.user: set[str] = set()
        self.ignore: set[str] = set()
        self.math: set[str] = set()
        self._lock = threading.Lock()

    def load(self, on_done=None):
        """Load dictionaries (call from a thread)."""
        with self._lock:
            if self.ready:
                return
            self.loading = True
            try:
                from spylls.hunspell import Dictionary
                d = _dict_dir()
                _normalise_line_endings(d)
                self.en = Dictionary.from_files(str(d / "en" / "index"))
                self.fa = Dictionary.from_files(str(d / "fa" / "index"))
                try:
                    self.math = {w.strip().lower() for w in (d / "math_words.txt").read_text(encoding="utf-8").splitlines() if w.strip()}
                except OSError:
                    pass
                try:
                    self.user = {w.strip().lower() for w in user_dict_path().read_text(encoding="utf-8").splitlines() if w.strip()}
                except OSError:
                    pass
                self.ready = True
            except Exception:
                import traceback
                self.error = traceback.format_exc()
                self.ready = False
            finally:
                self.loading = False
        if on_done:
            on_done()

    @staticmethod
    def is_persian(word: str) -> bool:
        return bool(ARABIC.search(word))

    def check(self, word: str) -> bool:
        """True when the word is fine (or should not be checked)."""
        if not self.ready:
            return True
        key = word
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        ok = self._check(word)
        self._cache[key] = ok
        return ok

    def _check(self, word: str) -> bool:
        w = word.strip("'’-‌")
        low = w.lower()
        if len(w) <= 2 or low in self.user or low in self.ignore or low in self.math:
            return True
        if self.is_persian(w):
            w = DIACRITICS.sub("", w).replace("ي", "ی").replace("ك", "ک")
            if self.fa.lookup(w) or self.fa.lookup(w.replace("‌", "")):
                return True
            # a clitic-less split on half-space: check every part (e.g. "کتاب‌های")
            parts = [p for p in w.split("‌") if p]
            return len(parts) > 1 and all(self.fa.lookup(p) or len(p) <= 2 for p in parts)
        if w.isupper() and len(w) <= 8:          # acronyms: FFT, PDE
            return True
        if any(c.isdigit() for c in w):
            return True
        if self.en.lookup(w) or self.en.lookup(low) or self.en.lookup(w.capitalize()):
            return True
        # hyphenated compounds: every part must be a word
        parts = [p for p in re.split(r"[-’']", w) if p]
        return len(parts) > 1 and all(self.en.lookup(p) or self.en.lookup(p.lower()) or len(p) <= 2 for p in parts)

    def suggest(self, word: str, limit: int = 7) -> list[str]:
        if not self.ready:
            return []
        try:
            d = self.fa if self.is_persian(word) else self.en
            out = []
            for s in d.suggest(word.strip("'’-")):
                if s not in out:
                    out.append(s)
                if len(out) >= limit:
                    break
            return out
        except Exception:
            return []

    def add(self, word: str):
        w = word.strip().lower()
        self.user.add(w)
        self._cache.clear()
        try:
            p = user_dict_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(w + "\n")
        except OSError:
            pass

    def ignore_word(self, word: str):
        self.ignore.add(word.lower())
        self._cache.clear()


CHECKER = SpellChecker()
