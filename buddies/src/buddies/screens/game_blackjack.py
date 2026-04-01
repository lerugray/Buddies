"""BlackjackScreen — play Blackjack against your buddy as dealer.

Press H to hit, S to stand, D to double down.
Buddy deals and plays with personality-driven behavior.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.blackjack import BlackjackGame
from buddies.core.games.prose_games import pick_game_line, GAME_START


class BlackjackScreen(Screen):
    """Blackjack game screen — player vs buddy-dealer."""

    BINDINGS = [
        Binding("h", "hit", "Hit", show=True),
        Binding("s", "stand", "Stand", show=True),
        Binding("d", "double", "Double", show=True),
        Binding("n", "new_game", "New Hand", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    BlackjackScreen {
        layout: vertical;
        background: $background;
    }
    BlackjackScreen #bj-header {
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    BlackjackScreen #bj-table {
        height: auto;
        max-height: 8;
        padding: 0 2;
        text-align: center;
        content-align: center middle;
    }
    BlackjackScreen #bj-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: BlackjackGame | None = None
        self._result: GameResult | None = None
        self._hands_played: int = 0
        self._hands_won: int = 0

    def compose(self) -> ComposeResult:
        yield Static("🃏 BLACKJACK 🃏", id="bj-header")
        yield Static("", id="bj-table")
        yield RichLog(id="bj-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._start_hand()

    def _start_hand(self):
        self.game = BlackjackGame(buddy_state=self.buddy_state)
        self._result = None
        log = self.query_one("#bj-log", RichLog)
        log.clear()

        name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        if self._hands_played == 0:
            log.write(f"[bold]{emoji} {name} shuffles the deck...[/bold]")
            log.write(pick_game_line(GAME_START, self.buddy_state))
        else:
            log.write(f"[dim]— New hand —[/dim]")
            log.write(f"[dim]Record: {self._hands_won}W / {self._hands_played - self._hands_won}L[/dim]")

        log.write("")

        # Deal
        self.game.deal_initial()
        self._update_table(hide_dealer=True)

        # Check for naturals
        if self.game.is_over:
            self._update_table(hide_dealer=False)
            self._show_outcome(log)
        else:
            if self.game.player.is_blackjack:
                log.write("[bold yellow]BLACKJACK![/bold yellow]")
            else:
                can_dbl = "  [bold]D[/bold]=Double" if self.game.can_double() else ""
                log.write(f"[dim][bold]H[/bold]=Hit  [bold]S[/bold]=Stand{can_dbl}  |  [bold]N[/bold]=New  [bold]Esc[/bold]=Back[/dim]")

    def _update_table(self, hide_dealer: bool = False):
        """Update the card table display."""
        if not self.game:
            return
        table = self.query_one("#bj-table", Static)
        name = self.buddy_state.name

        dealer_str = self.game.dealer.display(hide_second=hide_dealer)
        player_str = self.game.player.display()

        table.update(
            f"[bold]{name}[/bold] (dealer): {dealer_str}\n"
            f"\n"
            f"[bold]You[/bold]: {player_str}"
        )

    def _show_outcome(self, log: RichLog):
        """Display the game outcome."""
        if not self.game or not self.game.outcome:
            return

        self._result = self.game.get_result()
        self._hands_played += 1
        name = self.buddy_state.name
        outcome = self.game.outcome.value

        log.write("")

        if self.game.player.is_bust:
            log.write(f"[red bold]BUST![/red bold] You went over 21.")
            log.write(pick_game_line(BJ_DEALER_WINS, self.buddy_state))
        elif self.game.dealer.is_bust:
            log.write(f"[green bold]{name} BUSTS![/green bold] Dealer went over 21!")
            log.write(pick_game_line(BJ_PLAYER_WINS, self.buddy_state))
            self._hands_won += 1
        elif self.game.player.is_blackjack and not self.game.dealer.is_blackjack:
            log.write(f"[bold yellow]BLACKJACK! You win![/bold yellow]")
            self._hands_won += 1
        elif self.game.dealer.is_blackjack and not self.game.player.is_blackjack:
            log.write(f"[red]{name} has BLACKJACK![/red]")
        elif outcome == "win":
            log.write(f"[green bold]You win![/green bold] {self.game.player.value} beats {self.game.dealer.value}.")
            log.write(pick_game_line(BJ_PLAYER_WINS, self.buddy_state))
            self._hands_won += 1
        elif outcome == "lose":
            log.write(f"[red]Dealer wins.[/red] {self.game.dealer.value} beats {self.game.player.value}.")
            log.write(pick_game_line(BJ_DEALER_WINS, self.buddy_state))
        else:
            log.write(f"[yellow]Push![/yellow] Both have {self.game.player.value}.")
            log.write(pick_game_line(BJ_PUSH, self.buddy_state))

        xp = self._result.xp_for_outcome
        log.write(f"[dim]+{xp} XP  |  [bold]N[/bold]=New hand  [bold]Esc[/bold]=Back[/dim]")

    def action_hit(self):
        if not self.game or self.game.is_over or self.game.player.is_standing:
            return
        log = self.query_one("#bj-log", RichLog)
        card = self.game.player_hit()
        log.write(f"  You draw: {card.rich_str()}  (total: {self.game.player.value})")
        self._update_table(hide_dealer=True)

        if self.game.player.is_bust:
            self._update_table(hide_dealer=False)
            self._show_outcome(log)
        elif self.game.player.value == 21:
            log.write("  [bold]21![/bold] Standing automatically.")
            self._do_dealer_play()

    def action_stand(self):
        if not self.game or self.game.is_over or self.game.player.is_standing:
            return
        log = self.query_one("#bj-log", RichLog)
        log.write(f"  You stand on {self.game.player.value}.")
        self.game.player_stand()
        self._do_dealer_play()

    def action_double(self):
        if not self.game or self.game.is_over or not self.game.can_double():
            return
        log = self.query_one("#bj-log", RichLog)
        card = self.game.player_double()
        log.write(f"  [bold]Double down![/bold] You draw: {card.rich_str()}  (total: {self.game.player.value})")
        self._update_table(hide_dealer=True)

        if self.game.player.is_bust:
            self._update_table(hide_dealer=False)
            self._show_outcome(log)
        else:
            self._do_dealer_play()

    def _do_dealer_play(self):
        """Trigger dealer draw sequence and show outcome."""
        if not self.game:
            return
        log = self.query_one("#bj-log", RichLog)
        name = self.buddy_state.name

        log.write("")
        log.write(f"[bold]{name} reveals: {self.game.dealer.cards[1].rich_str()}[/bold]")
        log.write(f"  {name}'s hand: {self.game.dealer.display()}")

        drawn = self.game.dealer_play()
        for card in drawn:
            log.write(f"  {name} draws: {card.rich_str()}  (total: {self.game.dealer.value})")
            # Add personality flavor on risky draws
            if self.game.dealer.value >= 17 and not self.game.dealer.is_bust:
                log.write(f"  {pick_game_line(BJ_DEALER_STANDS, self.buddy_state)}")

        self._update_table(hide_dealer=False)
        self._show_outcome(log)

    def action_new_game(self):
        if self._result:
            # Return last result to arcade so XP is awarded, then start fresh
            self.dismiss(self._result)
            return
        self._start_hand()

    def action_back(self):
        self.dismiss(self._result)


# ---------------------------------------------------------------------------
# Blackjack-specific prose templates
# ---------------------------------------------------------------------------

BJ_DEALER_WINS = {
    "clinical": [
        "House wins. The statistics were not in your favor.",
        "Dealer takes the hand. Expected outcome.",
        "Loss recorded. The house edge is real.",
    ],
    "sarcastic": [
        "Better luck next time. Or not. I don't care.",
        "Oh no, I won. How terrible for you.",
        "The house always wins. Especially when I'm dealing.",
    ],
    "absurdist": [
        "The cards have spoken! And they said 'no'.",
        "Your chips dissolve into the mathematical void.",
        "The deck itself conspired against you. I saw it.",
    ],
    "philosophical": [
        "Every loss at the table is a lesson about attachment.",
        "The cards reveal what was always true.",
        "In Blackjack, as in life, the house has the edge.",
    ],
    "calm": [
        "That's how it goes sometimes. Another hand?",
        "Not your hand. No worries.",
        "The cards weren't there this time.",
    ],
}

BJ_PLAYER_WINS = {
    "clinical": [
        "You win. An anomaly in the house edge.",
        "Player victory confirmed. Recalculating odds.",
        "Interesting. You beat the dealer legitimately.",
    ],
    "sarcastic": [
        "Fine, you win. Don't let it go to your head.",
        "Enjoy it while it lasts.",
        "A win? I must be going soft.",
    ],
    "absurdist": [
        "The cards BOW before you!",
        "Victory! The chips multiply! The table trembles!",
        "You've broken the matrix. Temporarily.",
    ],
    "philosophical": [
        "Fortune smiles today. Savor it.",
        "The cards aligned with your destiny.",
        "A win well earned. The journey continues.",
    ],
    "calm": [
        "Nice hand! Well played.",
        "That's a win. Good call.",
        "Clean victory. Nicely done.",
    ],
}

BJ_PUSH = {
    "clinical": ["Draw. Statistically unremarkable.", "Push. Bets returned.", "Tied outcome."],
    "sarcastic": ["A tie. Riveting.", "Nobody wins. How exciting.", "Push. We both wasted our time."],
    "absurdist": ["The universe refuses to choose!", "A draw?! The cards are INDECISIVE!", "Neither wins. The void claims all."],
    "philosophical": ["Balance in all things.", "A tie speaks of harmony.", "Equal hands, equal fates."],
    "calm": ["Push. Fair enough.", "A tie. On to the next one.", "Even match this time."],
}

BJ_DEALER_STANDS = {
    "clinical": ["Standing. The math checks out."],
    "sarcastic": ["I'll stop here. You're welcome."],
    "absurdist": ["The cards told me to stop. I listen to the cards."],
    "philosophical": ["Enough. Wisdom knows when to hold."],
    "calm": ["Standing. Let's see how this plays out."],
}
