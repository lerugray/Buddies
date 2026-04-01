"""User Character — derive a playable character from the user's behavior.

Stats are built from session tool usage, game history, chat patterns,
and general activity. The user joins the dungeon party as a real
character with a class, HP, and abilities — shaped by how they
actually use the software.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from buddies.core.buddy_brain import BuddyState, Species, Rarity


@dataclass
class UserStats:
    """Derived stats for the user character."""
    debugging: int = 10
    chaos: int = 10
    snark: int = 10
    wisdom: int = 10
    patience: int = 10

    @property
    def as_dict(self) -> dict[str, int]:
        return {
            "debugging": self.debugging,
            "chaos": self.chaos,
            "snark": self.snark,
            "wisdom": self.wisdom,
            "patience": self.patience,
        }

    @property
    def dominant(self) -> str:
        d = self.as_dict
        return max(d, key=d.get)

    @property
    def total(self) -> int:
        return sum(self.as_dict.values())


def derive_user_stats(
    tool_counts: Counter | dict | None = None,
    messages_sent: int = 0,
    games_played: int = 0,
    games_won: int = 0,
    game_types_played: dict | None = None,
    edit_count: int = 0,
    files_touched: int = 0,
    event_count: int = 0,
    discussions_started: int = 0,
) -> UserStats:
    """Derive user stats from their actual behavior.

    The more they've done, the higher their stats. Specific activities
    boost specific stats.
    """
    stats = UserStats()
    tc = dict(tool_counts or {})

    # --- DEBUGGING: code editing, reading, grepping ---
    edits = tc.get("Edit", 0) + tc.get("Write", 0)
    reads = tc.get("Read", 0) + tc.get("Grep", 0) + tc.get("Glob", 0)
    stats.debugging += min(30, edits // 2 + reads // 3)

    # --- WISDOM: agent spawns, research, discussions ---
    agents = tc.get("Agent", 0)
    stats.wisdom += min(25, agents * 2 + discussions_started * 3 + reads // 5)

    # --- CHAOS: bash commands, frequent tool switching, game variety ---
    bash = tc.get("Bash", 0)
    game_variety = len(game_types_played or {})
    stats.chaos += min(25, bash // 2 + game_variety * 3)

    # --- PATIENCE: chat messages, session length, files touched ---
    stats.patience += min(25, messages_sent // 5 + files_touched // 3)

    # --- SNARK: games played, win rate, short sessions ---
    if games_played > 0:
        win_rate = games_won / games_played
        stats.snark += min(20, int(games_played * win_rate * 2))
    stats.snark += min(10, discussions_started * 2)

    # --- General activity bonus ---
    activity = min(15, event_count // 20)
    stats.debugging += activity // 2
    stats.wisdom += activity // 3
    stats.patience += activity // 2

    # Clamp all stats
    for attr in ("debugging", "chaos", "snark", "wisdom", "patience"):
        setattr(stats, attr, max(5, min(50, getattr(stats, attr))))

    return stats


# The user's "species" — a special one-off
USER_SPECIES = Species(
    name="human",
    emoji="👤",
    rarity=Rarity.LEGENDARY,
    base_stats={"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10},
    description="The one behind the keyboard. Surprisingly capable.",
)


def create_user_buddy_state(
    name: str = "You",
    stats: UserStats | None = None,
) -> BuddyState:
    """Create a BuddyState representing the user.

    This lets the user join dungeon parties as a real character
    with stats derived from their actual behavior.
    """
    if stats is None:
        stats = UserStats()

    return BuddyState(
        buddy_id=-1,  # Special ID for user character
        name=name,
        species=USER_SPECIES,
        level=max(1, stats.total // 15),
        xp=0,
        mood="happy",
        mood_value=70,
        stats=stats.as_dict,
        shiny=False,
        soul_description="The player. Stats from real session data.",
        hat=None,
        hats_owned=[],
    )
