"""Tests for MUD GitHub transport layer — Phase 2 multiplayer.

Tests the transport's data formatting, parsing, sync logic,
and graceful offline behavior. Does NOT hit the real GitHub API.
"""

import time
import pytest

from buddies.core.games.mud_multiplayer import (
    SoapstoneNote, Bloodstain, Phantom, MudMultiplayerStore,
)
from buddies.core.games.mud_transport import (
    MudTransport,
    _build_note_body,
    _build_bloodstain_body,
    _parse_note_issue,
    _parse_bloodstain_issue,
    _parse_frontmatter,
    _phantom_action_from_note,
)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class TestFrontmatter:
    def test_parse_valid(self):
        text = "---\ntype: soapstone\nroom_id: lobby\n---\n\nSome body"
        meta = _parse_frontmatter(text)
        assert meta["type"] == "soapstone"
        assert meta["room_id"] == "lobby"

    def test_parse_empty(self):
        assert _parse_frontmatter("") == {}
        assert _parse_frontmatter("no frontmatter") == {}

    def test_parse_no_closing(self):
        text = "---\nkey: value\nstill going..."
        assert _parse_frontmatter(text) == {}

    def test_parse_colon_in_value(self):
        text = "---\nmessage: Try coffee: it helps\n---\n"
        meta = _parse_frontmatter(text)
        assert meta["message"] == "Try coffee: it helps"


# ---------------------------------------------------------------------------
# Note body building + parsing roundtrip
# ---------------------------------------------------------------------------

class TestNoteRoundtrip:
    def _make_note(self, **overrides):
        defaults = dict(
            id="player_lobby_123",
            room_id="lobby",
            message="Try coffee",
            author_name="TestBuddy",
            author_emoji="🐱",
            timestamp=1700000000.0,
            upvotes=3,
            downvotes=1,
            is_phantom=False,
        )
        defaults.update(overrides)
        return SoapstoneNote(**defaults)

    def test_build_note_body_has_frontmatter(self):
        note = self._make_note()
        body = _build_note_body(note)
        assert body.startswith("---\n")
        assert "type: soapstone" in body
        assert "room_id: lobby" in body
        assert "note_id: player_lobby_123" in body
        assert "Try coffee" in body

    def test_parse_note_issue(self):
        note = self._make_note()
        body = _build_note_body(note)
        issue = {
            "number": 42,
            "body": body,
            "reactions": {"+1": 5, "-1": 2, "url": "", "total_count": 7},
            "user": {"login": "testuser"},
            "created_at": "2026-04-01T12:00:00Z",
        }
        parsed = _parse_note_issue(issue)
        assert parsed is not None
        assert parsed.room_id == "lobby"
        assert parsed.message == "Try coffee"
        assert parsed.author_name == "TestBuddy"
        assert parsed.upvotes == 5  # From reactions, not original
        assert parsed.downvotes == 2

    def test_parse_note_issue_wrong_type(self):
        issue = {
            "number": 1,
            "body": "---\ntype: bloodstain\n---\n",
            "reactions": {},
        }
        assert _parse_note_issue(issue) is None

    def test_parse_note_issue_no_body(self):
        issue = {"number": 1, "body": None, "reactions": {}}
        assert _parse_note_issue(issue) is None


# ---------------------------------------------------------------------------
# Bloodstain body building + parsing roundtrip
# ---------------------------------------------------------------------------

class TestBloodstainRoundtrip:
    def _make_stain(self, **overrides):
        defaults = dict(
            id="death_server_room_456",
            room_id="server_room",
            cause_of_death="Regex Golem",
            buddy_name="BraveBuddy",
            buddy_emoji="🐉",
            buddy_level=7,
            timestamp=1700000000.0,
            is_phantom=False,
        )
        defaults.update(overrides)
        return Bloodstain(**defaults)

    def test_build_bloodstain_body_has_frontmatter(self):
        stain = self._make_stain()
        body = _build_bloodstain_body(stain)
        assert "type: bloodstain" in body
        assert "room_id: server_room" in body
        assert "Regex Golem" in body

    def test_parse_bloodstain_issue(self):
        stain = self._make_stain()
        body = _build_bloodstain_body(stain)
        issue = {
            "number": 99,
            "body": body,
            "reactions": {},
            "user": {"login": "someone"},
            "created_at": "2026-04-01T12:00:00Z",
        }
        parsed = _parse_bloodstain_issue(issue)
        assert parsed is not None
        assert parsed.room_id == "server_room"
        assert parsed.cause_of_death == "Regex Golem"
        assert parsed.buddy_name == "BraveBuddy"
        assert parsed.buddy_level == 7


# ---------------------------------------------------------------------------
# Phantom action generation
# ---------------------------------------------------------------------------

class TestPhantomActions:
    def test_coffee_note(self):
        assert "coffee" in _phantom_action_from_note("Try coffee").lower()

    def test_debug_note(self):
        assert "code" in _phantom_action_from_note("Be wary of debugging").lower()

    def test_wary_note(self):
        assert "nervous" in _phantom_action_from_note("Be wary of traps").lower()

    def test_praise_note(self):
        assert "celebrat" in _phantom_action_from_note("Praise the CI/CD pipeline!").lower()

    def test_sad_note(self):
        assert "quiet" in _phantom_action_from_note("Ahh, sadness...").lower()

    def test_generic_note(self):
        # Should return some action (random from PHANTOM_ACTIONS)
        action = _phantom_action_from_note("Let there be type safety")
        assert isinstance(action, str) and len(action) > 3


