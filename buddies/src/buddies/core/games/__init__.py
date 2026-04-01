"""Games Arcade — card games, battles, trivia, and arcade games.

Buddy stats drive AI playstyle across all game types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GameType(Enum):
    RPS = "rps"
    BLACKJACK = "blackjack"
    HOLDEM = "holdem"
    WHIST = "whist"
    BATTLE = "battle"
    TRIVIA = "trivia"
    PONG = "pong"
    DUNGEON = "dungeon"
    CRAWL = "crawl"
    MUD = "mud"


class GameOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"


@dataclass
class GameResult:
    """Result of a completed game."""
    game_type: GameType
    outcome: GameOutcome
    buddy_id: int
    score: dict = field(default_factory=dict)
    xp_earned: int = 0
    mood_delta: int = 0

    @property
    def xp_for_outcome(self) -> int:
        """Default XP by outcome — can be overridden by specific games."""
        if self.xp_earned:
            return self.xp_earned
        return {GameOutcome.WIN: 15, GameOutcome.LOSE: 5, GameOutcome.DRAW: 10}[self.outcome]

    @property
    def mood_for_outcome(self) -> int:
        """Default mood delta by outcome."""
        if self.mood_delta:
            return self.mood_delta
        return {GameOutcome.WIN: 5, GameOutcome.LOSE: -2, GameOutcome.DRAW: 0}[self.outcome]
