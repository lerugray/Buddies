"""SkiFreeScreen — Stack Descent in the terminal.

Buddy skis down a mountain of deprecated code.
Dodge obstacles, collect pickups, outrun The Auditor.
~10 FPS scroll loop via Textual timer.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer
from textual.screen import Screen
from textual.timer import Timer

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.skifree import (
    SkiFreeGame, CellType, NUM_LANES, VISIBLE_ROWS, AUDITOR_DISTANCE, DISTANCE_PER_TICK,
)
from buddies.core.games.prose_games import pick_game_line, GAME_WIN, GAME_LOSE

SKIFREE_CRASH = {
    "clinical": [
        "Impact detected. {distance}m traveled. Damage: critical.",
        "Collision with {obstacle}. Run terminated at {distance}m.",
        "Fatal obstacle contact. Distance: {distance}m.",
    ],
    "sarcastic": [
        "Ran into a {obstacle}. Bold choice.",
        "{distance}m and then... {obstacle}. Classic.",
        "A {obstacle}. Of all things. {distance}m.",
    ],
    "absurdist": [
        "THE {obstacle} OF DESTINY HAS CLAIMED ME! ({distance}m)",
        "I skied right into a {obstacle}. The universe willed it.",
        "{distance}m of glory, ended by a {obstacle}.",
    ],
    "philosophical": [
        "The {obstacle} was always there. We simply met. {distance}m.",
        "All runs end. This one ended at a {obstacle}.",
        "{distance}m. The mountain reclaims its own.",
    ],
    "calm": [
        "Hit a {obstacle} at {distance}m. These things happen.",
        "{distance}m — not bad. The {obstacle} got me.",
        "Ended by a {obstacle}. Ready to try again.",
    ],
}

SKIFREE_AUDITOR_APPEARS = {
    "clinical": ["Warning: The Auditor detected. Closing velocity: high."],
    "sarcastic": ["Oh great. The Auditor. The AUDITOR is here."],
    "absurdist": ["HE COMES. THE SUIT. THE CLIPBOARD. THE END."],
    "philosophical": ["The performance review catches up with us all."],
    "calm": ["The Auditor is behind you. Just keep moving."],
}

SKIFREE_AUDITOR_CLOSE = {
    "clinical": ["Auditor closing distance. Escape probability: low."],
    "sarcastic": ["He's GAINING. Probably because of your Q3 metrics."],
    "absurdist": ["THE CLIPBOARD GROWS LOUDER. THE QUESTIONS BEGIN."],
    "philosophical": ["You cannot outrun what you owe."],
    "calm": ["He's close. Just don't stop."],
}

SKIFREE_CAUGHT = {
    "clinical": ["Caught by Auditor at {distance}m. Performance review initiated."],
    "sarcastic": ["Caught. He's going to ask about your test coverage."],
    "absurdist": ["THE AUDIT BEGINS. NOTHING WILL EVER BE THE SAME."],
    "philosophical": ["All things must be accounted for. Even you."],
    "calm": ["Caught at {distance}m. The audit has begun."],
}

SKIFREE_PICKUP_DUCK = [
    "🦆 Rubber duck! +100 points!",
    "Found a rubber duck. Debugging begins.",
    "🦆 The duck watches over you.",
]

SKIFREE_PICKUP_COFFEE = [
    "☕ Coffee! Temporary immunity!",
    "Caffeinated! Shield active.",
    "☕ The coffee protects you — briefly.",
]

SKIFREE_PICKUP_COMMIT = [
    "📦 Git commit found! Auditor delayed!",
    "Committed to the bit. +50m lead.",
    "📦 Pushed to remote. The Auditor sighs.",
]

# Cell type to display string mapping
CELL_DISPLAY = {
    CellType.EMPTY: " ",
    CellType.OBSTACLE_LEGACY: "[red]█[/red]",
    CellType.OBSTACLE_BUG: "[bold red]B[/bold red]",
    CellType.OBSTACLE_MERGE: "[bold yellow]X[/bold yellow]",
    CellType.OBSTACLE_WALL: "[red]▓[/red]",
    CellType.COFFEE: "[bold yellow]☕[/bold yellow]",
    CellType.DUCK: "[bold yellow]🦆[/bold yellow]",
    CellType.COMMIT: "[bold green]📦[/bold green]",
    CellType.PLAYER: "[bold green]🎿[/bold green]",
    CellType.AUDITOR: "[bold magenta]👔[/bold magenta]",
}

OBSTACLE_NAMES = {
    CellType.OBSTACLE_LEGACY: "legacy code",
    CellType.OBSTACLE_BUG: "bug report",
    CellType.OBSTACLE_MERGE: "merge conflict",
    CellType.OBSTACLE_WALL: "firewall",
}


class SkiFreeScreen(Screen):
    """Stack Descent — ski free arcade game."""

    BINDINGS = [
        Binding("left", "move_left", "←", show=True),
        Binding("right", "move_right", "→", show=True),
        Binding("a", "move_left", "A", show=False),
        Binding("d", "move_right", "D", show=False),
        Binding("p", "pause", "Pause", show=True),
        Binding("n", "new_game", "New", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    SkiFreeScreen {
        layout: vertical;
        background: $background;
    }
    SkiFreeScreen #ski-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }
    SkiFreeScreen #ski-field {
        height: 1fr;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        border: round $primary;
        margin: 0 2;
    }
    SkiFreeScreen #ski-commentary {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: SkiFreeGame | None = None
        self._result: GameResult | None = None
        self._timer: Timer | None = None
        self._paused = False
        self._last_comment = ""
        self._crash_cell = CellType.OBSTACLE_LEGACY

    def compose(self) -> ComposeResult:
        yield Static("", id="ski-header")
        yield Static("", id="ski-field")
        yield Static("", id="ski-commentary")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        if self._timer:
            self._timer.stop()
        self.game = SkiFreeGame(buddy_state=self.buddy_state)
        self._paused = False
        self._last_comment = f"Ski down the mountain. Avoid the legacy code."
        self._timer = self.set_interval(self.game.current_tick_interval, self._tick)
        self._render()

    def _tick(self):
        if not self.game or self._paused:
            return

        import random
        evts = self.game.tick(self.game.current_tick_interval)

        for ev in evts:
            if ev == "crash":
                self._last_comment = pick_game_line(
                    SKIFREE_CRASH, self.buddy_state,
                    distance=self.game.distance,
                    obstacle=OBSTACLE_NAMES.get(self._crash_cell, "obstacle"),
                )
            elif ev == "caught":
                self._last_comment = pick_game_line(
                    SKIFREE_CAUGHT, self.buddy_state,
                    distance=self.game.distance,
                )
            elif ev == "auditor_appears":
                self._last_comment = pick_game_line(SKIFREE_AUDITOR_APPEARS, self.buddy_state)
            elif ev == "pickup:coffee":
                self._last_comment = random.choice(SKIFREE_PICKUP_COFFEE)
            elif ev == "pickup:duck":
                self._last_comment = random.choice(SKIFREE_PICKUP_DUCK)
            elif ev == "pickup:commit":
                self._last_comment = random.choice(SKIFREE_PICKUP_COMMIT)

        # Auditor close warning
        if self.game.auditor_warning and not self.game.is_over:
            if self.game.ticks % 15 == 0:
                self._last_comment = pick_game_line(SKIFREE_AUDITOR_CLOSE, self.buddy_state)

        # Update timer for speed ramp
        if self._timer:
            self._timer.stop()
            if self.game.alive:
                self._timer = self.set_interval(self.game.current_tick_interval, self._tick)

        self._render()

        if self.game.is_over:
            self._result = self.game.get_result()

    def _render(self):
        if not self.game:
            return
        g = self.game

        # Header
        shield_str = " [bold cyan]🛡SHIELD[/bold cyan]" if g.shield_ticks > 0 else ""
        auditor_str = " [bold magenta]👔 AUDITOR![/bold magenta]" if g.auditor_warning else ""
        header = (
            f"[bold]Stack Descent[/bold]  "
            f"Score: [bold green]{g.score}[/bold green]  "
            f"Distance: {g.distance}m"
            f"{shield_str}{auditor_str}"
        )
        self.query_one("#ski-header", Static).update(header)

        if g.is_over:
            lines = [
                "┌──────────────────────────────┐",
                "│       AUDIT COMPLETE         │",
                f"│  Score: {g.score:<7} {g.distance}m traveled   │",
                "│  [N] New Run   [Esc] Exit    │",
                "└──────────────────────────────┘",
            ]
            self.query_one("#ski-field", Static).update("\n".join(lines))
        else:
            terrain = g.render_terrain()
            lane_width = 3
            border = "─" * (NUM_LANES * lane_width + 2)
            rows = ["┌" + border + "┐"]
            for row in terrain:
                cells_str = "".join(
                    f" {CELL_DISPLAY.get(cell, cell.value)} " for cell in row
                )
                rows.append(f"│{cells_str}│")
            rows.append("└" + border + "┘")
            self.query_one("#ski-field", Static).update("\n".join(rows))

        # Commentary
        bs = self.buddy_state
        comment = f"[dim]{bs.species.emoji} {bs.name}:[/dim] {self._last_comment}"
        self.query_one("#ski-commentary", Static).update(comment)

    def action_move_left(self):
        if self.game and self.game.alive:
            self.game.move_left()
            self._render()

    def action_move_right(self):
        if self.game and self.game.alive:
            self.game.move_right()
            self._render()

    def action_pause(self):
        self._paused = not self._paused

    def action_new_game(self):
        self._result = None
        self._start_game()

    def action_back(self):
        if self._timer:
            self._timer.stop()
        self.dismiss(self._result)
