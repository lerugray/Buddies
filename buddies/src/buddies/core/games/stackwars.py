"""StackWars — a micro-4X wargame for the Buddies Arcade.

Designed by Claude with direction from "A Contemporary Guide to Wargame Design"
by Ray Weiss, and inspired by Avianos from UFO 50.

Core design principles (from the book):
- Thesis: personality traits that make you a good coder make you a terrible
  conqueror. Each faction's strength is its strategic blind spot.
- Scope fence: 5x5 grid, 3 resources, 5 unit types, 5 abilities, ~20 turns.
- Chrome test: every mechanic produces decisions every turn.
- Movement is the foundation.
- Asymmetry through faction menus, not just stats.

Zero AI cost. Pure deterministic/random resolution. No API calls.
Architected for 2-4 players (AI opponents now, async PBEM later).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_W = 5
GRID_H = 5
FLAGS_TO_WIN = 3
HOLD_TURNS_TO_WIN = 1  # Must hold flags through opponent's full turn


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Terrain(Enum):
    PLAINS = "plains"
    MOUNTAIN = "mountain"      # +2 defense
    SERVER = "server"          # +1 resource gain
    FIREWALL = "firewall"      # Blocks movement
    HQ = "hq"                  # Starting base, produces units
    FLAG = "flag"              # Capture objective


class UnitType(Enum):
    SCRIPT_KIDDIE = "script_kiddie"  # Cheap melee swarm
    HACKER = "hacker"                # Glass cannon ranged
    ARCHITECT = "architect"          # Defensive ranged
    OPERATOR = "operator"            # Fast flanker
    SYSADMIN = "sysadmin"            # Heavy elite


class Faction(Enum):
    ENGINEERS = "engineers"        # DEBUGGING — precision, intel, defense
    ANARCHISTS = "anarchists"      # CHAOS — speed, unpredictability
    PROVOCATEURS = "provocateurs"  # SNARK — disruption, theft, conversion
    SAGES = "sages"                # WISDOM — upgrades, late-game power
    MONKS = "monks"                # PATIENCE — economy, fortification


class AbilityType(Enum):
    DEPLOY = "deploy"    # Gain code, recruit, place
    BUILD = "build"      # Structures, workers, fortify
    MARCH = "march"      # Move, claim, scout
    INVOKE = "invoke"    # Bugs, spells, coffee
    RALLY = "rally"      # Muster, deploy to flags, trade


class OrderType(Enum):
    ATTACK = "attack"
    HOLD = "hold"
    RAZE = "raze"
    FLEE = "flee"


# ---------------------------------------------------------------------------
# Stat → Faction mapping
# ---------------------------------------------------------------------------

STAT_TO_FACTION: dict[str, Faction] = {
    "debugging": Faction.ENGINEERS,
    "chaos": Faction.ANARCHISTS,
    "snark": Faction.PROVOCATEURS,
    "wisdom": Faction.SAGES,
    "patience": Faction.MONKS,
}

FACTION_EMOJI: dict[Faction, str] = {
    Faction.ENGINEERS: "🔧",
    Faction.ANARCHISTS: "🔥",
    Faction.PROVOCATEURS: "🗡️",
    Faction.SAGES: "📖",
    Faction.MONKS: "🛡️",
}

FACTION_COLOR: dict[Faction, str] = {
    Faction.ENGINEERS: "cyan",
    Faction.ANARCHISTS: "red",
    Faction.PROVOCATEURS: "magenta",
    Faction.SAGES: "blue",
    Faction.MONKS: "green",
}

FACTION_DESC: dict[Faction, str] = {
    Faction.ENGINEERS: "Methodical. Perfect intel, strong defense, slow expansion.",
    Faction.ANARCHISTS: "Unpredictable. Fast expansion, weak garrisons.",
    Faction.PROVOCATEURS: "Disruptive. Steal, sabotage, convert. Weak in fair fights.",
    Faction.SAGES: "Strategic. Best upgrades, powerful late game. Vulnerable early.",
    Faction.MONKS: "Defensive. Best economy and forts. Weakest offense.",
}


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

UNIT_STATS: dict[UnitType, dict] = {
    UnitType.SCRIPT_KIDDIE: {
        "name": "Script Kiddie", "emoji": "👾", "cost": 3,
        "attack": 2, "defense": 1, "speed": 2, "hp": 3,
    },
    UnitType.HACKER: {
        "name": "Hacker", "emoji": "💻", "cost": 5,
        "attack": 4, "defense": 1, "speed": 1, "hp": 2,
    },
    UnitType.ARCHITECT: {
        "name": "Architect", "emoji": "🏗️", "cost": 5,
        "attack": 2, "defense": 4, "speed": 1, "hp": 4,
    },
    UnitType.OPERATOR: {
        "name": "Operator", "emoji": "⚡", "cost": 4,
        "attack": 3, "defense": 2, "speed": 3, "hp": 3,
    },
    UnitType.SYSADMIN: {
        "name": "Sysadmin", "emoji": "🛠️", "cost": 8,
        "attack": 4, "defense": 4, "speed": 1, "hp": 6,
    },
}

# Rock-paper-scissors-plus matchup bonuses (attacker type → defender type → bonus)
UNIT_MATCHUPS: dict[UnitType, dict[UnitType, int]] = {
    UnitType.SCRIPT_KIDDIE: {UnitType.ARCHITECT: +2, UnitType.HACKER: -2},
    UnitType.HACKER: {UnitType.SCRIPT_KIDDIE: +2, UnitType.SYSADMIN: +1, UnitType.ARCHITECT: -1},
    UnitType.ARCHITECT: {UnitType.HACKER: +2, UnitType.OPERATOR: -2},
    UnitType.OPERATOR: {UnitType.ARCHITECT: +2, UnitType.SCRIPT_KIDDIE: -1},
    UnitType.SYSADMIN: {UnitType.OPERATOR: +1, UnitType.HACKER: -1},
}


@dataclass
class Unit:
    """A single unit on the board."""
    unit_type: UnitType
    owner: int           # Player index
    hp: int = 0
    moved_this_turn: bool = False

    def __post_init__(self):
        if self.hp == 0:
            self.hp = UNIT_STATS[self.unit_type]["hp"]

    @property
    def stats(self) -> dict:
        return UNIT_STATS[self.unit_type]

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def name(self) -> str:
        return self.stats["name"]

    @property
    def emoji(self) -> str:
        return self.stats["emoji"]


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------

class BuildingType(Enum):
    SEED_FACTORY = "seed_factory"    # +2 Code per turn
    BARRACKS = "barracks"            # Can recruit units here
    FORTRESS = "fortress"            # +3 defense for tile
    MONUMENT = "monument"            # +1 favor per turn


BUILDING_STATS: dict[BuildingType, dict] = {
    BuildingType.SEED_FACTORY: {"name": "Seed Factory", "emoji": "🏭", "cost": 8},
    BuildingType.BARRACKS: {"name": "Barracks", "emoji": "⚔️", "cost": 6},
    BuildingType.FORTRESS: {"name": "Fortress", "emoji": "🏰", "cost": 10},
    BuildingType.MONUMENT: {"name": "Monument", "emoji": "🗿", "cost": 12},
}


@dataclass
class Building:
    building_type: BuildingType
    owner: int

    @property
    def stats(self) -> dict:
        return BUILDING_STATS[self.building_type]


# ---------------------------------------------------------------------------
# Map tile
# ---------------------------------------------------------------------------

@dataclass
class Tile:
    """A single tile on the 5x5 grid."""
    x: int
    y: int
    terrain: Terrain
    owner: int = -1          # -1 = neutral
    units: list[Unit] = field(default_factory=list)
    building: Building | None = None
    fortified: bool = False

    @property
    def defense_bonus(self) -> int:
        bonus = 0
        if self.terrain == Terrain.MOUNTAIN:
            bonus += 2
        if self.terrain == Terrain.HQ:
            bonus += 3
        if self.fortified:
            bonus += 1
        if self.building and self.building.building_type == BuildingType.FORTRESS:
            bonus += 3
        return bonus

    @property
    def is_flag(self) -> bool:
        return self.terrain == Terrain.FLAG


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

@dataclass
class PlayerState:
    """State for one player."""
    index: int
    faction: Faction
    buddy_name: str
    buddy_emoji: str
    # Resources
    code: int = 15           # Main currency (capped at 99)
    bugs: int = 0            # Spell resource (capped at 9)
    coffee: int = 0          # Special resource (capped at 9)
    # Ability cooldowns (0 = available, >0 = turns until available)
    cooldowns: dict[str, int] = field(default_factory=lambda: {
        a.value: 0 for a in AbilityType
    })
    # Ability favor (invest to upgrade — every 2 favor = 1 blessing)
    favor: dict[str, int] = field(default_factory=lambda: {
        a.value: 0 for a in AbilityType
    })
    blessings: dict[str, int] = field(default_factory=lambda: {
        a.value: 0 for a in AbilityType
    })
    # Flags held
    flags_held: int = 0
    flags_held_turns: int = 0  # Consecutive turns holding enough flags
    # Is AI?
    is_ai: bool = False
    eliminated: bool = False

    def cap_resources(self):
        self.code = min(99, max(0, self.code))
        self.bugs = min(9, max(0, self.bugs))
        self.coffee = min(9, max(0, self.coffee))

    def available_abilities(self) -> list[AbilityType]:
        return [a for a in AbilityType if self.cooldowns[a.value] == 0]

    def tick_cooldowns(self):
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= 1


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class StackWarsState:
    """Complete game state."""
    grid: list[list[Tile]]
    players: list[PlayerState]
    current_player: int = 0
    turn: int = 1
    phase: str = "choose_ability"  # choose_ability, action_1, action_2, action_3, combat, end_turn
    chosen_ability: AbilityType | None = None
    action_step: int = 0       # Which action (0, 1, 2) in the chosen ability
    winner: int = -1           # -1 = no winner yet
    log: list[str] = field(default_factory=list)
    max_turns: int = 30

    @property
    def active_player(self) -> PlayerState:
        return self.players[self.current_player]

    @property
    def game_over(self) -> bool:
        return self.winner >= 0 or self.turn > self.max_turns

    def tile_at(self, x: int, y: int) -> Tile | None:
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            return self.grid[y][x]
        return None

    def player_units(self, player_idx: int) -> list[tuple[int, int, Unit]]:
        """Get all units for a player as (x, y, unit) tuples."""
        results = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                for unit in self.grid[y][x].units:
                    if unit.owner == player_idx:
                        results.append((x, y, unit))
        return results

    def player_tiles(self, player_idx: int) -> list[Tile]:
        """Get all tiles owned by a player."""
        return [
            self.grid[y][x]
            for y in range(GRID_H)
            for x in range(GRID_W)
            if self.grid[y][x].owner == player_idx
        ]

    def count_flags(self, player_idx: int) -> int:
        return sum(
            1 for y in range(GRID_H) for x in range(GRID_W)
            if self.grid[y][x].is_flag and self.grid[y][x].owner == player_idx
        )


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------

def generate_map(num_players: int = 2) -> list[list[Tile]]:
    """Generate a 5x5 grid with symmetric terrain placement."""
    grid = [[Tile(x=x, y=y, terrain=Terrain.PLAINS) for x in range(GRID_W)] for y in range(GRID_H)]

    # HQ positions (opposite corners for 2 players)
    hq_positions = [(0, 0), (4, 4), (0, 4), (4, 0)]
    for i in range(min(num_players, 4)):
        x, y = hq_positions[i]
        grid[y][x].terrain = Terrain.HQ
        grid[y][x].owner = i

    # Flag tiles — center and symmetric positions
    flag_positions = [(2, 2), (1, 1), (3, 3), (1, 3), (3, 1)]
    for i, (x, y) in enumerate(flag_positions):
        if i < max(3, num_players + 1):
            grid[y][x].terrain = Terrain.FLAG

    # Mountains — symmetric placement
    mountain_positions = [(0, 2), (4, 2), (2, 0), (2, 4)]
    for x, y in mountain_positions:
        if grid[y][x].terrain == Terrain.PLAINS:
            grid[y][x].terrain = Terrain.MOUNTAIN

    # Servers — resource tiles
    server_positions = [(1, 0), (3, 4), (0, 3), (4, 1)]
    for x, y in server_positions:
        if grid[y][x].terrain == Terrain.PLAINS:
            grid[y][x].terrain = Terrain.SERVER

    # One firewall near center
    if grid[2][1].terrain == Terrain.PLAINS:
        grid[2][1].terrain = Terrain.FIREWALL
    if grid[2][3].terrain == Terrain.PLAINS:
        grid[2][3].terrain = Terrain.FIREWALL

    return grid


# ---------------------------------------------------------------------------
# Game creation
# ---------------------------------------------------------------------------

def faction_from_buddy(state: BuddyState) -> Faction:
    """Determine faction from buddy's dominant stat."""
    dominant = max(state.stats, key=state.stats.get)
    return STAT_TO_FACTION.get(dominant, Faction.ENGINEERS)


