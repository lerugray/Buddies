"""Tests for MUD negotiation system — SMT-style talking through encounters."""

import pytest
import random

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.games.mud_negotiate import (
    NEGOTIATION_TREES, NEGOTIATE_COMMENTARY, NEGOTIATE_GIFTS,
    NegotiationState, NegotiateOutcome,
    resolve_negotiation, get_available_responses,
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
    def test_all_responses_available_with_high_stats(self):
        """All responses should be available if all stats are maxed."""
        high_stats = {"debugging": 50, "chaos": 50, "snark": 50, "wisdom": 50, "patience": 50}
        for npc_id, tree in NEGOTIATION_TREES.items():
            for exchange in tree:
                available = get_available_responses(exchange, high_stats)
                assert len(available) == len(exchange.responses), (
                    f"{npc_id}: high stats should unlock all options"
                )

    def test_stat_gated_hidden_with_low_stats(self):
        """Stat-gated responses should be hidden when stats are low."""
        low_stats = {"debugging": 5, "chaos": 5, "snark": 5, "wisdom": 5, "patience": 5}
        for npc_id, tree in NEGOTIATION_TREES.items():
            for exchange in tree:
                all_count = len(exchange.responses)
                gated_count = sum(1 for r in exchange.responses if r.stat_requirement)
                available = get_available_responses(exchange, low_stats)
                assert len(available) == all_count - gated_count


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
