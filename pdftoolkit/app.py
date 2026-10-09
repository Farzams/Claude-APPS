"""PDF Toolkit - split, merge, compress, convert, images->PDF, page tools, OCR."""
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

ctk.set_default_color_theme("blue")
ACCENT = ("#4f46e5", "#6366f1")
ACCENT_HOVER = ("#4338ca", "#818cf8")
BG = ("#f3f4f9", "#12141a")
SIDEBAR = ("#ffffff", "#191c24")
CARD = ("#ffffff", "#1d212b")
FIELD = ("#f1f2f8", "#272c38")
MUTED = ("gray40", "gray62")
FONT = "Segoe UI"


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
        for text, cmd in [("＋ Add files", self.add), ("▲ Up", lambda: self.move(-1)),
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
                          selectbackground="#6366f1" if dark else "#4f46e5", selectforeground="white",
                          highlightthickness=0)

    def add(self):
        for p in filedialog.askopenfilenames(filetypes=self.types):
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
    """Base page: title, subtitle, content grid, run button."""

    title, subtitle = "", ""

    def __init__(self, app):
        super().__init__(app.main, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=self.title, font=ctk.CTkFont(FONT, 26, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(self, text=self.subtitle, anchor="w", justify="left", wraplength=640,
                     font=ctk.CTkFont(FONT, 13), text_color=MUTED).grid(
            row=1, column=0, sticky="ew", pady=(0, 14))
        self.body = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.build()

    def build(self): ...

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

    def note(self, text):
        self.add(ctk.CTkLabel(self.body, text=text, anchor="w", justify="left", wraplength=620,
                              text_color=MUTED))

    def need(self, *vals):
        if not all(vals):
            messagebox.showwarning("Missing information", "Please fill in all the fields above.")
            return False
        return True


# ------------------------------------------------------------------ tools
PDF = [("PDF files", "*.pdf")]
LANG_NAMES = {"eng": "English", "fas": "Persian (Farsi)", "ara": "Arabic", "deu": "German",
              "fra": "French", "spa": "Spanish", "ita": "Italian", "rus": "Russian",
              "tur": "Turkish", "nld": "Dutch", "por": "Portuguese", "heb": "Hebrew",
              "ell": "Greek", "chi_sim": "Chinese (Simplified)", "jpn": "Japanese", "kor": "Korean"}


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
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=lambda p: (
            None if self.out.get() else self.out.var.set(str(Path(p).parent)))))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.level = self.option_row("Level", list(core.COMPRESS_LEVELS), list(core.COMPRESS_LEVELS)[1])
        gs = core.find_gs()
        engines = (["Ghostscript (stronger)"] if gs else []) + ["Built-in"]
        self.engine = self.option_row("Engine", engines)
        self.note("Ghostscript is built in — it gives the strongest compression for scanned books."
                  if gs else "Ghostscript is not available in this build; using the built-in engine.")
        self.note("Saved as <name>_compressed.pdf. If a file can't be made smaller, the original is kept.")
        self.button("Compress", self.run)

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
        self.note(core.supported_status() + "\nEverything else works out of the box.")
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
    title, subtitle = "OCR (searchable PDF)", "Turn scanned pages into a PDF whose text can be searched and copied."

    def build(self):
        self.src = self.add(FileRow(self.body, "PDF file", types=PDF, on_pick=self._picked))
        self.out = self.add(FileRow(self.body, "Save as", kind="save", types=PDF))
        codes = core.ocr_languages()
        self.lang_map = {f"{LANG_NAMES.get(c, c)} ({c})": c for c in codes}
        names = list(self.lang_map) or ["English (eng)"]
        self.lang = self.option_row("Language", names, next((n for n in names if n.endswith("(eng)")), None))
        self.dpi = self.option_row("Scan quality", ["150 dpi (fast)", "200 dpi", "300 dpi (best)"], "200 dpi")
        self.note("OCR is built in. Pick the language of the scanned text."
                  if codes else "OCR language data is missing from this build.")
        self.button("Run OCR", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_ocr.pdf")))

    def run(self):
        src, out = self.src.get(), self.out.get()
        lang = self.lang_map.get(self.lang.get(), "eng")
        dpi = int(self.dpi.get().split()[0])
        if not self.need(src, out):
            return

        def job(log, prog):
            n = core.ocr_pdf(src, out, lang, dpi, prog)
            log(f"✔ OCR finished: {n} pages → {Path(out).name}")
            return str(Path(out).parent)
        self.app.run(job)


# ------------------------------------------------------------------ app
class App(ctk.CTk):
    TOOLS = [("✂  Split", SplitTool), ("⧉  Merge", MergeTool), ("🗜  Compress", CompressTool),
             ("⇄  Convert to PDF", ConvertTool), ("🖼  Images to PDF", ImagesTool),
             ("☰  Page tools", PagesTool), ("🔍  OCR", OcrTool)]

    def __init__(self):
        super().__init__()
        self.title("PDF Toolkit")
        self.geometry("1080x800")
        self.minsize(980, 720)
        self.q: queue.Queue = queue.Queue()
        self.busy, self.last_dir = False, None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.configure(fg_color=BG)
        if sys.platform == "win32":
            try:
                self.iconbitmap(str(Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "icon.ico"))
            except Exception:
                pass
        side = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=SIDEBAR)
        side.grid(row=0, column=0, rowspan=2, sticky="ns")
        side.grid_propagate(False)
        logo = ctk.CTkFrame(side, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(26, 22))
        ctk.CTkLabel(logo, text="PDF", width=40, height=40, corner_radius=11, fg_color=ACCENT,
                     text_color="white", font=ctk.CTkFont(FONT, 14, "bold")).pack(side="left")
        ctk.CTkLabel(logo, text="Toolkit", font=ctk.CTkFont(FONT, 21, "bold")).pack(side="left", padx=10)
        self.nav = {}
        for name, cls in self.TOOLS:
            b = ctk.CTkButton(side, text=name, anchor="w", height=42, corner_radius=11,
                              fg_color="transparent", text_color=("gray20", "gray88"),
                              hover_color=("#eceef7", "#262b38"), font=ctk.CTkFont(FONT, 14),
                              command=lambda n=name: self.show(n))
            b.pack(fill="x", padx=14, pady=2)
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
        self.log = ctk.CTkTextbox(foot, height=90, state="disabled", fg_color=FIELD, corner_radius=10,
                                  font=ctk.CTkFont(FONT, 12))
        self.log.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 16))
        self.show(self.TOOLS[0][0])
        self.after(100, self._poll)
        self.after(300, self._prebuild)

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
        self.after(50, lambda: [w.recolor() for p in self.pages.values()
                                for w in p.body.winfo_children() if isinstance(w, FileList)])

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
