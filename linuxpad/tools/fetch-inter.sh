#!/usr/bin/env bash
# Fetches the Inter font (SIL OFL 1.1, a clean sans-serif close to the Mac system font) from its official release, checks it against a
# pinned SHA-256, and puts the variable .ttf files into the app's assets. A failed download is not fatal: the app then uses Selawik.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL="https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
SHA="9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e"
OUT="$ROOT/app/src/main/assets/fonts"; mkdir -p "$OUT"
CACHE="${LINUXPAD_DL_CACHE:-$HOME/.cache/linuxpad-dl}"; mkdir -p "$CACHE"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
zip="$CACHE/$SHA"
if ! { [[ -f "$zip" ]] && echo "$SHA  $zip" | sha256sum -c - >/dev/null 2>&1; }; then
    ok=0
    for i in 1 2 3; do
        if curl --fail --location --silent --show-error --connect-timeout 20 --max-time 180 "$URL" -o "$TMP/inter.zip" \
            && echo "$SHA  $TMP/inter.zip" | sha256sum -c - >/dev/null 2>&1; then cp "$TMP/inter.zip" "$zip"; ok=1; break; fi
        echo "retry $i: Inter" >&2; sleep $((i * 5))
    done
    [[ $ok = 1 ]] || { echo "WARNING: Inter could not be downloaded; the app will use Selawik" >&2; exit 0; }
fi
unzip -q -o -j "$zip" InterVariable.ttf InterVariable-Italic.ttf LICENSE.txt -d "$TMP/x"
cp "$TMP/x/InterVariable.ttf" "$TMP/x/InterVariable-Italic.ttf" "$OUT/"
cp "$TMP/x/LICENSE.txt" "$OUT/INTER-LICENSE.txt"
ls -la "$OUT"
exit 0
