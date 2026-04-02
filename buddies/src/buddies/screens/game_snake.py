"""SnakeScreen — Buffer Overflow (Snake) in the terminal.

Player moves the snake with arrow keys. Eat data packets to grow.
Dodge obstacles, collect power-ups, survive as long as possible.
~10 FPS game loop via Textual timer.
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
from buddies.core.games.snake import SnakeGame, Direction, GRID_W, GRID_H
from buddies.core.games.prose_games import pick_game_line, GAME_WIN, GAME_LOSE, GAME_START

# Personality-driven death commentary
SNAKE_DEATH = {
    "clinical": [
        "Segmentation fault. Core dumped.",
        "Null pointer dereference at {score} points.",
        "Stack overflow at length {length}. Ironic.",
        "Fatal: memory access violation.",
    ],
    "sarcastic": [
        "WOW. Length {length}. Incredible. Really.",
        "Died at {score} points. A bold strategy.",
        "That obstacle was CLEARLY in your path.",
        "'{length} segments' — a legacy worth celebrating.",
    ],
    "absurdist": [
        "THE FIREWALL HAS CONSUMED ME! ({score} pts)",
        "I return to the void from whence I came!",
        "At length {length}, I achieved enlightenment. Then died.",
        "The memory leak... it got me. Tell my packets I loved them.",
    ],
    "philosophical": [
        "Length {length}. A life fully lived.",
        "To crash is to understand the system's limits.",
        "The snake must end for the pointer to begin anew.",
        "We are all just memory — and memory leaks.",
    ],
    "calm": [
        "Game over. {score} points. Not bad.",
        "Length {length}. A reasonable run.",
        "Hit a wall at {score}. These things happen.",
        "Died. Ready to go again when you are.",
    ],
}

SNAKE_MILESTONE = [
    "Length {length}! The packets fear you!",
    "{score} points! The data flows!",
    "Length {length} — this is getting serious.",
    "{score} pts! Stack overflow imminent!",
]

SNAKE_MULTIPLIER = {
    "clinical": ["2x multiplier active. Score efficiency increased."],
    "sarcastic": ["Ooh, a multiplier. Try not to immediately die."],
    "absurdist": ["THE STAR BLESSES YOU WITH DOUBLE POINTS!"],
    "philosophical": ["In the multiplied moment, all points are doubled."],
    "calm": ["Multiplier active. Make it count."],
}

SNAKE_SPEEDBOOST = {
    "clinical": ["Speed boost engaged. Collision risk elevated."],
    "sarcastic": ["Speed boost. What could possibly go wrong."],
    "absurdist": ["I AM SPEED! I AM VELOCITY! I AM DOOMED!"],
    "philosophical": ["Faster motion, sharper mind. Or so one hopes."],
    "calm": ["Speed boost. Stay focused."],
}

SNAKE_GARBAGE = {
    "clinical": ["Garbage collected. {removed} segments freed."],
    "sarcastic": ["Garbage collector ran. You're welcome."],
    "absurdist": ["THE BROOM OF DESTINY SWEEPS AWAY YOUR BURDENS!"],
    "philosophical": ["What was held is released. The snake breathes."],
    "calm": ["Garbage collected. A little lighter now."],
}


class SnakeScreen(Screen):
    """Buffer Overflow — Snake arcade game."""

    BINDINGS = [
        Binding("up", "move_up", "↑", show=True),
        Binding("down", "move_down", "↓", show=True),
        Binding("left", "move_left", "←", show=True),
        Binding("right", "move_right", "→", show=True),
        Binding("w", "move_up", "W", show=False),
        Binding("s", "move_down", "S", show=False),
        Binding("a", "move_left", "A", show=False),
        Binding("d", "move_right", "D", show=False),
        Binding("p", "pause", "Pause", show=True),
        Binding("n", "new_game", "New", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    SnakeScreen {
        layout: vertical;
        background: $background;
    }
    SnakeScreen #snake-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }
    SnakeScreen #snake-field {
        height: 1fr;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        border: round $primary;
        margin: 0 2;
    }
    SnakeScreen #snake-commentary {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, buddy_state: BuddyState, high_score: int = 0):
        super().__init__()
        self.buddy_state = buddy_state
        self.high_score = high_score
        self.game: SnakeGame | None = None
        self._result: GameResult | None = None
        self._timer: Timer | None = None
        self._paused = False
        self._last_comment = ""
        self._milestone_next = 50  # Next score milestone for comment

    def compose(self) -> ComposeResult:
        yield Static("", id="snake-header")
        yield Static("", id="snake-field")
        yield Static("", id="snake-commentary")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        if self._timer:
            self._timer.stop()
        self.game = SnakeGame(buddy_state=self.buddy_state, high_score=self.high_score)
        self._paused = False
        self._milestone_next = 50
        self._last_comment = pick_game_line(GAME_START, self.buddy_state)
        self._timer = self.set_interval(self.game.current_tick_interval, self._tick)
        self._render()

    def _tick(self):
        if not self.game or self._paused:
            return

        events = self.game.tick(self.game.current_tick_interval)

        # Process events for commentary
        for ev in events:
            if ev == "wall" or ev == "self" or ev == "obstacle":
                self._last_comment = pick_game_line(
                    SNAKE_DEATH, self.buddy_state,
                    score=self.game.score, length=self.game.length,
                )
            elif ev == "powerup:⚡":
                self._last_comment = pick_game_line(SNAKE_SPEEDBOOST, self.buddy_state)
            elif ev == "powerup:★":
                self._last_comment = pick_game_line(SNAKE_MULTIPLIER, self.buddy_state)
            elif ev == "powerup:🧹":
                self._last_comment = pick_game_line(SNAKE_GARBAGE, self.buddy_state, removed=3)

        # Milestone commentary
        if self.game.score >= self._milestone_next:
            import random
            self._last_comment = random.choice(SNAKE_MILESTONE).format(
                score=self.game.score, length=self.game.length
            )
            self._milestone_next = self.game.score + random.randint(40, 80)

        # Update timer interval for speed ramp
        if self._timer:
            self._timer.stop()
            if self.game.alive:
                self._timer = self.set_interval(self.game.current_tick_interval, self._tick)

        self._render()

        if self.game.is_over:
            self._result = self.game.get_result()
            if self._timer:
                self._timer.stop()

    def _render(self):
        if not self.game:
            return

        g = self.game

        # Header
        mult_str = f" [bold yellow]×2![/bold yellow]" if g.multiplier_ticks > 0 else ""
        boost_str = f" [bold cyan]BOOST![/bold cyan]" if g.speedboost_ticks > 0 else ""
        hi_str = f"  HI:{g.high_score}" if g.high_score > 0 else ""
        header = (
            f"[bold]Buffer Overflow[/bold]  "
            f"Score: [bold green]{g.score}[/bold green]{mult_str}{boost_str}  "
            f"Length: {g.length}{hi_str}"
        )
        self.query_one("#snake-header", Static).update(header)

        if g.is_over:
            # Game over overlay
            lines = [
                "┌─────────────────────────────┐",
                "│      SEGMENTATION FAULT      │",
                f"│   Score: {g.score:<6}  Length: {g.length:<4}│",
                "│  [N] New Game  [Esc] Exit    │",
                "└─────────────────────────────┘",
            ]
            field_text = "\n".join(lines)
            self.query_one("#snake-field", Static).update(field_text)
        else:
            # Render grid with border
            rows = g.render_grid()
            bordered = "┌" + "─" * GRID_W + "┐\n"
            for row in rows:
                # Color the grid elements
                colored = row
                colored = colored.replace("►", "[bold green]►[/bold green]")
                colored = colored.replace("◄", "[bold green]◄[/bold green]")
                colored = colored.replace("▲", "[bold green]▲[/bold green]")
                colored = colored.replace("▼", "[bold green]▼[/bold green]")
                colored = colored.replace("█", "[green]█[/green]")
                colored = colored.replace("●", "[bold yellow]●[/bold yellow]")
                colored = colored.replace("⚡", "[bold cyan]⚡[/bold cyan]")
                colored = colored.replace("★", "[bold yellow]★[/bold yellow]")
                colored = colored.replace("☠", "[bold red]☠[/bold red]")
                colored = colored.replace("🧹", "[bold blue]🧹[/bold blue]")
                colored = colored.replace("█", "[red]█[/red]")  # obstacles after snake
                bordered += f"│{colored}│\n"
            bordered += "└" + "─" * GRID_W + "┘"
            self.query_one("#snake-field", Static).update(bordered)

        # Commentary
        bs = self.buddy_state
        comment = f"[dim]{bs.species.emoji} {bs.name}:[/dim] {self._last_comment}"
        self.query_one("#snake-commentary", Static).update(comment)

    def action_move_up(self):
        if self.game and self.game.alive:
            self.game.set_direction(Direction.UP)

    def action_move_down(self):
        if self.game and self.game.alive:
            self.game.set_direction(Direction.DOWN)

    def action_move_left(self):
        if self.game and self.game.alive:
            self.game.set_direction(Direction.LEFT)

    def action_move_right(self):
        if self.game and self.game.alive:
            self.game.set_direction(Direction.RIGHT)

    def action_pause(self):
        self._paused = not self._paused
        status = "PAUSED — press P to resume" if self._paused else self._last_comment
        self.query_one("#snake-commentary", Static).update(
            f"[bold yellow]{status}[/bold yellow]" if self._paused else status
        )

    def action_new_game(self):
        if self._result:
            self.high_score = max(self.high_score, self._result.score.get("score", 0))
        self._result = None
        self._start_game()

    def action_back(self):
        if self._timer:
            self._timer.stop()
        self.dismiss(self._result)