def create_stackwars(
    buddy: BuddyState,
    opponent_faction: Faction | None = None,
    num_players: int = 2,
) -> StackWarsState:
    """Create a new StackWars game."""
    grid = generate_map(num_players)

    # Player 0 = human (buddy's faction)
    player_faction = faction_from_buddy(buddy)
    players = [
        PlayerState(
            index=0,
            faction=player_faction,
            buddy_name=buddy.name,
            buddy_emoji=buddy.species.emoji,
        ),
    ]

    # AI opponents
    ai_factions = [f for f in Faction if f != player_faction]
    random.shuffle(ai_factions)
    for i in range(1, num_players):
        faction = opponent_faction if (i == 1 and opponent_faction) else ai_factions[i - 1]
        players.append(
            PlayerState(
                index=i,
                faction=faction,
                buddy_name=f"{FACTION_EMOJI[faction]} AI",
                buddy_emoji=FACTION_EMOJI[faction],
                is_ai=True,
            ),
        )

    state = StackWarsState(grid=grid, players=players)

    # Place starting units
    hq_positions = [(0, 0), (4, 4), (0, 4), (4, 0)]
    for i, player in enumerate(players):
        x, y = hq_positions[i]
        tile = grid[y][x]
        # Each player starts with 2 Script Kiddies and 1 Operator
        tile.units.append(Unit(UnitType.SCRIPT_KIDDIE, i))
        tile.units.append(Unit(UnitType.SCRIPT_KIDDIE, i))
        tile.units.append(Unit(UnitType.OPERATOR, i))

    state.log.append("[bold]StackWars begins![/bold]")
    state.log.append(f"Hold {FLAGS_TO_WIN} flag tiles for a full round to win.")
    state.log.append("")

    return state


