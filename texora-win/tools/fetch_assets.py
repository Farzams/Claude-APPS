"""Downloads the offline TeX engine (BusyTeX, WebAssembly) and the extra LaTeX packages into texora-win/assets/tex,
the same files the Android app carries.  Works on Windows and Linux with Python 3.8 and nothing else.
Usage: python tools/fetch_assets.py [target-dir]"""
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, "..", "assets", "tex"))

BUSYTEX = "https://github.com/busytex/busytex/releases/download/build_wasm_4499aa69fd3cf77ad86a47287d9a5193cf5ad993_7936974349_1/"
BUSYTEX_FILES = ["busytex.js", "busytex.wasm", "busytex_pipeline.js", "texlive-basic.js", "texlive-basic.data",
                 "ubuntu-texlive-latex-base.js", "ubuntu-texlive-latex-base.data",
                 "ubuntu-texlive-latex-recommended.js", "ubuntu-texlive-latex-recommended.data",
                 "ubuntu-texlive-latex-extra.js", "ubuntu-texlive-latex-extra.data",
                 "ubuntu-texlive-science.js", "ubuntu-texlive-science.data"]
UBUNTU = "http://archive.ubuntu.com/ubuntu/pool/universe/t/"
DEBS = {
    "texlive-lang-arabic": (UBUNTU + "texlive-lang/texlive-lang-arabic_2023.20240207-1_all.deb",
                            "17768e33d82957990a820e3583fb39a38ae9eef7717150927d3482cd89de9565069881f8750b00f982092cbe435ece66251d10e2b3c16f1e660110aa7c885021"),
    "texlive-pictures": (UBUNTU + "texlive-base/texlive-pictures_2023.20240207-1_all.deb",
                         "61ca87154637405fb8e06d882edf6046951e7e220060e38e3ad1c182f13f3be2d43dd58945cf8584f895559664bd75558f616514e5c5cdc298392ace159b502f"),
    "texlive-publishers": (UBUNTU + "texlive-extra/texlive-publishers_2023.20240207-1_all.deb",
                           "4a9028630b0ab7c6e58321f032e50e8605927d9c2d2fdc06d0a2d21531045a3814c3a59275c6a04c2867e7c21720787984d359a642268de969fa551184fc99a7"),
}
TDS = "usr/share/texlive/texmf-dist/"


def download(url, dest, sha512=None):
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for attempt in range(5):
        try:
            print("download", url, flush=True)
            h = hashlib.sha512()
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    h.update(b)
                    f.write(b)
            if sha512 and h.hexdigest() != sha512:
                raise IOError("checksum mismatch for " + url)
            os.replace(tmp, dest)
            return
        except Exception as e:  # network hiccup: try again
            print("  failed:", e, flush=True)
            if attempt == 4:
                raise
    return


def deb_members(path):
    """Yields (name, TarFile) of the data archive inside a .deb (an 'ar' archive)."""
    with open(path, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise IOError("not a deb: " + path)
        while True:
            head = f.read(60)
            if len(head) < 60:
                return
            name = head[:16].decode().strip()
            size = int(head[48:58])
            data_start = f.tell()
            if name.startswith("data.tar"):
                f.seek(data_start)
                blob = io.BytesIO(f.read(size))
                yield name, tarfile.open(fileobj=blob, mode="r:*")
                return
            f.seek(data_start + size + (size % 2))


def extract_dirs(deb, wanted, out_root, rel_prefix, mindepth=None):
    """Copies directories of the deb's TeX tree into out_root/texmf/texmf-dist/...  `wanted` is a list of
    (subtree, name) pairs such as ('tex/latex', 'pgf')."""
    n = 0
    _, tf = next(deb_members(deb))
    prefixes = []
    for sub, name in wanted:
        prefixes.append(TDS + sub + "/" + name + "/")
    for m in tf:
        if not m.isfile():
            continue
        for p in prefixes:
            if m.name.lstrip("./").startswith(p):
                rel = m.name.lstrip("./")[len(TDS):]
                dest = os.path.join(out_root, "texmf", "texmf-dist", *rel.split("/"))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with tf.extractfile(m) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                n += 1
                break
    return n


def write_list(folder):
    base = os.path.join(OUT, folder)
    files = []
    for root, _, names in os.walk(base):
        for f in names:
            files.append(os.path.relpath(os.path.join(root, f), base).replace("\\", "/"))
    with open(os.path.join(OUT, folder + ".json"), "w", encoding="utf-8") as f:
        json.dump(sorted(files), f)
    print(folder, len(files), "files")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in BUSYTEX_FILES:
        download(BUSYTEX + f, os.path.join(OUT, f))
    for f in ("tex_host.html", "tex_worker.js", "tex_passes.js"):
        shutil.copy(os.path.join(ROOT, "android", "app", "src", "latex", "assets", "tex", f), os.path.join(OUT, f))

    cache = os.path.join(OUT, "..", "_debs")
    debs = {}
    for k, (url, sha) in DEBS.items():
        debs[k] = os.path.join(cache, os.path.basename(url))
        download(url, debs[k], sha)

    # Persian: xepersian and bidi (LPPL) and the Vazirmatn fonts (OFL)
    shutil.rmtree(os.path.join(OUT, "extras"), ignore_errors=True)
    extract_dirs(debs["texlive-lang-arabic"], [("tex/xelatex", p) for p in ("bidi", "xepersian", "xepersian-hm")], os.path.join(OUT, "extras"), "")
    fonts = os.path.join(OUT, "extras", "fonts")
    os.makedirs(fonts, exist_ok=True)
    for f in ("Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf"):
        shutil.copy(os.path.join(ROOT, "pdftoolkit", "fonts", f), fonts)
    write_list("extras")

    # TikZ, pgfplots, circuitikz (loaded only when a project uses them) and the Elsevier class
    pic = [(s, p) for s in ("tex/latex", "tex/generic", "tex/plain") for p in ("pgf", "pgfplots", "circuitikz")]
    shutil.rmtree(os.path.join(OUT, "extras_pgf"), ignore_errors=True)
    extract_dirs(debs["texlive-pictures"], pic, os.path.join(OUT, "extras_pgf"), "")
    write_list("extras_pgf")
    shutil.rmtree(os.path.join(OUT, "extras_pub"), ignore_errors=True)
    extract_dirs(debs["texlive-publishers"], [("tex/latex", "elsarticle")], os.path.join(OUT, "extras_pub"), "")
    write_list("extras_pub")

    # bibliography styles go next to the project files
    bst = os.path.join(OUT, "extras_bst")
    shutil.rmtree(bst, ignore_errors=True)
    os.makedirs(bst)
    _, tf = next(deb_members(debs["texlive-publishers"]))
    for m in tf:
        base = os.path.basename(m.name)
        if m.isfile() and "/bibtex/bst/" in m.name and base.startswith("elsarticle-") and base.endswith(".bst"):
            with tf.extractfile(m) as src, open(os.path.join(bst, base), "wb") as dst:
                shutil.copyfileobj(src, dst)
    write_list("extras_bst")
    # Chromium 83 (the browser of Qt 5.15, needed for Windows 7) cannot start the engine as it comes
    sys.path.insert(0, HERE)
    import patch_wasm
    print("busytex.wasm", patch_wasm.patch_wasm(os.path.join(OUT, "busytex.wasm")))
    print("busytex.js", patch_wasm.patch_js(os.path.join(OUT, "busytex.js")))
    print("compat.js", patch_wasm.patch_compat(OUT))
    print("assets ready in", OUT)


if __name__ == "__main__":
    main()
