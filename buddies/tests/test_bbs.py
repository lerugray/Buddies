"""Tests for the BBS system — boards, profiles, nudge detection, content engine, auto-activity."""

from __future__ import annotations

import asyncio
import random
import unittest

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.bbs_boards import (
    BOARDS, BOARD_MAP, POST_TITLES, SYSOP_MESSAGES,
    BBSBoard, get_board, get_board_by_index,
)
from buddies.core.bbs_profile import BBSProfile, RARITY_STARS, REGISTER_MAP
from buddies.core.bbs_nudge import (
    NudgeDetector, NudgeResolver, NudgeAction, NudgeIntent, NudgeOutcome,
    BOARD_ALIASES,
)
from buddies.core.bbs_content import BBSContentEngine, BBSPost, BBSReply
from buddies.core.bbs_auto import BBSAutoActivity, BBSAutoEvent, AutoEventType
from buddies.core.prose import ProseEngine
from buddies.config import BBSConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_buddy(
    name="Tester",
    dominant="patience",
    chaos=10,
    mood="happy",
    level=5,
    hat=None,
    shiny=False,
    **overrides,
) -> BuddyState:
    stats = {"debugging": 10, "chaos": chaos, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = max(stats.get(dominant, 10), 30)
    sp = Species(
        name="test_species",
        emoji="\U0001f431",
        rarity=Rarity.COMMON,
        base_stats=stats,
        description="Test buddy",
    )
    defaults = dict(
        name=name,
        species=sp,
        level=level,
        xp=0,
        mood=mood,
        stats=stats,
        shiny=shiny,
        buddy_id=1,
        mood_value=50,
        soul_description="test",
        hat=hat,
        hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


def run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ===================================================================
# Boards
# ===================================================================

class TestBoards(unittest.TestCase):
    """Tests for bbs_boards.py"""

    def test_seven_boards_exist(self):
        self.assertEqual(len(BOARDS), 7)

    def test_all_boards_have_required_fields(self):
        for board in BOARDS:
            self.assertIsInstance(board, BBSBoard)
            self.assertTrue(board.name)
            self.assertTrue(board.label)
            self.assertTrue(board.color)
            self.assertTrue(board.tagline)
            self.assertTrue(board.vibe)
            self.assertTrue(board.stat_affinity)
            self.assertTrue(board.header)

    def test_get_board_by_label(self):
        board = get_board("CHAOS-LOUNGE")
        self.assertIsNotNone(board)
        self.assertEqual(board.name, "CHAOS LOUNGE")

    def test_get_board_returns_none_for_invalid(self):
        self.assertIsNone(get_board("NONEXISTENT-BOARD"))

    def test_get_board_by_index_valid(self):
        board = get_board_by_index(0)
        self.assertIsNotNone(board)
        self.assertEqual(board.label, "CHAOS-LOUNGE")

    def test_get_board_by_index_invalid(self):
        self.assertIsNone(get_board_by_index(-1))
        self.assertIsNone(get_board_by_index(99))

    def test_post_titles_for_all_non_sysop_boards(self):
        non_sysop = [b for b in BOARDS if b.label != "SYSOP-CORNER"]
        for board in non_sysop:
            self.assertIn(board.label, POST_TITLES, f"Missing POST_TITLES for {board.label}")
            self.assertGreater(len(POST_TITLES[board.label]), 0)

    def test_sysop_messages_non_empty(self):
        self.assertGreater(len(SYSOP_MESSAGES), 0)
        for msg in SYSOP_MESSAGES:
            self.assertIsInstance(msg, str)
            self.assertTrue(msg)


# ===================================================================
# Profiles
# ===================================================================

class TestProfiles(unittest.TestCase):
    """Tests for bbs_profile.py"""

    def test_from_buddy_state_sets_all_fields(self):
        buddy = make_buddy(name="TestBud", dominant="snark", level=8)
        profile = BBSProfile.from_buddy_state(buddy)
        self.assertEqual(profile.handle, "TestBud")
        self.assertEqual(profile.species, "test_species")
        self.assertEqual(profile.emoji, "\U0001f431")
        self.assertEqual(profile.rarity, "common")
        self.assertEqual(profile.level, 8)
        self.assertEqual(profile.dominant_stat, "snark")
        self.assertEqual(profile.register, "sarcastic")
        self.assertFalse(profile.shiny)
        self.assertIsNone(profile.hat)
        self.assertEqual(profile.privacy, "public")

    def test_to_frontmatter_yaml_delimiters(self):
        buddy = make_buddy()
        profile = BBSProfile.from_buddy_state(buddy)
        fm = profile.to_frontmatter()
        lines = fm.split("\n")
        self.assertEqual(lines[0], "---")
        self.assertEqual(lines[-1], "---")
        self.assertIn("buddy: Tester", fm)
        self.assertIn("species: test_species", fm)

    def test_to_short_tag_includes_key_info(self):
        buddy = make_buddy(name="Sparky", dominant="chaos")
        profile = BBSProfile.from_buddy_state(buddy)
        tag = profile.to_short_tag()
        self.assertIn("\U0001f431", tag)
        self.assertIn("Sparky", tag)
        self.assertIn("test_species", tag)
        self.assertIn("absurdist", tag)

    def test_to_profile_card_includes_species_level_stat(self):
        buddy = make_buddy(name="Sage", dominant="wisdom", level=10)
        profile = BBSProfile.from_buddy_state(buddy)
        card = profile.to_profile_card()
        self.assertIn("test_species", card)
        self.assertIn("10", card)
        self.assertIn("wisdom", card)

    def test_to_ascii_signature_format(self):
        buddy = make_buddy(name="Sig", level=7)
        profile = BBSProfile.from_buddy_state(buddy)
        sig = profile.to_ascii_signature()
        self.assertTrue(sig.startswith("-- "))
        self.assertIn("Sig", sig)
        self.assertIn("lvl 7", sig)

    def test_shiny_in_frontmatter_and_short_tag(self):
        buddy = make_buddy(shiny=True)
        profile = BBSProfile.from_buddy_state(buddy)
        fm = profile.to_frontmatter()
        self.assertIn("shiny: true", fm)
        tag = profile.to_short_tag()
        self.assertIn("\u2726", tag)  # ✦

    def test_hat_in_frontmatter(self):
        buddy = make_buddy(hat="top_hat")
        profile = BBSProfile.from_buddy_state(buddy)
        fm = profile.to_frontmatter()
        self.assertIn("hat: top_hat", fm)

    def test_privacy_levels(self):
        buddy = make_buddy()
        for level in ("public", "friends_only", "private"):
            profile = BBSProfile.from_buddy_state(buddy, privacy=level)
            self.assertEqual(profile.privacy, level)
            self.assertIn(f"privacy: {level}", profile.to_frontmatter())


# ===================================================================
# Nudge Detection
# ===================================================================

class TestNudgeDetection(unittest.TestCase):
    """Tests for NudgeDetector.detect()"""

    def setUp(self):
        self.detector = NudgeDetector()

    # POST intent
    def test_post_about_debugging(self):
        intent = self.detector.detect("post about debugging")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.POST)

    def test_go_post_something(self):
        intent = self.detector.detect("go post something")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.POST)

    def test_write_about_bugs(self):
        intent = self.detector.detect("write about bugs")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.POST)

    # BROWSE intent
    def test_check_the_bbs(self):
        intent = self.detector.detect("check the bbs")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.BROWSE)

    def test_go_browse_the_boards(self):
        intent = self.detector.detect("go browse the boards")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.BROWSE)

    def test_look_at_chaos_lounge(self):
        intent = self.detector.detect("look at the chaos lounge")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.BROWSE)

    # REPLY intent
    def test_reply_to_that_post(self):
        intent = self.detector.detect("reply to that post")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.REPLY)

    # REACT intent
    def test_react_to_latest_post(self):
        intent = self.detector.detect("react to the latest post")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.REACT)

    def test_what_do_you_think_about_that_post(self):
        intent = self.detector.detect("what do you think about that post")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, NudgeAction.REACT)

    # Board extraction
    def test_board_alias_chaos(self):
        self.assertIn("chaos", BOARD_ALIASES)
        self.assertEqual(BOARD_ALIASES["chaos"], "CHAOS-LOUNGE")

    def test_board_alias_debug_clinic(self):
        self.assertIn("debug clinic", BOARD_ALIASES)
        self.assertEqual(BOARD_ALIASES["debug clinic"], "DEBUG-CLINIC")

    # Non-BBS messages
    def test_returns_none_for_unrelated(self):
        self.assertIsNone(self.detector.detect("hello how are you"))
        self.assertIsNone(self.detector.detect("what is the weather"))

    def test_short_messages_return_none(self):
        self.assertIsNone(self.detector.detect("hi"))
        self.assertIsNone(self.detector.detect("ok"))
        self.assertIsNone(self.detector.detect(""))


