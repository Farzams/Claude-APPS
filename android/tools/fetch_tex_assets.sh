#!/usr/bin/env bash
# Downloads the offline TeX engine (BusyTeX, WebAssembly) and the Persian packages into the app's assets.
# The files are not stored in git (about 220 MB); the build runs this first.
set -euo pipefail
cd "$(dirname "$0")/.."
A=app/src/latex/assets/tex
mkdir -p "$A/extras"
R=build_wasm_4499aa69fd3cf77ad86a47287d9a5193cf5ad993_7936974349_1
for f in busytex.js busytex.wasm busytex_pipeline.js \
         texlive-basic.js texlive-basic.data \
         ubuntu-texlive-latex-base.js ubuntu-texlive-latex-base.data \
         ubuntu-texlive-latex-recommended.js ubuntu-texlive-latex-recommended.data \
         ubuntu-texlive-latex-extra.js ubuntu-texlive-latex-extra.data \
         ubuntu-texlive-science.js ubuntu-texlive-science.data; do
  if [ ! -s "$A/$f" ]; then
    curl -fsSL --retry 5 --retry-delay 5 -o "$A/$f" "https://github.com/busytex/busytex/releases/download/$R/$f"
  fi
done

# Persian: xepersian + bidi come from the Ubuntu texlive-lang-arabic package (LPPL), fonts from the repo (OFL).
W=$(mktemp -d)
(cd "$W" && apt-get download texlive-lang-arabic >/dev/null && dpkg-deb -x ./*.deb x)
TDS="$W/x/usr/share/texlive/texmf-dist/tex/xelatex"
for pkg in bidi xepersian xepersian-hm; do
  mkdir -p "$A/extras/texmf/texmf-dist/tex/xelatex/$pkg"
  cp -r "$TDS/$pkg/." "$A/extras/texmf/texmf-dist/tex/xelatex/$pkg/"
done
mkdir -p "$A/extras/fonts"
cp ../pdftoolkit/fonts/Vazirmatn-Regular.ttf ../pdftoolkit/fonts/Vazirmatn-Bold.ttf "$A/extras/fonts/"
(cd "$A/extras" && find . -type f | sed 's|^\./||' | sort | python3 -c "import sys, json; json.dump([l.strip() for l in sys.stdin], open('../extras.json', 'w'))")
# More LaTeX the BusyTeX bundles do not have, loaded only when a project uses it:
# TikZ, pgfplots and circuitikz (texlive-pictures), and the IEEE, Elsevier and Springer classes (texlive-publishers).
X=$(mktemp -d)
(cd "$X" && apt-get download texlive-pictures texlive-publishers >/dev/null && for d in ./*.deb; do dpkg-deb -x "$d" x; done)
SRC="$X/x/usr/share/texlive/texmf-dist"
json_of() { (cd "$A/$1" && find . -type f | sed 's|^\./||' | sort | python3 -c "import sys, json; json.dump([l.strip() for l in sys.stdin], open('../$1.json', 'w'))"); }
copy_pkgs() {
  local out="$1"; shift
  mkdir -p "$A/$out"
  for pkg in "$@"; do
    find "$SRC/tex" -mindepth 2 -maxdepth 2 -type d -name "$pkg" | while read -r d; do
      rel=${d#"$SRC"/}
      mkdir -p "$A/$out/texmf/texmf-dist/$rel"
      cp -r "$d/." "$A/$out/texmf/texmf-dist/$rel/"
    done
  done
  json_of "$out"
}
copy_pkgs extras_pgf pgf pgfplots circuitikz
copy_pkgs extras_pub IEEEtran elsarticle 'svjour*'
mkdir -p "$A/extras_bst"
find "$SRC/bibtex/bst" -type f \( -name 'IEEEtran.bst' -o -name 'elsarticle-*.bst' -o -name 'sp*.bst' \) -exec cp {} "$A/extras_bst/" \;
json_of extras_bst
echo "TeX assets ready:"; du -sh "$A"
