"""Buddy Relationships — buddies develop opinions about each other.

Relationships form based on:
- Stat compatibility (similar stats = friendship, opposite = rivalry)
- Shared activities (games played together, discussions)
- Idle life social events
- Time spent in the same party

Relationships affect discussions (allies agree more, rivals argue)
and can unlock special dialogue.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState


class RelationType:
    STRANGER = "stranger"       # 0-19: don't know each other
    ACQUAINTANCE = "acquaintance"  # 20-39: aware of each other
    FRIEND = "friend"           # 40-59: like each other
    BEST_FRIEND = "best_friend" # 60-79: close bond
    RIVAL = "rival"             # negative: competitive tension
    NEMESIS = "nemesis"         # very negative: active opposition


@dataclass
class Relationship:
    """A relationship between two buddies."""
    buddy_a_id: int
    buddy_b_id: int
    affinity: int = 0  # -100 to 100
    shared_games: int = 0
    shared_discussions: int = 0
    idle_interactions: int = 0

    @property
    def type(self) -> str:
        if self.affinity <= -50:
            return RelationType.NEMESIS
        elif self.affinity < 0:
            return RelationType.RIVAL
        elif self.affinity < 20:
            return RelationType.STRANGER
        elif self.affinity < 40:
            return RelationType.ACQUAINTANCE
        elif self.affinity < 60:
            return RelationType.FRIEND
        else:
            return RelationType.BEST_FRIEND

    @property
    def label(self) -> str:
        """Human-readable relationship label."""
        return {
            RelationType.STRANGER: "Strangers",
            RelationType.ACQUAINTANCE: "Acquaintances",
            RelationType.FRIEND: "Friends",
            RelationType.BEST_FRIEND: "Best Friends",
            RelationType.RIVAL: "Rivals",
            RelationType.NEMESIS: "Nemeses",
        }[self.type]

    @property
    def emoji(self) -> str:
        return {
            RelationType.STRANGER: "❓",
            RelationType.ACQUAINTANCE: "👋",
            RelationType.FRIEND: "😊",
            RelationType.BEST_FRIEND: "💕",
            RelationType.RIVAL: "⚡",
            RelationType.NEMESIS: "🔥",
        }[self.type]


def compute_stat_compatibility(a: BuddyState, b: BuddyState) -> int:
    """How compatible are two buddies based on their stats?

    Similar stat distributions = positive (friendship)
    Opposite stat distributions = negative (rivalry)
    Returns -20 to +20.
    """
    diff = 0
    for stat in ("debugging", "chaos", "snark", "wisdom", "patience"):
        diff += abs(a.stats.get(stat, 10) - b.stats.get(stat, 10))

    # Average difference per stat
    avg_diff = diff / 5.0

    if avg_diff < 5:
        return 15  # Very similar — strong bond
    elif avg_diff < 8:
        return 8   # Somewhat similar
    elif avg_diff < 12:
        return 0   # Neutral
    elif avg_diff < 18:
        return -5  # Different enough to clash
    else:
        return -12 # Very different — rivalry material


class RelationshipManager:
    """Tracks and updates relationships between all buddies."""

    def __init__(self):
        self._relationships: dict[tuple[int, int], Relationship] = {}

    def _key(self, a_id: int, b_id: int) -> tuple[int, int]:
        """Canonical key — smaller ID first."""
        return (min(a_id, b_id), max(a_id, b_id))

    def get(self, a_id: int, b_id: int) -> Relationship:
        """Get or create a relationship between two buddies."""
        if a_id == b_id:
            # Self-relationship (shouldn't happen but handle gracefully)
            return Relationship(a_id, b_id, affinity=100)
        key = self._key(a_id, b_id)
        if key not in self._relationships:
            self._relationships[key] = Relationship(key[0], key[1])
        return self._relationships[key]

    def on_shared_game(self, a_id: int, b_id: int, both_won: bool = False):
        """Called when two buddies play a game together."""
        if a_id == b_id:
            return
        rel = self.get(a_id, b_id)
        rel.shared_games += 1
        # Games together generally build affinity
        rel.affinity = max(-100, min(100, rel.affinity + 3))
        if both_won:
            rel.affinity = max(-100, min(100, rel.affinity + 2))

    def on_shared_discussion(self, a_id: int, b_id: int):
        """Called when two buddies participate in a discussion together."""
        if a_id == b_id:
            return
        rel = self.get(a_id, b_id)
        rel.shared_discussions += 1
        rel.affinity = max(-100, min(100, rel.affinity + 2))

    def on_idle_interaction(self, a_id: int, b_id: int, positive: bool = True):
        """Called when buddies interact during idle time."""
        if a_id == b_id:
            return
        rel = self.get(a_id, b_id)
        rel.idle_interactions += 1
        delta = 2 if positive else -3
        rel.affinity = max(-100, min(100, rel.affinity + delta))

    def initialize_from_stats(self, buddies: list[BuddyState]):
        """Initialize base affinity from stat compatibility for all pairs."""
        for i, a in enumerate(buddies):
            for b in buddies[i + 1:]:
                key = self._key(a.buddy_id, b.buddy_id)
                if key not in self._relationships:
                    compat = compute_stat_compatibility(a, b)
                    self._relationships[key] = Relationship(
                        key[0], key[1], affinity=compat,
                    )

    def get_all_for_buddy(self, buddy_id: int) -> list[tuple[int, Relationship]]:
        """Get all relationships for a specific buddy.

        Returns list of (other_buddy_id, relationship).
        """
        results = []
        for (a, b), rel in self._relationships.items():
            if a == buddy_id:
                results.append((b, rel))
            elif b == buddy_id:
                results.append((a, rel))
        return results

    def get_discussion_modifier(self, a_id: int, b_id: int) -> float:
        """Get a modifier for how buddy A reacts to buddy B in discussions.

        Friends agree more (positive modifier), rivals disagree more (negative).
        Returns -0.5 to +0.5.
        """
        if a_id == b_id:
            return 0.0
        rel = self.get(a_id, b_id)
        return rel.affinity / 200.0  # Maps -100..100 to -0.5..0.5

    def summary(self, buddies: dict[int, BuddyState]) -> str:
        """Generate a summary of all relationships."""
        if not self._relationships:
            return "No relationships formed yet."

        lines = ["[bold]Buddy Relationships:[/bold]", ""]
        for (a_id, b_id), rel in sorted(self._relationships.items()):
            a_name = buddies.get(a_id)
            b_name = buddies.get(b_id)
            if not a_name or not b_name:
                continue
            a_label = f"{a_name.species.emoji} {a_name.name}"
            b_label = f"{b_name.species.emoji} {b_name.name}"
            lines.append(
                f"  {a_label} {rel.emoji} {b_label} — "
                f"{rel.label} ({rel.affinity:+d})"
            )

        return "\n".join(lines)
