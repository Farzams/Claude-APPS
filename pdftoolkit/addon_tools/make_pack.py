"""Builds the tex-full add-on: every cache file that `full` added on top of `base`, as a zip (paths relative to the cache)."""
import os
import sys
import zipfile
from pathlib import Path

base, full, out = (Path(p) for p in sys.argv[1:4])
n = size = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(full.rglob("*")):
        if not p.is_file() or p.name == ".seeded":
            continue
        rel = p.relative_to(full)
        q = base / rel
        if q.exists() and q.stat().st_size == p.stat().st_size and q.read_bytes() == p.read_bytes():
            continue                       # already part of the program's own cache
        z.write(p, rel.as_posix())
        n += 1
        size += p.stat().st_size
print(f"{n} files, {size // 1048576} MB before compression -> {out.stat().st_size // 1048576} MB")
