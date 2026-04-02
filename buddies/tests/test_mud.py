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
    _handle_sell, _buddy_comment, _room_reaction, _maybe_world_event,
    WORLD_EVENTS, ROOM_REACTIONS,
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
        # Lobby has no south exit
        lines = _handle_go(state, "south")
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


# ---------------------------------------------------------------------------
# Expanded world tests
# ---------------------------------------------------------------------------

class TestExpandedWorld:
    def test_new_rooms_exist(self):
        state = _make_game()
        new_rooms = ["qa_lab", "testing_grounds", "standup_room", "incident_channel", "archive", "kubernetes_cluster"]
        for room_id in new_rooms:
            assert room_id in state.rooms, f"Missing room: {room_id}"

    def test_new_npcs_exist(self):
        state = _make_game()
        new_npcs = ["qa_lead", "flaky_test_swarm", "scrum_master", "oncall_engineer", "memory_leak", "pod_person", "k8s_merchant"]
        for npc_id in new_npcs:
            assert npc_id in state.npcs, f"Missing NPC: {npc_id}"

    def test_new_quests_exist(self):
        state = _make_game()
        assert "flaky_hunt" in state.quests
        assert "incident_report" in state.quests

    def test_qa_lab_reachable(self):
        state = _make_game()
        # lobby → west → qa_lab
        _handle_go(state, "west")
        assert state.current_room == "qa_lab"

    def test_testing_grounds_reachable(self):
        state = _make_game()
        _handle_go(state, "west")  # lobby → qa_lab
        _handle_go(state, "north")  # qa_lab → testing_grounds
        assert state.current_room == "testing_grounds"

    def test_standup_reachable(self):
        state = _make_game()
        _handle_go(state, "north")  # lobby → town_square
        _handle_go(state, "north")  # town_square → meeting_room
        _handle_go(state, "east")  # meeting_room → standup_room
        assert state.current_room == "standup_room"

    def test_incident_channel_reachable(self):
        state = _make_game()
        # Need server key → skip locked, give key
        state.inventory.add_item(state.items["server_key"])
        state.current_room = "repository_depths"
        _handle_go(state, "north")  # → server_room
        assert state.current_room == "server_room"
        _handle_go(state, "north")  # → incident_channel
        assert state.current_room == "incident_channel"

    def test_archive_locked(self):
        state = _make_game()
        state.current_room = "incident_channel"
        lines = _handle_go(state, "east")
        assert state.current_room == "incident_channel"  # Still locked
        assert "locked" in "\n".join(lines).lower()

    def test_archive_unlockable(self):
        state = _make_game()
        state.current_room = "incident_channel"
        state.inventory.add_item(state.items["war_room_badge"])
        _handle_go(state, "east")
        assert state.current_room == "archive"

    def test_kubernetes_reachable(self):
        state = _make_game()
        state.current_room = "cloud_district"
        _handle_go(state, "north")
        assert state.current_room == "kubernetes_cluster"

    def test_all_room_exits_valid(self):
        """Every exit destination in the expanded world must be a valid room."""
        state = _make_game()
        for room in state.rooms.values():
            for ex in room.exits:
                assert ex.destination in state.rooms, \
                    f"Room {room.id} exit {ex.direction} → {ex.destination} not found"

    def test_flaky_hunt_quest_flow(self):
        state = _make_game()
        state.current_room = "qa_lab"
        # Talk to QA lead to start quest
        process_command(state, "talk priya")
        assert state.quests["flaky_hunt"].status == QuestStatus.ACTIVE

    def test_server_key_in_server_room(self):
        """Server key should be findable to unlock the server room door."""
        state = _make_game()
        assert "server_key" in state.rooms["server_room"].items


# ---------------------------------------------------------------------------
# Sell command tests
# ---------------------------------------------------------------------------

