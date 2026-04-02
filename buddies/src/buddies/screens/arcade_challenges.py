"""ArcadeChallengesScreen — browse challenges and view leaderboards.

Two views:
- CHALLENGES: Open challenges from other players to accept
- LEADERBOARD: Top scores per game type

Local-first — shows local data always, remote sync in background.
"""

from __future__ import annotations

import time
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.games.arcade_multiplayer import (
    ArcadeMultiplayerStore,
    Challenge,
    LeaderboardEntry,
    LEADERBOARD_GAMES,
)
from buddies.core.games import GameType


# Friendly game names
GAME_NAMES: dict[str, str] = {
    "trivia": "🧠 Trivia",
    "snake": "🐍 Buffer Overflow",
    "skifree": "⛷️ Stack Descent",
    "deckbuilder": "🃏 Deploy or Die",
    "holdem": "🎰 Texas Hold'em",
    "whist": "🂡 Whist",
    "stackwars": "⚔️ StackWars",
}


class ArcadeChallengesScreen(Screen):
    """Browse arcade challenges and leaderboards."""

    CSS = """
    ArcadeChallengesScreen {
        background: $background;
    }

    #challenges-title {
        text-align: center;
        text-style: bold;
        color: $text;
        height: 1;
        margin: 1 0 0 0;
    }

    #challenges-mode {
        text-align: center;
        height: 1;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    #challenges-log {
        height: 1fr;
        border: solid $primary;
        margin: 0 1;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("c", "show_challenges", "Challenges", show=True),
        Binding("l", "show_leaderboard", "Leaderboard", show=True),
        Binding("1", "filter_1", "Trivia"),
        Binding("2", "filter_2", "Snake"),
        Binding("3", "filter_3", "SkiFree"),
        Binding("4", "filter_4", "Deckbuilder"),
        Binding("5", "filter_5", "Hold'em"),
        Binding("6", "filter_6", "Whist"),
        Binding("7", "filter_7", "StackWars"),
        Binding("a", "filter_all", "All Games", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    GAME_FILTER_MAP = {
        "1": "trivia", "2": "snake", "3": "skifree", "4": "deckbuilder",
        "5": "holdem", "6": "whist", "7": "stackwars",
    }

    def __init__(self, store: ArcadeMultiplayerStore):
        super().__init__()
        self.store = store
        self._view = "challenges"  # "challenges" or "leaderboard"
        self._game_filter: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("🏆 ARCADE MULTIPLAYER 🏆", id="challenges-title")
        yield Static("[dim]challenges[/]", id="challenges-mode")
        yield RichLog(id="challenges-log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._refresh_display()

    def _refresh_display(self):
        if self._view == "challenges":
            self._show_challenges()
        else:
            self._show_leaderboard()

    def _show_challenges(self):
        log = self.query_one("#challenges-log", RichLog)
        log.clear()

        mode = self.query_one("#challenges-mode", Static)
        filter_label = GAME_NAMES.get(self._game_filter, "All Games") if self._game_filter else "All Games"
        mode.update(f"[dim]open challenges — {filter_label}[/]")

        challenges = self.store.get_open_challenges(self._game_filter)

        if not challenges:
            log.write("[dim]No open challenges right now.[/]")
            log.write("")
            log.write("[dim]Play any game and choose 'Share Challenge' to create one![/]")
            log.write("")
            log.write("[dim]Filter: 1=Trivia 2=Snake 3=SkiFree 4=Deckbuilder 5=Hold'em 6=Whist 7=StackWars a=All[/]")
            return

        log.write(f"[bold]{len(challenges)} open challenge(s):[/bold]")
        log.write("")

        for i, ch in enumerate(challenges[:20], 1):
            game_name = GAME_NAMES.get(ch.game_type, ch.game_type)
            age = _format_age(ch.created_at)
            log.write(
                f"  [bold cyan]{i:>2}.[/bold cyan] {game_name} — "
                f"{ch.challenger_emoji} [bold]{ch.challenger_name}[/bold] "
                f"({ch.challenger_species}) scored [yellow]{ch.challenger_score_value}[/yellow]"
            )
            if ch.seed:
                log.write(f"      [dim]Seed: {ch.seed}  |  {age}[/dim]")
            else:
                log.write(f"      [dim]{age}[/dim]")
            log.write("")

        log.write("[dim]Filter: 1=Trivia 2=Snake 3=SkiFree 4=Deckbuilder 5=Hold'em 6=Whist 7=StackWars a=All[/dim]")

    def _show_leaderboard(self):
        log = self.query_one("#challenges-log", RichLog)
        log.clear()

        mode = self.query_one("#challenges-mode", Static)

        if self._game_filter:
            game_name = GAME_NAMES.get(self._game_filter, self._game_filter)
            mode.update(f"[dim]leaderboard — {game_name}[/]")
            entries = self.store.get_leaderboard(self._game_filter, limit=20)
            self._render_game_leaderboard(log, self._game_filter, entries)
        else:
            mode.update("[dim]leaderboard — all games[/]")
            # Show top 5 per game type
            for gt in LEADERBOARD_GAMES:
                entries = self.store.get_leaderboard(gt.value, limit=5)
                if entries:
                    self._render_game_leaderboard(log, gt.value, entries)
                    log.write("")

            if not any(self.store.get_leaderboard(gt.value, limit=1) for gt in LEADERBOARD_GAMES):
                log.write("[dim]No scores yet! Play some games to populate the leaderboard.[/]")

        log.write("")
        log.write("[dim]Filter: 1=Trivia 2=Snake 3=SkiFree 4=Deckbuilder 5=Hold'em 6=Whist 7=StackWars a=All[/dim]")

    def _render_game_leaderboard(
        self, log: RichLog, game_type: str, entries: list[LeaderboardEntry],
    ):
        game_name = GAME_NAMES.get(game_type, game_type)
        log.write(f"[bold]{game_name}[/bold]")

        if not entries:
            log.write("  [dim]No scores yet[/dim]")
            return

        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(entries):
            medal = medals[i] if i < 3 else f"  {i + 1}."
            log.write(
                f"  {medal} {entry.buddy_emoji} [bold]{entry.buddy_name}[/bold] "
                f"— [yellow]{entry.score_value}[/yellow]"
            )

    # ── Actions ──

    def action_show_challenges(self):
        self._view = "challenges"
        self._refresh_display()

    def action_show_leaderboard(self):
        self._view = "leaderboard"
        self._refresh_display()

    def action_filter_all(self):
        self._game_filter = None
        self._refresh_display()

    def _set_filter(self, key: str):
        self._game_filter = self.GAME_FILTER_MAP.get(key)
        self._refresh_display()

    def action_filter_1(self): self._set_filter("1")
    def action_filter_2(self): self._set_filter("2")
    def action_filter_3(self): self._set_filter("3")
    def action_filter_4(self): self._set_filter("4")
    def action_filter_5(self): self._set_filter("5")
    def action_filter_6(self): self._set_filter("6")
    def action_filter_7(self): self._set_filter("7")

    def action_back(self):
        self.dismiss(None)


def _format_age(timestamp: float) -> str:
    """Format a timestamp as relative age (e.g., '2h ago')."""
    delta = time.time() - timestamp
    if delta < 60:
        return "just now"
    elif delta < 3600:
        return f"{int(delta / 60)}m ago"
    elif delta < 86400:
        return f"{int(delta / 3600)}h ago"
    else:
        return f"{int(delta / 86400)}d ago"
