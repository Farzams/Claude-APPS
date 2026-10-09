"""Colour themes and a tiny style registry.

Widgets are registered with {option: role}. Switching theme only re-colours the pages
that are visible; hidden pages catch up the next time they are shown. This avoids
CustomTkinter's slow "re-theme every widget" appearance switch.
"""
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
}


class _State:
    name = "indigo_night"
    pal = THEMES["indigo_night"]
    version = 0
    owner = "chrome"


STATE = _State()
_registry: dict[str, list] = {}
_applied: dict[str, int] = {}


def set_theme(name: str) -> dict:
    STATE.name = name if name in THEMES else "indigo_night"
    STATE.pal = THEMES[STATE.name]
    STATE.version += 1
    return STATE.pal


def set_owner(owner: str) -> None:
    STATE.owner = owner


def col(role: str) -> str:
    """Colour for a role; 'transparent' passes through; '#rrggbb' strings are used as-is."""
    if role == "transparent" or role.startswith("#"):
        return role
    return STATE.pal[role]


def style(widget, **roles):
    """Configure widget now and remember the roles so the theme can re-apply them."""
    _registry.setdefault(STATE.owner, []).append((widget, roles))
    try:
        widget.configure(**{k: col(v) for k, v in roles.items()})
    except Exception:
        pass
    return widget


def apply(owner: str) -> None:
    """Re-colour one owner's widgets (only if its colours are out of date)."""
    if _applied.get(owner) == STATE.version:
        return
    _applied[owner] = STATE.version
    for widget, roles in _registry.get(owner, []):
        try:
            widget.configure(**{k: col(v) for k, v in roles.items()})
        except Exception:
            pass


def mark_built(owner: str) -> None:
    _applied[owner] = STATE.version
