"""GamesScreen — the Games Arcade hub.

ASCII art arcade cabinet menu with game selection.
Each game launches as a separate pushed screen.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.screens.game_snake import SnakeScreen
from buddies.screens.game_skifree import SkiFreeScreen
from buddies.screens.game_deckbuilder import DeckbuilderScreen
from buddies.screens.game_pong import PongScreen
from buddies.screens.game_trivia import TriviaScreen
from buddies.screens.game_holdem import HoldemScreen
from buddies.screens.game_whist import WhistScreen
from buddies.screens.game_crawl import CrawlScreen
from buddies.screens.party_select import PartySelectScreen
from buddies.screens.game_mud import MudScreen
from buddies.screens.game_stackwars import StackWarsScreen


GAME_MENU = """\
[bold]Available Games:[/bold]

  [bold cyan]1[/bold cyan]  🐍 [bold]Buffer Overflow[/bold]        — Snake with StackHaven curveballs
  [bold cyan]2[/bold cyan]  ⛷️ [bold]Stack Descent[/bold]           — Ski Free, but The Auditor chases you
  [bold cyan]3[/bold cyan]  🃏 [bold]Deploy or Die[/bold]           — Deckbuilder: survive 7 sprints of production hell
  [bold cyan]4[/bold cyan]  🎰 [bold]Texas Hold'em[/bold]           — Poker with your party
  [bold cyan]5[/bold cyan]  🂡 [bold]Whist[/bold]                   — Team trick-taking
  [bold cyan]6[/bold cyan]  🧠 [bold]Trivia[/bold]                  — Coding quiz, you vs buddy
  [bold cyan]7[/bold cyan]  🏓 [bold]Pong[/bold]                    — Real-time paddle action
  [bold cyan]8[/bold cyan]  🗡️ [bold]Blobber Dungeon[/bold]          — First-person party CRPG
  [bold cyan]9[/bold cyan]  🏢 [bold]StackHaven MUD[/bold]           — Text adventure in a broken tech company
  [bold cyan]0[/bold cyan]  ⚔️ [bold]StackWars[/bold]                — Micro-4X wargame (buddy factions!)

