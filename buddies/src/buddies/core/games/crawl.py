"""Blobber CRPG dungeon engine — grid-based first-person dungeon crawl.

Inspired by Eye of the Beholder and Ultima 4. Party of 1-4 buddies
explore a procedurally generated dungeon, fight monsters in turn-based
combat, and use class abilities to solve exploration challenges.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, IntEnum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state
from buddies.core.games.combat import (
    BattleFighter, Move, MoveType, Enemy, ENEMY_POOL, MOVE_POOLS,
    random_enemy, get_buddy_moves, TYPE_CHART,
)


# ---------------------------------------------------------------------------
# Grid types
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Class-flavored dungeon dialogue
# ---------------------------------------------------------------------------

CRAWL_DIALOGUE: dict[str, dict[str, list[str]]] = {
    "monster_spotted": {
        "ENG": [
            "\"Analyzing threat level... it's not great.\"",
            "\"I can see its weakness. Cover me.\"",
            "\"Running diagnostics on the enemy...\"",
        ],
        "BER": [
            "\"FINALLY! Something to hit!\"",
            "\"Stand back. I've got this.\"",
            "\"My fists are READY.\"",
        ],
        "ROG": [
            "\"I could sneak past... but where's the fun?\"",
            "\"Watch for an opening. I'll go for the crit.\"",
            "\"Dibs on whatever it drops.\"",
        ],
        "MAG": [
            "\"I sense dark energy... well, buggy energy.\"",
            "\"Let me prepare a refactoring spell.\"",
            "\"Stand behind me. This could get arcane.\"",
        ],
        "PAL": [
            "\"Stay close. I'll take the hits.\"",
            "\"We face this together. As a team.\"",
            "\"Everyone stay calm. We've got this.\"",
        ],
    },
    "combat_victory": {
        "ENG": ["\"Threat neutralized. Logging results.\"", "\"As predicted.\""],
        "BER": ["\"WHO'S NEXT?!\"", "\"That was barely a warmup!\""],
        "ROG": ["\"Too easy. Check for loot.\"", "\"And they never saw it coming.\""],
        "MAG": ["\"The arcane energies settle.\"", "\"Knowledge is the greatest weapon.\""],
        "PAL": ["\"Well fought, everyone.\"", "\"The team prevails.\""],
    },
    "trap_found": {
        "ENG": ["\"Wait — I'm detecting anomalies ahead!\""],
        "BER": ["\"Ow! What was— oh. A trap.\""],
        "ROG": ["\"Classic trap. I've seen a hundred of these.\""],
        "MAG": ["\"I sense something... unpleasant.\""],
        "PAL": ["\"Careful, everyone. Stay behind me.\""],
    },
    "treasure_found": {
        "ENG": ["\"Interesting find. Cataloguing it.\""],
        "BER": ["\"LOOT! Mine! ...I mean, ours.\""],
        "ROG": ["\"Now THAT is what I'm here for.\""],
        "MAG": ["\"Fascinating. The dungeon provides.\""],
        "PAL": ["\"A welcome discovery. We share equally.\""],
    },
    "descend": {
        "ENG": ["\"Structural analysis: floor below is more dangerous.\""],
        "BER": ["\"Deeper? DEEPER! Let's GO!\""],
        "ROG": ["\"Darker down there. I like it.\""],
        "MAG": ["\"The magical density increases below...\""],
        "PAL": ["\"Everyone ready? Stay together.\""],
    },
    "low_hp": {
        "ENG": ["\"Warning: party vitals critical.\""],
        "BER": ["\"Just a scratch! ...okay maybe not.\""],
        "ROG": ["\"We should find somewhere to rest. Fast.\""],
        "MAG": ["\"Our life force wanes. We need healing.\""],
        "PAL": ["\"Hold on, everyone. I'll do what I can.\""],
    },
}


def _buddy_says(party: list, context: str) -> str | None:
    """Pick a random alive party member and return a dialogue line."""
    alive = [m for m in party if m.is_alive]
    if not alive:
        return None
    speaker = random.choice(alive)
    pool = CRAWL_DIALOGUE.get(context, {}).get(speaker.buddy_class.value, [])
    if not pool:
        return None
    line = random.choice(pool)
    return f"{speaker.emoji} {speaker.name}: {line}"


class CellType(IntEnum):
    WALL = 0
    FLOOR = 1
    DOOR = 2
    STAIRS_DOWN = 3
    STAIRS_UP = 4


class Facing(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


# Direction deltas: (dy, dx) — north is -y
DIRECTION_DELTA = {
    Facing.NORTH: (-1, 0),
    Facing.EAST: (0, 1),
    Facing.SOUTH: (1, 0),
    Facing.WEST: (0, -1),
}


class EncounterKind(Enum):
    MONSTER = "monster"
    TRAP = "trap"
    TREASURE = "treasure"
    MYSTERY = "mystery"
    REST = "rest"
    BOSS = "boss"


@dataclass
class Encounter:
    """An encounter placed on the grid."""
    kind: EncounterKind
    name: str
    description: str
    resolved: bool = False
    # Kind-specific data
    enemy: Enemy | None = None
    enemy_count: int = 1
    trap_stat: str = "debugging"
    loot_value: int = 0
    loot_name: str = ""


@dataclass
class Cell:
    """A single cell in the dungeon grid."""
    terrain: CellType = CellType.WALL
    encounter: Encounter | None = None
    revealed: bool = False
    visited: bool = False


# ---------------------------------------------------------------------------
# Class system
# ---------------------------------------------------------------------------

class BuddyClass(Enum):
    ENGINEER = "ENG"
    BERSERKER = "BER"
    ROGUE = "ROG"
    MAGE = "MAG"
    PALADIN = "PAL"


CLASS_FROM_STAT = {
    "debugging": BuddyClass.ENGINEER,
    "chaos": BuddyClass.BERSERKER,
    "snark": BuddyClass.ROGUE,
    "wisdom": BuddyClass.MAGE,
    "patience": BuddyClass.PALADIN,
}

CLASS_NAMES = {
    BuddyClass.ENGINEER: "Engineer",
    BuddyClass.BERSERKER: "Berserker",
    BuddyClass.ROGUE: "Rogue",
    BuddyClass.MAGE: "Mage",
    BuddyClass.PALADIN: "Paladin",
}


class StatusEffect(Enum):
    """Status effects that can afflict party members or enemies."""
    POISON = "poison"      # Take damage each turn
    SILENCE = "silence"    # Cannot use class skills
    STUN = "stun"          # Skip next turn


# Front row classes (melee fighters) vs back row (ranged/support)
FRONT_ROW_CLASSES = {BuddyClass.ENGINEER, BuddyClass.BERSERKER, BuddyClass.PALADIN}
BACK_ROW_CLASSES = {BuddyClass.ROGUE, BuddyClass.MAGE}


@dataclass
class PartyMember:
    """A buddy in the dungeon party with class role."""
    buddy_state: BuddyState
    buddy_class: BuddyClass
    personality: GamePersonality
    hp: int
    max_hp: int
    attack: int
    defense: int
    moves: list[Move]
    defending: bool = False
    analyze_buff: bool = False  # Engineer: next attack +50%
    # Wizardry VI additions
    row: str = "front"  # "front" or "back"
    hidden: bool = False  # Rogue: hiding for backstab
    status_effects: list[StatusEffect] = field(default_factory=list)

    @classmethod
    def from_buddy(cls, state: BuddyState) -> PartyMember:
        """Create a party member from a BuddyState."""
        stats = state.stats
        dominant = max(stats, key=stats.get)
        buddy_class = CLASS_FROM_STAT.get(dominant, BuddyClass.PALADIN)
        personality = personality_from_state(state)

        # Derive combat stats
        total = sum(stats.values())
        hp = 20 + total // 2 + stats.get("patience", 10)
        attack = 5 + stats.get("debugging", 10) // 3 + stats.get("chaos", 10) // 4
        defense = 2 + stats.get("patience", 10) // 4

        moves = get_buddy_moves(state)

        # Auto-assign row based on class
        row = "front" if buddy_class in FRONT_ROW_CLASSES else "back"

        return cls(
            buddy_state=state,
            buddy_class=buddy_class,
            personality=personality,
            hp=hp, max_hp=hp,
            attack=attack, defense=defense,
            moves=moves,
            row=row,
        )

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def name(self) -> str:
        return self.buddy_state.name

    @property
    def emoji(self) -> str:
        return self.buddy_state.species.emoji

    def hp_bar(self, width: int = 10) -> str:
        """Rich markup HP bar."""
        filled = int((self.hp / self.max_hp) * width) if self.max_hp > 0 else 0
        empty = width - filled
        color = "green" if self.hp > self.max_hp * 0.5 else ("yellow" if self.hp > self.max_hp * 0.25 else "red")
        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


# ---------------------------------------------------------------------------
# Dungeon grid generation
# ---------------------------------------------------------------------------

GRID_SIZE = 16


@dataclass
class Room:
    """A room in the dungeon."""
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.y + self.h // 2, self.x + self.w // 2)

    def intersects(self, other: Room, padding: int = 1) -> bool:
        return not (
            self.x - padding >= other.x + other.w + padding or
            other.x - padding >= self.x + self.w + padding or
            self.y - padding >= other.y + other.h + padding or
            other.y - padding >= self.y + self.h + padding
        )


def generate_floor(floor_num: int) -> tuple[list[list[Cell]], int, int, Facing]:
    """Generate a dungeon floor grid.

    Returns (grid, start_y, start_x, start_facing).
    """
    grid = [[Cell(CellType.WALL) for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    # Place rooms
    rooms: list[Room] = []
    num_rooms = random.randint(4, 6)
    attempts = 0

    while len(rooms) < num_rooms and attempts < 200:
        attempts += 1
        w = random.randint(3, 5)
        h = random.randint(3, 5)
        x = random.randint(1, GRID_SIZE - w - 1)
        y = random.randint(1, GRID_SIZE - h - 1)
        room = Room(x, y, w, h)

        if not any(room.intersects(r) for r in rooms):
            rooms.append(room)
            # Carve room
            for ry in range(room.y, room.y + room.h):
                for rx in range(room.x, room.x + room.w):
                    grid[ry][rx].terrain = CellType.FLOOR

    # Connect rooms with L-shaped corridors
    for i in range(len(rooms) - 1):
        cy1, cx1 = rooms[i].center
        cy2, cx2 = rooms[i + 1].center

        # Horizontal then vertical
        if random.random() < 0.5:
            _carve_h(grid, cx1, cx2, cy1)
            _carve_v(grid, cy1, cy2, cx2)
        else:
            _carve_v(grid, cy1, cy2, cx1)
            _carve_h(grid, cx1, cx2, cy2)

    # Place stairs
    if len(rooms) >= 2:
        # Start in first room
        sy, sx = rooms[0].center
        grid[sy][sx].terrain = CellType.STAIRS_UP

        # Stairs down in last room
        ey, ex = rooms[-1].center
        grid[ey][ex].terrain = CellType.STAIRS_DOWN
    else:
        sy, sx = GRID_SIZE // 2, GRID_SIZE // 2
        grid[sy][sx].terrain = CellType.STAIRS_UP

    # Place encounters in middle rooms
    _place_encounters(grid, rooms, floor_num)

    return grid, sy, sx, Facing.NORTH


def _carve_h(grid: list[list[Cell]], x1: int, x2: int, y: int):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if 0 < x < GRID_SIZE - 1 and 0 < y < GRID_SIZE - 1:
            if grid[y][x].terrain == CellType.WALL:
                grid[y][x].terrain = CellType.FLOOR


def _carve_v(grid: list[list[Cell]], y1: int, y2: int, x: int):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if 0 < x < GRID_SIZE - 1 and 0 < y < GRID_SIZE - 1:
            if grid[y][x].terrain == CellType.WALL:
                grid[y][x].terrain = CellType.FLOOR


def _place_encounters(grid: list[list[Cell]], rooms: list[Room], floor_num: int):
    """Place encounters in rooms (skip first and last rooms)."""
    middle_rooms = rooms[1:-1] if len(rooms) > 2 else rooms[1:] if len(rooms) > 1 else []

    # Collect valid floor cells in middle rooms
    candidates: list[tuple[int, int]] = []
    for room in middle_rooms:
        for ry in range(room.y + 1, room.y + room.h - 1):
            for rx in range(room.x + 1, room.x + room.w - 1):
                if grid[ry][rx].terrain == CellType.FLOOR and grid[ry][rx].encounter is None:
                    candidates.append((ry, rx))

    random.shuffle(candidates)

    encounters_to_place = []

    # Monsters (3-4)
    num_monsters = random.randint(3, 4)
    for _ in range(num_monsters):
        enemy = random_enemy(floor_num * 3)
        encounters_to_place.append(Encounter(
            kind=EncounterKind.MONSTER,
            name=enemy.name,
            description=f"A {enemy.name} blocks the path!",
            enemy=enemy,
            enemy_count=min(1 + floor_num // 2, 3),
        ))

    # Boss on floor 5
    if floor_num == 5 and rooms:
        boss_room = rooms[-1]
        by, bx = boss_room.center
        # Place boss adjacent to stairs
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = by + dy, bx + dx
            if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE and grid[ny][nx].terrain == CellType.FLOOR:
                boss = random_enemy(floor_num * 5)
                boss = Enemy(
                    name="The Monolith",
                    emoji="🏛️",
                    hp=60,
                    attack=10,
                    defense=5,
                    move_type=MoveType.LOGIC,
                    moves=[
                        Move("Legacy Crush", MoveType.LOGIC, 12, 0.85, "10,000 lines of pain."),
                        Move("Dependency Hell", MoveType.CHAOS, 15, 0.70, "Everything depends on everything."),
                    ],
                )
                grid[ny][nx].encounter = Encounter(
                    kind=EncounterKind.BOSS,
                    name=boss.name,
                    description="A single 10,000-line file. It does everything.",
                    enemy=boss,
                    enemy_count=1,
                )
                break

    # Traps (1-2)
    trap_defs = [
        ("Segfault Pit", "The floor vanishes into invalid memory!", "debugging"),
        ("Callback Hell", "Nested promises spiral downward endlessly!", "patience"),
        ("Type Coercion", "JavaScript turns your sword into 'undefined'!", "wisdom"),
        ("YAML Indentation", "One space wrong and the whole dungeon collapses!", "patience"),
    ]
    for _ in range(random.randint(1, 2)):
        t = random.choice(trap_defs)
        encounters_to_place.append(Encounter(
            kind=EncounterKind.TRAP, name=t[0], description=t[1], trap_stat=t[2],
        ))

    # Treasures (1-2)
    treasure_defs = [
        ("Golden Semicolon", 15), ("Ancient Documentation", 10),
        ("Rubber Duck (Legendary)", 20), ("Working Docker Config", 25),
        ("Perfectly Formatted JSON", 8), ("Mechanical Keyboard", 18),
    ]
    for _ in range(random.randint(1, 2)):
        t = random.choice(treasure_defs)
        encounters_to_place.append(Encounter(
            kind=EncounterKind.TREASURE, name=t[0],
            description=f"You found: {t[0]}!", loot_value=t[1], loot_name=t[0],
        ))

    # Mystery (1)
    encounters_to_place.append(Encounter(
        kind=EncounterKind.MYSTERY,
        name="Strange Terminal",
        description="A terminal glows with an unfamiliar prompt...",
    ))

    # Rest (1)
    encounters_to_place.append(Encounter(
        kind=EncounterKind.REST,
        name="Coffee Machine",
        description="A coffee machine that still works. Blessed.",
    ))

    # Place encounters
    for i, enc in enumerate(encounters_to_place):
        if i < len(candidates):
            y, x = candidates[i]
            grid[y][x].encounter = enc


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class CrawlState:
    """Full blobber dungeon crawl state."""
    party: list[PartyMember]
    grid: list[list[Cell]]
    player_y: int
    player_x: int
    facing: Facing
    floor: int = 1
    max_floors: int = 5
    gold: int = 0
    items: list[str] = field(default_factory=list)
    potions: int = 2  # Start with 2 potions
    monsters_defeated: int = 0
    floors_cleared: int = 0

    is_over: bool = False
    game_won: bool = False
    action_log: list[str] = field(default_factory=list)

    # Combat state
    in_combat: bool = False
    combat_enemies: list[BattleFighter] = field(default_factory=list)
    combat_turn: int = 0  # Index into turn order
    current_member_idx: int = 0  # Which party member is acting

    @classmethod
    def new_game(cls, buddies: list[BuddyState]) -> CrawlState:
        """Start a new dungeon crawl with a party of buddies."""
        party = [PartyMember.from_buddy(b) for b in buddies[:4]]
        grid, sy, sx, facing = generate_floor(1)

        state = cls(
            party=party, grid=grid,
            player_y=sy, player_x=sx, facing=facing,
        )

        # Reveal starting area
        state._reveal_around(sy, sx)
        state.grid[sy][sx].visited = True

        return state

    def _reveal_around(self, y: int, x: int, radius: int = 2):
        """Reveal cells around a position."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                    self.grid[ny][nx].revealed = True

    # -----------------------------------------------------------------------
    # Movement
    # -----------------------------------------------------------------------

    def move_forward(self) -> bool:
        """Move one cell forward. Returns True if moved."""
        if self.in_combat:
            return False
        dy, dx = DIRECTION_DELTA[self.facing]
        ny, nx = self.player_y + dy, self.player_x + dx
        return self._try_move(ny, nx)

    def move_backward(self) -> bool:
        """Move one cell backward."""
        if self.in_combat:
            return False
        dy, dx = DIRECTION_DELTA[self.facing]
        ny, nx = self.player_y - dy, self.player_x - dx
        return self._try_move(ny, nx)

    def turn_left(self):
        """Turn 90 degrees left."""
        self.facing = Facing((self.facing - 1) % 4)

    def turn_right(self):
        """Turn 90 degrees right."""
        self.facing = Facing((self.facing + 1) % 4)

    def _try_move(self, ny: int, nx: int) -> bool:
        """Try to move to a cell. Returns True if successful."""
        if not (0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE):
            return False

        cell = self.grid[ny][nx]
        if cell.terrain == CellType.WALL:
            return False

        if cell.terrain == CellType.DOOR and not cell.visited:
            self.action_log.append("[yellow]A locked door blocks the way![/yellow]")
            return False

        self.player_y = ny
        self.player_x = nx
        cell.visited = True
        self._reveal_around(ny, nx)

        # Check for encounters
        if cell.encounter and not cell.encounter.resolved:
            self._trigger_encounter(cell.encounter)

        # Check for stairs
        if cell.terrain == CellType.STAIRS_DOWN:
            self.action_log.append("[bold cyan]You found stairs leading down![/bold cyan]")
            self.action_log.append("[dim]Press Space to descend.[/dim]")

        return True

    def descend(self):
        """Go down stairs to the next floor."""
        cell = self.grid[self.player_y][self.player_x]
        if cell.terrain != CellType.STAIRS_DOWN:
            return

        self.floors_cleared += 1
        self.floor += 1

        if self.floor > self.max_floors:
            self.is_over = True
            self.game_won = True
            self.action_log.append("[bold green]═══ DUNGEON CLEARED! ═══[/bold green]")
            return

        self.action_log.append(f"\n[bold cyan]═══ DESCENDING TO FLOOR {self.floor} ═══[/bold cyan]")
        line = _buddy_says(self.party, "descend")
        if line:
            self.action_log.append(line)
        self.grid, self.player_y, self.player_x, self.facing = generate_floor(self.floor)
        self._reveal_around(self.player_y, self.player_x)
        self.grid[self.player_y][self.player_x].visited = True

    # -----------------------------------------------------------------------
    # Encounter triggering
    # -----------------------------------------------------------------------

    def _trigger_encounter(self, enc: Encounter):
        """Handle stepping onto an encounter."""
        if enc.kind in (EncounterKind.MONSTER, EncounterKind.BOSS):
            self.action_log.append(f"\n[red bold]⚔ {enc.name} blocks the path![/red bold]")
            self.action_log.append(f"[dim]{enc.description}[/dim]")
            line = _buddy_says(self.party, "monster_spotted")
            if line:
                self.action_log.append(line)
            self._start_combat(enc)
        elif enc.kind == EncounterKind.TREASURE:
            self.gold += enc.loot_value
            self.items.append(enc.loot_name)
            self.action_log.append(f"[yellow]✨ Found {enc.name}! (+{enc.loot_value} gold)[/yellow]")
            line = _buddy_says(self.party, "treasure_found")
            if line:
                self.action_log.append(line)
            enc.resolved = True
        elif enc.kind == EncounterKind.REST:
            heal = 15
            # Paladin bonus
            for m in self.party:
                if m.buddy_class == BuddyClass.PALADIN and m.is_alive:
                    heal = 25
                    self.action_log.append(f"{m.emoji} {m.name}'s Paladin aura doubles the rest healing!")
                    break
            for m in self.party:
                if m.is_alive:
                    m.hp = min(m.max_hp, m.hp + heal)
            self.action_log.append(f"[green]☕ {enc.name} — Party heals {heal} HP![/green]")
            enc.resolved = True
        elif enc.kind == EncounterKind.TRAP:
            self._handle_trap(enc)
        elif enc.kind == EncounterKind.MYSTERY:
            self._handle_mystery(enc)

    def _start_combat(self, enc: Encounter):
        """Initialize combat with enemies from an encounter."""
        self.in_combat = True
        self.combat_enemies = []
        self.combat_turn = 0
        self.current_member_idx = 0

        for i in range(enc.enemy_count):
            if enc.enemy:
                e = enc.enemy
                fighter = BattleFighter(
                    name=e.name + (f" #{i+1}" if enc.enemy_count > 1 else ""),
                    emoji=e.emoji,
                    hp=e.hp, max_hp=e.hp,
                    attack=e.attack, defense=e.defense,
                    moves=e.moves, primary_type=e.move_type,
                )
                self.combat_enemies.append(fighter)

        # Show enemy info
        for e in self.combat_enemies:
            self.action_log.append(f"  {e.emoji} {e.name} (HP: {e.hp})")

        self.action_log.append("")
        self._prompt_combat_action()

    def _prompt_combat_action(self):
        """Set up for the current party member's turn."""
        alive = [m for m in self.party if m.is_alive]
        if not alive:
            self._end_combat(won=False)
            return

        # Skip dead members
        while self.current_member_idx < len(self.party) and not self.party[self.current_member_idx].is_alive:
            self.current_member_idx += 1

        if self.current_member_idx >= len(self.party):
            # All party members have acted — enemy turn
            self._enemy_turn()
            return

        m = self.party[self.current_member_idx]
        row_tag = "[dim](front)[/dim]" if m.row == "front" else "[dim](back)[/dim]"
        status_tag = ""
        if m.status_effects:
            status_names = [s.value for s in m.status_effects]
            status_tag = f" [magenta][{'|'.join(status_names)}][/magenta]"
        hidden_tag = " [dim](hidden)[/dim]" if m.hidden else ""
        self.action_log.append(
            f"[bold]{m.emoji} {m.name}'s turn ({m.buddy_class.value}) {row_tag}{status_tag}{hidden_tag}:[/bold]"
        )

    # -----------------------------------------------------------------------
    # Combat actions
    # -----------------------------------------------------------------------

    def combat_attack(self):
        """Current party member attacks."""
        if not self.in_combat:
            return
        m = self.party[self.current_member_idx]
        if not m.is_alive or not self.combat_enemies:
            return

        # Status check: stunned = skip turn
        if StatusEffect.STUN in m.status_effects:
            m.status_effects.remove(StatusEffect.STUN)
            self.action_log.append(f"  {m.emoji} {m.name} is stunned and can't act!")
            self._advance_combat_turn()
            return

        # Pick target (first alive enemy)
        target = next((e for e in self.combat_enemies if e.hp > 0), None)
        if not target:
            return

        # Use first move
        move = m.moves[0] if m.moves else Move("Punch", MoveType.LOGIC, 5, 0.9, "Basic hit.")

        damage = self._calc_damage(m, target, move)

        # Analyze buff from Engineer
        if m.analyze_buff:
            damage = int(damage * 1.5)
            m.analyze_buff = False

        # Hidden Rogue backstab bonus
        if m.hidden:
            damage = int(damage * 2.5)
            m.hidden = False
            self.action_log.append(f"  [bold yellow]⚡ BACKSTAB![/bold yellow]")

        target.hp = max(0, target.hp - damage)
        self.action_log.append(
            f"  {m.emoji} {m.name} uses {move.name}! {damage} damage to {target.emoji} {target.name}!"
        )

        if target.hp <= 0:
            self.action_log.append(f"  [green]{target.emoji} {target.name} defeated![/green]")
            self.monsters_defeated += 1

        m.defending = False
        self._advance_combat_turn()

    def combat_skill(self):
        """Current party member uses class skill."""
        if not self.in_combat:
            return
        m = self.party[self.current_member_idx]
        if not m.is_alive:
            return

        # Silenced = can't use skills
        if StatusEffect.SILENCE in m.status_effects:
            self.action_log.append(f"  {m.emoji} {m.name} is silenced and can't use skills!")
            self._advance_combat_turn()
            return

        if m.buddy_class == BuddyClass.ENGINEER:
            # Analyze — next party attack +50%
            for ally in self.party:
                if ally.is_alive:
                    ally.analyze_buff = True
            self.action_log.append(f"  {m.emoji} {m.name} analyzes the enemy! Next attacks deal +50% damage!")

        elif m.buddy_class == BuddyClass.BERSERKER:
            # Berserk — double damage, take 25% recoil
            target = next((e for e in self.combat_enemies if e.hp > 0), None)
            if target:
                move = m.moves[0] if m.moves else Move("Smash", MoveType.CHAOS, 10, 0.8, "SMASH!")
                damage = self._calc_damage(m, target, move) * 2
                target.hp = max(0, target.hp - damage)
                recoil = max(1, damage // 4)
                m.hp = max(1, m.hp - recoil)
                self.action_log.append(
                    f"  {m.emoji} {m.name} goes BERSERK! {damage} damage! (took {recoil} recoil)"
                )
                if target.hp <= 0:
                    self.action_log.append(f"  [green]{target.emoji} {target.name} defeated![/green]")
                    self.monsters_defeated += 1

        elif m.buddy_class == BuddyClass.ROGUE:
            # Hide — spend a turn becoming hidden. Next attack is a 2.5x backstab.
            if m.hidden:
                # Already hidden — just attack with backstab bonus
                self.combat_attack()
                return
            m.hidden = True
            self.action_log.append(
                f"  {m.emoji} {m.name} slips into the shadows... [dim](next attack: BACKSTAB)[/dim]"
            )

        elif m.buddy_class == BuddyClass.MAGE:
            # AoE — hit all enemies for reduced damage
            move = m.moves[0] if m.moves else Move("Magic", MoveType.LOGIC, 6, 0.9, "Arcane blast.")
            for target in self.combat_enemies:
                if target.hp > 0:
                    damage = max(1, self._calc_damage(m, target, move) // 2)
                    target.hp = max(0, target.hp - damage)
                    self.action_log.append(f"  AoE hits {target.emoji} {target.name} for {damage}!")
                    if target.hp <= 0:
                        self.action_log.append(f"  [green]{target.emoji} {target.name} defeated![/green]")
                        self.monsters_defeated += 1

        elif m.buddy_class == BuddyClass.PALADIN:
            # Heal — restore HP to weakest, cure one status effect
            weakest = min((a for a in self.party if a.is_alive), key=lambda a: a.hp)
            heal = 10 + m.buddy_state.stats.get("patience", 10) // 3
            weakest.hp = min(weakest.max_hp, weakest.hp + heal)
            self.action_log.append(
                f"  {m.emoji} {m.name} heals {weakest.emoji} {weakest.name} for {heal} HP!"
            )
            # Cure one status effect
            if weakest.status_effects:
                cured = weakest.status_effects.pop(0)
                self.action_log.append(
                    f"  [green]{m.emoji} {m.name} cures {weakest.emoji} {weakest.name}'s {cured.value}![/green]"
                )

        m.defending = False
        self._advance_combat_turn()

    def combat_defend(self):
        """Current party member defends (half damage until next turn)."""
        if not self.in_combat:
            return
        m = self.party[self.current_member_idx]
        m.defending = True
        self.action_log.append(f"  {m.emoji} {m.name} takes a defensive stance!")
        self._advance_combat_turn()

    def combat_item(self):
        """Use a potion on the weakest party member."""
        if not self.in_combat or self.potions <= 0:
            self.action_log.append("[dim]No potions left![/dim]")
            return
        weakest = min((a for a in self.party if a.is_alive), key=lambda a: a.hp)
        self.potions -= 1
        heal = 15
        weakest.hp = min(weakest.max_hp, weakest.hp + heal)
        self.action_log.append(
            f"  Used potion on {weakest.emoji} {weakest.name}! +{heal} HP ({self.potions} left)"
        )
        self._advance_combat_turn()

    def _calc_damage(self, member: PartyMember, target: BattleFighter, move: Move) -> int:
        """Calculate damage from a party member to an enemy."""
        base = move.power + member.attack
        # Type effectiveness
        eff = TYPE_CHART.get(move.move_type, {}).get(target.primary_type, 1.0)
        # Variance
        variance = random.uniform(0.85, 1.15)
        # Defense reduction
        defense = max(1, target.defense)
        damage = max(1, int((base - defense // 2) * eff * variance))
        return damage

    def _advance_combat_turn(self):
        """Move to the next party member or enemy turn."""
        # Check if all enemies dead
        if all(e.hp <= 0 for e in self.combat_enemies):
            self._end_combat(won=True)
            return

        self.current_member_idx += 1

        # Skip dead members
        while self.current_member_idx < len(self.party) and not self.party[self.current_member_idx].is_alive:
            self.current_member_idx += 1

        if self.current_member_idx >= len(self.party):
            self._enemy_turn()
        else:
            self._prompt_combat_action()

    def _enemy_turn(self):
        """All enemies attack."""
        self.action_log.append("")

        # Process status effects on party at start of enemy phase
        for m in self.party:
            if not m.is_alive:
                continue
            if StatusEffect.POISON in m.status_effects:
                poison_dmg = max(1, 3 + self.floor)
                m.hp = max(0, m.hp - poison_dmg)
                self.action_log.append(f"  [magenta]🧪 {m.emoji} {m.name} takes {poison_dmg} poison damage![/magenta]")
                if m.hp <= 0:
                    self.action_log.append(f"  [red]{m.emoji} {m.name} falls to poison![/red]")
                # 30% chance to clear each turn
                if random.random() < 0.30:
                    m.status_effects.remove(StatusEffect.POISON)
                    self.action_log.append(f"  [green]{m.emoji} {m.name} shakes off the poison![/green]")
            # Silence clears after 1 enemy turn
            if StatusEffect.SILENCE in m.status_effects:
                if random.random() < 0.50:
                    m.status_effects.remove(StatusEffect.SILENCE)
                    self.action_log.append(f"  [green]{m.emoji} {m.name} can use skills again.[/green]")

        alive_party = [m for m in self.party if m.is_alive]

        for enemy in self.combat_enemies:
            if enemy.hp <= 0 or not alive_party:
                continue

            # Wizardry VI-style targeting: prefer front row (70/30 split)
            front = [m for m in alive_party if m.row == "front"]
            back = [m for m in alive_party if m.row == "back"]
            if front and back:
                target = random.choice(front) if random.random() < 0.70 else random.choice(back)
            elif front:
                target = random.choice(front)
            else:
                target = random.choice(back if back else alive_party)

            # Hidden rogues are harder to hit
            if target.hidden and random.random() < 0.5:
                self.action_log.append(f"  {enemy.emoji} {enemy.name} swings at shadows — {target.emoji} {target.name} dodges!")
                continue
            move = random.choice(enemy.moves) if enemy.moves else Move("Hit", MoveType.CHAOS, 5, 0.85, "Ouch.")

            # Accuracy check
            if random.random() > move.accuracy:
                self.action_log.append(f"  {enemy.emoji} {enemy.name} misses {target.emoji} {target.name}!")
                continue

            base = move.power + enemy.attack
            variance = random.uniform(0.85, 1.15)
            damage = max(1, int(base * variance))

            if target.defending:
                damage = max(1, damage // 2)

            # Back row defense bonus — take 25% less damage from melee
            if target.row == "back" and move.move_type != MoveType.HACK:
                damage = max(1, int(damage * 0.75))

            target.hp = max(0, target.hp - damage)
            self.action_log.append(
                f"  {enemy.emoji} {enemy.name} hits {target.emoji} {target.name} for {damage}!"
            )

            # Status effect chance from certain move types
            if target.is_alive and move.move_type == MoveType.CHAOS and random.random() < 0.20:
                if StatusEffect.POISON not in target.status_effects:
                    target.status_effects.append(StatusEffect.POISON)
                    self.action_log.append(f"  [magenta]🧪 {target.emoji} {target.name} is poisoned![/magenta]")
            elif target.is_alive and move.move_type == MoveType.HACK and random.random() < 0.15:
                if StatusEffect.SILENCE not in target.status_effects:
                    target.status_effects.append(StatusEffect.SILENCE)
                    self.action_log.append(f"  [magenta]🔇 {target.emoji} {target.name} is silenced![/magenta]")

            if target.hp <= 0:
                self.action_log.append(f"  [red]{target.emoji} {target.name} falls![/red]")
                alive_party = [m for m in self.party if m.is_alive]

        # Check party wipe
        if not any(m.is_alive for m in self.party):
            self._end_combat(won=False)
            return

        # Start new round
        self.current_member_idx = 0
        self.combat_turn += 1
        self.action_log.append(f"\n[dim]— Round {self.combat_turn + 1} —[/dim]")
        self._prompt_combat_action()

    def _end_combat(self, won: bool):
        """End combat."""
        self.in_combat = False
        # Clear all status effects and hidden state on combat end
        for m in self.party:
            m.status_effects.clear()
            m.hidden = False
            m.defending = False

        if won:
            gold = random.randint(5, 15) * self.floor
            self.gold += gold
            # Chance for potion drop
            if random.random() < 0.3:
                self.potions += 1
                self.action_log.append(f"[yellow]Found a potion! ({self.potions} total)[/yellow]")
            self.action_log.append(f"[green bold]Victory! +{gold} gold[/green bold]")
            line = _buddy_says(self.party, "combat_victory")
            if line:
                self.action_log.append(line)

            # Low HP warning
            worst = min((m.hp / m.max_hp for m in self.party if m.is_alive), default=1.0)
            if worst < 0.3:
                line = _buddy_says(self.party, "low_hp")
                if line:
                    self.action_log.append(line)

            # Resolve the encounter
            cell = self.grid[self.player_y][self.player_x]
            if cell.encounter:
                cell.encounter.resolved = True
        else:
            self.is_over = True
            self.action_log.append("[red bold]💀 Your party has been defeated! 💀[/red bold]")

    # -----------------------------------------------------------------------
    # Trap and mystery handling
    # -----------------------------------------------------------------------

    def _handle_trap(self, enc: Encounter):
        """Handle stepping on a trap."""
        self.action_log.append(f"[red]⚠ {enc.name}![/red]")
        self.action_log.append(f"[dim]{enc.description}[/dim]")
        line = _buddy_says(self.party, "trap_found")
        if line:
            self.action_log.append(line)

        # Check for Rogue to disarm
        rogue = next((m for m in self.party if m.buddy_class == BuddyClass.ROGUE and m.is_alive), None)
        paladin = next((m for m in self.party if m.buddy_class == BuddyClass.PALADIN and m.is_alive), None)

        if rogue:
            skill = rogue.buddy_state.stats.get("snark", 10)
            if random.random() < min(0.9, 0.5 + skill / 50.0):
                gold = random.randint(5, 12)
                self.gold += gold
                self.action_log.append(
                    f"[green]{rogue.emoji} {rogue.name} disarms the trap! +{gold} salvage gold[/green]"
                )
                enc.resolved = True
                return

        # Trap triggers
        damage = random.randint(5, 12)
        if paladin:
            damage = max(1, damage // 2)
            self.action_log.append(f"{paladin.emoji} {paladin.name}'s Shield Wall halves the damage!")

        for m in self.party:
            if m.is_alive:
                m.hp = max(0, m.hp - damage)

        self.action_log.append(f"[red]The trap hits the party for {damage} damage each![/red]")

        if not any(m.is_alive for m in self.party):
            self.is_over = True
            self.action_log.append("[red bold]💀 Your party has been wiped! 💀[/red bold]")

        enc.resolved = True

    def _handle_mystery(self, enc: Encounter):
        """Handle a mystery encounter."""
        self.action_log.append(f"[magenta]❓ {enc.name}[/magenta]")
        self.action_log.append(f"[dim]{enc.description}[/dim]")

        mage = next((m for m in self.party if m.buddy_class == BuddyClass.MAGE and m.is_alive), None)
        wisdom = max((m.buddy_state.stats.get("wisdom", 10) for m in self.party if m.is_alive), default=10)
        good_chance = min(0.85, 0.4 + wisdom / 60.0)

        if mage:
            self.action_log.append(f"{mage.emoji} {mage.name} senses what lies ahead...")
            good_chance += 0.15

        if random.random() < good_chance:
            gold = random.randint(10, 25)
            self.gold += gold
            self.action_log.append(f"[green]Solved the mystery! +{gold} gold[/green]")
        else:
            damage = random.randint(3, 8)
            for m in self.party:
                if m.is_alive:
                    m.hp = max(0, m.hp - damage)
            self.action_log.append(f"[red]It was a trap! {damage} damage to all![/red]")

        enc.resolved = True

    # -----------------------------------------------------------------------
    # Result
    # -----------------------------------------------------------------------

    def get_result(self) -> GameResult:
        if self.game_won:
            outcome = GameOutcome.WIN
            xp = 30 + self.monsters_defeated * 3 + self.floors_cleared * 5
            mood = 8
        elif self.floors_cleared > 0:
            outcome = GameOutcome.DRAW
            xp = 10 + self.monsters_defeated * 2 + self.floors_cleared * 3
            mood = 0
        else:
            outcome = GameOutcome.LOSE
            xp = 5 + self.monsters_defeated * 2
            mood = -3

        return GameResult(
            game_type=GameType.CRAWL,
            outcome=outcome,
            buddy_id=0,
            score={"floors": self.floors_cleared, "monsters": self.monsters_defeated,
                   "gold": self.gold, "won": self.game_won},
            xp_earned=xp, mood_delta=mood,
        )
