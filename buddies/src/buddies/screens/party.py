"""PartyScreen — manage your buddy collection.

Shows all hatched buddies, allows switching active buddy, renaming, and hat equipping.
"""

from __future__ import annotations

import asyncio
import json
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, ScrollableContainer
from textual.widgets import Static, Input, Footer
from textual.screen import Screen

from buddies.db.store import BuddyStore
from buddies.core.buddy_brain import (
    HAT_UNLOCK_RULES, SPECIES_CATALOG, get_evolution_stage, Rarity,
)
from buddies.widgets.styling import RARITY_COLORS, RARITY_STARS


class PartyScreen(Screen):
    """Manage buddy collection — switch, rename, equip hats."""

    CSS = """
    PartyScreen {
        align: center middle;
        background: $background;
    }

    #party-scroll {
        width: 96%;
        max-width: 100;
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #party-container {
        width: 1fr;
        height: auto;
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
        margin: 0;
        width: 1fr;
        overflow: auto;
    }

    .buddy-row {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0;
        border: none;
    }

    #rename-input {
        margin: 1 0;
    }

    #party-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("enter", "switch_buddy", "Switch", show=True),
        Binding("h", "cycle_hat", "Hat", show=True),
        Binding("n", "rename", "Rename", show=True),
        Binding("d", "discuss", "Discuss", show=True),
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
        self._renaming = False

    def compose(self) -> ComposeResult:
        with Center():
            with ScrollableContainer(id="party-scroll"):
                with Vertical(id="party-container"):
                    yield Static("🐾 BUDDY PARTY 🐾", id="party-title")
                    yield Vertical(id="buddies-list")
                    yield Static(
                        "[dim]↑↓ navigate  enter=switch  h=hat  n=rename  d=discuss  del=release  +=hatch[/]",
                        id="party-help",
                    )
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

        # Remove existing children
        await buddies_list.query("Static").remove()
        # Also remove any lingering Input widgets from rename mode
        await buddies_list.query("Input").remove()

        rows = []
        for idx, buddy in enumerate(self.buddies):
            is_active = "★ " if buddy.get("is_active") else "  "
            is_selected = "[reverse]" if idx == self.selected_idx else ""
            end_tag = "[/]" if idx == self.selected_idx else ""

            species_name = buddy.get("species", "unknown")
            species_info = next(
                (s for s in SPECIES_CATALOG if s.name == species_name), None
            )
            rarity = species_info.rarity.value if species_info else "common"
            color = RARITY_COLORS.get(rarity, "white")
            stars = RARITY_STARS.get(rarity, "★")

            # Evolution stage
            level = buddy.get("level", 1)
            stage = get_evolution_stage(level)
            stage_str = stage["name"][:4]  # Hatc/Juv/Adul/Elde

            # Buddy name (truncated)
            buddy_name = buddy.get("name", "Buddy")[:12]

            # Hat info
            hat = buddy.get("hat")
            hat_str = f" [{hat}]" if hat else ""

            # Hats owned count
            hats_owned = buddy.get("hats_owned", "[]")
            if isinstance(hats_owned, str):
                try:
                    hats_owned = json.loads(hats_owned)
                except json.JSONDecodeError:
                    hats_owned = []
            hat_count = len(hats_owned) if isinstance(hats_owned, list) else 0

            # Format: ★ species  name  L5 Juv  🎩x2
            text = (
                f"{is_selected}{is_active}"
                f"[{color}]{species_name[:8]:<8}[/] "
                f"{buddy_name:<12} "
                f"L{level:<3}"
                f"[dim]{stage_str}[/]"
                f"{hat_str}"
                f"{end_tag}"
            )
            row = Static(text, classes="buddy-row")
            rows.append(row)

        await buddies_list.mount(*rows)

    def action_close(self):
        """Close the party screen without switching."""
        if self._renaming:
            self._cancel_rename()
            return
        self.dismiss(None)

    def action_switch_buddy(self):
        """Switch to selected buddy."""
        if self._renaming:
            return
        if 0 <= self.selected_idx < len(self.buddies):
            buddy_id = self.buddies[self.selected_idx]["id"]
            self.dismiss(buddy_id)

    def action_release_buddy(self):
        """Delete the selected buddy from the collection."""
        if self._renaming:
            return
        asyncio.create_task(self._do_release_buddy())

    async def _do_release_buddy(self):
        """Async logic for releasing/deleting a buddy."""
        if not (0 <= self.selected_idx < len(self.buddies)):
            return

        buddy = self.buddies[self.selected_idx]
        buddy_id = buddy["id"]
        was_active = bool(buddy.get("is_active"))

        try:
            await self.store.delete_buddy(buddy_id)
        except Exception:
            return

        self.buddies = await self.store.get_all_buddies()

        if not self.buddies:
            self.dismiss("hatch_new")
            return

        if was_active:
            new_active_id = self.buddies[0]["id"]
            await self.store.set_active_buddy(new_active_id)
            self.buddies = await self.store.get_all_buddies()

        if self.selected_idx >= len(self.buddies):
            self.selected_idx = len(self.buddies) - 1

        await self._render_buddies()

    def action_cycle_hat(self):
        """Cycle to next hat for selected buddy."""
        if self._renaming:
            return
        asyncio.create_task(self._do_cycle_hat())

    async def _do_cycle_hat(self):
        """Async logic for hat cycling."""
        if not (0 <= self.selected_idx < len(self.buddies)):
            return

        buddy = self.buddies[self.selected_idx]
        buddy_id = buddy["id"]
        hats_owned = buddy.get("hats_owned", "[]")

        if isinstance(hats_owned, str):
            try:
                hats_owned = json.loads(hats_owned)
            except json.JSONDecodeError:
                hats_owned = []

        if not hats_owned:
            return

        current_hat = buddy.get("hat")
        options = [None] + hats_owned
        try:
            current_idx = options.index(current_hat)
        except ValueError:
            current_idx = 0

        new_hat = options[(current_idx + 1) % len(options)]

        await self.store.update_buddy_by_id(buddy_id, hat=new_hat)
        buddy["hat"] = new_hat
        await self._render_buddies()

    def action_rename(self):
        """Show inline rename input for selected buddy."""
        if self._renaming:
            return
        if not (0 <= self.selected_idx < len(self.buddies)):
            return
        self._renaming = True
        buddy = self.buddies[self.selected_idx]
        current_name = buddy.get("name", "Buddy")

        buddies_list = self.query_one("#buddies-list", Vertical)
        rename_input = Input(
            placeholder="New name...",
            id="rename-input",
            value=current_name,
        )
        asyncio.create_task(self._mount_rename(buddies_list, rename_input))

    async def _mount_rename(self, container: Vertical, rename_input: Input):
        await container.mount(rename_input)
        rename_input.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle rename input submission."""
        if event.input.id != "rename-input":
            return

        new_name = event.value.strip()
        if new_name and 0 <= self.selected_idx < len(self.buddies):
            buddy = self.buddies[self.selected_idx]
            buddy_id = buddy["id"]
            await self.store.update_buddy_by_id(buddy_id, name=new_name)
            buddy["name"] = new_name

        self._renaming = False
        await event.input.remove()
        await self._render_buddies()

    def _cancel_rename(self):
        """Cancel rename mode."""
        self._renaming = False
        try:
            rename_input = self.query_one("#rename-input", Input)
            asyncio.create_task(rename_input.remove())
        except Exception:
            pass

    def action_discuss(self):
        """Dismiss with signal to open discussion screen."""
        if self._renaming:
            return
        self.dismiss("discuss")

    def action_hatch(self):
        """Dismiss with signal to hatch a new buddy."""
        if self._renaming:
            return
        self.dismiss("hatch_new")

    def action_navigate_up(self):
        """Move selection up."""
        if self._renaming:
            return
        asyncio.create_task(self._do_navigate_up())

    async def _do_navigate_up(self):
        if self.buddies:
            self.selected_idx = (self.selected_idx - 1) % len(self.buddies)
            await self._render_buddies()

    def action_navigate_down(self):
        """Move selection down."""
        if self._renaming:
            return
        asyncio.create_task(self._do_navigate_down())

    async def _do_navigate_down(self):
        if self.buddies:
            self.selected_idx = (self.selected_idx + 1) % len(self.buddies)
            await self._render_buddies()
