# PDF Toolkit

Split, merge, compress, convert (EPUB, MOBI, FB2, DjVu, XPS, CBZ, HTML, TXT, DOCX…), images to PDF, page tools and OCR.

The Windows build bundles everything, so nothing else needs installing:
- **DjVuLibre** (`ddjvu`, GPL-2.0, https://djvu.sourceforge.net) – DjVu conversion
- **Ghostscript** (AGPL-3.0, https://ghostscript.com) – strong PDF compression
- **Tesseract language data** (Apache-2.0, tessdata_fast) – OCR via PyMuPDF's built-in engine
- **Pandoc** (GPL-2.0, https://pandoc.org) – DOCX/ODT/RTF/Markdown conversion

Each runs as a separate, unmodified program. Calibre is optional and only needed for legacy `.doc`, `.lit`, `.pdb`, `.cbr`.
