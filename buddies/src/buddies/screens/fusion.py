"""FusionScreen — sacrifice two buddies to create something new.

Two-phase selection: pick parent A, then parent B, see preview, confirm.
Inspired by SMT demon fusion and Siralim 3 breeding.
"""

from __future__ import annotations

import asyncio
import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Footer
from textual.screen import Screen

from buddies.core.buddy_brain import SPECIES_CATALOG, get_evolution_stage
from buddies.core.fusion import (
    check_fusion, format_fusion_preview, get_discovered_recipes,
    CHIMERA_CROWN_HAT, FUSED_TAG, FUSION_SPECIES_BY_NAME, FUSION_SPECIES,
    FUSION_RECIPES,
)
from buddies.db.store import BuddyStore
from buddies.widgets.styling import RARITY_COLORS


class FusionScreen(Screen):
    """Buddy Fusion — combine two buddies into one."""

    CSS = """
    FusionScreen {
        background: $background;
    }
    #fusion-scroll {
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }
    #fusion-container {
        width: 1fr;
        height: auto;
    }
    #fusion-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #fusion-list {
        height: auto;
        border: solid $primary;
        padding: 1;
        width: 1fr;
    }
    #fusion-preview {
        height: auto;
        border: solid $accent;
        padding: 1;
        margin-top: 1;
        width: 1fr;
    }
    #fusion-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    .buddy-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("enter", "select", "Select", show=True),
        Binding("y", "confirm_fusion", "Confirm", show=False),
        Binding("r", "show_recipes", "Recipes", show=True),
        Binding("c", "show_codex", "Codex", show=True),
        Binding("up", "nav_up", show=False),
        Binding("down", "nav_down", show=False),
    ]

    def __init__(self, store: BuddyStore):
        super().__init__()
        self.store = store
        self.buddies: list[dict] = []
        self.selected_idx = 0
        self.parent_a: dict | None = None
        self.parent_b: dict | None = None
        self._phase = "select_a"  # select_a, select_b, confirm
        self._preview_result = None

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="fusion-scroll"):
            with Vertical(id="fusion-container"):
                yield Static("", id="fusion-title")
                yield Vertical(id="fusion-list")
                yield Static("", id="fusion-preview")
                yield Static("", id="fusion-help")
        yield Footer()

    async def on_mount(self):
        self.buddies = await self.store.get_all_buddies()
        # Need at least 2 buddies to fuse
        if len(self.buddies) < 2:
            title = self.query_one("#fusion-title", Static)
            title.update("[bold]Buddy Fusion[/bold]\n\n[dim]You need at least 2 buddies to fuse.[/dim]")
            return
        await self._render_phase()

    async def _render_phase(self):
        title = self.query_one("#fusion-title", Static)
        help_w = self.query_one("#fusion-help", Static)
        preview = self.query_one("#fusion-preview", Static)

        if self._phase == "select_a":
            title.update("[bold]BUDDY FUSION — Select First Parent[/bold]")
            help_w.update("[dim]↑↓=navigate  enter=select  r=recipes  esc=close[/dim]")
            preview.update("")
            await self._render_buddy_list()

        elif self._phase == "select_b":
            a_name = self.parent_a.get("name", "?")
            a_species = self.parent_a.get("species", "?")
            title.update(f"[bold]BUDDY FUSION — Select Second Parent[/bold]\n[dim]First: {a_name} ({a_species})[/dim]")
            help_w.update("[dim]↑↓=navigate  enter=select  esc=go back[/dim]")
            preview.update("")
            await self._render_buddy_list(exclude_id=self.parent_a["id"])

        elif self._phase == "confirm":
            title.update("[bold]BUDDY FUSION — Confirm?[/bold]")
            help_w.update("[bold yellow]y[/bold yellow]=FUSE (permanent!)  [bold]esc[/bold]=cancel")
            await self._render_preview()

    async def _render_buddy_list(self, exclude_id: int | None = None):
        buddy_list = self.query_one("#fusion-list", Vertical)
        await buddy_list.query("Static").remove()

        visible = [b for b in self.buddies if b["id"] != exclude_id] if exclude_id else list(self.buddies)

        if not visible:
            await buddy_list.mount(Static("[dim]No buddies available.[/dim]"))
            return

        # Clamp selection
        if self.selected_idx >= len(visible):
            self.selected_idx = 0

        rows = []
        for idx, buddy in enumerate(visible):
            is_active = "[yellow]★[/yellow] " if buddy.get("is_active") else "  "
            sel = "[reverse]" if idx == self.selected_idx else ""
            end = "[/]" if idx == self.selected_idx else ""

            species_name = buddy.get("species", "unknown")
            sp = next((s for s in SPECIES_CATALOG if s.name == species_name), None)
            rarity = sp.rarity.value if sp else "common"
            color = RARITY_COLORS.get(rarity, "white")

            level = buddy.get("level", 1)
            stage = get_evolution_stage(level)["name"][:4]
            name = buddy.get("name", "Buddy")[:20]

            text = (
                f"{sel}{is_active}"
                f"[{color}]{species_name:<14}[/] "
                f"{name:<18} "
                f"L{level:<3} {stage}"
                f"{end}"
            )
            rows.append(Static(text, classes="buddy-row"))

        await buddy_list.mount(*rows)

        # Store visible list for selection mapping
        self._visible_buddies = visible

    async def _render_preview(self):
        if not self.parent_a or not self.parent_b or not self._preview_result:
            return

        preview = self.query_one("#fusion-preview", Static)
        buddy_list = self.query_one("#fusion-list", Vertical)
        await buddy_list.query("Static").remove()

        # Show parents
        a = self.parent_a
        b = self.parent_b
        lines = [
            f"  Parent A: {a.get('name')} ({a.get('species')})",
            f"  Parent B: {b.get('name')} ({b.get('species')})",
        ]
        await buddy_list.mount(Static("\n".join(lines)))

        # Show fusion preview
        preview_lines = format_fusion_preview(self._preview_result)
        preview.update("\n".join(preview_lines))

    def action_select(self):
        asyncio.create_task(self._do_select())

    async def _do_select(self):
        if self._phase == "select_a":
            if not hasattr(self, "_visible_buddies") or not self._visible_buddies:
                return
            if 0 <= self.selected_idx < len(self._visible_buddies):
                self.parent_a = self._visible_buddies[self.selected_idx]
                self._phase = "select_b"
                self.selected_idx = 0
                await self._render_phase()

        elif self._phase == "select_b":
            if not hasattr(self, "_visible_buddies") or not self._visible_buddies:
                return
            if 0 <= self.selected_idx < len(self._visible_buddies):
                self.parent_b = self._visible_buddies[self.selected_idx]

                # Build BuddyState objects for the fusion check
                from buddies.core.buddy_brain import BuddyState
                state_a = BuddyState.from_db(self.parent_a)
                state_b = BuddyState.from_db(self.parent_b)
                self._preview_result = check_fusion(state_a, state_b)

                self._phase = "confirm"
                await self._render_phase()

    def action_confirm_fusion(self):
        if self._phase != "confirm":
            return
        asyncio.create_task(self._do_fusion())

    async def _do_fusion(self):
        if not self._preview_result or not self._preview_result.success:
            return
        if not self.parent_a or not self.parent_b:
            return

        result = self._preview_result
        a_id = self.parent_a["id"]
        b_id = self.parent_b["id"]
        a_was_active = self.parent_a.get("is_active")

        # Create the fused buddy in DB
        species = result.species
        stats = result.inherited_stats
        name = result.name_suggestion[:30]

        # Build hats_owned list with chimera crown
        hats = [CHIMERA_CROWN_HAT]

        # Add soul description with fused tag
        soul = f"{FUSED_TAG} {species.description}"

        # Create buddy (basic), then update with fusion-specific fields
        new_buddy = await self.store.create_buddy(
            species=species.name,
            name=name,
            shiny=False,
            soul_description=soul,
        )
        fused_id = new_buddy["id"]

        # Apply fusion stats, hat, and hats_owned via update
        import json as _json
        await self.store.update_buddy_by_id(
            fused_id,
            hat=CHIMERA_CROWN_HAT,
            hats_owned=_json.dumps(hats),
            **{f"stat_{k}": v for k, v in stats.items()},
        )

        # Log the fusion event
        recipe_name = result.recipe_used.result if result.recipe_used else None
        await self.store.log_fusion(
            parent_a_species=a.get("species", ""),
            parent_b_species=b.get("species", ""),
            result_species=species.name,
            result_buddy_id=fused_id,
            recipe_name=recipe_name,
        )

        # Delete both parents
        await self.store.delete_buddy(a_id)
        await self.store.delete_buddy(b_id)

        # If either parent was active, make the fused buddy active
        if a_was_active or self.parent_b.get("is_active"):
            await self.store.set_active_buddy(fused_id)

        # Dismiss with signal to refresh
        self.dismiss("fused")

    def action_back(self):
        if self._phase == "select_b":
            self._phase = "select_a"
            self.parent_a = None
            self.selected_idx = 0
            asyncio.create_task(self._render_phase())
        elif self._phase == "confirm":
            self._phase = "select_b"
            self.parent_b = None
            self._preview_result = None
            self.selected_idx = 0
            asyncio.create_task(self._render_phase())
        else:
            self.dismiss(None)

    def action_show_recipes(self):
        asyncio.create_task(self._do_show_recipes())

    async def _do_show_recipes(self):
        owned_species = {b.get("species", "") for b in self.buddies}
        recipes = get_discovered_recipes(owned_species)

        preview = self.query_one("#fusion-preview", Static)
        if not recipes:
            preview.update("[dim]No fusion recipes available with your current collection.\nCollect more species to discover recipes![/dim]")
            return

        lines = ["[bold]Available Fusion Recipes:[/bold]", ""]
        for r in recipes:
            result_sp = FUSION_SPECIES_BY_NAME.get(r.result)
            emoji = result_sp.emoji if result_sp else "?"
            rarity = result_sp.rarity.value if result_sp else "?"
            lines.append(f"  {r.species_a} + {r.species_b} → {emoji} [bold]{r.result}[/bold] ({rarity})")
        lines.append(f"\n[dim]{len(recipes)} recipe(s) available[/dim]")
        preview.update("\n".join(lines))

    def action_show_codex(self):
        asyncio.create_task(self._do_show_codex())

    async def _do_show_codex(self):
        """Show the Fusion Codex — discovered vs undiscovered fusion species."""
        # Get all species the player owns or has created via fusion
        owned_species = {b.get("species", "") for b in self.buddies}

        # Also check soul descriptions for fused buddies (they might own fusion species)
        discovered_fusion = set()
        for b in self.buddies:
            sp = b.get("species", "")
            if sp in FUSION_SPECIES_BY_NAME:
                discovered_fusion.add(sp)
            # Check fusion log via soul description tag
            soul = b.get("soul_description", "")
            if FUSED_TAG in soul:
                discovered_fusion.add(sp)

        preview = self.query_one("#fusion-preview", Static)
        total = len(FUSION_SPECIES)
        found = len(discovered_fusion)

        lines = [
            f"[bold]═══ FUSION CODEX ({found}/{total}) ═══[/bold]",
            "",
        ]

        for species in FUSION_SPECIES:
            if species.name in discovered_fusion:
                # Discovered — show full details
                color = RARITY_COLORS.get(species.rarity.value, "white")
                lines.append(
                    f"  {species.emoji} [{color}][bold]{species.name.replace('_', ' ').title()}[/bold][/{color}] "
                    f"({species.rarity.value.upper()})"
                )
                lines.append(f"    [dim italic]{species.description}[/dim italic]")
                # Show which recipe produces it
                for r in FUSION_RECIPES:
                    if r.result == species.name:
                        lines.append(f"    [dim]Recipe: {r.species_a} + {r.species_b}[/dim]")
                        break
            else:
                # Undiscovered — show silhouette with hint
                lines.append(
                    f"  ❓ [dim]???[/dim] ({species.rarity.value.upper()})"
                )
                # Give a vague hint from the recipe
                for r in FUSION_RECIPES:
                    if r.result == species.name:
                        # Check if player has either parent
                        has_a = r.species_a in owned_species
                        has_b = r.species_b in owned_species
                        if has_a and has_b:
                            lines.append(f"    [yellow]Hint: You have both ingredients![/yellow]")
                        elif has_a:
                            lines.append(f"    [dim]Hint: Requires {r.species_a} + ???[/dim]")
                        elif has_b:
                            lines.append(f"    [dim]Hint: Requires ??? + {r.species_b}[/dim]")
                        else:
                            lines.append(f"    [dim]Hint: Keep collecting...[/dim]")
                        break
            lines.append("")

        if found == total:
            lines.append("[bold yellow]★ FUSION MASTER — All fusion species discovered! ★[/bold yellow]")
        else:
            lines.append(f"[dim]{total - found} species remaining to discover.[/dim]")

        preview.update("\n".join(lines))

    def action_nav_up(self):
        asyncio.create_task(self._do_nav(-1))

    def action_nav_down(self):
        asyncio.create_task(self._do_nav(1))

    async def _do_nav(self, delta: int):
        if self._phase in ("select_a", "select_b"):
            visible = getattr(self, "_visible_buddies", [])
            if visible:
                self.selected_idx = (self.selected_idx + delta) % len(visible)
                exclude = self.parent_a["id"] if self._phase == "select_b" and self.parent_a else None
                await self._render_buddy_list(exclude_id=exclude)
