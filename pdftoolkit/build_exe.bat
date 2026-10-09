@echo off
rem Builds dist\PDFToolkit\PDFToolkit.exe (fast-starting one-folder build). Needs Python 3.10+.
rem To bundle DjVu: copy the DjVuLibre folder (ddjvu.exe + dlls) to a "djvu" folder here and add --add-data "djvu;djvu".
rem For an installer, then open installer.iss with Inno Setup (jrsoftware.org/isinfo.php).
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --onedir --windowed --name PDFToolkit --icon icon.ico --add-data "icon.ico;." --add-data "fonts;fonts" --add-data "gs;gs" --add-data "tesseract;tesseract" --add-data "djvu;djvu" --collect-all customtkinter --collect-all pypandoc --collect-all tkinterdnd2 --collect-all docx app.py || exit /b 1
echo.
echo Done: dist\PDFToolkit\PDFToolkit.exe
