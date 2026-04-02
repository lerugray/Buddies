"""StackWarsScreen — micro-4X wargame TUI.

Designed by Claude with direction from "A Contemporary Guide to Wargame Design"
by Ray Weiss, and inspired by Avianos from UFO 50.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.stackwars import (
    StackWarsState, create_stackwars, AbilityType, FLAGS_TO_WIN,
    choose_ability, execute_action, skip_action,
    render_map, render_status, FACTION_EMOJI, FACTION_DESC,
    ABILITY_ACTIONS, faction_from_buddy,
)
from buddies.core.games.prose_games import (
    pick_stackwars_line,
    STACKWARS_TURN_START, STACKWARS_COMBAT_WIN, STACKWARS_COMBAT_LOSE,
    STACKWARS_BUILD, STACKWARS_FLAG_CAPTURED, STACKWARS_VICTORY, STACKWARS_DEFEAT,
)


class StackWarsScreen(Screen):
    """StackWars — a micro-4X wargame in your terminal."""

    BINDINGS = [
        Binding("escape", "quit_game", "Exit", show=True),
    ]

    DEFAULT_CSS = """
    StackWarsScreen {
        layout: horizontal;
        background: $background;
    }
    StackWarsScreen #sw-main {
        width: 3fr;
        height: 100%;
    }
    StackWarsScreen #sw-log {
        height: 1fr;
        padding: 0 1;
        background: $surface;
        border: round $primary;
        margin: 0 0 0 1;
    }
    StackWarsScreen #sw-input {
        dock: bottom;
        margin: 0 0 0 1;
    }
    StackWarsScreen #sw-sidebar {
        width: 1fr;
        min-width: 28;
        max-width: 36;
        height: 100%;
        margin: 0 1 0 0;
    }
    StackWarsScreen #sw-map {
        height: auto;
        max-height: 50%;
        padding: 1;
        background: $surface;
        border: round $accent;
    }
    StackWarsScreen #sw-status {
        height: auto;
        max-height: 50%;
        padding: 1;
        background: $surface;
        border: round $success;
        margin-top: 1;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.state = create_stackwars(buddy_state)
        self._faction_name = faction_from_buddy(buddy_state).value
        self._last_flags = 0

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="sw-main"):
                yield RichLog(id="sw-log", wrap=True, markup=True, auto_scroll=True)
                yield Input(id="sw-input", placeholder="Choose ability or action...")
            with Vertical(id="sw-sidebar"):
                yield Static(id="sw-map")
                yield Static(id="sw-status")
        yield Footer()

    def on_mount(self):
        log = self.query_one("#sw-log", RichLog)

        # Intro
        faction = faction_from_buddy(self.buddy_state)
        emoji = FACTION_EMOJI[faction]
        log.write("[bold]" + "=" * 45 + "[/bold]")
        log.write(f"[bold]   {emoji} STACKWARS {emoji}[/bold]")
        log.write("[bold]   A Micro-4X Wargame[/bold]")
        log.write("[bold]" + "=" * 45 + "[/bold]")
        log.write("")
        log.write(f"[bold]Your faction:[/bold] {emoji} {faction.value.title()}")
        log.write(f"[dim]{FACTION_DESC[faction]}[/dim]")
        log.write("")
        log.write(f"[dim]Hold {3} flag tiles (F) for a full round to win.[/dim]")
        log.write(f"[dim]Each turn: choose an ability, then execute its 3 actions.[/dim]")
        log.write("")

        # Show initial log
        for line in self.state.log:
            log.write(line)

        self._show_ability_prompt()
        self._update_sidebar()
        self.query_one("#sw-input", Input).focus()

    def _show_ability_prompt(self):
        log = self.query_one("#sw-log", RichLog)
        player = self.state.active_player

        if player.is_ai or self.state.game_over:
            return

        log.write(f"\n[bold]Turn {self.state.turn} — Choose an ability:[/bold]")
        available = player.available_abilities()
        for i, ability in enumerate(AbilityType):
            cd = player.cooldowns[ability.value]
            favor = player.favor[ability.value]
            bless = player.blessings[ability.value]
            if cd > 0:
                log.write(f"  [dim]{i+1}. {ability.value.upper()} (cooldown: {cd} turns)[/dim]")
            else:
                actions = ", ".join(ABILITY_ACTIONS[ability])
                bless_str = f" [yellow]Lv.{bless}[/yellow]" if bless else ""
                log.write(f"  [bold cyan]{i+1}[/bold cyan]. [bold]{ability.value.upper()}[/bold]{bless_str} — {actions}")

        log.write("\n[dim]Type a number (1-5) to choose, or 'help' for commands.[/dim]")

    def _show_action_prompt(self):
        log = self.query_one("#sw-log", RichLog)
        if not self.state.chosen_ability or self.state.game_over:
            return

        step = self.state.action_step
        actions = ABILITY_ACTIONS[self.state.chosen_ability]
        if step < len(actions):
            log.write(f"\n[bold]Action {step + 1}:[/bold] {actions[step]}")
            log.write("[dim]Type a target/choice, or 'skip' to skip this action.[/dim]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        event.input.clear()

        log = self.query_one("#sw-log", RichLog)
        log.write(f"\n[bold green]> {raw}[/bold green]")

        if self.state.game_over:
            log.write("[dim]Game is over. Press Esc to exit.[/dim]")
            return

        lines = self._process_input(raw)
        for line in lines:
            log.write(line)

        # Inject faction commentary based on what happened
        self._inject_commentary(log, lines)

        self._update_sidebar()

        # Show next prompt
        if not self.state.game_over:
            if self.state.phase == "choose_ability" and not self.state.active_player.is_ai:
                self._show_ability_prompt()
            elif self.state.chosen_ability and not self.state.active_player.is_ai:
                self._show_action_prompt()

    def _process_input(self, raw: str) -> list[str]:
        """Process player input."""
        lower = raw.lower().strip()

        # Help
        if lower in ("help", "h", "?"):
            return [
                "\n[bold]StackWars Commands[/bold]",
                "  [bold]1-5[/bold]     — Choose ability (Deploy/Build/March/Invoke/Rally)",
                "  [bold]skip[/bold]    — Skip current action",
                "  [bold]x,y[/bold]     — Target coordinates (e.g. '2,3') for build/deploy/bomb",
                "  [bold]map[/bold]     — Show the map",
                "  [bold]status[/bold]  — Show player status",
                "  [bold]units[/bold]   — List your units",
                "  [bold]help[/bold]    — This help",
                "  [bold]Esc[/bold]     — Quit game",
            ]

        if lower == "map":
            return render_map(self.state)

        if lower in ("status", "s"):
            return render_status(self.state)

        if lower == "units":
            from buddies.core.games.stackwars import UNIT_STATS
            player = self.state.active_player
            units = self.state.player_units(player.index)
            if not units:
                return ["No units."]
            lines = [f"[bold]Your units ({len(units)}):[/bold]"]
            for x, y, u in units:
                lines.append(f"  {u.emoji} {u.name} HP:{u.hp}/{u.stats['hp']} at ({x},{y})")
            return lines

        # Ability selection phase
        if self.state.phase == "choose_ability":
            ability_map = {"1": AbilityType.DEPLOY, "2": AbilityType.BUILD, "3": AbilityType.MARCH,
                           "4": AbilityType.INVOKE, "5": AbilityType.RALLY,
                           "deploy": AbilityType.DEPLOY, "build": AbilityType.BUILD,
                           "march": AbilityType.MARCH, "invoke": AbilityType.INVOKE,
                           "rally": AbilityType.RALLY}
            ability = ability_map.get(lower)
            if ability:
                return choose_ability(self.state, ability)
            return ["Choose an ability (1-5): Deploy, Build, March, Invoke, Rally"]

        # Action phase
        if self.state.chosen_ability:
            if lower == "skip":
                return skip_action(self.state)
            return execute_action(self.state, raw)

        return ["Type 'help' for commands."]

    def _inject_commentary(self, log: RichLog, lines: list[str]) -> None:
        """Add faction-flavored buddy commentary based on what just happened."""
        combined = " ".join(lines).lower()
        f = self._faction_name
        name = self.buddy_state.name

        if self.state.game_over:
            if self.state.winner == 0:
                line = pick_stackwars_line(STACKWARS_VICTORY, f)
            else:
                line = pick_stackwars_line(STACKWARS_DEFEAT, f)
            log.write(f"\n[italic dim]{name}: \"{line}\"[/italic dim]")
            return

        # Combat commentary
        if "victory" in combined or "wins" in combined:
            line = pick_stackwars_line(STACKWARS_COMBAT_WIN, f)
            log.write(f"[italic dim]{name}: \"{line}\"[/italic dim]")
        elif "repulsed" in combined or "holds" in combined:
            line = pick_stackwars_line(STACKWARS_COMBAT_LOSE, f)
            log.write(f"[italic dim]{name}: \"{line}\"[/italic dim]")

        # Build commentary
        if "built" in combined:
            line = pick_stackwars_line(STACKWARS_BUILD, f)
            log.write(f"[italic dim]{name}: \"{line}\"[/italic dim]")

        # Flag capture detection
        current_flags = self.state.count_flags(0)
        if current_flags > self._last_flags:
            line = pick_stackwars_line(
                STACKWARS_FLAG_CAPTURED, f,
                flags=current_flags, target=FLAGS_TO_WIN,
            )
            log.write(f"[italic dim]{name}: \"{line}\"[/italic dim]")
        self._last_flags = current_flags

        # Turn start commentary (when it's the player's turn and ability phase)
        if ("turn" in combined and "choose" not in combined
                and self.state.phase == "choose_ability"
                and not self.state.active_player.is_ai
                and self.state.turn > 1):
            import random
            if random.random() < 0.4:  # Don't spam every turn
                line = pick_stackwars_line(STACKWARS_TURN_START, f)
                log.write(f"[italic dim]{name}: \"{line}\"[/italic dim]")

    def _update_sidebar(self):
        # Map
        map_widget = self.query_one("#sw-map", Static)
        map_lines = render_map(self.state)
        # Legend
        map_lines.append("")
        map_lines.append("[dim]. plains  ^ mountain[/dim]")
        map_lines.append("[dim]$ server  # firewall[/dim]")
        map_lines.append("[dim]H HQ      F flag[/dim]")
        map_widget.update("\n".join(map_lines))

        # Status
        status_widget = self.query_one("#sw-status", Static)
        status_lines = render_status(self.state)
        status_widget.update("\n".join(status_lines))

    def action_quit_game(self):
        player = self.state.players[0]
        flags = self.state.count_flags(0)
        if self.state.winner == 0:
            outcome = GameOutcome.WIN
        elif self.state.winner > 0:
            outcome = GameOutcome.LOSE
        else:
            outcome = GameOutcome.DRAW

        result = GameResult(
            game_type=GameType.STACKWARS if hasattr(GameType, "STACKWARS") else GameType.BATTLE,
            outcome=outcome,
            buddy_id=self.buddy_state.buddy_id,
            turns=self.state.turn,
            details=f"flags:{flags} turn:{self.state.turn}",
        )
        self.dismiss(result)
