"""Whist engine — classic trick-taking card game.

4 players in 2 partnerships: You + partner buddy vs 2 opponent buddies.
13 tricks per round. Last card dealt determines trump suit.
AI plays based on personality stats.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state
from buddies.core.games.card_common import Card, Deck, Suit, SUIT_SYMBOLS, RANK_NAMES


@dataclass
class WhistPlayer:
    """A player at the whist table."""
    name: str
    emoji: str
    is_human: bool = False
    personality: GamePersonality | None = None
    buddy_state: BuddyState | None = None
    hand: list[Card] = field(default_factory=list)
    team: int = 0  # 0 = player's team, 1 = opponent team

    def sort_hand(self):
        """Sort hand by suit then rank."""
        self.hand.sort(key=lambda c: (c.suit, c.rank if c.rank != 1 else 14))


@dataclass
class Trick:
    """A single trick (4 cards played)."""
    cards: list[tuple[int, Card]] = field(default_factory=list)  # (player_index, card)
    lead_suit: Suit | None = None
    winner_index: int = -1

    def add_card(self, player_idx: int, card: Card):
        if not self.cards:
            self.lead_suit = card.suit
        self.cards.append((player_idx, card))

    @property
    def is_complete(self) -> bool:
        return len(self.cards) == 4


@dataclass
class WhistGame:
    """Full whist game state."""
    player_state: BuddyState
    partner_state: BuddyState | None = None
    opp1_state: BuddyState | None = None
    opp2_state: BuddyState | None = None

    players: list[WhistPlayer] = field(default_factory=list)
    trump_suit: Suit | None = None
    trump_card: Card | None = None  # The revealed trump card

    tricks_won: list[int] = field(default_factory=lambda: [0, 0])  # [team0, team1]
    current_trick: Trick = field(default_factory=Trick)
    tricks_played: list[Trick] = field(default_factory=list)
    current_player: int = 0  # Index of who plays next

    is_over: bool = False
    action_log: list[str] = field(default_factory=list)
    _waiting_for_player: bool = False

    def __post_init__(self):
        self._setup_players()

    def _setup_players(self):
        """Set up 4 players: human + 3 AI buddies.

        Seating: Player(0) - Opp1(1) - Partner(2) - Opp2(3)
        Teams: 0,2 vs 1,3
        """
        # Player
        self.players = [WhistPlayer(
            name="You", emoji="👤", is_human=True, team=0,
        )]

        # Opponent 1 (across from partner)
        if self.opp1_state:
            self.players.append(WhistPlayer(
                name=self.opp1_state.name, emoji=self.opp1_state.species.emoji,
                personality=personality_from_state(self.opp1_state),
                buddy_state=self.opp1_state, team=1,
            ))
        else:
            self.players.append(WhistPlayer(
                name=self.player_state.name, emoji=self.player_state.species.emoji,
                personality=personality_from_state(self.player_state),
                buddy_state=self.player_state, team=1,
            ))

        # Partner
        if self.partner_state:
            self.players.append(WhistPlayer(
                name=self.partner_state.name, emoji=self.partner_state.species.emoji,
                personality=personality_from_state(self.partner_state),
                buddy_state=self.partner_state, team=0,
            ))
        else:
            self.players.append(WhistPlayer(
                name="Partner", emoji="🤝",
                personality=personality_from_state(self.player_state),
                team=0,
            ))

        # Opponent 2
        if self.opp2_state:
            self.players.append(WhistPlayer(
                name=self.opp2_state.name, emoji=self.opp2_state.species.emoji,
                personality=personality_from_state(self.opp2_state),
                buddy_state=self.opp2_state, team=1,
            ))
        else:
            self.players.append(WhistPlayer(
                name="Dealer", emoji="🎴",
                personality=personality_from_state(self.player_state),
                team=1,
            ))

    def deal(self):
        """Shuffle and deal 13 cards each, reveal trump."""
        deck = Deck()
        deck.shuffle()

        for i, player in enumerate(self.players):
            player.hand = deck.deal(13)
            player.sort_hand()

        # Trump is determined by the last card dealt (to dealer = player 3)
        self.trump_card = self.players[3].hand[-1]
        self.trump_suit = self.trump_card.suit

        self.tricks_won = [0, 0]
        self.tricks_played = []
        self.current_trick = Trick()
        self.current_player = 0  # Player leads first trick
        self.is_over = False

        trump_sym = SUIT_SYMBOLS[self.trump_suit]
        self.action_log.append(f"Trump: [bold]{trump_sym}[/bold] ({self.trump_card.rich_str()} revealed)")
        self.action_log.append("")

        self._waiting_for_player = True

    @property
    def waiting_for_player(self) -> bool:
        return self._waiting_for_player and not self.is_over

    def get_playable_cards(self) -> list[Card]:
        """Get cards the human player can legally play."""
        hand = self.players[0].hand
        if not self.current_trick.cards:
            return hand  # Lead anything

        lead_suit = self.current_trick.lead_suit
        suited = [c for c in hand if c.suit == lead_suit]
        return suited if suited else hand  # Must follow suit if possible

    def play_card(self, card: Card):
        """Human plays a card."""
        if not self._waiting_for_player:
            return

        player = self.players[0]
        if card not in player.hand:
            return

        player.hand.remove(card)
        self.current_trick.add_card(0, card)
        self.action_log.append(f"👤 You play {card.rich_str()}")

        self._waiting_for_player = False
        self._continue_trick()

    def _continue_trick(self):
        """Continue the trick with AI players."""
        while not self.current_trick.is_complete:
            # Next player
            self.current_player = (self.current_player + 1) % 4
            player = self.players[self.current_player]

            if player.is_human:
                self._waiting_for_player = True
                return

            # AI plays
            card = self._ai_choose_card(player)
            player.hand.remove(card)
            self.current_trick.add_card(self.current_player, card)
            self.action_log.append(f"{player.emoji} {player.name} plays {card.rich_str()}")

        # Trick complete — determine winner
        self._resolve_trick()

    def _ai_choose_card(self, player: WhistPlayer) -> Card:
        """AI chooses a card to play."""
        hand = player.hand
        trick = self.current_trick
        p = player.personality

        if not trick.cards:
            # Leading — play strong cards if aggressive, weak if patient
            if p and p.should_be_aggressive():
                # Lead with high cards
                return max(hand, key=lambda c: c.rank if c.rank != 1 else 14)
            elif p and p.patience_factor > 0.5:
                # Lead with low cards, save trump
                non_trump = [c for c in hand if c.suit != self.trump_suit]
                pool = non_trump if non_trump else hand
                return min(pool, key=lambda c: c.rank if c.rank != 1 else 14)
            else:
                return random.choice(hand)

        lead_suit = trick.lead_suit
        suited = [c for c in hand if c.suit == lead_suit]

        if suited:
            # Must follow suit
            if p and p.should_play_optimal():
                # Try to win: play highest if we can beat current best
                current_best = self._current_trick_best()
                winners = [c for c in suited if self._card_beats(c, current_best)]
                if winners:
                    return min(winners, key=lambda c: c.rank if c.rank != 1 else 14)  # Win with lowest possible
                return min(suited, key=lambda c: c.rank if c.rank != 1 else 14)  # Can't win, play low
            return random.choice(suited)

        # Can't follow suit — trump or discard
        trumps = [c for c in hand if c.suit == self.trump_suit]
        if trumps and (p is None or p.should_be_aggressive() or random.random() < 0.6):
            return min(trumps, key=lambda c: c.rank if c.rank != 1 else 14)  # Trump with lowest

        # Discard lowest non-trump
        return min(hand, key=lambda c: c.rank if c.rank != 1 else 14)

    def _card_beats(self, card: Card, best: tuple[int, Card] | None) -> bool:
        """Check if card beats the current best in the trick."""
        if best is None:
            return True
        _, best_card = best
        if card.suit == self.trump_suit and best_card.suit != self.trump_suit:
            return True
        if card.suit == best_card.suit:
            r1 = card.rank if card.rank != 1 else 14
            r2 = best_card.rank if best_card.rank != 1 else 14
            return r1 > r2
        return False

    def _current_trick_best(self) -> tuple[int, Card] | None:
        """Get the current winning card in the trick."""
        if not self.current_trick.cards:
            return None

        best_idx, best_card = self.current_trick.cards[0]
        for idx, card in self.current_trick.cards[1:]:
            if self._card_beats_card(card, best_card):
                best_idx, best_card = idx, card
        return best_idx, best_card

    def _card_beats_card(self, card: Card, best: Card) -> bool:
        """Does card beat best in the context of lead suit and trump?"""
        lead = self.current_trick.lead_suit
        if card.suit == self.trump_suit and best.suit != self.trump_suit:
            return True
        if card.suit != best.suit:
            return False
        r1 = card.rank if card.rank != 1 else 14
        r2 = best.rank if best.rank != 1 else 14
        return r1 > r2

    def _resolve_trick(self):
        """Determine trick winner and set up next trick."""
        trick = self.current_trick
        winner_idx, winner_card = trick.cards[0]
        for idx, card in trick.cards[1:]:
            if self._card_beats_card(card, winner_card):
                winner_idx, winner_card = idx, card

        trick.winner_index = winner_idx
        winner = self.players[winner_idx]
        team = winner.team
        self.tricks_won[team] += 1

        self.action_log.append(
            f"  → {winner.emoji} {winner.name} wins the trick! "
            f"[dim](Team scores: {self.tricks_won[0]} - {self.tricks_won[1]})[/dim]"
        )
        self.action_log.append("")

        self.tricks_played.append(trick)
        self.current_trick = Trick()

        # Check if round is over (13 tricks)
        if sum(self.tricks_won) >= 13:
            self.is_over = True
            return

        # Winner leads next trick
        self.current_player = winner_idx

        if self.players[winner_idx].is_human:
            self._waiting_for_player = True
        else:
            # AI leads, then continues
            self._continue_trick()

    @property
    def player_team_tricks(self) -> int:
        return self.tricks_won[0]

    @property
    def opponent_team_tricks(self) -> int:
        return self.tricks_won[1]

    def get_result(self) -> GameResult:
        """Build game result."""
        p_tricks = self.tricks_won[0]
        o_tricks = self.tricks_won[1]

        if p_tricks > o_tricks:
            outcome = GameOutcome.WIN
            xp = 20 + (p_tricks - 7) * 3  # Bonus for tricks over 7
            mood = 5
        elif p_tricks < o_tricks:
            outcome = GameOutcome.LOSE
            xp = 8
            mood = -2
        else:
            outcome = GameOutcome.DRAW
            xp = 12
            mood = 0

        return GameResult(
            game_type=GameType.WHIST,
            outcome=outcome,
            buddy_id=0,
            score={"player_team": p_tricks, "opponent_team": o_tricks},
            xp_earned=xp,
            mood_delta=mood,
        )

    def render_table(self) -> str:
        """Render the whist table with 4 players and current trick.

        Layout:
                  🐙 Opp1
              ┌───────────┐
        🤝 P │  [trick]   │ 🦊 Opp2
              └───────────┘
                  👤 You
        """
        lines = []
        p0, p1, p2, p3 = self.players  # You, Opp1, Partner, Opp2

        table_w = 25
        trump_sym = SUIT_SYMBOLS[self.trump_suit] if self.trump_suit else "?"

        # Opp1 (top)
        lines.append(f"{self._player_label(p1):^{table_w + 16}}")
        lines.append(f"{self._hand_summary(p1):^{table_w + 16}}")

        # Table top
        lines.append(f"{'':>8}┌{'─' * table_w}┐")

        # Trick cards in center
        trick_str = self._render_trick()
        p2_label = self._player_label(p2)
        p3_label = self._player_label(p3)
        lines.append(f"{p2_label:>8}│{trick_str:^{table_w}}│ {p3_label}")

        # Trump indicator
        trump_str = f"Trump: {trump_sym}"
        tricks_str = f"Us {self.tricks_won[0]} - {self.tricks_won[1]} Them"
        info = f"{trump_str}  {tricks_str}"
        p2_hand = self._hand_summary(p2)
        p3_hand = self._hand_summary(p3)
        lines.append(f"{p2_hand:>8}│{info:^{table_w}}│ {p3_hand}")

        # Table bottom
        lines.append(f"{'':>8}└{'─' * table_w}┘")

        # Player (bottom)
        lines.append(f"{self._player_label(p0):^{table_w + 16}}")

        return "\n".join(lines)

    def _player_label(self, player: WhistPlayer) -> str:
        team = "You" if player.team == 0 else "Opp"
        return f"{player.emoji} {player.name}"

    def _hand_summary(self, player: WhistPlayer) -> str:
        """Show card count for AI, actual cards for human."""
        if player.is_human:
            return ""  # Shown separately
        return f"[dim]({len(player.hand)} cards)[/dim]"

    def _render_trick(self) -> str:
        """Render current trick cards."""
        if not self.current_trick.cards:
            return "—"
        parts = []
        for idx, card in self.current_trick.cards:
            p = self.players[idx]
            parts.append(f"{p.emoji}{card.rich_str()}")
        return " ".join(parts)
