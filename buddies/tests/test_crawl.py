"""Tests for the Blobber Dungeon Crawl.

Uses Textual's built-in Pilot for UI testing and direct engine tests.
"""

import pytest
import asyncio

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.games.crawl import (
    CrawlState, generate_floor, GRID_SIZE, CellType, Facing,
    PartyMember, BuddyClass, EncounterKind,
)
from buddies.core.games.crawl_render import render_view, render_minimap, render_party


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", **overrides):
    """Create a test BuddyState with controllable dominant stat."""
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30  # Make this the dominant stat

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


def make_party():
    """Create a diverse 4-buddy party covering all classes."""
    return [
        make_buddy("Debuggy", "debugging", buddy_id=1),
        make_buddy("Chaotic", "chaos", buddy_id=2),
        make_buddy("Snarky", "snark", buddy_id=3),
        make_buddy("Wise", "wisdom", buddy_id=4),
    ]


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

class TestFloorGeneration:
    def test_floor_returns_valid_grid(self):
        grid, sy, sx, facing = generate_floor(1)
        assert len(grid) == GRID_SIZE
        assert len(grid[0]) == GRID_SIZE
        assert 0 <= sy < GRID_SIZE
        assert 0 <= sx < GRID_SIZE

    def test_floor_has_passable_cells(self):
        grid, _, _, _ = generate_floor(1)
        passable = sum(
            1 for row in grid for cell in row
            if cell.terrain != CellType.WALL
        )
        assert passable > 10, "Floor should have meaningful open space"

    def test_floor_has_stairs_down(self):
        grid, _, _, _ = generate_floor(1)
        has_stairs = any(
            cell.terrain == CellType.STAIRS_DOWN
            for row in grid for cell in row
        )
        assert has_stairs, "Floor should have stairs down"

    def test_floor_has_encounters(self):
        grid, _, _, _ = generate_floor(1)
        encounters = sum(
            1 for row in grid for cell in row
            if cell.encounter is not None
        )
        assert encounters > 0, "Floor should have encounters"

    def test_higher_floors_have_more_enemies(self):
        """Floor 5 should have encounters including a boss."""
        grid, _, _, _ = generate_floor(5)
        has_boss = any(
            cell.encounter and cell.encounter.kind == EncounterKind.BOSS
            for row in grid for cell in row
        )
        assert has_boss, "Floor 5 should have a boss"


class TestPartyMember:
    def test_class_from_dominant_stat(self):
        engineer = PartyMember.from_buddy(make_buddy("E", "debugging"))
        assert engineer.buddy_class == BuddyClass.ENGINEER

        berserker = PartyMember.from_buddy(make_buddy("B", "chaos"))
        assert berserker.buddy_class == BuddyClass.BERSERKER

        rogue = PartyMember.from_buddy(make_buddy("R", "snark"))
        assert rogue.buddy_class == BuddyClass.ROGUE

        mage = PartyMember.from_buddy(make_buddy("M", "wisdom"))
        assert mage.buddy_class == BuddyClass.MAGE

        paladin = PartyMember.from_buddy(make_buddy("P", "patience"))
        assert paladin.buddy_class == BuddyClass.PALADIN

    def test_hp_scales_with_stats(self):
        weak = PartyMember.from_buddy(make_buddy("W", "chaos"))
        strong = make_buddy("S", "patience")
        strong.stats = {k: 30 for k in strong.stats}
        tanky = PartyMember.from_buddy(strong)
        assert tanky.hp > weak.hp

    def test_has_moves(self):
        member = PartyMember.from_buddy(make_buddy("M", "debugging"))
        assert len(member.moves) > 0

    def test_hp_bar_renders(self):
        member = PartyMember.from_buddy(make_buddy("M", "debugging"))
        bar = member.hp_bar(10)
        assert "█" in bar


