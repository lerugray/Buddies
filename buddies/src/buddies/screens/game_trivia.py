"""TriviaScreen — coding trivia quiz, you vs your buddy.

10 questions, both you and your buddy answer independently.
Press A/B/C/D to pick your answer. Buddy reveals theirs after.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.trivia import TriviaGame
from buddies.core.games.prose_games import (
    pick_game_line,
    TRIVIA_CORRECT, TRIVIA_WRONG,
    TRIVIA_BUDDY_CORRECT, TRIVIA_BUDDY_WRONG,
    TRIVIA_PERFECT,
    GAME_START, GAME_WIN, GAME_LOSE, GAME_DRAW,
)


class TriviaScreen(Screen):
    """Coding trivia quiz screen."""

    BINDINGS = [
        Binding("a", "answer_a", "A", show=True),
        Binding("b", "answer_b", "B", show=True),
        Binding("c", "answer_c", "C", show=True),
        Binding("d", "answer_d", "D", show=True),
        Binding("n", "new_game", "New Game", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    TriviaScreen {
        layout: vertical;
        background: $background;
    }
    TriviaScreen #trivia-header {
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    TriviaScreen #trivia-score {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text;
    }
    TriviaScreen #trivia-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: TriviaGame | None = None
        self._result: GameResult | None = None
        self._waiting_for_answer: bool = False

    def compose(self) -> ComposeResult:
        yield Static("🧠 CODING TRIVIA 🧠", id="trivia-header")
        yield Static("", id="trivia-score")
        yield RichLog(id="trivia-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = TriviaGame(buddy_state=self.buddy_state)
        self._result = None
        self._waiting_for_answer = False
        log = self.query_one("#trivia-log", RichLog)
        log.clear()
        name = self.buddy_state.name
        log.write(f"[bold]10 Questions — You vs {self.buddy_state.species.emoji} {name}[/bold]")
        log.write(pick_game_line(GAME_START, self.buddy_state))
        log.write("")
        self._update_score()
        self._show_question()

    def _update_score(self):
        if not self.game:
            return
        g = self.game
        name = self.buddy_state.name
        q_num = min(g.current_index + 1, len(g.questions))
        score = self.query_one("#trivia-score", Static)
        score.update(
            f"[bold]You[/bold] {g.player_score}  —  {g.buddy_score} [bold]{name}[/bold]"
            f"  │  Question {q_num}/{len(g.questions)}"
        )

    def _show_question(self):
        """Display the current question."""
        if not self.game or self.game.is_over:
            return

        q = self.game.current_question
        if not q:
            return

        log = self.query_one("#trivia-log", RichLog)
        q_num = self.game.current_index + 1

        # Category and difficulty stars
        diff_stars = "⭐" * q.difficulty
        log.write(f"[bold cyan]━━━ Question {q_num} ━━━[/bold cyan]  [dim]{q.category} {diff_stars}[/dim]")
        log.write(f"[bold]{q.text}[/bold]")
        log.write("")

        letters = "ABCD"
        for i, choice in enumerate(q.choices):
            log.write(f"  [bold cyan]{letters[i]}[/bold cyan]  {choice}")

        log.write("")
        log.write("[dim]Press A, B, C, or D to answer[/dim]")
        self._waiting_for_answer = True

    def _answer(self, choice_index: int):
        """Process player's answer."""
        if not self.game or not self._waiting_for_answer or self.game.is_over:
            return

        self._waiting_for_answer = False
        log = self.query_one("#trivia-log", RichLog)
        q = self.game.current_question
        if not q:
            return

        letters = "ABCD"
        rnd = self.game.answer(choice_index)

        log.write("")

        # Show player result
        player_letter = letters[rnd.player_answer]
        if rnd.player_correct:
            log.write(f"[green bold]✓ You picked {player_letter} — Correct![/green bold]")
            log.write(f"  [green]{pick_game_line(TRIVIA_CORRECT, self.buddy_state)}[/green]")
        else:
            correct_text = q.choices[q.answer]
            log.write(f"[red]✗ You picked {player_letter} — Wrong![/red]")
            log.write(f"  [red]{pick_game_line(TRIVIA_WRONG, self.buddy_state, correct=f'{q.correct_letter}: {correct_text}')}[/red]")

        # Show buddy result
        buddy_letter = letters[rnd.buddy_answer]
        name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji
        if rnd.buddy_correct:
            log.write(f"  {emoji} {name} picked [bold]{buddy_letter}[/bold] — [green]Correct![/green]")
            log.write(f"  [dim]{pick_game_line(TRIVIA_BUDDY_CORRECT, self.buddy_state)}[/dim]")
        else:
            log.write(f"  {emoji} {name} picked [bold]{buddy_letter}[/bold] — [red]Wrong[/red]")
            log.write(f"  [dim]{pick_game_line(TRIVIA_BUDDY_WRONG, self.buddy_state)}[/dim]")

        log.write("")
        self._update_score()

        # Check if game is over
        if self.game.is_over:
            self._result = self.game.get_result()
            self._show_final()
        else:
            self._show_question()

    def _show_final(self):
        """Show final results."""
        if not self.game:
            return

        log = self.query_one("#trivia-log", RichLog)
        g = self.game
        name = self.buddy_state.name

        log.write("[bold cyan]━━━━━━ FINAL RESULTS ━━━━━━[/bold cyan]")
        log.write("")
        log.write(f"  [bold]You:[/bold] {g.player_score}/{len(g.questions)}")
        log.write(f"  [bold]{name}:[/bold] {g.buddy_score}/{len(g.questions)}")
        log.write("")

        # Perfect score check
        if g.player_score == len(g.questions):
            log.write(f"[bold yellow]{pick_game_line(TRIVIA_PERFECT, self.buddy_state)}[/bold yellow]")
        elif g.player_score > g.buddy_score:
            log.write(f"[green bold]You win! {pick_game_line(GAME_LOSE, self.buddy_state)}[/green bold]")
        elif g.player_score < g.buddy_score:
            log.write(f"[red]{name} wins! {pick_game_line(GAME_WIN, self.buddy_state)}[/red]")
        else:
            log.write(f"[yellow]It's a tie! {pick_game_line(GAME_DRAW, self.buddy_state)}[/yellow]")

        xp = self._result.xp_for_outcome if self._result else 0
        log.write("")
        log.write(f"[dim]+{xp} XP  |  [bold]N[/bold]=New game  [bold]Esc[/bold]=Back[/dim]")

    def action_answer_a(self):
        self._answer(0)

    def action_answer_b(self):
        self._answer(1)

    def action_answer_c(self):
        self._answer(2)

    def action_answer_d(self):
        self._answer(3)

    def action_new_game(self):
        if self._result:
            self.dismiss(self._result)
            return
        self._start_game()

    def action_back(self):
        self.dismiss(self._result)
