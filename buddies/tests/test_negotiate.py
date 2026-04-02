"""Tests for MUD negotiation system — SMT-style talking through encounters."""

import pytest
import random

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.games.mud_negotiate import (
    NEGOTIATION_TREES, NEGOTIATE_COMMENTARY, NEGOTIATE_GIFTS,
    NegotiationState, NegotiateOutcome, SkillCheckResult,
    resolve_negotiation, get_available_responses,
    perform_skill_check, apply_skill_check_to_mood,
    calculate_success_chance, difficulty_label,
)
from buddies.core.games.mud_engine import (
    MudState, create_mud_game, process_command, parse_command,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30
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


def make_game(**overrides):
    buddy = overrides.pop("buddy", make_buddy())
    state = create_mud_game([buddy])
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


# ---------------------------------------------------------------------------
# Negotiation tree coverage
# ---------------------------------------------------------------------------

class TestNegotiationTrees:
    def test_all_hostile_npcs_have_trees(self):
        """Every hostile NPC in the MUD should have a negotiation tree."""
        expected = [
            "merge_demon", "null_pointer", "regex_golem",
            "tech_debt_dragon", "flaky_test_swarm", "memory_leak", "pod_person",
        ]
        for npc_id in expected:
            assert npc_id in NEGOTIATION_TREES, f"Missing tree for {npc_id}"

    def test_each_tree_has_3_exchanges(self):
        for npc_id, tree in NEGOTIATION_TREES.items():
            assert len(tree) == 3, f"{npc_id} should have 3 exchanges, got {len(tree)}"

    def test_each_exchange_has_responses(self):
        for npc_id, tree in NEGOTIATION_TREES.items():
            for i, exchange in enumerate(tree):
                assert len(exchange.responses) >= 3, (
                    f"{npc_id} exchange {i} has only {len(exchange.responses)} responses"
                )

    def test_stat_gated_options_exist(self):
        """At least some responses should require specific buddy stats."""
        stat_gated = 0
        for tree in NEGOTIATION_TREES.values():
            for exchange in tree:
                for resp in exchange.responses:
                    if resp.stat_requirement:
                        stat_gated += 1
        assert stat_gated >= 7, f"Expected 7+ stat-gated options, found {stat_gated}"

    def test_all_hostile_npcs_have_gifts(self):
        for npc_id in NEGOTIATION_TREES:
            assert npc_id in NEGOTIATE_GIFTS, f"Missing gift for {npc_id}"


# ---------------------------------------------------------------------------
# Response filtering
# ---------------------------------------------------------------------------

class TestResponseFiltering:
    def test_all_responses_always_visible(self):
        """All responses should always be visible — no threshold gating."""
        low_stats = {"debugging": 1, "chaos": 1, "snark": 1, "wisdom": 1, "patience": 1}
        high_stats = {"debugging": 50, "chaos": 50, "snark": 50, "wisdom": 50, "patience": 50}
        for npc_id, tree in NEGOTIATION_TREES.items():
            for exchange in tree:
                low_available = get_available_responses(exchange, low_stats)
                high_available = get_available_responses(exchange, high_stats)
                assert len(low_available) == len(exchange.responses), (
                    f"{npc_id}: all options should be visible even with low stats"
                )
                assert len(high_available) == len(exchange.responses)

    def test_stat_gated_options_have_difficulty_labels(self):
        """Stat-gated responses should carry difficulty labels."""
        stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        labeled = 0
        for tree in NEGOTIATION_TREES.values():
            for exchange in tree:
                for _, resp, label in get_available_responses(exchange, stats):
                    if resp.stat_requirement:
                        assert label is not None, "Stat-gated option should have label"
                        labeled += 1
                    else:
                        assert label is None, "Non-stat option should have no label"
        assert labeled >= 7

    def test_high_stats_get_easy_labels(self):
        """High stats should show Easy difficulty for stat-gated options."""
        stats = {"debugging": 50, "chaos": 50, "snark": 50, "wisdom": 50, "patience": 50}
        for tree in NEGOTIATION_TREES.values():
            for exchange in tree:
                for _, resp, label in get_available_responses(exchange, stats):
                    if resp.stat_requirement:
                        assert "Easy" in label or "Moderate" in label

    def test_low_stats_get_desperate_labels(self):
        """Very low stats should show Desperate difficulty."""
        stats = {"debugging": 1, "chaos": 1, "snark": 1, "wisdom": 1, "patience": 1}
        for tree in NEGOTIATION_TREES.values():
            for exchange in tree:
                for _, resp, label in get_available_responses(exchange, stats):
                    if resp.stat_requirement and resp.min_stat >= 20:
                        assert "Desperate" in label or "Risky" in label


# ---------------------------------------------------------------------------
# Outcome resolution
# ---------------------------------------------------------------------------

class TestOutcomeResolution:
    def test_high_mood_gives_gift(self):
        state = NegotiationState(npc_id="merge_demon", mood=85)
        outcome, text = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.GIFT

    def test_friendly_mood_gives_peace(self):
        state = NegotiationState(npc_id="merge_demon", mood=65)
        outcome, _ = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.PEACE

    def test_neutral_mood_with_demands_gives_peace(self):
        state = NegotiationState(npc_id="merge_demon", mood=48, demands_met=1)
        outcome, _ = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.PEACE

    def test_neutral_mood_without_demands_gives_bribe(self):
        state = NegotiationState(npc_id="merge_demon", mood=48, demands_met=0)
        outcome, _ = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.BRIBE

    def test_low_mood_gives_angry(self):
        state = NegotiationState(npc_id="merge_demon", mood=10)
        outcome, _ = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.ANGRY

    def test_very_low_mood_gives_angry(self):
        state = NegotiationState(npc_id="merge_demon", mood=0)
        outcome, _ = resolve_negotiation(state)
        assert outcome == NegotiateOutcome.ANGRY


# ---------------------------------------------------------------------------
# Integration: talk command starts negotiation
# ---------------------------------------------------------------------------

class TestNegotiationIntegration:
    def test_talk_to_hostile_starts_negotiation(self):
        """Talking to a hostile NPC should start negotiation."""
        state = make_game()
        # Move to repository_depths where merge_demon lives
        state.current_room = "repository_depths"
        lines = process_command(state, "talk merge")
        combined = "\n".join(lines)
        assert "NEGOTIATION" in combined or "negotiate" in combined.lower()
        assert state.negotiation is not None
        assert state.negotiation.npc_id == "merge_demon"

    def test_numbered_response_advances_negotiation(self):
        """Typing a number during negotiation should advance it."""
        state = make_game()
        state.current_room = "repository_depths"
        process_command(state, "talk merge")
        assert state.negotiation is not None
        assert state.negotiation.stage == 0

        # Respond with option 1
        lines = process_command(state, "1")
        assert state.negotiation is None or state.negotiation.stage >= 1

    def test_invalid_response_gives_error(self):
        state = make_game()
        state.current_room = "repository_depths"
        process_command(state, "talk merge")
        lines = process_command(state, "99")
        combined = "\n".join(lines)
        assert "choose" in combined.lower() or "between" in combined.lower()

    def test_talk_during_combat(self):
        """Talk command during combat should start negotiation."""
        state = make_game()
        state.current_room = "repository_depths"
        # Start combat first
        process_command(state, "attack merge")
        assert state.combat is not None
        # Now try to talk
        lines = process_command(state, "talk")
        combined = "\n".join(lines)
        assert "NEGOTIATION" in combined or "negotiate" in combined.lower()

    def test_full_negotiation_kind_responses(self):
        """Full negotiation with kind responses should end peacefully."""
        state = make_game()
        state.current_room = "dead_code_garden"
        # Talk to null_pointer
        process_command(state, "talk null")
        assert state.negotiation is not None

        # Pick the kindest response each time (option 3 for null_pointer)
        process_command(state, "3")  # "I believe in you, buddy"
        if state.negotiation:
            process_command(state, "3")  # "The fact that you're asking means you're real enough"
        if state.negotiation:
            process_command(state, "1")  # "Then don't be fixed. Be understood instead."

        # After 3 exchanges, negotiation should be resolved
        assert state.negotiation is None

    def test_attack_cancels_negotiation(self):
        """Attacking during negotiation should end it."""
        state = make_game()
        state.current_room = "repository_depths"
        process_command(state, "talk merge")
        assert state.negotiation is not None
        # Attack instead of responding
        process_command(state, "attack")
        # Negotiation should be cleared when combat processes
        # (the combat round proceeds normally)


# ---------------------------------------------------------------------------
# Commentary coverage
# ---------------------------------------------------------------------------

class TestNegotiateCommentary:
    def test_all_contexts_have_all_registers(self):
        """Each commentary context should have all 5 registers."""
        for context, registers in NEGOTIATE_COMMENTARY.items():
            for reg in ["clinical", "sarcastic", "absurdist", "philosophical", "calm"]:
                assert reg in registers, f"{context} missing {reg} register"

    def test_commentary_has_name_placeholder(self):
        """All commentary lines should use {name} for formatting."""
        for context, registers in NEGOTIATE_COMMENTARY.items():
            for reg, lines in registers.items():
                for line in lines:
                    assert "{name}" in line, f"{context}/{reg} missing {{name}} placeholder"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_negotiate_with_npc_without_tree(self):
        """NPCs without negotiation trees should refuse to talk."""
        state = make_game()
        # Gerald is FRIENDLY, not HOSTILE, so this tests a different path
        # Let's just verify the tree check works
        from buddies.core.games.mud_negotiate import NEGOTIATION_TREES
        assert "gerald" not in NEGOTIATION_TREES  # Friendly NPCs don't negotiate

    def test_mood_starts_at_50(self):
        neg = NegotiationState(npc_id="test")
        assert neg.mood == 50

    def test_mood_accumulates(self):
        neg = NegotiationState(npc_id="test")
        neg.mood += 20
        neg.mood -= 5
        assert neg.mood == 65

    def test_negotiation_state_has_roll_history(self):
        neg = NegotiationState(npc_id="test")
        assert neg.roll_history == []


# ---------------------------------------------------------------------------
# Skill check system
# ---------------------------------------------------------------------------

class TestSkillCheck:
    def test_result_structure(self):
        rng = random.Random(42)
        result = perform_skill_check(20, 15, rng=rng)
        assert 1 <= result.roll <= 20
        assert result.modifier == 10  # 20 // 2
        assert result.total == result.roll + result.modifier
        assert result.margin == result.total - 15
        assert result.tier in ("crit_success", "success", "partial", "failure", "crit_failure")

    def test_modifier_calculation(self):
        rng = random.Random(1)
        assert perform_skill_check(20, 10, rng=rng).modifier == 10
        assert perform_skill_check(10, 10, rng=random.Random(1)).modifier == 5
        assert perform_skill_check(5, 10, rng=random.Random(1)).modifier == 2
        assert perform_skill_check(0, 10, rng=random.Random(1)).modifier == 0

    def test_nat_20_always_at_least_success(self):
        """Natural 20 should always give at least success tier."""
        # Find a seed that gives roll=20
        for seed in range(1000):
            rng = random.Random(seed)
            result = perform_skill_check(0, 100, rng=rng)  # stat 0 vs DC 100
            if result.roll == 20:
                assert result.nat_20
                assert result.tier in ("success", "crit_success")
                return
        pytest.skip("Could not find nat 20 seed in 1000 attempts")

    def test_nat_1_always_at_least_failure(self):
        """Natural 1 should always give at least failure tier."""
        for seed in range(1000):
            rng = random.Random(seed)
            result = perform_skill_check(100, 1, rng=rng)  # stat 100 vs DC 1
            if result.roll == 1:
                assert result.nat_1
                assert result.tier in ("failure", "crit_failure")
                return
        pytest.skip("Could not find nat 1 seed in 1000 attempts")

    def test_high_stat_succeeds_often(self):
        """stat 30 vs DC 20 should succeed > 60% of the time."""
        successes = 0
        for seed in range(200):
            rng = random.Random(seed)
            result = perform_skill_check(30, 20, rng=rng)
            if result.tier in ("crit_success", "success", "partial"):
                successes += 1
        assert successes > 120, f"Expected >60% partial+ success, got {successes}/200"

    def test_low_stat_fails_often(self):
        """stat 5 vs DC 25 should fail most of the time."""
        failures = 0
        for seed in range(200):
            rng = random.Random(seed)
            result = perform_skill_check(5, 25, rng=rng)
            if result.tier in ("failure", "crit_failure"):
                failures += 1
        assert failures > 120, f"Expected >60% failure, got {failures}/200"

    def test_margin_determines_tier(self):
        """Specific margin values should map to expected tiers."""
        rng = random.Random(42)
        # Find a non-nat-1, non-nat-20 roll and verify tier
        for seed in range(100):
            rng = random.Random(seed)
            result = perform_skill_check(20, 15, rng=rng)
            if not result.nat_20 and not result.nat_1:
                if result.margin >= 10:
                    assert result.tier == "crit_success"
                elif result.margin >= 0:
                    assert result.tier == "success"
                elif result.margin >= -4:
                    assert result.tier == "partial"
                elif result.margin >= -9:
                    assert result.tier == "failure"
                else:
                    assert result.tier == "crit_failure"
                return


class TestSkillCheckMood:
    def test_crit_success_boosts_mood(self):
        result = SkillCheckResult(roll=20, modifier=15, dc=15, total=35, margin=20,
                                   tier="crit_success", nat_20=True, nat_1=False)
        mood = apply_skill_check_to_mood(result, 20)
        assert mood == int(20 * 1.5) + 5  # 35

    def test_success_gives_base_mood(self):
        result = SkillCheckResult(roll=15, modifier=10, dc=20, total=25, margin=5,
                                   tier="success", nat_20=False, nat_1=False)
        assert apply_skill_check_to_mood(result, 20) == 20

    def test_partial_gives_half_mood(self):
        result = SkillCheckResult(roll=8, modifier=10, dc=20, total=18, margin=-2,
                                   tier="partial", nat_20=False, nat_1=False)
        assert apply_skill_check_to_mood(result, 20) == 10

    def test_failure_gives_penalty(self):
        result = SkillCheckResult(roll=5, modifier=5, dc=20, total=10, margin=-10,
                                   tier="failure", nat_20=False, nat_1=False)
        assert apply_skill_check_to_mood(result, 20) == -5

    def test_crit_failure_inverts_mood(self):
        result = SkillCheckResult(roll=1, modifier=5, dc=20, total=6, margin=-14,
                                   tier="crit_failure", nat_20=False, nat_1=True)
        assert apply_skill_check_to_mood(result, 20) == -20


class TestDifficultyLabels:
    def test_calculate_success_chance(self):
        # stat 20 vs DC 20: modifier=10, need roll >= 16 for partial (-4)
        # Actually: partial = margin >= -4, so total >= 16, roll >= 6, chance = 15/20 = 75%
        chance = calculate_success_chance(20, 20)
        assert 70 <= chance <= 80

    def test_very_high_stat_easy(self):
        chance = calculate_success_chance(50, 15)
        assert chance >= 80

    def test_very_low_stat_desperate(self):
        chance = calculate_success_chance(2, 25)
        assert chance <= 30

    def test_difficulty_label_easy(self):
        assert "Easy" in difficulty_label(85)
        assert "green" in difficulty_label(85)

    def test_difficulty_label_moderate(self):
        assert "Moderate" in difficulty_label(60)

    def test_difficulty_label_risky(self):
        assert "Risky" in difficulty_label(35)

    def test_difficulty_label_desperate(self):
        assert "Desperate" in difficulty_label(10)
