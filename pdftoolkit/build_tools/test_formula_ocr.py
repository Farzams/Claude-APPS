"""Build check for the bundled Formula OCR models: recognise a rendered formula. usage: test_formula_ocr.py <models dir>"""
import sys
from pathlib import Path

models = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import formula_ocr

fig = plt.figure(figsize=(4, 1.2), dpi=200)
fig.text(0.05, 0.3, r"$\int_0^1 x^2\,dx=\frac{1}{3}$", fontsize=22)
fig.savefig("formula_test.png")
m = formula_ocr.FormulaOCR(models)
res = m.recognize("formula_test.png")
print("recognised:", res)
assert "frac" in res and "int" in res, res
