"""Game engine foundation — stat-to-behavior mapping and base game class.

Every buddy's 5 stats (DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE) blend
into a GamePersonality that drives AI decisions across all game types.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from buddies.core.buddy_brain import BuddyState


@dataclass
class GamePersonality:
    """Derived from BuddyState stats for game AI decisions.

    All values are 0.0-1.0 floats representing probabilities/weights.
    A high-CHAOS buddy bluffs constantly; a high-WISDOM buddy plays optimally.
    Blended from all 5 stats, not just the dominant one.
    """
    bluff_chance: float       # chaos-driven — probability of deceptive play
    optimal_play: float       # debugging + wisdom — probability of picking the "correct" move
    aggression: float         # chaos + snark — tendency toward bold/risky plays
    patience_factor: float    # patience — willingness to wait for better opportunities
    trash_talk_chance: float  # snark — probability of commentary between moves
    wild_card_chance: float   # chaos * (1 - debugging) — truly random action
    name: str = ""            # buddy name for prose

    def should_bluff(self) -> bool:
        return random.random() < self.bluff_chance

    def should_play_optimal(self) -> bool:
        return random.random() < self.optimal_play

    def should_be_aggressive(self) -> bool:
        return random.random() < self.aggression

    def should_trash_talk(self) -> bool:
        return random.random() < self.trash_talk_chance

    def should_wild_card(self) -> bool:
        return random.random() < self.wild_card_chance


def personality_from_state(state: BuddyState) -> GamePersonality:
    """Derive a GamePersonality from a buddy's current stats.

    Stats range roughly 1-50+, normalized to 0-1 range (capped at 50).
    """
    s = state.stats
    cap = 50.0  # Normalize against this ceiling

    debugging = min(s.get("debugging", 10) / cap, 1.0)
    chaos = min(s.get("chaos", 10) / cap, 1.0)
    snark = min(s.get("snark", 10) / cap, 1.0)
    wisdom = min(s.get("wisdom", 10) / cap, 1.0)
    patience = min(s.get("patience", 10) / cap, 1.0)

    return GamePersonality(
        bluff_chance=chaos * 0.6,
        optimal_play=min((debugging + wisdom) * 0.4, 0.95),
        aggression=min((chaos + snark) * 0.35, 0.9),
        patience_factor=patience * 0.7,
        trash_talk_chance=snark * 0.5,
        wild_card_chance=chaos * (1.0 - debugging) * 0.3,
        name=state.name,
    )
