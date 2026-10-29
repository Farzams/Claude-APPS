# TeXora for Windows

Offline LaTeX editor for maths and science (English and Persian), the Windows sibling of the TeXora Android app.
It runs the same offline TeX engine (BusyTeX, TeX Live 2023 compiled to WebAssembly), so nothing is installed or downloaded when you compile.

## Windows 7

* 64-bit Windows 7 **SP1** with the *Universal C Runtime* update (KB2999226) is required (Windows 8.1 and later already have it).
* Built with Python 3.8 and PySide2 (Qt 5.15), the newest versions that still run on Windows 7.
* The engine page runs in Qt 5.15's Chromium; the first compile after start takes a little longer because the engine loads.

## Build

    pip install -r requirements.txt
    python tools/fetch_assets.py          # TeX engine + packages into assets/tex (about 220 MB)
    python -m texora                      # run
    python -m texora --selftest out.json  # compile a Persian page and report

CI (`.github/workflows/build-texora-windows.yml`) builds `TeXora-Setup.exe` and `TeXora-portable.zip`.

Data lives in `%APPDATA%\TeXora` (projects, history, settings).
