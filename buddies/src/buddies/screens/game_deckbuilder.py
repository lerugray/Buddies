"""DeckbuilderScreen — Deploy or Die in the terminal.

Survive 7 sprints of production hell by playing cards to generate
Dev Points and resolve incidents. Buy better cards from the shop.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameResult
from buddies.core.games.deckbuilder import (
    DeckbuilderGame, GamePhase, Card, Incident,
)
from buddies.core.games.prose_games import pick_game_line, GAME_WIN, GAME_LOSE

DECKBUILDER_START = {
    "clinical": ["Sprint 1 initiated. Incident queue loading."],
    "sarcastic": ["Oh good. Production incidents. My favorite."],
    "absurdist": ["THE SERVERS CRY OUT. THE TICKETS MULTIPLY."],
    "philosophical": ["Every sprint begins the same. Hope and dread, balanced."],
    "calm": ["Alright. Let's keep the system running."],
}

DECKBUILDER_WIN = {
    "clinical": ["7 sprints completed. Stability maintained. Mission successful."],
    "sarcastic": ["You... actually survived? Impressive. Don't get used to it."],
    "absurdist": ["THE PRODUCTION SYSTEM LIVES! AGAINST ALL ODDS, IT LIVES!"],
    "philosophical": ["Seven sprints. Each one a lesson. The system endures."],
    "calm": ["All 7 sprints survived. Well done. The codebase thanks you."],
}

DECKBUILDER_LOSE = {
    "clinical": ["Stability reached 0. System failure at sprint {sprint}."],
    "sarcastic": ["Production is down. At sprint {sprint}. Yikes."],
    "absurdist": ["THE SYSTEM HAS FALLEN. AT SPRINT {sprint}. THE TICKETS WIN."],
    "philosophical": ["The system fell at sprint {sprint}. We rebuild. We learn."],
    "calm": ["Production went down at sprint {sprint}. It happens. Try again."],
}

DECKBUILDER_RESOLVE = {
    "clinical": ["Incident resolved. System nominal."],
    "sarcastic": ["Fixed it. You're welcome, users."],
    "absurdist": ["THE INCIDENT DISSOLVES INTO THE VOID!"],
    "philosophical": ["The problem passes. Until the next one."],
    "calm": ["Resolved. Good work."],
}


class DeckbuilderScreen(Screen):
    """Deploy or Die — deckbuilder game screen."""

    BINDINGS = [
        Binding("1", "slot_1", "1", show=True),
        Binding("2", "slot_2", "2", show=True),
        Binding("3", "slot_3", "3", show=True),
        Binding("4", "slot_4", "4", show=True),
        Binding("5", "slot_5", "5", show=True),
        Binding("r", "action_resolve", "Resolve", show=True),
        Binding("e", "end_phase", "End Phase", show=True),
        Binding("n", "new_game", "New Game", show=False),
        Binding("escape", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    DeckbuilderScreen {
        layout: vertical;
        background: $background;
    }
    DeckbuilderScreen #deck-header {
        height: 1;
        content-align: center middle;
        text-align: center;
        text-style: bold;
        padding: 0 1;
    }
    DeckbuilderScreen #deck-main {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    DeckbuilderScreen #deck-commentary {
        height: 2;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, buddy_state: BuddyState):
        super().__init__()
        self.buddy_state = buddy_state
        self.game: DeckbuilderGame | None = None
        self._result: GameResult | None = None
        self._last_comment = ""
        self._message = ""
        self._pending_effect: str | None = None  # For multi-step effects
        self._pending_idx: int = -1
        self._select_mode: str = ""  # "trash", "defer", "resolve_sel", "feature_flag"

    def compose(self) -> ComposeResult:
        yield Static("", id="deck-header")
        yield RichLog(id="deck-main", wrap=True, markup=True)
        yield Static("", id="deck-commentary")
        yield Footer()

    def on_mount(self):
        self._start_game()

    def _start_game(self):
        self.game = DeckbuilderGame(buddy_state=self.buddy_state)
        self._select_mode = ""
        self._message = pick_game_line(DECKBUILDER_START, self.buddy_state)
        self._last_comment = self._message
        self._render()

    def _render(self):
        if not self.game:
            return
        g = self.game
        log = self.query_one("#deck-main", RichLog)
        log.clear()

        # Header
        stab_bars = "█" * g.stability + "░" * (g.max_stability - g.stability)
        stab_color = "green" if g.stability > 5 else ("yellow" if g.stability > 2 else "red")
        header = (
            f"[bold]Sprint {g.sprint}/{g.total_sprints}[/bold]  "
            f"Stability: [{stab_color}]{stab_bars}[/{stab_color}] {g.stability}/{g.max_stability}  "
            f"DP: [bold cyan]{g.dp_available}[/bold cyan]  "
            f"Deck:{g.deck_size} Disc:{g.discard_size}"
        )
        self.query_one("#deck-header", Static).update(header)

        if g.is_over:
            if g.won:
                log.write(f"\n[bold green]✅ PRODUCTION SURVIVED — ALL {g.total_sprints} SPRINTS COMPLETE![/bold green]\n")
                log.write(pick_game_line(DECKBUILDER_WIN, self.buddy_state))
            else:
                log.write(f"\n[bold red]💥 PRODUCTION IS DOWN — Sprint {g.sprint}[/bold red]\n")
                log.write(pick_game_line(DECKBUILDER_LOSE, self.buddy_state, sprint=g.sprint))
            log.write("\n[dim][N] New Game  [Esc] Exit[/dim]")
            self.query_one("#deck-commentary", Static).update("")
            return

        # Phase label
        phase_labels = {
            GamePhase.PLAY: "[bold cyan]PLAY PHASE[/bold cyan] — Play cards to generate DP",
            GamePhase.RESOLVE: "[bold yellow]RESOLVE PHASE[/bold yellow] — Spend DP to fix incidents",
            GamePhase.SHOP: "[bold magenta]SHOP PHASE[/bold magenta] — Buy 1 card with remaining DP",
        }
        log.write(phase_labels.get(g.phase, f"Phase: {g.phase.value}"))
        log.write("")

        # Incidents
        log.write("[bold red]INCIDENTS:[/bold red]")
        if not g.active_incidents:
            log.write("  [green]No incidents! The system is healthy.[/green]")
        else:
            for i, inc in enumerate(g.active_incidents):
                status = "[dim](ignored)[/dim]" if inc.ignored else f"[red]{inc.current_cost} DP[/red], [bold]{inc.stability_damage} dmg[/bold]"
                log.write(f"  [{i+1}] [bold]{inc.name}[/bold] — {status}")
                log.write(f"      [dim]{inc.description}[/dim]")
        log.write("")

        if g.phase == GamePhase.PLAY:
            log.write(f"[bold green]YOUR HAND:[/bold green] ({g.hand_size} cards)")
            if not g.hand:
                log.write("  [dim](empty — press E to end play phase)[/dim]")
            else:
                for i, card in enumerate(g.hand):
                    dp_str = f" → [cyan]+{card.dp_value}DP[/cyan]" if card.dp_value else ""
                    eff_str = f" [dim]({card.effect})[/dim]" if card.effect else ""
                    log.write(f"  [[bold cyan]{i+1}[/bold cyan]] [bold]{card.name}[/bold]{dp_str}{eff_str}")
                    log.write(f"       [dim]{card.description}[/dim]")
            log.write("")
            log.write(f"[dim][1-{g.hand_size}] Play card  [E] End play phase  [Esc] Quit[/dim]")

        elif g.phase == GamePhase.RESOLVE:
            log.write(f"[bold yellow]RESOLVE PHASE[/bold yellow] — DP available: [bold cyan]{g.dp_available}[/bold cyan]")
            log.write("")
            if not g.active_incidents or all(i.ignored for i in g.active_incidents):
                log.write("  [green]All incidents handled. Press [E] to continue to shop.[/green]")
            else:
                for i, inc in enumerate(g.active_incidents):
                    if not inc.ignored:
                        can_afford = g.dp_available >= inc.current_cost
                        afford_str = "[green]✓[/green]" if can_afford else "[red]✗[/red]"
                        log.write(
                            f"  [{i+1}] {afford_str} [bold]{inc.name}[/bold] — "
                            f"[red]{inc.current_cost} DP[/red] to resolve"
                        )
            log.write("")
            log.write("[dim][1-3] Resolve incident  [E] End resolve phase  [Esc] Quit[/dim]")

        elif g.phase == GamePhase.SHOP:
            log.write(f"[bold magenta]SHOP[/bold magenta] — DP available: [bold cyan]{g.dp_available}[/bold cyan]")
            log.write("")
            if self.game.prod_freeze_active:
                log.write("  [yellow]Production Freeze active — shop closed this sprint.[/yellow]")
            elif not g.shop_offerings:
                log.write("  [dim]No cards available.[/dim]")
            else:
                for i, card in enumerate(g.shop_offerings):
                    can_afford = g.dp_available >= card.cost
                    afford_str = "[green]✓[/green]" if can_afford else "[red]✗[/red]"
                    rarity_colors = {
                        "common": "white", "uncommon": "cyan",
                        "rare": "magenta", "legendary": "yellow",
                    }
                    rc = rarity_colors.get(card.rarity.value, "white")
                    log.write(
                        f"  [{i+1}] {afford_str} [{rc}][bold]{card.name}[/bold][/{rc}] "
                        f"— [red]{card.cost} DP[/red]"
                    )
                    log.write(f"       [dim]{card.description}[/dim]")
            log.write("")
            log.write("[dim][1-3] Buy card  [E] End sprint  [Esc] Quit[/dim]")

        # Message line
        if self._message:
            log.write("")
            log.write(f"[dim]→ {self._message}[/dim]")

        # Commentary
        bs = self.buddy_state
        comment = f"[dim]{bs.species.emoji} {bs.name}:[/dim] {self._last_comment}"
        self.query_one("#deck-commentary", Static).update(comment)

    def _slot_action(self, slot: int):
        """Handle numeric key press based on current phase."""
        if not self.game:
            return
        g = self.game
        idx = slot - 1  # 0-indexed

        if g.phase == GamePhase.PLAY:
            if idx >= len(g.hand):
                return
            events = g.play_card(idx)
            card_name = next((e.split(":")[1] for e in events if e.startswith("played:")), "card")
            self._message = f"Played {card_name}. DP: {g.dp_available}"

            # Handle multi-step effects
            for ev in events:
                if ev == "choose_trash":
                    self._select_mode = "trash"
                    self._message = "Choose a card from hand to trash [1-5]:"
                elif ev == "choose_refactor":
                    self._select_mode = "refactor"
                    self._message = "Choose up to 2 cards to trash [1-5], then [E] when done:"
                elif ev == "choose_defer":
                    self._select_mode = "defer"
                    self._message = "Choose an incident to defer [1-3]:"
                elif ev == "choose_feature_flag":
                    self._select_mode = "feature_flag"
                    self._message = "Feature Flag: [1] Take 3 DP  [2] Resolve cheapest free"
                elif ev.startswith("draw:"):
                    n = ev.split(":")[1]
                    self._message += f" Drew {n} card(s)."
                elif ev.startswith("intern:"):
                    dp = ev.split(":")[1]
                    self._message = f"The Intern generated {dp} DP!"
                elif ev.startswith("intern_incident:"):
                    name = ev.split(":")[1]
                    self._message += f" Intern caused incident: {name}!"
                elif ev == "double_applied":
                    self._message = f"CI Pipeline doubled that! DP: {g.dp_available}"
                elif ev == "prod_freeze":
                    self._message = "Production Freeze! No incidents OR shop this sprint."
                elif ev == "max_stability_up":
                    self._message = f"Kubernetes Cluster! Max Stability now {g.max_stability}."

        elif g.phase == GamePhase.RESOLVE:
            if self._select_mode == "defer":
                events = g.defer_incident(idx)
                self._select_mode = ""
                self._message = f"Incident deferred. It'll be back next sprint (+1 cost)."
            elif self._select_mode == "feature_flag":
                if slot == 1:
                    g.feature_flag_dp()
                    self._message = "Feature Flag: took 3 DP."
                elif slot == 2:
                    g.feature_flag_resolve()
                    self._message = "Feature Flag: cheapest incident resolved free."
                self._select_mode = ""
            else:
                if idx < len(g.active_incidents):
                    events = g.resolve_incident(idx)
                    if "insufficient_dp" in events:
                        self._message = "Not enough DP to resolve that incident."
                    elif "resolved" in (events[0] if events else ""):
                        name = events[0].split(":")[1] if events else "incident"
                        self._message = f"{name} resolved. DP remaining: {g.dp_available}"
                        self._last_comment = pick_game_line(DECKBUILDER_RESOLVE, self.buddy_state)

        elif g.phase == GamePhase.SHOP:
            if idx < len(g.shop_offerings):
                events = g.buy_card(idx)
                if "insufficient_dp" in events:
                    self._message = "Not enough DP."
                elif any(e.startswith("bought:") for e in events):
                    name = next(e.split(":")[1] for e in events if e.startswith("bought:"))
                    self._message = f"Bought {name}. Added to discard pile."

        elif self._select_mode == "trash":
            events = g.trash_from_hand(idx)
            self._select_mode = ""
            if events:
                name = events[0].split(":")[1]
                self._message = f"Trashed {name}."

        elif self._select_mode == "refactor":
            events = g.trash_from_hand(idx)
            if events:
                name = events[0].split(":")[1]
                g._draw(1)
                self._message = f"Refactored {name} — drew 1 card."

        self._render()

    def action_slot_1(self): self._slot_action(1)
    def action_slot_2(self): self._slot_action(2)
    def action_slot_3(self): self._slot_action(3)
    def action_slot_4(self): self._slot_action(4)
    def action_slot_5(self): self._slot_action(5)

    def action_action_resolve(self):
        """Move to resolve phase."""
        if not self.game:
            return
        if self.game.phase == GamePhase.PLAY:
            self.game.start_resolve_phase()
            self._message = "Resolve phase. Spend DP on incidents."
            self._render()

    def action_end_phase(self):
        if not self.game:
            return
        g = self.game
        self._select_mode = ""

        if g.phase == GamePhase.PLAY:
            g.start_resolve_phase()
            self._message = "Moving to resolve phase."

        elif g.phase == GamePhase.RESOLVE:
            g.start_shop_phase()
            self._message = "Moving to shop phase."

        elif g.phase == GamePhase.SHOP:
            events = g.end_sprint()
            for ev in events:
                if ev == "game_over":
                    self._last_comment = pick_game_line(
                        DECKBUILDER_LOSE, self.buddy_state, sprint=g.sprint
                    )
                    self._result = g.get_result()
                elif ev == "win":
                    self._last_comment = pick_game_line(DECKBUILDER_WIN, self.buddy_state)
                    self._result = g.get_result()
                elif ev.startswith("damage:"):
                    parts = ev.split(":")
                    self._message = f"{parts[1]} unresolved — {parts[2]} stability damage!"
                elif ev.startswith("sprint_start:"):
                    sprint = ev.split(":")[1]
                    self._message = f"Sprint {sprint} begins!"

        self._render()

    def action_new_game(self):
        self._result = None
        self._start_game()

    def action_back(self):
        self.dismiss(self._result)
