"""PDF Toolkit - read, OCR, extract, convert, split, merge, compress, images, page tools.

English and Persian interface, 9 colour themes, picture banners, colourful icons.
"""
from __future__ import annotations

import io
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import art
import core
import helpdata
import i18n
import settings
import symbols
import templates
import texengine
import theme
from i18n import t

try:  # drag & drop files onto the window (optional)
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:  # pragma: no cover
    HAS_DND = False

CFG = settings.load()
i18n.set_lang(CFG["lang"])
theme.set_theme(CFG["theme"])
RTL = i18n.rtl()
ctk.set_appearance_mode("dark")  # never switched again: every colour is set explicitly from the theme
ctk.set_default_color_theme("blue")

FA_FAMILY = "Noto Sans Arabic"
UI_FONT = "Segoe UI"
PDF = [("PDF", "*.pdf")]
LANG_NAMES = {"fas": "Persian (Farsi)", "eng": "English", "ara": "Arabic", "deu": "German",
              "fra": "French", "spa": "Spanish", "ita": "Italian", "rus": "Russian",
              "tur": "Turkish", "nld": "Dutch", "por": "Portuguese", "heb": "Hebrew",
              "ell": "Greek", "chi_sim": "Chinese (Simplified)", "jpn": "Japanese", "kor": "Korean"}
LANG_ORDER = ["fas", "eng", "ara"]
FA_LANG_NAMES = {"fas": "فارسی", "eng": "انگلیسی", "ara": "عربی", "deu": "آلمانی", "fra": "فرانسوی",
                 "spa": "اسپانیایی", "ita": "ایتالیایی", "rus": "روسی", "tur": "ترکی", "nld": "هلندی",
                 "por": "پرتغالی", "heb": "عبری", "ell": "یونانی", "chi_sim": "چینی", "jpn": "ژاپنی",
                 "kor": "کره‌ای"}


def setup_fonts():
    global UI_FONT
    if RTL:
        reg = i18n.register_font(art.FONT_DIR / "NotoSansArabic-Regular.ttf")
        i18n.register_font(art.FONT_DIR / "NotoSansArabic-Bold.ttf")
        UI_FONT = FA_FAMILY if reg else "Tahoma"
    else:
        UI_FONT = "Segoe UI"


def F(size=13, bold=False):
    return ctk.CTkFont(UI_FONT, size, "bold" if bold else "normal")


def _measure_font(size, bold=False):
    return tkfont.Font(family=UI_FONT, size=-size, weight="bold" if bold else "normal")


def D(text, size=13, wrap=0, bold=False):
    """Display string for a Tk widget (translated, wrapped for RTL, shaped)."""
    if not RTL:
        return t(text)
    if wrap:
        f = _measure_font(size, bold)
        return i18n.display(text, f.measure, wrap)
    return i18n.display(text)


def lang_choices() -> dict[str, str]:
    codes = core.ocr_languages()
    codes.sort(key=lambda c: (LANG_ORDER.index(c) if c in LANG_ORDER else 99, LANG_NAMES.get(c, c)))
    names = FA_LANG_NAMES if RTL else LANG_NAMES
    return {D(f"{names.get(c, c)}  ({c})"): c for c in codes}


def tess_lang(code: str, also_english: bool) -> str:
    if also_english and code != "eng" and "eng" in core.ocr_languages():
        return f"{code}+eng"
    return code


def tf(template: str, **kw) -> str:
    return t(template).format(**kw)


def tsf(template: str, **kw) -> str:
    """Translated + formatted + shaped, ready for a Tk widget."""
    s = t(template).format(**kw)
    return i18n.shape(s) if RTL else s


def missing_tools() -> str:
    names = [n for n, ok in [("DjVu", core.find_ddjvu()), ("DOCX / ODT / RTF", core.find_pandoc()),
                             ("OCR", core.find_tesseract()), ("Ghostscript", core.find_gs()),
                             ("LaTeX", texengine.find_engine())] if not ok]
    return ", ".join(names)


# ------------------------------------------------------------------ styled widget factories
def frame(parent, role="card", radius=16, **kw):
    f = ctk.CTkFrame(parent, corner_radius=radius, **kw)
    return theme.style(f, fg_color=role)


def label(parent, text="", size=13, bold=False, role="text", wrap=0, anchor=None, **kw):
    anchor = anchor or ("e" if RTL else "w")
    if wrap and not RTL:
        kw["wraplength"] = wrap
    lb = ctk.CTkLabel(parent, text=D(text, size, wrap, bold), font=F(size, bold), anchor=anchor,
                      justify="right" if RTL else "left", **kw)
    theme.style(lb, text_color=role, fg_color="transparent")
    return lb


def button(parent, text, command, kind="primary", width=0, height=34, size=13, bold=False, **kw):
    b = ctk.CTkButton(parent, text=D(text, size), command=command, height=height, corner_radius=10,
                      font=F(size, bold), **({"width": width} if width else {}), **kw)
    if kind == "primary":
        theme.style(b, fg_color="accent", hover_color="accent_hover", text_color="on_accent")
    else:
        theme.style(b, fg_color="field", hover_color="hover", text_color="text")
    return b


def entry(parent, var=None, hint="", width=0, **kw):
    e = ctk.CTkEntry(parent, textvariable=var, placeholder_text=hint, height=34, corner_radius=10,
                     border_width=0, font=F(13), justify="right" if RTL else "left",
                     **({"width": width} if width else {}), **kw)
    return theme.style(e, fg_color="field", text_color="text", placeholder_text_color="muted")


def option(parent, var, values, **kw):
    o = ctk.CTkOptionMenu(parent, variable=var, values=values, height=34, corner_radius=10,
                          font=F(13), dropdown_font=F(13), anchor="e" if RTL else "w", **kw)
    return theme.style(o, fg_color="field", button_color="accent", button_hover_color="accent_hover",
                       text_color="text", dropdown_fg_color="card", dropdown_hover_color="hover",
                       dropdown_text_color="text")


def check(parent, text, var):
    c = ctk.CTkCheckBox(parent, text=D(text), variable=var, corner_radius=6, font=F(13))
    return theme.style(c, fg_color="accent", hover_color="accent_hover", border_color="muted",
                       text_color="text", checkmark_color="on_accent")


def ctk_image(pil, size):
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)


# ------------------------------------------------------------------ widgets
class FileRow(ctk.CTkFrame):
    """Label + entry + browse button (file or folder)."""

    def __init__(self, master, text, kind="open", types=None, on_pick=None, save_ext=".pdf"):
        super().__init__(master, fg_color="transparent")
        theme.style(self, fg_color="card")
        self.kind, self.types, self.on_pick, self.save_ext = kind, types, on_pick, save_ext
        self.var = tk.StringVar()
        self.columnconfigure(1, weight=1)
        lab, ent, btn = (2, 1, 0) if RTL else (0, 1, 2)
        label(self, text, width=120).grid(row=0, column=lab)
        entry(self, self.var).grid(row=0, column=ent, sticky="ew", padx=8)
        button(self, "Browse…", self._browse, width=90).grid(row=0, column=btn)

    def _browse(self):
        if self.kind == "open":
            p = filedialog.askopenfilename(filetypes=self.types or [("All files", "*.*")])
        elif self.kind == "save":
            p = filedialog.asksaveasfilename(defaultextension=self.save_ext, filetypes=self.types)
        else:
            p = filedialog.askdirectory()
        if p:
            self.set(p)

    def set(self, p):
        self.var.set(p)
        if self.on_pick:
            self.on_pick(p)

    def get(self):
        return self.var.get().strip()


