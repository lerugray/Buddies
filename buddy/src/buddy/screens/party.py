"""PartyScreen — manage your buddy collection.

Shows all hatched buddies, allows switching active buddy, renaming, and hat equipping.
"""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, ScrollableContainer
from textual.widgets import Static, Button
from textual.screen import Screen

from buddy.db.store import BuddyStore
from buddy.core.buddy_brain import HAT_UNLOCK_RULES


class PartyScreen(Screen):
    """Manage buddy collection — switch, rename, equip hats."""

    CSS = """
    PartyScreen {
        align: center middle;
        background: $background;
    }

    #party-container {
        width: 1fr;
        max-width: 70;
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
    }

    .buddy-row {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: solid $accent;
    }

    #party-footer {
        text-align: center;
        height: auto;
        padding: 1 0;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Close", show=True),
        Binding("enter", "switch_buddy", "Switch", show=False),
        Binding("h", "cycle_hat", "Hat", show=True),
        Binding("n", "rename", "Rename", show=False),
        Binding("plus", "hatch", "Hatch New", show=True),
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
                yield Static(
                    "Keys: [enter] switch  [h] hat  [+] hatch new  [esc] close",
                    id="party-footer"
                )

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
            is_active = "[bold yellow]★[/] " if buddy.get("is_active") else "  "
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

            hat_str = f" 🎩 {buddy.get('hat')}" if buddy.get("hat") else ""
            text = (
                f"{is_selected}{is_active}"
                f"[{color}]{buddy.get('species', '?').upper()}[/] "
                f"{buddy.get('name')} "
                f"Lv.{buddy.get('level', 1)}"
                f"{hat_str}"
                f"{end_tag}"
            )
            row = Static(text, classes="buddy-row")
            rows.append(row)

        await buddies_list.mount(*rows)

    def action_switch_buddy(self):
        """Switch to selected buddy."""
        if 0 <= self.selected_idx < len(self.buddies):
            buddy_id = self.buddies[self.selected_idx]["id"]
            self.dismiss(buddy_id)

    async def action_cycle_hat(self):
        """Cycle to next hat for selected buddy."""
        if not (0 <= self.selected_idx < len(self.buddies)):
            return

        buddy = self.buddies[self.selected_idx]
        buddy_id = buddy["id"]
        hats_owned = buddy.get("hats_owned", "[]")

        # Parse JSON if string
        if isinstance(hats_owned, str):
            import json
            hats_owned = json.loads(hats_owned)

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

    async def action_navigate_up(self):
        """Move selection up."""
        if self.buddies:
            self.selected_idx = (self.selected_idx - 1) % len(self.buddies)
            await self._render_buddies()

    async def action_navigate_down(self):
        """Move selection down."""
        if self.buddies:
            self.selected_idx = (self.selected_idx + 1) % len(self.buddies)
            await self._render_buddies()