# ---------------------------------------------------------------------------
# Ability actions
# ---------------------------------------------------------------------------

ABILITY_ACTIONS: dict[AbilityType, list[str]] = {
    AbilityType.DEPLOY: ["Gain +5 Code", "Recruit a unit (at HQ/Barracks)", "Deploy: move a unit to any owned tile"],
    AbilityType.BUILD: ["Build a structure on owned tile", "Fortify a tile (+1 def)", "Gain +2 Code"],
    AbilityType.MARCH: ["Move all unmoved units 1 tile", "Claim neutral tiles with units on them", "Scout (reveal all enemy unit counts)"],
    AbilityType.INVOKE: ["Gain +2 Bugs", "Cast Bug Bomb (2 dmg to all enemies on a tile, costs 3 Bugs)", "Gain +1 Coffee"],
    AbilityType.RALLY: ["Gain +3 Code at each Server you own", "Recruit free Script Kiddie at each Barracks", "Gain +1 Bug, +1 Coffee"],
}


def choose_ability(state: StackWarsState, ability: AbilityType) -> list[str]:
    """Player chooses an ability for this turn."""
    player = state.active_player
    lines = []

    if player.cooldowns[ability.value] > 0:
        return [f"[red]{ability.value.title()} is on cooldown for {player.cooldowns[ability.value]} more turn(s).[/red]"]

    state.chosen_ability = ability
    state.phase = "actions"
    state.action_step = 0

    # Set cooldown (2 turns)
    player.cooldowns[ability.value] = 2

    # Gain favor
    player.favor[ability.value] += 1
    favor = player.favor[ability.value]
    if favor > 0 and favor % 2 == 0:
        player.blessings[ability.value] += 1
        lines.append(f"[bold yellow]Blessing earned! {ability.value.title()} ability upgraded (level {player.blessings[ability.value]})[/bold yellow]")

    emoji = FACTION_EMOJI[player.faction]
    lines.append(f"\n{emoji} {player.buddy_name} invokes [bold]{ability.value.upper()}[/bold]")

    actions = ABILITY_ACTIONS[ability]
    for i, desc in enumerate(actions):
        lines.append(f"  Action {i+1}: {desc}")

    return lines


def execute_action(state: StackWarsState, target: str = "") -> list[str]:
    """Execute the current action step. Returns output lines."""
    if not state.chosen_ability:
        return ["No ability chosen."]

    player = state.active_player
    ability = state.chosen_ability
    step = state.action_step
    lines = []
    blessed = player.blessings[ability.value]

    if ability == AbilityType.DEPLOY:
        if step == 0:
            gain = 5 + blessed
            player.code += gain
            player.cap_resources()
            lines.append(f"[yellow]+{gain} Code[/yellow] (total: {player.code})")
        elif step == 1:
            lines.extend(_action_recruit(state, target))
        elif step == 2:
            lines.extend(_action_teleport_unit(state, target))

    elif ability == AbilityType.BUILD:
        if step == 0:
            lines.extend(_action_build(state, target))
        elif step == 1:
            lines.extend(_action_fortify(state, target))
        elif step == 2:
            gain = 2 + blessed
            player.code += gain
            player.cap_resources()
            lines.append(f"[yellow]+{gain} Code[/yellow]")

    elif ability == AbilityType.MARCH:
        if step == 0:
            lines.extend(_action_move_all(state))
        elif step == 1:
            lines.extend(_action_claim_tiles(state))
        elif step == 2:
            lines.extend(_action_scout(state))

    elif ability == AbilityType.INVOKE:
        if step == 0:
            gain = 2 + blessed
            player.bugs += gain
            player.cap_resources()
            lines.append(f"[magenta]+{gain} Bugs[/magenta] (total: {player.bugs})")
        elif step == 1:
            lines.extend(_action_bug_bomb(state, target))
        elif step == 2:
            player.coffee += 1
            player.cap_resources()
            lines.append(f"[yellow]+1 Coffee[/yellow] (total: {player.coffee})")

    elif ability == AbilityType.RALLY:
        if step == 0:
            lines.extend(_action_server_income(state))
        elif step == 1:
            lines.extend(_action_free_recruits(state))
        elif step == 2:
            player.bugs += 1
            player.coffee += 1
            player.cap_resources()
            lines.append(f"[magenta]+1 Bug[/magenta], [yellow]+1 Coffee[/yellow]")

    # Advance step
    state.action_step += 1
    if state.action_step >= 3:
        lines.extend(_end_turn(state))

    return lines


def skip_action(state: StackWarsState) -> list[str]:
    """Skip the current action step."""
    state.action_step += 1
    lines = [f"[dim]Skipped action {state.action_step}.[/dim]"]
    if state.action_step >= 3:
        lines.extend(_end_turn(state))
    return lines


# ---------------------------------------------------------------------------
# Coordinate parsing helper
# ---------------------------------------------------------------------------

def _parse_coords(text: str) -> tuple[int, int] | None:
    """Parse 'x,y' or 'x y' coordinate input. Returns (x, y) or None."""
    text = text.strip().lower()
    for sep in [",", " "]:
        if sep in text:
            parts = text.split(sep, 1)
            try:
                x, y = int(parts[0].strip()), int(parts[1].strip())
                if 0 <= x < GRID_W and 0 <= y < GRID_H:
                    return (x, y)
            except (ValueError, IndexError):
                pass
    return None


# ---------------------------------------------------------------------------
# Action implementations
# ---------------------------------------------------------------------------