# ===================================================================
# Nudge Resolver
# ===================================================================

class TestNudgeResolver(unittest.TestCase):
    """Tests for NudgeResolver.resolve()"""

    def setUp(self):
        self.resolver = NudgeResolver()

    def test_ecstatic_mood_increases_compliance(self):
        buddy = make_buddy(mood="ecstatic")
        intent = NudgeIntent(action=NudgeAction.POST)
        # Run many trials to check the statistical trend
        random.seed(42)
        results = [self.resolver.resolve(buddy, intent).accepted for _ in range(200)]
        ecstatic_rate = sum(results) / len(results)

        buddy_grumpy = make_buddy(mood="grumpy")
        random.seed(42)
        results_grumpy = [self.resolver.resolve(buddy_grumpy, intent).accepted for _ in range(200)]
        grumpy_rate = sum(results_grumpy) / len(results_grumpy)

        self.assertGreater(ecstatic_rate, grumpy_rate)

    def test_grumpy_mood_decreases_compliance(self):
        buddy = make_buddy(mood="grumpy")
        intent = NudgeIntent(action=NudgeAction.POST)
        random.seed(99)
        results = [self.resolver.resolve(buddy, intent).accepted for _ in range(200)]
        rate = sum(results) / len(results)
        # Grumpy base: 0.70 - 0.30 - 0.05 (post) = 0.35
        self.assertLess(rate, 0.55)

    def test_browse_gets_bonus_compliance(self):
        buddy = make_buddy(mood="neutral")
        intent_browse = NudgeIntent(action=NudgeAction.BROWSE)
        intent_post = NudgeIntent(action=NudgeAction.POST)

        random.seed(42)
        browse_results = [self.resolver.resolve(buddy, intent_browse).accepted for _ in range(200)]
        random.seed(42)
        post_results = [self.resolver.resolve(buddy, intent_post).accepted for _ in range(200)]

        browse_rate = sum(browse_results) / len(browse_results)
        post_rate = sum(post_results) / len(post_results)
        self.assertGreater(browse_rate, post_rate)

    def test_board_affinity_boosts_compliance(self):
        # Make a chaos-dominant buddy posting to CHAOS-LOUNGE
        buddy = make_buddy(dominant="chaos", mood="neutral")
        intent_match = NudgeIntent(action=NudgeAction.POST, board_hint="CHAOS-LOUNGE")
        intent_no_match = NudgeIntent(action=NudgeAction.POST, board_hint="DEBUG-CLINIC")

        random.seed(42)
        match_results = [self.resolver.resolve(buddy, intent_match).accepted for _ in range(300)]
        random.seed(42)
        no_match_results = [self.resolver.resolve(buddy, intent_no_match).accepted for _ in range(300)]

        match_rate = sum(match_results) / len(match_results)
        no_match_rate = sum(no_match_results) / len(no_match_results)
        self.assertGreater(match_rate, no_match_rate)

    def test_always_returns_nudge_outcome(self):
        buddy = make_buddy()
        intent = NudgeIntent(action=NudgeAction.BROWSE)
        outcome = self.resolver.resolve(buddy, intent)
        self.assertIsInstance(outcome, NudgeOutcome)
        self.assertIsInstance(outcome.accepted, bool)


