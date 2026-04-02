"""Deploy or Die — Deckbuilder game engine for Buddies Arcade.

You're a junior dev maintaining a production codebase in StackHaven.
Each sprint brings incidents (bugs). Play cards to generate Dev Points (DP).
Spend DP to resolve incidents or buy better cards from the shop.
Survive 7 sprints to win.

Personality effects:
  DEBUGGING  → Tool/optimization cards in starting deck, shop weighted toward tools
  CHAOS      → High-variance cards in starting deck, wilder shop offerings
  SNARK      → Aggressive resolve cards, faster but costly options
  WISDOM     → Architecture cards cheaper, starting cards reveal info
  PATIENCE   → +2 starting Stability, slow-burn value cards
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import personality_from_state


# ---------------------------------------------------------------------------
# Card definitions
# ---------------------------------------------------------------------------

class CardRarity(Enum):
    BASIC = "basic"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"


@dataclass
class Card:
    name: str
    cost: int           # DP cost to buy from shop (0 = in starting deck)
    rarity: CardRarity
    description: str
    dp_value: int = 0   # Base DP generated when played
    # Special effect tag (parsed by game engine)
    effect: str = ""    # e.g. "draw:1", "trash:1", "resolve_free", "double_next"
    personality_tag: str = ""  # Which personality prefers this card

    def __str__(self):
        return f"{self.name} ({self.dp_value}DP{', ' + self.effect if self.effect else ''})"


# ---------------------------------------------------------------------------
# Card pool (~30 unique cards)
# ---------------------------------------------------------------------------

ALL_CARDS: list[Card] = [
    # --- BASIC (in starting deck) ---
    Card("Commit",      0, CardRarity.BASIC,    "Generate 2 DP.",                   dp_value=2),
    Card("Quick Fix",   0, CardRarity.BASIC,    "1 DP. Draw 1 if incident resolved this sprint.",
         dp_value=1, effect="draw_if_resolved:1"),

    # --- COMMON (2-3 DP to buy) ---
    Card("Git Push",    2, CardRarity.COMMON,   "Generate 2 DP.",                   dp_value=2),
    Card("Stack Overflow Search", 2, CardRarity.COMMON,
         "1 DP. Draw 1 card.",                                                       dp_value=1, effect="draw:1"),
    Card("Coffee Break", 2, CardRarity.COMMON,
         "Draw 2 cards.",                                                            dp_value=0, effect="draw:2"),
    Card("Rubber Duck", 2, CardRarity.COMMON,
         "1 DP. Reveal next sprint's incidents.",                                    dp_value=1, effect="preview_incidents",
         personality_tag="wisdom"),
    Card("Pair Programming", 3, CardRarity.COMMON,
         "1 DP per other card played this sprint.",                                  dp_value=0, effect="dp_per_card_played",
         personality_tag="patience"),
    Card("Copy Paste",  3, CardRarity.COMMON,
         "Replay the last card's DP value.",                                         dp_value=0, effect="copy_last_dp",
         personality_tag="chaos"),
    Card("Linter",      2, CardRarity.COMMON,
         "1 DP. Trash a card from hand.",                                            dp_value=1, effect="trash:1",
         personality_tag="debugging"),
    Card("TODO Comment", 2, CardRarity.COMMON,
         "Defer 1 incident to next sprint (+1 cost when it returns).",               dp_value=0, effect="defer_incident",
         personality_tag="patience"),

    # --- UNCOMMON (4-5 DP to buy) ---
    Card("Code Review", 4, CardRarity.UNCOMMON, "Generate 3 DP.",                   dp_value=3),
    Card("Unit Test",   4, CardRarity.UNCOMMON,
         "2 DP. +1 DP per incident resolved this sprint.",                           dp_value=2, effect="dp_per_resolved",
         personality_tag="debugging"),
    Card("Refactor",    5, CardRarity.UNCOMMON,
         "Trash up to 2 cards from hand. Draw 1 per trashed.",                      dp_value=0, effect="refactor",
         personality_tag="wisdom"),
    Card("CI Pipeline", 4, CardRarity.UNCOMMON,
         "2 DP. The next card played generates double DP.",                          dp_value=2, effect="double_next",
         personality_tag="debugging"),
    Card("Docker Container", 4, CardRarity.UNCOMMON,
         "2 DP. Ignore 1 incident this sprint (no damage).",                        dp_value=2, effect="ignore_incident",
         personality_tag="patience"),
    Card("Feature Flag", 4, CardRarity.UNCOMMON,
         "Choose: 3 DP or resolve cheapest incident free.",                          dp_value=0, effect="feature_flag",
         personality_tag="snark"),
    Card("Merge Conflict", 5, CardRarity.UNCOMMON,
         "3 DP. Shuffle discard pile back into deck now.",                           dp_value=3, effect="reshuffle",
         personality_tag="chaos"),

    # --- RARE (6-8 DP to buy) ---
    Card("Senior Dev",  6, CardRarity.RARE,     "Generate 4 DP.",                   dp_value=4),
    Card("Kubernetes Cluster", 7, CardRarity.RARE,
         "2 DP. Permanently gain +1 max Stability.",                                dp_value=2, effect="max_stability_up",
         personality_tag="patience"),
    Card("Incident Commander", 6, CardRarity.RARE,
         "Resolve the cheapest incident for free.",                                  dp_value=0, effect="resolve_cheapest_free",
         personality_tag="debugging"),
    Card("Legacy Rewrite", 7, CardRarity.RARE,
         "Trash your entire hand. Draw 5 fresh cards.",                              dp_value=0, effect="legacy_rewrite",
         personality_tag="chaos"),
    Card("Chaos Engineering", 8, CardRarity.RARE,
         "Reveal 3 future incidents. Resolve 1 for free.",                           dp_value=0, effect="chaos_engineering",
         personality_tag="chaos"),
    Card("The Intern",  6, CardRarity.RARE,
         "Generate 0-6 DP (random). 30% chance to spawn an extra incident.",        dp_value=0, effect="intern",
         personality_tag="chaos"),

    # --- LEGENDARY (appear sprint 5+) ---
    Card("10x Developer", 9, CardRarity.LEGENDARY,
         "5 DP. Draw 2 cards. Trash 1 card from hand.",                             dp_value=5, effect="ten_x",
         personality_tag="debugging"),
    Card("Open Source Community", 10, CardRarity.LEGENDARY,
         "Generate 1 DP per unique card name in your deck.",                         dp_value=0, effect="open_source",
         personality_tag="wisdom"),
    Card("Production Freeze", 9, CardRarity.LEGENDARY,
         "Skip all incidents this sprint. No shop phase either.",                    dp_value=0, effect="prod_freeze",
         personality_tag="patience"),
]

CARD_BY_NAME: dict[str, Card] = {c.name: c for c in ALL_CARDS}

# Personality starting bonus cards (2 extras per dominant stat)
PERSONALITY_STARTING_CARDS: dict[str, tuple[str, str]] = {
    "debugging": ("Linter", "Unit Test"),
    "chaos":     ("Copy Paste", "The Intern"),
    "snark":     ("Feature Flag", "Code Review"),
    "wisdom":    ("Rubber Duck", "Refactor"),
    "patience":  ("TODO Comment", "Docker Container"),
}

# Shop weight boosts by personality tag
PERSONALITY_SHOP_WEIGHTS: dict[str, float] = {
    "debugging": 2.5,
    "chaos":     2.5,
    "snark":     2.5,
    "wisdom":    2.5,
    "patience":  2.5,
}


# ---------------------------------------------------------------------------
# Incident definitions
# ---------------------------------------------------------------------------

class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BOSS = "boss"


@dataclass
class Incident:
    name: str
    base_cost: int          # DP to resolve
    stability_damage: int   # Stability loss if unresolved
    severity: IncidentSeverity
    description: str
    effect: str = ""        # e.g. "escalate:1" (cost +1 per unresolved sprint), "spawn_incident"
    deferred: bool = False  # Was deferred via TODO Comment?
    defer_cost_bonus: int = 0  # Extra cost accumulated through deferral
    ignored: bool = False   # Docker Container effect

    @property
    def current_cost(self) -> int:
        return self.base_cost + self.defer_cost_bonus

    def __str__(self):
        return f"{self.name} ({self.current_cost} DP, {self.stability_damage} dmg)"


ALL_INCIDENTS: list[Incident] = [
    # Low (cheap to resolve, still hurts if ignored)
    Incident("Typo in Production", 1, 2, IncidentSeverity.LOW, "Someone deployed a typo to prod."),
    Incident("Stale Cache",        1, 2, IncidentSeverity.LOW, "Users seeing 6-hour-old data."),
    Incident("Dependency Update",  2, 2, IncidentSeverity.LOW, "A package has a security patch."),
    Incident("Flaky Test",         1, 1, IncidentSeverity.LOW,
             "CI is red 50% of the time.",                    effect="flaky"),  # 50% self-resolves

    # Medium (meaningful both ways)
    Incident("Memory Leak",        3, 3, IncidentSeverity.MEDIUM,
             "Server is slowly running out of memory.",        effect="escalate:1"),
    Incident("Race Condition",     3, 3, IncidentSeverity.MEDIUM, "Two threads fighting over state."),
    Incident("SQL Injection Attempt", 4, 3, IncidentSeverity.MEDIUM,
             "Someone's trying to drop your tables."),
    Incident("Certificate Expiry", 3, 3, IncidentSeverity.MEDIUM,
             "SSL cert expires in 2 days.",                   effect="next_incident_cost:2"),
    Incident("Runaway Process",    3, 3, IncidentSeverity.MEDIUM,
             "PID 666 is eating 100% CPU.",                   effect="spawn_incident"),

    # High (must resolve or die)
    Incident("Database Corruption", 5, 4, IncidentSeverity.HIGH,
             "The primary database has inconsistent records."),
    Incident("DDoS Attack",        6, 4, IncidentSeverity.HIGH,  "Someone is very angry at your API."),
    Incident("Cascading Failure",  5, 4, IncidentSeverity.HIGH,
             "One service's death is killing its neighbors.",  effect="spawn_incident"),
    Incident("Data Breach",        7, 4, IncidentSeverity.HIGH,
             "User data was exposed. Legal is calling.",       effect="deadline:2"),

    # Boss (sprint 7 only)
    Incident("Total System Meltdown", 8, 5, IncidentSeverity.BOSS,
             "Everything is on fire. The CEO is watching."),
    Incident("The Audit",          10, 4, IncidentSeverity.BOSS,
             "The auditors are here. All incidents must be resolved.",
             effect="must_resolve"),
]

LOW_INCIDENTS    = [i for i in ALL_INCIDENTS if i.severity == IncidentSeverity.LOW]
MEDIUM_INCIDENTS = [i for i in ALL_INCIDENTS if i.severity == IncidentSeverity.MEDIUM]
HIGH_INCIDENTS   = [i for i in ALL_INCIDENTS if i.severity == IncidentSeverity.HIGH]
BOSS_INCIDENTS   = [i for i in ALL_INCIDENTS if i.severity == IncidentSeverity.BOSS]


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class GamePhase(Enum):
    DRAW = "draw"
    PLAY = "play"
    RESOLVE = "resolve"
    SHOP = "shop"
    SPRINT_END = "sprint_end"
    GAME_OVER = "game_over"
    WIN = "win"


@dataclass
class DeckbuilderGame:
    """Core game engine for Deploy or Die."""

    buddy_state: BuddyState

    # --- Config ---
    total_sprints: int = 7
    starting_stability: int = 10

    # --- State ---
    sprint: int = 1
    stability: int = 10
    max_stability: int = 10
    phase: GamePhase = GamePhase.DRAW

    deck: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)

    active_incidents: list[Incident] = field(default_factory=list)
    next_sprint_preview: list[Incident] | None = None  # Set by Rubber Duck

    shop_offerings: list[Card] = field(default_factory=list)
    dp_this_sprint: int = 0        # Total DP generated
    dp_available: int = 0          # DP available to spend
    cards_played: int = 0          # Cards played this sprint
    incidents_resolved: int = 0    # Incidents resolved this sprint
    double_next: bool = False       # CI Pipeline effect
    next_incident_cost_bonus: int = 0  # Certificate Expiry effect
    prod_freeze_active: bool = False   # Production Freeze effect
    last_dp_played: int = 0         # For Copy Paste

    # Personality params
    _dominant_stat: str = ""

    def __post_init__(self):
        self.stability = self.starting_stability
        self.max_stability = self.starting_stability

        # Determine dominant stat
        stats = self.buddy_state.stats
        self._dominant_stat = max(stats, key=stats.get)

        # Apply PATIENCE bonus
        if self._dominant_stat == "patience":
            self.stability += 2
            self.max_stability += 2

        # Build starting deck
        self._build_starting_deck()

        # Shuffle and draw
        self._shuffle_deck()
        self._start_sprint()

    # ------------------------------------------------------------------
    # Deck building
    # ------------------------------------------------------------------

    def _build_starting_deck(self):
        # 5 Commits + 1 Quick Fix + 2 personality cards
        base = [CARD_BY_NAME["Commit"]] * 5 + [CARD_BY_NAME["Quick Fix"]]
        bonus_names = PERSONALITY_STARTING_CARDS.get(self._dominant_stat, ("Git Push", "Git Push"))
        for name in bonus_names:
            if name in CARD_BY_NAME:
                base.append(CARD_BY_NAME[name])
        self.deck = list(base)

    def _shuffle_deck(self):
        random.shuffle(self.deck)

    def _draw(self, n: int = 1):
        for _ in range(n):
            if not self.deck:
                if not self.discard:
                    return
                self.deck = self.discard[:]
                self.discard = []
                self._shuffle_deck()
            if self.deck:
                self.hand.append(self.deck.pop())

    # ------------------------------------------------------------------
    # Sprint lifecycle
    # ------------------------------------------------------------------

    def _start_sprint(self):
        """Set up a new sprint."""
        self.phase = GamePhase.DRAW
        self.dp_this_sprint = 0
        self.dp_available = 0
        self.cards_played = 0
        self.incidents_resolved = 0
        self.double_next = False
        self.prod_freeze_active = False
        self.shop_offerings = []

        # Flip incidents
        self.active_incidents = self._generate_incidents()

        # Apply escalation from previous unresolved (handled at cleanup)

        # Draw hand
        self._draw(5)
        self.phase = GamePhase.PLAY

    def _generate_incidents(self) -> list[Incident]:
        incidents = []

        # Sprint 1-2: 1 incident; 3-5: 2; 6-7: 3
        if self.sprint <= 2:
            count = 1
        elif self.sprint <= 5:
            count = 2
        else:
            count = 3

        if self.sprint == self.total_sprints:
            # Boss sprint: include at least 1 boss
            boss = random.choice(BOSS_INCIDENTS)
            incidents.append(copy.copy(boss))
            count -= 1

        # Fill remaining from weighted pool
        pool = []
        if self.sprint <= 3:
            pool = LOW_INCIDENTS * 3 + MEDIUM_INCIDENTS
        elif self.sprint <= 5:
            pool = LOW_INCIDENTS + MEDIUM_INCIDENTS * 2 + HIGH_INCIDENTS
        else:
            pool = MEDIUM_INCIDENTS + HIGH_INCIDENTS * 2

        # Apply next_incident_cost_bonus
        for _ in range(count):
            if pool:
                inc = copy.copy(random.choice(pool))
                if self.next_incident_cost_bonus > 0:
                    inc.defer_cost_bonus += self.next_incident_cost_bonus
                incidents.append(inc)
        self.next_incident_cost_bonus = 0

        return incidents

    def _refresh_shop(self):
        """Generate 3 random shop offerings, personality-weighted."""
        buyable = [c for c in ALL_CARDS if c.cost > 0]

        # Filter legendaries to sprint 5+
        if self.sprint < 5:
            buyable = [c for c in buyable if c.rarity != CardRarity.LEGENDARY]

        weights = []
        for card in buyable:
            w = 1.0
            # Rarity weighting
            rarity_w = {
                CardRarity.COMMON: 4.0,
                CardRarity.UNCOMMON: 2.0,
                CardRarity.RARE: 1.0,
                CardRarity.LEGENDARY: 0.4,
            }
            w *= rarity_w.get(card.rarity, 1.0)
            # Personality boost
            if card.personality_tag == self._dominant_stat:
                w *= PERSONALITY_SHOP_WEIGHTS.get(self._dominant_stat, 1.0)
            weights.append(w)

        if not buyable:
            return

        n = min(3, len(buyable))
        try:
            self.shop_offerings = random.choices(buyable, weights=weights, k=n)
            # Deduplicate by name
            seen = set()
            unique = []
            for c in self.shop_offerings:
                if c.name not in seen:
                    seen.add(c.name)
                    unique.append(c)
            # If we deduped, top up
            attempts = 0
            while len(unique) < n and attempts < 20:
                c = random.choices(buyable, weights=weights, k=1)[0]
                if c.name not in seen:
                    seen.add(c.name)
                    unique.append(c)
                attempts += 1
            self.shop_offerings = unique[:n]
        except Exception:
            self.shop_offerings = random.sample(buyable, k=n)

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def play_card(self, hand_index: int) -> list[str]:
        """Play a card from hand. Returns list of events."""
        if self.phase != GamePhase.PLAY:
            return ["wrong_phase"]
        if hand_index < 0 or hand_index >= len(self.hand):
            return ["invalid"]

        card = self.hand.pop(hand_index)
        events: list[str] = [f"played:{card.name}"]

        # Calculate DP
        dp = card.dp_value
        if self.double_next:
            dp *= 2
            self.double_next = False
            events.append("double_applied")

        # Special base effects
        if card.effect == "dp_per_card_played":
            dp += self.cards_played  # Pair Programming

        elif card.effect == "open_source":
            unique_names = len({c.name for c in self.deck + self.hand + self.discard + [card]})
            dp += unique_names

        self.dp_available += dp
        self.dp_this_sprint += dp
        self.last_dp_played = card.dp_value
        self.cards_played += 1

        # Apply effects
        events += self._apply_card_effect(card)

        # Discard
        self.discard.append(card)
        return events

    def _apply_card_effect(self, card: Card) -> list[str]:
        events = []
        effect = card.effect

        if not effect:
            return events

        if effect.startswith("draw:"):
            n = int(effect.split(":")[1])
            self._draw(n)
            events.append(f"draw:{n}")

        elif effect == "draw:2" or effect == "draw:1":
            n = int(effect.split(":")[1])
            self._draw(n)

        elif effect == "draw_if_resolved:1":
            if self.incidents_resolved > 0:
                self._draw(1)
                events.append("draw:1")

        elif effect == "trash:1":
            events.append("choose_trash")  # Screen will prompt

        elif effect == "copy_last_dp":
            self.dp_available += self.last_dp_played
            events.append(f"copy:{self.last_dp_played}")

        elif effect == "double_next":
            self.double_next = True
            events.append("double_next_set")

        elif effect == "reshuffle":
            self.deck += self.discard
            self.discard = []
            random.shuffle(self.deck)
            events.append("reshuffled")

        elif effect == "dp_per_resolved":
            bonus = self.incidents_resolved
            self.dp_available += bonus
            events.append(f"bonus_dp:{bonus}")

        elif effect == "refactor":
            events.append("choose_refactor")  # Screen handles

        elif effect == "ignore_incident":
            # Mark cheapest unresolved incident as ignored
            unresolved = [i for i in self.active_incidents if not i.ignored]
            if unresolved:
                cheapest = min(unresolved, key=lambda i: i.current_cost)
                cheapest.ignored = True
                events.append(f"ignored:{cheapest.name}")

        elif effect == "feature_flag":
            events.append("choose_feature_flag")  # Screen handles choice

        elif effect == "resolve_cheapest_free":
            self._resolve_incident_free()
            events.append("resolved_free")

        elif effect == "defer_incident":
            events.append("choose_defer")  # Screen handles

        elif effect == "preview_incidents":
            events.append("preview_incidents")

        elif effect == "legacy_rewrite":
            self.discard += self.hand
            self.hand = []
            self._draw(5)
            events.append("legacy_rewrite")

        elif effect == "chaos_engineering":
            events.append("chaos_engineering")  # Screen handles

        elif effect == "intern":
            dp = random.randint(0, 6)
            self.dp_available += dp
            events.append(f"intern:{dp}")
            if random.random() < 0.3:
                extra = copy.copy(random.choice(LOW_INCIDENTS + MEDIUM_INCIDENTS))
                self.active_incidents.append(extra)
                events.append(f"intern_incident:{extra.name}")

        elif effect == "max_stability_up":
            self.max_stability += 1
            self.stability = min(self.stability + 1, self.max_stability)
            events.append("max_stability_up")

        elif effect == "ten_x":
            self._draw(2)
            events.append("draw:2")
            events.append("choose_trash")

        elif effect == "prod_freeze":
            self.prod_freeze_active = True
            events.append("prod_freeze")

        return events

    def _resolve_incident_free(self):
        unresolved = [i for i in self.active_incidents if not i.ignored]
        if unresolved:
            cheapest = min(unresolved, key=lambda i: i.current_cost)
            self.active_incidents.remove(cheapest)
            self.incidents_resolved += 1

    def resolve_incident(self, incident_index: int) -> list[str]:
        """Spend DP to resolve an incident. Returns events."""
        if incident_index < 0 or incident_index >= len(self.active_incidents):
            return ["invalid"]
        incident = self.active_incidents[incident_index]
        if incident.ignored:
            return ["already_ignored"]
        cost = incident.current_cost
        if self.dp_available < cost:
            return ["insufficient_dp"]

        self.dp_available -= cost
        self.active_incidents.remove(incident)
        self.incidents_resolved += 1
        return [f"resolved:{incident.name}"]

    def buy_card(self, shop_index: int) -> list[str]:
        """Buy a card from the shop."""
        if self.phase != GamePhase.SHOP:
            return ["wrong_phase"]
        if shop_index < 0 or shop_index >= len(self.shop_offerings):
            return ["invalid"]
        card = self.shop_offerings[shop_index]
        if self.dp_available < card.cost:
            return ["insufficient_dp"]

        # WISDOM: architecture cards cost 1 less
        cost = card.cost
        if self._dominant_stat == "wisdom" and card.rarity in (CardRarity.RARE, CardRarity.LEGENDARY):
            cost = max(0, cost - 1)

        self.dp_available -= cost
        self.discard.append(card)
        self.shop_offerings.remove(card)
        return [f"bought:{card.name}"]

    def trash_from_hand(self, hand_index: int) -> list[str]:
        """Remove a card from hand permanently (Linter, Refactor, 10x Dev)."""
        if hand_index < 0 or hand_index >= len(self.hand):
            return ["invalid"]
        card = self.hand.pop(hand_index)
        return [f"trashed:{card.name}"]

    def feature_flag_dp(self):
        """Feature Flag: take the DP option (3 DP)."""
        self.dp_available += 3

    def feature_flag_resolve(self):
        """Feature Flag: resolve cheapest incident free."""
        self._resolve_incident_free()

    def defer_incident(self, incident_index: int) -> list[str]:
        """Defer incident to next sprint (TODO Comment)."""
        if incident_index < 0 or incident_index >= len(self.active_incidents):
            return ["invalid"]
        incident = self.active_incidents[incident_index]
        incident.defer_cost_bonus += 1
        incident.deferred = True
        # Remove from current sprint — will be re-added next sprint
        self.active_incidents.remove(incident)
        # Store deferred incident
        if not hasattr(self, "_deferred_incidents"):
            self._deferred_incidents = []
        self._deferred_incidents.append(incident)
        return [f"deferred:{incident.name}"]

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def start_resolve_phase(self):
        """Move from play to resolve phase."""
        self.phase = GamePhase.RESOLVE

    def start_shop_phase(self):
        """Move from resolve to shop phase."""
        if not self.prod_freeze_active:
            self._refresh_shop()
        self.phase = GamePhase.SHOP

    def end_sprint(self) -> list[str]:
        """End the sprint. Apply damage, check game over, advance sprint."""
        events = []

        # Apply damage from unresolved incidents
        for incident in list(self.active_incidents):
            if not incident.ignored:
                # Flaky test: 50% chance to self-resolve
                if incident.effect == "flaky" and random.random() < 0.5:
                    events.append(f"flaky_resolved:{incident.name}")
                    continue

                self.stability -= incident.stability_damage
                events.append(f"damage:{incident.name}:{incident.stability_damage}")

                # Escalation effect
                if incident.effect.startswith("escalate:"):
                    bonus = int(incident.effect.split(":")[1])
                    incident.defer_cost_bonus += bonus

                # Spawn extra incident
                if incident.effect == "spawn_incident":
                    extra = copy.copy(random.choice(LOW_INCIDENTS))
                    events.append(f"spawned_incident:{extra.name}")

                # Deadline effect
                if incident.effect.startswith("deadline:"):
                    sprints_left = int(incident.effect.split(":")[1])
                    if sprints_left <= 0:
                        self.stability = 0
                        events.append("deadline_missed")

                # Next incident cost bonus
                if incident.effect.startswith("next_incident_cost:"):
                    bonus = int(incident.effect.split(":")[1])
                    self.next_incident_cost_bonus += bonus

                # Must resolve (Audit)
                if incident.effect == "must_resolve":
                    self.stability = 0
                    events.append("audit_failed")

        # Re-add deferred incidents for next sprint
        if hasattr(self, "_deferred_incidents"):
            self.active_incidents = list(getattr(self, "_deferred_incidents", []))
            self._deferred_incidents = []
        else:
            self.active_incidents = []

        # Check game over
        if self.stability <= 0:
            self.phase = GamePhase.GAME_OVER
            events.append("game_over")
            return events

        # Check win
        if self.sprint >= self.total_sprints:
            self.phase = GamePhase.WIN
            events.append("win")
            return events

        # Advance sprint
        self.sprint += 1
        self.discard += self.hand
        self.hand = []
        self._start_sprint()
        events.append(f"sprint_start:{self.sprint}")
        return events

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def is_over(self) -> bool:
        return self.phase in (GamePhase.GAME_OVER, GamePhase.WIN)

    @property
    def won(self) -> bool:
        return self.phase == GamePhase.WIN

    @property
    def deck_size(self) -> int:
        return len(self.deck)

    @property
    def discard_size(self) -> int:
        return len(self.discard)

    @property
    def hand_size(self) -> int:
        return len(self.hand)

    def get_result(self) -> GameResult:
        outcome = GameOutcome.WIN if self.won else GameOutcome.LOSE
        return GameResult(
            game_type=GameType.DECKBUILDER,
            outcome=outcome,
            buddy_id=self.buddy_state.buddy_id,
            score={
                "sprints_survived": self.sprint,
                "stability_remaining": max(0, self.stability),
                "incidents_resolved": self.incidents_resolved,
            },
            xp_earned=15 if self.won else 5 + self.sprint * 2,
            turns=self.sprint,
        )
