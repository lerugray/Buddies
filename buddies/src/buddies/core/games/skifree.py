"""Stack Descent — Ski Free game engine for Buddies Arcade.

Your buddy skis down a mountain of deprecated code.
Dodge legacy blocks, collect pickups, and outrun The Auditor.

Personality effects:
  CHAOS     → erratic obstacle placement, random surprise pickups
  DEBUGGING → cleaner lane patterns, obstacles more predictable
  PATIENCE  → slower initial scroll speed, more reaction time
  WISDOM    → brief safe-lane hint every 15 seconds
  SNARK     → escalating commentary, panic lines when Auditor appears
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import personality_from_state


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_LANES = 7
VISIBLE_ROWS = 16          # How many rows of terrain are visible
TERRAIN_BUFFER = 30        # How many rows ahead to pre-generate
BASE_SCROLL_SPEED = 0.12   # Seconds per terrain scroll tick
MIN_SCROLL_SPEED = 0.04    # Fastest scroll
SPEED_RAMP_INTERVAL = 10   # Seconds between speed increases
SPEED_RAMP_AMOUNT = 0.006  # Seconds shaved per ramp

AUDITOR_DISTANCE = 150     # Distance (ticks) before The Auditor appears (~15s at 10FPS)
AUDITOR_CATCH_SPEED = 2    # How many scroll ticks of lead the auditor closes per tick

COFFEE_SHIELD_TICKS = 20   # Ticks of immunity from coffee
DISTANCE_PER_TICK = 5      # Meters per scroll tick


class CellType(Enum):
    EMPTY = " "
    OBSTACLE_LEGACY = "█"    # Legacy code block
    OBSTACLE_BUG = "B"       # Bug report
    OBSTACLE_MERGE = "X"     # Merge conflict
    OBSTACLE_WALL = "▓"      # Firewall wall segment
    COFFEE = "☕"             # Shield pickup
    DUCK = "🦆"              # Rubber duck (+100 pts)
    COMMIT = "📦"            # Git commit (5s extra lead on Auditor)
    PLAYER = "🎿"
    AUDITOR = "👔"           # The Auditor (the yeti)


@dataclass
class TerrainRow:
    cells: list[CellType]   # NUM_LANES cells


@dataclass
class SkiFreeGame:
    """Core game engine for Stack Descent (Ski Free)."""

    buddy_state: BuddyState

    player_lane: int = 3         # 0-indexed, middle of 7
    alive: bool = True
    score: int = 0
    distance: int = 0            # Meters traveled
    ticks: int = 0
    elapsed_seconds: float = 0.0

    # Shield (coffee)
    shield_ticks: int = 0

    # Auditor
    auditor_active: bool = False
    auditor_lane: int = 3
    auditor_lead: int = AUDITOR_DISTANCE  # How far behind auditor is (in ticks)

    # Speed boost (from commit pickup)
    commit_boost_ticks: int = 0

    # Terrain
    terrain: list[TerrainRow] = field(default_factory=list)
    _gen_seed: int = field(default_factory=lambda: random.randint(0, 10000))
    _rng: random.Random = field(default_factory=random.Random)

    # Personality params
    _chaos: float = 0.0
    _debugging: float = 0.0
    _patience: float = 0.0
    _wisdom: float = 0.0
    _snark: float = 0.0

    def __post_init__(self):
        p = personality_from_state(self.buddy_state)
        self._chaos = p.aggression
        self._debugging = p.optimal_play
        self._patience = p.patience_factor
        self._wisdom = self.buddy_state.stats.get("wisdom", 10) / 50.0
        self._snark = self.buddy_state.stats.get("snark", 10) / 50.0
        self._rng.seed(self._gen_seed)
        self._generate_terrain(TERRAIN_BUFFER)

    # ------------------------------------------------------------------
    # Terrain generation
    # ------------------------------------------------------------------

    def _generate_terrain(self, num_rows: int):
        """Add num_rows of terrain ahead."""
        for _ in range(num_rows):
            row = self._generate_row(len(self.terrain))
            self.terrain.append(row)

    def _generate_row(self, row_idx: int) -> TerrainRow:
        """Generate a single terrain row with personality-adjusted density."""
        cells = [CellType.EMPTY] * NUM_LANES

        # First rows are clear — enough to cover the player's starting position
        if row_idx < VISIBLE_ROWS:
            return TerrainRow(cells=cells)

        # Obstacle density scales with distance
        base_density = min(0.12 + (self.distance / 10000) * 0.15, 0.35)

        # DEBUGGING → obstacles in cleaner column patterns
        # CHAOS → random placement anywhere
        for lane in range(NUM_LANES):
            if self._rng.random() > base_density:
                continue

            # DEBUGGING: obstacles cluster in specific lanes (columns 1,3,5)
            if self._debugging > 0.6:
                if lane not in [1, 3, 5]:
                    if self._rng.random() > 0.3:
                        continue

            obstacle_weights = {
                CellType.OBSTACLE_LEGACY: 40,
                CellType.OBSTACLE_BUG: 25,
                CellType.OBSTACLE_MERGE: 20,
                CellType.OBSTACLE_WALL: 15 + int(self._chaos * 20),
            }
            cells[lane] = self._rng.choices(
                list(obstacle_weights.keys()),
                weights=list(obstacle_weights.values()),
            )[0]

        # Don't block all lanes — ensure at least one path
        non_walls = [i for i, c in enumerate(cells) if c == CellType.EMPTY]
        if not non_walls:
            clear_lane = self._rng.randint(0, NUM_LANES - 1)
            cells[clear_lane] = CellType.EMPTY

        # Spawn pickups (after clearing)
        if not any(c != CellType.EMPTY for c in cells):
            pickup_chance = 0.08 + self._chaos * 0.05
            if self._rng.random() < pickup_chance:
                empty_lanes = [i for i, c in enumerate(cells) if c == CellType.EMPTY]
                if empty_lanes:
                    lane = self._rng.choice(empty_lanes)
                    pickup_weights = {
                        CellType.COFFEE: 40,
                        CellType.DUCK: 35,
                        CellType.COMMIT: 25,
                    }
                    cells[lane] = self._rng.choices(
                        list(pickup_weights.keys()),
                        weights=list(pickup_weights.values()),
                    )[0]

        return TerrainRow(cells=cells)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_seconds: float = 0.0) -> list[str]:
        """Advance one scroll tick. Returns event list."""
        if not self.alive:
            return []

        self.ticks += 1
        self.elapsed_seconds += delta_seconds
        events: list[str] = []

        # Scroll terrain (remove top row, add new row at bottom)
        if self.terrain:
            # Player is always at row VISIBLE_ROWS - 2 (near bottom)
            player_row_idx = VISIBLE_ROWS - 2
            if len(self.terrain) > player_row_idx:
                player_row = self.terrain[player_row_idx]
                cell = player_row.cells[self.player_lane]

                # Check collision
                if cell in (CellType.OBSTACLE_LEGACY, CellType.OBSTACLE_BUG,
                            CellType.OBSTACLE_MERGE, CellType.OBSTACLE_WALL):
                    if self.shield_ticks > 0:
                        events.append("shield_hit")
                        self.shield_ticks -= 1
                    else:
                        self.alive = False
                        events.append("crash")
                        return events

                # Check pickup
                elif cell == CellType.COFFEE:
                    self.shield_ticks = COFFEE_SHIELD_TICKS
                    player_row.cells[self.player_lane] = CellType.EMPTY
                    events.append("pickup:coffee")
                elif cell == CellType.DUCK:
                    self.score += 100
                    player_row.cells[self.player_lane] = CellType.EMPTY
                    events.append("pickup:duck")
                elif cell == CellType.COMMIT:
                    self.auditor_lead = min(self.auditor_lead + 50, AUDITOR_DISTANCE)
                    player_row.cells[self.player_lane] = CellType.EMPTY
                    events.append("pickup:commit")

            # Scroll: remove oldest visible row
            self.terrain.pop(0)

        # Add new row
        self._generate_terrain(1)

        # Tick effects
        if self.shield_ticks > 0:
            self.shield_ticks -= 1

        # Score and distance
        self.score += 5
        self.distance += DISTANCE_PER_TICK

        # Auditor logic — appears after AUDITOR_DISTANCE ticks
        if self.ticks >= AUDITOR_DISTANCE:
            if not self.auditor_active:
                self.auditor_active = True
                events.append("auditor_appears")
            else:
                # Close the gap
                self.auditor_lead -= AUDITOR_CATCH_SPEED
                if self.auditor_lead <= 0:
                    self.alive = False
                    events.append("caught")
                    return events

                # Auditor moves toward player lane
                if self.ticks % 3 == 0:
                    if self.auditor_lane < self.player_lane:
                        self.auditor_lane += 1
                    elif self.auditor_lane > self.player_lane:
                        self.auditor_lane -= 1

        return events

    def move_left(self):
        if self.player_lane > 0:
            self.player_lane -= 1

    def move_right(self):
        if self.player_lane < NUM_LANES - 1:
            self.player_lane += 1

    # ------------------------------------------------------------------
    # Speed
    # ------------------------------------------------------------------

    @property
    def current_tick_interval(self) -> float:
        ramp_factor = 1.0 if self._patience < 0.4 else 0.75
        ramps = int(self.elapsed_seconds / SPEED_RAMP_INTERVAL)
        interval = BASE_SCROLL_SPEED - (ramps * SPEED_RAMP_AMOUNT * ramp_factor)
        return max(interval, MIN_SCROLL_SPEED)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def render_terrain(self) -> list[list[CellType]]:
        """Return the visible terrain rows (VISIBLE_ROWS)."""
        visible = self.terrain[:VISIBLE_ROWS]
        # Pad if needed
        while len(visible) < VISIBLE_ROWS:
            visible.append(TerrainRow(cells=[CellType.EMPTY] * NUM_LANES))

        # Place player
        player_row = VISIBLE_ROWS - 2
        row = list(visible[player_row].cells)
        row[self.player_lane] = CellType.PLAYER
        visible[player_row] = TerrainRow(cells=row)

        # Place auditor (2 rows behind player)
        if self.auditor_active and self.auditor_lead < 60:
            auditor_row_idx = player_row + 2
            if auditor_row_idx < VISIBLE_ROWS:
                row = list(visible[auditor_row_idx].cells)
                row[self.auditor_lane] = CellType.AUDITOR
                visible[auditor_row_idx] = TerrainRow(cells=row)

        return [r.cells for r in visible]

    @property
    def is_over(self) -> bool:
        return not self.alive

    @property
    def auditor_warning(self) -> bool:
        return self.auditor_active and self.auditor_lead < 80

    def get_result(self) -> GameResult:
        outcome = GameOutcome.WIN if self.distance > 3000 else GameOutcome.LOSE
        return GameResult(
            game_type=GameType.SKIFREE,
            outcome=outcome,
            buddy_id=self.buddy_state.buddy_id,
            score={"score": self.score, "distance": self.distance},
            xp_earned=max(5, self.score // 20),
            turns=self.ticks,
        )