# ===================================================================
# Content Engine
# ===================================================================

class TestContentEngine(unittest.TestCase):
    """Tests for BBSContentEngine"""

    def setUp(self):
        self.prose = ProseEngine()
        self.engine = BBSContentEngine(self.prose, ai_backend=None)
        self.buddy = make_buddy(dominant="chaos", chaos=30)

    def test_generate_post_returns_bbs_post(self):
        post = run(self.engine.generate_post(self.buddy, "CHAOS-LOUNGE"))
        self.assertIsInstance(post, BBSPost)
        self.assertEqual(post.board_label, "CHAOS-LOUNGE")
        self.assertTrue(post.title)
        self.assertTrue(post.body)
        self.assertIsInstance(post.profile, BBSProfile)

    def test_generate_reply_returns_bbs_reply(self):
        reply = run(self.engine.generate_reply(
            self.buddy,
            original_post_body="I found a weird bug today.",
            original_author="OtherBuddy",
        ))
        self.assertIsInstance(reply, BBSReply)
        self.assertTrue(reply.body)
        self.assertIsInstance(reply.profile, BBSProfile)

    def test_generate_browse_thought_returns_string(self):
        thought = self.engine.generate_browse_thought(self.buddy, "CHAOS LOUNGE")
        self.assertIsInstance(thought, str)
        self.assertTrue(thought)

    def test_generate_nudge_response_accept(self):
        response = self.engine.generate_nudge_response(self.buddy, accepted=True)
        self.assertIsInstance(response, str)
        self.assertTrue(response)

    def test_generate_nudge_response_refuse(self):
        response = self.engine.generate_nudge_response(self.buddy, accepted=False)
        self.assertIsInstance(response, str)
        self.assertTrue(response)

    def test_get_sysop_motd_returns_string(self):
        motd = self.engine.get_sysop_motd()
        self.assertIsInstance(motd, str)
        self.assertIn(motd, SYSOP_MESSAGES)

    def test_should_auto_post_returns_bool(self):
        random.seed(42)
        result = self.engine.should_auto_post(self.buddy)
        self.assertIsInstance(result, bool)

    def test_pick_best_board_returns_valid_label(self):
        random.seed(42)
        label = self.engine.pick_best_board(self.buddy)
        valid_labels = [b.label for b in BOARDS]
        self.assertIn(label, valid_labels)
        self.assertNotEqual(label, "SYSOP-CORNER")

    def test_generate_title_returns_string(self):
        title = self.engine._generate_title(self.buddy, "CHAOS-LOUNGE")
        self.assertIsInstance(title, str)
        self.assertTrue(title)


