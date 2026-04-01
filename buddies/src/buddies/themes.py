"""Theme definitions for Buddies TUI.

Each theme defines colors that Textual's design system uses.
Themes cycle with [F2] and the choice persists in config.
"""

from __future__ import annotations

from textual.theme import Theme


# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

BUDDY_THEMES: dict[str, Theme] = {
    "default": Theme(
        name="default",
        primary="#88aaff",
        secondary="#aa88ff",
        accent="#ffaa44",
        background="#1a1a2e",
        surface="#16213e",
        panel="#0f3460",
        warning="#ffaa44",
        error="#ff4444",
        success="#44ff88",
        dark=True,
    ),
    "midnight": Theme(
        name="midnight",
        primary="#6644cc",
        secondary="#cc44aa",
        accent="#ff6688",
        background="#0d0d1a",
        surface="#1a1a33",
        panel="#2a1a4a",
        warning="#ffcc44",
        error="#ff4466",
        success="#44ccaa",
        dark=True,
    ),
    "forest": Theme(
        name="forest",
        primary="#44aa66",
        secondary="#88cc44",
        accent="#ccaa44",
        background="#0a1a0a",
        surface="#1a2a1a",
        panel="#0a3a1a",
        warning="#ccaa44",
        error="#cc4444",
        success="#44cc44",
        dark=True,
    ),
    "ocean": Theme(
        name="ocean",
        primary="#4488cc",
        secondary="#44aacc",
        accent="#44cccc",
        background="#0a1a2a",
        surface="#0a2a3a",
        panel="#0a3a4a",
        warning="#ccaa44",
        error="#cc4466",
        success="#44ccaa",
        dark=True,
    ),
    "sunset": Theme(
        name="sunset",
        primary="#cc6644",
        secondary="#cc8844",
        accent="#ccaa44",
        background="#1a0a0a",
        surface="#2a1a0a",
        panel="#3a1a0a",
        warning="#cccc44",
        error="#cc4444",
        success="#88cc44",
        dark=True,
    ),
    "light": Theme(
        name="light",
        primary="#3366aa",
        secondary="#6633aa",
        accent="#aa6633",
        background="#f0f0f0",
        surface="#ffffff",
        panel="#e0e8f0",
        warning="#aa6600",
        error="#cc2222",
        success="#228844",
        dark=False,
    ),
}

# Order for cycling
THEME_ORDER = ["default", "midnight", "forest", "ocean", "sunset", "light"]


def get_theme(name: str) -> Theme:
    """Get a theme by name, falling back to default."""
    return BUDDY_THEMES.get(name, BUDDY_THEMES["default"])


def next_theme(current: str) -> str:
    """Get the next theme name in the cycle."""
    try:
        idx = THEME_ORDER.index(current)
        return THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
    except ValueError:
        return THEME_ORDER[0]
