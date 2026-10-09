"""PDF Toolkit - read, split, merge, compress, convert, images to PDF, page tools, OCR (Farsi ready)."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import core

try:  # drag & drop files onto the window (optional)
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:  # pragma: no cover
    HAS_DND = False

ctk.set_default_color_theme("blue")
ACCENT = ("#4f46e5", "#6366f1")
ACCENT_HOVER = ("#4338ca", "#818cf8")
BG = ("#f3f4f9", "#12141a")
SIDEBAR = ("#ffffff", "#191c24")
CARD = ("#ffffff", "#1d212b")
CARD_HOVER = ("#eef0fb", "#262b3a")
FIELD = ("#f1f2f8", "#272c38")
MUTED = ("gray40", "gray62")
FONT = "Segoe UI"

PDF = [("PDF files", "*.pdf")]
LANG_NAMES = {"fas": "Persian (Farsi)", "eng": "English", "ara": "Arabic", "deu": "German",
              "fra": "French", "spa": "Spanish", "ita": "Italian", "rus": "Russian",
              "tur": "Turkish", "nld": "Dutch", "por": "Portuguese", "heb": "Hebrew",
              "ell": "Greek", "chi_sim": "Chinese (Simplified)", "jpn": "Japanese", "kor": "Korean"}
LANG_ORDER = ["fas", "eng", "ara"]


def lang_choices() -> dict[str, str]:
    """{label: code} with Persian first."""
    codes = core.ocr_languages()
    codes.sort(key=lambda c: (LANG_ORDER.index(c) if c in LANG_ORDER else 99, LANG_NAMES.get(c, c)))
    return {f"{LANG_NAMES.get(c, c)}  ({c})": c for c in codes}


def tess_lang(code: str, also_english: bool) -> str:
    if also_english and code != "eng" and "eng" in core.ocr_languages():
        return f"{code}+eng"
    return code


# ------------------------------------------------------------------ widgets
class FileRow(ctk.CTkFrame):
    """Label + entry + browse button (file or folder)."""

    def __init__(self, master, label, kind="open", types=None, on_pick=None, save_ext=".pdf"):
        super().__init__(master, fg_color="transparent")
        self.kind, self.types, self.on_pick, self.save_ext = kind, types, on_pick, save_ext
        self.var = tk.StringVar()
        self.columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=label, width=110, anchor="w").grid(row=0, column=0)
        ctk.CTkEntry(self, textvariable=self.var, fg_color=FIELD, border_width=0, corner_radius=10,
                     height=34).grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkButton(self, text="Browse…", width=90, height=34, corner_radius=10, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self._browse).grid(row=0, column=2)

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
        self.types = types
        self.files: list[str] = []
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.lb = tk.Listbox(self, height=height, selectmode="extended", borderwidth=0,
                             highlightthickness=0, activestyle="none", font=(FONT, 10))
        self.lb.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(self, command=self.lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.lb.configure(yscrollcommand=sb.set)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for text, cmd in [("＋ Add files", self.add_dialog), ("▲ Up", lambda: self.move(-1)),
                          ("▼ Down", lambda: self.move(1)), ("Remove", self.remove),
                          ("Clear", self.clear)]:
            primary = text.startswith("＋")
            ctk.CTkButton(bar, text=text, width=84, height=30, corner_radius=9, command=cmd,
                          fg_color=ACCENT if primary else FIELD,
                          hover_color=ACCENT_HOVER if primary else ("gray82", "gray30"),
                          text_color="white" if primary else ("gray15", "gray90")
                          ).pack(side="left", padx=(0, 6))
        self.count = ctk.CTkLabel(bar, text="0 files")
        self.count.pack(side="right")
        self.recolor()

    def recolor(self):
        dark = ctk.get_appearance_mode() == "Dark"
        self.lb.configure(bg="#272c38" if dark else "#f1f2f8", fg="#e8e8ee" if dark else "#14151a",
                          selectbackground="#6366f1" if dark else "#4f46e5", selectforeground="white")

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
        self.count.configure(text=f"{len(self.files)} file(s)")

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
    """Base page: title, subtitle, content card, run button."""

    title, subtitle = "", ""

    def __init__(self, app):
        super().__init__(app.main, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=self.title, font=ctk.CTkFont(FONT, 26, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(self, text=self.subtitle, anchor="w", justify="left", wraplength=700,
                     font=ctk.CTkFont(FONT, 13), text_color=MUTED).grid(
            row=1, column=0, sticky="ew", pady=(0, 14))
        self.body = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.build()
        if app.dnd:
            self._enable_drop()

    def build(self): ...

    # ---- drag & drop: the first file list / file row on the page receives the files
    def _enable_drop(self):
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", lambda e: self.drop(list(self.tk.splitlist(e.data))))
            self.body.drop_target_register(DND_FILES)
            self.body.dnd_bind("<<Drop>>", lambda e: self.drop(list(self.tk.splitlist(e.data))))
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

    def add(self, widget, **kw):
        row = self.body.grid_size()[1]
        pad = kw.pop("pady", 6)
        if isinstance(pad, tuple):
            pad = (pad[0] + (14 if row == 0 else 0), pad[1])
        elif row == 0:
            pad = (pad + 14, pad)
        widget.grid(row=row, column=0, sticky="ew", padx=22, pady=pad, **kw)
        return widget

    def button(self, text, cmd):
        b = ctk.CTkButton(self.body, text=text, height=44, corner_radius=12,
                          font=ctk.CTkFont(FONT, 15, "bold"), fg_color=ACCENT,
                          hover_color=ACCENT_HOVER, command=cmd)
        self.add(b, pady=(18, 20))
        return b

    def entry_row(self, label, default="", hint=""):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        f.columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=label, width=110, anchor="w").grid(row=0, column=0)
        var = tk.StringVar(value=default)
        ctk.CTkEntry(f, textvariable=var, placeholder_text=hint, fg_color=FIELD, border_width=0,
                     corner_radius=10, height=34).grid(row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def option_row(self, label, values, default=None):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        f.columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=label, width=110, anchor="w").grid(row=0, column=0)
        var = tk.StringVar(value=default or values[0])
        ctk.CTkOptionMenu(f, variable=var, values=values, fg_color=FIELD, button_color=ACCENT,
                          button_hover_color=ACCENT_HOVER, text_color=("gray10", "gray92"),
                          corner_radius=10, height=34, dropdown_font=ctk.CTkFont(FONT, 13)).grid(
            row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def check_row(self, text, default=True):
        var = tk.BooleanVar(value=default)
        self.add(ctk.CTkCheckBox(self.body, text=text, variable=var, fg_color=ACCENT,
                                 hover_color=ACCENT_HOVER, corner_radius=6), pady=4)
        return var

    def note(self, text):
        self.add(ctk.CTkLabel(self.body, text=text, anchor="w", justify="left", wraplength=660,
                              text_color=MUTED))

    def need(self, *vals):
        if not all(vals):
            messagebox.showwarning("Missing information", "Please fill in all the fields above.")
            return False
        return True


# ------------------------------------------------------------------ tools
class ReadTool(Tool):
    title = "Read"
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
        top = ctk.CTkFrame(b, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        ctk.CTkButton(top, text="Open PDF…", width=100, height=32, corner_radius=9, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, command=self.open_dialog).pack(side="left")
        self.name = ctk.CTkLabel(top, text="No file open — or drop a PDF here", text_color=MUTED, anchor="w")
        self.name.pack(side="left", padx=12)
        bar = ctk.CTkFrame(b, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(2, 8))
        small = dict(width=34, height=30, corner_radius=8, fg_color=FIELD, hover_color=("gray82", "gray30"),
                     text_color=("gray15", "gray90"))
        ctk.CTkButton(bar, text="◀", command=lambda: self.go(self.page - 1), **small).pack(side="left")
        self.pg_var = tk.StringVar(value="1")
        e = ctk.CTkEntry(bar, textvariable=self.pg_var, width=52, height=30, justify="center",
                         fg_color=FIELD, border_width=0)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self._goto_entry())
        self.total = ctk.CTkLabel(bar, text="/ 0", width=44)
        self.total.pack(side="left")
        ctk.CTkButton(bar, text="▶", command=lambda: self.go(self.page + 1), **small).pack(side="left")
        ctk.CTkButton(bar, text="−", command=lambda: self.set_zoom(self.zoom / 1.2), **small).pack(
            side="left", padx=(14, 0))
        ctk.CTkButton(bar, text="+", command=lambda: self.set_zoom(self.zoom * 1.2), **small).pack(
            side="left", padx=4)
        ctk.CTkButton(bar, text="Fit", command=self.fit_width, **small).pack(side="left")
        self.q = tk.StringVar()
        s = ctk.CTkEntry(bar, textvariable=self.q, placeholder_text="Search (Farsi OK)", height=30,
                         width=170, fg_color=FIELD, border_width=0)
        s.pack(side="left", padx=(14, 4))
        s.bind("<Return>", lambda _e: self.find(1))
        ctk.CTkButton(bar, text="Find", command=lambda: self.find(1), **small).pack(side="left")
        self.hit_lbl = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.hit_lbl.pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Copy text", width=84, height=30, corner_radius=8, fg_color=FIELD,
                      hover_color=("gray82", "gray30"), text_color=("gray15", "gray90"),
                      command=self.copy_text).pack(side="right")
        holder = ctk.CTkFrame(b, fg_color=FIELD, corner_radius=10)
        holder.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self.cv = tk.Canvas(holder, highlightthickness=0, bd=0)
        self.cv.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        vs = ctk.CTkScrollbar(holder, command=self.cv.yview)
        vs.grid(row=0, column=1, sticky="ns")
        hs = ctk.CTkScrollbar(holder, orientation="horizontal", command=self.cv.xview)
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
        self.recolor()

    def recolor(self):
        self.cv.configure(bg="#272c38" if ctk.get_appearance_mode() == "Dark" else "#e4e6f0")

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
            return messagebox.showerror("Cannot open", str(e))
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
        if self.fit and self.reader:
            if self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(150, self.fit_width)

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
            self.hit_lbl.configure(text=f"{n} match(es) here" if n else "none on this page")

    def find(self, step):
        if not self.reader or not self.q.get().strip():
            return
        if not self.hits or self._last_q != self.q.get():
            self._last_q = self.q.get()
            self.hits = self.reader.search(self.q.get())
        if not self.hits:
            self.hit_lbl.configure(text="not found")
            return
        later = [p for p in self.hits if p > self.page]
        target = later[0] if later else self.hits[0]
        self.go(target)
        self.hit_lbl.configure(text=f"page {target + 1}  ({self.hits.index(target) + 1}/{len(self.hits)})")

    def copy_text(self):
        if not self.reader:
            return
        self.clipboard_clear()
        self.clipboard_append(self.reader.text(self.page))
        self.app.toast("Page text copied")

    def _wheel(self, e):
        self.cv.yview_scroll(int(-e.delta / 120) * 3, "units")


class SplitTool(Tool):
    title, subtitle = "Split PDF", "Cut a PDF into several smaller files."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.info = ctk.CTkLabel(self.body, text="", anchor="w")
        self.add(self.info)
        self.mode = self.option_row("Split by", [
            "Custom ranges (one file per range)", "Every N pages", "Into N equal parts",
            "Every page separately"])
        self.val = self.entry_row("Value", "1-5, 6-10", "e.g. 1-3, 5, 8-   or   10")
        self.note("Ranges: '1-3, 5, 8-' makes three files (pages 1-3, page 5, page 8 to the end). "
                  "For 'Every N pages' / 'Into N equal parts' type just the number.")
        self.button("Split PDF", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).parent))
        try:
            self.info.configure(text=f"   {core.page_count(p)} pages · {core.fmt_size(Path(p).stat().st_size)}")
        except Exception as e:
            self.info.configure(text=f"   Cannot open: {e}")

    def run(self):
        src, out, mode, val = self.src.get(), self.out.get(), self.mode.get(), self.val.get().strip()
        if not self.need(src, out):
            return

        def job(log, prog):
            n = core.page_count(src)
            if mode.startswith("Custom"):
                groups = core.parse_ranges(val, n)
            elif mode.startswith("Every N"):
                groups = core.groups_every_n(n, int(val))
            elif mode.startswith("Into"):
                groups = core.groups_into_parts(n, int(val))
            else:
                groups = core.groups_every_n(n, 1)
            files = core.split_pdf(src, out, groups, prog)
            log(f"✔ Created {len(files)} file(s)")
            return out
        self.app.run(job)


class MergeTool(Tool):
    title, subtitle = "Merge PDFs", "Combine several PDF files into one, in the order shown."

    def build(self):
        self.files = self.add(FileList(self.body, PDF, height=9))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.button("Merge PDFs", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if len(files) < 2 or not out:
            return messagebox.showwarning("Missing information", "Add at least two PDFs and choose where to save.")

        def job(log, prog):
            n = core.merge_pdfs(files, out, prog)
            log(f"✔ Merged {len(files)} files → {Path(out).name} ({n} pages)")
            return str(Path(out).parent)
        self.app.run(job)


class CompressTool(Tool):
    title, subtitle = "Compress PDF", "Make PDFs smaller by reducing image size and cleaning up the file."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.level = self.option_row("Level", list(core.COMPRESS_LEVELS), list(core.COMPRESS_LEVELS)[1])
        gs = core.find_gs()
        engines = (["Ghostscript (stronger)"] if gs else []) + ["Built-in"]
        self.engine = self.option_row("Engine", engines)
        self.note("Ghostscript is built in — it gives the strongest compression for scanned books."
                  if gs else "Ghostscript is not available in this build; using the built-in engine.")
        self.note("Saved as <name>_compressed.pdf. If a file can't be made smaller, the original is kept.")
        self.button("Compress", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).parent))

    def run(self):
        src, out, level = self.src.get(), self.out.get(), self.level.get()
        engine = "ghostscript" if self.engine.get().startswith("Ghost") else "builtin"
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
    title, subtitle = "Convert to PDF", "EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT, DOCX and more."

    def build(self):
        self.files = self.add(FileList(self.body, [("Supported", " ".join("*" + e for e in core.ALL_FORMATS)),
                                                   ("All files", "*.*")], height=4))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.size = self.option_row("Ebook page size", ["A5", "A4", "A6", "Letter"])
        self.font = self.option_row("Ebook font size", [str(i) for i in range(8, 21)], "11")
        self.note(core.supported_status() + "\nPersian / Arabic / Hebrew documents are shaped and laid "
                  "out right-to-left automatically.")
        self.button("Convert", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if not files or not out:
            return messagebox.showwarning("Missing information", "Add files and choose an output folder.")
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
    title, subtitle = "Images to PDF", "Pick several pictures, put them in order and turn them into one PDF."

    def build(self):
        ex = " ".join("*" + e for e in core.IMAGE_EXTS)
        self.files = self.add(FileList(self.body, [("Images", ex), ("All files", "*.*")], height=8))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.size = self.option_row("Page size", core.PAGE_SIZES, "A4")
        self.margin = self.option_row("Margin", ["None", "Small", "Normal"], "Small")
        self.button("Create PDF", self.run)

    def run(self):
        files, out = list(self.files.files), self.out.get()
        if not files or not out:
            return messagebox.showwarning("Missing information", "Add pictures and choose where to save.")
        size = self.size.get()
        margin = {"None": 0, "Small": 18, "Normal": 36}[self.margin.get()]

        def job(log, prog):
            n = core.images_to_pdf(files, out, size, margin, prog)
            log(f"✔ {n} picture(s) to {Path(out).name}")
            return str(Path(out).parent)
        self.app.run(job)


class PagesTool(Tool):
    title, subtitle = "Page tools", "Delete, extract, rotate or reverse pages."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.info = self.add(ctk.CTkLabel(self.body, text="", anchor="w"))
        self.action = self.option_row("Action", ["Delete pages", "Keep only (extract) pages",
                                                 "Rotate pages", "Reverse page order"])
        self.pages = self.entry_row("Pages", "1-3, 7", "e.g. 1-3, 7, 10-")
        self.angle = self.option_row("Rotate by", ["90° clockwise", "180°", "90° counter-clockwise"])
        self.button("Apply", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_edited.pdf")))
        try:
            self.info.configure(text=f"   {core.page_count(p)} pages")
        except Exception as e:
            self.info.configure(text=f"   Cannot open: {e}")

    def run(self):
        src, out, a = self.src.get(), self.out.get(), self.action.get()
        if not self.need(src, out):
            return
        if Path(src).resolve() == Path(out).resolve():
            return messagebox.showwarning("Choose another file", "Save to a different file than the original.")
        action = {"Del": "delete", "Kee": "keep", "Rot": "rotate", "Rev": "reverse"}[a[:3]]
        angle = {"90° c": 90, "180°": 180, "90° counter-clockwise": 270}.get(self.angle.get(), 90)
        spec = self.pages.get().strip()

        def job(log, prog):
            n = core.edit_pages(src, out, action, spec, angle)
            log(f"✔ Saved {Path(out).name} ({n} pages)")
            return str(Path(out).parent)
        self.app.run(job)


class OcrTool(Tool):
    title = "OCR — searchable PDF"
    subtitle = ("Turn scanned books and documents into PDFs whose text can be searched and copied. "
                "Persian (Farsi) and Arabic are fully supported.")

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        self.langs = lang_choices()
        names = list(self.langs) or ["English  (eng)"]
        self.lang = self.option_row("Language", names, names[0])
        self.eng = self.check_row("Also recognise English words (recommended for mixed text)", True)
        self.dpi = self.option_row("Scan quality", ["200 dpi (fast)", "300 dpi (recommended)", "400 dpi (small print)"],
                                   "300 dpi (recommended)")
        self.skip = self.check_row("Skip pages that already contain text", True)
        self.note("The original page images stay untouched — only an invisible text layer is added, "
                  "so the file keeps its quality." if self.langs else
                  "OCR engine is missing from this build.")
        self.button("Run OCR", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_ocr.pdf")))

    def run(self):
        src, out = self.src.get(), self.out.get()
        if not self.need(src, out):
            return
        lang = tess_lang(self.langs.get(self.lang.get(), "eng"), self.eng.get())
        dpi, skip = int(self.dpi.get().split()[0]), self.skip.get()

        def job(log, prog):
            n, total = core.ocr_pdf(src, out, lang, dpi, skip, 3, prog)
            log(f"✔ OCR finished: {n} of {total} pages → {Path(out).name}")
            return str(Path(out).parent)
        self.app.run(job)


class ExtractTool(Tool):
    title = "Extract text"
    subtitle = "Get the text out of a PDF as a clean .txt or Word file. Scanned pages are read with OCR."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.fmt = self.option_row("Format", ["Text file (.txt)", "Word document (.docx)"])
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
        fmt = "docx" if "docx" in self.fmt.get() else "txt"
        lang = (tess_lang(self.langs.get(self.lang.get(), "eng"), self.eng.get())
                if self.ocr.get() and self.langs else None)
        rev = self.rev.get()

        def job(log, prog):
            dst = core.unique_path(Path(out) / (Path(src).stem + "." + fmt))
            chars, ocr_pages = core.extract_text(src, str(dst), fmt, lang, rev, prog)
            extra = f", {ocr_pages} page(s) read with OCR" if ocr_pages else ""
            log(f"✔ {dst.name}: {chars:,} characters{extra}")
            if chars == 0:
                log("  (no text found — try enabling OCR)")
            return out
        self.app.run(job)


# ------------------------------------------------------------------ home
class HomeTool(Tool):
    title = "PDF Toolkit"
    subtitle = "Everything for your PDFs in one place — with first-class Persian (Farsi) support."

    CARDS = [("📖", "Read", "Open and search PDFs, including Farsi"),
             ("🔍", "OCR", "Make scanned books searchable (Farsi, Arabic…)"),
             ("📝", "Extract text", "PDF to clean TXT / Word, with OCR"),
             ("⇄", "Convert to PDF", "EPUB, DjVu, DOCX, MOBI, TXT, HTML…"),
             ("✂", "Split", "Cut a PDF into parts or ranges"),
             ("⧉", "Merge", "Join PDFs in any order"),
             ("🗜", "Compress", "Four levels, up to Ghostscript power"),
             ("🖼", "Images to PDF", "Many pictures into one PDF"),
             ("☰", "Page tools", "Delete, extract, rotate, reverse")]

    def build(self):
        self.body.configure(fg_color="transparent")
        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        grid.grid(row=0, column=0, sticky="nsew")
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="c")
        for i, (icon, name, desc) in enumerate(self.CARDS):
            card = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=16, height=118)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(FONT, 26), text_color=ACCENT).place(x=16, y=12)
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(FONT, 15, "bold"), anchor="w").place(x=16, y=52)
            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(FONT, 11), text_color=MUTED, anchor="w",
                         justify="left", wraplength=190).place(x=16, y=76)
            target = next(n for n, _ in App.TOOLS if n.split(None, 1)[-1].strip() == name)

            def enter(_e, c=card): c.configure(fg_color=CARD_HOVER)
            def leave(_e, c=card): c.configure(fg_color=CARD)
            def click(_e, t=target): self.app.show(t)
            for w in [card, *card.winfo_children()]:
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)
                w.bind("<Button-1>", click)
                try:
                    w.configure(cursor="hand2")
                except Exception:
                    pass
        chips = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=16)
        chips.grid(row=1, column=0, sticky="ew", padx=6, pady=(10, 0))
        langs = core.ocr_languages()
        status = [("Persian OCR", "fas" in langs), ("Arabic OCR", "ara" in langs),
                  ("DjVu", bool(core.find_ddjvu())), ("DOCX / ODT / RTF", bool(core.find_pandoc())),
                  ("Ghostscript", bool(core.find_gs()))]
        for j, (n, ok) in enumerate(status):
            ctk.CTkLabel(chips, text=("●  " if ok else "○  ") + n, font=ctk.CTkFont(FONT, 12),
                         text_color=("#15803d", "#4ade80") if ok else MUTED).grid(
                row=0, column=j, padx=14, pady=12)
        ctk.CTkLabel(self.body, text="Tip: drag & drop files onto the window to use them in the open tool.",
                     text_color=MUTED, anchor="w").grid(row=2, column=0, sticky="w", padx=8, pady=(10, 0))


# ------------------------------------------------------------------ app
_Base = type("_Base", (ctk.CTk, TkinterDnD.DnDWrapper), {}) if HAS_DND else ctk.CTk


class App(_Base):
    TOOLS = [("⌂  Home", HomeTool), ("📖  Read", ReadTool), ("🔍  OCR", OcrTool),
             ("📝  Extract text", ExtractTool), ("⇄  Convert to PDF", ConvertTool),
             ("✂  Split", SplitTool), ("⧉  Merge", MergeTool), ("🗜  Compress", CompressTool),
             ("🖼  Images to PDF", ImagesTool), ("☰  Page tools", PagesTool)]

    def __init__(self):
        super().__init__()
        self.dnd = False
        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd = True
            except Exception:
                self.dnd = False
        self.title("PDF Toolkit")
        self.geometry("1120x820")
        self.minsize(1000, 740)
        self.q: queue.Queue = queue.Queue()
        self.busy, self.last_dir = False, None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.configure(fg_color=BG)
        if sys.platform == "win32":
            try:
                self.iconbitmap(str(core._app_dir() / "icon.ico"))
            except Exception:
                pass

        side = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=SIDEBAR)
        side.grid(row=0, column=0, rowspan=2, sticky="ns")
        side.grid_propagate(False)
        logo = ctk.CTkFrame(side, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(26, 18))
        ctk.CTkLabel(logo, text="PDF", width=40, height=40, corner_radius=11, fg_color=ACCENT,
                     text_color="white", font=ctk.CTkFont(FONT, 14, "bold")).pack(side="left")
        ctk.CTkLabel(logo, text="Toolkit", font=ctk.CTkFont(FONT, 21, "bold")).pack(side="left", padx=10)
        self.nav = {}
        for name, cls in self.TOOLS:
            b = ctk.CTkButton(side, text=name, anchor="w", height=40, corner_radius=11,
                              fg_color="transparent", text_color=("gray20", "gray88"),
                              hover_color=("#eceef7", "#262b38"), font=ctk.CTkFont(FONT, 14),
                              command=lambda n=name: self.show(n))
            b.pack(fill="x", padx=14, pady=1)
            self.nav[name] = b
        self.theme = ctk.CTkSwitch(side, text="Dark mode", command=self._toggle_theme,
                                   progress_color=ACCENT, font=ctk.CTkFont(FONT, 13))
        self.theme.pack(side="bottom", padx=22, pady=22, anchor="w")
        self.theme.select() if ctk.get_appearance_mode() == "Dark" else self.theme.deselect()

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew", padx=28, pady=(24, 8))
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.pages, self.current = {}, None

        foot = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        foot.grid(row=1, column=1, sticky="ew", padx=28, pady=(0, 20))
        foot.columnconfigure(0, weight=1)
        self.bar = ctk.CTkProgressBar(foot, progress_color=ACCENT, height=8, fg_color=FIELD)
        self.bar.set(0)
        self.bar.grid(row=0, column=0, sticky="ew", padx=(18, 8), pady=(16, 0))
        self.open_btn = ctk.CTkButton(foot, text="Open folder", width=110, height=28, corner_radius=9,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                      state="disabled", command=self.open_folder)
        self.open_btn.grid(row=0, column=1, padx=(0, 18), pady=(12, 0))
        self.log = ctk.CTkTextbox(foot, height=80, state="disabled", fg_color=FIELD, corner_radius=10,
                                  font=ctk.CTkFont(FONT, 12))
        self.log.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 16))
        self.toast_lbl = ctk.CTkLabel(self, text="", fg_color=ACCENT, text_color="white", corner_radius=10,
                                      font=ctk.CTkFont(FONT, 12))
        self.show(self.TOOLS[0][0])
        self.after(100, self._poll)
        self.after(300, self._prebuild)

    def toast(self, text):
        self.toast_lbl.configure(text="  " + text + "  ")
        self.toast_lbl.place(relx=0.5, rely=0.03, anchor="n")
        self.after(1600, self.toast_lbl.place_forget)

    def _page(self, name):
        if name not in self.pages:
            self.pages[name] = dict(self.TOOLS)[name](self)
        return self.pages[name]

    def _prebuild(self):
        """Build the remaining pages while idle (hidden), one per tick, so tab switches are instant."""
        for name, _ in self.TOOLS:
            if name not in self.pages:
                self._page(name)
                self.after(60, self._prebuild)
                return

    def show(self, name):
        if self.current == name:
            return
        if self.current:
            self.pages[self.current].grid_remove()  # hidden pages take no part in resize/layout
        page = self._page(name)
        page.grid(row=0, column=0, sticky="nsew")
        self.current = name
        for n, b in self.nav.items():
            b.configure(fg_color=ACCENT if n == name else "transparent",
                        hover_color=ACCENT_HOVER if n == name else ("#eceef7", "#262b38"),
                        text_color="white" if n == name else ("gray20", "gray88"))

    def _toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme.get() else "light")

        def recolor():
            for p in self.pages.values():
                for w in p.body.winfo_children():
                    if isinstance(w, FileList):
                        w.recolor()
                if isinstance(p, ReadTool):
                    p.recolor()
        self.after(50, recolor)

    # ---- background jobs
    def run(self, job):
        if self.busy:
            return
        self.busy = True
        self.bar.set(0)
        self.open_btn.configure(state="disabled")

        def wrap():
            try:
                self.q.put(("dir", job(lambda m: self.q.put(("log", m)),
                                       lambda i, t: self.q.put(("prog", i / max(t, 1))))))
            except Exception as e:
                self.q.put(("log", f"✘ Error: {e}"))
            self.q.put(("done",))
        threading.Thread(target=wrap, daemon=True).start()

    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", m[1] + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif m[0] == "prog":
                    self.bar.set(m[1])
                elif m[0] == "dir" and m[1]:
                    self.last_dir = m[1]
                    self.open_btn.configure(state="normal")
                elif m[0] == "done":
                    self.busy = False
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
    ctk.set_appearance_mode("system")
    App().mainloop()
