"""TUI screen walkthrough tests — verify every screen mounts and navigates.

Uses Textual's Pilot to simulate keyboard navigation through the entire app.
Catches crashes, import errors, and rendering bugs before the user sees them.
"""

import pytest

from buddies.core.buddy_brain import BuddyState, Species, Rarity


def make_buddy(name="Hero", dominant="debugging", buddy_id=1):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 25
    sp = Species(
        name="phoenix", emoji="🔥", rarity=Rarity.EPIC,
        base_stats=stats, description="Test buddy",
    )
    return BuddyState(
        name=name, species=sp, level=5, xp=100, mood="happy",
        stats=stats, shiny=False, buddy_id=buddy_id, mood_value=60,
        soul_description="test", hat=None, hats_owned=["tinyduck"],
    )


def make_party():
    return [
        make_buddy("Debuggy", "debugging", 2),
        make_buddy("Chaotic", "chaos", 3),
        make_buddy("Snarky", "snark", 4),
    ]


# ---------------------------------------------------------------------------
# Game screen standalone tests — each game screen mounts and accepts input
# ---------------------------------------------------------------------------

class TestGameScreens:
    """Test each game screen individually via a minimal test app."""

    @pytest.fixture
    def buddy(self):
        return make_buddy()

    @pytest.fixture
    def party(self):
        return make_party()

    @pytest.mark.asyncio
    async def test_rps_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_rps import RPSScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(RPSScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "RPSScreen"
            # Play a round
            await pilot.press("1")  # Throw rock
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_blackjack_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_blackjack import BlackjackScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(BlackjackScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "BlackjackScreen"
            # Hit then stand
            await pilot.press("h")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_battle_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_battle import BattleScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(BattleScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "BattleScreen"
            # Attack
            await pilot.press("1")
            await pilot.pause()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Textual render_strips internals bug with timer-driven Static updates")
    async def test_pong_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_pong import PongScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(PongScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "PongScreen"
            # Move paddle
            await pilot.press("w")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            # Pause and unpause
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_trivia_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_trivia import TriviaScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(TriviaScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "TriviaScreen"
            # Answer first 3 questions
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_holdem_screen(self, buddy, party):
        from textual.app import App
        from buddies.screens.game_holdem import HoldemScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(HoldemScreen(buddy_state=buddy, party_states=party))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "HoldemScreen"
            # Call
            await pilot.press("c")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_whist_screen(self, buddy, party):
        from textual.app import App
        from buddies.screens.game_whist import WhistScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(WhistScreen(buddy_state=buddy, party_states=party))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "WhistScreen"
            # Play first card
            await pilot.press("1")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_dungeon_screen(self, buddy):
        from textual.app import App
        from buddies.screens.game_dungeon import DungeonScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(DungeonScreen(buddy_state=buddy))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "DungeonScreen"
            # Advance through rooms
            await pilot.press("space")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_crawl_screen(self, buddy, party):
        from textual.app import App
        from buddies.screens.game_crawl import CrawlScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(CrawlScreen(buddy_state=buddy, party_states=party))

        async with TestApp().run_test(size=(120, 35)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "CrawlScreen"
            # WASD movement
            await pilot.press("w")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_games_hub(self, buddy, party):
        from textual.app import App
        from buddies.screens.games import GamesScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(GamesScreen(buddy_state=buddy, party_states=party))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "GamesScreen"


# ---------------------------------------------------------------------------
# Non-game screen tests
# ---------------------------------------------------------------------------

class TestNonGameScreens:
    """Test non-game modal screens mount correctly."""

    @pytest.fixture
    def buddy(self):
        return make_buddy()

    @pytest.mark.asyncio
    async def test_achievements_screen(self):
        from textual.app import App
        from buddies.screens.achievements import AchievementsScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(AchievementsScreen(unlocked_ids=set()))

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "AchievementsScreen"

    @pytest.mark.asyncio
    async def test_config_health_screen(self):
        from textual.app import App
        from buddies.screens.config_health import ConfigHealthScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(ConfigHealthScreen())

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "ConfigHealthScreen"

    @pytest.mark.asyncio
    async def test_conversations_screen(self):
        from textual.app import App
        from buddies.screens.conversations import ConversationsScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(ConversationsScreen())

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "ConversationsScreen"

    @pytest.mark.asyncio
    async def test_tool_browser_screen(self):
        from textual.app import App
        from buddies.screens.tool_browser import ToolBrowserScreen

        class TestApp(App):
            def on_mount(self):
                self.push_screen(ToolBrowserScreen())

        async with TestApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert pilot.app.screen.__class__.__name__ == "ToolBrowserScreen"


# ---------------------------------------------------------------------------
# Core system import tests — verify all modules load without errors
# ---------------------------------------------------------------------------

class TestImports:
    """Verify all key modules import cleanly."""

    def test_app_imports(self):
        from buddies.app import BuddyApp
        assert BuddyApp is not None

    def test_all_screens_import(self):
        from buddies.screens.party import PartyScreen
        from buddies.screens.discussion import DiscussionScreen
        from buddies.screens.conversations import ConversationsScreen
        from buddies.screens.tool_browser import ToolBrowserScreen
        from buddies.screens.config_health import ConfigHealthScreen
        from buddies.screens.achievements import AchievementsScreen
        from buddies.screens.bbs import BBSScreen
        from buddies.screens.wiki import WikiScreen
        from buddies.screens.memory import MemoryScreen
        from buddies.screens.games import GamesScreen
        from buddies.screens.game_rps import RPSScreen
        from buddies.screens.game_blackjack import BlackjackScreen
        from buddies.screens.game_battle import BattleScreen
        from buddies.screens.game_pong import PongScreen
        from buddies.screens.game_trivia import TriviaScreen
        from buddies.screens.game_holdem import HoldemScreen
        from buddies.screens.game_whist import WhistScreen
        from buddies.screens.game_dungeon import DungeonScreen
        from buddies.screens.game_crawl import CrawlScreen

    def test_all_core_modules_import(self):
        from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
        from buddies.core.prose import ProseEngine
        from buddies.core.discussion import DiscussionEngine
        from buddies.core.conversation import ConversationLog
        from buddies.core.config_intel import ConfigIntelligence
        from buddies.core.token_guardian import TokenGuardian
        from buddies.core.model_tracker import ModelTracker
        from buddies.core.achievements import ACHIEVEMENTS
        from buddies.core.personality_drift import drift_for_game
        from buddies.core.idle_life import IdleLife
        from buddies.core.relationships import RelationshipManager
        from buddies.core.memory import MemoryManager
        from buddies.core.obsidian_vault import ObsidianVault
        from buddies.core.machine_detect import MachineInfo
        import buddies.core.readme_intel
        import buddies.core.code_map

    def test_all_game_engines_import(self):
        from buddies.core.games import GameType, GameOutcome, GameResult
        from buddies.core.games.engine import GamePersonality
        from buddies.core.games.rps import RPSGame
        from buddies.core.games.blackjack import BlackjackGame
        from buddies.core.games.battle import Battle
        from buddies.core.games.pong import PongGame
        from buddies.core.games.trivia import TriviaGame
        from buddies.core.games.holdem import HoldemGame
        from buddies.core.games.whist import WhistGame
        from buddies.core.games.dungeon import DungeonGame
        from buddies.core.games.crawl import CrawlState

    def test_species_catalog_has_70(self):
        from buddies.core.buddy_brain import SPECIES_CATALOG
        assert len(SPECIES_CATALOG) == 70

    def test_achievements_count(self):
        from buddies.core.achievements import ACHIEVEMENTS
        assert len(ACHIEVEMENTS) >= 49  # Should have at least 49
