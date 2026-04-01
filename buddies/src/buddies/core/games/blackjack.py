"""Blackjack engine — player vs buddy-dealer.

Standard rules with personality-driven dealer behavior:
- High CHAOS dealer hits on soft 17, sometimes "accidentally" shows cards
- High WISDOM dealer plays textbook (stands on 17+)
- High SNARK dealer commentates every move
- High PATIENCE dealer is slow and methodical
- High DEBUGGING dealer counts cards (plays optimally)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state
from buddies.core.games.card_common import Card, Deck, render_hand_inline


class BJAction(Enum):
    HIT = auto()
    STAND = auto()
    DOUBLE = auto()
    BUST = auto()
    BLACKJACK = auto()


def hand_value(cards: list[Card]) -> int:
    """Calculate best blackjack hand value (aces count as 1 or 11)."""
    total = 0
    aces = 0
    for card in cards:
        if card.rank == 1:  # Ace
            aces += 1
            total += 11
        elif card.rank >= 10:  # Face cards
            total += 10
        else:
            total += card.rank
    # Demote aces from 11 to 1 as needed
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_soft(cards: list[Card]) -> bool:
    """Check if hand is 'soft' (contains an ace counted as 11)."""
    total = 0
    aces = 0
    for card in cards:
        if card.rank == 1:
            aces += 1
            total += 11
        elif card.rank >= 10:
            total += 10
        else:
            total += card.rank
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return aces > 0 and total <= 21


def is_blackjack(cards: list[Card]) -> bool:
    """Natural blackjack — exactly 2 cards totaling 21."""
    return len(cards) == 2 and hand_value(cards) == 21


@dataclass
class BJHand:
    """A blackjack hand (player or dealer)."""
    cards: list[Card] = field(default_factory=list)
    is_standing: bool = False
    is_doubled: bool = False

    @property
    def value(self) -> int:
        return hand_value(self.cards)

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        return is_blackjack(self.cards)

    @property
    def is_done(self) -> bool:
        return self.is_standing or self.is_bust or self.is_blackjack

    def display(self, hide_second: bool = False) -> str:
        """Rich-markup hand display."""
        hidden = 1 if hide_second and len(self.cards) >= 2 else 0
        hand_str = render_hand_inline(self.cards, hidden=hidden)
        if hidden:
            return f"{hand_str}  (showing {self.cards[0].rich_str()})"
        return f"{hand_str}  ({self.value})"


@dataclass
class BlackjackGame:
    """A single hand of Blackjack — player vs buddy-dealer.

    Dealer behavior influenced by personality:
    - Textbook: stand on hard 17+, hit on soft 17
    - Chaos: sometimes hits when shouldn't, random "mistakes"
    - Optimal: counts cards, plays perfect basic strategy as dealer
    """
    buddy_state: BuddyState
    deck: Deck = field(default_factory=Deck)
    player: BJHand = field(default_factory=BJHand)
    dealer: BJHand = field(default_factory=BJHand)
    bet: int = 10
    is_over: bool = False
    outcome: GameOutcome | None = None
    _personality: GamePersonality = field(init=False)

    def __post_init__(self):
        self._personality = personality_from_state(self.buddy_state)
        self.deck = Deck()
        self.deck.shuffle()

    def deal_initial(self) -> None:
        """Deal initial 2 cards each."""
        self.player.cards = self.deck.deal(2)
        self.dealer.cards = self.deck.deal(2)

        # Check for naturals
        if self.player.is_blackjack and self.dealer.is_blackjack:
            self.is_over = True
            self.outcome = GameOutcome.DRAW
        elif self.player.is_blackjack:
            self.is_over = True
            self.outcome = GameOutcome.WIN
        elif self.dealer.is_blackjack:
            self.is_over = True
            self.outcome = GameOutcome.LOSE

    def player_hit(self) -> Card:
        """Player takes a card. Returns the dealt card."""
        card = self.deck.deal_one()
        self.player.cards.append(card)
        if self.player.is_bust:
            self.is_over = True
            self.outcome = GameOutcome.LOSE
        return card

    def player_stand(self) -> None:
        """Player stands — trigger dealer play."""
        self.player.is_standing = True

    def player_double(self) -> Card:
        """Double down — one more card, bet doubles, then stand."""
        self.player.is_doubled = True
        self.bet *= 2
        card = self.deck.deal_one()
        self.player.cards.append(card)
        self.player.is_standing = True
        if self.player.is_bust:
            self.is_over = True
            self.outcome = GameOutcome.LOSE
        return card

    def can_double(self) -> bool:
        """Can only double on first 2 cards."""
        return len(self.player.cards) == 2 and not self.player.is_standing

    def dealer_play(self) -> list[Card]:
        """Dealer draws cards according to personality-modified rules.

        Returns list of cards drawn.
        """
        drawn: list[Card] = []
        p = self._personality

        while not self.dealer.is_done:
            val = self.dealer.value
            soft = is_soft(self.dealer.cards)

            # Standard rule: stand on hard 17+
            should_hit = val < 17

            # Soft 17: textbook dealers hit, some stand
            if val == 17 and soft:
                should_hit = True
                # Patient/wise dealers might stand on soft 17
                if p.patience_factor > 0.5 and random.random() < 0.3:
                    should_hit = False

            # Chaos factor: sometimes makes "mistakes"
            if p.should_wild_card():
                if val >= 17 and val <= 19:
                    should_hit = True  # Risky hit
                elif val < 17:
                    should_hit = False  # Early stand

            if should_hit:
                card = self.deck.deal_one()
                self.dealer.cards.append(card)
                drawn.append(card)
            else:
                self.dealer.is_standing = True

        # Determine outcome
        if self.dealer.is_bust:
            self.outcome = GameOutcome.WIN
        elif self.dealer.value > self.player.value:
            self.outcome = GameOutcome.LOSE
        elif self.dealer.value < self.player.value:
            self.outcome = GameOutcome.WIN
        else:
            self.outcome = GameOutcome.DRAW

        self.is_over = True
        return drawn

    def get_result(self) -> GameResult:
        """Get the final game result."""
        return GameResult(
            game_type=GameType.BLACKJACK,
            outcome=self.outcome or GameOutcome.DRAW,
            buddy_id=self.buddy_state.buddy_id,
            score={
                "player_value": self.player.value,
                "dealer_value": self.dealer.value,
                "player_blackjack": self.player.is_blackjack,
                "dealer_blackjack": self.dealer.is_blackjack,
                "player_bust": self.player.is_bust,
                "dealer_bust": self.dealer.is_bust,
                "doubled": self.player.is_doubled,
            },
        )
