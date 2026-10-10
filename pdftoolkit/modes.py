"""The windows (modes) of the program. Same files, started with --mode, give separate apps."""

MODES = {
    "full": dict(title="PDF Toolkit", sidebar=None, start="home", compact=False, icon=None, aumid="PDFToolkit.Full"),
    "reader": dict(title="PDF Toolkit — Reader", sidebar=["read", "settings", "help"], start="read", compact=True,
                   icon="read", aumid="PDFToolkit.Reader"),
    "math": dict(title="PDF Toolkit — Math Studio", sidebar=["math", "formulaocr", "latex", "formula", "settings", "help"],
                 start="math", compact=False, icon="math", aumid="PDFToolkit.MathStudio"),
}