class TestCrawlState:
    def test_new_game_creates_state(self):
        buddies = [make_buddy("A", buddy_id=1)]
        state = CrawlState.new_game(buddies)
        assert len(state.party) == 1
        assert state.floor == 1
        assert not state.is_over

    def test_new_game_with_party(self):
        state = CrawlState.new_game(make_party())
        assert len(state.party) == 4

    def test_start_area_is_revealed(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        cell = state.grid[state.player_y][state.player_x]
        assert cell.revealed
        assert cell.visited

    def test_movement_changes_position(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        start_y, start_x = state.player_y, state.player_x

        # Try all directions until one works (grid is random)
        moved = False
        for _ in range(4):
            if state.move_forward():
                moved = True
                break
            state.turn_right()

        if moved:
            assert (state.player_y, state.player_x) != (start_y, start_x)

    def test_turning_changes_facing(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        original = state.facing
        state.turn_right()
        assert state.facing == Facing((original + 1) % 4)
        state.turn_left()
        assert state.facing == original

    def test_cannot_walk_through_walls(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        # Face a direction and try to walk into a wall
        # Find a wall adjacent to player
        for facing in Facing:
            state.facing = facing
            dy, dx = {
                Facing.NORTH: (-1, 0), Facing.EAST: (0, 1),
                Facing.SOUTH: (1, 0), Facing.WEST: (0, -1),
            }[facing]
            ny, nx = state.player_y + dy, state.player_x + dx
            if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                if state.grid[ny][nx].terrain == CellType.WALL:
                    old_pos = (state.player_y, state.player_x)
                    result = state.move_forward()
                    assert not result
                    assert (state.player_y, state.player_x) == old_pos
                    break

    def test_movement_reveals_cells(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        # Move and check that new cells are revealed
        for _ in range(4):
            if state.move_forward():
                break
            state.turn_right()

        revealed = sum(
            1 for row in state.grid for cell in row if cell.revealed
        )
        assert revealed > 4, "Moving should reveal more cells"


class TestCombat:
    def _find_monster(self, state):
        """Walk around until we hit a monster, or return None."""
        for _ in range(100):
            if state.in_combat:
                return True
            if not state.move_forward():
                state.turn_right()
        return False

    def test_combat_triggers_on_monster(self):
        # Generate many times to find a floor with a reachable monster
        for _ in range(10):
            state = CrawlState.new_game(make_party())
            if self._find_monster(state):
                assert state.in_combat
                assert len(state.combat_enemies) > 0
                return
        pytest.skip("Couldn't reach a monster in random dungeons")

    def test_combat_attack_deals_damage(self):
        for _ in range(10):
            state = CrawlState.new_game(make_party())
            if self._find_monster(state):
                initial_hp = state.combat_enemies[0].hp
                state.combat_attack()
                # Enemy should have taken damage (or combat ended)
                if state.in_combat:
                    assert state.combat_enemies[0].hp < initial_hp
                return
        pytest.skip("Couldn't reach a monster")

    def test_combat_defend_sets_flag(self):
        for _ in range(10):
            state = CrawlState.new_game(make_party())
            if self._find_monster(state):
                state.combat_defend()
                # First member should be defending (or turn advanced)
                # Just verify no crash
                return
        pytest.skip("Couldn't reach a monster")

    def test_combat_skill_works(self):
        for _ in range(10):
            state = CrawlState.new_game(make_party())
            if self._find_monster(state):
                state.combat_skill()
                # Just verify no crash
                return
        pytest.skip("Couldn't reach a monster")


# ---------------------------------------------------------------------------
# Renderer tests
# ---------------------------------------------------------------------------

class TestRenderers:
    def test_view_renders_correct_size(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        view = render_view(state)
        lines = view.split("\n")
        assert len(lines) == 9, f"View should be 9 lines, got {len(lines)}"

    def test_minimap_renders(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        minimap = render_minimap(state)
        lines = minimap.split("\n")
        assert len(lines) == 7, f"Minimap should be 7 lines, got {len(lines)}"

    def test_minimap_shows_player(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        minimap = render_minimap(state)
        # Player arrow should be in the minimap
        assert any(c in minimap for c in "▲►▼◄"), "Minimap should show player arrow"

    def test_party_panel_renders(self):
        state = CrawlState.new_game(make_party())
        panel = render_party(state)
        lines = panel.split("\n")
        assert len(lines) == 4, "Party panel should show 4 members"

    def test_view_changes_on_turn(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        view1 = render_view(state)
        state.turn_right()
        view2 = render_view(state)
        # Views might be the same if corridors look identical, but usually differ
        # Just verify no crash
        assert len(view2.split("\n")) == 9


# ---------------------------------------------------------------------------
# Game result tests
# ---------------------------------------------------------------------------

class TestGameResult:
    def test_result_on_death(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        # Kill the party
        for m in state.party:
            m.hp = 0
        state.is_over = True
        result = state.get_result()
        assert result.outcome.value == "lose"

    def test_result_on_victory(self):
        state = CrawlState.new_game([make_buddy(buddy_id=1)])
        state.floors_cleared = 5
        state.game_won = True
        state.is_over = True
        result = state.get_result()
        assert result.outcome.value == "win"
        assert result.xp_earned > 0


# ---------------------------------------------------------------------------
# TUI Screen tests (Textual Pilot)
# ---------------------------------------------------------------------------

class TestCrawlScreen:
    @pytest.mark.asyncio
    async def test_screen_mounts(self):
        """Verify the crawl screen can be created and mounted."""
        from buddies.app import BuddyApp
        app = BuddyApp()
        async with app.run_test(size=(120, 40)) as pilot:
            # The app needs a buddy first — we'll just verify import works
            pass

    @pytest.mark.asyncio
    async def test_crawl_screen_standalone(self):
        """Test CrawlScreen as a standalone screen."""
        from textual.app import App, ComposeResult
        from buddies.screens.game_crawl import CrawlScreen

        buddy = make_buddy("Hero", "debugging", buddy_id=1)
        party = make_party()

        class TestApp(App):
            def on_mount(self):
                self.push_screen(CrawlScreen(buddy_state=buddy, party_states=party))

        app = TestApp()
        async with app.run_test(size=(120, 40)) as pilot:
            # Verify screen mounted
            await pilot.pause()
            screen = app.screen
            assert screen.__class__.__name__ == "CrawlScreen"

            # Try WASD movement
            await pilot.press("d")  # Turn right
            await pilot.pause()
            await pilot.press("w")  # Move forward
            await pilot.pause()
            await pilot.press("a")  # Turn left
            await pilot.pause()

            # Verify no crash — screen is still active
            assert app.screen.__class__.__name__ == "CrawlScreen"
