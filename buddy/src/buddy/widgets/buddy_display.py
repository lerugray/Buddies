"""Buddy display widget — shows the pixel art sprite, stats, and mood."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from buddy.art.sprites import get_sprite, get_frame_count
from buddy.core.buddy_brain import BuddyState, xp_for_next_level


class SpriteDisplay(Static):
    """Renders the animated pixel art sprite with Rich markup colors."""

    DEFAULT_CSS = """
    SpriteDisplay {
        height: auto;
        min-height: 10;
        width: 1fr;
        content-align: center middle;
        text-align: center;
        overflow: auto;
    }
    """

    def __init__(self, **kwargs):
        initial = get_sprite("duck", 0, False)
        super().__init__(initial, markup=True, **kwargs)
        self.species = "duck"
        self.shiny = False
        self.hat: str | None = None
        self._frame = 0
        self._frame_count = 2

    def on_mount(self):
        self.refresh_sprite()
        self.set_interval(1.0, self.advance_frame)

    def advance_frame(self):
        """Advance to next animation frame and update display."""
        self._frame = (self._frame + 1) % self._frame_count
        self.refresh_sprite()

    def refresh_sprite(self):
        """Update the displayed sprite."""
        sprite = get_sprite(self.species, self._frame, self.shiny, hat=self.hat)
        self.update(sprite)

    def set_species(self, species: str, shiny: bool = False, hat: str | None = None):
        self.species = species
        self.shiny = shiny
        self.hat = hat
        self._frame = 0
        self._frame_count = get_frame_count(species)
        self.refresh_sprite()


class StatsDisplay(Static):
    """Shows buddy stats, level, and mood."""

    DEFAULT_CSS = """
    StatsDisplay {
        height: auto;
        width: 1fr;
        padding: 1 0 0 0;
        overflow: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("Loading...", markup=True, **kwargs)

    def render_stats(self, state: BuddyState):
        rarity_colors = {
            "common": "white",
            "uncommon": "green",
            "rare": "cyan",
            "epic": "magenta",
            "legendary": "yellow",
        }
        rarity = state.species.rarity.value
        color = rarity_colors.get(rarity, "white")
        shiny_tag = " ✨SHINY✨" if state.shiny else ""

        xp_next = xp_for_next_level(state.level)
        xp_bar_width = 12  # Reduced from 16 for narrow terminals
        xp_progress = min(state.xp / max(xp_next, 1), 1.0)
        filled = int(xp_progress * xp_bar_width)
        xp_bar = "█" * filled + "░" * (xp_bar_width - filled)

        mood_icons = {
            "ecstatic": "😄",
            "happy": "🙂",
            "neutral": "😐",
            "bored": "😒",
            "grumpy": "😠",
        }
        mood_icon = mood_icons.get(state.mood, "😐")

        # Hat display: current hat or empty
        hat_line = f"🎩 {state.hat}" if state.hat else ""

        # Truncate owned hats: show first 3, then +N count
        owned_hats = state.hats_owned if state.hats_owned else []
        if len(owned_hats) > 3:
            hats_display = ", ".join(owned_hats[:3]) + f" +{len(owned_hats) - 3}"
        else:
            hats_display = ", ".join(owned_hats) if owned_hats else "none"

        lines = [
            f"[bold {color}]{state.species.emoji} {state.name}[/]  [{color}]{rarity.upper()}[/]{shiny_tag}",
            f"[dim]{state.species.description[:40]}[/]",  # Truncate description
            "",
            f"Lv.{state.level} {xp_bar} {state.xp}/{xp_next}",
            f"{mood_icon} {state.mood.capitalize()}",
            "",
            f"🎩 Owned: {hats_display}",
            "",
            # Stats in compact format, one per line
            f"[red]⚔[/] DEBUG   {state.stats['debugging']:>3}",
            f"[blue]🛡[/] PATIENCE {state.stats['patience']:>3}",
            f"[magenta]💥[/] CHAOS   {state.stats['chaos']:>3}",
            f"[cyan]📖[/] WISDOM  {state.stats['wisdom']:>3}",
            f"[yellow]💬[/] SNARK   {state.stats['snark']:>3}",
        ]

        if state.soul_description:
            # Truncate soul description to 50 chars with ellipsis
            soul_text = state.soul_description[:50]
            if len(state.soul_description) > 50:
                soul_text += "..."
            lines.append("")
            lines.append(f"[dim italic]\"{soul_text}\"[/]")

        self.update("\n".join(lines))


class BuddyDisplay(Vertical):
    """Combined buddy display with sprite and stats."""

    DEFAULT_CSS = """
    BuddyDisplay {
        width: 1fr;
        height: auto;
        min-height: 20;
        border: solid $primary;
        padding: 1;
        overflow: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield SpriteDisplay(id="buddy-sprite")
        yield StatsDisplay(id="buddy-stats")

    def update_buddy(self, state: BuddyState):
        self.query_one("#buddy-sprite", SpriteDisplay).set_species(
            state.species.name, state.shiny, hat=state.hat
        )
        self.query_one("#buddy-stats", StatsDisplay).render_stats(state)
