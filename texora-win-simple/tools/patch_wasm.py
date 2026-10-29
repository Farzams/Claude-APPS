"""Makes the BusyTeX engine start in Chromium 83 (the browser inside Qt 5.15, the last Qt that runs on Windows 7).

The engine module uses atomic instructions but declares a plain memory; Chromium 83 refuses that combination
("Atomic opcodes used without shared memory"), newer browsers accept it.  Declaring the memory as shared fixes it,
and the two places of the glue code that hand heap bytes to TextDecoder / crypto.getRandomValues get a copy
(those APIs reject views of shared memory).  Usage: python tools/patch_wasm.py <assets/tex>"""
import os
import sys


def _leb(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            return r, i


def patch_wasm(path):
    with open(path, "rb") as f:
        d = bytearray(f.read())
    i = 8
    while i < len(d):
        sid = d[i]
        i += 1
        size, i = _leb(d, i)
        if sid == 5:                                  # memory section
            n, j = _leb(d, i)
            if n != 1:
                raise SystemExit("unexpected memory section")
            if d[j] == 1:                             # limits with a maximum, not shared
                d[j] = 3
                with open(path, "wb") as f:
                    f.write(d)
                return "patched"
            return "already shared" if d[j] == 3 else "unexpected memory flags %d" % d[j]
        i += size
    raise SystemExit("no memory section in " + path)


DECODE_OLD = "return UTF8Decoder.decode(heapOrArray.subarray(idx, endPtr));"
DECODE_NEW = ("return UTF8Decoder.decode(typeof SharedArrayBuffer != 'undefined' && heapOrArray.buffer instanceof SharedArrayBuffer"
              " ? heapOrArray.slice(idx, endPtr) : heapOrArray.subarray(idx, endPtr));")


RANDOM_OLD = "return (view) => crypto.getRandomValues(view);"
RANDOM_NEW = "return (view) => { var t = new Uint8Array(view.byteLength); crypto.getRandomValues(t); new Uint8Array(view.buffer, view.byteOffset, view.byteLength).set(t); return view; };"


def patch_js(path):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    if DECODE_NEW in s and RANDOM_NEW in s:
        return "already patched"
    if (DECODE_OLD not in s and DECODE_NEW not in s) or (RANDOM_OLD not in s and RANDOM_NEW not in s):
        raise SystemExit("glue code not recognised: " + path)
    s = s.replace(DECODE_OLD, DECODE_NEW).replace(RANDOM_OLD, RANDOM_NEW)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    return "patched"


def patch_data_packages(root):
    """The data packages cache themselves in IndexedDB; a half-written cache made Windows runs fail
    (RangeError while joining chunks).  The files come from a local server, so the cache is not needed: switch it off."""
    old = "var openRequest = indexedDB.open(DB_NAME, DB_VERSION);"
    new = "throw new Error('package cache disabled');"
    n = 0
    for name in sorted(os.listdir(root)):
        if name.endswith(".js") and ("texlive" in name):
            path = os.path.join(root, name)
            s = open(path, encoding="latin-1").read()          # some of these files are not UTF-8: keep every byte as it is
            if old in s:
                open(path, "w", encoding="latin-1").write(s.replace(old, new))
                n += 1
    return "patched %d files" % n


COMPAT = r"""// Functions newer than Chromium 83 that the engine's scripts use.
(function (g) {
  if (!String.prototype.replaceAll) String.prototype.replaceAll = function (a, b) {
    if (a instanceof RegExp) { if (!a.global) throw new TypeError('replaceAll must be called with a global RegExp'); return this.replace(a, b); }
    return this.replace(new RegExp(String(a).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), b);
  };
  if (!Array.prototype.at) Array.prototype.at = function (i) { i = Math.trunc(i) || 0; if (i < 0) i += this.length; return this[i]; };
  if (!String.prototype.at) String.prototype.at = function (i) { i = Math.trunc(i) || 0; if (i < 0) i += this.length; return this.charAt(i) || undefined; };
  if (!Object.hasOwn) Object.hasOwn = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };
  if (typeof g.structuredClone !== 'function') g.structuredClone = function (v) { return v === undefined ? v : JSON.parse(JSON.stringify(v)); };
})(typeof self !== 'undefined' ? self : this);
"""


def patch_compat(root):
    with open(os.path.join(root, "compat.js"), "w", encoding="utf-8") as f:
        f.write(COMPAT)
    p = os.path.join(root, "tex_worker.js")
    s = open(p, encoding="utf-8").read()
    if "compat.js" not in s:
        open(p, "w", encoding="utf-8").write("importScripts('compat.js');\n" + s)
    p = os.path.join(root, "tex_host.html")
    s = open(p, encoding="utf-8").read()
    if "compat.js" not in s:
        open(p, "w", encoding="utf-8").write(s.replace("<body>", "<body>\n<script src=\"/assets/tex/compat.js\"></script>", 1))
    return "added"


if __name__ == "__main__":
    root = sys.argv[1]
    print("compat.js", patch_compat(root))
    print("data packages", patch_data_packages(root))
    print("busytex.wasm", patch_wasm(os.path.join(root, "busytex.wasm")))
    print("busytex.js", patch_js(os.path.join(root, "busytex.js")))
