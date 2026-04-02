"""Tests for the MUD save/load system."""

import json
import pytest

from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.games.mud_engine import create_mud_game, process_command
from buddies.core.games.mud_save import (
    save_mud_state, load_mud_state, has_save, list_saves, delete_save,
    _save_dir, _save_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_buddy():
    species = SPECIES_CATALOG[0]
    return BuddyState(
        buddy_id=1, species=species, name="Test",
        shiny=False, stats={"debugging": 15, "chaos": 10, "snark": 12, "wisdom": 20, "patience": 18},
        xp=100, level=5, mood="happy", mood_value=70,
        soul_description="test", hat=None, hats_owned=["tinyduck"],
    )


def _make_game():
    return create_mud_game([_make_buddy()])


@pytest.fixture(autouse=True)
def _redirect_saves(tmp_path, monkeypatch):
    """Redirect all save operations to a temp directory."""
    monkeypatch.setattr("buddies.core.games.mud_save.get_data_dir", lambda: tmp_path)


# ---------------------------------------------------------------------------
# Basic save/load tests
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_save_and_load_roundtrip(self):
        state = _make_game()
        # Modify state
        state.current_room = "town_square"
        state.inventory.gold = 42
        state.rooms_visited = 5
        state.turns = 10
        assert save_mud_state(state)

        # Create fresh game and load
        state2 = _make_game()
        assert load_mud_state(state2)
        assert state2.current_room == "town_square"
        assert state2.inventory.gold == 42
        assert state2.rooms_visited == 5
        assert state2.turns == 10

    def test_save_creates_file(self, tmp_path):
        state = _make_game()
        save_mud_state(state)
        save_file = tmp_path / "mud_saves" / "auto.json"
        assert save_file.exists()

    def test_has_save_false(self):
        assert not has_save()

    def test_has_save_true(self):
        state = _make_game()
        save_mud_state(state)
        assert has_save()

    def test_delete_save(self):
        state = _make_game()
        save_mud_state(state)
        assert has_save()
        assert delete_save()
        assert not has_save()

    def test_delete_save_missing(self):
        assert not delete_save()

    def test_list_saves_empty(self):
        assert list_saves() == []

    def test_list_saves_with_data(self):
        state = _make_game()
        save_mud_state(state)
        saves = list_saves()
        assert len(saves) == 1
        assert saves[0]["slot"] == "auto"
        assert "timestamp" in saves[0]


# ---------------------------------------------------------------------------
# State preservation tests
# ---------------------------------------------------------------------------

class TestStatePreservation:
    def test_load_preserves_inventory(self):
        state = _make_game()
        state.inventory.gold = 999
        # Add an item to inventory
        item = state.items.get("rubber_duck")
        if item:
            state.inventory.add_item(item)
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.inventory.gold == 999
        if item:
            assert state2.inventory.has_item("rubber_duck")

    def test_load_preserves_room_position(self):
        state = _make_game()
        state.current_room = "break_room"
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.current_room == "break_room"

    def test_load_preserves_quest_progress(self):
        state = _make_game()
        # Start a quest by talking to Gerald
        state.current_room = "town_square"
        process_command(state, "talk gerald")
        from buddies.core.games.mud_world import QuestStatus
        assert state.quests["fix_pipeline"].status == QuestStatus.ACTIVE
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.quests["fix_pipeline"].status == QuestStatus.ACTIVE

    def test_load_preserves_npc_state(self):
        state = _make_game()
        # Mark an NPC as talked to
        state.npcs["sysadmin"].talked_to = True
        state.npcs["sysadmin"].defeated = False
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.npcs["sysadmin"].talked_to is True

    def test_load_preserves_stats(self):
        state = _make_game()
        state.rooms_visited = 7
        state.npcs_talked = 3
        state.npcs_defeated = 2
        state.items_collected = 5
        state.quests_completed = 1
        state.gold_earned = 100
        state.gold_spent = 50
        state.turns = 42
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.rooms_visited == 7
        assert state2.npcs_talked == 3
        assert state2.npcs_defeated == 2
        assert state2.items_collected == 5
        assert state2.quests_completed == 1
        assert state2.gold_earned == 100
        assert state2.gold_spent == 50
        assert state2.turns == 42

    def test_load_preserves_unlocked_exits(self):
        state = _make_game()
        state.current_room = "town_square"
        # Give VPN token to unlock cloud district
        vpn = state.items["vpn_token"]
        state.inventory.add_item(vpn)
        process_command(state, "go up")
        assert state.current_room == "cloud_district"
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        # The exit from town_square up should now be unlocked
        room = state2.rooms["town_square"]
        up_exit = next(ex for ex in room.exits if ex.direction == "up")
        assert not up_exit.locked

    def test_load_preserves_visited_rooms(self):
        state = _make_game()
        state.rooms["lobby"].visited = True
        state.rooms["town_square"].visited = True
        save_mud_state(state)

        state2 = _make_game()
        load_mud_state(state2)
        assert state2.rooms["lobby"].visited is True
        assert state2.rooms["town_square"].visited is True


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_load_invalid_json(self, tmp_path):
        save_dir = tmp_path / "mud_saves"
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "auto.json").write_text("not valid json {{{", encoding="utf-8")
        state = _make_game()
        assert not load_mud_state(state)

    def test_load_bad_version(self, tmp_path):
        save_dir = tmp_path / "mud_saves"
        save_dir.mkdir(parents=True, exist_ok=True)
        data = {"version": 0, "current_room": "lobby"}
        (save_dir / "auto.json").write_text(json.dumps(data), encoding="utf-8")
        state = _make_game()
        assert not load_mud_state(state)


# ---------------------------------------------------------------------------
# Command integration tests
# ---------------------------------------------------------------------------

class TestSaveCommands:
    def test_save_command(self):
        state = _make_game()
        lines = process_command(state, "save")
        text = "\n".join(lines)
        assert "save" in text.lower() or "Save" in text
        assert has_save()

    def test_newsave_command(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 77
        save_mud_state(state)
        # newsave should reset the game
        lines = process_command(state, "newsave")
        text = "\n".join(lines)
        assert "new" in text.lower() or "fresh" in text.lower() or "restart" in text.lower() or "STACKHAVEN" in text
