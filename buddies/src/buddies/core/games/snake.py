"""Buffer Overflow — Snake game engine for Buddies Arcade.

StackHaven-themed snake: you're a memory pointer eating data packets.
Power-ups, obstacles, and personality-driven buddy commentary.

Personality effects:
  CHAOS     → more random obstacle spawns, power-ups relocate often
  DEBUGGING → obstacles in grid-aligned patterns, more garbage collectors
  PATIENCE  → slower initial speed ramp, longer multiplier windows
  WISDOM    → occasional hint arrow toward nearest multiplier zone
  SNARK     → death commentary and milestone trash talk
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import personality_from_state


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_W = 38   # Grid width (cells)
GRID_H = 18   # Grid height (cells)
BASE_TICK_INTERVAL = 0.14   # Seconds per game tick (base speed)
SPEED_RAMP_INTERVAL = 8     # Seconds between speed increases
SPEED_RAMP_AMOUNT = 0.008   # Seconds shaved off interval per ramp
MIN_TICK_INTERVAL = 0.05    # Fastest possible tick

PACKET_SCORE = 10           # Points per data packet eaten
MULTIPLIER_BONUS = 10       # Extra points per packet while multiplier active
MULTIPLIER_DURATION = 40    # Ticks multiplier lasts
SPEEDBOOST_DURATION = 15    # Ticks speed boost lasts
OBSTACLE_START_LENGTH = 6   # Snake length before obstacles appear


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class CellType(Enum):
    EMPTY = "."
    PACKET = "●"        # Normal food
    SPEEDBOOST = "⚡"   # Temporary speed boost
    MULTIPLIER = "★"    # Score multiplier zone
    MEMORYLEAK = "☠"    # Poison: adds dead length
    GARBAGE = "🧹"      # Removes 3 tail segments


@dataclass
class SnakeCell:
    x: int
    y: int

    def __eq__(self, other):
        return isinstance(other, SnakeCell) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


@dataclass
class PowerUp:
    x: int
    y: int
    cell_type: CellType
    ticks_remaining: int = 30   # Disappears if not collected


@dataclass
class Obstacle:
    x: int
    y: int


@dataclass
class SnakeGame:
    """Core game engine for Buffer Overflow (Snake)."""

    buddy_state: BuddyState
    high_score: int = 0

    # Snake state
    body: deque = field(default_factory=deque)
    direction: Direction = Direction.RIGHT
    _next_direction: Direction = field(default=Direction.RIGHT)
    alive: bool = True
    score: int = 0
    ticks: int = 0
    elapsed_seconds: float = 0.0

    # Food and items
    packet: SnakeCell | None = None
    powerups: list[PowerUp] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)

    # Active effects
    multiplier_ticks: int = 0
    speedboost_ticks: int = 0

    # Dead segments from memory leaks (position, ticks to decay)
    dead_segments: list[tuple[int, int]] = field(default_factory=list)

    # Personality-driven parameters (set in __post_init__)
    _chaos: float = 0.0
    _debugging: float = 0.0
    _patience: float = 0.0
    _wisdom: float = 0.0

    def __post_init__(self):
        p = personality_from_state(self.buddy_state)
        self._chaos = p.aggression          # chaos proxy
        self._debugging = p.optimal_play   # debugging proxy
        self._patience = p.patience_factor
        self._wisdom = (self.buddy_state.stats.get("wisdom", 10) / 50.0)

        # Start snake in center, length 3, heading right
        cx, cy = GRID_W // 2, GRID_H // 2
        self.body = deque([
            SnakeCell(cx, cy),
            SnakeCell(cx - 1, cy),
            SnakeCell(cx - 2, cy),
        ])
        self._next_direction = Direction.RIGHT
        self.direction = Direction.RIGHT
        self._spawn_packet()

    # ------------------------------------------------------------------
    # Tick (called by TUI timer)
    # ------------------------------------------------------------------

    def tick(self, delta_seconds: float = 0.0) -> list[str]:
        """Advance game state by one tick. Returns list of event strings."""
        if not self.alive:
            return []

        self.ticks += 1
        self.elapsed_seconds += delta_seconds
        events: list[str] = []

        # Apply direction (prevent 180-degree reversal)
        nd = self._next_direction
        cur = self.direction
        opposite = {
            Direction.UP: Direction.DOWN, Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT, Direction.RIGHT: Direction.LEFT,
        }
        if nd != opposite.get(cur):
            self.direction = nd

        # Move snake
        head = self.body[0]
        dx, dy = self.direction.value
        new_head = SnakeCell(head.x + dx, head.y + dy)

        # Wall collision
        if not (0 <= new_head.x < GRID_W and 0 <= new_head.y < GRID_H):
            self.alive = False
            events.append("wall")
            return events

        # Self collision
        if new_head in set(self.body):
            self.alive = False
            events.append("self")
            return events

        # Obstacle collision
        obs_positions = {(o.x, o.y) for o in self.obstacles}
        if (new_head.x, new_head.y) in obs_positions:
            self.alive = False
            events.append("obstacle")
            return events

        self.body.appendleft(new_head)

        # Check food/powerup collection
        ate_food = False
        if self.packet and new_head.x == self.packet.x and new_head.y == self.packet.y:
            pts = PACKET_SCORE
            if self.multiplier_ticks > 0:
                pts += MULTIPLIER_BONUS
            self.score += pts
            ate_food = True
            self._spawn_packet()
            events.append("eat")
            self._maybe_spawn_powerup()
            self._maybe_spawn_obstacle()

        # Check powerup collection
        for pw in list(self.powerups):
            if pw.x == new_head.x and pw.y == new_head.y:
                events.append(f"powerup:{pw.cell_type.value}")
                self._apply_powerup(pw)
                self.powerups.remove(pw)
                break

        # Shrink tail unless we ate food
        if not ate_food:
            self.body.pop()

        # Tick active effects
        if self.multiplier_ticks > 0:
            self.multiplier_ticks -= 1
        if self.speedboost_ticks > 0:
            self.speedboost_ticks -= 1

        # Age powerups out
        for pw in list(self.powerups):
            pw.ticks_remaining -= 1
            if pw.ticks_remaining <= 0:
                self.powerups.remove(pw)

        # Decay dead segments
        self.dead_segments = [(x, y) for x, y in self.dead_segments]  # just keep them for now

        # Wisdom hint: occasionally announce direction to nearest multiplier
        if self._wisdom > 0.6 and self.ticks % 30 == 0:
            mult = next((pw for pw in self.powerups if pw.cell_type == CellType.MULTIPLIER), None)
            if mult:
                events.append("wisdom_hint")

        return events

    def set_direction(self, direction: Direction):
        self._next_direction = direction

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _occupied_cells(self) -> set[tuple[int, int]]:
        occupied = {(c.x, c.y) for c in self.body}
        occupied |= {(pw.x, pw.y) for pw in self.powerups}
        occupied |= {(o.x, o.y) for o in self.obstacles}
        if self.packet:
            occupied.add((self.packet.x, self.packet.y))
        return occupied

    def _random_empty_cell(self) -> SnakeCell | None:
        occupied = self._occupied_cells()
        candidates = [
            (x, y) for x in range(GRID_W) for y in range(GRID_H)
            if (x, y) not in occupied
        ]
        if not candidates:
            return None
        x, y = random.choice(candidates)
        return SnakeCell(x, y)

    def _spawn_packet(self):
        cell = self._random_empty_cell()
        self.packet = cell

    def _maybe_spawn_powerup(self):
        """Spawn a powerup with personality-driven probability."""
        if len(self.powerups) >= 2:
            return

        # More frequent powerups with chaos
        base_chance = 0.3 + self._chaos * 0.2
        if random.random() > base_chance:
            return

        cell = self._random_empty_cell()
        if not cell:
            return

        # DEBUGGING buddies spawn more garbage collectors
        if self._debugging > 0.6 and random.random() < 0.4:
            pw_type = CellType.GARBAGE
        else:
            weights = {
                CellType.SPEEDBOOST: 25,
                CellType.MULTIPLIER: 20,
                CellType.MEMORYLEAK: 15 + int(self._chaos * 20),
                CellType.GARBAGE: 20 + int(self._debugging * 20),
            }
            pw_type = random.choices(list(weights.keys()), weights=list(weights.values()))[0]

        # PATIENCE buddies get longer multiplier windows
        duration = MULTIPLIER_DURATION
        if self._patience > 0.5 and pw_type == CellType.MULTIPLIER:
            duration = int(MULTIPLIER_DURATION * 1.5)

        # CHAOS: powerups disappear faster
        lifetime = 30 if self._chaos < 0.5 else random.randint(15, 30)

        self.powerups.append(PowerUp(
            x=cell.x, y=cell.y,
            cell_type=pw_type,
            ticks_remaining=lifetime,
        ))

    def _maybe_spawn_obstacle(self):
        """Spawn firewall obstacles as snake grows."""
        if len(self.body) < OBSTACLE_START_LENGTH:
            return

        # One obstacle chance per food eaten, more with chaos
        obstacle_chance = 0.2 + self._chaos * 0.3
        if random.random() > obstacle_chance:
            return

        if len(self.obstacles) >= 12:  # Cap
            return

        cell = self._random_empty_cell()
        if not cell:
            return

        # DEBUGGING: obstacles cluster in grid patterns
        if self._debugging > 0.6:
            # Snap to even coordinates for predictable layout
            cell.x = (cell.x // 2) * 2
            cell.y = (cell.y // 2) * 2
            # Check it's still empty after snapping
            if (cell.x, cell.y) in self._occupied_cells():
                return

        self.obstacles.append(Obstacle(x=cell.x, y=cell.y))

    def _apply_powerup(self, pw: PowerUp):
        if pw.cell_type == CellType.SPEEDBOOST:
            self.speedboost_ticks = SPEEDBOOST_DURATION
        elif pw.cell_type == CellType.MULTIPLIER:
            self.multiplier_ticks = MULTIPLIER_DURATION
        elif pw.cell_type == CellType.MEMORYLEAK:
            # Add 3 dead tail segments (extend without scoring)
            tail = list(self.body)[-1] if self.body else SnakeCell(0, 0)
            for _ in range(3):
                self.body.append(SnakeCell(tail.x, tail.y))
        elif pw.cell_type == CellType.GARBAGE:
            # Remove up to 3 tail segments
            for _ in range(3):
                if len(self.body) > 1:
                    self.body.pop()

    # ------------------------------------------------------------------
    # Speed
    # ------------------------------------------------------------------

    @property
    def current_tick_interval(self) -> float:
        """Seconds per tick — decreases over time."""
        # PATIENCE buddies get slower speed ramp
        ramp_factor = 1.0 if self._patience < 0.4 else 0.7
        ramps = int(self.elapsed_seconds / SPEED_RAMP_INTERVAL)
        interval = BASE_TICK_INTERVAL - (ramps * SPEED_RAMP_AMOUNT * ramp_factor)
        interval = max(interval, MIN_TICK_INTERVAL)

        # Speed boost cuts interval in half (risky!)
        if self.speedboost_ticks > 0:
            interval = max(interval * 0.5, MIN_TICK_INTERVAL)

        return interval

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def render_grid(self) -> list[str]:
        """Return list of strings, one per row, representing the grid."""
        grid = [["." for _ in range(GRID_W)] for _ in range(GRID_H)]

        # Place food
        if self.packet:
            grid[self.packet.y][self.packet.x] = "●"

        # Place powerups
        for pw in self.powerups:
            grid[pw.y][pw.x] = pw.cell_type.value

        # Place obstacles
        for obs in self.obstacles:
            if 0 <= obs.y < GRID_H and 0 <= obs.x < GRID_W:
                grid[obs.y][obs.x] = "█"

        # Place snake body
        body_list = list(self.body)
        for i, cell in enumerate(body_list):
            if 0 <= cell.y < GRID_H and 0 <= cell.x < GRID_W:
                if i == 0:
                    # Head — direction arrow
                    arrow = {
                        Direction.UP: "▲", Direction.DOWN: "▼",
                        Direction.LEFT: "◄", Direction.RIGHT: "►",
                    }[self.direction]
                    grid[cell.y][cell.x] = arrow
                else:
                    grid[cell.y][cell.x] = "█"

        return ["".join(row) for row in grid]

    @property
    def length(self) -> int:
        return len(self.body)

    @property
    def is_over(self) -> bool:
        return not self.alive

    def get_result(self) -> GameResult:
        outcome = GameOutcome.WIN if self.score > self.high_score else GameOutcome.LOSE
        return GameResult(
            game_type=GameType.SNAKE,
            outcome=outcome,
            buddy_id=self.buddy_state.buddy_id,
            score={"score": self.score, "length": self.length, "high_score": self.high_score},
            xp_earned=max(5, self.score // 10),
            turns=self.ticks,
        )