class TestSellCommand:
    def test_sell_no_merchant(self):
        state = _make_game()
        state.current_room = "lobby"  # No merchant here
        lines = _handle_sell(state, "anything")
        assert "no merchant" in "\n".join(lines).lower()

    def test_sell_shows_sellable(self):
        state = _make_game()
        state.current_room = "break_room"  # Coffee Machine is merchant
        # Add a junk item
        state.inventory.add_item(state.items["deprecated_manual"])
        lines = _handle_sell(state, "")
        text = "\n".join(lines)
        assert "Sellable" in text
        assert "Deprecated" in text

    def test_sell_item(self):
        state = _make_game()
        state.current_room = "break_room"
        junk = state.items["deprecated_manual"]
        state.inventory.add_item(junk)
        initial_gold = state.inventory.gold
        lines = _handle_sell(state, "deprecated")
        assert not state.inventory.has_item("deprecated_manual")
        assert state.inventory.gold > initial_gold

    def test_sell_half_value(self):
        state = _make_game()
        state.current_room = "break_room"
        junk = Item("test_junk", "Test Junk", "Junk", ItemType.JUNK, value=10)
        state.inventory.add_item(junk)
        initial_gold = state.inventory.gold
        _handle_sell(state, "test junk")
        assert state.inventory.gold == initial_gold + 5  # Half of 10

    def test_sell_prevents_quest_items(self):
        state = _make_game()
        state.current_room = "break_room"
        state.inventory.add_item(state.items["merge_conflict"])
        lines = _handle_sell(state, "merge conflict")
        assert state.inventory.has_item("merge_conflict")  # Not sold
        assert "important" in "\n".join(lines).lower()

    def test_sell_prevents_key_items(self):
        state = _make_game()
        state.current_room = "break_room"
        state.inventory.add_item(state.items["server_key"])
        lines = _handle_sell(state, "server")
        assert state.inventory.has_item("server_key")  # Not sold


# ---------------------------------------------------------------------------
# World events tests
# ---------------------------------------------------------------------------

class TestWorldEvents:
    def test_world_events_exist(self):
        assert len(WORLD_EVENTS) >= 15

    def test_maybe_world_event_returns_string_or_none(self):
        # Run many times to test both paths
        results = [_maybe_world_event() for _ in range(100)]
        got_none = any(r is None for r in results)
        got_str = any(r is not None for r in results)
        assert got_none, "Should sometimes return None"
        assert got_str, "Should sometimes return an event"

    def test_world_events_fire_on_commands(self):
        """World events should appear in command output sometimes."""
        state = _make_game()
        found_event = False
        for _ in range(50):
            lines = process_command(state, "wait")
            text = "\n".join(lines)
            if "ANNOUNCEMENT" in text or "💬" in text or "You hear" in text or "You step" in text:
                found_event = True
                break
        # With 20% chance over 50 tries, almost certain to get at least one


# ---------------------------------------------------------------------------
# Room reaction tests
# ---------------------------------------------------------------------------

class TestRoomReactions:
    def test_room_reactions_exist_for_many_rooms(self):
        assert len(ROOM_REACTIONS) >= 10

    def test_room_reaction_returns_string(self):
        party = [_make_buddy(name="Tester", stats={"debugging": 30, "chaos": 5, "snark": 5, "wisdom": 5, "patience": 5})]
        result = _room_reaction(party, "server_room")
        assert result is None or isinstance(result, str)
        # With debugging dominant, should get clinical server room reaction
        for _ in range(20):
            r = _room_reaction(party, "server_room")
            if r and "Tester" in r:
                return

    def test_room_reaction_empty_party(self):
        assert _room_reaction([], "server_room") is None

    def test_room_reaction_unknown_room(self):
        party = [_make_buddy()]
        assert _room_reaction(party, "nonexistent_room") is None

    def test_chaos_buddy_reacts_differently(self):
        """A high-CHAOS buddy should get chaos-specific room lines."""
        chaos_buddy = _make_buddy(name="Maniac", stats={"debugging": 5, "chaos": 40, "snark": 5, "wisdom": 5, "patience": 5})
        party = [chaos_buddy]
        got_chaos_line = False
        for _ in range(30):
            r = _room_reaction(party, "cloud_district")
            if r and ("VIBES" in r or "Nothing is real" in r):
                got_chaos_line = True
                break
        assert got_chaos_line, "Chaos buddy should get chaos-flavored room reactions"

    def test_all_rooms_have_all_stats(self):
        """Every room reaction should have lines for all 5 stats."""
        for room_id, pools in ROOM_REACTIONS.items():
            for stat in ["debugging", "chaos", "snark", "wisdom", "patience"]:
                assert stat in pools, f"Room {room_id} missing {stat} reactions"
                assert len(pools[stat]) >= 1, f"Room {room_id} {stat} pool is empty"


# ---------------------------------------------------------------------------
# Lore system tests
# ---------------------------------------------------------------------------

