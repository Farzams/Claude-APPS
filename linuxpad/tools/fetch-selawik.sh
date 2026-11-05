#!/usr/bin/env bash
# Fetches the Selawik font (SIL OFL 1.1, Microsoft's open replacement for Segoe UI) from its official release and puts the .ttf files into
# the app's assets, so the app carries them. A failed download is not fatal: the app then falls back to other fonts.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/app/src/main/assets/fonts"; mkdir -p "$OUT"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ok=0
if command -v gh >/dev/null 2>&1 && [[ -n "${GH_TOKEN:-}" ]]; then
    gh release download --repo microsoft/Selawik --pattern '*.zip' --dir "$TMP" 2>&1 && ok=1
fi
if [[ $ok -eq 0 ]]; then
    curl --fail --location --silent --show-error --connect-timeout 20 --max-time 120 --retry 3 \
        -o "$TMP/selawik.zip" "https://github.com/microsoft/Selawik/releases/download/1.01/Selawik_Release.zip" && ok=1
fi
if [[ $ok -eq 1 ]]; then
    for z in "$TMP"/*.zip; do
        echo "selawik archive: $(sha256sum "$z")"          # printed so the checksum can be pinned later
        unzip -q -o "$z" -d "$TMP/x" && find "$TMP/x" -iname '*.ttf' -exec cp {} "$OUT"/ \;
    done
    ls -la "$OUT"
else
    echo "WARNING: Selawik could not be downloaded; the app will use other fonts" >&2
fi
exit 0
