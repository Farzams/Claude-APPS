@echo off
rem Builds dist\PDFToolkit.exe  (needs Python 3.10+ from python.org)
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name PDFToolkit --collect-all customtkinter app.py || exit /b 1
echo.
echo Done: dist\PDFToolkit.exe
