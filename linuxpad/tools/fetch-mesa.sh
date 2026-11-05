#!/usr/bin/env bash
# Fetches the Mesa build for Android containers (patched Turnip/KGSL graphics drivers, Debian trixie arm64, MIT) from its release and
# puts it into the app's assets. The file is checked against the SHA-256 listed in the release notes; a failed download is not fatal:
# the app then offers no GPU option. https://github.com/lfdevs/mesa-for-android-container
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="mesa-26.2.0-devel-20260709"
FILE="mesa-for-android-container_26.2.0-devel-20260709_debian_trixie_arm64.tar.gz"
SHA="4ee525b4844fb189f3762ff75ef77f5b80eee8f6cdab2e5588731b5c9f8168bb"
OUT="$ROOT/app/src/main/assets/gpu"; mkdir -p "$OUT"
CACHE="${LINUXPAD_DL_CACHE:-$HOME/.cache/linuxpad-dl}"; mkdir -p "$CACHE"
dest="$OUT/mesa-android.tar.gz"
if [[ -f "$CACHE/$SHA" ]] && echo "$SHA  $CACHE/$SHA" | sha256sum -c - >/dev/null 2>&1; then cp "$CACHE/$SHA" "$dest"; echo "mesa package from cache"; exit 0; fi
for i in 1 2 3; do
    if curl --fail --location --silent --show-error --connect-timeout 20 --max-time 180 \
        "https://github.com/lfdevs/mesa-for-android-container/releases/download/$TAG/$FILE" --output "$dest" \
        && echo "$SHA  $dest" | sha256sum -c - >/dev/null 2>&1; then
        cp "$dest" "$CACHE/$SHA"; ls -la "$dest"; exit 0
    fi
    echo "retry $i: mesa package" >&2; sleep $((i * 5))
done
rm -f "$dest"
echo "WARNING: the Mesa package could not be downloaded or did not match its checksum; this build has no GPU option" >&2
exit 0
