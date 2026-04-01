"""Tests for the MUD async multiplayer system (Dark Souls-style)."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.games.mud_multiplayer import (
    SoapstoneNote, Bloodstain, Phantom, MudMultiplayerStore,
    TEMPLATES, SUBJECTS, PHANTOM_ACTIONS, PHANTOM_AUTHORS,
    build_note_message, get_template_list, get_subject_list,
    format_note_display, format_bloodstain_display, format_phantom_display,
)
from buddies.core.games.mud_engine import (
    MudState, create_mud_game, process_command, _handle_note, _handle_notes,
    _handle_rate, _handle_bloodstain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_buddy(name="TestBuddy", species_name="phoenix", stats=None) -> BuddyState:
    species = next((s for s in SPECIES_CATALOG if s.name == species_name), SPECIES_CATALOG[0])
    return BuddyState(
        buddy_id=1, species=species, name=name, shiny=False,
        stats=stats or {"debugging": 15, "chaos": 10, "snark": 12, "wisdom": 20, "patience": 18},
        xp=100, level=5, mood="happy", mood_value=70,
        soul_description="A test buddy", hat=None, hats_owned=["tinyduck"],
    )


def _make_game() -> MudState:
    return create_mud_game([_make_buddy()])


# ---------------------------------------------------------------------------
# Template system tests
# ---------------------------------------------------------------------------

class TestTemplateSystem:
    def test_templates_exist(self):
        assert len(TEMPLATES) >= 15

    def test_subjects_exist(self):
        assert len(SUBJECTS) >= 30

    def test_build_note_message(self):
        msg = build_note_message(0, 0)
        assert msg == TEMPLATES[0].format(subject=SUBJECTS[0])

    def test_build_note_message_invalid(self):
        assert build_note_message(-1, 0) == ""
        assert build_note_message(0, -1) == ""
        assert build_note_message(999, 0) == ""

    def test_template_list_format(self):
        lines = get_template_list()
        assert len(lines) == len(TEMPLATES)

    def test_subject_list_format(self):
        lines = get_subject_list()
        assert len(lines) == len(SUBJECTS)


# ---------------------------------------------------------------------------
# SoapstoneNote tests
# ---------------------------------------------------------------------------

class TestSoapstoneNote:
    def test_note_creation(self):
        note = SoapstoneNote(
            id="test_1", room_id="lobby",
            message="Try coffee",
            author_name="Tester", author_emoji="🔥",
        )
        assert note.rating == 0
        assert note.room_id == "lobby"

    def test_note_rating(self):
        note = SoapstoneNote(
            id="test_1", room_id="lobby",
            message="Try coffee",
            author_name="Tester", author_emoji="🔥",
            upvotes=5, downvotes=2,
        )
        assert note.rating == 3

    def test_note_serialization(self):
        note = SoapstoneNote(
            id="test_1", room_id="lobby",
            message="Try coffee",
            author_name="Tester", author_emoji="🔥",
        )
        d = note.to_dict()
        restored = SoapstoneNote.from_dict(d)
        assert restored.id == note.id
        assert restored.message == note.message

    def test_note_rating_text(self):
        note = SoapstoneNote(id="t", room_id="r", message="m", author_name="a", author_emoji="e")
        assert "☆" in note.rating_text  # 0 rating
        note.upvotes = 3
        assert "★" in note.rating_text  # Positive rating


# ---------------------------------------------------------------------------
# Bloodstain tests
# ---------------------------------------------------------------------------

class TestBloodstain:
    def test_bloodstain_creation(self):
        stain = Bloodstain(
            id="death_1", room_id="server_room",
            cause_of_death="Regex Golem",
            buddy_name="Tester", buddy_emoji="🔥", buddy_level=5,
        )
        assert stain.room_id == "server_room"
        assert stain.cause_of_death == "Regex Golem"

    def test_bloodstain_serialization(self):
        stain = Bloodstain(
            id="death_1", room_id="server_room",
            cause_of_death="Dragon",
            buddy_name="Hero", buddy_emoji="⚔️", buddy_level=10,
        )
        d = stain.to_dict()
        restored = Bloodstain.from_dict(d)
        assert restored.cause_of_death == "Dragon"


# ---------------------------------------------------------------------------
# Phantom tests
# ---------------------------------------------------------------------------

class TestPhantom:
    def test_phantom_creation(self):
        p = Phantom(
            room_id="lobby", buddy_name="Ghost",
            buddy_emoji="👻", buddy_species="phoenix",
            action="searching for something",
        )
        assert p.room_id == "lobby"

    def test_phantom_actions_exist(self):
        assert len(PHANTOM_ACTIONS) >= 10

    def test_phantom_authors_exist(self):
        assert len(PHANTOM_AUTHORS) >= 10


# ---------------------------------------------------------------------------
# Display formatting tests
# ---------------------------------------------------------------------------

class TestDisplayFormatting:
    def test_format_note_display(self):
        note = SoapstoneNote(
            id="test", room_id="lobby",
            message="Try coffee",
            author_name="Tester", author_emoji="🔥",
            upvotes=3, downvotes=1,
        )
        text = format_note_display(note)
        assert "Try coffee" in text
        assert "Tester" in text
        assert "📜" in text

    def test_format_bloodstain_display(self):
        stain = Bloodstain(
            id="d1", room_id="lobby",
            cause_of_death="Dragon",
            buddy_name="Hero", buddy_emoji="⚔️", buddy_level=10,
        )
        text = format_bloodstain_display(stain)
        assert "Hero" in text
        assert "Dragon" in text
        assert "💀" in text

    def test_format_phantom_display(self):
        p = Phantom(
            room_id="lobby", buddy_name="Ghost",
            buddy_emoji="👻", buddy_species="phoenix",
            action="debugging",
        )
        text = format_phantom_display(p)
        assert "Ghost" in text
        assert "👻" in text


# ---------------------------------------------------------------------------
# Store tests (uses temp directory)
# ---------------------------------------------------------------------------

class TestMudMultiplayerStore:
    def test_store_seeds_notes(self):
        store = MudMultiplayerStore()
        assert len(store.notes) >= 20  # Seeded phantom notes

    def test_store_seeds_bloodstains(self):
        store = MudMultiplayerStore()
        assert len(store.bloodstains) >= 5

    def test_add_note(self):
        store = MudMultiplayerStore()
        initial = len(store.notes)
        note = SoapstoneNote(
            id="user_test_1", room_id="lobby",
            message="Try debugging",
            author_name="Me", author_emoji="🔥",
        )
        store.add_note(note)
        assert len(store.notes) == initial + 1

    def test_get_notes_for_room(self):
        store = MudMultiplayerStore()
        lobby_notes = store.get_notes_for_room("lobby")
        assert all(n.room_id == "lobby" for n in lobby_notes)

    def test_rate_note(self):
        store = MudMultiplayerStore()
        notes = store.get_notes_for_room("lobby", limit=1)
        if notes:
            note = notes[0]
            old_upvotes = note.upvotes
            store.rate_note(note.id, upvote=True)
            assert note.upvotes == old_upvotes + 1
            # Can't rate twice
            assert not store.rate_note(note.id, upvote=True)

    def test_get_phantom_for_room(self):
        store = MudMultiplayerStore()
        # Add a phantom first
        p = Phantom(room_id="lobby", buddy_name="Ghost", buddy_emoji="👻",
                     buddy_species="phoenix", action="waiting")
        store.add_phantom(p)
        # Should sometimes return a phantom (30% chance)
        found = False
        for _ in range(30):
            result = store.get_phantom_for_room("lobby")
            if result is not None:
                found = True
                break


# ---------------------------------------------------------------------------
# Engine integration tests
# ---------------------------------------------------------------------------

class TestMudMultiplayerIntegration:
    def test_note_without_soapstone(self):
        state = _make_game()
        lines = process_command(state, "note")
        text = "\n".join(lines)
        assert "Orange Soapstone" in text

    def test_note_with_soapstone(self):
        state = _make_game()
        state.inventory.add_item(state.items["orange_soapstone"])
        lines = process_command(state, "note")
        text = "\n".join(lines)
        assert "Template" in text or "template" in text

    def test_note_creation_flow(self):
        state = _make_game()
        state.inventory.add_item(state.items["orange_soapstone"])
        lines = process_command(state, "note 0 2")  # "Try coffee"
        text = "\n".join(lines)
        assert "inscribed" in text.lower() or "message" in text.lower()
        assert state.notes_left == 1

    def test_notes_command(self):
        state = _make_game()
        if state.mp_store:
            lines = process_command(state, "notes")
            # Should show seeded notes or "no notes"
            text = "\n".join(lines)
            assert "note" in text.lower() or "Note" in text

    def test_rate_command(self):
        state = _make_game()
        if state.mp_store:
            # Rate notes in lobby (should have seeded ones)
            lines = process_command(state, "rate")
            text = "\n".join(lines)
            assert "Rate" in text or "no notes" in text.lower()

    def test_bloodstain_command(self):
        state = _make_game()
        if state.mp_store:
            lines = process_command(state, "bloodstain")
            text = "\n".join(lines)
            # Lobby has no bloodstains, but the command should work
            assert "Bloodstain" in text or "fallen" in text.lower() or "No adventurers" in text

    def test_help_includes_multiplayer(self):
        state = _make_game()
        lines = process_command(state, "help")
        text = "\n".join(lines)
        assert "note" in text.lower()
        assert "rate" in text.lower()
        assert "bloodstain" in text.lower()

    def test_room_look_shows_notes(self):
        state = _make_game()
        if state.mp_store:
            # Lobby should have seeded notes
            lines = process_command(state, "look")
            text = "\n".join(lines)
            # May or may not show notes depending on seeding
            # Just verify no crash
            assert "Lobby" in text

    def test_duck_gives_soapstone(self):
        state = _make_game()
        state.current_room = "codebase_ruins"
        lines = process_command(state, "talk rubber duck")
        # Should give orange soapstone
        assert state.inventory.has_item("orange_soapstone")
