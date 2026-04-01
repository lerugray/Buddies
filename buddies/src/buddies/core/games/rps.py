"""Rock-Paper-Scissors tournament engine.

The simplest game — proves the architecture works. Buddy AI decisions
are driven by personality stats: CHAOS = truly random (actually optimal),
WISDOM = pattern-tracking, DEBUGGING = counter-strategy, SNARK = psychological warfare.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state


class RPSChoice(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


# What beats what
BEATS = {
    RPSChoice.ROCK: RPSChoice.SCISSORS,
    RPSChoice.PAPER: RPSChoice.ROCK,
    RPSChoice.SCISSORS: RPSChoice.PAPER,
}

# What loses to what (inverse)
LOSES_TO = {v: k for k, v in BEATS.items()}

CHOICE_EMOJI = {
    RPSChoice.ROCK: "🪨",
    RPSChoice.PAPER: "📄",
    RPSChoice.SCISSORS: "✂️",
}


@dataclass
class RPSRound:
    """Result of a single RPS round."""
    round_num: int
    player_choice: RPSChoice
    buddy_choice: RPSChoice
    outcome: GameOutcome  # From the PLAYER's perspective

    @property
    def player_won(self) -> bool:
        return self.outcome == GameOutcome.WIN

    @property
    def buddy_won(self) -> bool:
        return self.outcome == GameOutcome.LOSE


def judge_round(player: RPSChoice, buddy: RPSChoice) -> GameOutcome:
    """Determine round outcome from the PLAYER's perspective."""
    if player == buddy:
        return GameOutcome.DRAW
    if BEATS[player] == buddy:
        return GameOutcome.WIN
    return GameOutcome.LOSE


@dataclass
class RPSGame:
    """A best-of-N Rock-Paper-Scissors tournament.

    The buddy AI picks throws based on personality:
    - High CHAOS: truly random (actually the optimal RPS strategy)
    - High WISDOM: tracks player patterns, counter-picks
    - High DEBUGGING: methodical counter-strategy
    - High SNARK: picks whatever lets them trash-talk best
    - High PATIENCE: tends to repeat the same throw (stubborn)
    """
    buddy_state: BuddyState
    best_of: int = 5
    rounds: list[RPSRound] = field(default_factory=list)
    player_wins: int = 0
    buddy_wins: int = 0
    draws: int = 0
    player_history: list[RPSChoice] = field(default_factory=list)
    buddy_history: list[RPSChoice] = field(default_factory=list)
    _personality: GamePersonality = field(init=False)
    _favorite_throw: RPSChoice = field(init=False)

    def __post_init__(self):
        self._personality = personality_from_state(self.buddy_state)
        # Each buddy has a "favorite" throw based on species name hash
        choices = list(RPSChoice)
        seed = sum(ord(c) for c in self.buddy_state.species.name)
        self._favorite_throw = choices[seed % 3]

    @property
    def wins_needed(self) -> int:
        return (self.best_of // 2) + 1

    @property
    def is_over(self) -> bool:
        return self.player_wins >= self.wins_needed or self.buddy_wins >= self.wins_needed

    @property
    def round_num(self) -> int:
        return len(self.rounds) + 1

    @property
    def winner(self) -> str | None:
        """'player', 'buddy', or None if not over."""
        if self.player_wins >= self.wins_needed:
            return "player"
        if self.buddy_wins >= self.wins_needed:
            return "buddy"
        return None

    def buddy_pick(self) -> RPSChoice:
        """AI picks a throw based on personality."""
        choices = list(RPSChoice)
        p = self._personality

        # Wild card: completely random (high CHAOS)
        if p.should_wild_card():
            return random.choice(choices)

        # Optimal play: try to counter player patterns (high WISDOM/DEBUGGING)
        if p.should_play_optimal() and len(self.player_history) >= 2:
            # Simple pattern: counter whatever player picked most recently
            last = self.player_history[-1]
            return LOSES_TO[last]

        # Aggressive: pick what beats the player's most common choice
        if p.should_be_aggressive() and self.player_history:
            from collections import Counter
            common = Counter(self.player_history).most_common(1)[0][0]
            return LOSES_TO[common]

        # Patient: stick with favorite throw (stubbornly consistent)
        if random.random() < p.patience_factor:
            return self._favorite_throw

        # Default: random
        return random.choice(choices)

    def play_round(self, player_choice: RPSChoice) -> RPSRound:
        """Play a round. Returns the round result."""
        buddy_choice = self.buddy_pick()
        outcome = judge_round(player_choice, buddy_choice)

        if outcome == GameOutcome.WIN:
            self.player_wins += 1
        elif outcome == GameOutcome.LOSE:
            self.buddy_wins += 1
        else:
            self.draws += 1

        self.player_history.append(player_choice)
        self.buddy_history.append(buddy_choice)

        rnd = RPSRound(
            round_num=len(self.rounds) + 1,
            player_choice=player_choice,
            buddy_choice=buddy_choice,
            outcome=outcome,
        )
        self.rounds.append(rnd)
        return rnd

    def get_result(self) -> GameResult:
        """Get the final game result (call after is_over)."""
        if self.winner == "player":
            outcome = GameOutcome.WIN
        elif self.winner == "buddy":
            outcome = GameOutcome.LOSE
        else:
            outcome = GameOutcome.DRAW

        return GameResult(
            game_type=GameType.RPS,
            outcome=outcome,
            buddy_id=self.buddy_state.buddy_id,
            score={
                "player_wins": self.player_wins,
                "buddy_wins": self.buddy_wins,
                "draws": self.draws,
                "rounds_played": len(self.rounds),
            },
        )

    def get_player_streak(self) -> int:
        """Current player win streak (consecutive wins from end)."""
        streak = 0
        for rnd in reversed(self.rounds):
            if rnd.outcome == GameOutcome.WIN:
                streak += 1
            else:
                break
        return streak

    def get_buddy_streak(self) -> int:
        """Current buddy win streak."""
        streak = 0
        for rnd in reversed(self.rounds):
            if rnd.outcome == GameOutcome.LOSE:
                streak += 1
            else:
                break
        return streak
