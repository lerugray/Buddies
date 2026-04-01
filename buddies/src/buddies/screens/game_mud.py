"""MudScreen — text adventure TUI for the StackHaven MUD.

Full text-adventure interface with scrolling output, command input,
minimap panel, and party status. Launched from the Games Arcade.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.mud_engine import (
    MudState, create_mud_game, process_command, get_intro_text, get_game_result,
)


class MudScreen(Screen):
    """The StackHaven MUD — a text adventure in a tech company gone wrong."""

    BINDINGS = [
        Binding("escape", "quit_mud", "Exit MUD", show=True),
    ]

    DEFAULT_CSS = """
    MudScreen {
        layout: horizontal;
        background: $background;
    }
    MudScreen #mud-main {
        width: 3fr;
        height: 100%;
    }
    MudScreen #mud-output {
        height: 1fr;
        padding: 0 1;
        background: $surface;
        border: round $primary;
        margin: 0 0 0 1;
    }
    MudScreen #mud-input {
        dock: bottom;
        margin: 0 0 0 1;
    }
    MudScreen #mud-sidebar {
        width: 1fr;
        min-width: 22;
        max-width: 30;
        height: 100%;
        margin: 0 1 0 0;
    }
    MudScreen #mud-map {
        height: auto;
        max-height: 50%;
        padding: 1;
        background: $surface;
        border: round $accent;
    }
    MudScreen #mud-party {
        height: auto;
        max-height: 50%;
        padding: 1;
        background: $surface;
        border: round $success;
        margin-top: 1;
    }
    """

    def __init__(self, buddy_state: BuddyState, party_states: list[BuddyState] | None = None):
        super().__init__()
        self.buddy_state = buddy_state
        self.party_states = party_states or []
        all_buddies = [buddy_state] + self.party_states
        self.mud_state = create_mud_game(all_buddies)
        self._result: GameResult | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="mud-main"):
                yield RichLog(id="mud-output", wrap=True, markup=True, auto_scroll=True)
                yield Input(id="mud-input", placeholder="Enter command (help for commands)...")
            with Vertical(id="mud-sidebar"):
                yield Static(id="mud-map")
                yield Static(id="mud-party")
        yield Footer()

    def on_mount(self):
        output = self.query_one("#mud-output", RichLog)
        for line in get_intro_text(self.mud_state):
            output.write(line)
        self._update_sidebar()
        # Focus the input
        self.query_one("#mud-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input."""
        raw = event.value.strip()
        if not raw:
            return

        event.input.clear()
        output = self.query_one("#mud-output", RichLog)

        # Echo command
        output.write(f"\n[bold green]> {raw}[/bold green]")

        # Process
        lines = process_command(self.mud_state, raw)
        for line in lines:
            output.write(line)

        self._update_sidebar()

    def _update_sidebar(self):
        """Update the minimap and party panels."""
        # Minimap
        map_widget = self.query_one("#mud-map", Static)
        room = self.mud_state.rooms[self.mud_state.current_room]
        map_lines = [f"[bold]🗺️ {room.emoji} {room.name}[/bold]", ""]

        # Show exits
        for ex in room.exits:
            if ex.hidden:
                continue
            arrow = {"north": "↑", "south": "↓", "east": "→", "west": "←", "up": "⬆", "down": "⬇"}.get(ex.direction, "•")
            dest = self.mud_state.rooms.get(ex.destination)
            dest_name = dest.name if dest else ex.destination
            lock = " 🔒" if ex.locked else ""
            visited = " ✓" if dest and dest.visited else ""
            map_lines.append(f" {arrow} {ex.direction}: {dest_name}{lock}{visited}")

        map_lines.append(f"\n[dim]Explored: {self.mud_state.rooms_visited}/{len(self.mud_state.rooms)}[/dim]")
        map_lines.append(f"[yellow]Gold: {self.mud_state.inventory.gold}g[/yellow]")
        map_widget.update("\n".join(map_lines))

        # Party panel
        party_widget = self.query_one("#mud-party", Static)
        party_lines = ["[bold]👥 Party[/bold]", ""]
        for b in self.mud_state.party:
            party_lines.append(f"{b.species.emoji} {b.name}")
            party_lines.append(f"  Lv.{b.level} {b.species.name}")

        # Combat status
        if self.mud_state.combat and self.mud_state.combat.active:
            c = self.mud_state.combat
            party_lines.append("")
            party_lines.append("[bold red]⚔️ In Combat![/bold red]")
            party_lines.append(f"You: {c.player.hp_bar(10)}")
            party_lines.append(f"{c.enemy.emoji}: {c.enemy.hp_bar(10)}")

        # Quest count
        active_quests = sum(1 for q in self.mud_state.quests.values() if q.status.value == "active")
        if active_quests:
            party_lines.append(f"\n[cyan]📋 {active_quests} active quest(s)[/cyan]")

        # Items
        n_items = len(self.mud_state.inventory.items)
        if n_items:
            party_lines.append(f"[dim]📦 {n_items} item(s)[/dim]")

        # Soapstone status
        has_soapstone = self.mud_state.inventory.has_item("orange_soapstone")
        if has_soapstone:
            party_lines.append(f"[yellow]🧡 Soapstone[/yellow]")
        if self.mud_state.notes_left:
            party_lines.append(f"[dim]📜 {self.mud_state.notes_left} note(s) left[/dim]")

        party_widget.update("\n".join(party_lines))

    def action_quit_mud(self):
        """Exit the MUD and return results."""
        self._result = get_game_result(self.mud_state, self.buddy_state.buddy_id)
        self.dismiss(self._result)
