"""JRPG Battle engine — goofy Pokemon-style fights with coding-themed moves.

Types: LOGIC > CHAOS > HACK > LOGIC (rock-paper-scissors triangle) + DEBUG (neutral support)
Moves derived from buddy stats. Enemies are silly coding-themed monsters.
Not balanced. Not competitive. Just weird and funny.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state


# ---------------------------------------------------------------------------
# Type system
# ---------------------------------------------------------------------------

class MoveType(Enum):
    LOGIC = "logic"
    CHAOS = "chaos"
    HACK = "hack"
    DEBUG = "debug"


# Type effectiveness: attacker -> defender -> multiplier
TYPE_CHART: dict[MoveType, dict[MoveType, float]] = {
    MoveType.LOGIC: {MoveType.CHAOS: 1.5, MoveType.HACK: 0.5, MoveType.LOGIC: 1.0, MoveType.DEBUG: 1.0},
    MoveType.CHAOS: {MoveType.HACK: 1.5, MoveType.LOGIC: 0.5, MoveType.CHAOS: 1.0, MoveType.DEBUG: 1.0},
    MoveType.HACK:  {MoveType.LOGIC: 1.5, MoveType.CHAOS: 0.5, MoveType.HACK: 1.0, MoveType.DEBUG: 1.0},
    MoveType.DEBUG: {MoveType.LOGIC: 1.0, MoveType.CHAOS: 1.0, MoveType.HACK: 1.0, MoveType.DEBUG: 1.0},
}

TYPE_EMOJI = {
    MoveType.LOGIC: "🔷",
    MoveType.CHAOS: "🔴",
    MoveType.HACK: "🟢",
    MoveType.DEBUG: "🟡",
}


# ---------------------------------------------------------------------------
# Moves
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Move:
    name: str
    move_type: MoveType
    power: int
    accuracy: float  # 0.0-1.0
    description: str
    heals: bool = False  # DEBUG moves can heal instead of damage
    buff_defense: bool = False

# Move pools by dominant stat — each buddy gets their top-2 stat moves (2 each = 4 moves)
MOVE_POOLS: dict[str, list[Move]] = {
    "debugging": [
        Move("Stack Trace", MoveType.LOGIC, 8, 0.95, "Traces the error to its source."),
        Move("Lint Strike", MoveType.DEBUG, 5, 1.0, "Clean code, clean hit.", buff_defense=True),
        Move("Breakpoint", MoveType.LOGIC, 10, 0.85, "Freezes execution. Hits hard."),
        Move("Unit Test", MoveType.LOGIC, 6, 1.0, "Methodical. Reliable. Boring."),
    ],
    "chaos": [
        Move("Segfault", MoveType.CHAOS, 12, 0.70, "Crashes everything. Including itself sometimes."),
        Move("rm -rf", MoveType.CHAOS, 15, 0.55, "Nuclear option. Might miss spectacularly."),
        Move("Bit Flip", MoveType.CHAOS, 7, 0.90, "One tiny change. Maximum chaos."),
        Move("Fork Bomb", MoveType.CHAOS, 10, 0.75, "Exponential mayhem."),
    ],
    "snark": [
        Move("Code Review", MoveType.HACK, 7, 0.95, "Devastating criticism. Lowers morale."),
        Move("Passive-Aggressive Comment", MoveType.HACK, 9, 0.85, "// This could be better."),
        Move("Git Blame", MoveType.HACK, 8, 0.90, "Points the finger. It stings."),
        Move("Rejected PR", MoveType.HACK, 11, 0.75, "The ultimate insult."),
    ],
    "wisdom": [
        Move("Refactor", MoveType.DEBUG, 0, 1.0, "Heals through understanding.", heals=True),
        Move("Design Pattern", MoveType.LOGIC, 6, 1.0, "Elegant. Effective.", buff_defense=True),
        Move("Rubber Duck", MoveType.DEBUG, 0, 1.0, "Talk it out. Heal up.", heals=True),
        Move("Architecture Review", MoveType.LOGIC, 9, 0.85, "Sees the big picture."),
    ],
    "patience": [
        Move("Rubber Duck", MoveType.DEBUG, 0, 1.0, "Talk it out. Heal up.", heals=True),
        Move("Sit and Wait", MoveType.DEBUG, 0, 1.0, "Skip turn. Next attack does 2x.", buff_defense=True),
        Move("Steady Refactor", MoveType.LOGIC, 7, 1.0, "Slow but sure improvement."),
        Move("Timeout Handler", MoveType.LOGIC, 8, 0.90, "Patience has limits."),
    ],
}


def get_buddy_moves(state: BuddyState) -> list[Move]:
    """Get 4 moves for a buddy based on their top 2 stats."""
    sorted_stats = sorted(state.stats.items(), key=lambda x: x[1], reverse=True)
    top_stats = [s[0] for s in sorted_stats[:2]]

    moves: list[Move] = []
    seen_names: set[str] = set()
    for stat in top_stats:
        pool = MOVE_POOLS.get(stat, MOVE_POOLS["patience"])
        for move in pool:
            if move.name not in seen_names and len(moves) < 4:
                moves.append(move)
                seen_names.add(move.name)
    # Fill remaining slots from first stat pool
    if len(moves) < 4:
        for move in MOVE_POOLS.get(top_stats[0], []):
            if move.name not in seen_names and len(moves) < 4:
                moves.append(move)
                seen_names.add(move.name)
    return moves[:4]


# ---------------------------------------------------------------------------
# Enemies — silly coding-themed monsters
# ---------------------------------------------------------------------------

@dataclass
class Enemy:
    name: str
    emoji: str
    hp: int
    attack: int
    defense: int
    move_type: MoveType  # Primary type
    moves: list[Move] = field(default_factory=list)


ENEMY_POOL: list[Enemy] = [
    Enemy("Wild Segfault", "💥", 25, 8, 3, MoveType.CHAOS, [
        Move("Core Dump", MoveType.CHAOS, 10, 0.80, "Memory everywhere!"),
        Move("Crash", MoveType.CHAOS, 12, 0.65, "Takes you down with it."),
    ]),
    Enemy("Rogue Semicolon", "❗", 15, 6, 2, MoveType.HACK, [
        Move("Syntax Error", MoveType.HACK, 7, 0.95, "Tiny but devastating."),
        Move("Misplaced Logic", MoveType.HACK, 5, 1.0, "Where did that come from?"),
    ]),
    Enemy("Untested Function", "❓", 30, 7, 4, MoveType.LOGIC, [
        Move("Unexpected Return", MoveType.LOGIC, 8, 0.90, "Nobody knows what it does."),
        Move("Side Effect", MoveType.CHAOS, 6, 0.85, "Surprise! There are side effects."),
    ]),
    Enemy("Escaped Regex", "🕸️", 20, 9, 3, MoveType.HACK, [
        Move("Catastrophic Backtrack", MoveType.HACK, 11, 0.75, "O(2^n) pain."),
        Move("Greedy Match", MoveType.HACK, 7, 0.90, "Consumes everything."),
    ]),
    Enemy("Legacy Codebase", "📜", 40, 5, 6, MoveType.LOGIC, [
        Move("Undocumented Behavior", MoveType.LOGIC, 6, 1.0, "It's a feature, not a bug."),
        Move("Dependency Hell", MoveType.CHAOS, 8, 0.85, "You need version what?"),
    ]),
    Enemy("Phantom Type Error", "👻", 18, 10, 2, MoveType.HACK, [
        Move("Type Mismatch", MoveType.HACK, 9, 0.90, "str is not int. Or is it?"),
        Move("Null Reference", MoveType.CHAOS, 12, 0.70, "The billion-dollar mistake."),
    ]),
    Enemy("Infinite Loop", "🔄", 35, 6, 5, MoveType.CHAOS, [
        Move("while True:", MoveType.CHAOS, 5, 1.0, "It never stops."),
        Move("Stack Overflow", MoveType.CHAOS, 13, 0.60, "Too deep. Way too deep."),
    ]),
    Enemy("Merge Conflict", "⚡", 22, 8, 4, MoveType.LOGIC, [
        Move("<<<< HEAD", MoveType.LOGIC, 8, 0.90, "Both versions attack!"),
        Move("Diverged Branch", MoveType.HACK, 7, 0.85, "Which path is correct?"),
    ]),
    Enemy("Flaky Test", "🎭", 20, 7, 3, MoveType.CHAOS, [
        Move("Random Failure", MoveType.CHAOS, 9, 0.50, "Works on my machine."),
        Move("False Positive", MoveType.HACK, 6, 0.95, "Green doesn't mean good."),
    ]),
    Enemy("Production Bug", "🐛", 28, 9, 4, MoveType.HACK, [
        Move("Friday Deploy", MoveType.CHAOS, 11, 0.80, "Worst timing possible."),
        Move("Silent Failure", MoveType.HACK, 8, 0.90, "Nobody noticed. Until now."),
    ]),
]


def random_enemy(level: int = 1) -> Enemy:
    """Pick a random enemy, scaled to buddy level."""
    template = random.choice(ENEMY_POOL)
    # Scale HP and attack slightly with level
    scale = 1.0 + (level - 1) * 0.1
    return Enemy(
        name=template.name,
        emoji=template.emoji,
        hp=int(template.hp * scale),
        attack=int(template.attack * scale),
        defense=template.defense,
        move_type=template.move_type,
        moves=list(template.moves),
    )


# ---------------------------------------------------------------------------
# Battle engine
# ---------------------------------------------------------------------------

@dataclass
class BattleFighter:
    """A combatant in a battle."""
    name: str
    emoji: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    moves: list[Move]
    primary_type: MoveType = MoveType.LOGIC
    defense_buff: bool = False  # From buff moves
    power_buff: bool = False    # From "Sit and Wait"

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0

    def hp_bar(self, width: int = 20) -> str:
        """Rich-markup HP bar."""
        ratio = max(0, self.hp) / self.max_hp
        filled = int(ratio * width)
        empty = width - filled
        if ratio > 0.5:
            color = "green"
        elif ratio > 0.25:
            color = "yellow"
        else:
            color = "red"
        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}] {self.hp}/{self.max_hp}"


def fighter_from_buddy(state: BuddyState) -> BattleFighter:
    """Create a battle fighter from a buddy state."""
    hp = 20 + (state.level * 2) + (state.stats.get("patience", 10) // 2)
    attack = 5 + (max(state.stats.values()) // 3)
    defense = 3 + (state.stats.get("patience", 10) // 5)
    moves = get_buddy_moves(state)
    dominant = max(state.stats, key=state.stats.get)
    type_map = {
        "debugging": MoveType.LOGIC, "chaos": MoveType.CHAOS,
        "snark": MoveType.HACK, "wisdom": MoveType.DEBUG,
        "patience": MoveType.DEBUG,
    }
    return BattleFighter(
        name=state.name, emoji=state.species.emoji,
        hp=hp, max_hp=hp, attack=attack, defense=defense,
        moves=moves, primary_type=type_map.get(dominant, MoveType.LOGIC),
    )


def fighter_from_enemy(enemy: Enemy) -> BattleFighter:
    """Create a battle fighter from an enemy."""
    return BattleFighter(
        name=enemy.name, emoji=enemy.emoji,
        hp=enemy.hp, max_hp=enemy.hp, attack=enemy.attack, defense=enemy.defense,
        moves=enemy.moves, primary_type=enemy.move_type,
    )


@dataclass
class BattleTurn:
    """Result of one turn of combat."""
    attacker: str
    move: Move
    damage: int
    healed: int
    is_crit: bool
    is_miss: bool
    effectiveness: str  # "super", "not_very", "neutral"
    defender_hp: int


@dataclass
class Battle:
    """A single JRPG-style battle between buddy and enemy."""
    buddy_state: BuddyState
    buddy: BattleFighter = field(init=False)
    enemy_fighter: BattleFighter = field(init=False)
    enemy_data: Enemy = field(init=False)
    turns: list[BattleTurn] = field(default_factory=list)
    is_over: bool = False
    outcome: GameOutcome | None = None
    _personality: GamePersonality = field(init=False)

    def __post_init__(self):
        self._personality = personality_from_state(self.buddy_state)
        self.buddy = fighter_from_buddy(self.buddy_state)
        self.enemy_data = random_enemy(self.buddy_state.level)
        self.enemy_fighter = fighter_from_enemy(self.enemy_data)

    def player_attack(self, move_index: int) -> BattleTurn:
        """Player's buddy attacks with chosen move."""
        moves = self.buddy.moves
        if move_index >= len(moves):
            move_index = 0
        move = moves[move_index]
        return self._execute_move(self.buddy, self.enemy_fighter, move)

    def enemy_attack(self) -> BattleTurn:
        """Enemy picks a move and attacks."""
        move = random.choice(self.enemy_fighter.moves)
        return self._execute_move(self.enemy_fighter, self.buddy, move)

    def _execute_move(
        self, attacker: BattleFighter, defender: BattleFighter, move: Move
    ) -> BattleTurn:
        """Execute a move from attacker to defender."""
        # Miss check
        if random.random() > move.accuracy:
            turn = BattleTurn(
                attacker=attacker.name, move=move,
                damage=0, healed=0, is_crit=False, is_miss=True,
                effectiveness="neutral", defender_hp=defender.hp,
            )
            self.turns.append(turn)
            self._check_end()
            return turn

        # Heal move
        if move.heals:
            heal_amount = 8 + (attacker.attack // 2)
            attacker.hp = min(attacker.max_hp, attacker.hp + heal_amount)
            turn = BattleTurn(
                attacker=attacker.name, move=move,
                damage=0, healed=heal_amount, is_crit=False, is_miss=False,
                effectiveness="neutral", defender_hp=defender.hp,
            )
            self.turns.append(turn)
            return turn

        # Buff move
        if move.buff_defense:
            attacker.defense_buff = True
            # Still does some damage
            if move.power == 0:
                attacker.power_buff = True
                turn = BattleTurn(
                    attacker=attacker.name, move=move,
                    damage=0, healed=0, is_crit=False, is_miss=False,
                    effectiveness="neutral", defender_hp=defender.hp,
                )
                self.turns.append(turn)
                return turn

        # Damage calculation
        base = move.power + (attacker.attack // 3)

        # Power buff from "Sit and Wait"
        if attacker.power_buff:
            base = int(base * 2)
            attacker.power_buff = False

        # Type effectiveness
        eff = TYPE_CHART.get(move.move_type, {}).get(defender.primary_type, 1.0)
        if eff > 1.0:
            eff_str = "super"
        elif eff < 1.0:
            eff_str = "not_very"
        else:
            eff_str = "neutral"

        # Crit chance (higher chaos = more crits)
        chaos = self.buddy_state.stats.get("chaos", 10) if attacker == self.buddy else 15
        is_crit = random.random() < (chaos / 200.0)
        crit_mult = 2.0 if is_crit else 1.0

        # Defense reduction
        def_reduction = max(1, defender.defense - (2 if defender.defense_buff else 0))
        defender.defense_buff = False

        # Random variance
        variance = random.uniform(0.85, 1.15)

        damage = max(1, int((base - def_reduction / 2) * eff * crit_mult * variance))
        defender.hp = max(0, defender.hp - damage)

        turn = BattleTurn(
            attacker=attacker.name, move=move,
            damage=damage, healed=0, is_crit=is_crit, is_miss=False,
            effectiveness=eff_str, defender_hp=defender.hp,
        )
        self.turns.append(turn)
        self._check_end()
        return turn

    def _check_end(self):
        """Check if battle is over."""
        if self.enemy_fighter.is_fainted:
            self.is_over = True
            self.outcome = GameOutcome.WIN
        elif self.buddy.is_fainted:
            self.is_over = True
            self.outcome = GameOutcome.LOSE

    def get_result(self) -> GameResult:
        xp = 20 if self.outcome == GameOutcome.WIN else 8
        return GameResult(
            game_type=GameType.BATTLE,
            outcome=self.outcome or GameOutcome.DRAW,
            buddy_id=self.buddy_state.buddy_id,
            xp_earned=xp,
            mood_delta=8 if self.outcome == GameOutcome.WIN else -3,
            score={
                "enemy": self.enemy_data.name,
                "turns": len(self.turns),
                "buddy_hp_remaining": self.buddy.hp,
                "enemy_hp_remaining": self.enemy_fighter.hp,
            },
        )
