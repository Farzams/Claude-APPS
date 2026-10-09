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
ACCENT = ("#2563eb", "#3b82f6")


# ------------------------------------------------------------------ widgets
class FileRow(ctk.CTkFrame):
    """Label + entry + browse button (file or folder)."""

    def __init__(self, master, label, kind="open", types=None, on_pick=None, save_ext=".pdf"):
        super().__init__(master, fg_color="transparent")
        self.kind, self.types, self.on_pick, self.save_ext = kind, types, on_pick, save_ext
        self.var = tk.StringVar()
        self.columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=label, width=110, anchor="w").grid(row=0, column=0)
        ctk.CTkEntry(self, textvariable=self.var).grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkButton(self, text="Browse…", width=90, command=self._browse).grid(row=0, column=2)

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
                             highlightthickness=1, activestyle="none", font=("Segoe UI", 10))
        self.lb.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(self, command=self.lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.lb.configure(yscrollcommand=sb.set)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for text, cmd in [("＋ Add files", self.add), ("▲ Up", lambda: self.move(-1)),
                          ("▼ Down", lambda: self.move(1)), ("Remove", self.remove),
                          ("Clear", self.clear)]:
            ctk.CTkButton(bar, text=text, width=84, height=28, command=cmd,
                          fg_color=ACCENT if text.startswith("＋") else ("gray70", "gray30"),
                          text_color=("white" if text.startswith("＋") else ("black", "white"))
                          ).pack(side="left", padx=(0, 6))
        self.count = ctk.CTkLabel(bar, text="0 files")
        self.count.pack(side="right")
        self.recolor()

    def recolor(self):
        dark = ctk.get_appearance_mode() == "Dark"
        self.lb.configure(bg="#1f1f23" if dark else "#ffffff", fg="#e5e5e5" if dark else "#111111",
                          selectbackground="#2563eb", selectforeground="white",
                          highlightbackground="#3a3a40" if dark else "#c9c9cf")

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
        ctk.CTkLabel(self, text=self.title, font=ctk.CTkFont(size=24, weight="bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(self, text=self.subtitle, anchor="w", justify="left", wraplength=620,
                     text_color=("gray35", "gray65")).grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.build()

    def build(self): ...

    def add(self, widget, **kw):
        widget.grid(row=self.body.grid_size()[1], column=0, sticky="ew", pady=kw.pop("pady", 5), **kw)
        return widget

    def button(self, text, cmd):
        b = ctk.CTkButton(self.body, text=text, height=40, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=ACCENT, command=cmd)
        self.add(b, pady=(16, 0))
        return b

    def entry_row(self, label, default="", hint=""):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        f.columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=label, width=110, anchor="w").grid(row=0, column=0)
        var = tk.StringVar(value=default)
        ctk.CTkEntry(f, textvariable=var, placeholder_text=hint).grid(row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def option_row(self, label, values, default=None):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        f.columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=label, width=110, anchor="w").grid(row=0, column=0)
        var = tk.StringVar(value=default or values[0])
        ctk.CTkOptionMenu(f, variable=var, values=values, fg_color=ACCENT).grid(
            row=0, column=1, sticky="ew", padx=8)
        self.add(f)
        return var

    def note(self, text):
        self.add(ctk.CTkLabel(self.body, text=text, anchor="w", justify="left", wraplength=620,
                              text_color=("gray35", "gray65")))

    def need(self, *vals):
        if not all(vals):
            messagebox.showwarning("Missing information", "Please fill in all the fields above.")
            return False
        return True


# ------------------------------------------------------------------ tools
PDF = [("PDF files", "*.pdf")]


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
        engines = ["Built-in"] + (["Ghostscript (stronger)"] if gs else [])
        self.engine = self.option_row("Engine", engines)
        self.note("Ghostscript detected — pick it for stronger compression of scanned books."
                  if gs else
                  "Tip: install Ghostscript (ghostscript.com) to unlock a stronger compression engine.")
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
                                                   ("All files", "*.*")], height=6))
        self.out = self.add(FileRow(self.body, "Output folder", kind="dir"))
        self.size = self.option_row("Ebook page size", ["A5", "A4", "A6", "Letter"])
        self.font = self.option_row("Ebook font size", [str(i) for i in range(8, 21)], "11")
        self.note(core.supported_status() + "\nEPUB/MOBI/FB2/XPS/CBZ/HTML/TXT work out of the box. "
                  "DjVu needs DjVuLibre; DOCX/AZW3/RTF/ODT need Calibre.")
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
    title, subtitle = "Images → PDF", "Pick several pictures, put them in order and turn them into one PDF."

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
            log(f"✔ {n} picture(s) → {Path(out).name}")
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
        langs = core.ocr_languages()
        self.lang = self.option_row("Language", langs or ["eng"], "eng" if "eng" in langs else None)
        self.dpi = self.option_row("Scan quality", ["150 dpi (fast)", "200 dpi", "300 dpi (best)"], "200 dpi")
        self.note("OCR is available (Tesseract found)." if langs else
                  "Tesseract OCR not found. Install it from github.com/UB-Mannheim/tesseract/wiki "
                  "(tick extra languages in the installer) and restart the app.")
        self.button("Run OCR", self.run)

    def _picked(self, p):
        if not self.out.get():
            self.out.var.set(str(Path(p).with_name(Path(p).stem + "_ocr.pdf")))

    def run(self):
        src, out, lang = self.src.get(), self.out.get(), self.lang.get()
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
             ("⇄  Convert to PDF", ConvertTool), ("🖼  Images → PDF", ImagesTool),
             ("☰  Page tools", PagesTool), ("🔍  OCR", OcrTool)]

    def __init__(self):
        super().__init__()
        self.title("PDF Toolkit")
        self.geometry("1020x720")
        self.minsize(900, 620)
        self.q: queue.Queue = queue.Queue()
        self.busy, self.last_dir = False, None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=210, corner_radius=0)
        side.grid(row=0, column=0, rowspan=2, sticky="ns")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="PDF Toolkit", font=ctk.CTkFont(size=22, weight="bold")).pack(
            padx=20, pady=(24, 18), anchor="w")
        self.nav = {}
        for name, cls in self.TOOLS:
            b = ctk.CTkButton(side, text=name, anchor="w", height=38, corner_radius=8,
                              fg_color="transparent", text_color=("gray10", "gray90"),
                              hover_color=("gray75", "gray25"), font=ctk.CTkFont(size=14),
                              command=lambda n=name: self.show(n))
            b.pack(fill="x", padx=12, pady=2)
            self.nav[name] = b
        self.theme = ctk.CTkSwitch(side, text="Dark mode", command=self._toggle_theme)
        self.theme.pack(side="bottom", padx=20, pady=20, anchor="w")
        self.theme.select() if ctk.get_appearance_mode() == "Dark" else self.theme.deselect()

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 8))
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.pages = {}
        for name, cls in self.TOOLS:
            p = cls(self)
            p.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = p

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=1, column=1, sticky="ew", padx=24, pady=(0, 16))
        foot.columnconfigure(0, weight=1)
        self.bar = ctk.CTkProgressBar(foot)
        self.bar.set(0)
        self.bar.grid(row=0, column=0, sticky="ew")
        self.open_btn = ctk.CTkButton(foot, text="Open folder", width=110, height=26,
                                      state="disabled", command=self.open_folder)
        self.open_btn.grid(row=0, column=1, padx=(10, 0))
        self.log = ctk.CTkTextbox(foot, height=110, state="disabled")
        self.log.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.show(self.TOOLS[0][0])
        self.after(100, self._poll)

    def show(self, name):
        self.pages[name].tkraise()
        for n, b in self.nav.items():
            b.configure(fg_color=ACCENT if n == name else "transparent",
                        text_color="white" if n == name else ("gray10", "gray90"))

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
