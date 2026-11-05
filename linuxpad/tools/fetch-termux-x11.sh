#!/usr/bin/env bash
# Fetches the Termux:X11 sources (GPL-3.0) at a pinned commit, with submodules, into third_party/termux-x11.
# Not stored in git. Run before building. Safe to run again.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/third_party/termux-x11"
COMMIT=0cb0203c283bfafbad380b90444296aa42af058d
if [[ -d "$DEST/.git" ]] && [[ "$(git -C "$DEST" rev-parse HEAD)" == "$COMMIT" ]]; then
    echo "Termux:X11 $COMMIT already present"
else
    rm -rf "$DEST"; mkdir -p "$DEST"
    git -C "$DEST" init -q
    git -C "$DEST" remote add origin https://github.com/termux/termux-x11.git
    git -C "$DEST" fetch --depth 1 origin "$COMMIT"
    git -C "$DEST" checkout -q FETCH_HEAD
fi
git -C "$DEST" submodule update --init --recursive --jobs 8 --depth 1
# LinuxPad's patches (see patches/termux-x11), applied in file-name order. A marker holds the hash of the applied set,
# so running the script again on a patched tree does nothing.
PATCHSET="$(cat "$ROOT"/patches/termux-x11/*.patch | sha256sum | cut -d' ' -f1)"
if [[ -f "$DEST/.linuxpad-patched" ]] && [[ "$(cat "$DEST/.linuxpad-patched")" == "$PATCHSET" ]]; then
    echo "LinuxPad patches already applied"
else
    git -C "$DEST" checkout -q -- . 2>/dev/null || true       # start from the pristine sources
    for patch in "$ROOT"/patches/termux-x11/*.patch; do
        git -C "$DEST" apply "$patch"
        echo "applied: $(basename "$patch")"
    done
    echo "$PATCHSET" > "$DEST/.linuxpad-patched"
fi
echo "Termux:X11 ready at $DEST"
