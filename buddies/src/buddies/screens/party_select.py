"""PartySelectScreen — pick your dungeon party before entering.

Shows all buddies with their class, stats, and HP. Optional user
character at the top. Select 1-4 members, then launch the crawl.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games.crawl import PartyMember, BuddyClass, CLASS_NAMES


class PartySelectScreen(Screen):
    """Select party members for the dungeon crawl."""

    BINDINGS = [
        Binding("up", "cursor_up", "↑", show=False),
        Binding("down", "cursor_down", "↓", show=False),
        Binding("space", "toggle_select", "Toggle", show=True),
        Binding("enter", "start_crawl", "Enter Dungeon", show=True),
        Binding("u", "toggle_user", "Add/Remove You", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    PartySelectScreen {
        layout: vertical;
        background: $background;
    }
    PartySelectScreen #ps-header {
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    PartySelectScreen #ps-list {
        height: 1fr;
        padding: 1 2;
        background: $surface;
        border: round $primary;
        margin: 1 2;
    }
    PartySelectScreen #ps-preview {
        height: 6;
        padding: 0 2;
        content-align: center middle;
        text-align: center;
    }
    PartySelectScreen #ps-help {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        all_buddies: list[BuddyState],
        user_state: BuddyState | None = None,
    ):
        super().__init__()
        self.all_buddies = all_buddies
        self.user_state = user_state
        self.cursor = 0
        self.selected: set[int] = set()  # Indices into display list
        self.include_user = False
        self._display_list: list[tuple[str, BuddyState]] = []  # ("buddy"|"user", state)

    def compose(self) -> ComposeResult:
        yield Static("⚔️ ASSEMBLE YOUR PARTY ⚔️", id="ps-header")
        yield Static("", id="ps-list")
        yield Static("", id="ps-preview")
        yield Static(
            "[dim]↑/↓=Navigate  Space=Toggle  U=Add/Remove You  Enter=Start  Esc=Back[/dim]\n"
            "[dim]Select 1-4 party members for the dungeon[/dim]",
            id="ps-help",
        )
        yield Footer()

    def on_mount(self):
        self._build_display_list()
        # Auto-select first buddy
        if self._display_list:
            self.selected.add(0)
        self._render()

    def _build_display_list(self):
        """Build the display list with optional user character."""
        self._display_list = []
        if self.include_user and self.user_state:
            self._display_list.append(("user", self.user_state))
        for b in self.all_buddies:
            self._display_list.append(("buddy", b))

    def _render(self):
        """Render the party selection list."""
        list_widget = self.query_one("#ps-list", Static)
        lines = []

        for i, (kind, state) in enumerate(self._display_list):
            # Determine class
            member = PartyMember.from_buddy(state)
            cls_name = CLASS_NAMES[member.buddy_class]
            cls_tag = member.buddy_class.value

            # Selection indicator
            sel = "[bold green]✓[/bold green]" if i in self.selected else " "
            cursor = "►" if i == self.cursor else " "

            # Stats summary
            stats = state.stats
            top_stat = max(stats, key=stats.get)
            stat_val = stats[top_stat]

            # User character has special label
            if kind == "user":
                name_str = f"[bold yellow]👤 {state.name}[/bold yellow]"
                tag = "[yellow](YOU)[/yellow]"
            else:
                rarity_colors = {
                    "common": "white", "uncommon": "green",
                    "rare": "cyan", "epic": "magenta", "legendary": "yellow",
                }
                color = rarity_colors.get(state.species.rarity.value, "white")
                name_str = f"[{color}]{state.species.emoji} {state.name}[/{color}]"
                tag = f"[dim]Lv.{state.level}[/dim]"

            line = (
                f" {cursor} {sel}  {name_str:30} {tag:12} "
                f"[bold]{cls_tag}[/bold] ({cls_name:10}) "
                f"HP:{member.max_hp:3}  ATK:{member.attack:2}  DEF:{member.defense:2}  "
                f"[dim]{top_stat.upper()}:{stat_val}[/dim]"
            )
            lines.append(line)

        if not lines:
            lines.append("[dim]No buddies available. Hatch some first![/dim]")

        list_widget.update("\n".join(lines))

        # Preview panel
        preview = self.query_one("#ps-preview", Static)
        count = len(self.selected)
        if count == 0:
            preview.update("[yellow]Select at least 1 party member[/yellow]")
        else:
            members = []
            for i in self.selected:
                if i < len(self._display_list):
                    _, state = self._display_list[i]
                    m = PartyMember.from_buddy(state)
                    members.append(f"{state.species.emoji} {state.name} ({CLASS_NAMES[m.buddy_class]})")
            party_str = "  ".join(members)
            classes = set()
            for i in self.selected:
                if i < len(self._display_list):
                    _, state = self._display_list[i]
                    m = PartyMember.from_buddy(state)
                    classes.add(m.buddy_class)

            # Show party composition analysis
            missing = set(BuddyClass) - classes
            missing_str = ", ".join(CLASS_NAMES[c] for c in missing) if missing else "None!"
            preview.update(
                f"[bold]Party ({count}/4):[/bold] {party_str}\n"
                f"[dim]Missing roles: {missing_str}[/dim]"
            )

    def action_cursor_up(self):
        if self._display_list:
            self.cursor = (self.cursor - 1) % len(self._display_list)
            self._render()

    def action_cursor_down(self):
        if self._display_list:
            self.cursor = (self.cursor + 1) % len(self._display_list)
            self._render()

    def action_toggle_select(self):
        if not self._display_list:
            return
        if self.cursor in self.selected:
            self.selected.discard(self.cursor)
        elif len(self.selected) < 4:
            self.selected.add(self.cursor)
        self._render()

    def action_toggle_user(self):
        """Toggle the user character in/out of the list."""
        if not self.user_state:
            return
        self.include_user = not self.include_user
        # Rebuild list and reset selection
        old_selected_states = set()
        for i in self.selected:
            if i < len(self._display_list):
                old_selected_states.add(id(self._display_list[i][1]))

        self._build_display_list()

        # Restore selection by matching state objects
        self.selected = set()
        for i, (_, state) in enumerate(self._display_list):
            if id(state) in old_selected_states:
                self.selected.add(i)

        # Auto-select user if just added
        if self.include_user and self.user_state:
            for i, (kind, _) in enumerate(self._display_list):
                if kind == "user":
                    self.selected.add(i)
                    break

        self.cursor = 0
        self._render()

    def action_start_crawl(self):
        """Launch the dungeon with selected party."""
        if not self.selected:
            return

        party: list[BuddyState] = []
        for i in sorted(self.selected):
            if i < len(self._display_list):
                _, state = self._display_list[i]
                party.append(state)

        if not party:
            return

        self.dismiss(party)

    def action_back(self):
        self.dismiss(None)
