"""PDF Toolkit - split, compress and convert to PDF (Windows/any, tkinter GUI)."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import core


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Toolkit")
        self.geometry("720x560")
        self.minsize(640, 500)
        self.q: queue.Queue = queue.Queue()
        self.busy = False

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self._build_split(nb)
        self._build_compress(nb)
        self._build_convert(nb)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=8, pady=(6, 0))
        self.log = tk.Text(self, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", padx=8, pady=8)
        self.after(100, self._poll)

    # ------------------------------------------------------------ widgets
    def _row_file(self, parent, label, var, command, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=6)
        ttk.Button(parent, text="Browse…", command=command).grid(row=row, column=2)

    def _build_split(self, nb):
        f = ttk.Frame(nb, padding=12)
        f.columnconfigure(1, weight=1)
        nb.add(f, text="Split PDF")
        self.sp_src, self.sp_out = tk.StringVar(), tk.StringVar()
        self.sp_mode = tk.StringVar(value="ranges")
        self.sp_val = tk.StringVar(value="1-5, 6-10")
        self._row_file(f, "PDF file:", self.sp_src, self._sp_pick, 0)
        self._row_file(f, "Output folder:", self.sp_out, lambda: self._pick_dir(self.sp_out), 1)
        self.sp_info = ttk.Label(f, text="")
        self.sp_info.grid(row=2, column=1, sticky="w", padx=6)
        box = ttk.LabelFrame(f, text="How to split", padding=8)
        box.grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)
        box.columnconfigure(1, weight=1)
        opts = [("ranges", "Custom ranges (e.g. 1-3, 5, 8-)  — one file per range"),
                ("every", "Every N pages (enter N)"),
                ("parts", "Into N equal parts (enter N)"),
                ("single", "Every page as its own file")]
        for i, (v, t) in enumerate(opts):
            ttk.Radiobutton(box, text=t, value=v, variable=self.sp_mode).grid(
                row=i, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="Value:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(box, textvariable=self.sp_val).grid(row=4, column=1, sticky="ew", padx=6, pady=(8, 0))
        ttk.Button(f, text="Split", command=self._do_split).grid(row=4, column=0, columnspan=3, pady=6)

    def _build_compress(self, nb):
        f = ttk.Frame(nb, padding=12)
        f.columnconfigure(1, weight=1)
        nb.add(f, text="Compress PDF")
        self.cp_src, self.cp_out = tk.StringVar(), tk.StringVar()
        self.cp_level = tk.StringVar(value=list(core.COMPRESS_LEVELS)[1])
        self._row_file(f, "PDF file:", self.cp_src, lambda: self._pick_pdf(self.cp_src, self.cp_out), 0)
        self._row_file(f, "Output folder:", self.cp_out, lambda: self._pick_dir(self.cp_out), 1)
        ttk.Label(f, text="Level:").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Combobox(f, textvariable=self.cp_level, values=list(core.COMPRESS_LEVELS),
                     state="readonly").grid(row=2, column=1, columnspan=2, sticky="ew", padx=6)
        ttk.Label(f, text="Output is saved as <name>_compressed.pdf. If compression cannot "
                          "shrink the file, the original is kept.", wraplength=620).grid(
            row=3, column=0, columnspan=3, sticky="w")
        ttk.Button(f, text="Compress", command=self._do_compress).grid(row=4, column=0, columnspan=3, pady=14)

    def _build_convert(self, nb):
        f = ttk.Frame(nb, padding=12)
        f.columnconfigure(1, weight=1)
        nb.add(f, text="Convert to PDF")
        self.cv_files: list[str] = []
        self.cv_out = tk.StringVar()
        self.cv_size = tk.StringVar(value="a5")
        self.cv_font = tk.IntVar(value=11)
        ttk.Button(f, text="Add files…", command=self._cv_add).grid(row=0, column=0, sticky="w")
        ttk.Button(f, text="Clear", command=self._cv_clear).grid(row=0, column=1, sticky="w", padx=6)
        self.cv_list = tk.Listbox(f, height=6)
        self.cv_list.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=6)
        f.rowconfigure(1, weight=1)
        self._row_file(f, "Output folder:", self.cv_out, lambda: self._pick_dir(self.cv_out), 2)
        opt = ttk.Frame(f)
        opt.grid(row=3, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Label(opt, text="Ebook page size:").pack(side="left")
        ttk.Combobox(opt, textvariable=self.cv_size, width=8, state="readonly",
                     values=["a4", "a5", "a6", "letter"]).pack(side="left", padx=6)
        ttk.Label(opt, text="Font size:").pack(side="left", padx=(12, 0))
        ttk.Spinbox(opt, from_=7, to=24, textvariable=self.cv_font, width=4).pack(side="left", padx=6)
        ttk.Label(f, text=core.supported_status(), foreground="#555").grid(
            row=4, column=0, columnspan=3, sticky="w")
        ttk.Label(f, text="EPUB, MOBI, FB2, XPS, CBZ, HTML, TXT, images work out of the box. "
                          "DjVu needs DjVuLibre; DOCX/AZW3/RTF etc. need Calibre.",
                  wraplength=620).grid(row=5, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Button(f, text="Convert", command=self._do_convert).grid(row=6, column=0, columnspan=3, pady=6)

    # ------------------------------------------------------------ pickers
    def _pick_dir(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)

    def _pick_pdf(self, var, outvar):
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if p:
            var.set(p)
            if not outvar.get():
                outvar.set(str(Path(p).parent))
        return p

    def _sp_pick(self):
        p = self._pick_pdf(self.sp_src, self.sp_out)
        if p:
            try:
                self.sp_info.config(text=f"{core.page_count(p)} pages, {core.fmt_size(Path(p).stat().st_size)}")
            except Exception as e:
                self.sp_info.config(text=f"Cannot open: {e}")

    def _cv_add(self):
        exts = " ".join("*" + e for e in core.ALL_FORMATS)
        for p in filedialog.askopenfilenames(filetypes=[("Supported", exts), ("All", "*.*")]):
            if p not in self.cv_files:
                self.cv_files.append(p)
                self.cv_list.insert("end", p)
                if not self.cv_out.get():
                    self.cv_out.set(str(Path(p).parent))

    def _cv_clear(self):
        self.cv_files.clear()
        self.cv_list.delete(0, "end")

    # ------------------------------------------------------------ actions
    def _do_split(self):
        src, out = self.sp_src.get(), self.sp_out.get()
        if not src or not out:
            return messagebox.showwarning("Missing", "Choose a PDF and an output folder.")
        mode, val = self.sp_mode.get(), self.sp_val.get().strip()

        def job():
            n = core.page_count(src)
            if mode == "ranges":
                groups = core.parse_ranges(val, n)
            elif mode == "every":
                groups = core.groups_every_n(n, int(val))
            elif mode == "parts":
                groups = core.groups_into_parts(n, int(val))
            else:
                groups = core.groups_every_n(n, 1)
            files = core.split_pdf(src, out, groups, lambda i, t: self.q.put(("prog", i, t)))
            self.q.put(("log", f"Created {len(files)} file(s) in {out}"))
        self._run(job)

    def _do_compress(self):
        src, out = self.cp_src.get(), self.cp_out.get()
        if not src or not out:
            return messagebox.showwarning("Missing", "Choose a PDF and an output folder.")
        level = self.cp_level.get()

        def job():
            self.q.put(("prog", 0, 1))
            dst = core.unique_path(Path(out) / (Path(src).stem + "_compressed.pdf"))
            a, b = core.compress_pdf(src, str(dst), level)
            saved = (1 - b / a) * 100 if a else 0
            self.q.put(("prog", 1, 1))
            self.q.put(("log", f"{dst.name}: {core.fmt_size(a)} -> {core.fmt_size(b)} (-{saved:.1f}%)"))
        self._run(job)

    def _do_convert(self):
        if not self.cv_files or not self.cv_out.get():
            return messagebox.showwarning("Missing", "Add files and choose an output folder.")
        files, out = list(self.cv_files), self.cv_out.get()
        size, font = self.cv_size.get(), self.cv_font.get()

        def job():
            for i, f in enumerate(files, 1):
                try:
                    p = core.convert_to_pdf(f, out, size, font)
                    self.q.put(("log", f"OK  {Path(f).name} -> {p.name}"))
                except Exception as e:
                    self.q.put(("log", f"FAIL {Path(f).name}: {e}"))
                self.q.put(("prog", i, len(files)))
        self._run(job)

    # ------------------------------------------------------------ threading
    def _run(self, fn):
        if self.busy:
            return
        self.busy = True
        self.progress["value"] = 0

        def wrap():
            try:
                fn()
            except Exception as e:
                self.q.put(("log", f"ERROR: {e}"))
            self.q.put(("done",))
        threading.Thread(target=wrap, daemon=True).start()

    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "log":
                    self.log.config(state="normal")
                    self.log.insert("end", m[1] + "\n")
                    self.log.see("end")
                    self.log.config(state="disabled")
                elif m[0] == "prog":
                    self.progress["value"] = 100 * m[1] / max(m[2], 1)
                elif m[0] == "done":
                    self.busy = False
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    App().mainloop()