# ===================================================================
# Auto Activity
# ===================================================================

class TestAutoActivity(unittest.TestCase):
    """Tests for BBSAutoActivity"""

    def setUp(self):
        self.prose = ProseEngine()
        self.engine = BBSContentEngine(self.prose, ai_backend=None)
        self.config = BBSConfig()
        self.buddy = make_buddy(dominant="chaos", chaos=30, level=5)
        self.profile = BBSProfile.from_buddy_state(self.buddy)

    def test_tick_returns_nothing_before_interval(self):
        auto = BBSAutoActivity(
            transport=None, content=self.engine, config=self.config,
        )
        # Immediately after creation, timer hasn't elapsed
        event = run(auto.tick(self.buddy, self.profile))
        self.assertEqual(event.event_type, AutoEventType.NOTHING)

    def test_tick_disabled_config_returns_nothing(self):
        config = BBSConfig(auto_browse=False, auto_post=False)
        auto = BBSAutoActivity(
            transport=None, content=self.engine, config=config,
        )
        # Force timer expiry
        auto._last_activity_time = 0
        auto._next_check_minutes = 0
        event = run(auto.tick(self.buddy, self.profile))
        self.assertEqual(event.event_type, AutoEventType.NOTHING)

    def test_auto_browse_returns_browsed_event(self):
        auto = BBSAutoActivity(
            transport=None, content=self.engine, config=self.config,
        )
        event = run(auto._auto_browse(self.buddy))
        self.assertEqual(event.event_type, AutoEventType.BROWSED)
        self.assertTrue(event.message)
        self.assertTrue(event.board)

    def test_auto_event_dataclass_fields(self):
        event = BBSAutoEvent(event_type=AutoEventType.POSTED, message="hi", board="X", post_title="T")
        self.assertEqual(event.event_type, AutoEventType.POSTED)
        self.assertEqual(event.message, "hi")
        self.assertEqual(event.board, "X")
        self.assertEqual(event.post_title, "T")


if __name__ == "__main__":
    unittest.main()
