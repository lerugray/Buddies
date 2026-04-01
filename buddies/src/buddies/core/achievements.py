"""Achievements system — track milestones and reward exploration.

Achievements are checked periodically and on key events.
Unlocked achievements persist in the DB and notify the user once.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Achievement:
    """An achievement definition."""
    id: str
    name: str
    description: str
    icon: str
    category: str  # "collection", "social", "exploration", "mastery", "secret"


# ---------------------------------------------------------------------------
# Achievement catalog
# ---------------------------------------------------------------------------

ACHIEVEMENTS: list[Achievement] = [
    # Collection achievements
    Achievement("first_hatch", "First Steps", "Hatch your first buddy", "🥚", "collection"),
    Achievement("party_of_3", "Getting Crowded", "Have 3 buddies in your collection", "👥", "collection"),
    Achievement("party_of_5", "Full House", "Have 5 buddies in your collection", "🏠", "collection"),
    Achievement("party_of_10", "Zookeeper", "Have 10 buddies in your collection", "🦁", "collection"),
    Achievement("shiny_hunter", "Shiny Hunter", "Hatch a shiny buddy", "✨", "collection"),
    Achievement("common_collector", "Common Touch", "Own a Common rarity buddy", "⭐", "collection"),
    Achievement("rare_collector", "Rare Find", "Own a Rare rarity buddy", "💎", "collection"),
    Achievement("epic_collector", "Epic Discovery", "Own an Epic rarity buddy", "🔮", "collection"),
    Achievement("legendary_collector", "Legendary Encounter", "Own a Legendary buddy", "👑", "collection"),

    # Leveling achievements
    Achievement("level_5", "Growing Up", "Reach level 5 with any buddy", "📈", "mastery"),
    Achievement("level_10", "Adult Buddy", "Reach level 10 (Adult evolution)", "🌟", "mastery"),
    Achievement("level_20", "Elder Wisdom", "Reach level 20 (Elder evolution)", "🏆", "mastery"),
    Achievement("max_stat", "Specialist", "Get any stat to 50+", "💪", "mastery"),
    Achievement("all_stats_25", "Well-Rounded", "Get all stats to 25+", "⚖️", "mastery"),

    # Hat achievements
    Achievement("first_hat", "Haberdashery", "Unlock your first non-starter hat", "🎩", "collection"),
    Achievement("hat_collector_5", "Hat Rack", "Own 5 different hats", "🧢", "collection"),
    Achievement("all_hats", "Fashion Icon", "Unlock all 10 hats", "👒", "collection"),

    # Social / discussion achievements
    Achievement("first_discussion", "Town Hall", "Start a party discussion", "🗣️", "social"),
    Achievement("chatty", "Chatty", "Send 50 messages to your buddy", "💬", "social"),
    Achievement("storyteller", "Storyteller", "Send 200 messages total", "📖", "social"),

    # Session / exploration achievements
    Achievement("session_watcher", "Watchful Eye", "Observe 100 session events", "👁️", "exploration"),
    Achievement("session_marathon", "Marathon", "Observe 500 session events", "🏃", "exploration"),
    Achievement("token_saver", "Token Miser", "Save 10,000+ tokens via local AI", "💰", "exploration"),
    Achievement("config_health_a", "Clean Config", "Get an A grade on config health", "📋", "exploration"),
    Achievement("quick_saver", "Safety First", "Use quick-save [F1]", "💾", "exploration"),
    Achievement("theme_changer", "Fashionable", "Change the theme", "🎨", "exploration"),

    # Mood achievements
    Achievement("ecstatic", "Over The Moon", "Get a buddy to ecstatic mood", "🤩", "mastery"),
    Achievement("grumpy_buddy", "Grumpy Cat", "Let a buddy get grumpy", "😤", "secret"),
    Achievement("nightcap_earned", "Sleepyhead", "Unlock the nightcap hat via boredom", "😴", "secret"),

    # Secret achievements
    Achievement("phoenix_owner", "Reborn", "Own a Phoenix", "🔥", "secret"),
    Achievement("claude_owner", "Meta", "Own a Claude buddy", "🤖", "secret"),
    Achievement("zorak_owner", "Space Ghost", "Own a Zorak", "👾", "secret"),
    Achievement("void_cat_owner", "Stare Into The Void", "Own a Void Cat", "🐱", "secret"),
]

ACHIEVEMENT_MAP: dict[str, Achievement] = {a.id: a for a in ACHIEVEMENTS}


# ---------------------------------------------------------------------------
# Achievement checker — evaluates current state against all achievements
# ---------------------------------------------------------------------------

def check_achievements(
    buddies: list[dict],
    active_buddy: dict | None = None,
    session_events: int = 0,
    tokens_saved: int = 0,
    messages_sent: int = 0,
    discussions_started: int = 0,
    config_grade: str = "?",
    quick_saves: int = 0,
    themes_changed: int = 0,
    unlocked_ids: set[str] | None = None,
) -> list[Achievement]:
    """Check all achievements and return newly unlocked ones.

    Args:
        buddies: List of all buddy dicts from DB
        active_buddy: The currently active buddy dict
        session_events: Total session events observed
        tokens_saved: Total tokens saved by local AI
        messages_sent: Total user messages in current session
        discussions_started: Number of discussions opened
        config_grade: Current config health grade
        quick_saves: Number of quick-saves performed
        themes_changed: Number of theme changes
        unlocked_ids: Set of already-unlocked achievement IDs

    Returns:
        List of newly unlocked achievements
    """
    if unlocked_ids is None:
        unlocked_ids = set()

    newly_unlocked: list[Achievement] = []

    def _check(aid: str, condition: bool):
        if aid not in unlocked_ids and condition:
            newly_unlocked.append(ACHIEVEMENT_MAP[aid])

    # Collection
    _check("first_hatch", len(buddies) >= 1)
    _check("party_of_3", len(buddies) >= 3)
    _check("party_of_5", len(buddies) >= 5)
    _check("party_of_10", len(buddies) >= 10)

    rarities = {b.get("species", "") for b in buddies}
    species_names = {b.get("species", "") for b in buddies}
    shiny_count = sum(1 for b in buddies if b.get("shiny"))

    _check("shiny_hunter", shiny_count > 0)

    # Check rarities — need to look up species catalog
    from buddies.core.buddy_brain import SPECIES_CATALOG
    buddy_rarities = set()
    for b in buddies:
        for sp in SPECIES_CATALOG:
            if sp.name == b.get("species"):
                buddy_rarities.add(sp.rarity.value)
                break

    _check("common_collector", "common" in buddy_rarities)
    _check("rare_collector", "rare" in buddy_rarities)
    _check("epic_collector", "epic" in buddy_rarities)
    _check("legendary_collector", "legendary" in buddy_rarities)

    # Leveling — check all buddies
    max_level = max((b.get("level", 1) for b in buddies), default=1)
    _check("level_5", max_level >= 5)
    _check("level_10", max_level >= 10)
    _check("level_20", max_level >= 20)

    # Stat achievements — check all buddies
    for b in buddies:
        stats = [
            b.get("stat_debugging", 10),
            b.get("stat_patience", 10),
            b.get("stat_chaos", 10),
            b.get("stat_wisdom", 10),
            b.get("stat_snark", 10),
        ]
        if any(s >= 50 for s in stats):
            _check("max_stat", True)
        if all(s >= 25 for s in stats):
            _check("all_stats_25", True)

    # Hat achievements — check all buddies
    import json
    all_hats = set()
    for b in buddies:
        try:
            hats = json.loads(b.get("hats_owned", "[]"))
            all_hats.update(hats)
        except (json.JSONDecodeError, TypeError):
            pass

    non_starter_hats = all_hats - {"tinyduck"}
    _check("first_hat", len(non_starter_hats) >= 1)
    _check("hat_collector_5", len(all_hats) >= 5)
    _check("all_hats", len(all_hats) >= 10)

    # Mood achievements
    if active_buddy:
        _check("ecstatic", active_buddy.get("mood") == "ecstatic")
        _check("grumpy_buddy", active_buddy.get("mood") == "grumpy")
    _check("nightcap_earned", "nightcap" in all_hats)

    # Social
    _check("first_discussion", discussions_started >= 1)
    _check("chatty", messages_sent >= 50)
    _check("storyteller", messages_sent >= 200)

    # Session / exploration
    _check("session_watcher", session_events >= 100)
    _check("session_marathon", session_events >= 500)
    _check("token_saver", tokens_saved >= 10000)
    _check("config_health_a", config_grade == "A")
    _check("quick_saver", quick_saves >= 1)
    _check("theme_changer", themes_changed >= 1)

    # Secret — specific species
    _check("phoenix_owner", "phoenix" in species_names)
    _check("claude_owner", "claude" in species_names)
    _check("zorak_owner", "zorak" in species_names)
    _check("void_cat_owner", "void_cat" in species_names)

    return newly_unlocked
