#!/usr/bin/env bash
# Builds the audio runtime for arm64 from official Termux packages: PulseAudio, its native TCP protocol module and the OpenSL ES
# output/input modules (Android audio), plus every library they depend on. The Termux repository keeps only current versions, so the
# versions are resolved from the repository index at build time (fetched over TLS); every package is checked against the SHA256
# listed in that index. Output: app/src/main/assets/runtime/pulseaudio-runtime.zip
# Approach adapted from udroid-app (MIT), https://github.com/RandomCoderOrg/udroid-app
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="https://packages.termux.dev/apt/termux-main"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
EX="$WORK/extracted"; STAGE="$WORK/stage"; mkdir -p "$EX" "$STAGE/bin" "$STAGE/lib" "$STAGE/modules"

for i in 1 2 3 4; do
    curl --fail --location --silent --show-error --connect-timeout 20 --max-time 120 "$REPO/dists/stable/main/binary-aarch64/Packages" -o "$WORK/Packages" && break
    echo "retry $i: package index" >&2; sleep $((i * 5))
done
[[ -s "$WORK/Packages" ]] || { echo "could not download the Termux package index" >&2; exit 1; }

# resolve pulseaudio and its dependencies -> lines "name|path|sha256"
python3 - "$WORK/Packages" > "$WORK/list.tsv" <<'PY'
import sys, re
pk = {}
for block in open(sys.argv[1], encoding="utf-8").read().split("\n\n"):
    f = dict(re.findall(r"^([A-Za-z0-9-]+): (.*)$", block, re.M))
    if "Package" in f: pk[f["Package"]] = f
skip = {"termux-exec", "termux-tools", "termux-keyring", "apt", "bash", "dash", "coreutils", "busybox"}
seen, todo = set(), ["pulseaudio"]
while todo:
    n = todo.pop()
    if n in seen or n in skip: continue
    if n not in pk: sys.exit("package missing from the index: " + n)
    seen.add(n)
    for dep in pk[n].get("Depends", "").split(","):
        dep = re.sub(r"\(.*?\)", "", dep.split("|")[0]).strip()
        if dep: todo.append(dep)
for n in sorted(seen):
    print("%s|%s|%s" % (n, pk[n]["Filename"], pk[n]["SHA256"]))
PY
echo "resolved packages:"; cut -d'|' -f1 "$WORK/list.tsv" | tr '\n' ' '; echo

while IFS='|' read -r name path sha; do
    ok=0
    for i in 1 2 3; do
        if curl --fail --location --silent --show-error --connect-timeout 20 --max-time 120 "$REPO/$path" --output "$WORK/p.deb" && echo "$sha  $WORK/p.deb" | sha256sum -c - >/dev/null 2>&1; then ok=1; break; fi
        echo "retry $i: $name" >&2; sleep $((i * 5))
    done
    [[ $ok = 1 ]] || { echo "could not download a verified $name" >&2; exit 1; }
    dpkg-deb -x "$WORK/p.deb" "$EX"
done < "$WORK/list.tsv"

P="$EX/data/data/com.termux/files/usr"
[[ -f "$P/bin/pulseaudio" ]] || { echo "missing in the packages: bin/pulseaudio" >&2; exit 1; }
cp -L "$P/bin/pulseaudio" "$STAGE/bin/pulseaudio"; chmod 755 "$STAGE/bin/pulseaudio"
# every shared library (also the PulseAudio private ones), flat; symlinks are resolved into real files
for f in "$P"/lib/*.so* "$P"/lib/pulseaudio/*.so*; do
    [[ -e "$f" && ! -d "$f" ]] || continue
    cp -L "$f" "$STAGE/lib/$(basename "$f")"; chmod 755 "$STAGE/lib/$(basename "$f")"
done
for m in module-native-protocol-tcp.so module-sles-sink.so module-sles-source.so; do
    [[ -e "$P/lib/pulseaudio/modules/$m" ]] || { echo "missing in the packages: $m" >&2; exit 1; }
    cp -L "$P/lib/pulseaudio/modules/$m" "$STAGE/modules/$m"; chmod 755 "$STAGE/modules/$m"
done
# the protocol module and PulseAudio's own libraries also live next to the modules
cp -L "$P"/lib/pulseaudio/modules/libprotocol-native.so "$STAGE/modules/" 2>/dev/null || true
ver="$(grep -h '^pulseaudio|' "$WORK/list.tsv" | sed 's#.*/##')"; echo "${ver:-unknown}" > "$STAGE/VERSION"
OUT="$ROOT/app/src/main/assets/runtime"; mkdir -p "$OUT"; rm -f "$OUT/pulseaudio-runtime.zip"
( cd "$STAGE" && find . -type f | LC_ALL=C sort | zip -9 -X -q "$OUT/pulseaudio-runtime.zip" -@ )
ls -la "$OUT/pulseaudio-runtime.zip"; ( cd "$STAGE" && ls lib modules )
