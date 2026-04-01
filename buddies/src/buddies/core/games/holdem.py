"""Texas Hold'em engine — simplified No-Limit Hold'em.

You + up to 4 party buddies at a table. Buddies bet, bluff, and fold
based on personality stats. Simplified hand evaluation (no side pots).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from itertools import combinations

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state
from buddies.core.games.card_common import Card, Deck, Suit, RANK_NAMES


# ---------------------------------------------------------------------------
# Hand rankings
# ---------------------------------------------------------------------------

class HandRank(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


HAND_RANK_NAMES = {
    HandRank.HIGH_CARD: "High Card",
    HandRank.PAIR: "Pair",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.THREE_KIND: "Three of a Kind",
    HandRank.STRAIGHT: "Straight",
    HandRank.FLUSH: "Flush",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FOUR_KIND: "Four of a Kind",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    HandRank.ROYAL_FLUSH: "Royal Flush",
}


def evaluate_hand(cards: list[Card]) -> tuple[HandRank, list[int]]:
    """Evaluate the best 5-card hand from 5-7 cards.

    Returns (HandRank, tiebreaker_values) for comparison.
    """
    best_rank = HandRank.HIGH_CARD
    best_kickers: list[int] = []

    # Try all 5-card combinations
    for combo in combinations(cards, 5):
        rank, kickers = _eval_five(list(combo))
        if (rank, kickers) > (best_rank, best_kickers):
            best_rank = rank
            best_kickers = kickers

    return best_rank, best_kickers


def _eval_five(cards: list[Card]) -> tuple[HandRank, list[int]]:
    """Evaluate exactly 5 cards."""
    ranks = sorted([c.rank if c.rank != 1 else 14 for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    is_flush = len(set(suits)) == 1

    # Check straight (including ace-low: A-2-3-4-5)
    is_straight = False
    straight_high = 0
    if ranks == list(range(ranks[0], ranks[0] - 5, -1)):
        is_straight = True
        straight_high = ranks[0]
    elif ranks == [14, 5, 4, 3, 2]:  # Ace-low straight
        is_straight = True
        straight_high = 5

    # Count ranks
    from collections import Counter
    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)
    count_ranks = sorted(rank_counts.keys(), key=lambda r: (rank_counts[r], r), reverse=True)

    if is_flush and is_straight:
        if straight_high == 14 and ranks[1] == 13:
            return HandRank.ROYAL_FLUSH, [straight_high]
        return HandRank.STRAIGHT_FLUSH, [straight_high]
    if counts == [4, 1]:
        return HandRank.FOUR_KIND, count_ranks
    if counts == [3, 2]:
        return HandRank.FULL_HOUSE, count_ranks
    if is_flush:
        return HandRank.FLUSH, ranks
    if is_straight:
        return HandRank.STRAIGHT, [straight_high]
    if counts == [3, 1, 1]:
        return HandRank.THREE_KIND, count_ranks
    if counts == [2, 2, 1]:
        return HandRank.TWO_PAIR, count_ranks
    if counts == [2, 1, 1, 1]:
        return HandRank.PAIR, count_ranks

    return HandRank.HIGH_CARD, ranks


# ---------------------------------------------------------------------------
# Player / seat at the table
# ---------------------------------------------------------------------------

@dataclass
class Seat:
    """A seat at the poker table."""
    name: str
    emoji: str
    is_player: bool = False
    personality: GamePersonality | None = None
    buddy_state: BuddyState | None = None

    hole_cards: list[Card] = field(default_factory=list)
    chips: int = 100
    current_bet: int = 0
    total_bet_this_round: int = 0
    is_folded: bool = False
    is_all_in: bool = False

    @property
    def is_active(self) -> bool:
        return not self.is_folded and self.chips > 0

    def reset_for_hand(self):
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet_this_round = 0
        self.is_folded = False
        self.is_all_in = False


class BettingPhase(IntEnum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4


PHASE_NAMES = {
    BettingPhase.PREFLOP: "Pre-Flop",
    BettingPhase.FLOP: "Flop",
    BettingPhase.TURN: "Turn",
    BettingPhase.RIVER: "River",
    BettingPhase.SHOWDOWN: "Showdown",
}


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------

@dataclass
class HoldemGame:
    """Texas Hold'em game state."""
    player_state: BuddyState
    party_states: list[BuddyState] = field(default_factory=list)

    seats: list[Seat] = field(default_factory=list)
    community: list[Card] = field(default_factory=list)
    deck: Deck = field(default_factory=Deck)
    pot: int = 0
    phase: BettingPhase = BettingPhase.PREFLOP
    current_bet: int = 0  # The bet everyone needs to match
    small_blind: int = 1
    big_blind: int = 2

    # Tracking
    hands_played: int = 0
    is_over: bool = False  # True when player is broke or only one left
    hand_over: bool = False
    winner_seat: Seat | None = None
    winning_hand_name: str = ""

    # Action log for UI
    action_log: list[str] = field(default_factory=list)
    _waiting_for_player: bool = False

    def __post_init__(self):
        self._setup_seats()

    def _setup_seats(self):
        """Create seats from player + party buddies."""
        # Player always seat 0 (bottom of table)
        self.seats = [Seat(
            name="You",
            emoji="👤",
            is_player=True,
            chips=100,
        )]

        # Add party buddies (up to 4)
        for bs in self.party_states[:4]:
            p = personality_from_state(bs)
            self.seats.append(Seat(
                name=bs.name,
                emoji=bs.species.emoji,
                personality=p,
                buddy_state=bs,
                chips=100,
            ))

        # Need at least 2 players — add a house dealer buddy if solo
        if len(self.seats) < 2:
            self.seats.append(Seat(
                name=self.player_state.name,
                emoji=self.player_state.species.emoji,
                personality=personality_from_state(self.player_state),
                buddy_state=self.player_state,
                chips=100,
            ))

    def start_hand(self):
        """Start a new hand — shuffle, deal, blinds."""
        self.hand_over = False
        self.winner_seat = None
        self.winning_hand_name = ""
        self.action_log = []
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.phase = BettingPhase.PREFLOP

        # Reset seats
        for seat in self.seats:
            seat.reset_for_hand()

        # Remove busted players (except player — game over if player busts)
        self.seats = [s for s in self.seats if s.chips > 0 or s.is_player]

        if self.seats[0].chips <= 0:
            self.is_over = True
            return

        active = [s for s in self.seats if s.chips > 0]
        if len(active) < 2:
            self.is_over = True
            return

        # Shuffle and deal
        self.deck = Deck()
        self.deck.shuffle()

        for seat in self.seats:
            if seat.chips > 0:
                seat.hole_cards = self.deck.deal(2)

        # Post blinds
        active_seats = [s for s in self.seats if s.chips > 0]
        if len(active_seats) >= 2:
            self._post_blind(active_seats[0], self.small_blind, "small blind")
            self._post_blind(active_seats[1], self.big_blind, "big blind")
            self.current_bet = self.big_blind

        self.hands_played += 1
        self._waiting_for_player = True

        # AI acts before player in preflop (players after big blind)
        self._ai_betting_round_before_player()

    def _post_blind(self, seat: Seat, amount: int, label: str):
        actual = min(amount, seat.chips)
        seat.chips -= actual
        seat.current_bet = actual
        seat.total_bet_this_round = actual
        self.pot += actual
        self.action_log.append(f"{seat.emoji} {seat.name} posts {label} ({actual})")

    def _ai_betting_round_before_player(self):
        """Let AI seats act before the player in current round."""
        # In preflop, AI after big blind but before player acts
        # For simplicity, just mark that we're waiting for player
        pass

    # -----------------------------------------------------------------------
    # Player actions
    # -----------------------------------------------------------------------

    def player_fold(self):
        """Player folds."""
        if not self._waiting_for_player:
            return
        self.seats[0].is_folded = True
        self.action_log.append("👤 You fold.")
        self._waiting_for_player = False
        self._finish_betting_round()

    def player_call(self):
        """Player calls the current bet."""
        if not self._waiting_for_player:
            return
        seat = self.seats[0]
        to_call = self.current_bet - seat.current_bet
        actual = min(to_call, seat.chips)
        seat.chips -= actual
        seat.current_bet += actual
        seat.total_bet_this_round += actual
        self.pot += actual

        if actual == 0:
            self.action_log.append("👤 You check.")
        else:
            self.action_log.append(f"👤 You call ({actual}).")

        if seat.chips == 0:
            seat.is_all_in = True
            self.action_log.append("👤 You are ALL IN!")

        self._waiting_for_player = False
        self._ai_betting_round_after_player()

    def player_raise(self, amount: int = 0):
        """Player raises."""
        if not self._waiting_for_player:
            return
        seat = self.seats[0]
        if amount == 0:
            amount = min(self.big_blind * 2, seat.chips)

        to_call = self.current_bet - seat.current_bet
        total_cost = to_call + amount
        actual = min(total_cost, seat.chips)
        seat.chips -= actual
        seat.current_bet += actual
        seat.total_bet_this_round += actual
        self.pot += actual
        self.current_bet = seat.current_bet

        self.action_log.append(f"👤 You raise to {seat.current_bet}.")

        if seat.chips == 0:
            seat.is_all_in = True
            self.action_log.append("👤 You are ALL IN!")

        self._waiting_for_player = False
        self._ai_betting_round_after_player()

    def player_all_in(self):
        """Player goes all in."""
        if not self._waiting_for_player:
            return
        seat = self.seats[0]
        amount = seat.chips
        seat.current_bet += amount
        seat.total_bet_this_round += amount
        self.pot += amount
        seat.chips = 0
        seat.is_all_in = True
        if seat.current_bet > self.current_bet:
            self.current_bet = seat.current_bet

        self.action_log.append(f"👤 You go ALL IN! ({amount})")
        self._waiting_for_player = False
        self._ai_betting_round_after_player()

    # -----------------------------------------------------------------------
    # AI actions
    # -----------------------------------------------------------------------

    def _ai_betting_round_after_player(self):
        """All AI seats act after the player."""
        for seat in self.seats[1:]:
            if seat.is_folded or seat.is_all_in or seat.chips <= 0:
                continue
            self._ai_act(seat)

        self._finish_betting_round()

    def _ai_act(self, seat: Seat):
        """AI seat makes a decision based on personality and hand strength."""
        p = seat.personality
        if not p:
            # Fallback — just call
            self._ai_call(seat)
            return

        to_call = self.current_bet - seat.current_bet

        # Evaluate hand strength (rough estimate)
        hand_strength = self._estimate_hand_strength(seat)

        # Decision matrix
        if hand_strength > 0.8:
            # Strong hand — raise
            if p.should_be_aggressive() or random.random() < 0.6:
                self._ai_raise(seat)
            else:
                self._ai_call(seat)
        elif hand_strength > 0.5:
            # Decent hand
            if to_call == 0:
                # Free to check
                self._ai_call(seat)
            elif p.should_bluff():
                self._ai_raise(seat)
            elif p.should_play_optimal() or random.random() < 0.5:
                self._ai_call(seat)
            else:
                self._ai_fold(seat)
        elif hand_strength > 0.25:
            # Weak-ish hand
            if to_call == 0:
                self._ai_call(seat)
            elif p.should_bluff():
                self._ai_raise(seat)
            elif p.patience_factor > 0.4 and to_call <= self.big_blind:
                self._ai_call(seat)
            else:
                self._ai_fold(seat)
        else:
            # Bad hand
            if to_call == 0:
                self._ai_call(seat)
            elif p.should_wild_card():
                self._ai_raise(seat)  # YOLO
            elif p.should_bluff() and random.random() < 0.3:
                self._ai_raise(seat)
            else:
                self._ai_fold(seat)

    def _estimate_hand_strength(self, seat: Seat) -> float:
        """Rough hand strength estimate 0-1."""
        cards = seat.hole_cards + self.community

        if len(cards) < 2:
            return 0.5

        if len(cards) >= 5:
            rank, _ = evaluate_hand(cards)
            return min(rank.value / 9.0 + 0.2, 1.0)

        # Preflop — just evaluate hole cards
        c1, c2 = seat.hole_cards
        r1 = c1.rank if c1.rank != 1 else 14
        r2 = c2.rank if c2.rank != 1 else 14
        high = max(r1, r2)
        low = min(r1, r2)
        suited = c1.suit == c2.suit
        paired = r1 == r2

        strength = 0.2
        if paired:
            strength = 0.5 + (high / 14) * 0.4
        else:
            strength = (high / 14) * 0.35 + (low / 14) * 0.15
            if suited:
                strength += 0.1
            if abs(r1 - r2) <= 2:  # Connectors
                strength += 0.05

        return min(strength, 1.0)

    def _ai_call(self, seat: Seat):
        to_call = self.current_bet - seat.current_bet
        actual = min(to_call, seat.chips)
        seat.chips -= actual
        seat.current_bet += actual
        seat.total_bet_this_round += actual
        self.pot += actual

        if actual == 0:
            self.action_log.append(f"{seat.emoji} {seat.name} checks.")
        else:
            self.action_log.append(f"{seat.emoji} {seat.name} calls ({actual}).")
            if seat.chips == 0:
                seat.is_all_in = True

    def _ai_raise(self, seat: Seat):
        to_call = self.current_bet - seat.current_bet
        raise_amt = min(self.big_blind * 2, seat.chips - to_call)
        if raise_amt <= 0:
            self._ai_call(seat)
            return

        total = to_call + raise_amt
        actual = min(total, seat.chips)
        seat.chips -= actual
        seat.current_bet += actual
        seat.total_bet_this_round += actual
        self.pot += actual
        self.current_bet = max(self.current_bet, seat.current_bet)

        self.action_log.append(f"{seat.emoji} {seat.name} raises to {seat.current_bet}!")
        if seat.chips == 0:
            seat.is_all_in = True
            self.action_log.append(f"{seat.emoji} {seat.name} is ALL IN!")

    def _ai_fold(self, seat: Seat):
        seat.is_folded = True
        self.action_log.append(f"{seat.emoji} {seat.name} folds.")

    # -----------------------------------------------------------------------
    # Phase progression
    # -----------------------------------------------------------------------

    def _finish_betting_round(self):
        """End the current betting round, advance phase."""
        active = [s for s in self.seats if s.is_active]

        # Only one player left — they win
        if len(active) <= 1:
            self.winner_seat = active[0] if active else self.seats[0]
            self.winning_hand_name = "Last one standing"
            self.winner_seat.chips += self.pot
            self.hand_over = True
            self.action_log.append(
                f"\n{self.winner_seat.emoji} {self.winner_seat.name} wins the pot ({self.pot})!"
            )
            return

        # Reset bets for next phase
        for s in self.seats:
            s.current_bet = 0

        self.current_bet = 0
        self.phase = BettingPhase(self.phase + 1)

        if self.phase == BettingPhase.FLOP:
            self.community.extend(self.deck.deal(3))
            self.action_log.append(f"\n[bold]═══ FLOP ═══[/bold]")
            self._waiting_for_player = not self.seats[0].is_folded and not self.seats[0].is_all_in
            if not self._waiting_for_player:
                self._auto_advance()
        elif self.phase == BettingPhase.TURN:
            self.community.extend(self.deck.deal(1))
            self.action_log.append(f"\n[bold]═══ TURN ═══[/bold]")
            self._waiting_for_player = not self.seats[0].is_folded and not self.seats[0].is_all_in
            if not self._waiting_for_player:
                self._auto_advance()
        elif self.phase == BettingPhase.RIVER:
            self.community.extend(self.deck.deal(1))
            self.action_log.append(f"\n[bold]═══ RIVER ═══[/bold]")
            self._waiting_for_player = not self.seats[0].is_folded and not self.seats[0].is_all_in
            if not self._waiting_for_player:
                self._auto_advance()
        elif self.phase == BettingPhase.SHOWDOWN:
            self._showdown()

    def _auto_advance(self):
        """When player is folded/all-in, auto-play AI rounds to showdown."""
        for seat in self.seats[1:]:
            if seat.is_folded or seat.is_all_in or seat.chips <= 0:
                continue
            self._ai_act(seat)
        self._finish_betting_round()

    def _showdown(self):
        """Evaluate all remaining hands and determine winner."""
        active = [s for s in self.seats if not s.is_folded]
        self.hand_over = True

        if not active:
            return

        best_seat = None
        best_eval = (HandRank.HIGH_CARD, [])

        self.action_log.append(f"\n[bold]═══ SHOWDOWN ═══[/bold]")

        for seat in active:
            all_cards = seat.hole_cards + self.community
            rank, kickers = evaluate_hand(all_cards)
            hand_name = HAND_RANK_NAMES[rank]

            hole_str = " ".join(c.rich_str() for c in seat.hole_cards)
            self.action_log.append(f"{seat.emoji} {seat.name}: {hole_str} — [bold]{hand_name}[/bold]")

            if (rank, kickers) > best_eval:
                best_eval = (rank, kickers)
                best_seat = seat
                self.winning_hand_name = hand_name

        if best_seat:
            self.winner_seat = best_seat
            best_seat.chips += self.pot
            self.action_log.append(
                f"\n{best_seat.emoji} [bold]{best_seat.name}[/bold] wins with {self.winning_hand_name}! (+{self.pot} chips)"
            )

    # -----------------------------------------------------------------------
    # State queries
    # -----------------------------------------------------------------------

    @property
    def waiting_for_player(self) -> bool:
        return self._waiting_for_player and not self.hand_over

    @property
    def player_seat(self) -> Seat:
        return self.seats[0]

    @property
    def to_call(self) -> int:
        return max(0, self.current_bet - self.seats[0].current_bet)

    def get_result(self) -> GameResult:
        """Build a game result. Called when player leaves the table."""
        player_chips = self.seats[0].chips
        if player_chips > 100:
            outcome = GameOutcome.WIN
            xp = 25
            mood = 5
        elif player_chips < 100:
            outcome = GameOutcome.LOSE
            xp = 8
            mood = -2
        else:
            outcome = GameOutcome.DRAW
            xp = 15
            mood = 0

        return GameResult(
            game_type=GameType.HOLDEM,
            outcome=outcome,
            buddy_id=0,
            score={"chips": player_chips, "hands": self.hands_played,
                   "started_with": 100},
            xp_earned=xp,
            mood_delta=mood,
        )

    def render_table(self) -> str:
        """Render the poker table as ASCII art with buddy profile pics.

        Layout (example with 4 players):

                  🐙 Octo (52)
              ┌─────────────────┐
        🦊 Fox│   [community]   │🐱 Cat
          (98)│                 │ (104)
              └─────────────────┘
                  👤 You (100)
        """
        lines = []

        active_others = self.seats[1:]  # All non-player seats

        # Position buddies: top center, left, right
        top = active_others[0] if len(active_others) >= 1 else None
        left = active_others[1] if len(active_others) >= 2 else None
        right = active_others[2] if len(active_others) >= 3 else None
        top_right = active_others[3] if len(active_others) >= 4 else None

        table_w = 35

        # Top seats
        top_labels = []
        if top:
            top_labels.append(self._seat_label(top))
        if top_right:
            top_labels.append(self._seat_label(top_right))

        if top_labels:
            combined = "    ".join(top_labels)
            lines.append(f"{combined:^{table_w + 12}}")

        # Top cards (hidden for opponents)
        top_cards = []
        if top:
            top_cards.append(self._seat_cards_hidden(top))
        if top_right:
            top_cards.append(self._seat_cards_hidden(top_right))
        if top_cards:
            combined = "    ".join(top_cards)
            lines.append(f"{combined:^{table_w + 12}}")

        # Table top border
        lines.append(f"{'':>6}┌{'─' * table_w}┐")

        # Community cards
        comm_str = self._render_community()
        left_label = self._seat_label(left) if left else ""
        right_label = self._seat_label(right) if right else ""

        # Left/right seat labels
        if left or right:
            lines.append(
                f"{left_label:>6}│{comm_str:^{table_w}}│ {right_label}"
            )
        else:
            lines.append(f"{'':>6}│{comm_str:^{table_w}}│")

        # Pot
        pot_str = f"Pot: {self.pot}"
        left_cards = self._seat_cards_hidden(left) if left else ""
        right_cards = self._seat_cards_hidden(right) if right else ""
        if left or right:
            lines.append(
                f"{left_cards:>6}│{pot_str:^{table_w}}│ {right_cards}"
            )
        else:
            lines.append(f"{'':>6}│{pot_str:^{table_w}}│")

        # Table bottom border
        lines.append(f"{'':>6}└{'─' * table_w}┘")

        # Player's cards (visible)
        player = self.seats[0]
        p_label = self._seat_label(player)
        lines.append(f"{p_label:^{table_w + 12}}")
        if player.hole_cards:
            cards_str = " ".join(c.rich_str() for c in player.hole_cards)
            lines.append(f"{cards_str:^{table_w + 12}}")

        return "\n".join(lines)

    def _seat_label(self, seat: Seat) -> str:
        """Compact seat label: emoji Name (chips)"""
        if seat.is_folded:
            return f"[dim]{seat.emoji} {seat.name} (fold)[/dim]"
        return f"{seat.emoji} {seat.name} ({seat.chips})"

    def _seat_cards_hidden(self, seat: Seat | None) -> str:
        if not seat or seat.is_folded or not seat.hole_cards:
            return ""
        return "[dim]\\[??] \\[??][/dim]"

    def _render_community(self) -> str:
        if not self.community:
            return "— waiting —"
        return " ".join(c.rich_str() for c in self.community)
