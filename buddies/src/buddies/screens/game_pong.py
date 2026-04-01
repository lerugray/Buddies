"""PongScreen — real-time Pong in the terminal.

Player controls left paddle with W/S or Up/Down arrows.
Buddy controls right paddle based on personality stats.
First to 5 wins. ~15 FPS game loop via Textual timer.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer
from textual.screen import Screen
from textual.timer import Timer
from textual import events

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.pong import PongGame
from buddies.core.games.prose_games import (
    pick_game_line, PONG_SCORE_PLAYER, PONG_SCORE_BUDDY,
    PONG_RALLY, PONG_WIN, PONG_LOSE, PONG_TAUNT,
    GAME_START,
)


class PongScreen(Screen):
    """Real-time Pong game screen."""

    BINDINGS = [
        Binding("w", "move_up", "Up", show=False),
        Binding("s", "move_down", "Down", show=False),
        Binding("up", "move_up", "↑ Up", show=True),
        Binding("down", "move_down", "↓ Down", show=True),
        Binding("p", "pause", "Pause", show=True),
        Binding("n", "new_game", "New Game", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    PongScreen {
        layout: vertical;
        background: $background;
    }
    PongScreen #pong-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }
    PongScreen #pong-field {
        height: 1fr;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
    }
    PongScreen #pong-commentary {
        height: 3;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    PongScreen #pong-help {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: PongGame | None = None
        self._result: GameResult | None = None
        self._timer: Timer | None = None
        self._held_keys: set[str] = set()
        self._commentary: str = ""
        self._commentary_ticks: int = 0
        self._taunt_cooldown: int = 0

    def compose(self) -> ComposeResult:
        yield Static("", id="pong-header")
        yield Static("", id="pong-field")
        yield Static("", id="pong-commentary")
        yield Static("[dim]W/S or ↑/↓=Move  P=Pause  N=New  Esc=Back[/dim]", id="pong-help")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = PongGame(buddy_state=self.buddy_state)
        self._result = None
        self._set_commentary(pick_game_line(GAME_START, self.buddy_state))

        # Start game loop at ~15 FPS
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(1 / 15, self._game_tick)
        self._render()

    def _set_commentary(self, text: str, duration: int = 45):
        """Set commentary text that fades after N ticks."""
        self._commentary = text
        self._commentary_ticks = duration

    def _game_tick(self):
        """Called ~15 times per second."""
        if not self.game or self.game.is_over:
            return

        # Process held keys for smooth movement
        if "up" in self._held_keys or "w" in self._held_keys:
            self.game.move_player_up()
        if "down" in self._held_keys or "s" in self._held_keys:
            self.game.move_player_down()

        old_p = self.game.player_score
        old_b = self.game.buddy_score
        old_rally = self.game.rally_length

        self.game.tick()

        # Check for scoring events
        if self.game.player_score > old_p:
            self._set_commentary(pick_game_line(PONG_SCORE_PLAYER, self.buddy_state, diff="?"))
        elif self.game.buddy_score > old_b:
            self._set_commentary(pick_game_line(PONG_SCORE_BUDDY, self.buddy_state, diff="?"))

        # Rally commentary
        if self.game.rally_length >= 8 and self.game.rally_length > old_rally and self.game.rally_length % 4 == 0:
            self._set_commentary(pick_game_line(PONG_RALLY, self.buddy_state, n=self.game.rally_length))

        # Random taunts
        self._taunt_cooldown = max(0, self._taunt_cooldown - 1)
        if self._taunt_cooldown == 0 and self.game.ticks % 60 == 0 and self.game.personality.should_trash_talk():
            self._set_commentary(pick_game_line(PONG_TAUNT, self.buddy_state))
            self._taunt_cooldown = 90  # Don't taunt too often

        # Fade commentary
        if self._commentary_ticks > 0:
            self._commentary_ticks -= 1
        if self._commentary_ticks == 0:
            self._commentary = ""

        # Check game over
        if self.game.is_over:
            self._result = self.game.get_result()
            if self.game.winner == "player":
                self._set_commentary(pick_game_line(PONG_LOSE, self.buddy_state), duration=999)
            else:
                self._set_commentary(pick_game_line(PONG_WIN, self.buddy_state), duration=999)

        self._render()

    def _render(self):
        """Render the current game state to the screen."""
        if not self.game:
            return

        g = self.game
        name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        # Header with score
        header = self.query_one("#pong-header", Static)
        if g.is_over:
            winner = "YOU WIN!" if g.winner == "player" else f"{name.upper()} WINS!"
            header.update(
                f"[bold green]{winner}[/bold green]  "
                f"You [bold]{g.player_score}[/bold] — [bold]{g.buddy_score}[/bold] {emoji} {name}"
            )
        elif g.is_paused:
            header.update(
                f"[yellow bold]⏸ PAUSED[/yellow bold]  "
                f"You [bold]{g.player_score}[/bold] — [bold]{g.buddy_score}[/bold] {emoji} {name}"
            )
        else:
            header.update(
                f"🏓 You [bold]{g.player_score}[/bold] — [bold]{g.buddy_score}[/bold] {emoji} {name}  "
                f"[dim]│ First to {g.winning_score}[/dim]"
            )

        # Field
        field_widget = self.query_one("#pong-field", Static)
        rows = g.render_field()

        # Add color — player paddle green, buddy paddle based on rarity, ball white
        colored_rows = []
        for row in rows:
            # The borders and content are plain text from the engine
            # Color the paddles and ball with Rich markup
            colored = row
            colored = colored.replace("●", "[bold white]●[/bold white]")
            colored_rows.append(colored)

        field_widget.update("\n".join(colored_rows))

        # Commentary
        commentary_widget = self.query_one("#pong-commentary", Static)
        if self._commentary:
            commentary_widget.update(f"[italic]{self._commentary}[/italic]")
        else:
            commentary_widget.update("")

    def on_key(self, event: events.Key) -> None:
        """Track key presses for smooth held-key movement."""
        if event.key in ("up", "down", "w", "s"):
            self._held_keys.add(event.key)

    def on_key_up(self, event: events.Key) -> None:
        """Track key releases."""
        self._held_keys.discard(event.key)

    def action_move_up(self):
        if self.game and not self.game.is_over and not self.game.is_paused:
            self.game.move_player_up()

    def action_move_down(self):
        if self.game and not self.game.is_over and not self.game.is_paused:
            self.game.move_player_down()

    def action_pause(self):
        if self.game and not self.game.is_over:
            self.game.is_paused = not self.game.is_paused
            self._render()

    def action_new_game(self):
        if self._result:
            self.dismiss(self._result)
            return
        self._start_game()

    def action_back(self):
        if self._timer:
            self._timer.stop()
        self.dismiss(self._result)

    def on_unmount(self):
        if self._timer:
            self._timer.stop()
