"""Tests for CC Companion Dialogue Engine — Tier 4 integration.

Tests the dialogue engine generates proper messages for all modes,
CC buddy speaks with distinct voice, and party reacts appropriately.
"""

import pytest

from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.cc_dialogue import (
    CCDialogueEngine,
    CCDialogueMessage,
    CC_DIALOGUE_OPEN,
    CC_DIALOGUE_TOPIC,
    CC_DIALOGUE_ASK,
    PARTY_REACT_TO_CC,
    PARTY_INTRO_CC,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_buddy(name: str = "TestBuddy", species: str = "duck", **stat_overrides) -> BuddyState:
    species_obj = next((s for s in SPECIES_CATALOG if s.name == species), SPECIES_CATALOG[0])
    stats = {"debugging": 10, "patience": 10, "chaos": 10, "wisdom": 10, "snark": 10}
    stats.update(stat_overrides)
    return BuddyState(
        buddy_id=1,
        species=species_obj,
        name=name,
        shiny=False,
        stats=stats,
        xp=0,
        level=1,
        mood="neutral",
        mood_value=50,
        soul_description="",
        hat=None,
        hats_owned=[],
    )


def _make_cc_buddy(name: str = "CC Buddy") -> BuddyState:
    return _make_buddy(name=name, species="duck")


def _make_party(count: int = 3) -> list[BuddyState]:
    names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    species = ["cat", "owl", "ghost", "dragon", "robot"]
    dominant_stats = [
        {"debugging": 30},
        {"snark": 30},
        {"chaos": 30},
        {"wisdom": 30},
        {"patience": 30},
    ]
    return [
        _make_buddy(name=names[i], species=species[i], **dominant_stats[i])
        for i in range(min(count, 5))
    ]


# ---------------------------------------------------------------------------
# Template pools exist
# ---------------------------------------------------------------------------

class TestTemplatePools:
    def test_cc_open_templates(self):
        assert len(CC_DIALOGUE_OPEN) >= 5

    def test_cc_topic_templates(self):
        assert len(CC_DIALOGUE_TOPIC) >= 5

    def test_cc_ask_templates(self):
        assert len(CC_DIALOGUE_ASK) >= 5

    def test_party_react_all_registers(self):
        for register in ["clinical", "sarcastic", "absurdist", "philosophical", "calm"]:
            assert register in PARTY_REACT_TO_CC
            assert len(PARTY_REACT_TO_CC[register]) >= 3

    def test_party_intro_all_registers(self):
        for register in ["clinical", "sarcastic", "absurdist", "philosophical", "calm"]:
            assert register in PARTY_INTRO_CC
            assert len(PARTY_INTRO_CC[register]) >= 1

    def test_topic_templates_have_placeholder(self):
        for tmpl in CC_DIALOGUE_TOPIC:
            assert "{topic}" in tmpl

    def test_react_templates_have_cc_name(self):
        for register, templates in PARTY_REACT_TO_CC.items():
            for tmpl in templates:
                assert "{cc_name}" in tmpl


# ---------------------------------------------------------------------------
# Open chat mode
# ---------------------------------------------------------------------------

class TestOpenChat:
    def test_generates_messages(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(2)
        messages = engine.open_chat(cc, party)
        assert len(messages) >= 3  # intro + CC + at least 1 reaction

    def test_cc_buddy_speaks(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("Inkwell")
        party = _make_party(1)
        messages = engine.open_chat(cc, party)
        cc_messages = [m for m in messages if m.is_cc_buddy]
        assert len(cc_messages) >= 1
        assert cc_messages[0].buddy_name == "Inkwell"

    def test_cc_message_marked(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(1)
        messages = engine.open_chat(cc, party)
        cc_msgs = [m for m in messages if m.is_cc_buddy]
        non_cc = [m for m in messages if not m.is_cc_buddy]
        assert len(cc_msgs) >= 1
        assert len(non_cc) >= 1

    def test_party_intro_present(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("TestCC")
        party = _make_party(2)
        messages = engine.open_chat(cc, party)
        # First message should be from a party buddy (introduction)
        assert not messages[0].is_cc_buddy

    def test_empty_party(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        messages = engine.open_chat(cc, [])
        # Should still have CC speaking
        assert any(m.is_cc_buddy for m in messages)

    def test_cc_register_is_official(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(1)
        messages = engine.open_chat(cc, party)
        cc_msg = next(m for m in messages if m.is_cc_buddy)
        assert cc_msg.register == "official"


# ---------------------------------------------------------------------------
# Guided topic mode
# ---------------------------------------------------------------------------

class TestGuidedTopic:
    def test_generates_messages(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(2)
        messages = engine.guided_topic(cc, party, "refactoring")
        assert len(messages) >= 2

    def test_cc_mentions_topic(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(1)
        messages = engine.guided_topic(cc, party, "testing")
        cc_msg = next(m for m in messages if m.is_cc_buddy)
        assert "testing" in cc_msg.message.lower()

    def test_party_reacts(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(3)
        messages = engine.guided_topic(cc, party, "CI/CD")
        party_msgs = [m for m in messages if not m.is_cc_buddy]
        assert len(party_msgs) >= 1


# ---------------------------------------------------------------------------
# Ask CC mode
# ---------------------------------------------------------------------------

class TestAskCC:
    def test_generates_messages(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(2)
        messages = engine.ask_cc(cc, party, "What's a monad?")
        assert len(messages) >= 2

    def test_party_asks_question(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("Inkwell")
        party = _make_party(1)
        messages = engine.ask_cc(cc, party, "How do tests work?")
        # First message should be the asker
        assert not messages[0].is_cc_buddy
        assert "Inkwell" in messages[0].message

    def test_cc_responds(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        party = _make_party(1)
        messages = engine.ask_cc(cc, party, "Why Python?")
        cc_msgs = [m for m in messages if m.is_cc_buddy]
        assert len(cc_msgs) >= 1

    def test_empty_party_ask(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy()
        messages = engine.ask_cc(cc, [], "Hello?")
        assert any(m.is_cc_buddy for m in messages)


# ---------------------------------------------------------------------------
# Message dataclass
# ---------------------------------------------------------------------------

class TestCCDialogueMessage:
    def test_default_not_cc(self):
        msg = CCDialogueMessage(
            buddy_name="Test",
            species_emoji="🐱",
            rarity="common",
            register="calm",
            message="Hello",
        )
        assert not msg.is_cc_buddy

    def test_cc_flag(self):
        msg = CCDialogueMessage(
            buddy_name="CC",
            species_emoji="🦆",
            rarity="common",
            register="official",
            message="Hi",
            is_cc_buddy=True,
        )
        assert msg.is_cc_buddy


# ---------------------------------------------------------------------------
# Personality-driven reactions
# ---------------------------------------------------------------------------

class TestPersonalityReactions:
    def test_clinical_buddy_reacts(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("CC")
        party = [_make_buddy("Doc", debugging=50)]
        messages = engine.open_chat(cc, party)
        party_msgs = [m for m in messages if not m.is_cc_buddy]
        # At least one party message should exist
        assert len(party_msgs) >= 1

    def test_sarcastic_buddy_reacts(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("CC")
        party = [_make_buddy("Snarky", snark=50)]
        messages = engine.open_chat(cc, party)
        assert any(not m.is_cc_buddy for m in messages)

    def test_multiple_registers(self):
        engine = CCDialogueEngine()
        cc = _make_cc_buddy("CC")
        party = _make_party(5)  # Each with a different dominant stat
        messages = engine.open_chat(cc, party)
        registers = {m.register for m in messages if not m.is_cc_buddy}
        # Should have at least 2 different registers
        assert len(registers) >= 2
