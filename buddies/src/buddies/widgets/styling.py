"""Centralized styling utilities for buddy messages and UI elements.

Single source of truth for rarity colors, register accent colors, and
Rich-markup message formatting used across the TUI.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Rarity colors — used everywhere buddies are displayed
# ---------------------------------------------------------------------------

RARITY_COLORS: dict[str, str] = {
    "common": "white",
    "uncommon": "green",
    "rare": "cyan",
    "epic": "magenta",
    "legendary": "yellow",
}

RARITY_STARS: dict[str, str] = {
    "common": "★",
    "uncommon": "★★",
    "rare": "★★★",
    "epic": "★★★★",
    "legendary": "★★★★★",
}

# ---------------------------------------------------------------------------
# Register accent colors — each personality voice gets a color
# ---------------------------------------------------------------------------

REGISTER_COLORS: dict[str, str] = {
    "clinical": "blue",
    "sarcastic": "yellow",
    "absurdist": "magenta",
    "philosophical": "cyan",
    "calm": "green",
}

# Unicode left-border character for discussion mode
DISCUSSION_BORDER = "│"


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

def format_buddy_message(
    name: str,
    message: str,
    rarity: str = "common",
    emoji: str = "",
) -> str:
    """Format a buddy's chat message with rarity-colored name.

    Used in regular chat mode for the active buddy.
    """
    color = RARITY_COLORS.get(rarity, "white")
    prefix = f"{emoji} " if emoji else ""
    return f"[bold {color}]{prefix}{name}:[/] {message}"


def format_discussion_message(
    name: str,
    message: str,
    rarity: str = "common",
    register: str = "calm",
    emoji: str = "",
) -> str:
    """Format a buddy's message for discussion mode with colored left border.

    Produces output like:
        │ 🐱 Whiskers (sarcastic):
        │ Oh great, another group discussion...
    """
    name_color = RARITY_COLORS.get(rarity, "white")
    border_color = REGISTER_COLORS.get(register, "white")
    prefix = f"{emoji} " if emoji else ""
    border = f"[{border_color}]{DISCUSSION_BORDER}[/]"

    # Header line with name and register tag
    header = f"{border} [bold {name_color}]{prefix}{name}[/] [dim]({register})[/]"

    # Wrap message lines with border
    lines = message.split("\n")
    body = "\n".join(f"{border} {line}" for line in lines)

    return f"{header}\n{body}"


def format_system_message(message: str) -> str:
    """Format a system/status message."""
    return f"[dim italic]{message}[/]"