class FileList(ctk.CTkFrame):
    """Reorderable multi-file list."""

    def __init__(self, master, types, height=8):
        super().__init__(master, fg_color="transparent")
        theme.style(self, fg_color="card")
        self.types = types
        self.files: list[str] = []
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.lb = tk.Listbox(self, height=height, selectmode="extended", borderwidth=0,
                             highlightthickness=0, activestyle="none", font=(UI_FONT, 10))
        theme.style(self.lb, bg="field", fg="text", selectbackground="accent", selectforeground="on_accent")
        self.lb.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(self, command=self.lb.yview)
        theme.style(sb, button_color="hover", button_hover_color="accent")
        sb.grid(row=0, column=1, sticky="ns")
        self.lb.configure(yscrollcommand=sb.set)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        theme.style(bar, fg_color="card")
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        side = "right" if RTL else "left"
        for text, cmd, kind in [("＋ Add files", self.add_dialog, "primary"), ("▲ Up", lambda: self.move(-1), "field"),
                                ("▼ Down", lambda: self.move(1), "field"), ("Remove", self.remove, "field"),
                                ("Clear", self.clear, "field")]:
            button(bar, text, cmd, kind, width=84, height=30).pack(side=side, padx=(0, 6) if not RTL else (6, 0))
        self.count = label(bar, "")
        self.count.configure(text=tsf("{n} file(s)", n=0))
        self.count.pack(side="left" if RTL else "right")

    def add_dialog(self):
        self.add_paths(filedialog.askopenfilenames(filetypes=self.types))

    def add_paths(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh()

    def _refresh(self, select=()):
        self.lb.delete(0, "end")
        for i, f in enumerate(self.files, 1):
            self.lb.insert("end", f"{i:>3}.  {Path(f).name}    —  {Path(f).parent}")
        for i in select:
            self.lb.selection_set(i)
        self.count.configure(text=tsf("{n} file(s)", n=len(self.files)))

    def remove(self):
        for i in reversed(self.lb.curselection()):
            del self.files[i]
        self._refresh()

    def clear(self):
        self.files.clear()
        self._refresh()

    def move(self, d):
        sel = list(self.lb.curselection())
        if not sel:
            return
        n = len(self.files)
        if (d < 0 and sel[0] == 0) or (d > 0 and sel[-1] == n - 1):
            return
        for i in (sel if d < 0 else sel[::-1]):
            self.files[i], self.files[i + d] = self.files[i + d], self.files[i]
        self._refresh([i + d for i in sel])


class Tool(ctk.CTkFrame):
    """Page: picture banner on top, content card below."""

    key = ""
    icon = "read"
    title = ""
    subtitle = ""

    def __init__(self, app):
        super().__init__(app.main, fg_color="transparent")
        theme.style(self, fg_color="bg")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.banner_lbl = ctk.CTkLabel(self, text="", height=110, anchor="center")
        theme.style(self.banner_lbl, fg_color="bg")
        self.banner_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._banner_key = None
        self.body = frame(self, "card")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.build()
        if app.dnd:
            self._enable_drop()

    def build(self): ...

    def on_show(self):
        self.refresh_banner()

    def refresh_banner(self, force=False):
        w = max(self.app.main.winfo_width() - 4, 700)
        key = (theme.STATE.name, CFG["wallpaper"], CFG["custom_picture"], CFG["lang"], w // 20)
        if key == self._banner_key and not force:
            return
        self._banner_key = key
        img = art.banner(t(self.title), t(self.subtitle), self.icon, (w, 110), theme.STATE.pal,
                         CFG["wallpaper"], CFG["custom_picture"], RTL)
        self._banner_img = ctk_image(img, (w, 110))
        self.banner_lbl.configure(image=self._banner_img)

    # ---- drag & drop: the first file list / file row on the page receives the files
    def _enable_drop(self):
        try:
            for w in (self, self.body):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", lambda e: self.drop(list(self.tk.splitlist(e.data))))
        except Exception:
            pass

    def drop(self, paths):
        for w in self.body.winfo_children():
            if isinstance(w, FileList):
                w.add_paths(paths)
                return
            if isinstance(w, FileRow) and w.kind == "open":
                w.set(paths[0])
                return

    # ---- layout helpers
    def add(self, widget, pady=6):
        row = self.body.grid_size()[1]
        if isinstance(pady, tuple):
            pad = (pady[0] + (16 if row == 0 else 0), pady[1])
        else:
            pad = (pady + 16 if row == 0 else pady, pady)
        widget.grid(row=row, column=0, sticky="ew", padx=22, pady=pad)
        return widget

    def button(self, text, cmd):
        b = button(self.body, text, cmd, "primary", height=44, size=15, bold=True)
        b.configure(corner_radius=12)
        self.add(b, pady=(18, 20))
        return b

    def _row(self, text):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        theme.style(f, fg_color="card")
        f.columnconfigure(1, weight=1)
        label(f, text, width=120).grid(row=0, column=2 if RTL else 0)
        return f

    def entry_row(self, text, default="", hint=""):
        f = self._row(text)
        var = tk.StringVar(value=default)
        entry(f, var, t(hint) if not RTL else "").grid(row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def option_row(self, text, values, default=None):
        f = self._row(text)
        var = tk.StringVar(value=default or values[0])
        option(f, var, values).grid(row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def check_row(self, text, default=True):
        var = tk.BooleanVar(value=default)
        c = check(self.body, text, var)
        self.add(c, pady=4)
        if RTL:
            c.grid_configure(sticky="e")
        return var

    def note(self, text):
        self.add(label(self.body, text, 12, role="muted", wrap=700))

    def need(self, *vals):
        if not all(vals):
            messagebox.showwarning(D("Missing information"), D("Please fill in all the fields above."))
            return False
        return True


# ------------------------------------------------------------------ tools
class ReadTool(Tool):
    key, icon, title = "read", "read", "Read"
    subtitle = "View any PDF. Persian (Farsi), Arabic and English text can be searched and copied."

    def build(self):
        self.reader: core.PdfReader | None = None
        self.page, self.zoom, self.fit = 0, 1.2, True
        self.hits: list[int] = []
        self._img = None
        self._resize_job = None
        self._last_q = None
        b = self.body
        b.rowconfigure(2, weight=1)
        side = "right" if RTL else "left"
        opp = "left" if RTL else "right"
        top = frame(b, "card")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        button(top, "Open PDF…", self.open_dialog, width=100, height=32).pack(side=side)
        self.name = label(top, "No file open — or drop a PDF here", role="muted")
        self.name.pack(side=side, padx=12)
        bar = frame(b, "card")
        bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(2, 8))
        small = dict(width=34, height=30)
        button(bar, "▶" if RTL else "◀", lambda: self.go(self.page - 1), "field", **small).pack(side=side)
        self.pg_var = tk.StringVar(value="1")
        e = entry(bar, self.pg_var, width=52)
        e.configure(height=30, justify="center")
        e.pack(side=side, padx=4)
        e.bind("<Return>", lambda _e: self._goto_entry())
        self.total = label(bar, "/ 0", width=44, anchor="center")
        self.total.pack(side=side)
        button(bar, "◀" if RTL else "▶", lambda: self.go(self.page + 1), "field", **small).pack(side=side)
        button(bar, "−", lambda: self.set_zoom(self.zoom / 1.2), "field", **small).pack(side=side, padx=(14, 0))
        button(bar, "+", lambda: self.set_zoom(self.zoom * 1.2), "field", **small).pack(side=side, padx=4)
        button(bar, "Fit", self.fit_width, "field", **small).pack(side=side)
        self.q = tk.StringVar()
        s = entry(bar, self.q, "Search" if not RTL else "", width=170)
        s.configure(height=30)
        s.pack(side=side, padx=(14, 4))
        s.bind("<Return>", lambda _e: self.find(1))
        self.q.trace_add("write", lambda *_: self._preview())
        button(bar, "Find", lambda: self.find(1), "field", **small).pack(side=side)
        self.hit_lbl = label(bar, "", role="muted")
        self.hit_lbl.pack(side=side, padx=6)
        button(bar, "Copy text", self.copy_text, "field", width=84, height=30).pack(side=opp)
        holder = frame(b, "field", 10)
        holder.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self.cv = tk.Canvas(holder, highlightthickness=0, bd=0)
        theme.style(self.cv, bg="field")
        self.cv.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        vs = ctk.CTkScrollbar(holder, command=self.cv.yview)
        theme.style(vs, button_color="hover", button_hover_color="accent")
        vs.grid(row=0, column=1, sticky="ns")
        hs = ctk.CTkScrollbar(holder, orientation="horizontal", command=self.cv.xview)
        theme.style(hs, button_color="hover", button_hover_color="accent")
        hs.grid(row=1, column=0, sticky="ew")
        self.cv.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.cv.bind("<MouseWheel>", self._wheel)
        self.cv.bind("<Button-4>", lambda e: self.cv.yview_scroll(-3, "units"))
        self.cv.bind("<Button-5>", lambda e: self.cv.yview_scroll(3, "units"))
        self.cv.bind("<Control-MouseWheel>",
                     lambda e: self.set_zoom(self.zoom * (1.1 if e.delta > 0 else 1 / 1.1)))
        self.cv.bind("<Left>", lambda e: self.go(self.page - 1))
        self.cv.bind("<Right>", lambda e: self.go(self.page + 1))
        self.cv.bind("<Button-1>", lambda e: self.cv.focus_set())
        self.cv.bind("<Configure>", lambda e: self._on_resize())

    def _preview(self):
        """Tk edit boxes cannot shape Persian, so show the search text correctly shaped next to them."""
        self._status("")

    def _status(self, text):
        """Result text, prefixed with the correctly shaped query when it is Persian/Arabic."""
        q = self.q.get().strip()
        shaped = i18n.shape(q) if core.ARABIC_RE.search(q) else ""
        self.hit_lbl.configure(text=(shaped + "    " if shaped else "") + text)

    def drop(self, paths):
        self.open_pdf(paths[0])

    def open_dialog(self):
        p = filedialog.askopenfilename(filetypes=PDF)
        if p:
            self.open_pdf(p)

    def open_pdf(self, path):
        try:
            r = core.PdfReader(path)
        except Exception as e:
            return messagebox.showerror(D("Cannot open"), str(e))
        if self.reader:
            self.reader.close()
        self.reader, self.page, self.hits, self._last_q = r, 0, [], None
        self.name.configure(text=Path(path).name)
        self.total.configure(text=f"/ {r.page_count}")
        self.fit_width()

    def _goto_entry(self):
        try:
            self.go(int(self.pg_var.get()) - 1)
        except ValueError:
            pass

    def fit_width(self):
        if not self.reader:
            return
        w = max(self.cv.winfo_width() - 24, 200)
        self.zoom = max(0.2, min(w / self.reader.page_size(self.page)[0], 4))
        self.fit = True
        self.show_page()

    def set_zoom(self, z):
        self.zoom, self.fit = max(0.2, min(z, 5)), False
        self.show_page()

    def _on_resize(self):
        if self.fit and self.reader and not self.app.resizing:
            if self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(200, self.fit_width)

    def go(self, i):
        if self.reader and 0 <= i < self.reader.page_count:
            self.page = i
            self.show_page()
            self.cv.yview_moveto(0)

    def show_page(self):
        if not self.reader:
            return
        png, n = self.reader.render(self.page, self.zoom, self.q.get())
        self._img = tk.PhotoImage(data=png)
        self.cv.delete("all")
        cw = max(self.cv.winfo_width(), 1)
        x = max((cw - self._img.width()) // 2, 0)
        self.cv.create_image(x, 0, anchor="nw", image=self._img)
        self.cv.configure(scrollregion=(0, 0, max(self._img.width(), cw), self._img.height()))
        self.pg_var.set(str(self.page + 1))
        if self.q.get().strip():
            self._status(tsf("{n} match(es) here", n=n) if n else D("none on this page"))

    def find(self, step):
        if not self.reader or not self.q.get().strip():
            return
        if not self.hits or self._last_q != self.q.get():
            self._last_q = self.q.get()
            self.hits = self.reader.search(self.q.get())
        if not self.hits:
            self._status(D("not found"))
            return
        later = [p for p in self.hits if p > self.page]
        target = later[0] if later else self.hits[0]
        self.go(target)
        self._status(f"{target + 1}  ({self.hits.index(target) + 1}/{len(self.hits)})")

    def copy_text(self):
        if not self.reader:
            return
        self.clipboard_clear()
        self.clipboard_append(self.reader.text(self.page))
        self.app.toast("Page text copied")

    def _wheel(self, e):
        self.cv.yview_scroll(int(-e.delta / 120) * 3, "units")


class SplitTool(Tool):
    key, icon, title = "split", "split", "Split"
    subtitle = "Cut a PDF into several smaller files."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.info = self.add(label(self.body, ""))
        self.modes = {D("Custom ranges (one file per range)"): "ranges", D("Every N pages"): "every",
                      D("Into N equal parts"): "parts", D("Every page separately"): "single"}
        self.mode = self.option_row("Split by", list(self.modes))
        self.val = self.entry_row("Value", "1-5, 6-10", "e.g. 1-3, 5, 8-   or   10")
        self.note("Ranges: '1-3, 5, 8-' makes three files (pages 1-3, page 5, page 8 to the end). "
                  "For 'Every N pages' / 'Into N equal parts' type just the number.")
        self.button("Split", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).parent))
        try:
            self.info.configure(text=tsf("{n} pages", n=core.page_count(p))
                                + f" · {core.fmt_size(Path(p).stat().st_size)}")
        except Exception as e:
            self.info.configure(text=str(e))

    def run(self):
        src, out, mode, val = self.src.get(), self.out.get(), self.modes[self.mode.get()], self.val.get().strip()
        if not self.need(src, out):
            return

        def job(log, prog):
            n = core.page_count(src)
            if mode == "ranges":
                groups = core.parse_ranges(val, n)
            elif mode == "every":
                groups = core.groups_every_n(n, int(val))
            elif mode == "parts":
                groups = core.groups_into_parts(n, int(val))
            else:
                groups = core.groups_every_n(n, 1)
            files = core.split_pdf(src, out, groups, prog)
            log(tf("✔ Created {n} file(s)", n=len(files)))
            return out
        self.app.run(job)


class MergeTool(Tool):
    key, icon, title = "merge", "merge", "Merge"
    subtitle = "Combine several PDF files into one, in the order shown."

    def build(self):
        self.files = self.add(FileList(self.body, PDF, height=9))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.button("Merge", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if len(files) < 2 or not out:
            return messagebox.showwarning(D("Missing information"), D("Add at least two PDFs and choose where to save."))

        def job(log, prog):
            n = core.merge_pdfs(files, out, prog)
            log(tf("✔ Merged {n} files → {name} ({pages} pages)", n=len(files), name=Path(out).name, pages=n))
            return str(Path(out).parent)
        self.app.run(job)


class CompressTool(Tool):
    key, icon, title = "compress", "compress", "Compress"
    subtitle = "Make PDFs smaller by reducing image size and cleaning up the file."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.levels = {D(k): k for k in core.COMPRESS_LEVELS}
        self.level = self.option_row("Level", list(self.levels), list(self.levels)[1])
        gs = core.find_gs()
        self.engines = {D("Ghostscript (stronger)"): "ghostscript", D("Built-in"): "builtin"}
        engines = [e for e in self.engines if gs or self.engines[e] == "builtin"]
        self.engine = self.option_row("Engine", engines)
        self.note("Ghostscript is built in — it gives the strongest compression for scanned books."
                  if gs else "Ghostscript is not available in this build; using the built-in engine.")
        self.note("Saved as <name>_compressed.pdf. If a file can't be made smaller, the original is kept.")
        self.button("Compress", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).parent))

    def run(self):
        src, out, level = self.src.get(), self.out.get(), self.levels[self.level.get()]
        engine = self.engines[self.engine.get()]
        if not self.need(src, out):
            return

        def job(log, prog):
            prog(0, 1)
            dst = core.unique_path(Path(out) / (Path(src).stem + "_compressed.pdf"))
            a, b = core.compress_pdf(src, str(dst), level, engine)
            prog(1, 1)
            log(f"✔ {dst.name}: {core.fmt_size(a)} → {core.fmt_size(b)}  (−{(1 - b / a) * 100:.1f}%)")
            return out
        self.app.run(job)


class ConvertTool(Tool):
    key, icon, title = "convert", "convert", "Convert to PDF"
    subtitle = "EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT, DOCX and more."

    def build(self):
        self.files = self.add(FileList(self.body, [("Supported", " ".join("*" + e for e in core.ALL_FORMATS)),
                                                   ("All files", "*.*")], height=4))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.size = self.option_row("Ebook page size", ["A5", "A4", "A6", "Letter"])
        self.font = self.option_row("Ebook font size", [str(i) for i in range(8, 21)], "11")
        miss = missing_tools()
        if miss:
            self.note(tf("Not available in this build: {names}", names=miss))
        self.note("Persian / Arabic / Hebrew documents are shaped and laid out right-to-left automatically.")
        self.button("Convert", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if not files or not out:
            return messagebox.showwarning(D("Missing information"), D("Add files and choose an output folder."))
        size, font = self.size.get().lower(), int(self.font.get())

        def job(log, prog):
            for i, f in enumerate(files, 1):
                try:
                    p = core.convert_to_pdf(f, out, size, font)
                    log(f"✔ {Path(f).name} → {p.name}")
                except Exception as e:
                    log(f"✘ {Path(f).name}: {e}")
                prog(i, len(files))
            return out
        self.app.run(job)


class ImagesTool(Tool):
    key, icon, title = "images", "images", "Images to PDF"
    subtitle = "Pick several pictures, put them in order and turn them into one PDF."

    def build(self):
        ex = " ".join("*" + e for e in core.IMAGE_EXTS)
        self.files = self.add(FileList(self.body, [("Images", ex), ("All files", "*.*")], height=8))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.sizes = {D("Fit to image"): "Fit to image", "A4": "A4", "A5": "A5", "Letter": "Letter"}
        self.size = self.option_row("Page size", list(self.sizes), "A4")
        self.margins = {D("None"): 0, D("Small"): 18, D("Normal"): 36}
        self.margin = self.option_row("Margin", list(self.margins), D("Small"))
        self.button("Create PDF", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if not files or not out:
            return messagebox.showwarning(D("Missing information"), D("Add pictures and choose where to save."))
        size, margin = self.sizes[self.size.get()], self.margins[self.margin.get()]

        def job(log, prog):
            n = core.images_to_pdf(files, out, size, margin, prog)
            log(tf("✔ {n} picture(s) → {name}", n=n, name=Path(out).name))
            return str(Path(out).parent)
        self.app.run(job)


class PagesTool(Tool):
    key, icon, title = "pages", "pages", "Page tools"
    subtitle = "Delete, extract, rotate or reverse pages."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.info = self.add(label(self.body, ""))
        self.actions = {D("Delete pages"): "delete", D("Keep only (extract) pages"): "keep",
                        D("Rotate pages"): "rotate", D("Reverse page order"): "reverse"}
        self.action = self.option_row("Action", list(self.actions))
        self.pages = self.entry_row("Pages", "1-3, 7", "e.g. 1-3, 7, 10-")
        self.angles = {D("90° clockwise"): 90, D("180°"): 180, D("90° counter-clockwise"): 270}
        self.angle = self.option_row("Rotate by", list(self.angles))
        self.button("Apply", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_edited.pdf")))
        try:
            self.info.configure(text=tsf("{n} pages", n=core.page_count(p)))
        except Exception as e:
            self.info.configure(text=str(e))

    def run(self):
        src, out, action = self.src.get(), self.out.get(), self.actions[self.action.get()]
        if not self.need(src, out):
            return
        if Path(src).resolve() == Path(out).resolve():
            return messagebox.showwarning(D("Choose another file"), D("Save to a different file than the original."))
        angle, spec = self.angles[self.angle.get()], self.pages.get().strip()

        def job(log, prog):
            n = core.edit_pages(src, out, action, spec, angle)
            log(tf("✔ Saved {name} ({pages} pages)", name=Path(out).name, pages=n))
            return str(Path(out).parent)
        self.app.run(job)


class OcrTool(Tool):
    key, icon, title = "ocr", "ocr", "OCR"
    subtitle = ("Turn scanned books and documents into PDFs whose text can be searched and copied. "
                "Persian (Farsi) and Arabic are fully supported.")

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.langs = lang_choices()
        names = list(self.langs) or ["English  (eng)"]
        self.lang = self.option_row("Language", names, names[0])
        self.eng = self.check_row("Also recognise English words (recommended for mixed text)", True)
        self.dpis = {D("200 dpi (fast)"): 200, D("300 dpi (recommended)"): 300, D("400 dpi (small print)"): 400}
        self.dpi = self.option_row("Scan quality", list(self.dpis), D("300 dpi (recommended)"))
        self.skip = self.check_row("Skip pages that already contain text", True)
        self.note("The original page images stay untouched — only an invisible text layer is added, "
                  "so the file keeps its quality." if self.langs else "OCR engine is missing from this build.")
        self.button("Run OCR", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_ocr.pdf")))

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        lang = tess_lang(self.langs.get(self.lang.get(), "eng"), self.eng.get())
        dpi, skip = self.dpis[self.dpi.get()], self.skip.get()

        def job(log, prog):
            n, total = core.ocr_pdf(src, out, lang, dpi, skip, 3, prog)
            log(tf("✔ OCR finished: {n} of {total} pages → {name}", n=n, total=total, name=Path(out).name))
            return str(Path(out).parent)
        self.app.run(job)


class ExtractTool(Tool):
    key, icon, title = "extract", "extract", "Extract text"
    subtitle = "Get the text out of a PDF as a clean .txt or Word file. Scanned pages are read with OCR."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.fmts = {D("Text file (.txt)"): "txt", D("Word document (.docx)"): "docx"}
        self.fmt = self.option_row("Format", list(self.fmts))
        self.langs = lang_choices()
        self.ocr = self.check_row("Read scanned pages with OCR", bool(self.langs))
        names = list(self.langs) or ["English  (eng)"]
        self.lang = self.option_row("OCR language", names, names[0])
        self.eng = self.check_row("Also recognise English words", True)
        self.rev = self.check_row("Fix backwards Persian/Arabic text (old PDFs that extract reversed)", False)
        self.note("Persian letters are normalised (ﻣﻘﺪﻣﻪ → مقدمه) so the text can be searched and pasted anywhere.")
        self.button("Extract text", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).parent))

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        fmt = self.fmts[self.fmt.get()]
        lang = (tess_lang(self.langs.get(self.lang.get(), "eng"), self.eng.get())
                if self.ocr.get() and self.langs else None)
        rev = self.rev.get()

        def job(log, prog):
            dst = core.unique_path(Path(out) / (Path(src).stem + "." + fmt))
            chars, ocr_pages = core.extract_text(src, str(dst), fmt, lang, rev, prog)
            log(tf("✔ {name}: {chars} characters", name=dst.name, chars=f"{chars:,}")
                + (tf(", {n} page(s) read with OCR", n=ocr_pages) if ocr_pages else ""))
            if chars == 0:
                log(t("  (no text found — try enabling OCR)"))
            return out
        self.app.run(job)


# ------------------------------------------------------------------ science: LaTeX, formulas, symbols
MONO = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
SYM_FONT = "Cambria Math" if sys.platform == "win32" else "DejaVu Sans"


class PreviewPane(ctk.CTkFrame):
    """Shows the compiled PDF next to the editor."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        theme.style(self, fg_color="card")
        self.app, self.reader, self.page, self._img, self._job = app, None, 0, None, None
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        bar = frame(self, "card")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        button(bar, "◀", lambda: self.go(self.page - 1), "field", width=34, height=28).pack(side="left")
        self.lbl = label(bar, "", anchor="center")
        self.lbl.pack(side="left", padx=10)
        button(bar, "▶", lambda: self.go(self.page + 1), "field", width=34, height=28).pack(side="left")
        holder = frame(self, "field", 10)
        holder.grid(row=1, column=0, sticky="nsew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self.cv = tk.Canvas(holder, highlightthickness=0, bd=0)
        theme.style(self.cv, bg="field")
        self.cv.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        vs = ctk.CTkScrollbar(holder, command=self.cv.yview)
        theme.style(vs, button_color="hover", button_hover_color="accent")
        vs.grid(row=0, column=1, sticky="ns")
        self.cv.configure(yscrollcommand=vs.set)
        self.cv.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(int(-e.delta / 120) * 3, "units"))
        self.cv.bind("<Button-4>", lambda e: self.cv.yview_scroll(-3, "units"))
        self.cv.bind("<Button-5>", lambda e: self.cv.yview_scroll(3, "units"))
        self.cv.bind("<Configure>", lambda e: self._later())

    def _later(self):
        if self.app.resizing or not self.reader:
            return
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(200, self.render)

    def load(self, path):
        try:
            r = core.PdfReader(path)
        except Exception:
            return
        if self.reader:
            self.reader.close()
        self.reader = r
        self.page = min(self.page, r.page_count - 1)
        self.render()

    def go(self, i):
        if self.reader and 0 <= i < self.reader.page_count:
            self.page = i
            self.render()
            self.cv.yview_moveto(0)

    def render(self):
        if not self.reader:
            return
        w = max(self.cv.winfo_width() - 20, 160)
        zoom = max(0.2, min(w / self.reader.page_size(self.page)[0], 3))
        png, _ = self.reader.render(self.page, zoom)
        self._img = tk.PhotoImage(data=png)
        self.cv.delete("all")
        self.cv.create_image(max((self.cv.winfo_width() - self._img.width()) // 2, 0), 0, anchor="nw", image=self._img)
        self.cv.configure(scrollregion=(0, 0, self._img.width(), self._img.height()))
        self.lbl.configure(text=f"{self.page + 1} / {self.reader.page_count}")


def _insert_snippet(widget, tex: str):
    """Insert LaTeX at the cursor; a '▢' marks where the cursor should end up."""
    pos = tex.find("▢")
    text = tex.replace("▢", "")
    start = widget.index("insert")
    widget.insert("insert", text)
    if pos >= 0:
        widget.mark_set("insert", f"{start}+{pos}c")
    widget.focus_set()


class LatexTool(Tool):
    key, icon, title = "latex", "latex", "LaTeX"
    subtitle = "Write or open a .tex file, compile it to PDF and see errors explained in plain words."

    def build(self):
        self.path = None
        self._saved_text = ""
        self._result = None
        self._imported = None
        self._hl_job = None
        b = self.body
        b.rowconfigure(1, weight=1)
        side = "right" if RTL else "left"
        opp = "left" if RTL else "right"
        bar = frame(b, "card")
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        self.tpl_names = {D(n): n for n in templates.TEMPLATES}
        self.tpl_prompt = D("New from template…")
        self.tpl_var = tk.StringVar(value=self.tpl_prompt)
        option(bar, self.tpl_var, [self.tpl_prompt] + list(self.tpl_names), command=self._new_template,
               width=210).pack(side=side)
        button(bar, "Open…", self.open_dialog, "field", width=76).pack(side=side, padx=5)
        button(bar, "Save", self.save, "field", width=64).pack(side=side)
        button(bar, "Import…", self.import_dialog, "field", width=80).pack(side=side, padx=5)
        button(bar, "Symbols", self.app.show_palette, "field", width=84).pack(side=side)
        self.compile_btn = button(bar, "Compile ▶", self.compile, "primary", width=108, bold=True)
        self.compile_btn.pack(side=opp)
        eng = texengine.find_engine()
        self.engine_lbl = label(bar, eng.label if eng else "No LaTeX engine", 11, role="muted")
        self.engine_lbl.pack(side=opp, padx=10)

        split = frame(b, "card")
        split.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        split.rowconfigure(0, weight=1)
        for c in (0, 1):
            split.columnconfigure(c, weight=1, uniform="s")
        ed_col, pv_col = (1, 0) if RTL else (0, 1)
        self.editor = ctk.CTkTextbox(split, wrap="none", corner_radius=10, font=ctk.CTkFont(MONO, 12), undo=True)
        theme.style(self.editor, fg_color="field", text_color="text", scrollbar_button_color="hover",
                    scrollbar_button_hover_color="accent")
        self.editor.grid(row=0, column=ed_col, sticky="nsew", padx=(0, 4) if not RTL else (4, 0))
        self.ed = self.editor._textbox
        theme.style(self.ed, insertbackground="text", selectbackground="accent", selectforeground="on_accent")
        self.preview = PreviewPane(split, self.app)
        self.preview.grid(row=0, column=pv_col, sticky="nsew", padx=(4, 0) if not RTL else (0, 4))
        for tag in ("mth", "cmd", "com", "err"):
            self.ed.tag_configure(tag)
        self._retag()
        self.ed.bind("<KeyRelease>", lambda e: self._schedule_highlight())
        self.ed.bind("<FocusIn>", lambda e: setattr(self.app, "insert_target", self.ed))
        self.ed.bind("<Control-Return>", lambda e: (self.compile(), "break")[1])
        self.ed.bind("<Control-s>", lambda e: (self.save(), "break")[1])

        self.status = label(b, "Write LaTeX, press Compile (Ctrl+Enter).", 12, role="muted")
        self.status.grid(row=2, column=0, sticky="ew", padx=20, pady=(2, 2))
        self.errs = tk.Listbox(b, height=4, borderwidth=0, highlightthickness=0, activestyle="none",
                               font=(UI_FONT, 10), selectmode="browse")
        theme.style(self.errs, bg="field", fg="text", selectbackground="accent", selectforeground="on_accent")
        self.errs.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.errs.bind("<<ListboxSelect>>", self._jump)
        self._errors: list = []

    def _retag(self):
        self.ed.tag_configure("mth", foreground=theme.col("good"))
        self.ed.tag_configure("cmd", foreground=theme.col("accent_hover"))
        self.ed.tag_configure("com", foreground=theme.col("muted"))
        self.ed.tag_configure("err", background=theme.col("hover"))

    def on_show(self):
        super().on_show()
        self._retag()

    # ---- highlighting
    def _schedule_highlight(self):
        if self._hl_job:
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(400, self._highlight)

    def _tag_regex(self, tag, pattern):
        idx, cnt = "1.0", tk.IntVar()
        while True:
            pos = self.ed.search(pattern, idx, "end", count=cnt, regexp=True)
            if not pos or cnt.get() == 0:
                break
            end = f"{pos}+{cnt.get()}c"
            self.ed.tag_add(tag, pos, end)
            idx = end

    def _highlight(self):
        if int(self.ed.index("end-1c").split(".")[0]) > 4000:
            return
        for tag in ("mth", "cmd", "com"):
            self.ed.tag_remove(tag, "1.0", "end")
        self._tag_regex("mth", r"\$[^$\n]*\$")
        self._tag_regex("cmd", r"\\[a-zA-Z@]+|\\[^a-zA-Z]")
        self._tag_regex("com", r"%[^\n]*")

    # ---- files
    def _text(self):
        return self.ed.get("1.0", "end-1c")

    def _set_text(self, text):
        self.ed.delete("1.0", "end")
        self.ed.insert("1.0", text)
        self._saved_text = text
        self._highlight()

    def _confirm_discard(self):
        if self._text() != self._saved_text and self._text().strip():
            return messagebox.askyesno(D("Unsaved changes"), D("Replace the text in the editor? Unsaved changes will be lost."))
        return True

    def _new_template(self, value):
        self.tpl_var.set(self.tpl_prompt)
        name = self.tpl_names.get(value)
        if not name or not self._confirm_discard():
            return
        self._set_text(templates.get(name, texengine.fonts_dir()))
        self.path = None
        self._set_status("Template loaded. Press Compile — you will be asked where to save it.")

    def open_dialog(self):
        p = filedialog.askopenfilename(filetypes=[("LaTeX", "*.tex *.ltx"), ("All files", "*.*")])
        if p:
            self.open_file(p)

    def open_file(self, p):
        if not self._confirm_discard():
            return
        self._set_text(Path(p).read_text(encoding="utf-8", errors="replace"))
        self.path = p
        self._set_status(str(p), raw=True)
        pdf = Path(p).with_suffix(".pdf")
        if pdf.exists():
            self.preview.load(str(pdf))

    def drop(self, paths):
        p = paths[0]
        if p.lower().endswith((".tex", ".ltx")):
            self.open_file(p)
        elif p.lower().endswith(".pdf"):
            self.preview.load(p)

    def save(self):
        if not self.path:
            p = filedialog.asksaveasfilename(defaultextension=".tex", filetypes=[("LaTeX", "*.tex")])
            if not p:
                return False
            self.path = p
        Path(self.path).write_text(self._text(), encoding="utf-8")
        self._saved_text = self._text()
        self._set_status(tsf("Saved {name}", name=Path(self.path).name), raw=True)
        return True

    def _set_status(self, text, raw=False):
        self.status.configure(text=text if raw else D(text))

    def import_dialog(self):
        p = filedialog.askopenfilename(filetypes=[("Word, Markdown, ODT, EPUB, HTML", "*.docx *.odt *.rtf *.md *.markdown *.epub *.html *.htm"),
                                                  ("All files", "*.*")])
        if not p or self.app.busy:
            return

        def job(log, prog):
            prog(1, 3)
            self._imported = texengine.import_to_latex(p, str(Path(p).parent))
            log(tf("✔ Imported {name} → {out}", name=Path(p).name, out=Path(self._imported).name))
            return str(Path(p).parent)
        self._imported = None
        self.app.run(job, done=lambda: self._imported and self.open_file(self._imported))

    # ---- compile
    def compile(self):
        if self.app.busy:
            return
        if not self.save():
            return
        path = self.path
        self._set_status("Compiling…")
        self.errs.delete(0, "end")

        def job(log, prog):
            prog(1, 4)
            res = texengine.compile_tex(path)
            self._result = res
            if res.ok:
                log(tf("✔ {name} compiled with {engine} in {sec} s", name=Path(path).name, engine=res.engine,
                       sec=f"{res.seconds:.1f}"))
            else:
                log(tf("✘ {n} error(s) in {name}", n=len(res.errors), name=Path(path).name))
            prog(1, 1)
            return str(Path(path).parent)
        self.app.run(job, done=self._after_compile)

    def _after_compile(self):
        res = self._result
        if not res:
            return
        self.errs.delete(0, "end")
        self._errors = res.errors
        self.ed.tag_remove("err", "1.0", "end")
        for e in res.errors:
            hint = f"   —   {D(e.hint)}" if e.hint else ""
            self.errs.insert("end", f"{e.line:>4}   {e.message}{hint}" if e.line else f"       {e.message}{hint}")
            if e.line:
                self.ed.tag_add("err", f"{e.line}.0", f"{e.line}.end")
        if res.ok:
            self._set_status(tsf("✔ {name} compiled with {engine} in {sec} s", name=Path(self.path).name,
                                 engine=res.engine, sec=f"{res.seconds:.1f}"), raw=True)
            self.engine_lbl.configure(text=res.engine)
            if res.pdf:
                self.preview.load(res.pdf)
        else:
            self._set_status(tsf("✘ {n} error(s) in {name}", n=len(res.errors), name=Path(self.path).name), raw=True)
            if res.errors and res.errors[0].line:
                self.ed.see(f"{res.errors[0].line}.0")

    def _jump(self, _e):
        sel = self.errs.curselection()
        if not sel or sel[0] >= len(self._errors):
            return
        e = self._errors[sel[0]]
        if e.line:
            self.ed.mark_set("insert", f"{e.line}.0")
            self.ed.see(f"{e.line}.0")
        if e.hint:
            self._set_status(e.hint)


class FormulaTool(Tool):
    key, icon, title = "formula", "formula", "Formula"
    subtitle = "Type a formula in LaTeX and get a crisp image (PNG, SVG or PDF) for slides, Word or papers."
    EXAMPLES = {
        "Luxemburg norm (Orlicz)": r"\|f\|_{(\Phi)}=\inf\Bigl\{k>0:\int_\Omega \Phi\Bigl(\frac{|f|}{k}\Bigr)\,d\mu\le 1\Bigr\}",
        "Quadratic formula": r"x=\frac{-b\pm\sqrt{b^{2}-4ac}}{2a}",
        "Fourier transform": r"\widehat{f}(\xi)=\int_{\mathbb{R}^{n}} f(x)\,e^{-2\pi i\,x\cdot\xi}\,dx",
        "Cauchy–Schwarz inequality": r"\left|\langle x,y\rangle\right|\le\|x\|\,\|y\|",
        "Schrödinger equation": r"i\hbar\,\frac{\partial}{\partial t}\Psi(\mathbf{r},t)=\hat H\,\Psi(\mathbf{r},t)",
        "Maxwell: Gauss's law": r"\nabla\cdot\mathbf{E}=\frac{\rho}{\varepsilon_{0}}",
        "Nernst equation": r"E=E^{\circ}-\frac{RT}{nF}\ln Q",
        "Methane combustion": r"\ce{CH4 + 2O2 -> CO2 + 2H2O}",
        "Ammonia equilibrium": r"\ce{N2 + 3H2 <=> 2NH3}",
    }
    COLORS = {"Black": None, "White": "#ffffff", "Dark blue": "#1e3a8a", "Red": "#b91c1c", "Green": "#166534"}

    def build(self):
        self.ex = {D(k): v for k, v in self.EXAMPLES.items()}
        self.ex_prompt = D("Examples…")
        row = self._row("Example")
        self.ex_var = tk.StringVar(value=self.ex_prompt)
        option(row, self.ex_var, [self.ex_prompt] + list(self.ex), command=self._example).grid(
            row=0, column=1, sticky="ew", padx=8)
        self.add(row, pady=(4, 4))
        self.add(label(self.body, "LaTeX", 13, True), pady=(2, 2))
        self.box = ctk.CTkTextbox(self.body, height=72, wrap="word", corner_radius=10, font=ctk.CTkFont(MONO, 13), undo=True)
        theme.style(self.box, fg_color="field", text_color="text", scrollbar_button_color="hover",
                    scrollbar_button_hover_color="accent")
        self.add(self.box, pady=2)
        self.tx = self.box._textbox
        theme.style(self.tx, insertbackground="text", selectbackground="accent", selectforeground="on_accent")
        self.tx.bind("<FocusIn>", lambda e: setattr(self.app, "insert_target", self.tx))
        self.tx.insert("1.0", r"\int_{0}^{1} x^{2}\,dx=\frac{1}{3}")
        opts = frame(self.body, "card")
        self.add(opts, pady=(6, 2))
        for c in range(3):
            opts.columnconfigure(c, weight=1, uniform="o")
        self.modes = {D("Display (large)"): True, D("Inline (small)"): False}
        self.sizes = {D("Normal (300 dpi)"): 300, D("Large (450 dpi)"): 450, D("Huge (600 dpi)"): 600}
        self.colors = {D(k): v for k, v in self.COLORS.items()}
        self.mode, self.size, self.color = (tk.StringVar(value=list(d)[0]) for d in (self.modes, self.sizes, self.colors))
        for i, (var, vals) in enumerate(((self.mode, self.modes), (self.size, self.sizes), (self.color, self.colors))):
            option(opts, var, list(vals)).grid(row=0, column=(2 - i) if RTL else i, sticky="ew", padx=3)
        bar = frame(self.body, "card")
        self.add(bar, pady=(6, 4))
        side = "right" if RTL else "left"
        self.transp = tk.BooleanVar(value=True)
        button(bar, "Render", self.render, "primary", width=110, height=38, bold=True).pack(side=side)
        button(bar, "Save…", self.save, "field", width=96, height=38).pack(side=side, padx=6)
        button(bar, "Copy LaTeX", self.copy, "field", width=116, height=38).pack(side=side)
        button(bar, "Symbols", self.app.show_palette, "field", width=96, height=38).pack(side=side, padx=6)
        check(bar, "Transparent background", self.transp).pack(side="left" if RTL else "right")
        self.paper = ctk.CTkFrame(self.body, height=120, corner_radius=12, fg_color="#ffffff")
        self.add(self.paper, pady=(4, 2))
        self.paper.grid_propagate(False)
        self.paper.columnconfigure(0, weight=1)
        self.paper.rowconfigure(0, weight=1)
        self.pic = ctk.CTkLabel(self.paper, text="", fg_color="transparent")
        self.pic.grid(row=0, column=0)
        self.msg = self.add(label(self.body, "", 12, role="muted"), pady=(2, 10))
        self._last = None

    def _example(self, value):
        tex = self.ex.get(value)
        self.ex_var.set(self.ex_prompt)
        if tex:
            self.tx.delete("1.0", "end")
            self.tx.insert("1.0", tex)
            self.render()

    def _params(self):
        return (self.tx.get("1.0", "end-1c").strip(), self.modes[self.mode.get()], self.colors[self.color.get()],
                self.transp.get())

    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.tx.get("1.0", "end-1c").strip())
        self.app.toast("LaTeX copied")

    def render(self):
        tex, disp, color, transp = self._params()
        if not tex or self.app.busy:
            return
        self.msg.configure(text=D("Rendering…"))
        self._last = None

        def job(log, prog):
            prog(1, 3)
            imgs, logtxt = texengine.render_formulas([(tex, disp)], dpi=300, color=color, transparent=True)
            im = imgs[0]
            if im.ok:
                self._last = im
            else:
                errs = texengine.parse_errors(logtxt)
                msg = errs[0].message if errs else "could not render"
                raise RuntimeError(msg)
            prog(1, 1)
        self.app.run(job, done=self._shown)

    def _shown(self):
        im = self._last
        if not im:
            self.msg.configure(text=D("Could not render this formula. See the log below."))
            return
        from PIL import Image
        pil = Image.open(io.BytesIO(im.png)).convert("RGBA")
        dark_paper = (self.colors[self.color.get()] or "").lower() == "#ffffff"
        bg = Image.new("RGBA", pil.size, (27, 27, 27, 255) if dark_paper else (255, 255, 255, 255))
        bg.alpha_composite(pil)
        self.paper.configure(fg_color="#1b1b1b" if dark_paper else "#ffffff")
        scale = min(1.0, 640 / pil.width, 108 / pil.height)
        size = (max(int(pil.width * scale), 1), max(int(pil.height * scale), 1))
        self._pic = ctk_image(bg.convert("RGB"), size)
        self.pic.configure(image=self._pic)
        self.msg.configure(text=D("Rendered. Use Save… for PNG, SVG or PDF."))

    def save(self):
        tex, disp, color, transp = self._params()
        if not tex or self.app.busy:
            return
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image", "*.png"), ("SVG vector", "*.svg"),
                                                                              ("PDF", "*.pdf")])
        if not p:
            return
        fmt = Path(p).suffix.lower().lstrip(".")
        if fmt not in ("png", "svg", "pdf"):
            fmt, p = "png", p + ".png"
        dpi = self.sizes[self.size.get()]
        base = str(Path(p).with_suffix(""))

        def job(log, prog):
            prog(1, 3)
            files = texengine.formula_files(tex, disp, base, (fmt,), dpi, color, transp)
            log(tf("✔ Saved {name}", name=Path(files[0]).name))
            return str(Path(p).parent)
        self.app.run(job)


class SymbolPalette(ctk.CTkToplevel):
    """Floating window: click a symbol to insert its LaTeX at the cursor."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Symbols" if not RTL else i18n.shape(t("Symbols")))
        self.geometry("700x520+80+80")
        self.minsize(600, 440)
        self.configure(fg_color=theme.col("bg"))
        self.transient(app)
        self.cat = symbols.CATEGORIES[0]
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self, fg_color=theme.col("bg"))
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        self.q = tk.StringVar()
        e = ctk.CTkEntry(top, textvariable=self.q, placeholder_text="Search: integral, alpha, ∂, norm…", height=34,
                         corner_radius=10, border_width=0, fg_color=theme.col("field"), text_color=theme.col("text"),
                         placeholder_text_color=theme.col("muted"), font=F(13))
        e.pack(fill="x")
        self.q.trace_add("write", lambda *_: self._search())
        side = ctk.CTkFrame(self, fg_color=theme.col("card"), corner_radius=14, width=170)
        side.grid(row=1, column=0, sticky="ns", padx=(12, 6), pady=6)
        side.grid_propagate(False)
        self.cat_btns = {}
        for c in symbols.CATEGORIES:
            b = ctk.CTkButton(side, text=D(c), anchor="w", height=30, corner_radius=8, font=F(12),
                              fg_color="transparent", hover_color=theme.col("hover"), text_color=theme.col("text"),
                              command=lambda c=c: self.show_cat(c))
            b.pack(fill="x", padx=8, pady=1)
            self.cat_btns[c] = b
        self.grid_frame = ctk.CTkFrame(self, fg_color=theme.col("card"), corner_radius=14)
        self.grid_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=6)
        self.info = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(MONO, 12), text_color=theme.col("muted"))
        self.info.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 10))
        self.show_cat(self.cat)
        self.bind("<Escape>", lambda e: self.destroy())

    def show_cat(self, cat):
        self.cat = cat
        for c, b in self.cat_btns.items():
            b.configure(fg_color=theme.col("accent") if c == cat else "transparent",
                        text_color=theme.col("on_accent") if c == cat else theme.col("text"))
        self._fill([(g, tex, words, pkg) for g, tex, words, pkg in symbols.SYMBOLS[cat]])

    def _search(self):
        q = self.q.get().strip()
        if not q:
            return self.show_cat(self.cat)
        self._fill([(g, tex, words, pkg) for g, tex, words, pkg, _c in symbols.search(q)])

    def _fill(self, items):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        cols = 8
        for i, (g, tex, words, pkg) in enumerate(items[:96]):
            b = tk.Button(self.grid_frame, text=g, font=(SYM_FONT, 13), width=5, height=1, relief="flat", bd=0,
                          highlightthickness=0, takefocus=0,
                          bg=theme.col("field"), fg=theme.col("text"), activebackground=theme.col("accent"),
                          activeforeground=theme.col("on_accent"), cursor="hand2",
                          command=lambda tex=tex: self.app.insert_snippet(tex))
            b.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky="nsew")
            b.bind("<Enter>", lambda e, tex=tex, words=words, pkg=pkg: self.info.configure(
                text=f"{tex.replace('▢', '')}     {words}" + (f"     [{pkg}]" if pkg else "")))
            b.bind("<Button-3>", lambda e, tex=tex: self.app.copy_snippet(tex))
        for c in range(cols):
            self.grid_frame.columnconfigure(c, weight=1)
        if not items:
            ctk.CTkLabel(self.grid_frame, text=D("Nothing found."), text_color=theme.col("muted")).pack(pady=30)


