"""Personality Drift — stats evolve based on how you interact with your buddy.

Instead of static species stats, buddies gradually shift toward
the activities you do together. The tamagotchi promise: your
choices shape who they become.

Drift events:
- Games: each game type nudges specific stats
- Session activity: coding tools boost DEBUGGING, agent spawns boost WISDOM
- Chat: talking to your buddy boosts PATIENCE
- Idle time: neglect increases CHAOS
- Discussions: boost SNARK and WISDOM
- BBS posting: boosts SNARK
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Drift rules — what activity boosts which stat
# ---------------------------------------------------------------------------

# Game type → stat boosts (stat_name, amount)
GAME_DRIFT: dict[str, list[tuple[str, int]]] = {
    "rps": [("chaos", 1), ("snark", 1)],
    "blackjack": [("patience", 1), ("wisdom", 1)],
    "holdem": [("wisdom", 1), ("patience", 1), ("snark", 1)],
    "whist": [("patience", 2), ("wisdom", 1)],
    "battle": [("debugging", 2), ("chaos", 1)],
    "trivia": [("wisdom", 2), ("debugging", 1)],
    "pong": [("patience", 1), ("debugging", 1)],
    "crawl": [("debugging", 1), ("wisdom", 1), ("patience", 1)],
    "mud": [("wisdom", 2), ("patience", 1), ("snark", 1)],
    "stackwars": [("wisdom", 2), ("debugging", 1), ("patience", 1)],
}

# Win/lose modifiers
WIN_DRIFT: list[tuple[str, int]] = [("debugging", 1)]   # Winners get sharper
LOSE_DRIFT: list[tuple[str, int]] = [("patience", 1)]    # Losers learn patience

# Session activity drift
SESSION_DRIFT: dict[str, list[tuple[str, int]]] = {
    "Edit": [("debugging", 1)],
    "Write": [("debugging", 1)],
    "Read": [("wisdom", 1)],
    "Grep": [("debugging", 1)],
    "Agent": [("wisdom", 1)],
    "Bash": [("chaos", 1)],
}

# Social drift
CHAT_DRIFT: list[tuple[str, int]] = [("patience", 1)]
DISCUSSION_DRIFT: list[tuple[str, int]] = [("snark", 1), ("wisdom", 1)]
BBS_POST_DRIFT: list[tuple[str, int]] = [("snark", 1), ("chaos", 1)]

# Fusion drift — fusing is transformative, boosts wisdom and chaos
FUSION_DRIFT: list[tuple[str, int]] = [("wisdom", 3), ("chaos", 2), ("patience", 1)]

# Idle/neglect drift (applied periodically when buddy hasn't been interacted with)
IDLE_DRIFT: list[tuple[str, int]] = [("chaos", 1)]

# Stat cap
STAT_MAX = 99


@dataclass
class DriftResult:
    """Result of applying drift to a buddy's stats."""
    changes: dict[str, int]  # stat_name → amount changed
    old_stats: dict[str, int]
    new_stats: dict[str, int]

    @property
    def has_changes(self) -> bool:
        return any(v != 0 for v in self.changes.values())

    def summary(self) -> str:
        """Human-readable summary of stat changes."""
        parts = []
        for stat, delta in self.changes.items():
            if delta > 0:
                parts.append(f"{stat.upper()} +{delta}")
            elif delta < 0:
                parts.append(f"{stat.upper()} {delta}")
        return ", ".join(parts) if parts else "no change"


def apply_drift(
    stats: dict[str, int],
    boosts: list[tuple[str, int]],
    multiplier: float = 1.0,
) -> DriftResult:
    """Apply stat boosts to a buddy's stats dict (mutates in place).

    Args:
        stats: The buddy's current stats dict
        boosts: List of (stat_name, amount) to apply
        multiplier: Scale factor (e.g., 0.5 for reduced drift)

    Returns:
        DriftResult with changes applied
    """
    old = dict(stats)
    changes: dict[str, int] = {}

    for stat_name, amount in boosts:
        if stat_name not in stats:
            continue
        actual = int(amount * multiplier)
        if actual == 0:
            continue
        before = stats[stat_name]
        stats[stat_name] = max(1, min(STAT_MAX, stats[stat_name] + actual))
        changes[stat_name] = stats[stat_name] - before

    return DriftResult(changes=changes, old_stats=old, new_stats=dict(stats))


def drift_for_game(
    stats: dict[str, int],
    game_type: str,
    won: bool,
) -> DriftResult:
    """Apply personality drift after a game.

    Args:
        stats: Buddy's stats dict (mutated in place)
        game_type: The game type string (e.g., "trivia", "pong")
        won: Whether the player won
    """
    boosts = list(GAME_DRIFT.get(game_type, []))
    if won:
        boosts.extend(WIN_DRIFT)
    else:
        boosts.extend(LOSE_DRIFT)

    return apply_drift(stats, boosts)


def drift_for_session_tool(
    stats: dict[str, int],
    tool_name: str,
) -> DriftResult:
    """Apply drift from a Claude Code session tool usage."""
    boosts = SESSION_DRIFT.get(tool_name, [])
    if not boosts:
        return DriftResult(changes={}, old_stats=dict(stats), new_stats=dict(stats))
    # Session tools fire frequently, so reduce drift amount
    return apply_drift(stats, boosts, multiplier=0.5)


def drift_for_chat(stats: dict[str, int]) -> DriftResult:
    """Apply drift from chatting with your buddy."""
    return apply_drift(stats, CHAT_DRIFT, multiplier=0.5)


def drift_for_fusion(stats: dict[str, int]) -> DriftResult:
    """Apply drift from fusing two buddies — a transformative event."""
    return apply_drift(stats, FUSION_DRIFT)


def drift_for_idle(stats: dict[str, int], minutes_idle: int) -> DriftResult:
    """Apply drift from buddy being neglected.

    Only kicks in after 30+ minutes of no interaction.
    """
    if minutes_idle < 30:
        return DriftResult(changes={}, old_stats=dict(stats), new_stats=dict(stats))

    # Scale with idle time, but cap it
    mult = min(minutes_idle / 60.0, 3.0)
    return apply_drift(stats, IDLE_DRIFT, multiplier=mult)
