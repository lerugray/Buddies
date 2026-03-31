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
        min-height: 8;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self, **kwargs):
        initial = get_sprite("duck", 0, False)
        super().__init__(initial, markup=True, **kwargs)
        self.species = "duck"
        self.shiny = False
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
        sprite = get_sprite(self.species, self._frame, self.shiny)
        self.update(sprite)

    def set_species(self, species: str, shiny: bool = False):
        self.species = species
        self.shiny = shiny
        self._frame = 0
        self._frame_count = get_frame_count(species)
        self.refresh_sprite()


class StatsDisplay(Static):
    """Shows buddy stats, level, and mood."""

    DEFAULT_CSS = """
    StatsDisplay {
        height: auto;
        padding: 1 0 0 0;
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
        xp_bar_width = 16
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

        lines = [
            f"[bold {color}]{state.species.emoji} {state.name}[/]  [{color}]{rarity.upper()}[/]{shiny_tag}",
            f"[dim]{state.species.description}[/]",
            "",
            f"Lv.{state.level}  {xp_bar}  {state.xp}/{xp_next} XP",
            f"Mood: {mood_icon} {state.mood.capitalize()} ({state.mood_value}/100)",
            "",
            f"[red]⚔ DEBUG[/]  {state.stats['debugging']:>3}   [blue]🛡 PATIENCE[/] {state.stats['patience']:>3}",
            f"[magenta]💥 CHAOS[/]  {state.stats['chaos']:>3}   [cyan]📖 WISDOM[/]  {state.stats['wisdom']:>3}",
            f"[yellow]💬 SNARK[/]  {state.stats['snark']:>3}",
        ]

        if state.soul_description:
            lines.append("")
            lines.append(f"[dim italic]\"{state.soul_description}\"[/]")

        self.update("\n".join(lines))


class BuddyDisplay(Vertical):
    """Combined buddy display with sprite and stats."""

    DEFAULT_CSS = """
    BuddyDisplay {
        width: 1fr;
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield SpriteDisplay(id="buddy-sprite")
        yield StatsDisplay(id="buddy-stats")

    def update_buddy(self, state: BuddyState):
        self.query_one("#buddy-sprite", SpriteDisplay).set_species(
            state.species.name, state.shiny
        )
        self.query_one("#buddy-stats", StatsDisplay).render_stats(state)