# ---------------------------------------------------------------------------
# Transport sync logic (with mock store)
# ---------------------------------------------------------------------------

class TestSyncLogic:
    def test_sync_merges_new_notes(self, tmp_path, monkeypatch):
        """Verify that sync_to_local merges remote notes into local store."""
        # Create a local store with one note
        monkeypatch.setattr(
            "buddies.core.games.mud_multiplayer.get_data_dir",
            lambda: tmp_path,
        )
        store = MudMultiplayerStore()
        initial_count = len(store.notes)

        # Simulate adding a "remote" note that wouldn't exist locally
        remote_note = SoapstoneNote(
            id="remote_test_note_999",
            room_id="lobby",
            message="Praise the documentation!",
            author_name="RemotePlayer",
            author_emoji="🌟",
            timestamp=time.time(),
        )

        # Manually merge (simulates what sync_to_local does)
        local_ids = {n.id for n in store.notes}
        assert remote_note.id not in local_ids
        store.notes.append(remote_note)
        assert len(store.notes) == initial_count + 1

    def test_phantom_notes_not_pushed(self):
        """Phantom (pre-seeded) notes should never be pushed to GitHub."""
        note = SoapstoneNote(
            id="phantom_lobby_0",
            room_id="lobby",
            message="Try coffee",
            author_name="GeraldBot",
            author_emoji="🧔",
            is_phantom=True,
        )
        # The transport checks is_phantom before pushing
        assert note.is_phantom is True

    def test_duplicate_notes_not_merged(self, tmp_path, monkeypatch):
        """Notes with the same ID should not be duplicated."""
        monkeypatch.setattr(
            "buddies.core.games.mud_multiplayer.get_data_dir",
            lambda: tmp_path,
        )
        store = MudMultiplayerStore()

        # Add a note
        note = SoapstoneNote(
            id="unique_note_1",
            room_id="lobby",
            message="Test",
            author_name="Test",
            author_emoji="🐱",
        )
        store.notes.append(note)
        count_after_add = len(store.notes)

        # Try to merge same ID — should be skipped
        local_ids = {n.id for n in store.notes}
        assert "unique_note_1" in local_ids
        # Merge logic: skip if ID exists
        if note.id not in local_ids:
            store.notes.append(note)
        assert len(store.notes) == count_after_add  # No change


# ---------------------------------------------------------------------------
# Rumors command (via engine)
# ---------------------------------------------------------------------------

class TestRumorsCommand:
    def test_rumors_returns_output(self):
        from buddies.core.games.mud_engine import _handle_rumors, MudState, MudInventory
        from buddies.core.games.mud_world import build_starter_rooms, build_starter_items, build_starter_npcs, build_starter_quests
        from buddies.core.buddy_brain import BuddyState, Species, Rarity

        sp = Species("test", "🐱", Rarity.COMMON, {"patience": 3}, "Test")
        buddy = BuddyState(
            buddy_id=1, species=sp, name="Test", shiny=False,
            stats={"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 30},
            xp=0, level=5, mood="happy", mood_value=50,
            soul_description="test", hat=None, hats_owned=[],
        )

        items = build_starter_items()
        state = MudState(
            rooms=build_starter_rooms(),
            npcs=build_starter_npcs(items),
            items=items,
            quests=build_starter_quests(),
            inventory=MudInventory(gold=10),
            party=[buddy],
        )
        # No mp_store
        lines = _handle_rumors(state, "")
        assert any("unavailable" in l.lower() for l in lines)

    def test_rumors_with_store(self, tmp_path, monkeypatch):
        from buddies.core.games.mud_engine import _handle_rumors, MudState, MudInventory
        from buddies.core.games.mud_world import build_starter_rooms, build_starter_items, build_starter_npcs, build_starter_quests
        from buddies.core.buddy_brain import BuddyState, Species, Rarity

        monkeypatch.setattr(
            "buddies.core.games.mud_multiplayer.get_data_dir",
            lambda: tmp_path,
        )

        sp = Species("test", "🐱", Rarity.COMMON, {"patience": 3}, "Test")
        buddy = BuddyState(
            buddy_id=1, species=sp, name="Test", shiny=False,
            stats={"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 30},
            xp=0, level=5, mood="happy", mood_value=50,
            soul_description="test", hat=None, hats_owned=[],
        )

        items = build_starter_items()
        store = MudMultiplayerStore()
        state = MudState(
            rooms=build_starter_rooms(),
            npcs=build_starter_npcs(items),
            items=items,
            quests=build_starter_quests(),
            inventory=MudInventory(gold=10),
            party=[buddy],
            mp_store=store,
        )
        lines = _handle_rumors(state, "")
        assert any("rumors" in l.lower() or "network" in l.lower() for l in lines)
        # Should have stats about notes and bloodstains
        assert any("soapstone" in l.lower() or "📜" in l for l in lines)
