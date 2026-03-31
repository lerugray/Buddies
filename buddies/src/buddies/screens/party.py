"""PartyScreen — manage your buddy collection.

Shows all hatched buddies, allows switching active buddy, renaming, and hat equipping.
"""

from __future__ import annotations

import asyncio
import json
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, ScrollableContainer
from textual.widgets import Static, Button, Footer
from textual.screen import Screen

from buddies.db.store import BuddyStore
from buddies.core.buddy_brain import HAT_UNLOCK_RULES


class PartyScreen(Screen):
    """Manage buddy collection — switch, rename, equip hats."""

    CSS = """
    PartyScreen {
        align: center middle;
        background: $background;
    }

    #party-container {
        width: 90%;
        max-width: 80;
        height: auto;
        border: double $primary;
        padding: 1 2;
        margin: 1 2;
    }

    #party-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #buddies-list {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        width: 1fr;
        overflow: auto;
    }

    .buddy-row {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: none;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("enter", "switch_buddy", "Switch", show=True),
        Binding("h", "cycle_hat", "Hat", show=True),
        Binding("delete", "release_buddy", "Release", show=True),
        Binding("plus", "hatch", "Hatch New", show=True),
        Binding("up", "navigate_up", "Up", show=False),
        Binding("down", "navigate_down", "Down", show=False),
    ]

    def __init__(self, store: BuddyStore):
        super().__init__()
        self.store = store
        self.buddies: list[dict] = []
        self.selected_idx = 0

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="party-container"):
                yield Static("🐾 BUDDY PARTY 🐾", id="party-title")
                yield ScrollableContainer(Vertical(id="buddies-list"))
        yield Footer()

    async def on_mount(self):
        """Load all buddies and display them."""
        self.buddies = await self.store.get_all_buddies()
        if not self.buddies:
            buddies_list = self.query_one("#buddies-list", Vertical)
            await buddies_list.mount(Static("[dim]No buddies yet. Hatch your first one![/]"))
            return

        # Find active buddy
        active_idx = next(
            (i for i, b in enumerate(self.buddies) if b.get("is_active")),
            0
        )
        self.selected_idx = active_idx

        await self._render_buddies()

    async def _render_buddies(self):
        """Render the list of buddies."""
        buddies_list = self.query_one("#buddies-list", Vertical)

        # Remove all existing children
        await buddies_list.query("Static").remove()

        # Create and mount new buddy rows
        rows = []
        for idx, buddy in enumerate(self.buddies):
            is_active = "★ " if buddy.get("is_active") else "  "
            is_selected = "[reverse]" if idx == self.selected_idx else ""
            end_tag = "[/]" if idx == self.selected_idx else ""

            rarity_colors = {
                "common": "white",
                "uncommon": "green",
                "rare": "cyan",
                "epic": "magenta",
                "legendary": "yellow",
            }
            rarity = buddy.get("species", "unknown").lower()
            color = rarity_colors.get(rarity, "white")

            # Truncate buddy name to 15 chars
            buddy_name = buddy.get('name', 'Buddy')[:15]

            # Hat display: just emoji if exists
            hat_str = " 🎩" if buddy.get("hat") else ""

            # Compact format: active | species | name | level | hat
            text = (
                f"{is_selected}{is_active}"
                f"[{color}]{buddy.get('species', '?')[:8]}[/] "
                f"{buddy_name:<15} "
                f"L{buddy.get('level', 1)}"
                f"{hat_str}"
                f"{end_tag}"
            )
            row = Static(text, classes="buddy-row")
            rows.append(row)

        await buddies_list.mount(*rows)

    def action_close(self):
        """Close the party screen without switching."""
        self.dismiss(None)

    def action_switch_buddy(self):
        """Switch to selected buddy."""
        if 0 <= self.selected_idx < len(self.buddies):
            buddy_id = self.buddies[self.selected_idx]["id"]
            self.dismiss(buddy_id)

    def action_release_buddy(self):
        """Delete the selected buddy from the collection."""
        asyncio.create_task(self._do_release_buddy())

    async def _do_release_buddy(self):
        """Async logic for releasing/deleting a buddy."""
        if not (0 <= self.selected_idx < len(self.buddies)):
            return

        buddy = self.buddies[self.selected_idx]
        buddy_id = buddy["id"]
        buddy_name = buddy.get("name", "Buddy")

        # Delete from DB using store method
        try:
            await self.store.delete_buddy(buddy_id)
        except Exception as e:
            # In a real app, show error dialog
            return

        # Reload buddies
        self.buddies = await self.store.get_all_buddies()

        if not self.buddies:
            # All buddies deleted, show empty state
            await self._render_buddies()
            return

        # Adjust selection if needed
        if self.selected_idx >= len(self.buddies):
            self.selected_idx = len(self.buddies) - 1

        await self._render_buddies()

    def action_cycle_hat(self):
        """Cycle to next hat for selected buddy."""
        asyncio.create_task(self._do_cycle_hat())

    async def _do_cycle_hat(self):
        """Async logic for hat cycling."""
        if not (0 <= self.selected_idx < len(self.buddies)):
            return

        buddy = self.buddies[self.selected_idx]
        buddy_id = buddy["id"]
        hats_owned = buddy.get("hats_owned", "[]")

        # Parse JSON if string
        if isinstance(hats_owned, str):
            try:
                hats_owned = json.loads(hats_owned)
            except json.JSONDecodeError:
                hats_owned = []

        if not hats_owned:
            return

        # Cycle: None → hat[0] → hat[1] → ... → None
        current_hat = buddy.get("hat")
        options = [None] + hats_owned
        try:
            current_idx = options.index(current_hat)
        except ValueError:
            current_idx = 0

        new_hat = options[(current_idx + 1) % len(options)]

        # Update in DB
        await self.store.update_buddy_by_id(buddy_id, hat=new_hat)

        # Update local state
        buddy["hat"] = new_hat
        await self._render_buddies()

    def action_rename(self):
        """Request rename for selected buddy (not yet implemented)."""
        pass  # TODO: implement inline rename

    def action_hatch(self):
        """Dismiss with signal to hatch a new buddy."""
        self.dismiss("hatch_new")

    def action_navigate_up(self):
        """Move selection up."""
        asyncio.create_task(self._do_navigate_up())

    async def _do_navigate_up(self):
        """Async logic for moving selection up."""
        if self.buddies:
            self.selected_idx = (self.selected_idx - 1) % len(self.buddies)
            await self._render_buddies()

    def action_navigate_down(self):
        """Move selection down."""
        asyncio.create_task(self._do_navigate_down())

    async def _do_navigate_down(self):
        """Async logic for moving selection down."""
        if self.buddies:
            self.selected_idx = (self.selected_idx + 1) % len(self.buddies)
            await self._render_buddies()
