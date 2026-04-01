"""MudScreen — text adventure TUI for the StackHaven MUD.

Full text-adventure interface with scrolling output, command input,
minimap panel, and party status. Launched from the Games Arcade.

Phase 2: GitHub Issues transport for cross-user multiplayer.
Notes, bloodstains, and phantoms sync to/from lerugray/buddies-bbs.
"""

from __future__ import annotations

import asyncio
import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input
from textual.screen import Screen

from buddies.config import BuddyConfig
from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.mud_engine import (
    MudState, create_mud_game, process_command, get_intro_text, get_game_result,
)
from buddies.core.games.mud_transport import MudTransport

log = logging.getLogger(__name__)


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
        self._transport: MudTransport | None = None

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
        # Phase 2: Background sync with GitHub
        asyncio.create_task(self._init_transport())

    async def _init_transport(self):
        """Initialize GitHub transport and sync remote data in background."""
        try:
            config = BuddyConfig.load()
            if not config.bbs.enabled:
                return

            self._transport = MudTransport(config.bbs)
            await self._transport.connect()

            if not await self._transport.is_available():
                log.info("MUD transport: remote not available, staying local")
                self._transport = None
                return

            # Store transport reference in game state for engine access
            self.mud_state.mp_transport = self._transport

            # Sync remote data into local store
            if self.mud_state.mp_store:
                output = self.query_one("#mud-output", RichLog)
                output.write("\n[dim]📡 Connecting to the StackHaven network...[/dim]")

                counts = await self._transport.sync_to_local(self.mud_state.mp_store)
                self.mud_state.remote_notes_synced = counts["notes"]
                self.mud_state.remote_stains_synced = counts["bloodstains"]

                total = counts["notes"] + counts["bloodstains"]
                if total > 0:
                    output.write(
                        f"[dim]📡 Synced {counts['notes']} note(s) and "
                        f"{counts['bloodstains']} bloodstain(s) from other adventurers.[/dim]"
                    )
                    output.write(
                        "[dim]Type [bold]rumors[/bold] to hear what they've been up to.[/dim]"
                    )
                else:
                    output.write("[dim]📡 Connected. No new messages from other adventurers.[/dim]")

        except Exception as e:
            log.warning("MUD transport init failed: %s", e)
            self._transport = None

    async def _push_note(self, note_id: str):
        """Push a specific note to GitHub in background."""
        if not self._transport or not self.mud_state.mp_store:
            return
        for note in self.mud_state.mp_store.notes:
            if note.id == note_id:
                await self._transport.push_note(note)
                break

    async def _push_bloodstain(self, stain_id: str):
        """Push a specific bloodstain to GitHub in background."""
        if not self._transport or not self.mud_state.mp_store:
            return
        for stain in self.mud_state.mp_store.bloodstains:
            if stain.id == stain_id:
                await self._transport.push_bloodstain(stain)
                break

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input."""
        raw = event.value.strip()
        if not raw:
            return

        event.input.clear()
        output = self.query_one("#mud-output", RichLog)

        # Track state before command for detecting new notes/bloodstains
        notes_before = self.mud_state.notes_left
        stains_before = len(self.mud_state.mp_store.bloodstains) if self.mud_state.mp_store else 0

        # Echo command
        output.write(f"\n[bold green]> {raw}[/bold green]")

        # Process
        lines = process_command(self.mud_state, raw)
        for line in lines:
            output.write(line)

        self._update_sidebar()

        # Phase 2: Auto-push new notes and bloodstains to GitHub
        if self._transport and self.mud_state.mp_store:
            if self.mud_state.notes_left > notes_before:
                # A new note was just left — push it
                newest_note = self.mud_state.mp_store.notes[-1]
                asyncio.create_task(self._push_note(newest_note.id))

            current_stains = len(self.mud_state.mp_store.bloodstains)
            if current_stains > stains_before:
                # A death just happened — push the bloodstain
                newest_stain = self.mud_state.mp_store.bloodstains[-1]
                asyncio.create_task(self._push_bloodstain(newest_stain.id))

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
        # Clean up transport
        if self._transport:
            asyncio.create_task(self._transport.close())
        self._result = get_game_result(self.mud_state, self.buddy_state.buddy_id)
        self.dismiss(self._result)
