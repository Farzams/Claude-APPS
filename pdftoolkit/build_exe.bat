@echo off
rem Builds dist\PDFToolkit\PDFToolkit.exe (fast-starting one-folder build). Needs Python 3.10+.
rem For an installer, then open installer.iss with Inno Setup (jrsoftware.org/isinfo.php).
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --onedir --windowed --name PDFToolkit --icon icon.ico --add-data "icon.ico;." --collect-all customtkinter app.py || exit /b 1
echo.
echo Done: dist\PDFToolkit\PDFToolkit.exe
