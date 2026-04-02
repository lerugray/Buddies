"""Tests for the personality-driven prose engine.

Covers: register selection, template pools, template suppression,
weirdness overlay, closers, context injection, and ProseEngine integration.
"""

import random
import pytest

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.prose import (
    REGISTERS, TEMPLATES, CLOSERS, WEIRD_OVERLAYS,
    CONTEXT_SPECIES, CONTEXT_MOOD,
    _dominant_stat, _register, _weirdness,
    ProseEngine,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", chaos=10, **overrides):
    stats = {"debugging": 10, "chaos": chaos, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = max(stats.get(dominant, 10), 30)
    sp = Species(
        name="test_species", emoji="🐱", rarity=Rarity.COMMON,
        base_stats=stats, description="Test buddy",
    )
    defaults = dict(
        name=name, species=sp, level=5, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=1, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


# ---------------------------------------------------------------------------
# Register system
# ---------------------------------------------------------------------------

class TestRegisters:
    def test_all_stats_map_to_register(self):
        for stat in ["debugging", "snark", "chaos", "wisdom", "patience"]:
            assert stat in REGISTERS

    def test_dominant_stat_selects_highest(self):
        buddy = make_buddy(dominant="debugging")
        assert _dominant_stat(buddy) == "debugging"

    def test_register_from_dominant_stat(self):
        for stat, expected_register in REGISTERS.items():
            buddy = make_buddy(dominant=stat)
            assert _register(buddy) == expected_register

    def test_register_tiebreak_is_deterministic(self):
        """When stats are tied, max() picks consistently."""
        buddy = make_buddy()
        buddy.stats = {"debugging": 20, "chaos": 20, "snark": 20, "wisdom": 20, "patience": 20}
        reg1 = _register(buddy)
        reg2 = _register(buddy)
        assert reg1 == reg2


# ---------------------------------------------------------------------------
# Weirdness scaling
# ---------------------------------------------------------------------------

class TestWeirdness:
    def test_low_chaos_low_weirdness(self):
        buddy = make_buddy(chaos=5)
        assert _weirdness(buddy) < 0.1

    def test_high_chaos_high_weirdness(self):
        buddy = make_buddy(chaos=99)
        assert _weirdness(buddy) > 0.9

    def test_weirdness_scales_linearly(self):
        buddy50 = make_buddy(chaos=50)
        buddy25 = make_buddy(chaos=25)
        assert _weirdness(buddy50) > _weirdness(buddy25)


# ---------------------------------------------------------------------------
# Template pools
# ---------------------------------------------------------------------------

class TestTemplatePools:
    def test_core_triggers_exist(self):
        expected = ["edit_storm", "bash_run", "long_session", "error_detected",
                    "idle", "session_start"]
        for trigger in expected:
            assert trigger in TEMPLATES, f"Missing trigger pool: {trigger}"

    def test_all_pools_have_multiple_templates(self):
        for trigger, pool in TEMPLATES.items():
            assert len(pool) >= 2, f"Pool '{trigger}' has only {len(pool)} template(s)"

    def test_templates_are_strings(self):
        for trigger, pool in TEMPLATES.items():
            for template in pool:
                assert isinstance(template, str)

    def test_closers_cover_all_registers(self):
        for register in REGISTERS.values():
            assert register in CLOSERS, f"Missing closer for register: {register}"

    def test_closers_have_multiple_options(self):
        for register, pool in CLOSERS.items():
            assert len(pool) >= 2, f"Closer pool '{register}' too small"

    def test_weird_overlays_exist(self):
        assert "absurd" in WEIRD_OVERLAYS
        assert "quirky" in WEIRD_OVERLAYS
        assert len(WEIRD_OVERLAYS["absurd"]) >= 3
        assert len(WEIRD_OVERLAYS["quirky"]) >= 3


# ---------------------------------------------------------------------------
# ProseEngine
# ---------------------------------------------------------------------------

class TestProseEngine:
    def test_generates_text_for_known_trigger(self):
        engine = ProseEngine()
        buddy = make_buddy()
        result = engine.thought("edit_storm", buddy, {"count": 5})
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_none_for_unknown_trigger(self):
        engine = ProseEngine()
        buddy = make_buddy()
        result = engine.thought("totally_fake_trigger", buddy)
        assert result is None

    def test_template_interpolation(self):
        """Templates should fill {name} placeholders."""
        engine = ProseEngine()
        buddy = make_buddy(name="Sparky")
        # Run many times — at least some templates use {name}
        found_name = False
        random.seed(42)
        for _ in range(50):
            result = engine.thought("edit_storm", buddy, {"count": 3})
            if result and "Sparky" in result:
                found_name = True
                break
        assert found_name, "Name placeholder never filled across 50 attempts"

    def test_template_suppression_avoids_repeats(self):
        """Engine should try to avoid repeating the last used template."""
        engine = ProseEngine()
        buddy = make_buddy()
        random.seed(1)  # Fixed seed
        results = set()
        for _ in range(20):
            result = engine.thought("edit_storm", buddy, {"count": 1})
            results.add(result)
        # With 8 templates and 20 tries, should get variety
        assert len(results) >= 3, "Too little variety in template selection"

    def test_weirdness_overlay_at_high_chaos(self):
        """High chaos should sometimes produce absurd overlays."""
        engine = ProseEngine()
        buddy = make_buddy(chaos=99, dominant="chaos")
        absurd_texts = set(WEIRD_OVERLAYS["absurd"] + WEIRD_OVERLAYS["quirky"])
        found_weird = False
        random.seed(42)
        for _ in range(200):
            result = engine.thought("idle", buddy)
            if result in absurd_texts:
                found_weird = True
                break
        assert found_weird, "High chaos never triggered weird overlay in 200 tries"

    def test_no_weirdness_at_low_chaos(self):
        """Low chaos should never produce absurd overlays."""
        engine = ProseEngine()
        buddy = make_buddy(chaos=1)
        absurd_texts = set(WEIRD_OVERLAYS["absurd"])
        random.seed(42)
        for _ in range(100):
            result = engine.thought("idle", buddy)
            assert result not in absurd_texts, f"Low chaos produced absurd overlay: {result}"

    def test_closer_adds_register_flavor(self):
        """Closers should sometimes be appended."""
        engine = ProseEngine()
        buddy = make_buddy(dominant="snark")
        sarcastic_closers = CLOSERS["sarcastic"]
        found_closer = False
        random.seed(42)
        for _ in range(100):
            result = engine.thought("idle", buddy)
            if result and any(c.format(species=buddy.species.name, hat="hat") in result
                             for c in sarcastic_closers):
                found_closer = True
                break
        # 35% chance per call — should find at least one in 100 tries
        assert found_closer, "No closer appended in 100 tries"

    def test_context_injection_adds_flavor(self):
        """Context injection should sometimes add species/mood references."""
        engine = ProseEngine()
        buddy = make_buddy(hat="crown")
        all_context = CONTEXT_SPECIES + CONTEXT_MOOD
        found_injection = False
        random.seed(42)
        for _ in range(200):
            result = engine.thought("edit_storm", buddy, {"count": 5, "minutes": 30})
            if result and any(
                ctx.format(species=buddy.species.name, hat="crown",
                           mood=buddy.mood, count=5, minutes=30)
                in result for ctx in all_context
            ):
                found_injection = True
                break
        assert found_injection, "No context injection in 200 tries"

    def test_all_triggers_produce_output(self):
        """Every trigger pool should produce valid output."""
        engine = ProseEngine()
        buddy = make_buddy()
        for trigger in TEMPLATES:
            ctx = {"count": 3, "minutes": 10, "tool": "Edit", "filename": "test.py",
                   "stage": "Adult", "topic": "testing", "line_count": 50,
                   "function_count": "5", "extension": ".py", "previous_speaker": "Alice"}
            result = engine.thought(trigger, buddy, ctx)
            assert result is not None, f"Trigger '{trigger}' returned None"
            assert len(result) > 0, f"Trigger '{trigger}' returned empty string"
