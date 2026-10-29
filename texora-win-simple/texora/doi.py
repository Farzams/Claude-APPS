"""Looks a reference up by its DOI. The only thing in the app that uses the internet, and only when asked."""
import re
import urllib.error
import urllib.parse
import urllib.request


def clean(text):
    s = text.strip()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:", "DOI:"):
        if s.startswith(p):
            s = s[len(p):]
    s = s.strip()
    return s if re.fullmatch(r"10\.\d{4,9}/\S+", s) else None


def fetch(doi, timeout=15):
    """Returns (entry, error): the BibTeX entry or an error message."""
    req = urllib.request.Request("https://doi.org/" + urllib.parse.quote(doi, safe="/()-._:;"),
                                 headers={"Accept": "application/x-bibtex; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as e:
        return None, "HTTP %d" % e.code
    except Exception as e:  # no network, timeout, TLS problems
        return None, str(e)
    if not text.startswith("@"):
        return None, "no BibTeX returned"
    return tidy(text), None


def tidy(entry):
    head = re.match(r"^@(\w+)\{([^,]+),", entry)
    if not head:
        return entry
    typ = head.group(1)
    fields = list(re.finditer(r'(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|\d+)', entry[head.end():]))

    def get(name):
        for f in fields:
            if f.group(1).lower() == name:
                return f.group(2).strip("{}\"")
        return ""

    a = get("author").split(" and ")[0]
    last = a.split(",")[0] if "," in a else a.split(" ")[-1]
    last = "".join(c for c in last.lower() if c.isalpha()) or "ref"
    key = last + get("year")
    body = ",\n".join("  %s = %s" % (f.group(1).lower().ljust(9), f.group(2)) for f in fields)
    return "@%s{%s,\n%s\n}\n" % (typ, key, body)
