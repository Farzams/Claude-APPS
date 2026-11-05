#!/usr/bin/env bash
# Builds PRoot (Termux fork, GPL-2.0) and its loader for arm64 Android with the NDK, on Linux.
# Approach and patch/cross-answers files adapted from udroid-app (MIT), https://github.com/RandomCoderOrg/udroid-app
# Output: app/src/main/jniLibs/arm64-v8a/libproot.so and libproot-loader.so (Android runs files from the native library dir).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NDK="${ANDROID_NDK_HOME:-${ANDROID_NDK_LATEST_HOME:?set ANDROID_NDK_HOME}}"
TOOLCHAIN="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
API=26
PROOT_VERSION=5.1.107.101
PROOT_SHA256=a66743f50c7b0bac1913b83bf55e139d679c80a0ca2808eec76432a65640017f
TALLOC_VERSION=2.4.3
TALLOC_SHA256=dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

fetch() { curl --fail --location --silent --show-error "$1" --output "$2"; echo "$3  $2" | sha256sum -c - ; }
fetch "https://github.com/termux/proot/archive/v${PROOT_VERSION}.zip" "$WORK/proot.zip" "$PROOT_SHA256"
fetch "https://www.samba.org/ftp/talloc/talloc-${TALLOC_VERSION}.tar.gz" "$WORK/talloc.tar.gz" "$TALLOC_SHA256"

triple=aarch64-linux-android
cc="$TOOLCHAIN/${triple}${API}-clang"; ar="$TOOLCHAIN/llvm-ar"; strip="$TOOLCHAIN/llvm-strip"
prefix="$WORK/prefix"; wrappers="$WORK/wrappers"
mkdir -p "$WORK/talloc" "$prefix/lib" "$prefix/include" "$wrappers"
ln -s "$TOOLCHAIN/llvm-readelf" "$wrappers/readelf"
unzip -q "$WORK/proot.zip" -d "$WORK/src"
tar -xzf "$WORK/talloc.tar.gz" -C "$WORK/talloc" --strip-components=1
patch -d "$WORK/src/proot-${PROOT_VERSION}" -p1 < "$ROOT/tools/proot-ndk28.patch"

( cd "$WORK/talloc"
  CC="$cc" AR="$ar" RANLIB="$TOOLCHAIN/llvm-ranlib" ./configure --prefix="$prefix" --disable-rpath --disable-python --cross-compile --cross-answers="$ROOT/tools/proot-cross-answers.txt"
  make
  "$ar" rcs "$prefix/lib/libtalloc.a" bin/default/talloc*.o
  install -m 644 talloc.h "$prefix/include/talloc.h" )

src="$WORK/src/proot-${PROOT_VERSION}"
( cd "$src"
  PATH="$wrappers:$PATH" make -C src CC="$cc" LD="$cc" STRIP="$strip" OBJCOPY="$TOOLCHAIN/llvm-objcopy" OBJDUMP="$TOOLCHAIN/llvm-objdump" \
    CPPFLAGS="-D_FILE_OFFSET_BITS=64 -D_GNU_SOURCE -DARG_MAX=131072 -DVERSION=\\\"${PROOT_VERSION}\\\" -I. -I$prefix/include" \
    CFLAGS="-Wall -Wextra -O2" LDFLAGS="-L$prefix/lib -ltalloc -Wl,-z,noexecstack"
  "$strip" src/proot )

out="$ROOT/app/src/main/jniLibs/arm64-v8a"; mkdir -p "$out"
install -m 755 "$src/src/proot" "$out/libproot.so"
install -m 755 "$src/src/loader/loader" "$out/libproot-loader.so"
file "$out"/*.so 2>/dev/null || true
sha256sum "$out"/*.so
