"""Pong game engine — real-time ball physics and AI paddle control.

The buddy controls the right paddle. Its personality stats influence
how it plays: high-PATIENCE tracks perfectly, high-CHAOS overshoots wildly,
high-DEBUGGING predicts ball trajectory, high-SNARK taunts on scores.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIELD_WIDTH = 60    # Internal game field width (columns)
FIELD_HEIGHT = 20   # Internal game field height (rows)
PADDLE_HEIGHT = 4   # Paddle size in rows
BALL_SPEED_X = 1.0  # Horizontal speed per tick
BALL_SPEED_Y = 0.6  # Vertical speed per tick
WINNING_SCORE = 5   # First to this wins
AI_REACTION_DELAY = 3  # Ticks before AI starts reacting to new ball direction


@dataclass
class Paddle:
    """A paddle on the field."""
    x: float          # Fixed x position
    y: float          # Top of paddle (0 = top of field)
    height: int = PADDLE_HEIGHT
    speed: float = 1.2  # Max movement per tick

    @property
    def center(self) -> float:
        return self.y + self.height / 2

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def move_up(self, amount: float = 1.0):
        self.y = max(0, self.y - min(amount, self.speed))

    def move_down(self, field_height: int, amount: float = 1.0):
        self.y = min(field_height - self.height, self.y + min(amount, self.speed))

    def contains_y(self, y: float) -> bool:
        return self.top <= y <= self.bottom


@dataclass
class Ball:
    """The bouncing ball."""
    x: float
    y: float
    dx: float = BALL_SPEED_X   # Direction + speed on x axis
    dy: float = BALL_SPEED_Y   # Direction + speed on y axis

    def reset(self, field_width: int, field_height: int, serve_right: bool = True):
        """Reset ball to center, serve in a direction."""
        self.x = field_width / 2
        self.y = field_height / 2
        angle = random.uniform(-0.8, 0.8)
        self.dx = BALL_SPEED_X if serve_right else -BALL_SPEED_X
        self.dy = BALL_SPEED_Y * angle


@dataclass
class PongGame:
    """Full pong game state."""
    buddy_state: BuddyState
    personality: GamePersonality = field(init=False)
    field_width: int = FIELD_WIDTH
    field_height: int = FIELD_HEIGHT

    # Game objects
    player_paddle: Paddle = field(init=False)
    buddy_paddle: Paddle = field(init=False)
    ball: Ball = field(init=False)

    # Score
    player_score: int = 0
    buddy_score: int = 0
    winning_score: int = WINNING_SCORE

    # AI state
    _ai_target_y: float = 0.0
    _ai_reaction_ticks: int = 0
    _ai_error: float = 0.0  # Intentional aim offset from personality

    # Game state
    is_over: bool = False
    is_paused: bool = False
    ticks: int = 0
    last_scorer: str = ""  # "player" or "buddy"
    rally_length: int = 0
    max_rally: int = 0

    def __post_init__(self):
        self.personality = personality_from_state(self.buddy_state)

        # Player on left (x=1), buddy on right (x=field_width-2)
        mid_y = (self.field_height - PADDLE_HEIGHT) / 2
        self.player_paddle = Paddle(x=1, y=mid_y)
        self.buddy_paddle = Paddle(x=self.field_width - 2, y=mid_y)

        self.ball = Ball(x=self.field_width / 2, y=self.field_height / 2)
        self._serve(serve_right=True)

    def _serve(self, serve_right: bool):
        """Serve the ball from center."""
        self.ball.reset(self.field_width, self.field_height, serve_right)
        self._ai_reaction_ticks = AI_REACTION_DELAY
        self._ai_error = self._calc_ai_error()
        self.rally_length = 0

    def _calc_ai_error(self) -> float:
        """Calculate how much the AI should miss by, based on personality.

        High patience = precise tracking
        High chaos = big random offsets
        High debugging = good prediction
        """
        base_error = random.uniform(-2.0, 2.0)

        # Patience reduces error
        patience_factor = 1.0 - self.personality.patience_factor
        # Chaos increases error
        chaos_bonus = self.personality.bluff_chance * random.uniform(-3.0, 3.0)
        # Debugging reduces error
        debug_reduction = self.personality.optimal_play * 0.5

        error = base_error * patience_factor + chaos_bonus
        error *= (1.0 - debug_reduction)

        return error

    def tick(self):
        """Advance one game tick. Call this ~20 times per second."""
        if self.is_over or self.is_paused:
            return

        self.ticks += 1

        # Move ball
        self.ball.x += self.ball.dx
        self.ball.y += self.ball.dy

        # Bounce off top/bottom walls
        if self.ball.y <= 0:
            self.ball.y = abs(self.ball.y)
            self.ball.dy = abs(self.ball.dy)
        elif self.ball.y >= self.field_height - 1:
            self.ball.y = 2 * (self.field_height - 1) - self.ball.y
            self.ball.dy = -abs(self.ball.dy)

        # Check paddle collisions
        self._check_paddle_hit(self.player_paddle, going_left=True)
        self._check_paddle_hit(self.buddy_paddle, going_left=False)

        # Check scoring (ball past paddles)
        if self.ball.x <= 0:
            # Buddy scores
            self.buddy_score += 1
            self.last_scorer = "buddy"
            self.max_rally = max(self.max_rally, self.rally_length)
            if self.buddy_score >= self.winning_score:
                self.is_over = True
            else:
                self._serve(serve_right=False)
        elif self.ball.x >= self.field_width - 1:
            # Player scores
            self.player_score += 1
            self.last_scorer = "player"
            self.max_rally = max(self.max_rally, self.rally_length)
            if self.player_score >= self.winning_score:
                self.is_over = True
            else:
                self._serve(serve_right=True)

        # AI paddle movement
        self._ai_tick()

    def _check_paddle_hit(self, paddle: Paddle, going_left: bool):
        """Check if ball hit a paddle and bounce it."""
        if going_left and self.ball.dx < 0:
            # Check left paddle
            if self.ball.x <= paddle.x + 1 and paddle.contains_y(self.ball.y):
                self.ball.dx = abs(self.ball.dx)
                # Add spin based on where ball hit paddle
                offset = (self.ball.y - paddle.center) / (paddle.height / 2)
                self.ball.dy += offset * 0.3
                # Clamp dy
                self.ball.dy = max(-1.2, min(1.2, self.ball.dy))
                self.ball.x = paddle.x + 1
                self.rally_length += 1
                # Speed up slightly each rally
                self.ball.dx = min(self.ball.dx * 1.02, 2.0)
        elif not going_left and self.ball.dx > 0:
            # Check right paddle (buddy)
            if self.ball.x >= paddle.x - 1 and paddle.contains_y(self.ball.y):
                self.ball.dx = -abs(self.ball.dx)
                offset = (self.ball.y - paddle.center) / (paddle.height / 2)
                self.ball.dy += offset * 0.3
                self.ball.dy = max(-1.2, min(1.2, self.ball.dy))
                self.ball.x = paddle.x - 1
                self.rally_length += 1
                self.ball.dx = max(self.ball.dx * 1.02, -2.0)

    def _ai_tick(self):
        """Move the buddy's paddle toward the ball (with personality quirks)."""
        # Reaction delay — simulate not-instant reflexes
        if self._ai_reaction_ticks > 0:
            self._ai_reaction_ticks -= 1
            return

        # Only react when ball is coming toward buddy
        if self.ball.dx > 0:
            # Predict where ball will arrive at paddle x
            if self.personality.should_play_optimal():
                # Good prediction — estimate y at paddle x
                ticks_to_arrive = (self.buddy_paddle.x - self.ball.x) / max(self.ball.dx, 0.1)
                predicted_y = self.ball.y + self.ball.dy * ticks_to_arrive
                # Bounce prediction (simple)
                while predicted_y < 0 or predicted_y >= self.field_height:
                    if predicted_y < 0:
                        predicted_y = -predicted_y
                    elif predicted_y >= self.field_height:
                        predicted_y = 2 * (self.field_height - 1) - predicted_y
                target_y = predicted_y + self._ai_error
            else:
                # Just track the ball's current y
                target_y = self.ball.y + self._ai_error
        else:
            # Ball going away — drift toward center
            target_y = self.field_height / 2

        # Move toward target
        diff = target_y - self.buddy_paddle.center
        move_speed = self.buddy_paddle.speed

        # Chaos: sometimes overshoot
        if self.personality.should_wild_card():
            move_speed *= random.uniform(1.5, 2.5)

        # Patience: smoother movement
        if self.personality.patience_factor > 0.5:
            move_speed *= 0.8  # Slower but steadier

        if diff > 0.5:
            self.buddy_paddle.move_down(self.field_height, min(abs(diff), move_speed))
        elif diff < -0.5:
            self.buddy_paddle.move_up(min(abs(diff), move_speed))

        # Occasionally recalculate error mid-rally for variety
        if self.ticks % 30 == 0:
            self._ai_error = self._calc_ai_error()

    def move_player_up(self):
        """Move player paddle up."""
        self.player_paddle.move_up(1.5)

    def move_player_down(self):
        """Move player paddle down."""
        self.player_paddle.move_down(self.field_height, 1.5)

    @property
    def winner(self) -> str | None:
        if not self.is_over:
            return None
        if self.player_score >= self.winning_score:
            return "player"
        return "buddy"

    def get_result(self) -> GameResult:
        """Build a GameResult from the completed game."""
        if self.winner == "player":
            outcome = GameOutcome.WIN
            xp = 20
            mood = 5
        else:
            outcome = GameOutcome.LOSE
            xp = 8
            mood = -2

        return GameResult(
            game_type=GameType.PONG,
            outcome=outcome,
            buddy_id=0,  # Filled in by caller
            score={"player": self.player_score, "buddy": self.buddy_score,
                   "max_rally": self.max_rally, "ticks": self.ticks},
            xp_earned=xp,
            mood_delta=mood,
        )

    def render_field(self) -> list[str]:
        """Render the game field as a list of strings (plain text, no markup).

        Each string is one row of the field. The caller adds Rich markup.
        """
        rows = []
        # Top border
        rows.append("╔" + "═" * self.field_width + "╗")

        for y in range(self.field_height):
            row_chars = [" "] * self.field_width

            # Center line (dashed)
            mid_x = self.field_width // 2
            if y % 2 == 0:
                row_chars[mid_x] = "│"

            # Player paddle (left)
            pp = self.player_paddle
            if pp.top <= y < pp.bottom:
                row_chars[int(pp.x)] = "█"

            # Buddy paddle (right)
            bp = self.buddy_paddle
            if bp.top <= y < bp.bottom:
                row_chars[int(bp.x)] = "█"

            # Ball
            ball_x = int(round(self.ball.x))
            ball_y = int(round(self.ball.y))
            if y == ball_y and 0 <= ball_x < self.field_width:
                row_chars[ball_x] = "●"

            rows.append("║" + "".join(row_chars) + "║")

        # Bottom border
        rows.append("╚" + "═" * self.field_width + "╝")

        return rows
