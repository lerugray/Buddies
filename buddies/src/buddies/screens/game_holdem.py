"""HoldemScreen — Texas Hold'em poker table.

You + party buddies around an ASCII felt table.
Buddy "profile pics" at each seat, community cards in the center.
Press F to fold, C to call/check, R to raise, A for all-in.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.holdem import HoldemGame
from buddies.core.games.prose_games import pick_game_line, GAME_START


# ---------------------------------------------------------------------------
# Hold'em-specific prose
# ---------------------------------------------------------------------------

HOLDEM_FOLD = {
    "clinical": [
        "Fold registered. A tactically sound retreat.",
        "Withdrawing from this hand. Optimal.",
    ],
    "sarcastic": [
        "Smart move. Those cards were garbage anyway.",
        "Folding? Coward. ...I mean, wise.",
    ],
    "absurdist": [
        "Your cards fly into the ABYSS!",
        "The fold echoes through eternity!",
    ],
    "philosophical": [
        "To fold is to preserve one's resources for the right moment.",
        "Patience. The cards will come.",
    ],
    "calm": [
        "Good fold. Live to play another hand.",
        "Sometimes the best move is to wait.",
    ],
}

HOLDEM_BIG_POT = [
    "The pot is getting HUGE!",
    "Big money on the table!",
    "Things are heating up!",
    "Someone's walking away rich...",
]

HOLDEM_BLUFF_DETECTED = [
    "Was that a bluff? 👀",
    "Interesting raise there...",
    "Bold move. Very bold.",
    "Either genius or madness. Hard to tell.",
]

HOLDEM_ALL_IN = [
    "ALL IN! This is it!",
    "Everything on the table! No going back!",
    "The absolute madlad went all in!",
    "HIGH STAKES! Maximum tension!",
]


class HoldemScreen(Screen):
    """Texas Hold'em poker table screen."""

    BINDINGS = [
        Binding("f", "fold", "Fold", show=True),
        Binding("c", "call", "Call/Check", show=True),
        Binding("r", "raise_bet", "Raise", show=True),
        Binding("i", "all_in", "All In", show=True),
        Binding("n", "new_hand", "Deal", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    HoldemScreen {
        layout: vertical;
        background: $background;
    }
    HoldemScreen #holdem-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
    }
    HoldemScreen #holdem-table {
        height: auto;
        min-height: 10;
        padding: 0 1;
        content-align: center middle;
        text-align: center;
    }
    HoldemScreen #holdem-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }
    HoldemScreen #holdem-actions {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, buddy_state: BuddyState, party_states: list[BuddyState] | None = None):
        super().__init__()
        self.buddy_state = buddy_state
        self.party_states = party_states or []
        self.game: HoldemGame | None = None
        self._result: GameResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("🃏 TEXAS HOLD'EM 🃏", id="holdem-header")
        yield Static("", id="holdem-table")
        yield RichLog(id="holdem-log", wrap=True, markup=True)
        yield Static("", id="holdem-actions")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = HoldemGame(
            player_state=self.buddy_state,
            party_states=self.party_states,
        )
        self._result = None
        log = self.query_one("#holdem-log", RichLog)
        log.clear()

        # Show who's at the table
        log.write("[bold]Players at the table:[/bold]")
        for seat in self.game.seats:
            log.write(f"  {seat.emoji} {seat.name} — {seat.chips} chips")
        log.write("")
        log.write(pick_game_line(GAME_START, self.buddy_state))
        log.write("")

        self._deal_hand()

    def _deal_hand(self):
        if not self.game:
            return

        log = self.query_one("#holdem-log", RichLog)

        if self.game.is_over:
            log.write("[bold red]Game over! You're out of chips.[/bold red]" if self.game.seats[0].chips <= 0
                      else "[bold green]You've outlasted everyone![/bold green]")
            self._result = self.game.get_result()
            self._update_table()
            self._update_actions()
            return

        self.game.start_hand()

        log.write(f"[bold cyan]━━━ Hand #{self.game.hands_played} ━━━[/bold cyan]")
        self._flush_log()
        self._update_table()
        self._update_actions()

    def _flush_log(self):
        """Write accumulated action log entries to the UI."""
        if not self.game:
            return
        log = self.query_one("#holdem-log", RichLog)
        for entry in self.game.action_log:
            log.write(entry)
        self.game.action_log.clear()

    def _update_table(self):
        """Re-render the ASCII poker table."""
        if not self.game:
            return
        table_widget = self.query_one("#holdem-table", Static)
        table_widget.update(self.game.render_table())

    def _update_actions(self):
        """Show available actions."""
        actions = self.query_one("#holdem-actions", Static)
        if not self.game or self.game.hand_over or self.game.is_over:
            actions.update("[dim][bold]N[/bold]=Deal  [bold]Esc[/bold]=Leave table[/dim]")
            return

        if self.game.waiting_for_player:
            to_call = self.game.to_call
            chips = self.game.player_seat.chips
            parts = ["[bold]F[/bold]=Fold"]
            if to_call == 0:
                parts.append("[bold]C[/bold]=Check")
            else:
                parts.append(f"[bold]C[/bold]=Call ({to_call})")
            parts.append("[bold]R[/bold]=Raise")
            if chips > 0:
                parts.append(f"[bold]I[/bold]=All In ({chips})")
            actions.update(f"[dim]{' | '.join(parts)}[/dim]")
        else:
            actions.update("[dim]Waiting...[/dim]")

    def action_fold(self):
        if not self.game or not self.game.waiting_for_player:
            return
        log = self.query_one("#holdem-log", RichLog)
        log.write(pick_game_line(HOLDEM_FOLD, self.buddy_state))
        self.game.player_fold()
        self._flush_log()
        self._update_table()
        self._update_actions()

    def action_call(self):
        if not self.game or not self.game.waiting_for_player:
            return
        self.game.player_call()
        self._flush_log()
        self._update_table()
        self._update_actions()

    def action_raise_bet(self):
        if not self.game or not self.game.waiting_for_player:
            return
        self.game.player_raise()
        self._flush_log()
        # Commentary on big pots
        if self.game.pot > 20:
            log = self.query_one("#holdem-log", RichLog)
            log.write(f"[yellow]{pick_game_line(HOLDEM_BIG_POT, self.buddy_state)}[/yellow]")
        self._update_table()
        self._update_actions()

    def action_all_in(self):
        if not self.game or not self.game.waiting_for_player:
            return
        log = self.query_one("#holdem-log", RichLog)
        log.write(f"[bold red]{pick_game_line(HOLDEM_ALL_IN, self.buddy_state)}[/bold red]")
        self.game.player_all_in()
        self._flush_log()
        self._update_table()
        self._update_actions()

    def action_new_hand(self):
        if not self.game:
            return
        if self.game.is_over:
            self._result = self.game.get_result()
            self.dismiss(self._result)
            return
        if self.game.hand_over:
            self._deal_hand()

    def action_back(self):
        if self.game and self.game.hands_played > 0:
            self._result = self.game.get_result()
        self.dismiss(self._result)