def _action_recruit(state: StackWarsState, unit_name: str) -> list[str]:
    """Recruit a unit at HQ or Barracks."""
    player = state.active_player

    # Parse unit type
    type_map = {
        "kiddie": UnitType.SCRIPT_KIDDIE, "script": UnitType.SCRIPT_KIDDIE, "1": UnitType.SCRIPT_KIDDIE,
        "hacker": UnitType.HACKER, "hack": UnitType.HACKER, "2": UnitType.HACKER,
        "architect": UnitType.ARCHITECT, "arch": UnitType.ARCHITECT, "3": UnitType.ARCHITECT,
        "operator": UnitType.OPERATOR, "op": UnitType.OPERATOR, "4": UnitType.OPERATOR,
        "sysadmin": UnitType.SYSADMIN, "sys": UnitType.SYSADMIN, "admin": UnitType.SYSADMIN, "5": UnitType.SYSADMIN,
    }

    if not unit_name:
        lines = ["[bold]Recruit which unit?[/bold]"]
        for ut in UnitType:
            s = UNIT_STATS[ut]
            lines.append(f"  {s['emoji']} [bold]{s['name']}[/bold] — {s['cost']} Code (ATK:{s['attack']} DEF:{s['defense']} SPD:{s['speed']} HP:{s['hp']})")
        lines.append("[dim]Type the unit name or number (1-5).[/dim]")
        return lines

    utype = type_map.get(unit_name.lower().strip())
    if not utype:
        return [f"Unknown unit '{unit_name}'. Try: kiddie, hacker, architect, operator, sysadmin"]

    cost = UNIT_STATS[utype]["cost"]
    if player.code < cost:
        return [f"[red]Not enough Code! Need {cost}, have {player.code}.[/red]"]

    # Find HQ or Barracks tile
    spawn_tile = None
    for tile in state.player_tiles(player.index):
        if tile.terrain == Terrain.HQ:
            spawn_tile = tile
            break
        if tile.building and tile.building.building_type == BuildingType.BARRACKS and tile.building.owner == player.index:
            spawn_tile = tile

    if not spawn_tile:
        return ["[red]No HQ or Barracks available to recruit at![/red]"]

    player.code -= cost
    spawn_tile.units.append(Unit(utype, player.index))
    return [f"[green]Recruited {UNIT_STATS[utype]['emoji']} {UNIT_STATS[utype]['name']} at ({spawn_tile.x},{spawn_tile.y})![/green] (-{cost} Code)"]


def _action_teleport_unit(state: StackWarsState, target: str) -> list[str]:
    """Teleport a unit from HQ/Barracks to any owned tile."""
    player = state.active_player

    # Find units at HQ or Barracks
    spawn_units: list[tuple[int, int, Unit]] = []
    for x, y, unit in state.player_units(player.index):
        tile = state.grid[y][x]
        if tile.terrain == Terrain.HQ or (tile.building and tile.building.building_type == BuildingType.BARRACKS):
            spawn_units.append((x, y, unit))

    if not spawn_units:
        return ["[dim]No units at HQ/Barracks to deploy.[/dim]"]

    # Find owned tiles to deploy to (excluding spawn tile itself)
    owned = [t for t in state.player_tiles(player.index)
             if not (t.terrain == Terrain.FIREWALL)]

    if not owned:
        return ["[dim]No owned tiles to deploy to.[/dim]"]

    if not target:
        lines = [f"[bold]Deploy a unit to an owned tile.[/bold]"]
        lines.append(f"  {len(spawn_units)} unit(s) available at staging areas.")
        # Show valid targets
        targets = [f"({t.x},{t.y})" for t in owned if t not in
                   [state.grid[sy][sx] for sx, sy, _ in spawn_units]][:8]
        if targets:
            lines.append(f"  Valid tiles: {' '.join(targets)}")
        lines.append("[dim]Type coordinates (e.g. '2,3') or 'skip'.[/dim]")
        return lines

    # Parse coordinates
    coords = _parse_coords(target)
    if not coords:
        return ["[dim]Type coordinates like '2,3' or 'skip'.[/dim]"]

    tx, ty = coords
    dest = state.tile_at(tx, ty)
    if not dest or dest.owner != player.index:
        return [f"[red]({tx},{ty}) is not an owned tile.[/red]"]
    if dest.terrain == Terrain.FIREWALL:
        return [f"[red]Can't deploy through a firewall.[/red]"]

    # Move first available unit
    sx, sy, unit = spawn_units[0]
    state.grid[sy][sx].units.remove(unit)
    dest.units.append(unit)
    unit.moved_this_turn = True
    return [f"[green]Deployed {unit.emoji} {unit.name} from ({sx},{sy}) to ({tx},{ty})![/green]"]


def _action_build(state: StackWarsState, target: str) -> list[str]:
    """Build a structure on an owned tile. Input: 'building_name' or 'building_name x,y'."""
    player = state.active_player

    if not target:
        lines = ["[bold]Build which structure?[/bold]"]
        for bt in BuildingType:
            s = BUILDING_STATS[bt]
            lines.append(f"  {s['emoji']} [bold]{s['name']}[/bold] — {s['cost']} Code")
        lines.append("[dim]Type: building name (e.g. 'barracks') or 'barracks 1,2' for a specific tile.[/dim]")
        return lines

    type_map = {
        "factory": BuildingType.SEED_FACTORY, "seed": BuildingType.SEED_FACTORY, "1": BuildingType.SEED_FACTORY,
        "barracks": BuildingType.BARRACKS, "bar": BuildingType.BARRACKS, "2": BuildingType.BARRACKS,
        "fortress": BuildingType.FORTRESS, "fort": BuildingType.FORTRESS, "3": BuildingType.FORTRESS,
        "monument": BuildingType.MONUMENT, "mon": BuildingType.MONUMENT, "4": BuildingType.MONUMENT,
    }

    # Parse "building x,y" or just "building"
    parts = target.lower().strip().split(maxsplit=1)
    building_name = parts[0]
    coord_str = parts[1] if len(parts) > 1 else ""

    btype = type_map.get(building_name)
    if not btype:
        return [f"Unknown building '{building_name}'. Try: factory, barracks, fortress, monument"]

    cost = BUILDING_STATS[btype]["cost"]
    if player.code < cost:
        return [f"[red]Not enough Code! Need {cost}, have {player.code}.[/red]"]

    # Try specific coordinates first
    build_tile = None
    if coord_str:
        coords = _parse_coords(coord_str)
        if coords:
            tile = state.tile_at(*coords)
            if tile and tile.owner == player.index and not tile.building and tile.terrain not in (Terrain.FIREWALL, Terrain.HQ):
                build_tile = tile
            elif tile:
                return [f"[red]Can't build at ({coords[0]},{coords[1]}) — must be your tile, no building, not HQ/firewall.[/red]"]

    # Auto-pick if no coords given
    if not build_tile:
        for tile in state.player_tiles(player.index):
            if not tile.building and tile.terrain not in (Terrain.FIREWALL, Terrain.HQ):
                build_tile = tile
                break

    if not build_tile:
        return ["[red]No available tile to build on![/red]"]

    player.code -= cost
    build_tile.building = Building(btype, player.index)
    return [f"[green]Built {BUILDING_STATS[btype]['emoji']} {BUILDING_STATS[btype]['name']} at ({build_tile.x},{build_tile.y})![/green]"]