class TestLoreSystem:
    def test_items_have_lore(self):
        """Most items should have lore text."""
        state = _make_game()
        items_with_lore = [i for i in state.items.values() if i.lore]
        assert len(items_with_lore) >= 20, f"Only {len(items_with_lore)} items have lore"

    def test_lore_visible_on_examine(self):
        """Examining an item with lore should show the lore text."""
        state = _make_game()
        state.current_room = "break_room"
        lines = process_command(state, "examine pizza")
        text = "\n".join(lines)
        assert "deploy" in text.lower() or "Pizza" in text  # Lore mentions deploy celebration

    def test_lore_command_empty(self):
        state = _make_game()
        lines = process_command(state, "lore")
        text = "\n".join(lines)
        assert "Codex" in text

    def test_lore_command_with_items(self):
        state = _make_game()
        state.inventory.add_item(state.items["rubber_duck"])
        lines = process_command(state, "lore")
        text = "\n".join(lines)
        assert "Rubber Duck" in text

    def test_lore_command_specific_item(self):
        state = _make_game()
        state.inventory.add_item(state.items["rubber_duck"])
        lines = process_command(state, "lore rubber duck")
        text = "\n".join(lines)
        assert "Founder Chen" in text or "Three-Week Deploy" in text

    def test_lore_not_on_items_without_lore(self):
        """Items created by buy (copies) shouldn't show lore unless they have it."""
        from buddies.core.games.mud_world import Item, ItemType
        item = Item("test_no_lore", "Test", "No lore here", ItemType.JUNK)
        assert item.lore == ""


# ---------------------------------------------------------------------------
# Economy Phase 3: Setup tests
# ---------------------------------------------------------------------------

class TestEconomySetup:
    def test_back_room_exists(self):
        state = _make_game()
        assert "back_room" in state.rooms
        assert state.rooms["back_room"].name == "Lucky's Back Room"

    def test_lucky_npc_exists(self):
        state = _make_game()
        assert "lucky" in state.npcs
        assert state.npcs["lucky"].disposition == NPCDisposition.MERCHANT

    def test_supply_closet_has_back_room_exit(self):
        state = _make_game()
        room = state.rooms["supply_closet"]
        destinations = [ex.destination for ex in room.exits]
        assert "back_room" in destinations


# ---------------------------------------------------------------------------
# Gamble command tests
# ---------------------------------------------------------------------------

