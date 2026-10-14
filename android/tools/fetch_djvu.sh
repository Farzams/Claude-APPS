#!/usr/bin/env bash
# Downloads the DjVuLibre sources (GPL) that the PDF app compiles into a small native library.
# The sources are not stored in git; the build runs this first.
set -euo pipefail
cd "$(dirname "$0")/.."
D=djvu/src/main/cpp/djvulibre
if [ -f "$D/libdjvu/ddjvuapi.cpp" ]; then echo "DjVuLibre sources already present"; exit 0; fi
mkdir -p "$D"
T=$(mktemp -d)
curl -fsSL --retry 5 --retry-delay 5 -o "$T/djvulibre.tgz" "https://downloads.sourceforge.net/project/djvu/DjVuLibre/3.5.28/djvulibre-3.5.28.tar.gz"
tar xzf "$T/djvulibre.tgz" -C "$T"
cp -r "$T/djvulibre-3.5.28/libdjvu" "$D/libdjvu"
cp "$T/djvulibre-3.5.28/COPYING" "$T/djvulibre-3.5.28/COPYRIGHT" "$D/"
find "$D" -name "Makefile*" -delete
echo "DjVuLibre sources ready:"; du -sh "$D"
