"""Comprehensive tests for the achievements system.

Tests all achievement conditions systematically.
"""

import json
import pytest

from buddies.core.achievements import (
    ACHIEVEMENTS, ACHIEVEMENT_MAP, check_achievements, Achievement,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_buddies(count=1, species="duck", level=1, shiny=False, hats="[]",
                 soul_description="", **stat_overrides):
    """Create a list of buddy dicts for testing."""
    buddies = []
    for i in range(count):
        buddy = {
            "id": i + 1,
            "species": species,
            "name": f"Buddy{i+1}",
            "level": level,
            "shiny": shiny,
            "hats_owned": hats,
            "is_active": 1 if i == 0 else 0,
            "stat_debugging": stat_overrides.get("debugging", 10),
            "stat_patience": stat_overrides.get("patience", 10),
            "stat_chaos": stat_overrides.get("chaos", 10),
            "stat_wisdom": stat_overrides.get("wisdom", 10),
            "stat_snark": stat_overrides.get("snark", 10),
            "mood": "happy",
            "soul_description": soul_description,
        }
        buddies.append(buddy)
    return buddies


def check(buddies=None, **kwargs):
    """Shorthand for check_achievements."""
    if buddies is None:
        buddies = make_buddies(1)
    return {a.id for a in check_achievements(buddies, **kwargs)}


# ---------------------------------------------------------------------------
# Catalog integrity
# ---------------------------------------------------------------------------

class TestAchievementCatalog:
    def test_all_achievements_have_unique_ids(self):
        ids = [a.id for a in ACHIEVEMENTS]
        assert len(ids) == len(set(ids))

    def test_all_achievements_have_fields(self):
        for a in ACHIEVEMENTS:
            assert a.id
            assert a.name
            assert a.description
            assert a.icon
            assert a.category in ("collection", "mastery", "social", "exploration", "secret")

    def test_achievement_map_matches_list(self):
        assert len(ACHIEVEMENT_MAP) == len(ACHIEVEMENTS)

    def test_achievement_count(self):
        """Track total — update when adding new achievements."""
        assert len(ACHIEVEMENTS) >= 52  # 49 original + 3 fusion


# ---------------------------------------------------------------------------
# Collection achievements
# ---------------------------------------------------------------------------

class TestCollectionAchievements:
    def test_first_hatch(self):
        assert "first_hatch" in check(make_buddies(1))

    def test_party_of_3(self):
        ids = check(make_buddies(3))
        assert "party_of_3" in ids

    def test_party_of_5(self):
        ids = check(make_buddies(5))
        assert "party_of_5" in ids

    def test_party_of_10(self):
        ids = check(make_buddies(10))
        assert "party_of_10" in ids

    def test_shiny_hunter(self):
        buddies = make_buddies(1, shiny=True)
        assert "shiny_hunter" in check(buddies)

    def test_no_shiny_hunter_without_shiny(self):
        assert "shiny_hunter" not in check(make_buddies(1))

    def test_rarity_achievements(self):
        # Common
        assert "common_collector" in check(make_buddies(1, species="duck"))
        # Rare
        assert "rare_collector" in check(make_buddies(1, species="dragon"))
        # Epic
        assert "epic_collector" in check(make_buddies(1, species="phoenix"))
        # Legendary
        assert "legendary_collector" in check(make_buddies(1, species="ghost"))


# ---------------------------------------------------------------------------
# Leveling achievements
# ---------------------------------------------------------------------------

class TestLevelingAchievements:
    def test_level_5(self):
        assert "level_5" in check(make_buddies(1, level=5))

    def test_level_10(self):
        assert "level_10" in check(make_buddies(1, level=10))

    def test_level_20(self):
        assert "level_20" in check(make_buddies(1, level=20))

    def test_no_level_achievement_at_level_1(self):
        ids = check(make_buddies(1, level=1))
        assert "level_5" not in ids
        assert "level_10" not in ids


# ---------------------------------------------------------------------------
# Stat achievements
# ---------------------------------------------------------------------------

class TestStatAchievements:
    def test_specialist_high_stat(self):
        buddies = make_buddies(1, debugging=55)
        assert "max_stat" in check(buddies)

    def test_no_specialist_at_normal_stats(self):
        assert "max_stat" not in check(make_buddies(1))

    def test_well_rounded(self):
        buddies = make_buddies(1, debugging=25, patience=25, chaos=25, wisdom=25, snark=25)
        assert "all_stats_25" in check(buddies)


# ---------------------------------------------------------------------------
# Hat achievements
# ---------------------------------------------------------------------------

class TestHatAchievements:
    def test_first_hat(self):
        buddies = make_buddies(1, hats='["tinyduck", "crown"]')
        assert "first_hat" in check(buddies)

    def test_no_first_hat_with_only_starter(self):
        buddies = make_buddies(1, hats='["tinyduck"]')
        assert "first_hat" not in check(buddies)

    def test_hat_collector_5(self):
        hats = json.dumps(["tinyduck", "crown", "wizard", "propeller", "nightcap"])
        buddies = make_buddies(1, hats=hats)
        assert "hat_collector_5" in check(buddies)


# ---------------------------------------------------------------------------
# Social achievements
# ---------------------------------------------------------------------------

class TestSocialAchievements:
    def test_first_discussion(self):
        assert "first_discussion" in check(discussions_started=1)

    def test_chatty(self):
        assert "chatty" in check(messages_sent=50)

    def test_storyteller(self):
        assert "storyteller" in check(messages_sent=200)


# ---------------------------------------------------------------------------
# BBS achievements
# ---------------------------------------------------------------------------

class TestBBSAchievements:
    def test_first_post(self):
        assert "first_post" in check(bbs_stats={"posts": 1, "replies": 0, "total": 1, "boards_used": 1, "unique_authors": 1})

    def test_thread_starter(self):
        stats = {"posts": 5, "replies": 0, "total": 5, "boards_used": 1, "unique_authors": 1}
        assert "thread_starter" in check(bbs_stats=stats)

    def test_board_hopper(self):
        stats = {"posts": 3, "replies": 0, "total": 3, "boards_used": 3, "unique_authors": 1}
        assert "board_hopper" in check(bbs_stats=stats)

    def test_social_butterfly(self):
        stats = {"posts": 3, "replies": 0, "total": 3, "boards_used": 1, "unique_authors": 3}
        assert "social_butterfly" in check(bbs_stats=stats)


# ---------------------------------------------------------------------------
# Game achievements
# ---------------------------------------------------------------------------

class TestGameAchievements:
    def _game_stats(self, **kwargs):
        base = {"games_played": 0, "games_won": 0, "by_type": {},
                "trivia_perfect": False}
        base.update(kwargs)
        return base

    def test_first_game(self):
        assert "first_game" in check(game_stats=self._game_stats(games_played=1))

    def test_arcade_regular(self):
        assert "arcade_regular" in check(game_stats=self._game_stats(games_played=25))

    def test_card_shark(self):
        stats = self._game_stats(by_type={
            "holdem": {"played": 5, "won": 5},
            "whist": {"played": 5, "won": 5},
        })
        assert "card_shark" in check(game_stats=stats)

    def test_trivia_master(self):
        stats = self._game_stats(trivia_perfect=True)
        assert "trivia_master" in check(game_stats=stats)

    def test_pong_champion(self):
        stats = self._game_stats(by_type={"pong": {"played": 1, "won": 1}})
        assert "pong_champion" in check(game_stats=stats)

    def test_stackwars_victor(self):
        stats = self._game_stats(by_type={"stackwars": {"played": 1, "won": 1}})
        assert "stackwars_victor" in check(game_stats=stats)

    def test_dungeon_master(self):
        stats = self._game_stats(by_type={"crawl": {"played": 1, "won": 1}})
        assert "dungeon_master" in check(game_stats=stats)

    # Snake achievements
    def test_snake_first(self):
        stats = self._game_stats(by_type={"snake": {"played": 1}})
        assert "snake_first" in check(game_stats=stats)

    def test_snake_score_500(self):
        stats = self._game_stats(by_type={"snake": {"played": 1, "best_score": 500}})
        assert "snake_score_500" in check(game_stats=stats)

    def test_snake_length_20(self):
        stats = self._game_stats(by_type={"snake": {"played": 1, "best_length": 20}})
        assert "snake_length_20" in check(game_stats=stats)

    def test_snake_score_1000(self):
        stats = self._game_stats(by_type={"snake": {"played": 1, "best_score": 1000}})
        assert "snake_score_1000" in check(game_stats=stats)

    # Ski Free achievements
    def test_ski_first(self):
        stats = self._game_stats(by_type={"skifree": {"played": 1}})
        assert "ski_first" in check(game_stats=stats)

    def test_ski_distance_1000(self):
        stats = self._game_stats(by_type={"skifree": {"played": 1, "best_distance": 1000}})
        assert "ski_distance_1000" in check(game_stats=stats)

    def test_ski_survive_auditor(self):
        stats = self._game_stats(by_type={"skifree": {"played": 1, "survived_auditor_ticks": 30}})
        assert "ski_survive_auditor" in check(game_stats=stats)

    def test_ski_distance_3000(self):
        stats = self._game_stats(by_type={"skifree": {"played": 1, "best_distance": 3000}})
        assert "ski_distance_3000" in check(game_stats=stats)

    # Deckbuilder achievements
    def test_deck_first(self):
        stats = self._game_stats(by_type={"deckbuilder": {"played": 1}})
        assert "deck_first" in check(game_stats=stats)

    def test_deck_win(self):
        stats = self._game_stats(by_type={"deckbuilder": {"played": 1, "won": 1}})
        assert "deck_win" in check(game_stats=stats)

    def test_deck_flawless(self):
        stats = self._game_stats(by_type={"deckbuilder": {"played": 1, "won": 1, "best_win_stability": 8}})
        assert "deck_flawless" in check(game_stats=stats)

    def test_deck_no_shop(self):
        stats = self._game_stats(by_type={"deckbuilder": {"played": 1, "won": 1, "no_shop_win": True}})
        assert "deck_no_shop" in check(game_stats=stats)


# ---------------------------------------------------------------------------
# MUD achievements
# ---------------------------------------------------------------------------

class TestMUDAchievements:
    def _mud_stats(self, **kwargs):
        mud = {"rooms_visited": 0, "npcs_defeated": 0, "quests_completed": 0,
               "dragon_slain": False, "items_bought": 0}
        mud.update(kwargs)
        return {"games_played": 1, "games_won": 0, "by_type": {"mud": mud},
                "trivia_perfect": False}

    def test_mud_explorer(self):
        assert "mud_explorer" in check(game_stats=self._mud_stats(rooms_visited=5))

    def test_mud_slayer(self):
        assert "mud_slayer" in check(game_stats=self._mud_stats(npcs_defeated=3))

    def test_mud_quester(self):
        assert "mud_quester" in check(game_stats=self._mud_stats(quests_completed=2))

    def test_mud_dragon(self):
        assert "mud_dragon" in check(game_stats=self._mud_stats(dragon_slain=True))

    def test_mud_shopper(self):
        assert "mud_shopper" in check(game_stats=self._mud_stats(items_bought=1))


# ---------------------------------------------------------------------------
# Exploration achievements
# ---------------------------------------------------------------------------

class TestExplorationAchievements:
    def test_session_watcher(self):
        assert "session_watcher" in check(session_events=100)

    def test_session_marathon(self):
        assert "session_marathon" in check(session_events=500)

    def test_config_health_a(self):
        assert "config_health_a" in check(config_grade="A")

    def test_quick_saver(self):
        assert "quick_saver" in check(quick_saves=1)

    def test_theme_changer(self):
        assert "theme_changer" in check(themes_changed=1)


# ---------------------------------------------------------------------------
# Secret achievements
# ---------------------------------------------------------------------------

class TestSecretAchievements:
    def test_phoenix_owner(self):
        assert "phoenix_owner" in check(make_buddies(1, species="phoenix"))

    def test_claude_owner(self):
        assert "claude_owner" in check(make_buddies(1, species="claude"))

    def test_zorak_owner(self):
        assert "zorak_owner" in check(make_buddies(1, species="zorak"))

    def test_void_cat_owner(self):
        assert "void_cat_owner" in check(make_buddies(1, species="void_cat"))

    def test_all_in_chaos(self):
        buddies = make_buddies(1, species="duck", chaos=35)
        active = buddies[0]
        stats = {"games_played": 1, "games_won": 1, "by_type": {},
                 "trivia_perfect": False}
        assert "all_in_chaos" in check(buddies, active_buddy=active, game_stats=stats)


# ---------------------------------------------------------------------------
# Fusion achievements
# ---------------------------------------------------------------------------

class TestFusionAchievements:
    def test_first_fusion_via_stats(self):
        assert "first_fusion" in check(fusion_stats={"total": 1, "recipes": 0})

    def test_recipe_fusion(self):
        assert "recipe_fusion" in check(fusion_stats={"total": 1, "recipes": 1})

    def test_fusion_collector(self):
        assert "fusion_collector" in check(fusion_stats={"total": 5, "recipes": 2})

    def test_fused_tag_detection(self):
        buddies = make_buddies(1, soul_description="(Fused) Two souls.")
        assert "first_fusion" in check(buddies)


# ---------------------------------------------------------------------------
# Already-unlocked filtering
# ---------------------------------------------------------------------------

class TestUnlockedFiltering:
    def test_already_unlocked_not_returned(self):
        """Previously unlocked achievements should not appear in results."""
        buddies = make_buddies(3)
        # First check — should include party_of_3
        first = check(buddies)
        assert "party_of_3" in first

        # Second check with party_of_3 already unlocked
        second = check(buddies, unlocked_ids={"party_of_3"})
        assert "party_of_3" not in second

    def test_multiple_achievements_at_once(self):
        """Multiple achievements can unlock simultaneously."""
        buddies = make_buddies(5, species="phoenix", level=10, shiny=True)
        ids = check(buddies)
        # Should unlock several at once
        assert len(ids) >= 4  # first_hatch, party_of_3, party_of_5, epic_collector, level_5, level_10, shiny_hunter...
