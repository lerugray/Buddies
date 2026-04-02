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
    Achievement("all_hats", "Fashion Icon", "Unlock all 16 hats", "👒", "collection"),

    # Social / discussion achievements
    Achievement("first_discussion", "Town Hall", "Start a party discussion", "🗣️", "social"),
    Achievement("chatty", "Chatty", "Send 50 messages to your buddy", "💬", "social"),
    Achievement("storyteller", "Storyteller", "Send 200 messages total", "📖", "social"),

    # BBS social achievements
    Achievement("first_post", "First Post!", "Make your first BBS post", "📝", "social"),
    Achievement("thread_starter", "Thread Starter", "Make 5 BBS posts", "🧵", "social"),
    Achievement("regular", "BBS Regular", "Make 20 BBS posts", "📰", "social"),
    Achievement("first_reply", "Conversationalist", "Reply to a BBS post", "↩️", "social"),
    Achievement("popular_poster", "Popular", "Make 50 total BBS posts and replies", "🌟", "social"),
    Achievement("board_hopper", "Board Hopper", "Post on 3 different boards", "🏄", "social"),
    Achievement("social_butterfly", "Social Butterfly", "Have 3 buddies post on the BBS", "🦋", "social"),

    # Games achievements
    Achievement("first_game", "Player One", "Play any game in the arcade", "🕹️", "exploration"),
    Achievement("rps_veteran", "RPS Veteran", "Win 10 RPS matches", "✊", "mastery"),
    Achievement("rps_streak", "Unbreakable", "Win an RPS match 3-0 (no losses)", "🔥", "mastery"),
    Achievement("card_shark", "Card Shark", "Win 10 card games", "🃏", "mastery"),
    Achievement("battle_veteran", "Battle Veteran", "Win 10 battles", "⚔️", "mastery"),
    Achievement("trivia_master", "Trivia Master", "Score 10/10 on trivia", "🧠", "mastery"),
    Achievement("pong_champion", "Pong Champion", "Win a game of Pong", "🏓", "mastery"),
    Achievement("dungeon_master", "Dungeon Delver", "Win a blobber dungeon crawl", "🗡️", "mastery"),
    Achievement("stackwars_victor", "Strategist", "Win a game of StackWars", "⚔️", "mastery"),
    Achievement("arcade_regular", "Arcade Regular", "Play 25 total games", "🕹️", "mastery"),
    Achievement("all_in_chaos", "ALL IN!", "Win a game with a high-CHAOS buddy", "🎰", "secret"),

    # MUD achievements
    Achievement("mud_explorer", "MUD Tourist", "Visit 5 rooms in StackHaven MUD", "🗺️", "exploration"),
    Achievement("mud_slayer", "Bug Squasher", "Defeat 3 hostile NPCs in the MUD", "🐛", "mastery"),
    Achievement("mud_quester", "Quest Hero", "Complete 2 quests in the MUD", "📋", "mastery"),
    Achievement("mud_dragon", "Debt Free", "Defeat the Technical Debt Dragon", "🐉", "secret"),
    Achievement("mud_shopper", "Consumer", "Buy something from a MUD merchant", "🛒", "exploration"),
    Achievement("mud_gambler", "High Roller", "Gamble 100+ gold total in the MUD", "🎰", "secret"),
    Achievement("mud_tipper", "Generous Tipper", "Tip 5 different NPCs in the MUD", "💸", "social"),
    Achievement("mud_bounty_hunter", "Bounty Hunter", "Complete 3 bounty contracts", "📋", "mastery"),

    # Fusion achievements
    Achievement("first_fusion", "Soul Splice", "Perform your first buddy fusion", "⚗️", "collection"),
    Achievement("recipe_fusion", "Alchemist", "Discover a special fusion recipe", "📜", "collection"),
    Achievement("fusion_collector", "Fusion Addict", "Perform 5 fusions", "🧬", "collection"),

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
    bbs_stats: dict | None = None,
    game_stats: dict | None = None,
    fusion_stats: dict | None = None,
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
        bbs_stats: BBS activity stats dict (posts, replies, total, boards_used, unique_authors)
        game_stats: Game stats dict (games_played, games_won, by_type, rps_max_streak)
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
    _check("all_hats", len(all_hats) >= 16)

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

    # BBS social achievements
    if bbs_stats:
        posts = bbs_stats.get("posts", 0)
        replies = bbs_stats.get("replies", 0)
        total = bbs_stats.get("total", 0)
        boards = bbs_stats.get("boards_used", 0)
        authors = bbs_stats.get("unique_authors", 0)
        _check("first_post", posts >= 1)
        _check("thread_starter", posts >= 5)
        _check("regular", posts >= 20)
        _check("first_reply", replies >= 1)
        _check("popular_poster", total >= 50)
        _check("board_hopper", boards >= 3)
        _check("social_butterfly", authors >= 3)

    # Games achievements
    if game_stats:
        gp = game_stats.get("games_played", 0)
        gw = game_stats.get("games_won", 0)
        by_type = game_stats.get("by_type", {})
        rps = by_type.get("rps", {})
        rps_won = rps.get("won", 0)
        rps_streak = game_stats.get("rps_max_streak", 0)
        cards_won = sum(
            by_type.get(g, {}).get("won", 0)
            for g in ("blackjack", "holdem", "whist")
        )
        battles_won = by_type.get("battle", {}).get("won", 0)
        pong_won = by_type.get("pong", {}).get("won", 0)
        dungeon_won = by_type.get("crawl", {}).get("won", 0)
        stackwars_won = by_type.get("stackwars", {}).get("won", 0)
        trivia_perfect = game_stats.get("trivia_perfect", False)

        # MUD achievements
        mud_stats = by_type.get("mud", {})
        mud_rooms = mud_stats.get("rooms_visited", 0)
        mud_kills = mud_stats.get("npcs_defeated", 0)
        mud_quests = mud_stats.get("quests_completed", 0)
        _check("mud_explorer", mud_rooms >= 5)
        _check("mud_slayer", mud_kills >= 3)
        _check("mud_quester", mud_quests >= 2)
        _check("mud_dragon", mud_stats.get("dragon_slain", False))
        _check("mud_shopper", mud_stats.get("items_bought", 0) >= 1)
        _check("mud_gambler", mud_stats.get("gold_gambled", 0) >= 100)
        _check("mud_tipper", mud_stats.get("tips_given", 0) >= 5)
        _check("mud_bounty_hunter", mud_stats.get("bounties_completed", 0) >= 3)

        _check("first_game", gp >= 1)
        _check("rps_veteran", rps_won >= 10)
        _check("rps_streak", rps_streak >= 3)
        _check("card_shark", cards_won >= 10)
        _check("battle_veteran", battles_won >= 10)
        _check("pong_champion", pong_won >= 1)
        _check("dungeon_master", dungeon_won >= 1)
        _check("stackwars_victor", stackwars_won >= 1)
        _check("trivia_master", trivia_perfect)
        _check("arcade_regular", gp >= 25)

        # Secret: win with high-CHAOS buddy
        if active_buddy and gw >= 1:
            chaos_val = active_buddy.get("stat_chaos", 10)
            _check("all_in_chaos", chaos_val >= 30)

    # Fusion achievements
    if fusion_stats:
        total_fusions = fusion_stats.get("total", 0)
        recipe_fusions = fusion_stats.get("recipes", 0)
        _check("first_fusion", total_fusions >= 1)
        _check("recipe_fusion", recipe_fusions >= 1)
        _check("fusion_collector", total_fusions >= 5)

    # Also detect fused buddies by the "(Fused)" tag in soul_description
    for b in buddies:
        soul = b.get("soul_description", "")
        if "(Fused)" in soul:
            _check("first_fusion", True)
            break

    return newly_unlocked
