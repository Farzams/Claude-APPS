# PDF Toolkit

Split, merge, compress, convert (EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT, DOCX…), images to PDF, page tools and OCR.

The Windows build bundles everything, so nothing else needs installing:
- **DjVuLibre** (`ddjvu`, GPL-2.0, https://djvu.sourceforge.net) – DjVu conversion
- **Ghostscript** (AGPL-3.0, https://ghostscript.com) – strong PDF compression
- **Tesseract OCR** (Apache-2.0, https://github.com/tesseract-ocr/tesseract) with `tessdata_best` Persian/Arabic and `tessdata_fast` models – OCR
- **Pandoc** (GPL-2.0, https://pandoc.org) – DOCX/ODT/RTF/EPUB/Markdown conversion
- **Noto Sans Arabic** (SIL OFL 1.1) and **DejaVu Sans** (free licence) fonts in `fonts/` – Persian/Arabic page rendering and OCR text layer

Each tool runs as a separate, unmodified program. Calibre is optional and only needed for legacy `.doc`, `.lit`, `.pdb`, `.cbr`.

## Persian (Farsi) support
- OCR with the best Persian model; the text layer is written in correct logical order, so search and copy work
- Converting DOCX/ODT/RTF/EPUB/TXT/HTML to PDF shapes letters, lays text out right-to-left and keeps headings as bookmarks
- Text files in UTF-8, UTF-16 or Windows-1256 are read correctly
- Extract text normalises Persian letters; Read tab searches Persian ignoring half-spaces

## Interface
- Built with **Qt (PySide6, LGPL)**: native speed, correct Persian shaping and right-to-left layout
- English and Persian interface; Help section in both languages; fonts Inter and Vazirmatn (SIL OFL, in `fonts/`)
- 9 colour themes (light and dark), a picture behind the whole window (built-in styles or your own photo) with adjustable visibility, colourful icons, drag & drop
- Theme changes restyle only the visible page; hidden pages catch up when opened
- Settings are stored in `%APPDATA%\PDFToolkit\settings.json`

## Science tools
- **LaTeX**: write or open `.tex`, compile with the bundled **Tectonic** (XeTeX; an installed XeLaTeX/MiKTeX/TeX Live is used if Tectonic is absent), preview the PDF, errors listed with line numbers and plain-words hints; 8 templates (article, Orlicz notes, thesis, Beamer, Persian + English, chemistry, physics, blank)
- **Formula**: one LaTeX formula to PNG / SVG / PDF with transparent background and colour choice
- **Symbols**: 300+ symbols (Greek, operators, analysis incl. Orlicz notation, algebra, physics, chemistry `\ce{}`/`\chemfig`, units) inserted at the cursor
- **Convert to PDF** typesets equations in Word/Markdown/ODT/EPUB (via Pandoc + LaTeX), also in Persian documents; `.tex` converts directly; Import turns Word/Markdown into `.tex`
- Tectonic (MIT) runs as a separate program; its package cache is pre-filled at build time so common packages work offline, others are fetched on first use

## Reader and PDF tools (v6)
- **Reader**: tabs, continuous scrolling, two-page and right-to-left modes, light / sepia / night, thumbnails, contents, bookmarks, Persian-aware search with highlights, text selection, links; opens PDF, DjVu, EPUB, MOBI/AZW, FB2, CBZ, XPS, DOCX, ODT, RTF, Markdown, HTML, TXT, TeX and pictures (non-PDF formats are converted once and cached)
- **Organize pages** (drag & drop thumbnails, rotate, delete, duplicate, insert, undo), **Crop**, **Delete blank pages**, **Header/footer/Bates**, **Watermark**, **Page background**
- **PDF to** pictures / Word / Excel / HTML / RTF / EPUB / text, **Password & permissions** (AES-256), **Remove hidden data**, **Redact** (words, patterns, drawn areas; also Persian), **Edit PDF** (replace/add text and pictures), **Compare PDFs**, **Batch process**
- Icons are vector (SVG, drawn by Qt); input fields have a visible border on every theme
- openpyxl (MIT) is used for Excel export
