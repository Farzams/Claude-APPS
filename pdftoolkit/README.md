# PDF Toolkit

Split, merge, compress, convert (EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT), images to PDF, page tools and more.

The Windows build bundles everything, so nothing else needs installing:
- **DjVuLibre** (`ddjvu`, GPL-2.0, https://djvu.sourceforge.net) – DjVu conversion
- **Ghostscript** (AGPL-3.0, https://ghostscript.com) – strong PDF compression
- **Noto Sans Arabic** (SIL OFL 1.1), **Vazirmatn**, **Inter** and **DejaVu Sans** fonts in `fonts/` – interface and Persian/Arabic page rendering

Each tool runs as a separate, unmodified program. Calibre is optional and only needed for legacy `.doc`, `.lit`, `.pdb`, `.cbr`.

## Persian (Farsi) support
- Converting EPUB/FB2/TXT/HTML to PDF shapes letters, lays text out right-to-left and keeps headings as bookmarks
- Text files in UTF-8, UTF-16 or Windows-1256 are read correctly

## Interface
- Built with **Qt (PySide6, LGPL)**: native speed, correct Persian shaping and right-to-left layout
- English and Persian interface; Help section in both languages
- 13 colour themes (Quiet Light/Dark, Paper, Paper Night and 9 classic ones), accent colours, four icon styles, text size, Persian font choice
- Ctrl+K search box for every tool and setting; Home page with the common jobs
- Settings are stored in `%APPDATA%\PDFToolkit\settings.json`

## Tools
- **Organize pages** (drag & drop thumbnails, rotate, delete, duplicate, insert, undo), **Crop**, **Delete blank pages**, **Header/footer/Bates**, **Watermark**, **Page background**, **Split**, **Merge**, **Compress**, **Images to PDF**, **Page tools**
- **PDF to** pictures / Word / Excel / HTML / text, **Password & permissions** (AES-256), **Remove hidden data**, **Redact** (words, patterns, drawn areas; also Persian), **Edit PDF** (replace/add text and pictures), **Compare PDFs**, **Batch process**
- **Repair & optimize** (pikepdf/qpdf); Word export writes flowing paragraphs with pictures (right-to-left aware, Persian safe)
- Icons are vector (SVG, drawn by Qt); input fields have a visible border on every theme
- openpyxl (MIT) is used for Excel export
- `PDFToolkit.exe --selftest out.json` checks the packaged program (used by the build)
