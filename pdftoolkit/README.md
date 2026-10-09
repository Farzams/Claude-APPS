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
