"""BattleScreen — JRPG-style turn-based combat.

Goofy Pokemon-lite fights against coding-themed enemies.
Press 1-4 to pick a move. Buddy stats determine available moves.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult, GameOutcome
from buddies.core.games.battle import (
    Battle, BattleTurn, TYPE_EMOJI, MoveType,
)
from buddies.core.games.prose_games import (
    pick_game_line, BATTLE_INTRO, BATTLE_ATTACK, BATTLE_CRIT,
    BATTLE_FAINT, BATTLE_VICTORY,
)


class BattleScreen(Screen):
    """JRPG battle screen — turn-based combat against coding monsters."""

    BINDINGS = [
        Binding("1", "move_1", "Move 1", show=True),
        Binding("2", "move_2", "Move 2", show=True),
        Binding("3", "move_3", "Move 3", show=True),
        Binding("4", "move_4", "Move 4", show=True),
        Binding("n", "new_battle", "New Battle", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    BattleScreen {
        layout: vertical;
        background: $background;
    }
    BattleScreen #battle-header {
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    BattleScreen #battle-field {
        height: auto;
        min-height: 6;
        max-height: 8;
        padding: 0 2;
    }
    BattleScreen #battle-moves {
        height: auto;
        max-height: 4;
        padding: 0 2;
        color: $text;
    }
    BattleScreen #battle-log {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.battle: Battle | None = None
        self._result: GameResult | None = None
        self._battles_fought: int = 0
        self._battles_won: int = 0

    def compose(self) -> ComposeResult:
        yield Static("⚔️ BATTLE ⚔️", id="battle-header")
        yield Static("", id="battle-field")
        yield Static("", id="battle-moves")
        yield RichLog(id="battle-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self._start_battle()

    def _start_battle(self):
        self.battle = Battle(buddy_state=self.buddy_state)
        self._result = None
        log = self.query_one("#battle-log", RichLog)
        log.clear()

        enemy = self.battle.enemy_fighter
        buddy = self.battle.buddy

        # Intro
        log.write(pick_game_line(BATTLE_INTRO, self.buddy_state, enemy=enemy.name))
        log.write(f"[bold]{enemy.emoji} {enemy.name}[/bold] — {TYPE_EMOJI[enemy.primary_type]} {enemy.primary_type.value.upper()}")
        log.write("")

        if self._battles_fought > 0:
            log.write(f"[dim]Record: {self._battles_won}W / {self._battles_fought - self._battles_won}L[/dim]")
            log.write("")

        self._update_field()
        self._update_moves()
        log.write("[dim]Pick a move (1-4)  |  [bold]N[/bold]=New battle  [bold]Esc[/bold]=Back[/dim]")

    def _update_field(self):
        """Update the battle field display showing both fighters."""
        if not self.battle:
            return
        field = self.query_one("#battle-field", Static)
        buddy = self.battle.buddy
        enemy = self.battle.enemy_fighter

        field.update(
            f"  {buddy.emoji} [bold]{buddy.name}[/bold]  "
            f"HP: {buddy.hp_bar()}\n"
            f"  [dim]{'─' * 40}[/dim]\n"
            f"  {enemy.emoji} [bold]{enemy.name}[/bold]  "
            f"HP: {enemy.hp_bar()}"
        )

    def _update_moves(self):
        """Show available moves."""
        if not self.battle or self.battle.is_over:
            moves_display = self.query_one("#battle-moves", Static)
            moves_display.update("")
            return

        moves_display = self.query_one("#battle-moves", Static)
        moves = self.battle.buddy.moves
        parts = []
        for i, move in enumerate(moves):
            emoji = TYPE_EMOJI[move.move_type]
            heal_tag = " [green]heal[/green]" if move.heals else ""
            buff_tag = " [cyan]buff[/cyan]" if move.buff_defense and not move.heals else ""
            parts.append(
                f"  [bold]{i+1}[/bold] {emoji} {move.name} "
                f"(pow:{move.power} acc:{int(move.accuracy*100)}%{heal_tag}{buff_tag})"
            )
        moves_display.update("\n".join(parts))

    def _do_turn(self, move_index: int):
        """Execute a full turn: player attacks, then enemy attacks."""
        if not self.battle or self.battle.is_over:
            return

        log = self.query_one("#battle-log", RichLog)

        # Player's turn
        turn = self.battle.player_attack(move_index)
        self._render_turn(log, turn, is_player=True)

        self._update_field()

        if self.battle.is_over:
            self._show_outcome(log)
            return

        # Enemy's turn
        enemy_turn = self.battle.enemy_attack()
        self._render_turn(log, enemy_turn, is_player=False)

        self._update_field()
        log.write("")

        if self.battle.is_over:
            self._show_outcome(log)

    def _render_turn(self, log: RichLog, turn: BattleTurn, is_player: bool):
        """Render a single turn to the battle log."""
        move = turn.move
        emoji = TYPE_EMOJI[move.move_type]

        if turn.is_miss:
            log.write(f"  {turn.attacker} uses {emoji} {move.name}... [dim]MISS![/dim]")
            return

        if turn.healed > 0:
            log.write(f"  {turn.attacker} uses {emoji} {move.name}! [green]+{turn.healed} HP[/green]")
            return

        if turn.damage == 0 and move.buff_defense:
            log.write(f"  {turn.attacker} uses {emoji} {move.name}! [cyan]Defense up![/cyan]")
            if move.name == "Sit and Wait":
                log.write(f"  [cyan]Next attack will deal double damage![/cyan]")
            return

        # Damage turn
        if is_player:
            line = pick_game_line(BATTLE_ATTACK, self.buddy_state,
                                  move=move.name, damage=turn.damage)
            log.write(f"  {line}")
        else:
            log.write(f"  {turn.attacker} uses {emoji} {move.name}! [red]-{turn.damage} HP[/red]")

        # Effectiveness
        if turn.effectiveness == "super":
            log.write(f"  [yellow]It's super effective![/yellow]")
        elif turn.effectiveness == "not_very":
            log.write(f"  [dim]Not very effective...[/dim]")

        # Crit
        if turn.is_crit:
            log.write(f"  {pick_game_line(BATTLE_CRIT, self.buddy_state, damage=turn.damage)}")

    def _show_outcome(self, log: RichLog):
        """Display battle outcome."""
        if not self.battle:
            return

        self._result = self.battle.get_result()
        self._battles_fought += 1
        self._update_moves()  # Clear move display

        log.write("")

        if self.battle.outcome == GameOutcome.WIN:
            self._battles_won += 1
            enemy_name = self.battle.enemy_fighter.name
            xp = self._result.xp_for_outcome
            log.write(pick_game_line(BATTLE_VICTORY, self.buddy_state,
                                      enemy=enemy_name, xp=xp))
            log.write(f"[green bold]VICTORY![/green bold] +{xp} XP")
        else:
            log.write(pick_game_line(BATTLE_FAINT, self.buddy_state))
            log.write(f"[red]Defeated...[/red] +{self._result.xp_for_outcome} XP (consolation)")

        log.write(f"[dim][bold]N[/bold]=New battle  [bold]Esc[/bold]=Back[/dim]")

    def action_move_1(self):
        self._do_turn(0)

    def action_move_2(self):
        self._do_turn(1)

    def action_move_3(self):
        self._do_turn(2)

    def action_move_4(self):
        self._do_turn(3)

    def action_new_battle(self):
        if self._result:
            self.dismiss(self._result)
            return
        self._start_battle()

    def action_back(self):
        self.dismiss(self._result)
