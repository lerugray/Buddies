"""Buddy display widget — shows the pixel art sprite, stats, and mood."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from buddies.art.sprites import get_sprite, get_frame_count
from buddies.core.buddy_brain import BuddyState, xp_for_next_level, get_evolution_stage


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

    # Animation speeds for different activity levels
    ANIM_SPEEDS = {
        "excited": 0.4,   # Fast cycling during active sessions
        "normal": 1.0,    # Default idle
        "sleepy": 2.5,    # Slow when nothing happening
    }

    def __init__(self, **kwargs):
        initial = get_sprite("duck", 0, False)
        super().__init__(initial, markup=True, **kwargs)
        self.species = "duck"
        self.shiny = False
        self.hat: str | None = None
        self.evolution_border: str | None = None
        self._frame = 0
        self._frame_count = 2
        self._activity = "normal"
        self._timer = None
        self._celebration_frames = 0

    def on_mount(self):
        self.refresh_sprite()
        self._timer = self.set_interval(1.0, self.advance_frame)

    def set_activity(self, level: str):
        """Change animation speed: 'excited', 'normal', or 'sleepy'."""
        if level == self._activity:
            return
        self._activity = level
        speed = self.ANIM_SPEEDS.get(level, 1.0)
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(speed, self.advance_frame)

    def celebrate(self, frames: int = 6):
        """Briefly speed up animation for level-up/evolution."""
        self._celebration_frames = frames
        old_activity = self._activity
        self.set_activity("excited")
        # Will auto-revert after celebration_frames ticks

    def advance_frame(self):
        """Advance to next animation frame and update display."""
        self._frame = (self._frame + 1) % self._frame_count
        self.refresh_sprite()
        # Handle celebration countdown
        if self._celebration_frames > 0:
            self._celebration_frames -= 1
            if self._celebration_frames == 0:
                self.set_activity("normal")

    def refresh_sprite(self):
        """Update the displayed sprite."""
        sprite = get_sprite(
            self.species, self._frame, self.shiny,
            hat=self.hat, evolution_border=self.evolution_border,
        )
        self.update(sprite)

    def set_species(
        self, species: str, shiny: bool = False,
        hat: str | None = None, evolution_border: str | None = None,
    ):
        self.species = species
        self.shiny = shiny
        self.hat = hat
        self.evolution_border = evolution_border
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

    def _truncate_at_word(self, text: str, max_len: int) -> str:
        """Truncate text at word boundary, add ellipsis if needed."""
        if len(text) <= max_len:
            return text
        truncated = text[:max_len].rsplit(" ", 1)[0]
        return truncated + "…" if truncated else text[:max_len - 1] + "…"

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

        # Scale XP bar and truncation to available width
        panel_w = self.size.width if self.size.width > 10 else 30
        text_limit = max(20, panel_w - 4)
        xp_bar_width = max(6, min(16, panel_w - 18))

        xp_next = xp_for_next_level(state.level)
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

        desc = self._truncate_at_word(state.species.description, text_limit)

        # Truncate owned hats: show first 3, then +N count
        owned_hats = state.hats_owned if state.hats_owned else []
        if len(owned_hats) > 3:
            hats_display = ", ".join(owned_hats[:3]) + f" +{len(owned_hats) - 3}"
        else:
            hats_display = ", ".join(owned_hats) if owned_hats else "none"

        stage = get_evolution_stage(state.level)

        lines = [
            f"[bold {color}]{state.species.emoji} {state.name}[/]  [{color}]{rarity.upper()}[/]{shiny_tag}",
            f"[dim]{desc}[/]",
            f"{stage['symbol']} {stage['name']}",
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
            soul_text = self._truncate_at_word(state.soul_description, text_limit)
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
        stage = get_evolution_stage(state.level)
        self.query_one("#buddy-sprite", SpriteDisplay).set_species(
            state.species.name, state.shiny,
            hat=state.hat, evolution_border=stage.get("border"),
        )
        self.query_one("#buddy-stats", StatsDisplay).render_stats(state)
