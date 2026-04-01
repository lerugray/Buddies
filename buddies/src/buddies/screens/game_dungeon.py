"""DungeonScreen — cooperative dungeon crawl with your buddy.

Navigate rooms with encounter choices. Your buddy assists based on stats.
Press F/R/D/J/T/I/L for encounter choices, Space to advance.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.dungeon import DungeonGame


class DungeonScreen(Screen):
    """Cooperative dungeon crawl screen."""

    BINDINGS = [
        Binding("space", "advance", "Next Room", show=True),
        Binding("f", "choice_f", "Fight", show=False),
        Binding("r", "choice_r", "Run", show=False),
        Binding("d", "choice_d", "Disarm", show=False),
        Binding("j", "choice_j", "Jump", show=False),
        Binding("t", "choice_t", "Trigger", show=False),
        Binding("i", "choice_i", "Investigate", show=False),
        Binding("l", "choice_l", "Leave", show=False),
        Binding("n", "new_game", "New Run", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    DungeonScreen {
        layout: vertical;
        background: $background;
    }
    DungeonScreen #dungeon-header {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
    }
    DungeonScreen #dungeon-status {
        height: 2;
        padding: 0 2;
        content-align: center middle;
        text-align: center;
    }
    DungeonScreen #dungeon-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }
    DungeonScreen #dungeon-choices {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: DungeonGame | None = None
        self._result: GameResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="dungeon-header")
        yield Static("", id="dungeon-status")
        yield RichLog(id="dungeon-log", wrap=True, markup=True)
        yield Static("", id="dungeon-choices")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = DungeonGame(buddy_state=self.buddy_state)
        self._result = None
        log = self.query_one("#dungeon-log", RichLog)
        log.clear()

        name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        log.write(f"[bold]🏰 THE CODING DUNGEON 🏰[/bold]")
        log.write(f"[dim]A cooperative adventure with {emoji} {name}[/dim]")
        log.write("")
        log.write(f"{emoji} {name}: \"Let's do this. Together.\"")
        log.write("")
        log.write(f"[bold cyan]═══ FLOOR 1 ═══[/bold cyan]")

        # Enter first room
        self.game.enter_room()
        self._flush_log()
        self._update_status()
        self._update_choices()

    def _flush_log(self):
        if not self.game:
            return
        log = self.query_one("#dungeon-log", RichLog)
        for entry in self.game.action_log:
            log.write(entry)
        self.game.action_log.clear()

    def _update_status(self):
        if not self.game:
            return
        s = self.game.state
        header = self.query_one("#dungeon-header", Static)
        header.update(
            f"🏰 Floor {self.game.current_floor}/{self.game.max_floors}  |  "
            f"Room {self.game.current_room + 1}/{self.game.rooms_per_floor}"
        )

        status = self.query_one("#dungeon-status", Static)
        hp_color = "green" if s.hp > s.max_hp * 0.5 else ("yellow" if s.hp > s.max_hp * 0.25 else "red")
        hp_bar_len = 20
        hp_filled = int((s.hp / s.max_hp) * hp_bar_len)
        hp_bar = "█" * hp_filled + "░" * (hp_bar_len - hp_filled)
        status.update(
            f"[{hp_color}]HP: {s.hp}/{s.max_hp} [{hp_bar}][/{hp_color}]  "
            f"💰 {s.gold} gold  ⚔️ {s.monsters_defeated} kills  📦 {len(s.items)} items"
        )

    def _update_choices(self):
        choices_widget = self.query_one("#dungeon-choices", Static)
        if not self.game:
            return

        if self.game.is_over:
            choices_widget.update("[dim][bold]N[/bold]=New Run  [bold]Esc[/bold]=Back[/dim]")
            return

        if self.game.awaiting_choice:
            parts = []
            for key, label in self.game.choices:
                parts.append(f"[bold]{key.upper()}[/bold]={label}")
            choices_widget.update(f"[dim]{' | '.join(parts)}[/dim]")
        else:
            room = self.game.current
            if room and room.resolved:
                choices_widget.update("[dim][bold]Space[/bold]=Next Room[/dim]")
            else:
                choices_widget.update("")

    def _make_choice(self, key: str):
        if not self.game or not self.game.awaiting_choice:
            return
        self.game.make_choice(key)
        self._flush_log()
        self._update_status()
        self._update_choices()

        if self.game.is_over:
            self._show_result()

    def _show_result(self):
        if not self.game:
            return
        self._result = self.game.get_result()
        log = self.query_one("#dungeon-log", RichLog)
        s = self.game.state

        if s.floors_cleared >= self.game.max_floors:
            log.write("")
            log.write(f"[bold yellow]🏆 DUNGEON COMPLETE! 🏆[/bold yellow]")
        elif s.hp <= 0:
            log.write("")
            log.write(f"[red bold]💀 GAME OVER 💀[/red bold]")
            emoji = self.buddy_state.species.emoji
            name = self.buddy_state.name
            log.write(f"{emoji} {name}: \"We'll get 'em next time.\"")

        xp = self._result.xp_for_outcome
        log.write(f"\n[dim]+{xp} XP  |  [bold]N[/bold]=New Run  [bold]Esc[/bold]=Back[/dim]")
        self._update_choices()

    def action_advance(self):
        if not self.game or self.game.is_over or self.game.awaiting_choice:
            return
        room = self.game.current
        if room and room.resolved:
            self.game.advance()
            self._flush_log()
            self._update_status()
            self._update_choices()
            if self.game.is_over:
                self._show_result()

    def action_choice_f(self): self._make_choice("f")
    def action_choice_r(self): self._make_choice("r")
    def action_choice_d(self): self._make_choice("d")
    def action_choice_j(self): self._make_choice("j")
    def action_choice_t(self): self._make_choice("t")
    def action_choice_i(self): self._make_choice("i")
    def action_choice_l(self): self._make_choice("l")

    def action_new_game(self):
        if self._result:
            self.dismiss(self._result)
            return
        self._start_game()

    def action_back(self):
        self.dismiss(self._result)
