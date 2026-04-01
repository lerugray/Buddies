"""GamesScreen — the Games Arcade hub.

ASCII art arcade cabinet menu with game selection.
Each game launches as a separate pushed screen.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.screens.game_rps import RPSScreen


ARCADE_HEADER = """\
[bold cyan]
╔══════════════════════════════════════════════╗
║          🕹️  BUDDIES ARCADE  🕹️              ║
║     Insert coin... just kidding, it's free   ║
╚══════════════════════════════════════════════╝
[/bold cyan]"""

GAME_MENU = """\
[bold]Available Games:[/bold]

  [bold cyan]1[/bold cyan]  ✊ [bold]Rock-Paper-Scissors[/bold]  — Best of 5, personality-driven AI
  [dim]2[/dim]  🃏 [dim]Blackjack[/dim]              — [dim]Coming soon[/dim]
  [dim]3[/dim]  🎰 [dim]Texas Hold'em[/dim]           — [dim]Coming soon[/dim]
  [dim]4[/dim]  🂡 [dim]Whist[/dim]                   — [dim]Coming soon[/dim]
  [dim]5[/dim]  ⚔️ [dim]Battle[/dim]                  — [dim]Coming soon[/dim]
  [dim]6[/dim]  🧠 [dim]Trivia[/dim]                  — [dim]Coming soon[/dim]
  [dim]7[/dim]  🏓 [dim]Pong[/dim]                    — [dim]Coming soon[/dim]

[dim]Press a number to play, Esc to exit[/dim]"""


class GamesScreen(Screen):
    """The Games Arcade hub — pick a game to play."""

    BINDINGS = [
        Binding("1", "play_rps", "RPS", show=True),
        Binding("2", "play_blackjack", "Blackjack", show=False),
        Binding("3", "play_holdem", "Hold'em", show=False),
        Binding("4", "play_whist", "Whist", show=False),
        Binding("5", "play_battle", "Battle", show=False),
        Binding("6", "play_trivia", "Trivia", show=False),
        Binding("7", "play_pong", "Pong", show=False),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    GamesScreen {
        layout: vertical;
        background: $background;
    }
    GamesScreen #arcade-display {
        height: 1fr;
        padding: 1 2;
        background: $surface;
        border: round $primary;
        margin: 1 2;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self._last_result: GameResult | None = None

    def compose(self) -> ComposeResult:
        yield RichLog(id="arcade-display", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._show_menu()

    def _show_menu(self):
        display = self.query_one("#arcade-display", RichLog)
        display.clear()
        display.write(ARCADE_HEADER)
        display.write(GAME_MENU)

        if self._last_result:
            r = self._last_result
            outcome_str = {
                "win": "[green]WIN[/green]",
                "lose": "[red]LOSS[/red]",
                "draw": "[yellow]DRAW[/yellow]",
            }[r.outcome.value]
            display.write("")
            display.write(f"[dim]Last game: {r.game_type.value.upper()} — {outcome_str} (+{r.xp_for_outcome} XP)[/dim]")

    def _on_game_dismissed(self, result: GameResult | None) -> None:
        """Handle game screen dismissal — store result and return to menu."""
        if result:
            self._last_result = result
        self._show_menu()

    def action_play_rps(self):
        self.app.push_screen(
            RPSScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_blackjack(self):
        self._coming_soon("Blackjack")

    def action_play_holdem(self):
        self._coming_soon("Texas Hold'em")

    def action_play_whist(self):
        self._coming_soon("Whist")

    def action_play_battle(self):
        self._coming_soon("Battle")

    def action_play_trivia(self):
        self._coming_soon("Trivia")

    def action_play_pong(self):
        self._coming_soon("Pong")

    def _coming_soon(self, name: str):
        display = self.query_one("#arcade-display", RichLog)
        display.write(f"\n[yellow]{name} is coming soon! Stay tuned.[/yellow]")

    def action_back(self):
        self.dismiss(self._last_result)