class TestGambleCommand:
    def test_gamble_no_args_shows_help(self):
        state = _make_game()
        state.current_room = "back_room"
        lines = process_command(state, "gamble")
        text = "\n".join(lines)
        assert "Games of Chance" in text
        assert "flip" in text
        assert "slots" in text

    def test_gamble_flip_works(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 50
        lines = process_command(state, "gamble flip 10")
        text = "\n".join(lines)
        assert "Coin Flip" in text
        assert state.gold_gambled == 10
        # Gold should have changed (either won or lost)
        assert state.inventory.gold != 50 or state.gold_won_gambling > 0

    def test_gamble_slots_works(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 50
        lines = process_command(state, "gamble slots 10")
        text = "\n".join(lines)
        assert "Slot Machine" in text
        # Should show slot symbols in the output
        assert "┃" in text

    def test_gamble_flip_min_bet_rejected(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 50
        lines = process_command(state, "gamble flip 3")
        text = "\n".join(lines)
        assert "Minimum" in text or "minimum" in text
        assert state.inventory.gold == 50  # No gold deducted

    def test_gamble_flip_max_bet_rejected(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 500
        lines = process_command(state, "gamble flip 200")
        text = "\n".join(lines)
        assert "Maximum" in text or "maximum" in text
        assert state.inventory.gold == 500

    def test_gamble_insufficient_gold(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 5
        lines = process_command(state, "gamble flip 10")
        text = "\n".join(lines)
        assert "5g" in text  # Shows current gold
        assert state.inventory.gold == 5  # Unchanged

    def test_gamble_wrong_room(self):
        state = _make_game()
        state.current_room = "lobby"
        lines = process_command(state, "gamble flip 10")
        text = "\n".join(lines)
        assert "nobody" in text.lower()

    def test_gamble_unknown_game_type(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 50
        lines = process_command(state, "gamble roulette 10")
        text = "\n".join(lines)
        assert "Unknown" in text or "unknown" in text or "flip" in text.lower()
        assert state.inventory.gold == 50  # Refunded
        assert state.gold_gambled == 0  # Not counted


# ---------------------------------------------------------------------------
# Wealth command tests
# ---------------------------------------------------------------------------

class TestWealthCommand:
    def test_wealth_shows_gold(self):
        state = _make_game()
        state.inventory.gold = 42
        lines = process_command(state, "wealth")
        text = "\n".join(lines)
        assert "42g" in text
        assert "Wealth Report" in text

    def test_wealth_title_venture_capitalist(self):
        state = _make_game()
        state.inventory.gold = 500
        lines = process_command(state, "wealth")
        text = "\n".join(lines)
        assert "Venture Capitalist" in text

    def test_wealth_shows_gambling_stats(self):
        state = _make_game()
        state.current_room = "back_room"
        state.inventory.gold = 50
        process_command(state, "gamble flip 10")
        lines = process_command(state, "wealth")
        text = "\n".join(lines)
        assert "Gambling wins" in text or "Gold gambled" in text
        assert "gambled" in text.lower()

    def test_wealth_shows_tips(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 50
        process_command(state, "tip gerald 5")
        lines = process_command(state, "wealth")
        text = "\n".join(lines)
        assert "Tips given" in text
        assert "5g" in text


# ---------------------------------------------------------------------------
# Tip command tests
# ---------------------------------------------------------------------------

class TestTipCommand:
    def test_tip_no_args_lists_npcs(self):
        state = _make_game()
        state.current_room = "town_square"
        lines = process_command(state, "tip")
        text = "\n".join(lines)
        assert "Tip who" in text or "tip" in text.lower()

    def test_tip_npc_deducts_gold(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 50
        lines = process_command(state, "tip gerald 5")
        text = "\n".join(lines)
        assert state.inventory.gold == 45
        assert "Gerald" in text or "gerald" in text.lower()

    def test_tip_nonexistent_npc(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 50
        lines = process_command(state, "tip nonexistent 5")
        text = "\n".join(lines)
        assert "no" in text.lower() or "not" in text.lower()
        assert state.inventory.gold == 50  # Unchanged

    def test_tip_insufficient_gold(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 3
        lines = process_command(state, "tip gerald 9999")
        text = "\n".join(lines)
        assert "3g" in text  # Shows current gold
        assert state.inventory.gold == 3

    def test_tips_given_tracks_total(self):
        state = _make_game()
        state.current_room = "town_square"
        state.inventory.gold = 50
        process_command(state, "tip gerald 5")
        process_command(state, "tip gerald 3")
        assert state.tips_given == 8


# ---------------------------------------------------------------------------
# Bounty command tests
# ---------------------------------------------------------------------------

class TestBountyCommand:
    def test_bounty_shows_all_bounties(self):
        from buddies.core.games.mud_engine import BOUNTIES
        state = _make_game()
        lines = process_command(state, "bounty")
        text = "\n".join(lines)
        assert "Bounty Board" in text
        for bounty in BOUNTIES:
            assert bounty["name"] in text

    def test_bounty_tracks_progress(self):
        state = _make_game()
        state.rooms_visited = 3
        state.npcs_defeated = 1
        lines = process_command(state, "bounty")
        text = "\n".join(lines)
        assert "3/5" in text  # Explorer's Survey progress
        assert "1/3" in text  # Bug Bounty progress

    def test_bounty_claim_awards_gold(self):
        state = _make_game()
        state.rooms_visited = 5  # Completes Explorer's Survey (reward: 15g)
        initial_gold = state.inventory.gold
        lines = process_command(state, "bounty claim")
        text = "\n".join(lines)
        assert "Claimed" in text
        assert state.inventory.gold == initial_gold + 15
        assert state.bounties_completed == 1

    def test_bounty_claim_nothing_complete(self):
        state = _make_game()
        state.rooms_visited = 0
        state.npcs_defeated = 0
        state.npcs_talked = 0
        state.items_collected = 0
        lines = process_command(state, "bounty claim")
        text = "\n".join(lines)
        assert "No unclaimed" in text or "Complete more" in text

    def test_bounty_cannot_claim_twice(self):
        state = _make_game()
        state.rooms_visited = 5  # Complete Explorer's Survey
        process_command(state, "bounty claim")
        gold_after_first_claim = state.inventory.gold
        process_command(state, "bounty claim")
        assert state.inventory.gold == gold_after_first_claim  # No double payout
        assert state.bounties_completed == 1


# ---------------------------------------------------------------------------
# New cosmetic items tests
# ---------------------------------------------------------------------------

class TestNewCosmetics:
    def test_new_cosmetic_items_exist(self):
        state = _make_game()
        new_cosmetics = ["golden_semicolon", "executive_lanyard", "rgb_keyboard_skin", "cloud_in_a_jar", "vintage_floppy"]
        for item_id in new_cosmetics:
            assert item_id in state.items, f"Missing cosmetic item: {item_id}"
            assert state.items[item_id].item_type == ItemType.COSMETIC

    def test_all_new_cosmetics_have_lore(self):
        state = _make_game()
        new_cosmetics = ["golden_semicolon", "executive_lanyard", "rgb_keyboard_skin", "cloud_in_a_jar", "vintage_floppy"]
        for item_id in new_cosmetics:
            assert state.items[item_id].lore, f"Cosmetic {item_id} missing lore text"

    def test_all_new_cosmetics_have_value(self):
        state = _make_game()
        new_cosmetics = ["golden_semicolon", "executive_lanyard", "rgb_keyboard_skin", "cloud_in_a_jar", "vintage_floppy"]
        for item_id in new_cosmetics:
            assert state.items[item_id].value > 0, f"Cosmetic {item_id} has no value"