def _action_fortify(state: StackWarsState, target: str) -> list[str]:
    """Fortify an owned tile (+1 defense). Optional target: 'x,y'."""
    player = state.active_player

    # Try specific coordinates
    if target:
        coords = _parse_coords(target)
        if coords:
            tile = state.tile_at(*coords)
            if tile and tile.owner == player.index and not tile.fortified and tile.units:
                tile.fortified = True
                return [f"[green]Fortified tile ({tile.x},{tile.y}) — +1 defense.[/green]"]
            elif tile:
                return [f"[red]Can't fortify ({coords[0]},{coords[1]}) — must be owned, unfortified, with units.[/red]"]

    # Auto-pick
    for tile in state.player_tiles(player.index):
        if not tile.fortified and tile.units:
            tile.fortified = True
            return [f"[green]Fortified tile ({tile.x},{tile.y}) — +1 defense.[/green]"]
    return ["[dim]No tiles with units available to fortify.[/dim]"]


def _action_move_all(state: StackWarsState) -> list[str]:
    """Move all unmoved units 1 tile toward the nearest flag or enemy."""
    player = state.active_player
    moved = 0

    # Find flag positions
    flags = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            if state.grid[y][x].is_flag and state.grid[y][x].owner != player.index:
                flags.append((x, y))

    if not flags:
        # All flags owned — move toward enemy HQ
        for p in state.players:
            if p.index != player.index and not p.eliminated:
                for y in range(GRID_H):
                    for x in range(GRID_W):
                        if state.grid[y][x].terrain == Terrain.HQ and state.grid[y][x].owner == p.index:
                            flags.append((x, y))

    units = state.player_units(player.index)
    for ux, uy, unit in units:
        if unit.moved_this_turn:
            continue

        # Find best adjacent tile toward nearest target
        best_tile = None
        best_dist = 999

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = ux + dx, uy + dy
            tile = state.tile_at(nx, ny)
            if not tile or tile.terrain == Terrain.FIREWALL:
                continue
            # Don't move into tiles with enemy units (that's combat)
            enemy_units = [u for u in tile.units if u.owner != player.index]
            if enemy_units:
                continue

            for fx, fy in flags:
                dist = abs(nx - fx) + abs(ny - fy)
                if dist < best_dist:
                    best_dist = dist
                    best_tile = tile

        if best_tile:
            # Move unit
            state.grid[uy][ux].units.remove(unit)
            best_tile.units.append(unit)
            unit.moved_this_turn = True
            moved += 1

    return [f"[cyan]Moved {moved} unit(s) toward objectives.[/cyan]"]


def _action_claim_tiles(state: StackWarsState) -> list[str]:
    """Claim neutral tiles that have the player's units on them."""
    player = state.active_player
    claimed = 0
    for y in range(GRID_H):
        for x in range(GRID_W):
            tile = state.grid[y][x]
            if tile.owner != player.index:
                player_units = [u for u in tile.units if u.owner == player.index]
                enemy_units = [u for u in tile.units if u.owner != player.index]
                if player_units and not enemy_units:
                    tile.owner = player.index
                    claimed += 1
    if claimed:
        return [f"[green]Claimed {claimed} tile(s)![/green]"]
    return ["[dim]No tiles to claim.[/dim]"]


def _action_scout(state: StackWarsState) -> list[str]:
    """Reveal all enemy positions."""
    lines = ["[cyan]Scout report:[/cyan]"]
    for p in state.players:
        if p.index == state.active_player.index or p.eliminated:
            continue
        units = state.player_units(p.index)
        emoji = FACTION_EMOJI[p.faction]
        lines.append(f"  {emoji} {p.buddy_name}: {len(units)} units, {p.code} Code, {state.count_flags(p.index)} flags")
    return lines


def _action_bug_bomb(state: StackWarsState, target: str) -> list[str]:
    """Deal 2 damage to all enemy units on a tile. Costs 3 Bugs. Target: 'x,y' or auto-picks densest cluster."""
    player = state.active_player
    if player.bugs < 3:
        return [f"[red]Need 3 Bugs, have {player.bugs}.[/red]"]

    # Collect all tiles with enemies
    enemy_tiles: list[tuple[int, int, list[Unit]]] = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            enemies = [u for u in state.grid[y][x].units if u.owner != player.index]
            if enemies:
                enemy_tiles.append((x, y, enemies))

    if not enemy_tiles:
        return ["[dim]No enemy units visible to bomb.[/dim]"]

    # Try specific coordinates
    bomb_x, bomb_y, bomb_enemies = None, None, None
    if target:
        coords = _parse_coords(target)
        if coords:
            for ex, ey, enemies in enemy_tiles:
                if ex == coords[0] and ey == coords[1]:
                    bomb_x, bomb_y, bomb_enemies = ex, ey, enemies
                    break
            if not bomb_enemies:
                return [f"[red]No enemies at ({coords[0]},{coords[1]}).[/red]"]

    # Auto-target: pick tile with most enemy units
    if not bomb_enemies:
        enemy_tiles.sort(key=lambda t: len(t[2]), reverse=True)
        bomb_x, bomb_y, bomb_enemies = enemy_tiles[0]

    player.bugs -= 3
    tile = state.grid[bomb_y][bomb_x]
    dmg = 2 + player.blessings[AbilityType.INVOKE.value]
    killed = 0
    for u in bomb_enemies:
        u.hp -= dmg
        if not u.alive:
            killed += 1
    tile.units = [u for u in tile.units if u.alive]
    return [f"[magenta]Bug Bomb at ({bomb_x},{bomb_y})! {dmg} damage to {len(bomb_enemies)} enemies, {killed} killed.[/magenta]"]


def _action_server_income(state: StackWarsState) -> list[str]:
    """Gain +3 Code at each Server you own."""
    player = state.active_player
    servers = sum(
        1 for tile in state.player_tiles(player.index)
        if tile.terrain == Terrain.SERVER
    )
    if servers:
        gain = servers * 3
        player.code += gain
        player.cap_resources()
        return [f"[yellow]+{gain} Code from {servers} Server(s)![/yellow]"]
    return ["[dim]No Servers owned.[/dim]"]