# ------------------------------------------------------------------ home / settings / help
class HomeTool(Tool):
    key, icon, title = "home", "home", "PDF Toolkit"
    subtitle = "Everything for your PDFs in one place — with first-class Persian (Farsi) support."
    CARDS = [("read", "Read", "Open and search PDFs, including Farsi"),
             ("ocr", "OCR", "Make scanned books searchable (Farsi, Arabic…)"),
             ("extract", "Extract text", "PDF to clean TXT / Word, with OCR"),
             ("convert", "Convert to PDF", "EPUB, DjVu, DOCX, MOBI, TXT, HTML…"),
             ("split", "Split", "Cut a PDF into parts or ranges"),
             ("merge", "Merge", "Join PDFs in any order"),
             ("compress", "Compress", "Four levels, up to Ghostscript power"),
             ("images", "Images to PDF", "Many pictures into one PDF"),
             ("pages", "Page tools", "Delete, extract, rotate, reverse"),
             ("latex", "LaTeX", "Write and compile .tex to PDF, with templates"),
             ("formula", "Formula", "LaTeX formula to PNG / SVG / PDF")]

    def build(self):
        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        theme.style(grid, fg_color="card")
        grid.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 4))
        self.body.rowconfigure(0, weight=1)
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="c")
        self._tiles = []
        for i, (key, name, desc) in enumerate(self.CARDS):
            r, c = divmod(i, 3)
            c = 2 - c if RTL else c
            tile = frame(grid, "field", 14, height=88)
            tile.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            tile.grid_propagate(False)
            icon_img = ctk_image(art.icon(key, 96), (44, 44))
            ic = ctk.CTkLabel(tile, text="", image=icon_img, fg_color="transparent")
            theme.style(ic, fg_color="field")
            ic.place(relx=1.0 if RTL else 0.0, x=-14 if RTL else 14, y=14, anchor="ne" if RTL else "nw")
            tx = label(tile, name, 15, True, wrap=0)
            tx.place(relx=1.0 if RTL else 0.0, x=-68 if RTL else 68, y=10, anchor="ne" if RTL else "nw")
            ds = label(tile, desc, 11, role="muted", wrap=170)
            ds.place(relx=1.0 if RTL else 0.0, x=-68 if RTL else 68, y=34, anchor="ne" if RTL else "nw")
            for w in (tile, ic, tx, ds):
                theme.style(w, fg_color="field") if w in (tile, ic) else None
                w.bind("<Enter>", lambda _e, t_=tile: t_.configure(fg_color=theme.col("hover")))
                w.bind("<Leave>", lambda _e, t_=tile: t_.configure(fg_color=theme.col("field")))
                w.bind("<Button-1>", lambda _e, k=key: self.app.show(k))
                try:
                    w.configure(cursor="hand2")
                except Exception:
                    pass
            for w in (tx, ds):
                theme.style(w, fg_color="transparent")
            self._tiles.append((tile, ic, tx, ds))
        chips = frame(self.body, "field", 14)
        chips.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 6))
        langs = core.ocr_languages()
        status = [("Persian OCR", "fas" in langs), ("Arabic OCR", "ara" in langs),
                  ("DjVu", bool(core.find_ddjvu())), ("DOCX / ODT / RTF", bool(core.find_pandoc())),
                  ("Ghostscript", bool(core.find_gs())), ("LaTeX", bool(texengine.find_engine()))]
        for j, (n, ok) in enumerate(status):
            lb = ctk.CTkLabel(chips, text=("●  " if ok else "○  ") + D(n), font=F(12))
            theme.style(lb, text_color="good" if ok else "muted", fg_color="field")
            lb.grid(row=0, column=(len(status) - 1 - j) if RTL else j, padx=10, pady=10)
        tip = label(self.body, "Tip: drag & drop files onto the window to use them in the open tool.", 12, role="muted")
        tip.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14))


