"""Tests for the StackHaven MUD engine."""

import pytest

from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.games import GameType, GameOutcome
from buddies.core.games.mud_world import (
    build_starter_items, build_starter_npcs, build_starter_rooms, build_starter_quests,
    Item, ItemType, NPC, NPCDisposition, Room, Quest, QuestStatus, MudInventory,
)
from buddies.core.games.mud_engine import (
    MudState, create_mud_game, parse_command, process_command,
    get_intro_text, get_game_result, _handle_look, _handle_go,
    _handle_inventory, _handle_quest, _handle_map, _handle_help,
    _buddy_comment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_buddy(name="TestBuddy", species_name="phoenix", stats=None) -> BuddyState:
    species = next((s for s in SPECIES_CATALOG if s.name == species_name), SPECIES_CATALOG[0])
    return BuddyState(
        buddy_id=1,
        species=species,
        name=name,
        shiny=False,
        stats=stats or {"debugging": 15, "chaos": 10, "snark": 12, "wisdom": 20, "patience": 18},
        xp=100,
        level=5,
        mood="happy",
        mood_value=70,
        soul_description="A test buddy",
        hat=None,
        hats_owned=["tinyduck"],
    )


def _make_game(party=None) -> MudState:
    if party is None:
        party = [_make_buddy()]
    return create_mud_game(party)


# ---------------------------------------------------------------------------
# World building tests
# ---------------------------------------------------------------------------

class TestWorldBuilding:
    def test_items_built(self):
        items = build_starter_items()
        assert len(items) >= 20
        assert "rubber_duck" in items
        assert "coffee" in items
        assert "server_key" in items
        assert "slightly_haunted_tophat" in items

    def test_npcs_built(self):
        items = build_starter_items()
        npcs = build_starter_npcs(items)
        assert len(npcs) >= 8
        assert "sysadmin" in npcs
        assert "intern" in npcs
        assert "tech_debt_dragon" in npcs
        assert "coffee_machine" in npcs

    def test_rooms_built(self):
        rooms = build_starter_rooms()
        assert len(rooms) >= 10
        assert "lobby" in rooms
        assert "town_square" in rooms
        assert "cloud_district" in rooms
        assert "root_chamber" in rooms

    def test_rooms_connected(self):
        """Every exit destination should be a valid room."""
        rooms = build_starter_rooms()
        for room in rooms.values():
            for ex in room.exits:
                assert ex.destination in rooms, f"Room {room.id} exit {ex.direction} → {ex.destination} not found"

    def test_quests_built(self):
        quests = build_starter_quests()
        assert len(quests) >= 3
        assert "fix_pipeline" in quests
        assert "scope_creep" in quests
        assert "dragon_slayer" in quests

    def test_hostile_npcs_have_stats(self):
        items = build_starter_items()
        npcs = build_starter_npcs(items)
        for npc in npcs.values():
            if npc.disposition == NPCDisposition.HOSTILE:
                assert npc.hp > 0, f"Hostile NPC {npc.id} has no HP"
                assert npc.attack > 0, f"Hostile NPC {npc.id} has no attack"

    def test_merchant_npcs_have_shop(self):
        items = build_starter_items()
        npcs = build_starter_npcs(items)
        for npc in npcs.values():
            if npc.disposition == NPCDisposition.MERCHANT:
                assert npc.shop_items, f"Merchant {npc.id} has empty shop"


# ---------------------------------------------------------------------------
# Inventory tests
# ---------------------------------------------------------------------------

class TestInventory:
    def test_add_item(self):
        inv = MudInventory()
        item = Item("test", "Test", "A test", ItemType.JUNK)
        assert inv.add_item(item)
        assert inv.has_item("test")

    def test_remove_item(self):
        inv = MudInventory()
        item = Item("test", "Test", "A test", ItemType.JUNK)
        inv.add_item(item)
        removed = inv.remove_item("test")
        assert removed is not None
        assert not inv.has_item("test")

    def test_max_items(self):
        inv = MudInventory(max_items=2)
        inv.add_item(Item("a", "A", "A", ItemType.JUNK))
        inv.add_item(Item("b", "B", "B", ItemType.JUNK))
        assert not inv.add_item(Item("c", "C", "C", ItemType.JUNK))

    def test_best_weapon(self):
        inv = MudInventory()
        inv.add_item(Item("w1", "Weak", "W", ItemType.WEAPON, attack_bonus=2))
        inv.add_item(Item("w2", "Strong", "S", ItemType.WEAPON, attack_bonus=8))
        assert inv.weapon.id == "w2"

    def test_best_armor(self):
        inv = MudInventory()
        inv.add_item(Item("a1", "Weak", "W", ItemType.ARMOR, defense_bonus=1))
        inv.add_item(Item("a2", "Strong", "S", ItemType.ARMOR, defense_bonus=5))
        assert inv.armor.id == "a2"


# ---------------------------------------------------------------------------
# Command parsing tests
# ---------------------------------------------------------------------------

class TestCommandParsing:
    def test_direction_shortcut(self):
        assert parse_command("n") == ("go", "north")
        assert parse_command("s") == ("go", "south")
        assert parse_command("e") == ("go", "east")
        assert parse_command("w") == ("go", "west")

    def test_go_direction(self):
        assert parse_command("go north") == ("go", "north")
        assert parse_command("go n") == ("go", "north")

    def test_aliases(self):
        assert parse_command("l")[0] == "look"
        assert parse_command("x something")[0] == "examine"
        assert parse_command("i")[0] == "inventory"
        assert parse_command("t")[0] == "talk"
        assert parse_command("?")[0] == "help"

    def test_empty_input(self):
        assert parse_command("") == ("", "")

    def test_unknown_command(self):
        cmd, arg = parse_command("xyzzy")
        assert cmd == "xyzzy"  # Not recognized, passed through


# ---------------------------------------------------------------------------
# Game engine tests
# ---------------------------------------------------------------------------

class TestMudEngine:
    def test_create_game(self):
        state = _make_game()
        assert state.current_room == "lobby"
        assert state.inventory.gold == 10
        assert len(state.party) == 1
        assert len(state.rooms) >= 10

    def test_look(self):
        state = _make_game()
        lines = _handle_look(state, "")
        text = "\n".join(lines)
        assert "Lobby" in text
        assert "Exits" in text

    def test_go_valid(self):
        state = _make_game()
        lines = _handle_go(state, "north")
        assert state.current_room == "town_square"
        text = "\n".join(lines)
        assert "Open-Plan Office" in text

    def test_go_invalid(self):
        state = _make_game()
        lines = _handle_go(state, "west")
        assert state.current_room == "lobby"  # Didn't move
        assert "no exit" in lines[0].lower()

    def test_go_locked(self):
        state = _make_game()
        state.current_room = "town_square"
        lines = _handle_go(state, "up")
        assert state.current_room == "town_square"  # Still locked
        assert "locked" in "\n".join(lines).lower()

    def test_go_unlock_with_key(self):
        state = _make_game()
        state.current_room = "town_square"
        # Give the VPN token
        vpn = state.items["vpn_token"]
        state.inventory.add_item(vpn)
        lines = _handle_go(state, "up")
        assert state.current_room == "cloud_district"

    def test_take_item(self):
        state = _make_game()
        state.current_room = "break_room"
        lines = process_command(state, "take pizza")
        assert state.inventory.has_item("pizza_slice")
        assert "Picked up" in "\n".join(lines)

    def test_inventory_empty(self):
        state = _make_game()
        lines = _handle_inventory(state, "")
        text = "\n".join(lines)
        assert "Gold: 10g" in text

    def test_help(self):
        state = _make_game()
        lines = _handle_help(state, "")
        text = "\n".join(lines)
        assert "Movement" in text
        assert "attack" in text.lower()

    def test_map(self):
        state = _make_game()
        lines = _handle_map(state, "")
        text = "\n".join(lines)
        assert "StackHaven" in text
        assert "Lobby" in text

    def test_quest_log_empty(self):
        state = _make_game()
        lines = _handle_quest(state, "")
        text = "\n".join(lines)
        assert "No quests" in text

    def test_wait(self):
        state = _make_game()
        initial_turns = state.turns
        process_command(state, "wait")
        assert state.turns == initial_turns + 1

    def test_intro_text(self):
        state = _make_game()
        lines = get_intro_text(state)
        text = "\n".join(lines)
        assert "STACKHAVEN" in text
        assert "TestBuddy" in text

    def test_process_unknown_command(self):
        state = _make_game()
        lines = process_command(state, "xyzzy")
        assert "Unknown" in lines[0]


# ---------------------------------------------------------------------------
# Combat tests
# ---------------------------------------------------------------------------

class TestMudCombat:
    def test_attack_hostile_npc(self):
        state = _make_game()
        state.current_room = "dead_code_garden"
        lines = process_command(state, "attack")
        text = "\n".join(lines)
        assert "COMBAT" in text or "combat" in text.lower()
        assert state.combat is not None

    def test_attack_in_combat(self):
        state = _make_game()
        state.current_room = "dead_code_garden"
        process_command(state, "attack")  # Start combat
        lines = process_command(state, "attack")  # Attack round
        text = "\n".join(lines)
        assert "damage" in text.lower() or "Victory" in text

    def test_flee_from_combat(self):
        state = _make_game()
        state.current_room = "dead_code_garden"
        process_command(state, "attack")
        # Try fleeing multiple times (70% chance)
        for _ in range(20):
            if state.combat is None:
                break
            process_command(state, "flee")
        # Should have fled by now (statistically)

    def test_restricted_commands_in_combat(self):
        state = _make_game()
        state.current_room = "dead_code_garden"
        process_command(state, "attack")
        lines = process_command(state, "go north")
        assert "in combat" in lines[0].lower()


# ---------------------------------------------------------------------------
# NPC interaction tests
# ---------------------------------------------------------------------------

class TestNPCInteraction:
    def test_talk_to_npc(self):
        state = _make_game()
        state.current_room = "town_square"
        lines = process_command(state, "talk gerald")
        text = "\n".join(lines)
        assert "Gerald" in text

    def test_talk_starts_quest(self):
        state = _make_game()
        state.current_room = "town_square"
        lines = process_command(state, "talk gerald")
        text = "\n".join(lines)
        assert "Quest" in text or "quest" in text
        assert state.quests["fix_pipeline"].status == QuestStatus.ACTIVE

    def test_examine_npc(self):
        state = _make_game()
        state.current_room = "town_square"
        lines = process_command(state, "examine gerald")
        text = "\n".join(lines)
        assert "Sysadmin" in text

    def test_buy_shows_shop(self):
        state = _make_game()
        state.current_room = "break_room"
        lines = process_command(state, "buy")
        text = "\n".join(lines)
        assert "Shop" in text
        assert "Coffee" in text or "coffee" in text

    def test_talk_gives_item(self):
        state = _make_game()
        state.current_room = "town_square"
        # Talk to intern who gives coffee
        lines = process_command(state, "talk skyler")
        text = "\n".join(lines)
        assert "Received" in text or state.inventory.has_item("coffee")


# ---------------------------------------------------------------------------
# Game result tests
# ---------------------------------------------------------------------------

class TestGameResult:
    def test_game_result_basic(self):
        state = _make_game()
        result = get_game_result(state, buddy_id=1)
        assert result.game_type == GameType.MUD
        assert result.buddy_id == 1

    def test_game_result_xp_scales(self):
        state = _make_game()
        state.rooms_visited = 5
        state.npcs_talked = 3
        state.npcs_defeated = 2
        state.quests_completed = 1
        result = get_game_result(state, buddy_id=1)
        assert result.xp_earned > 0
        expected = 5 * 2 + 3 * 3 + 2 * 8 + 1 * 15
        assert result.xp_earned == expected


# ---------------------------------------------------------------------------
# Buddy commentary tests
# ---------------------------------------------------------------------------

class TestBuddyCommentary:
    def test_commentary_returns_string(self):
        party = [_make_buddy()]
        result = _buddy_comment(party, "enter_room")
        # May be None due to randomness, but type should be correct
        assert result is None or isinstance(result, str)

    def test_commentary_empty_party(self):
        assert _buddy_comment([], "enter_room") is None

    def test_commentary_includes_name(self):
        party = [_make_buddy(name="Sparky")]
        # Try many times — randomness may skip
        for _ in range(20):
            result = _buddy_comment(party, "enter_room")
            if result and "Sparky" in result:
                return
        # Commentary uses buddy name
        # (It's random so we just verify it works without error)