def _action_free_recruits(state: StackWarsState) -> list[str]:
    """Recruit a free Script Kiddie at each Barracks."""
    player = state.active_player
    count = 0
    for tile in state.player_tiles(player.index):
        if tile.building and tile.building.building_type == BuildingType.BARRACKS and tile.building.owner == player.index:
            tile.units.append(Unit(UnitType.SCRIPT_KIDDIE, player.index))
            count += 1
    if count:
        return [f"[green]Mustered {count} free Script Kiddie(s) at Barracks![/green]"]
    return ["[dim]No Barracks to muster at.[/dim]"]


# ---------------------------------------------------------------------------
# Combat resolution (odds-based, per the book)
# ---------------------------------------------------------------------------

def resolve_combat(state: StackWarsState) -> list[str]:
    """Resolve combat on all contested tiles."""
    lines = []

    for y in range(GRID_H):
        for x in range(GRID_W):
            tile = state.grid[y][x]
            # Group units by owner
            by_owner: dict[int, list[Unit]] = {}
            for u in tile.units:
                by_owner.setdefault(u.owner, []).append(u)

            if len(by_owner) < 2:
                continue

            # Combat between each pair (simplified: strongest attacker vs defender)
            owners = list(by_owner.keys())
            attacker_idx = owners[0]
            defender_idx = owners[1]
            attackers = by_owner[attacker_idx]
            defenders = by_owner[defender_idx]

            # Calculate total strength
            atk_str = sum(u.stats["attack"] for u in attackers)
            def_str = sum(u.stats["defense"] for u in defenders) + tile.defense_bonus

            # Matchup bonuses
            for au in attackers:
                matchups = UNIT_MATCHUPS.get(au.unit_type, {})
                for du in defenders:
                    atk_str += matchups.get(du.unit_type, 0)

            # Faction bonuses
            atk_faction = state.players[attacker_idx].faction
            def_faction = state.players[defender_idx].faction
            if atk_faction == Faction.ANARCHISTS:
                atk_str += random.randint(0, 3)  # Unpredictable
            if def_faction == Faction.MONKS:
                def_str += 2  # Defensive bonus
            if atk_faction == Faction.PROVOCATEURS:
                def_str -= 1  # Disruption
            if def_faction == Faction.ENGINEERS:
                def_str += 1  # Precision defense

            # Odds ratio
            if def_str <= 0:
                def_str = 1
            ratio = atk_str / def_str

            # CRT resolution (simplified)
            roll = random.random()
            atk_emoji = FACTION_EMOJI[atk_faction]
            def_emoji = FACTION_EMOJI[def_faction]

            lines.append(f"\n[bold]Battle at ({x},{y})! {atk_emoji} ({atk_str}) vs {def_emoji} ({def_str})[/bold]")

            if ratio >= 3.0:
                # Overwhelming — defender destroyed
                for u in defenders:
                    u.hp = 0
                lines.append(f"  [green]Decisive victory for {atk_emoji}![/green]")
            elif ratio >= 2.0:
                # Strong — defender takes heavy losses
                for u in defenders:
                    u.hp -= random.randint(2, 4)
                atk_loss = random.choice(attackers)
                atk_loss.hp -= 1
                lines.append(f"  [green]{atk_emoji} wins with light losses.[/green]")
            elif ratio >= 1.2:
                # Slight advantage — exchange
                for u in defenders:
                    u.hp -= random.randint(1, 3)
                for u in attackers:
                    u.hp -= random.randint(1, 2)
                lines.append(f"  [yellow]Exchange! Both sides take losses.[/yellow]")
            elif ratio >= 0.8:
                # Even — mutual losses
                for u in defenders:
                    u.hp -= random.randint(1, 2)
                for u in attackers:
                    u.hp -= random.randint(1, 3)
                lines.append(f"  [yellow]Stalemate. Mutual losses.[/yellow]")
            else:
                # Defender advantage
                for u in attackers:
                    u.hp -= random.randint(2, 4)
                def_loss = random.choice(defenders)
                def_loss.hp -= 1
                lines.append(f"  [red]{def_emoji} holds! Attackers repulsed.[/red]")

            # Remove dead
            tile.units = [u for u in tile.units if u.alive]

            # If one side eliminated, winner claims tile
            remaining_owners = set(u.owner for u in tile.units)
            if len(remaining_owners) == 1:
                tile.owner = remaining_owners.pop()

    return lines


# ---------------------------------------------------------------------------
# End turn / win check
# ---------------------------------------------------------------------------

def _apply_faction_passive(state: StackWarsState, player: PlayerState) -> list[str]:
    """Apply faction-specific passive abilities at end of turn.

    These make each faction mechanically distinct (asymmetry through
    faction menus, not just stats — per the book).
    """
    lines = []
    emoji = FACTION_EMOJI[player.faction]

    if player.faction == Faction.ENGINEERS:
        # Engineers auto-fortify any tile with units (precision, discipline)
        boosted = 0
        for tile in state.player_tiles(player.index):
            if tile.units and not tile.fortified:
                tile.fortified = True
                boosted += 1
        if boosted:
            lines.append(f"[dim]{emoji} Engineer discipline: {boosted} tile(s) auto-fortified.[/dim]")

    elif player.faction == Faction.ANARCHISTS:
        # Chaos passive: 25% chance to spawn a free Script Kiddie at a random owned tile
        if random.random() < 0.25:
            owned = state.player_tiles(player.index)
            if owned:
                tile = random.choice(owned)
                tile.units.append(Unit(UnitType.SCRIPT_KIDDIE, player.index))
                lines.append(f"[dim]{emoji} Anarchist chaos: a Script Kiddie appeared at ({tile.x},{tile.y})![/dim]")

        # Garrison decay — anarchists lose 1 HP on a random unit each turn (weakness)
        units = state.player_units(player.index)
        if len(units) > 3 and random.random() < 0.3:
            vx, vy, victim = random.choice(units)
            victim.hp -= 1
            if not victim.alive:
                state.grid[vy][vx].units = [u for u in state.grid[vy][vx].units if u.alive]
                lines.append(f"[dim]{emoji} Anarchist entropy: a unit deserted.[/dim]")
            else:
                lines.append(f"[dim]{emoji} Anarchist entropy: a unit grows restless (-1 HP).[/dim]")

    elif player.faction == Faction.PROVOCATEURS:
        # Theft passive: steal 1-2 Code from each adjacent enemy
        for other in state.players:
            if other.index == player.index or other.eliminated:
                continue
            stolen = random.randint(0, 2)
            if stolen > 0 and other.code >= stolen:
                other.code -= stolen
                player.code += stolen
                player.cap_resources()
                lines.append(f"[dim]{emoji} Provocateur sabotage: stole {stolen} Code from {other.buddy_name}.[/dim]")

    elif player.faction == Faction.SAGES:
        # Knowledge passive: +1 favor to a random ability each turn
        abilities = list(AbilityType)
        chosen = random.choice(abilities)
        player.favor[chosen.value] += 1
        fav = player.favor[chosen.value]
        if fav > 0 and fav % 2 == 0:
            player.blessings[chosen.value] += 1
            lines.append(f"[dim]{emoji} Sage insight: {chosen.value.title()} blessed (Lv.{player.blessings[chosen.value]})![/dim]")
        else:
            lines.append(f"[dim]{emoji} Sage meditation: {chosen.value.title()} favor grows.[/dim]")

    elif player.faction == Faction.MONKS:
        # Economy passive: +1 Code per owned tile (capped — monks are rich but slow)
        owned = len(state.player_tiles(player.index))
        gain = min(owned, 5)  # Cap at 5
        player.code += gain
        player.cap_resources()
        if gain:
            lines.append(f"[dim]{emoji} Monk discipline: +{gain} Code from {owned} controlled tile(s).[/dim]")

    return lines