class SettingsTool(Tool):
    key, icon, title = "settings", "settings", "Settings"
    subtitle = "Choose a theme and picture, and switch the language."

    def build(self):
        b = self.body
        self.add(label(b, "Theme", 15, True), pady=(2, 2))
        grid = ctk.CTkFrame(b, fg_color="transparent")
        theme.style(grid, fg_color="card")
        self.add(grid, pady=2)
        self._theme_btns = {}
        for i, (key, pal) in enumerate(theme.THEMES.items()):
            r, c = divmod(i, 5)
            c = 4 - c if RTL else c
            img = ctk_image(art.swatch(pal, (116, 60)), (116, 60))
            btn = ctk.CTkButton(grid, text=D(pal["name"]), image=img, compound="top", width=130, height=92,
                                corner_radius=14, border_width=2, font=F(12),
                                command=lambda k=key: self.app.set_theme(k))
            theme.style(btn, fg_color="card", hover_color="hover", text_color="text", border_color="card")
            btn.grid(row=r, column=c, padx=3, pady=3)
            self._theme_btns[key] = btn
        self.add(label(b, "Picture", 15, True), pady=(8, 2))
        row = ctk.CTkFrame(b, fg_color="transparent")
        theme.style(row, fg_color="card")
        self.add(row)
        self.wp_names = {D(art.WALLPAPER_NAMES[k]): k for k in art.WALLPAPERS}
        self.wp_names[D(art.WALLPAPER_NAMES["custom"])] = "custom"
        self.wp = tk.StringVar(value=next((n for n, k in self.wp_names.items() if k == CFG["wallpaper"]), ""))
        side = "right" if RTL else "left"
        option(row, self.wp, list(self.wp_names), command=self._wp_changed, width=200).pack(side=side)
        button(row, "Choose my picture…", self._pick_picture, width=170).pack(side=side, padx=10)
        self.add(label(b, "Language", 15, True), pady=(8, 2))
        self.fa_label = i18n.shape("فارسی")
        self.seg = ctk.CTkSegmentedButton(b, values=["English", self.fa_label], command=self._lang_changed,
                                          height=34, font=F(13))
        theme.style(self.seg, fg_color="field", selected_color="accent", selected_hover_color="accent_hover",
                    unselected_color="field", unselected_hover_color="hover", text_color="text")
        self.seg.set(self.fa_label if CFG["lang"] == "fa" else "English")
        self.seg.configure(width=260)
        self.add(self.seg)
        self.seg.grid_configure(sticky="e" if RTL else "w")
        self.add(label(b, "Changing the language restarts the app (your files and settings are kept).", 12,
                       role="muted", wrap=700), pady=(2, 6))
        self.refresh_selection()

    def refresh_selection(self):
        for k, btn in self._theme_btns.items():
            btn.configure(border_color=theme.col("accent") if k == theme.STATE.name else theme.col("card"))

    def on_show(self):
        super().on_show()
        self.refresh_selection()

    def _wp_changed(self, name):
        key = self.wp_names.get(name, "aurora")
        if key == "custom" and not CFG["custom_picture"]:
            return self._pick_picture()
        self.app.set_wallpaper(key)

    def _pick_picture(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if p:
            self.app.set_wallpaper("custom", p)
            self.wp.set(D(art.WALLPAPER_NAMES["custom"]))

    def _lang_changed(self, value):
        new = "fa" if value == self.fa_label else "en"
        if new != CFG["lang"]:
            CFG["lang"] = new
            settings.save(CFG)
            self.app.restart()


class HelpTool(Tool):
    key, icon, title = "help", "help", "Help"
    subtitle = "How to use every tool, tips for Persian documents, and answers to common questions."

    def build(self):
        b = self.body
        b.columnconfigure(0, weight=0)
        b.columnconfigure(1, weight=1)
        b.rowconfigure(0, weight=1)
        self.topics = helpdata.TOPICS[CFG["lang"]]
        side = ctk.CTkFrame(b, fg_color="transparent", width=230)
        theme.style(side, fg_color="card")
        box = ctk.CTkTextbox(b, wrap="none" if RTL else "word", border_width=0, corner_radius=12, font=F(13),
                             activate_scrollbars=True)
        theme.style(box, fg_color="field", text_color="text", scrollbar_button_color="hover",
                    scrollbar_button_hover_color="accent")
        box.grid(row=0, column=0 if RTL else 1, sticky="nsew", padx=(14, 6) if RTL else (6, 14), pady=14)
        side.grid(row=0, column=1 if RTL else 0, sticky="ns", padx=(6, 14) if RTL else (14, 6), pady=14)
        b.columnconfigure(0, weight=1 if RTL else 0)
        b.columnconfigure(1, weight=0 if RTL else 1)
        self.box = box
        self.btns = []
        for i, (title, _body) in enumerate(self.topics):
            bt = button(side, title, lambda i=i: self.show_topic(i), "field", height=34, width=220)
            bt.pack(pady=2, anchor="e" if RTL else "w")
            self.btns.append(bt)
        self._cur = 0
        self.box.bind("<Configure>", lambda e: self._debounced())
        self._job = None
        self.show_topic(0)

    def _debounced(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, lambda: self.show_topic(self._cur))

    def on_show(self):
        super().on_show()
        self.show_topic(self._cur)

    def show_topic(self, i):
        self._cur = i
        for j, bt in enumerate(self.btns):
            if j == i:
                theme.style(bt, fg_color="accent", hover_color="accent_hover", text_color="on_accent")
            else:
                theme.style(bt, fg_color="field", hover_color="hover", text_color="text")
        title, body = self.topics[i]
        tb = self.box._textbox
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        width = max(self.box.winfo_width() - 60, 380)
        fnt_b, fnt = _measure_font(13), _measure_font(13)
        tb.tag_configure("h", font=F(19, True), spacing3=8)
        tb.tag_configure("p", font=F(13), spacing3=12)
        tb.tag_configure("r", justify="right")
        self.box.insert("end", (i18n.shape(title) if RTL else title) + "\n", ("h", "r") if RTL else "h")
        for para in body.strip().split("\n\n"):
            if RTL:
                lines = "\n".join(i18n.shape(l) for l in i18n.wrap(para.strip(), fnt.measure, width))
                self.box.insert("end", lines + "\n", ("p", "r"))
            else:
                self.box.insert("end", para.strip() + "\n", "p")
        self.box.configure(state="disabled")


# ------------------------------------------------------------------ app
_Base = type("_Base", (ctk.CTk, TkinterDnD.DnDWrapper), {}) if HAS_DND else ctk.CTk


class App(_Base):
    TOOLS = [("home", "Home", HomeTool), ("read", "Read", ReadTool), ("ocr", "OCR", OcrTool),
             ("extract", "Extract text", ExtractTool), ("convert", "Convert to PDF", ConvertTool),
             ("split", "Split", SplitTool), ("merge", "Merge", MergeTool), ("compress", "Compress", CompressTool),
             ("images", "Images to PDF", ImagesTool), ("pages", "Page tools", PagesTool),
             ("latex", "LaTeX", LatexTool), ("formula", "Formula", FormulaTool)]
    EXTRA = [("settings", "Settings", SettingsTool), ("help", "Help", HelpTool)]

    def __init__(self):
        super().__init__()
        setup_fonts()
        self.dnd = False
        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd = True
            except Exception:
                self.dnd = False
        self.title("PDF Toolkit" if not RTL else i18n.shape("جعبه‌ابزار PDF"))
        self.geometry("1120x820")
        self.minsize(1000, 740)
        self.q: queue.Queue = queue.Queue()
        self.busy, self.last_dir = False, None
        self.insert_target, self._palette, self._done_cb = None, None, None
        self.resizing, self._rz_job, self._size = False, None, (0, 0)
        theme.set_owner("chrome")
        theme.style(self, fg_color="bg")
        content_col, side_col = (0, 1) if RTL else (1, 0)
        self.columnconfigure(content_col, weight=1)
        self.columnconfigure(side_col, weight=0)
        self.rowconfigure(0, weight=1)
        if sys.platform == "win32":
            try:
                self.iconbitmap(str(core._app_dir() / "icon.ico"))
            except Exception:
                pass

        side = frame(self, "sidebar", 0, width=230)
        side.grid(row=0, column=side_col, rowspan=2, sticky="ns")
        side.grid_propagate(False)
        logo = ctk.CTkFrame(side, fg_color="transparent")
        theme.style(logo, fg_color="sidebar")
        logo.pack(fill="x", padx=18, pady=(24, 14))
        ic = ctk.CTkLabel(logo, text="", image=ctk_image(art.icon("home", 96), (42, 42)), fg_color="transparent")
        theme.style(ic, fg_color="sidebar")
        name = label(logo, "PDF Toolkit", 20, True)
        theme.style(name, fg_color="sidebar")
        ic.pack(side="right" if RTL else "left")
        name.pack(side="right" if RTL else "left", padx=10)
        self.nav = {}
        for key, title, cls in self.TOOLS + [("settings", "Settings", SettingsTool), ("help", "Help", HelpTool)]:
            if key in ("settings", "latex"):
                sep = ctk.CTkFrame(side, height=1, fg_color="transparent")
                theme.style(sep, fg_color="hover")
                sep.pack(fill="x", padx=18, pady=8)
            b = ctk.CTkButton(side, text="  " + D(title), anchor="e" if RTL else "w", height=40, corner_radius=11,
                              font=F(14), image=ctk_image(art.icon(key, 64), (26, 26)),
                              compound="right" if RTL else "left", command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=12, pady=1)
            self.nav[key] = b

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        theme.style(self.main, fg_color="bg")
        self.main.grid(row=0, column=content_col, sticky="nsew", padx=28, pady=(22, 8))
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.pages, self.current = {}, None

        self.foot = frame(self, "card")
        self.foot.grid(row=1, column=content_col, sticky="ew", padx=28, pady=(0, 20))
        self.foot.columnconfigure(0, weight=1)
        self.bar = ctk.CTkProgressBar(self.foot, height=8)
        theme.style(self.bar, progress_color="accent", fg_color="field")
        self.bar.set(0)
        self.open_btn = button(self.foot, "Open folder", self.open_folder, width=110, height=28)
        self.open_btn.configure(state="disabled")
        bar_col, btn_col = (1, 0) if RTL else (0, 1)
        self.foot.columnconfigure(bar_col, weight=1)
        self.foot.columnconfigure(btn_col, weight=0)
        self.bar.grid(row=0, column=bar_col, sticky="ew", padx=(18, 8), pady=(16, 0))
        self.open_btn.grid(row=0, column=btn_col, padx=(18, 0) if RTL else (0, 18), pady=(12, 0))
        self.log = ctk.CTkTextbox(self.foot, height=80, state="disabled", corner_radius=10, font=F(12))
        theme.style(self.log, fg_color="field", text_color="text")
        self.log.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 16))
        self.toast_lbl = ctk.CTkLabel(self, text="", corner_radius=10, font=F(12))
        theme.style(self.toast_lbl, fg_color="accent", text_color="on_accent")
        self.show("home")
        self._refresh_nav()
        theme.mark_built("chrome")
        self.after(100, self._poll)
        self.after(250, self._prebuild)
        self.bind("<Configure>", self._on_configure)

    # ---- pages
    def _page(self, key):
        if key not in self.pages:
            cls = {k: c for k, _, c in self.TOOLS + self.EXTRA}[key]
            theme.set_owner(key)
            self.pages[key] = cls(self)
            theme.mark_built(key)
        return self.pages[key]

    def _prebuild(self):
        """Build the remaining pages while idle (hidden), one per tick, so tab switches are instant."""
        for key, _, _ in self.TOOLS + self.EXTRA:
            if key not in self.pages:
                self._page(key)
                self.after(60, self._prebuild)
                return

    def show(self, key):
        if self.current == key:
            return
        if self.current:
            self.pages[self.current].grid_remove()
        page = self._page(key)
        theme.apply(key)              # catch up if the theme changed while this page was hidden
        page.grid(row=0, column=0, sticky="nsew")
        self.current = key
        self._refresh_nav()
        self.after(10, page.on_show)

    def _refresh_nav(self):
        for k, b in self.nav.items():
            active = k == self.current
            b.configure(fg_color=theme.col("accent") if active else "transparent",
                        hover_color=theme.col("accent_hover") if active else theme.col("hover"),
                        text_color=theme.col("on_accent") if active else theme.col("text"))

    # ---- theme / picture / language (fast path: only the visible page is touched)
    def set_theme(self, key):
        theme.set_theme(key)
        CFG["theme"] = key
        settings.save(CFG)
        theme.apply("chrome")
        self._refresh_nav()
        if self._palette is not None:
            try:
                self._palette.destroy()
            except Exception:
                pass
            self._palette = None
            self.after(50, self.show_palette)
        if self.current:
            theme.apply(self.current)
            self.pages[self.current].refresh_banner(force=True)

    def set_wallpaper(self, key, custom=None):
        CFG["wallpaper"] = key
        if custom:
            CFG["custom_picture"] = custom
        settings.save(CFG)
        if self.current:
            self.pages[self.current].refresh_banner(force=True)

    def restart(self):
        args = [sys.executable] + ([] if getattr(sys, "frozen", False) else sys.argv)
        try:
            subprocess.Popen(args)
        finally:
            self.destroy()

    def show_palette(self):
        if self._palette is not None:
            try:
                self._palette.deiconify()
                self._palette.lift()
                return
            except Exception:
                self._palette = None
        self._palette = SymbolPalette(self)

    def insert_snippet(self, tex):
        tgt = self.insert_target
        try:
            if tgt is not None and tgt.winfo_exists():
                _insert_snippet(tgt, tex)
                return
        except Exception:
            pass
        self.copy_snippet(tex)

    def copy_snippet(self, tex):
        self.clipboard_clear()
        self.clipboard_append(tex.replace("▢", ""))
        self.toast("LaTeX copied")

    def toast(self, text):
        self.toast_lbl.configure(text="  " + D(text) + "  ")
        self.toast_lbl.place(relx=0.5, rely=0.03, anchor="n")
        self.after(1600, self.toast_lbl.place_forget)

    # ---- smooth resizing: hide the heavy content while the window edge is being dragged
    def _on_configure(self, e):
        if e.widget is not self:
            return
        size = (e.width, e.height)
        if size == self._size:
            return
        first = self._size == (0, 0)
        self._size = size
        if first:
            return
        if not self.resizing:
            self.resizing = True
            self.main.grid_remove()
            self.foot.grid_remove()
        if self._rz_job:
            self.after_cancel(self._rz_job)
        self._rz_job = self.after(140, self._end_resize)

    def _end_resize(self):
        self.resizing = False
        content_col = 0 if RTL else 1
        self.main.grid(row=0, column=content_col, sticky="nsew", padx=28, pady=(22, 8))
        self.foot.grid(row=1, column=content_col, sticky="ew", padx=28, pady=(0, 20))
        if self.current:
            self.pages[self.current].refresh_banner()

    # ---- background jobs
    def run(self, job, done=None):
        if self.busy:
            return
        self._done_cb = done
        self.busy = True
        self.bar.set(0)
        self.open_btn.configure(state="disabled")

        def wrap():
            try:
                self.q.put(("dir", job(lambda m: self.q.put(("log", m)),
                                       lambda i, t_: self.q.put(("prog", i / max(t_, 1))))))
            except Exception as e:
                self.q.put(("log", f"✘ {t('Error')}: {e}"))
            self.q.put(("done",))
        threading.Thread(target=wrap, daemon=True).start()

    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "log":
                    self.log.configure(state="normal")
                    text = i18n.shape(m[1]) if RTL else m[1]
                    self.log.insert("end", text + "\n", "r" if RTL else None)
                    if RTL:
                        self.log._textbox.tag_configure("r", justify="right")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif m[0] == "prog":
                    self.bar.set(m[1])
                elif m[0] == "dir" and m[1]:
                    self.last_dir = m[1]
                    self.open_btn.configure(state="normal")
                elif m[0] == "done":
                    self.busy = False
                    cb, self._done_cb = self._done_cb, None
                    if cb:
                        cb()
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def open_folder(self):
        if not self.last_dir:
            return
        if sys.platform == "win32":
            os.startfile(self.last_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", self.last_dir])
        else:
            subprocess.run(["xdg-open", self.last_dir])


if __name__ == "__main__":
    App().mainloop()
