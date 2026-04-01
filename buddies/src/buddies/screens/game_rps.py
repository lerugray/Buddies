"""RPSScreen — Rock-Paper-Scissors tournament against your buddy.

Best-of-5 format. Buddy AI driven by personality stats.
Press 1/2/3 to throw Rock/Paper/Scissors.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameOutcome, GameResult
from buddies.core.games.rps import RPSGame, RPSChoice, CHOICE_EMOJI
from buddies.core.games.prose_games import (
    pick_game_line, RPS_THROW, RPS_WIN, RPS_LOSE, RPS_DRAW,
    RPS_STREAK, RPS_STREAK_BROKEN, GAME_START, GAME_WIN, GAME_LOSE,
)


class RPSScreen(Screen):
    """Rock-Paper-Scissors tournament screen."""

    BINDINGS = [
        Binding("1", "throw_rock", "🪨 Rock", show=True),
        Binding("2", "throw_paper", "📄 Paper", show=True),
        Binding("3", "throw_scissors", "✂️ Scissors", show=True),
        Binding("n", "new_game", "New Game", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    RPSScreen {
        layout: vertical;
        background: $background;
    }
    RPSScreen #rps-header {
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    RPSScreen #rps-score {
        height: 3;
        content-align: center middle;
        text-align: center;
        color: $text;
    }
    RPSScreen #rps-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: RPSGame | None = None
        self._result: GameResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("✊ ROCK — PAPER — SCISSORS ✂️", id="rps-header")
        yield Static("", id="rps-score")
        yield RichLog(id="rps-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = RPSGame(buddy_state=self.buddy_state, best_of=5)
        self._result = None
        log = self.query_one("#rps-log", RichLog)
        log.clear()
        log.write(f"[bold]Best of 5 vs {self.buddy_state.species.emoji} {self.buddy_state.name}[/bold]")
        log.write(pick_game_line(GAME_START, self.buddy_state))
        log.write("")
        log.write("[dim]Press [bold]1[/bold]=Rock  [bold]2[/bold]=Paper  [bold]3[/bold]=Scissors[/dim]")
        log.write("")
        self._update_score()

    def _update_score(self):
        if not self.game:
            return
        g = self.game
        name = self.buddy_state.name
        score = self.query_one("#rps-score", Static)
        score.update(
            f"[bold]You[/bold] {g.player_wins}  —  {g.buddy_wins} [bold]{name}[/bold]"
            f"  │  Round {g.round_num} of {g.best_of}  │  Draws: {g.draws}"
        )

    def _play(self, choice: RPSChoice):
        if not self.game or self.game.is_over:
            return

        log = self.query_one("#rps-log", RichLog)
        rnd = self.game.play_round(choice)

        # Show throws
        p_emoji = CHOICE_EMOJI[rnd.player_choice]
        b_emoji = CHOICE_EMOJI[rnd.buddy_choice]
        log.write(f"[bold]Round {rnd.round_num}:[/bold]")
        log.write(f"  You threw: {p_emoji} {rnd.player_choice.value}")

        # Buddy's throw with personality flavor
        buddy_line = pick_game_line(RPS_THROW, self.buddy_state, choice=rnd.buddy_choice.value)
        log.write(f"  {self.buddy_state.name}: {b_emoji} {buddy_line}")

        # Result
        if rnd.outcome == GameOutcome.WIN:
            log.write(f"  [green bold]You win this round![/green bold]")
            # Check if buddy had a streak that was broken
            buddy_streak = self.game.get_buddy_streak()
        elif rnd.outcome == GameOutcome.LOSE:
            line = pick_game_line(RPS_WIN, self.buddy_state, choice=rnd.buddy_choice.value)
            log.write(f"  [red]{self.buddy_state.name} wins![/red] {line}")
            # Check for buddy win streak
            streak = self.game.get_buddy_streak()
            if streak >= 3:
                log.write(f"  [yellow]{pick_game_line(RPS_STREAK, self.buddy_state, n=streak)}[/yellow]")
        else:
            line = pick_game_line(RPS_DRAW, self.buddy_state, choice=rnd.buddy_choice.value)
            log.write(f"  [dim]Draw![/dim] {line}")

        log.write("")
        self._update_score()

        # Check for game over
        if self.game.is_over:
            self._result = self.game.get_result()
            winner = self.game.winner
            if winner == "player":
                log.write(f"[green bold]═══ YOU WIN THE MATCH! ═══[/green bold]")
                log.write(pick_game_line(GAME_LOSE, self.buddy_state))
            else:
                log.write(f"[red bold]═══ {self.buddy_state.name.upper()} WINS THE MATCH! ═══[/red bold]")
                log.write(pick_game_line(GAME_WIN, self.buddy_state))

            log.write("")
            log.write(f"[dim]Final: You {self.game.player_wins} — {self.game.buddy_wins} {self.buddy_state.name}[/dim]")
            xp = self._result.xp_for_outcome
            log.write(f"[dim]+{xp} XP  |  Press [bold]N[/bold] for new game, [bold]Esc[/bold] to leave[/dim]")

    def action_throw_rock(self):
        self._play(RPSChoice.ROCK)

    def action_throw_paper(self):
        self._play(RPSChoice.PAPER)

    def action_throw_scissors(self):
        self._play(RPSChoice.SCISSORS)

    def action_new_game(self):
        # If there's a result from last game, dismiss it first so app can process
        if self._result:
            self.dismiss(self._result)
            return
        self._start_game()

    def action_back(self):
        self.dismiss(self._result)
