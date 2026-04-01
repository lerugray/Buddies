"""WhistScreen — classic trick-taking card game.

You + partner buddy vs 2 opponent buddies around the table.
Play cards by pressing 1-9 (or 0 for 10th+) to select from your hand.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.whist import WhistGame
from buddies.core.games.prose_games import pick_game_line, GAME_START, GAME_WIN, GAME_LOSE, GAME_DRAW


# Whist prose
WHIST_TRICK_WIN = [
    "Nice trick! Teamwork!",
    "That one's ours!",
    "Got it! Keep it up!",
    "Trick secured. Well played.",
]

WHIST_TRICK_LOSE = [
    "They took that one. We'll get the next.",
    "Lost that trick. Stay focused.",
    "Ouch. Regroup and rally.",
    "They're playing well. So are we.",
]

WHIST_TRUMP_PLAY = [
    "Trump card! The power move!",
    "Trumping in! Take that!",
    "Out comes the trump!",
]


class WhistScreen(Screen):
    """Whist card game screen — 4 players, trick-taking."""

    BINDINGS = [
        Binding("1", "play_1", "Card 1", show=False),
        Binding("2", "play_2", "Card 2", show=False),
        Binding("3", "play_3", "Card 3", show=False),
        Binding("4", "play_4", "Card 4", show=False),
        Binding("5", "play_5", "Card 5", show=False),
        Binding("6", "play_6", "Card 6", show=False),
        Binding("7", "play_7", "Card 7", show=False),
        Binding("8", "play_8", "Card 8", show=False),
        Binding("9", "play_9", "Card 9", show=False),
        Binding("0", "play_10", "Card 10+", show=False),
        Binding("n", "new_round", "New Round", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    WhistScreen {
        layout: vertical;
        background: $background;
    }
    WhistScreen #whist-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
    }
    WhistScreen #whist-table {
        height: auto;
        min-height: 8;
        padding: 0 1;
        content-align: center middle;
        text-align: center;
    }
    WhistScreen #whist-hand {
        height: auto;
        min-height: 3;
        padding: 0 2;
        content-align: center middle;
        text-align: center;
    }
    WhistScreen #whist-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }
    """

    def __init__(self, buddy_state: BuddyState, party_states: list[BuddyState] | None = None):
        super().__init__()
        self.buddy_state = buddy_state
        self.party_states = party_states or []
        self.game: WhistGame | None = None
        self._result: GameResult | None = None
        self._playable: list = []

    def compose(self) -> ComposeResult:
        yield Static("🂡 WHIST 🂡", id="whist-header")
        yield Static("", id="whist-table")
        yield Static("", id="whist-hand")
        yield RichLog(id="whist-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        # Assign buddies to roles: partner, opp1, opp2
        partner = self.party_states[0] if len(self.party_states) >= 1 else None
        opp1 = self.party_states[1] if len(self.party_states) >= 2 else None
        opp2 = self.party_states[2] if len(self.party_states) >= 3 else None

        self.game = WhistGame(
            player_state=self.buddy_state,
            partner_state=partner,
            opp1_state=opp1,
            opp2_state=opp2,
        )
        self._result = None

        log = self.query_one("#whist-log", RichLog)
        log.clear()

        # Show teams
        p = self.game.players
        log.write("[bold]Teams:[/bold]")
        log.write(f"  Your team: {p[0].emoji} {p[0].name} + {p[2].emoji} {p[2].name}")
        log.write(f"  Opponents: {p[1].emoji} {p[1].name} + {p[3].emoji} {p[3].name}")
        log.write("")
        log.write(pick_game_line(GAME_START, self.buddy_state))
        log.write("")

        self._deal_round()

    def _deal_round(self):
        if not self.game:
            return
        self.game.deal()
        self._flush_log()
        self._update_all()

    def _flush_log(self):
        if not self.game:
            return
        log = self.query_one("#whist-log", RichLog)
        for entry in self.game.action_log:
            log.write(entry)
        self.game.action_log.clear()

    def _update_all(self):
        self._update_table()
        self._update_hand()

    def _update_table(self):
        if not self.game:
            return
        table = self.query_one("#whist-table", Static)
        table.update(self.game.render_table())

    def _update_hand(self):
        """Show the player's hand with numbered selections."""
        if not self.game:
            return
        hand_widget = self.query_one("#whist-hand", Static)
        player = self.game.players[0]

        if not player.hand:
            hand_widget.update("[dim]No cards[/dim]")
            return

        playable = self.game.get_playable_cards()
        self._playable = playable

        parts = []
        for i, card in enumerate(player.hand):
            num = (i + 1) % 10  # 1-9, then 0
            if card in playable:
                parts.append(f"[bold cyan]{num}[/bold cyan]:{card.rich_str()}")
            else:
                parts.append(f"[dim]{num}:{card.name}[/dim]")

        hand_widget.update("Your hand: " + "  ".join(parts))

    def _play_index(self, idx: int):
        """Play card at the given index in the player's hand."""
        if not self.game or not self.game.waiting_for_player:
            return

        player = self.game.players[0]
        if idx >= len(player.hand):
            return

        card = player.hand[idx]
        playable = self.game.get_playable_cards()
        if card not in playable:
            return

        # Check if playing trump
        if self.game.trump_suit and card.suit == self.game.trump_suit and self.game.current_trick.cards:
            log = self.query_one("#whist-log", RichLog)
            import random
            log.write(f"[yellow]{random.choice(WHIST_TRUMP_PLAY)}[/yellow]")

        self.game.play_card(card)
        self._flush_log()

        # Add trick commentary
        if self.game.tricks_played:
            last_trick = self.game.tricks_played[-1]
            winner = self.game.players[last_trick.winner_index]
            log = self.query_one("#whist-log", RichLog)
            if winner.team == 0:
                import random
                log.write(f"[green]{random.choice(WHIST_TRICK_WIN)}[/green]")
            else:
                import random
                log.write(f"[red]{random.choice(WHIST_TRICK_LOSE)}[/red]")

        # Check game over
        if self.game.is_over:
            self._show_result()

        self._update_all()

    def _show_result(self):
        if not self.game:
            return
        log = self.query_one("#whist-log", RichLog)
        self._result = self.game.get_result()

        log.write("")
        log.write("[bold cyan]━━━ ROUND OVER ━━━[/bold cyan]")
        log.write(f"Your team: {self.game.tricks_won[0]} tricks")
        log.write(f"Opponents: {self.game.tricks_won[1]} tricks")

        if self.game.tricks_won[0] > self.game.tricks_won[1]:
            log.write(f"\n[green bold]Your team wins![/green bold]")
            log.write(pick_game_line(GAME_WIN, self.buddy_state))
        elif self.game.tricks_won[0] < self.game.tricks_won[1]:
            log.write(f"\n[red]Opponents win.[/red]")
            log.write(pick_game_line(GAME_LOSE, self.buddy_state))
        else:
            log.write(f"\n[yellow]It's a tie![/yellow]")
            log.write(pick_game_line(GAME_DRAW, self.buddy_state))

        xp = self._result.xp_for_outcome
        log.write(f"\n[dim]+{xp} XP  |  [bold]N[/bold]=New round  [bold]Esc[/bold]=Back[/dim]")

    # Card play actions (1-9, 0)
    def action_play_1(self): self._play_index(0)
    def action_play_2(self): self._play_index(1)
    def action_play_3(self): self._play_index(2)
    def action_play_4(self): self._play_index(3)
    def action_play_5(self): self._play_index(4)
    def action_play_6(self): self._play_index(5)
    def action_play_7(self): self._play_index(6)
    def action_play_8(self): self._play_index(7)
    def action_play_9(self): self._play_index(8)
    def action_play_10(self): self._play_index(9)

    def action_new_round(self):
        if self._result:
            self.dismiss(self._result)
            return
        if self.game and self.game.is_over:
            self._deal_round()

    def action_back(self):
        self.dismiss(self._result)