def _end_turn(state: StackWarsState) -> list[str]:
    """End the current player's turn."""
    lines = []
    player = state.active_player

    # Reset unit movement
    for y in range(GRID_H):
        for x in range(GRID_W):
            for u in state.grid[y][x].units:
                if u.owner == player.index:
                    u.moved_this_turn = False

    # Income from buildings
    for tile in state.player_tiles(player.index):
        if tile.building and tile.building.owner == player.index:
            if tile.building.building_type == BuildingType.SEED_FACTORY:
                player.code += 2
            elif tile.building.building_type == BuildingType.MONUMENT:
                # Bonus favor for a random ability
                chosen_ab = random.choice(list(AbilityType))
                player.favor[chosen_ab.value] += 1
                fav = player.favor[chosen_ab.value]
                if fav > 0 and fav % 2 == 0:
                    player.blessings[chosen_ab.value] += 1
                    lines.append(f"[dim]Monument inspires: {chosen_ab.value.title()} blessed (Lv.{player.blessings[chosen_ab.value]})![/dim]")
    player.cap_resources()

    # Faction passive abilities
    faction_lines = _apply_faction_passive(state, player)
    if faction_lines:
        lines.extend(faction_lines)

    # Resolve combat
    combat_lines = resolve_combat(state)
    if combat_lines:
        lines.extend(combat_lines)

    # Check win condition
    flags = state.count_flags(player.index)
    player.flags_held = flags
    if flags >= FLAGS_TO_WIN:
        player.flags_held_turns += 1
        if player.flags_held_turns >= HOLD_TURNS_TO_WIN:
            state.winner = player.index
            lines.append(f"\n[bold green]{FACTION_EMOJI[player.faction]} {player.buddy_name} wins! Held {flags} flags![/bold green]")
            return lines
        else:
            lines.append(f"[yellow]{player.buddy_name} holds {flags} flags! Hold for 1 more round to win![/yellow]")
    else:
        player.flags_held_turns = 0

    # Advance to next player
    state.current_player = (state.current_player + 1) % len(state.players)
    if state.current_player == 0:
        state.turn += 1
        if state.turn > state.max_turns:
            # Game over — most flags wins
            best = max(state.players, key=lambda p: state.count_flags(p.index))
            state.winner = best.index
            lines.append(f"\n[bold]Turn limit reached! {best.buddy_name} wins with {state.count_flags(best.index)} flags![/bold]")
            return lines

    # Tick cooldowns for next player
    state.players[state.current_player].tick_cooldowns()

    # Reset phase
    state.chosen_ability = None
    state.action_step = 0
    state.phase = "choose_ability"

    # AI turn
    next_player = state.active_player
    if next_player.is_ai and not state.game_over:
        lines.extend(ai_turn(state))

    return lines


# ---------------------------------------------------------------------------
# AI opponent
# ---------------------------------------------------------------------------

def _ai_choose_ability(state: StackWarsState, player: PlayerState) -> AbilityType:
    """Choose ability based on faction personality and game state."""
    available = player.available_abilities()
    if not available:
        return list(AbilityType)[0]  # fallback

    flags = state.count_flags(player.index)
    units = state.player_units(player.index)
    turn = state.turn

    # Situational overrides
    if flags >= FLAGS_TO_WIN and AbilityType.BUILD in available:
        return AbilityType.BUILD  # Fortify to hold
    if len(units) <= 1 and AbilityType.DEPLOY in available:
        return AbilityType.DEPLOY  # Need more troops
    if turn <= 3 and AbilityType.RALLY in available:
        return AbilityType.RALLY  # Early economy

    # Faction priority with phase awareness
    early = turn <= 8
    mid = 8 < turn <= 18

    priority: dict[Faction, list[AbilityType]] = {
        Faction.ENGINEERS: (
            [AbilityType.BUILD, AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.INVOKE, AbilityType.RALLY] if early else
            [AbilityType.MARCH, AbilityType.INVOKE, AbilityType.DEPLOY, AbilityType.BUILD, AbilityType.RALLY]
        ),
        Faction.ANARCHISTS: (
            [AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.RALLY, AbilityType.INVOKE, AbilityType.BUILD] if early else
            [AbilityType.MARCH, AbilityType.DEPLOY, AbilityType.INVOKE, AbilityType.RALLY, AbilityType.BUILD]
        ),
        Faction.PROVOCATEURS: (
            [AbilityType.INVOKE, AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.RALLY, AbilityType.BUILD] if early else
            [AbilityType.INVOKE, AbilityType.MARCH, AbilityType.DEPLOY, AbilityType.RALLY, AbilityType.BUILD]
        ),
        Faction.SAGES: (
            [AbilityType.RALLY, AbilityType.BUILD, AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.INVOKE] if early else
            [AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.INVOKE, AbilityType.BUILD, AbilityType.RALLY]
        ),
        Faction.MONKS: (
            [AbilityType.BUILD, AbilityType.RALLY, AbilityType.DEPLOY, AbilityType.MARCH, AbilityType.INVOKE] if early else
            [AbilityType.RALLY, AbilityType.BUILD, AbilityType.MARCH, AbilityType.DEPLOY, AbilityType.INVOKE]
        ),
    }

    for pref in priority.get(player.faction, list(AbilityType)):
        if pref in available:
            return pref
    return available[0]


def _ai_recruit_unit(player: PlayerState, faction: Faction) -> str:
    """AI decides which unit to recruit based on faction and resources."""
    code = player.code

    # Faction-specific recruitment preferences
    if faction == Faction.ANARCHISTS:
        # Swarm — lots of cheap units, occasional Operator for speed
        if code >= 4 and random.random() < 0.3:
            return "operator"
        return "kiddie"
    elif faction == Faction.ENGINEERS:
        # Balanced — Architects for defense, Hackers for ranged
        if code >= 8 and random.random() < 0.2:
            return "sysadmin"
        if code >= 5:
            return random.choice(["architect", "hacker"])
        return "kiddie"
    elif faction == Faction.PROVOCATEURS:
        # Glass cannon — Hackers and Operators
        if code >= 5:
            return random.choice(["hacker", "operator"])
        return "kiddie"
    elif faction == Faction.SAGES:
        # Elite — save for expensive units
        if code >= 8:
            return "sysadmin"
        if code >= 5:
            return "architect"
        return "kiddie"
    elif faction == Faction.MONKS:
        # Defensive — Architects and Sysadmins
        if code >= 8 and random.random() < 0.3:
            return "sysadmin"
        if code >= 5:
            return "architect"
        return "kiddie"

    return "kiddie"


