"""Tests for StackWars — micro-4X wargame engine."""

import pytest
import random

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.games import GameType
from buddies.core.games.stackwars import (
    StackWarsState, create_stackwars, generate_map,
    AbilityType, Faction, Terrain, UnitType, Unit, BuildingType,
    GRID_W, GRID_H, UNIT_STATS, UNIT_MATCHUPS, FACTION_EMOJI,
    STAT_TO_FACTION, ABILITY_ACTIONS,
    choose_ability, execute_action, skip_action,
    resolve_combat, render_map, render_status,
    faction_from_buddy, ai_turn,
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


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------

class TestMapGeneration:
    def test_map_is_5x5(self):
        grid = generate_map()
        assert len(grid) == GRID_H
        assert all(len(row) == GRID_W for row in grid)

    def test_map_has_hq_tiles(self):
        grid = generate_map(2)
        hq_count = sum(1 for y in range(GRID_H) for x in range(GRID_W)
                       if grid[y][x].terrain == Terrain.HQ)
        assert hq_count == 2

    def test_map_has_flag_tiles(self):
        grid = generate_map()
        flag_count = sum(1 for y in range(GRID_H) for x in range(GRID_W)
                         if grid[y][x].terrain == Terrain.FLAG)
        assert flag_count >= 3

    def test_map_has_mountains(self):
        grid = generate_map()
        mt_count = sum(1 for y in range(GRID_H) for x in range(GRID_W)
                       if grid[y][x].terrain == Terrain.MOUNTAIN)
        assert mt_count >= 2

    def test_map_has_firewalls(self):
        grid = generate_map()
        fw_count = sum(1 for y in range(GRID_H) for x in range(GRID_W)
                       if grid[y][x].terrain == Terrain.FIREWALL)
        assert fw_count >= 1


# ---------------------------------------------------------------------------
# Game creation
# ---------------------------------------------------------------------------

class TestGameCreation:
    def test_creates_2_players(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        assert len(state.players) == 2

    def test_player_0_is_human(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        assert not state.players[0].is_ai

    def test_player_1_is_ai(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        assert state.players[1].is_ai

    def test_starting_units(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        p0_units = state.player_units(0)
        assert len(p0_units) == 3  # 2 Script Kiddies + 1 Operator

    def test_starting_resources(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        assert state.players[0].code == 15
        assert state.players[0].bugs == 0
        assert state.players[0].coffee == 0

    def test_faction_from_dominant_stat(self):
        for stat, expected_faction in STAT_TO_FACTION.items():
            buddy = make_buddy(dominant=stat)
            assert faction_from_buddy(buddy) == expected_faction


# ---------------------------------------------------------------------------
# Ability system
# ---------------------------------------------------------------------------

class TestAbilitySystem:
    def test_choose_ability(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        lines = choose_ability(state, AbilityType.DEPLOY)
        assert state.chosen_ability == AbilityType.DEPLOY
        assert state.players[0].cooldowns["deploy"] == 2

    def test_cooldown_blocks_reuse(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        choose_ability(state, AbilityType.DEPLOY)
        # Reset state for next turn
        state.chosen_ability = None
        state.phase = "choose_ability"
        lines = choose_ability(state, AbilityType.DEPLOY)
        assert "cooldown" in lines[0].lower()

    def test_favor_accumulates(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        choose_ability(state, AbilityType.DEPLOY)
        assert state.players[0].favor["deploy"] == 1

    def test_blessing_at_2_favor(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        state.players[0].favor["deploy"] = 1  # Pre-set to 1
        state.players[0].cooldowns["deploy"] = 0
        choose_ability(state, AbilityType.DEPLOY)
        assert state.players[0].blessings["deploy"] == 1

    def test_all_abilities_have_3_actions(self):
        for ability in AbilityType:
            assert len(ABILITY_ACTIONS[ability]) == 3

    def test_available_abilities(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        available = state.players[0].available_abilities()
        assert len(available) == 5  # All available at start

    def test_tick_cooldowns(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        state.players[0].cooldowns["deploy"] = 2
        state.players[0].tick_cooldowns()
        assert state.players[0].cooldowns["deploy"] == 1


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class TestActions:
    def test_deploy_gain_code(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        choose_ability(state, AbilityType.DEPLOY)
        initial_code = state.players[0].code
        execute_action(state, "")  # Action 1: gain code
        assert state.players[0].code == initial_code + 5

    def test_skip_action(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        choose_ability(state, AbilityType.DEPLOY)
        lines = skip_action(state)
        assert state.action_step == 1

    def test_recruit_unit(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        choose_ability(state, AbilityType.DEPLOY)
        execute_action(state, "")  # Gain code
        initial_units = len(state.player_units(0))
        execute_action(state, "kiddie")  # Recruit
        assert len(state.player_units(0)) == initial_units + 1

    def test_recruit_too_expensive(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        state.players[0].code = 2  # Not enough for anything
        choose_ability(state, AbilityType.DEPLOY)
        skip_action(state)  # Skip code gain
        lines = execute_action(state, "sysadmin")
        assert any("not enough" in l.lower() for l in lines)


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

class TestCombat:
    def test_combat_resolves_contested_tiles(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        # Place opposing units on same tile
        tile = state.grid[2][2]
        tile.units = [
            Unit(UnitType.SYSADMIN, 0, hp=6),
            Unit(UnitType.SCRIPT_KIDDIE, 1, hp=3),
        ]
        lines = resolve_combat(state)
        assert len(lines) > 0  # Combat happened

    def test_no_combat_on_uncontested_tiles(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        # Clear all units from shared tiles
        for y in range(GRID_H):
            for x in range(GRID_W):
                state.grid[y][x].units = []
        lines = resolve_combat(state)
        assert len(lines) == 0

    def test_unit_matchup_bonuses_exist(self):
        # Script Kiddies should have bonus vs Architects
        assert UNIT_MATCHUPS[UnitType.SCRIPT_KIDDIE][UnitType.ARCHITECT] > 0
        # Hackers should have bonus vs Script Kiddies
        assert UNIT_MATCHUPS[UnitType.HACKER][UnitType.SCRIPT_KIDDIE] > 0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class TestRendering:
    def test_render_map_produces_lines(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        lines = render_map(state)
        assert len(lines) >= GRID_H + 1  # Header + rows

    def test_render_status_shows_players(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        lines = render_status(state)
        assert len(lines) >= 2  # At least 2 players + turn counter


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

class TestAI:
    def test_ai_takes_turn(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        state.current_player = 1  # AI player
        state.players[1].tick_cooldowns()
        lines = ai_turn(state)
        assert len(lines) > 0

    def test_ai_chooses_available_ability(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        state.current_player = 1
        # Put everything on cooldown except RALLY
        for a in AbilityType:
            state.players[1].cooldowns[a.value] = 2
        state.players[1].cooldowns[AbilityType.RALLY.value] = 0
        lines = ai_turn(state)
        assert any("RALLY" in l for l in lines)


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

class TestWinCondition:
    def test_game_not_over_at_start(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        assert not state.game_over
        assert state.winner == -1

    def test_count_flags(self):
        buddy = make_buddy()
        state = create_stackwars(buddy)
        # Claim all flag tiles for player 0
        for y in range(GRID_H):
            for x in range(GRID_W):
                if state.grid[y][x].is_flag:
                    state.grid[y][x].owner = 0
        assert state.count_flags(0) >= 3


# ---------------------------------------------------------------------------
# Faction coverage
# ---------------------------------------------------------------------------

class TestFactions:
    def test_all_factions_have_emoji(self):
        for f in Faction:
            assert f in FACTION_EMOJI

    def test_all_stats_map_to_faction(self):
        for stat in ["debugging", "chaos", "snark", "wisdom", "patience"]:
            assert stat in STAT_TO_FACTION

    def test_all_unit_types_have_stats(self):
        for ut in UnitType:
            assert ut in UNIT_STATS
            stats = UNIT_STATS[ut]
            assert "attack" in stats
            assert "defense" in stats
            assert "cost" in stats
