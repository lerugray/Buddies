"""Shared card infrastructure — Card, Deck, Hand.

Used by Blackjack, Texas Hold'em, and Whist.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum


class Suit(IntEnum):
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


SUIT_SYMBOLS = {Suit.CLUBS: "♣", Suit.DIAMONDS: "♦", Suit.HEARTS: "♥", Suit.SPADES: "♠"}
SUIT_COLORS = {Suit.CLUBS: "white", Suit.DIAMONDS: "red", Suit.HEARTS: "red", Suit.SPADES: "white"}

RANK_NAMES = {
    1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K",
}


@dataclass(frozen=True, order=True)
class Card:
    rank: int   # 1=Ace through 13=King
    suit: Suit

    @property
    def name(self) -> str:
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    @property
    def short(self) -> str:
        """Short display like 'A♠' or '10♥'."""
        return self.name

    @property
    def color(self) -> str:
        return SUIT_COLORS[self.suit]

    def rich_str(self) -> str:
        """Rich-markup colored card display."""
        c = self.color
        return f"[{c}]{self.name}[/{c}]"

    def ascii_art(self) -> list[str]:
        """3-line mini card for TUI display."""
        r = RANK_NAMES[self.rank].ljust(2)
        s = SUIT_SYMBOLS[self.suit]
        return [
            "┌───┐",
            f"│{r}{s}│",
            "└───┘",
        ]


@dataclass
class Deck:
    cards: list[Card] = field(default_factory=list)

    def __post_init__(self):
        if not self.cards:
            self.cards = [Card(rank, suit) for suit in Suit for rank in range(1, 14)]

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        dealt = self.cards[:n]
        self.cards = self.cards[n:]
        return dealt

    def deal_one(self) -> Card:
        return self.cards.pop(0)

    @property
    def remaining(self) -> int:
        return len(self.cards)


def render_hand_ascii(cards: list[Card], hidden: int = 0) -> str:
    """Render multiple cards side by side as ASCII art.

    Args:
        cards: Cards to display
        hidden: Number of cards from the end to show face-down
    """
    if not cards:
        return ""

    lines = [[], [], []]
    for i, card in enumerate(cards):
        if i >= len(cards) - hidden:
            # Face-down card
            lines[0].append("┌───┐")
            lines[1].append("│░░░│")
            lines[2].append("└───┘")
        else:
            art = card.ascii_art()
            for j in range(3):
                lines[j].append(art[j])

    return "\n".join(" ".join(row) for row in lines)


def render_hand_inline(cards: list[Card], hidden: int = 0) -> str:
    """Compact inline display: [A♠] [K♥] [??]"""
    parts = []
    for i, card in enumerate(cards):
        if i >= len(cards) - hidden:
            parts.append("[dim]\\[??][/dim]")
        else:
            parts.append(f"\\[{card.rich_str()}]")
    return " ".join(parts)