def _ai_build_choice(player: PlayerState, faction: Faction, state: StackWarsState) -> str:
    """AI decides what to build based on faction and current buildings."""
    code = player.code
    existing_buildings: list[BuildingType] = []
    for tile in state.player_tiles(player.index):
        if tile.building and tile.building.owner == player.index:
            existing_buildings.append(tile.building.building_type)

    has_barracks = BuildingType.BARRACKS in existing_buildings
    has_factory = BuildingType.SEED_FACTORY in existing_buildings

    if faction == Faction.MONKS:
        # Economy first
        if not has_factory and code >= 8:
            return "factory"
        if not has_barracks and code >= 6:
            return "barracks"
        if code >= 10:
            return "fortress"
    elif faction == Faction.ENGINEERS:
        # Defense oriented
        if not has_barracks and code >= 6:
            return "barracks"
        if code >= 10:
            return "fortress"
        if not has_factory and code >= 8:
            return "factory"
    elif faction == Faction.SAGES:
        # Monument for favor acceleration
        if code >= 12 and random.random() < 0.4:
            return "monument"
        if not has_factory and code >= 8:
            return "factory"
        if not has_barracks and code >= 6:
            return "barracks"
    else:
        # Anarchists / Provocateurs — barracks for production
        if not has_barracks and code >= 6:
            return "barracks"
        if not has_factory and code >= 8:
            return "factory"

    # Fallback — cheapest available
    if code >= 6:
        return "barracks"
    return ""


def ai_turn(state: StackWarsState) -> list[str]:
    """Execute a full AI turn with faction-specific strategy."""
    player = state.active_player
    lines = []

    emoji = FACTION_EMOJI[player.faction]
    lines.append(f"\n[dim]{emoji} {player.buddy_name}'s turn (Turn {state.turn})...[/dim]")

    available = player.available_abilities()
    if not available:
        lines.append(f"[dim]{emoji} passes.[/dim]")
        lines.extend(_end_turn(state))
        return lines

    chosen = _ai_choose_ability(state, player)
    lines.extend(choose_ability(state, chosen))

    # Execute all 3 actions with faction-appropriate decisions
    for step in range(3):
        if state.game_over:
            break

        if chosen == AbilityType.DEPLOY:
            if step == 1:
                # Recruit
                if player.code >= 3:
                    unit_name = _ai_recruit_unit(player, player.faction)
                    lines.extend(execute_action(state, unit_name))
                else:
                    lines.extend(skip_action(state))
            elif step == 2:
                # Teleport toward front lines
                spawn_units = []
                for x, y, unit in state.player_units(player.index):
                    tile = state.grid[y][x]
                    if tile.terrain == Terrain.HQ or (tile.building and tile.building.building_type == BuildingType.BARRACKS):
                        spawn_units.append((x, y, unit))
                if spawn_units:
                    # Find owned tile closest to a flag
                    owned = [t for t in state.player_tiles(player.index) if t.terrain != Terrain.FIREWALL]
                    flags = [(t.x, t.y) for row in state.grid for t in row if t.is_flag and t.owner != player.index]
                    if flags and owned:
                        best_tile = min(owned, key=lambda t: min(abs(t.x-fx)+abs(t.y-fy) for fx,fy in flags))
                        lines.extend(execute_action(state, f"{best_tile.x},{best_tile.y}"))
                    else:
                        lines.extend(skip_action(state))
                else:
                    lines.extend(execute_action(state, ""))
            else:
                lines.extend(execute_action(state, ""))

        elif chosen == AbilityType.BUILD:
            if step == 0:
                building = _ai_build_choice(player, player.faction, state)
                if building:
                    lines.extend(execute_action(state, building))
                else:
                    lines.extend(skip_action(state))
            else:
                lines.extend(execute_action(state, ""))

        elif chosen == AbilityType.INVOKE:
            if step == 1:
                # Bug Bomb if enough bugs and enemies exist
                if player.bugs >= 3:
                    lines.extend(execute_action(state, ""))
                else:
                    lines.extend(skip_action(state))
            else:
                lines.extend(execute_action(state, ""))

        else:
            lines.extend(execute_action(state, ""))

    return lines


# ---------------------------------------------------------------------------
# Map rendering (ASCII)
# ---------------------------------------------------------------------------

TERRAIN_CHAR: dict[Terrain, str] = {
    Terrain.PLAINS: ".",
    Terrain.MOUNTAIN: "^",
    Terrain.SERVER: "$",
    Terrain.FIREWALL: "#",
    Terrain.HQ: "H",
    Terrain.FLAG: "F",
}


def render_map(state: StackWarsState) -> list[str]:
    """Render the 5x5 map as ASCII with color."""
    lines = ["[bold]   0 1 2 3 4[/bold]"]

    for y in range(GRID_H):
        row = f"[bold]{y}[/bold]  "
        for x in range(GRID_W):
            tile = state.grid[y][x]
            char = TERRAIN_CHAR[tile.terrain]

            # Show unit count if units present
            units_here = len(tile.units)
            if units_here > 0:
                owner = tile.units[0].owner
                color = FACTION_COLOR[state.players[owner].faction]
                char = f"[bold {color}]{units_here}[/bold {color}]"
            elif tile.owner >= 0:
                color = FACTION_COLOR[state.players[tile.owner].faction]
                char = f"[{color}]{char}[/{color}]"
            else:
                char = f"[dim]{char}[/dim]"

            row += char + " "
        lines.append(row)

    return lines


def render_status(state: StackWarsState) -> list[str]:
    """Render player status panel."""
    lines = []
    for p in state.players:
        emoji = FACTION_EMOJI[p.faction]
        color = FACTION_COLOR[p.faction]
        flags = state.count_flags(p.index)
        marker = " [bold yellow]<<<[/bold yellow]" if p.index == state.current_player else ""
        lines.append(
            f"[{color}]{emoji} {p.buddy_name}[/{color}] "
            f"Code:{p.code} Bug:{p.bugs} Coffee:{p.coffee} "
            f"Flags:{flags}/{FLAGS_TO_WIN}{marker}"
        )
    lines.append(f"[dim]Turn {state.turn}/{state.max_turns}[/dim]")
    return lines
