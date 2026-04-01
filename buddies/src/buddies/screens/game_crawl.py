"""CrawlScreen — first-person blobber dungeon crawl.

WASD movement through ASCII corridors. Turn-based party combat.
Class abilities for exploration challenges. Minimap + party roster.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen
from textual.containers import Horizontal, Vertical

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.crawl import CrawlState
from buddies.core.games.crawl_render import (
    render_view, render_minimap, render_party, render_combat_actions,
)


class CrawlScreen(Screen):
    """First-person dungeon crawl screen."""

    BINDINGS = [
        Binding("w", "move_forward", "Forward", show=False),
        Binding("s", "move_backward", "Back", show=False),
        Binding("a", "turn_left", "Turn L", show=False),
        Binding("d", "turn_right", "Turn R", show=False),
        Binding("space", "interact", "Interact", show=False),
        Binding("1", "combat_1", "Attack", show=False),
        Binding("2", "combat_2", "Skill", show=False),
        Binding("3", "combat_3", "Defend", show=False),
        Binding("4", "combat_4", "Item", show=False),
        Binding("n", "new_game", "New Run", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    CrawlScreen {
        layout: vertical;
        background: $background;
    }
    CrawlScreen #crawl-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }
    CrawlScreen #crawl-main {
        height: 1fr;
        min-height: 12;
    }
    CrawlScreen #crawl-view {
        width: 1fr;
        min-width: 24;
        padding: 0 1;
        content-align: center middle;
        text-align: center;
    }
    CrawlScreen #crawl-sidebar {
        width: 34;
        padding: 0 1;
    }
    CrawlScreen #crawl-minimap {
        height: auto;
        min-height: 8;
        padding: 0 1;
        border: round $primary;
    }
    CrawlScreen #crawl-party {
        height: auto;
        min-height: 5;
        padding: 0 1;
        border: round $accent;
    }
    CrawlScreen #crawl-log {
        height: 8;
        border: round $primary;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }
    CrawlScreen #crawl-actions {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, buddy_state: BuddyState, party_states: list[BuddyState] | None = None):
        super().__init__()
        self.buddy_state = buddy_state
        self.party_states = party_states or []
        self.game: CrawlState | None = None
        self._result: GameResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="crawl-header")
        with Horizontal(id="crawl-main"):
            yield Static("", id="crawl-view")
            with Vertical(id="crawl-sidebar"):
                yield Static("", id="crawl-minimap")
                yield Static("", id="crawl-party")
        yield RichLog(id="crawl-log", wrap=True, markup=True)
        yield Static("", id="crawl-actions")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        # Build party: active buddy + party members
        all_buddies = [self.buddy_state] + self.party_states[:3]
        self.game = CrawlState.new_game(all_buddies)
        self._result = None

        log = self.query_one("#crawl-log", RichLog)
        log.clear()
        log.write("[bold]🏰 THE CODING DUNGEON 🏰[/bold]")
        log.write(f"[dim]Party of {len(self.game.party)} enters floor 1...[/dim]")

        # Show party classes
        for m in self.game.party:
            from buddies.core.games.crawl import CLASS_NAMES
            log.write(f"  {m.emoji} {m.name} — {CLASS_NAMES[m.buddy_class]}")
        log.write("")

        self._render_all()

    def _render_all(self):
        """Update all UI panels."""
        if not self.game:
            return

        # Header
        header = self.query_one("#crawl-header", Static)
        alive = sum(1 for m in self.game.party if m.is_alive)
        header.update(
            f"⚔ Floor {self.game.floor}/{self.game.max_floors}  "
            f"│  Party: {alive}/{len(self.game.party)}  "
            f"│  💰 {self.game.gold}  "
            f"│  ⚔ {self.game.monsters_defeated} kills  "
            f"│  🧪 {self.game.potions} potions"
        )

        # First-person view
        view = self.query_one("#crawl-view", Static)
        view.update(render_view(self.game))

        # Minimap
        minimap = self.query_one("#crawl-minimap", Static)
        minimap.update(render_minimap(self.game))

        # Party
        party = self.query_one("#crawl-party", Static)
        party.update(render_party(self.game))

        # Action bar
        self._update_actions()

        # Flush log
        self._flush_log()

    def _flush_log(self):
        if not self.game:
            return
        log = self.query_one("#crawl-log", RichLog)
        for entry in self.game.action_log:
            log.write(entry)
        self.game.action_log.clear()

    def _update_actions(self):
        actions = self.query_one("#crawl-actions", Static)
        if not self.game:
            return

        if self.game.is_over:
            actions.update("[dim][bold]N[/bold]=New Run  [bold]Esc[/bold]=Leave[/dim]")
        elif self.game.in_combat:
            combat_prompt = render_combat_actions(self.game)
            actions.update(combat_prompt)
        else:
            actions.update(
                "[dim][bold]W[/bold]/[bold]S[/bold]=Move  "
                "[bold]A[/bold]/[bold]D[/bold]=Turn  "
                "[bold]Space[/bold]=Interact  "
                "[bold]Esc[/bold]=Leave[/dim]"
            )

    # -----------------------------------------------------------------------
    # Movement actions
    # -----------------------------------------------------------------------

    def action_move_forward(self):
        if not self.game or self.game.in_combat or self.game.is_over:
            return
        self.game.move_forward()
        self._render_all()
        if self.game.is_over:
            self._show_result()

    def action_move_backward(self):
        if not self.game or self.game.in_combat or self.game.is_over:
            return
        self.game.move_backward()
        self._render_all()

    def action_turn_left(self):
        if not self.game or self.game.in_combat or self.game.is_over:
            return
        self.game.turn_left()
        self._render_all()

    def action_turn_right(self):
        if not self.game or self.game.in_combat or self.game.is_over:
            return
        self.game.turn_right()
        self._render_all()

    def action_interact(self):
        """Interact with the current cell (descend stairs, etc.)."""
        if not self.game or self.game.in_combat or self.game.is_over:
            return
        self.game.descend()
        self._render_all()
        if self.game.is_over:
            self._show_result()

    # -----------------------------------------------------------------------
    # Combat actions
    # -----------------------------------------------------------------------

    def action_combat_1(self):
        if not self.game or not self.game.in_combat:
            return
        self.game.combat_attack()
        self._render_all()
        if self.game.is_over:
            self._show_result()

    def action_combat_2(self):
        if not self.game or not self.game.in_combat:
            return
        self.game.combat_skill()
        self._render_all()
        if self.game.is_over:
            self._show_result()

    def action_combat_3(self):
        if not self.game or not self.game.in_combat:
            return
        self.game.combat_defend()
        self._render_all()
        if self.game.is_over:
            self._show_result()

    def action_combat_4(self):
        if not self.game or not self.game.in_combat:
            return
        self.game.combat_item()
        self._render_all()

    # -----------------------------------------------------------------------
    # Game flow
    # -----------------------------------------------------------------------

    def _show_result(self):
        if not self.game:
            return
        self._result = self.game.get_result()
        log = self.query_one("#crawl-log", RichLog)

        if self.game.game_won:
            log.write("\n[bold yellow]🏆 DUNGEON COMPLETE! 🏆[/bold yellow]")
        else:
            log.write("\n[red bold]💀 GAME OVER 💀[/red bold]")

        log.write(f"Floors: {self.game.floors_cleared} | Kills: {self.game.monsters_defeated} | Gold: {self.game.gold}")
        xp = self._result.xp_for_outcome
        log.write(f"\n[dim]+{xp} XP  |  [bold]N[/bold]=New Run  [bold]Esc[/bold]=Leave[/dim]")
        self._update_actions()

    def action_new_game(self):
        if self._result:
            self.dismiss(self._result)
            return
        self._start_game()

    def action_back(self):
        if self.game and (self.game.floors_cleared > 0 or self.game.monsters_defeated > 0):
            self._result = self.game.get_result()
        self.dismiss(self._result)
