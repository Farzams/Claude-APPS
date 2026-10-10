"""Colour themes."""
from __future__ import annotations

THEMES: dict[str, dict] = {
    "indigo_night": dict(name="Indigo Night", dark=True, bg="#12141a", sidebar="#191c24", card="#1d212b",
                         hover="#262b3a", field="#272c38", text="#e8e8ee", muted="#9aa0b4",
                         accent="#6366f1", accent_hover="#818cf8", on_accent="#ffffff", good="#4ade80"),
    "daylight": dict(name="Daylight", dark=False, bg="#f3f4f9", sidebar="#ffffff", card="#ffffff",
                     hover="#eef0fb", field="#f1f2f8", text="#14151a", muted="#5b6070",
                     accent="#4f46e5", accent_hover="#4338ca", on_accent="#ffffff", good="#15803d"),
    "ocean": dict(name="Ocean", dark=True, bg="#0b1a24", sidebar="#0f2331", card="#12293a",
                  hover="#1a3a50", field="#17344a", text="#e6f4fa", muted="#8fb3c4",
                  accent="#0ea5e9", accent_hover="#38bdf8", on_accent="#04202e", good="#4ade80"),
    "forest": dict(name="Forest", dark=True, bg="#0f1a14", sidebar="#13221a", card="#172a20",
                   hover="#20382b", field="#1f3528", text="#e8f3ec", muted="#96b5a2",
                   accent="#22c55e", accent_hover="#4ade80", on_accent="#04210f", good="#86efac"),
    "sunset": dict(name="Sunset", dark=False, bg="#fff4ec", sidebar="#ffffff", card="#ffffff",
                   hover="#ffe8d6", field="#fff0e4", text="#2a1a12", muted="#8a6a58",
                   accent="#f97316", accent_hover="#ea580c", on_accent="#ffffff", good="#15803d"),
    "rose": dict(name="Rose", dark=False, bg="#fdf2f6", sidebar="#ffffff", card="#ffffff",
                 hover="#fce4ee", field="#fdeaf1", text="#2a1520", muted="#8a5a70",
                 accent="#e11d74", accent_hover="#be185d", on_accent="#ffffff", good="#15803d"),
    "lavender": dict(name="Lavender", dark=False, bg="#f5f3ff", sidebar="#ffffff", card="#ffffff",
                     hover="#ede9fe", field="#f3f0ff", text="#1e1b2e", muted="#645d85",
                     accent="#7c3aed", accent_hover="#6d28d9", on_accent="#ffffff", good="#15803d"),
    "gold": dict(name="Midnight Gold", dark=True, bg="#101010", sidebar="#161616", card="#1c1b18",
                 hover="#2a2820", field="#26241d", text="#f2ead6", muted="#b3a780",
                 accent="#d4a017", accent_hover="#eab308", on_accent="#1a1400", good="#a3e635"),
    "graphite": dict(name="Graphite", dark=True, bg="#1a1a1a", sidebar="#212121", card="#262626",
                     hover="#303030", field="#2e2e2e", text="#eeeeee", muted="#9e9e9e",
                     accent="#14b8a6", accent_hover="#2dd4bf", on_accent="#03201c", good="#4ade80"),
    # flat "designer" themes: no picture, thin borders, solid colours
    "qp_light": dict(name="Quiet Light", dark=False, flat=True, bg="#f6f7f9", sidebar="#ffffff", card="#ffffff",
                     hover="#eef0f4", field="#ffffff", text="#101828", muted="#667085",
                     accent="#4f46e5", accent_hover="#4338ca", on_accent="#ffffff", good="#15803d", line="#e4e7ec"),
    "qp_dark": dict(name="Quiet Dark", dark=True, flat=True, bg="#0d0f13", sidebar="#101216", card="#14171c",
                    hover="#1c2027", field="#171a20", text="#e8eaee", muted="#8b93a1",
                    accent="#818cf8", accent_hover="#a5b4fc", on_accent="#ffffff", good="#4ade80", line="#232830"),
    "paper": dict(name="Paper", dark=False, flat=True, bg="#f3eee4", sidebar="#efe9dc", card="#fbf8f2",
                  hover="#e9e2d2", field="#fffdf8", text="#2b2620", muted="#7a6f60",
                  accent="#b4532a", accent_hover="#9a4522", on_accent="#ffffff", good="#4d7c0f", line="#ddd4c1"),
    "paper_dark": dict(name="Paper Night", dark=True, flat=True, bg="#1c1814", sidebar="#201b16", card="#26211b",
                       hover="#322b23", field="#2b251e", text="#eadfcb", muted="#a39881",
                       accent="#e08a5c", accent_hover="#eba078", on_accent="#ffffff", good="#a3e635", line="#3a3228"),
}

ACCENTS = ["#4f46e5", "#0f766e", "#be185d", "#ea580c", "#16a34a", "#e11d48", "#475569", "#ca8a04", "#2563eb"]

# which theme each (design style, light/dark) pair maps to
STYLES = {"quiet": ("qp_light", "qp_dark"), "paper": ("paper", "paper_dark"), "classic": ("daylight", "indigo_night")}


def style_of(name: str) -> str:
    for k, (a, b) in STYLES.items():
        if name in (a, b):
            return k
    return "classic"


def _lum(h: str) -> float:
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast_text(bg: str) -> str:
    """White or near-black, whichever reads better on bg (WCAG contrast)."""
    l = _lum(bg)
    white = 1.05 / (l + 0.05)
    black = (l + 0.05) / (_lum("#14110a") + 0.05)
    return "#ffffff" if white >= black else "#14110a"


def _mix(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join("%02x" % int(int(a[i:i + 2], 16) + (int(b[i:i + 2], 16) - int(a[i:i + 2], 16)) * t) for i in (0, 2, 4))


for _t in THEMES.values():
    _t["on_accent"] = contrast_text(_t["accent"])
    _t.setdefault("flat", False)
    _t.setdefault("line", _mix(_t["card"], _t["text"], 0.14))


def resolve(name: str, accent: str = "") -> dict:
    """A theme palette, optionally with the user's own accent colour."""
    P = dict(THEMES.get(name) or THEMES["indigo_night"])
    if accent and len(accent) == 7:
        P["accent"] = accent
        P["accent_hover"] = _mix(accent, "#ffffff" if P["dark"] else "#000000", 0.18)
        P["on_accent"] = contrast_text(accent)
    return P


class _State:
    name = "indigo_night"
    accent = ""
    pal = THEMES["indigo_night"]


STATE = _State()


def set_theme(name: str, accent: str | None = None) -> dict:
    if accent is not None:
        STATE.accent = accent
    STATE.name = name if name in THEMES else "indigo_night"
    STATE.pal = resolve(STATE.name, STATE.accent)
    return STATE.pal