[dim]Press a number to play  |  Esc=Back[/dim]"""


class GamesScreen(Screen):
    """The Games Arcade hub — pick a game to play."""

    BINDINGS = [
        Binding("1", "play_snake", "Snake", show=True),
        Binding("2", "play_skifree", "SkiFree", show=True),
        Binding("3", "play_deckbuilder", "Deckbuilder", show=True),
        Binding("4", "play_holdem", "Hold'em", show=True),
        Binding("5", "play_whist", "Whist", show=True),
        Binding("6", "play_trivia", "Trivia", show=True),
        Binding("7", "play_pong", "Pong", show=True),
        Binding("8", "play_crawl", "Blobber", show=True),
        Binding("9", "play_mud", "MUD", show=True),
        Binding("0", "play_stackwars", "StackWars", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    GamesScreen {
        layout: vertical;
        background: $background;
    }
    GamesScreen #arcade-display {
        height: 1fr;
        padding: 1 2;
        background: $surface;
        border: round $primary;
        margin: 1 2;
    }
    """

    def __init__(self, buddy_state: BuddyState, party_states: list[BuddyState] | None = None):
        super().__init__()
        self.buddy_state = buddy_state
        self.party_states = party_states or []
        self._last_result: GameResult | None = None
        self._pending_results: list[GameResult] = []

    def compose(self) -> ComposeResult:
        yield RichLog(id="arcade-display", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._show_menu()

    def _show_menu(self):
        display = self.query_one("#arcade-display", RichLog)
        display.clear()

        # Responsive header — scales to terminal width
        try:
            w = min(self.app.size.width - 8, 50)
        except Exception:
            w = 46
        w = max(w, 30)
        inner = w - 2
        title = "🕹️  BUDDIES ARCADE  🕹️"
        subtitle = "Insert coin... just kidding, it's free"
        display.write(f"[bold cyan]╔{'═' * inner}╗[/bold cyan]")
        display.write(f"[bold cyan]║{title:^{inner}}║[/bold cyan]")
        display.write(f"[bold cyan]║{subtitle:^{inner}}║[/bold cyan]")
        display.write(f"[bold cyan]╚{'═' * inner}╝[/bold cyan]")

        # Show who's playing
        bs = self.buddy_state
        display.write(f"\n[dim]Playing as: {bs.species.emoji} {bs.name} (Lv.{bs.level} {bs.species.name})[/dim]")

        display.write("")
        display.write(GAME_MENU)

        if self._last_result:
            r = self._last_result
            outcome_str = {
                "win": "[green]WIN[/green]",
                "lose": "[red]LOSS[/red]",
                "draw": "[yellow]DRAW[/yellow]",
            }[r.outcome.value]
            display.write("")
            display.write(f"[dim]Last game: {r.game_type.value.upper()} — {outcome_str} (+{r.xp_for_outcome} XP)[/dim]")

    def _on_game_dismissed(self, result: GameResult | None) -> None:
        """Handle game screen dismissal — forward result to app for XP, return to menu."""
        if result:
            self._last_result = result
            # Forward to app immediately so XP/mood is awarded per game
            self._pending_results.append(result)
        self._show_menu()

    def action_play_snake(self):
        self.app.push_screen(
            SnakeScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_skifree(self):
        self.app.push_screen(
            SkiFreeScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_deckbuilder(self):
        self.app.push_screen(
            DeckbuilderScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_holdem(self):
        self.app.push_screen(
            HoldemScreen(buddy_state=self.buddy_state, party_states=self.party_states),
            callback=self._on_game_dismissed,
        )

    def action_play_whist(self):
        self.app.push_screen(
            WhistScreen(buddy_state=self.buddy_state, party_states=self.party_states),
            callback=self._on_game_dismissed,
        )

    def action_play_trivia(self):
        self.app.push_screen(
            TriviaScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_pong(self):
        self.app.push_screen(
            PongScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_crawl(self):
        """Open party selection, then launch blobber dungeon with chosen party."""
        # Build user character from available session data
        user_state = None
        try:
            from buddies.core.user_character import derive_user_stats, create_user_buddy_state
            # Try to get session stats from app
            app = self.app
            observer = getattr(app, "observer", None)
            messages = getattr(app, "_messages_sent", 0)
            discussions = getattr(app, "_discussions_started", 0)

            tool_counts = observer.stats.tool_counts if observer else {}
            edit_count = observer.stats.edit_count if observer else 0
            files_touched = len(observer.stats.files_touched) if observer else 0
            event_count = observer.stats.event_count if observer else 0

            user_stats = derive_user_stats(
                tool_counts=tool_counts,
                messages_sent=messages,
                edit_count=edit_count,
                files_touched=files_touched,
                event_count=event_count,
                discussions_started=discussions,
            )
            user_state = create_user_buddy_state(name="You", stats=user_stats)
        except Exception:
            pass

        all_buddies = [self.buddy_state] + self.party_states
        self.app.push_screen(
            PartySelectScreen(all_buddies=all_buddies, user_state=user_state),
            callback=self._on_party_selected,
        )

    def _on_party_selected(self, result) -> None:
        """Handle party selection result — launch crawl or return to menu."""
        if result is None or not result:
            self._show_menu()
            return
        # result is list[BuddyState] — the chosen party
        party = result
        primary = party[0]
        others = party[1:] if len(party) > 1 else []
        self.app.push_screen(
            CrawlScreen(buddy_state=primary, party_states=others),
            callback=self._on_game_dismissed,
        )

    def action_play_stackwars(self):
        self.app.push_screen(
            StackWarsScreen(buddy_state=self.buddy_state),
            callback=self._on_game_dismissed,
        )

    def action_play_mud(self):
        self.app.push_screen(
            MudScreen(buddy_state=self.buddy_state, party_states=self.party_states),
            callback=self._on_game_dismissed,
        )

    def _coming_soon(self, name: str):
        display = self.query_one("#arcade-display", RichLog)
        display.write(f"\n[yellow]{name} is coming soon! Stay tuned.[/yellow]")

    def action_back(self):
        # Dismiss with all pending results so app can process XP for each
        self.dismiss(self._pending_results if self._pending_results else None)
