#!/usr/bin/env bash
# Builds the audio runtime for arm64 from checksum-pinned official Termux packages: PulseAudio, its native TCP protocol module and the
# OpenSL ES output/input modules (Android audio), plus the libraries they need. Output: app/src/main/assets/runtime/pulseaudio-runtime.zip
# Approach and package list adapted from udroid-app (MIT), https://github.com/RandomCoderOrg/udroid-app
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="https://packages.termux.dev/apt/termux-main"
TSV="$ROOT/tools/pulseaudio-packages.tsv"
CACHE="${LINUXPAD_DL_CACHE:-$HOME/.cache/linuxpad-dl}"; mkdir -p "$CACHE"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
EX="$WORK/extracted"; STAGE="$WORK/stage"; mkdir -p "$EX" "$STAGE/bin" "$STAGE/lib" "$STAGE/modules"

fetch() {   # fetch <dest> <sha256> <url>
    local dest="$1" sha="$2" url="$3" cached="$CACHE/$2"
    if [[ -f "$cached" ]] && echo "$sha  $cached" | sha256sum -c - >/dev/null 2>&1; then cp "$cached" "$dest"; return 0; fi
    for i in 1 2 3; do
        if curl --fail --location --silent --show-error --connect-timeout 20 --max-time 120 "$url" --output "$dest" && echo "$sha  $dest" | sha256sum -c - >/dev/null 2>&1; then
            cp "$dest" "$cached"; return 0
        fi
        echo "retry $i: $url" >&2; sleep $((i * 5))
    done
    echo "could not download a verified $url" >&2; return 1
}

n=0
while IFS='|' read -r arch package version path sha; do
    [[ -z "$arch" || "$arch" == \#* || "$arch" != aarch64 ]] && continue
    fetch "$WORK/$package.deb" "$sha" "$REPO/$path"
    dpkg-deb -x "$WORK/$package.deb" "$EX"
    n=$((n + 1))
done < "$TSV"
[[ $n -gt 0 ]] || { echo "no packages in $TSV" >&2; exit 1; }

P="$EX/data/data/com.termux/files/usr"
cp_l() { [[ -e "$1" ]] || { echo "missing in the packages: $1" >&2; exit 1; }; cp -L "$1" "$2"; chmod 755 "$2"; }
cp_l "$P/bin/pulseaudio" "$STAGE/bin/pulseaudio"
for lib in libFLAC.so libandroid-execinfo.so libdbus-1.so libiconv.so libltdl.so libmp3lame.so libogg.so libopus.so libprotocol-native.so \
           libpulse.so libsndfile.so libsoxr.so libspeexdsp.so libvorbis.so libvorbisenc.so; do
    cp_l "$P/lib/$lib" "$STAGE/lib/$lib"
done
cp_l "$P/lib/pulseaudio/libpulsecommon-17.0.so" "$STAGE/lib/libpulsecommon-17.0.so"
cp_l "$P/lib/pulseaudio/libpulsecore-17.0.so" "$STAGE/lib/libpulsecore-17.0.so"
for m in module-native-protocol-tcp.so module-sles-sink.so module-sles-source.so; do
    cp_l "$P/lib/pulseaudio/modules/$m" "$STAGE/modules/$m"
done
echo "17.0-3" > "$STAGE/VERSION"
OUT="$ROOT/app/src/main/assets/runtime"; mkdir -p "$OUT"
( cd "$STAGE" && find . -type f | LC_ALL=C sort | zip -9 -X -q "$OUT/pulseaudio-runtime.zip" -@ )
ls -la "$OUT/pulseaudio-runtime.zip"
