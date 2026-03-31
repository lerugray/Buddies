"""First-run setup screen — species selection with gacha mechanics.

Shown on first launch. User can:
1. Use their username as seed (deterministic)
2. Enter a custom seed
3. Random roll (time-based seed)
4. Keep rerolling until they like what they get
"""

from __future__ import annotations

import time
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, VerticalScroll
from textual.widgets import Static, Input, Button
from textual.screen import Screen

from buddies.art.sprites import get_sprite
from buddies.core.buddy_brain import pick_species, Species, Rarity


RARITY_COLORS = {
    Rarity.COMMON: "white",
    Rarity.UNCOMMON: "green",
    Rarity.RARE: "cyan",
    Rarity.EPIC: "magenta",
    Rarity.LEGENDARY: "yellow",
}

RARITY_LABELS = {
    Rarity.COMMON: "★ Common (40%)",
    Rarity.UNCOMMON: "★★ Uncommon (30%)",
    Rarity.RARE: "★★★ Rare (18%)",
    Rarity.EPIC: "★★★★ Epic (9%)",
    Rarity.LEGENDARY: "★★★★★ Legendary (3%)",
}


class HatchScreen(Screen):
    """The egg-hatching / species selection screen."""

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=True),
    ]

    def action_quit_app(self):
        self.app.exit()

    CSS = """
    HatchScreen {
        align: center middle;
        background: $background;
    }

    #hatch-scroll {
        width: 1fr;
        max-width: 50;
        height: 1fr;
        border: double $primary;
        padding: 1 2;
        margin: 1 2;
    }

    #hatch-container {
        width: 1fr;
        height: auto;
    }

    #hatch-title {
        text-align: center;
        text-style: bold;
        color: $text;
    }

    #sprite-preview {
        height: auto;
        min-height: 6;
        text-align: center;
        content-align: center middle;
    }

    #species-info {
        text-align: center;
        height: auto;
    }

    #seed-input {
        margin: 0;
    }

    #name-input {
        margin: 0;
    }

    #button-row {
        align: center middle;
        height: auto;
    }

    Button {
        width: 100%;
        margin: 0;
    }
    """

    def __init__(self):
        super().__init__()
        self._current_seed = os.environ.get("USER", os.environ.get("USERNAME", "buddy"))
        self._current_species: Species | None = None
        self._current_shiny = False
        self._roll_count = 0

    def compose(self) -> ComposeResult:
        with Center():
            with VerticalScroll(id="hatch-scroll"):
                with Vertical(id="hatch-container"):
                    yield Static("🥚 HATCH A NEW BUDDY 🥚", id="hatch-title")
                    yield Static("", id="sprite-preview")
                    yield Static("", id="species-info")
                    yield Input(
                        placeholder="Name your buddy...",
                        id="name-input",
                        value="Buddy",
                    )
                    yield Input(
                        placeholder="Enter a seed (or leave blank for username)",
                        id="seed-input",
                        value=self._current_seed,
                    )
                    with Vertical(id="button-row"):
                        yield Button("Roll with Seed", id="btn-seed", variant="primary")
                        yield Button("Random Roll!", id="btn-random", variant="warning")
                        yield Button("✓ Keep This One", id="btn-accept", variant="success", disabled=True)

    def on_mount(self):
        self._roll_with_seed(self._current_seed)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-seed":
            seed_input = self.query_one("#seed-input", Input)
            seed = seed_input.value.strip() or self._current_seed
            self._roll_with_seed(seed)
        elif event.button.id == "btn-random":
            random_seed = f"roll-{time.time_ns()}"
            self._roll_with_seed(random_seed)
        elif event.button.id == "btn-accept":
            name = self.query_one("#name-input", Input).value.strip() or "Buddy"
            self.dismiss((self._current_species, self._current_shiny, self._current_seed, name))

    def _roll_with_seed(self, seed: str):
        self._current_seed = seed
        self._roll_count += 1
        species, shiny = pick_species(seed)
        self._current_species = species
        self._current_shiny = shiny

        # Update sprite preview
        sprite_widget = self.query_one("#sprite-preview", Static)
        sprite = get_sprite(species.name, 0, shiny)
        sprite_widget.update(sprite)

        # Update species info
        info = self.query_one("#species-info", Static)
        color = RARITY_COLORS.get(species.rarity, "white")
        rarity_label = RARITY_LABELS.get(species.rarity, "")
        shiny_text = " [bold yellow]✨ SHINY! ✨[/]" if shiny else ""

        info.update(
            f"[bold {color}]{species.emoji} {species.name.upper()}[/]{shiny_text}\n"
            f"[{color}]{rarity_label}[/]\n"
            f"[dim]{species.description}[/]\n\n"
            f"[dim]Roll #{self._roll_count} — seed: \"{seed[:30]}\"[/]"
        )

        # Enable accept button
        accept = self.query_one("#btn-accept", Button)
        accept.disabled = False
