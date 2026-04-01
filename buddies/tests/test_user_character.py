"""Tests for user character derivation and party selection."""

import pytest
from collections import Counter

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.user_character import derive_user_stats, create_user_buddy_state, UserStats


def make_buddy(name="Test", buddy_id=1):
    sp = Species(name="test", emoji="T", rarity=Rarity.COMMON,
                 base_stats={"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10},
                 description="Test")
    return BuddyState(name=name, species=sp, level=5, xp=0, mood="happy",
                      stats={"debugging": 15, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10},
                      shiny=False, buddy_id=buddy_id, mood_value=50,
                      soul_description="test", hat=None, hats_owned=[])


class TestUserStats:
    def test_default_stats(self):
        stats = UserStats()
        assert stats.debugging == 10
        assert stats.total == 50

    def test_derive_from_edit_heavy_user(self):
        stats = derive_user_stats(
            tool_counts=Counter({"Edit": 100, "Write": 50, "Read": 20}),
        )
        assert stats.debugging > stats.chaos
        assert stats.debugging > 20

    def test_derive_from_agent_heavy_user(self):
        stats = derive_user_stats(
            tool_counts=Counter({"Agent": 30, "Read": 50}),
        )
        assert stats.wisdom > stats.chaos

    def test_derive_from_bash_heavy_user(self):
        stats = derive_user_stats(
            tool_counts=Counter({"Bash": 80}),
        )
        assert stats.chaos > 15

    def test_derive_from_chatty_user(self):
        stats = derive_user_stats(messages_sent=100)
        assert stats.patience > 15

    def test_derive_from_gamer(self):
        stats = derive_user_stats(
            games_played=20, games_won=15,
            game_types_played={"trivia": 5, "battle": 5, "rps": 5, "pong": 5},
        )
        assert stats.snark > 10
        assert stats.chaos > 15  # Game variety

    def test_stats_clamped(self):
        stats = derive_user_stats(
            tool_counts=Counter({"Edit": 10000}),
            messages_sent=10000,
            event_count=100000,
        )
        assert stats.debugging <= 50
        assert stats.patience <= 50

    def test_stats_minimum(self):
        stats = derive_user_stats()
        for attr in ("debugging", "chaos", "snark", "wisdom", "patience"):
            assert getattr(stats, attr) >= 5


class TestUserBuddyState:
    def test_creates_valid_state(self):
        state = create_user_buddy_state("TestUser")
        assert state.name == "TestUser"
        assert state.buddy_id == -1
        assert state.species.name == "human"

    def test_level_from_stats(self):
        high_stats = UserStats(debugging=40, chaos=30, snark=25, wisdom=35, patience=30)
        state = create_user_buddy_state("Pro", high_stats)
        assert state.level > 5  # High total stats = higher level

    def test_stats_passed_through(self):
        stats = UserStats(debugging=30, chaos=15, snark=20, wisdom=25, patience=10)
        state = create_user_buddy_state("Custom", stats)
        assert state.stats["debugging"] == 30
        assert state.stats["wisdom"] == 25


class TestPartySelectScreen:
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Textual Screen rendering quirk with push_screen in on_mount")
    async def test_screen_mounts(self):
        from textual.app import App
        from buddies.screens.party_select import PartySelectScreen

        buddies = [make_buddy("A", 1), make_buddy("B", 2), make_buddy("C", 3)]
        user = create_user_buddy_state("You")

        class TestApp(App):
            def on_mount(self):
                self.push_screen(PartySelectScreen(all_buddies=buddies, user_state=user))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "PartySelectScreen"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Textual Screen rendering quirk with push_screen in on_mount")
    async def test_toggle_user(self):
        from textual.app import App
        from buddies.screens.party_select import PartySelectScreen

        buddies = [make_buddy("A", 1)]
        user = create_user_buddy_state("You")

        class TestApp(App):
            def on_mount(self):
                self.push_screen(PartySelectScreen(all_buddies=buddies, user_state=user))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            # Toggle user on
            await pilot.press("u")
            await pilot.pause()
            # Toggle user off
            await pilot.press("u")
            await pilot.pause()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Textual Screen rendering quirk with push_screen in on_mount")
    async def test_navigate_and_select(self):
        from textual.app import App
        from buddies.screens.party_select import PartySelectScreen

        buddies = [make_buddy("A", 1), make_buddy("B", 2)]

        class TestApp(App):
            def on_mount(self):
                self.push_screen(PartySelectScreen(all_buddies=buddies))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            await pilot.press("down")  # Move to second buddy
            await pilot.pause()
            await pilot.press("space")  # Select it
            await pilot.pause()
