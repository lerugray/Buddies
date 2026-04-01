"""First-person dungeon renderer — ASCII wireframe corridors.

Template-based renderer that composites pre-built line arrays
based on what is visible at each depth (0-3 cells forward).
Also renders minimap and party panel.
"""

from __future__ import annotations

from buddies.core.games.crawl import (
    CellType, Facing, DIRECTION_DELTA, GRID_SIZE,
    CrawlState, PartyMember, EncounterKind,
)


# ---------------------------------------------------------------------------
# First-person view (22 wide × 9 tall)
# ---------------------------------------------------------------------------

VIEW_W = 22
VIEW_H = 9

# Base templates for each depth configuration
# Each template is 9 lines of 22 chars

# Solid wall (nothing visible ahead)
WALL_VIEW = [
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
    "██████████████████████",
]

# Open corridor — depth layers shown with shading
# ██ = outer wall, ▓▓ = mid depth wall, ░░ = near depth wall, spaces = passage

OPEN_3_DEEP = [
    "██████████████████████",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██ ▓▓ ░░░░░░░░ ▓▓ ██",
    "██ ▓▓ ░░      ░░ ▓▓ ██",
    "██ ▓▓ ░░      ░░ ▓▓ ██",
    "██ ▓▓ ░░░░░░░░ ▓▓ ██",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██",
    "██████████████████████",
]

OPEN_2_DEEP = [
    "██████████████████████",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██ ▓▓ ░░░░░░░░ ▓▓ ██",
    "██ ▓▓ ░░░░░░░░ ▓▓ ██",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██",
    "██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██",
    "██████████████████████",
]

OPEN_1_DEEP = [
    "██████████████████████",
    "██                  ██",
    "██  ░░░░░░░░░░░░░░  ██",
    "██  ░░          ░░  ██",
    "██  ░░          ░░  ██",
    "██  ░░░░░░░░░░░░░░  ██",
    "██                  ██",
    "██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██",
    "██████████████████████",
]

# Left opening at depth 1 (passage to the left)
LEFT_OPEN_1 = [
    "██████████████████████",
    "      ▓▓▓▓▓▓▓▓▓▓▓▓██",
    "      ░░░░░░░░░░░░ ██",
    "      ░░          ██",
    "      ░░          ██",
    "      ░░░░░░░░░░░░ ██",
    "      ▓▓▓▓▓▓▓▓▓▓▓▓██",
    "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██",
    "██████████████████████",
]

# Right opening at depth 1
RIGHT_OPEN_1 = [
    "██████████████████████",
    "██▓▓▓▓▓▓▓▓▓▓▓▓      ",
    "██ ░░░░░░░░░░░░      ",
    "██          ░░      ",
    "██          ░░      ",
    "██ ░░░░░░░░░░░░      ",
    "██▓▓▓▓▓▓▓▓▓▓▓▓      ",
    "██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓",
    "██████████████████████",
]


def _is_passable(grid, y, x):
    """Check if a cell is passable (not a wall)."""
    if 0 <= y < GRID_SIZE and 0 <= x < GRID_SIZE:
        return grid[y][x].terrain != CellType.WALL
    return False


def _get_encounter_overlay(grid, y, x) -> str | None:
    """Get an encounter icon for a cell if it has an unresolved encounter."""
    if 0 <= y < GRID_SIZE and 0 <= x < GRID_SIZE:
        cell = grid[y][x]
        if cell.encounter and not cell.encounter.resolved:
            kind = cell.encounter.kind
            if kind in (EncounterKind.MONSTER, EncounterKind.BOSS):
                return cell.encounter.enemy.emoji if cell.encounter.enemy else "👾"
            elif kind == EncounterKind.TRAP:
                return "⚠"
            elif kind == EncounterKind.TREASURE:
                return "✨"
            elif kind == EncounterKind.MYSTERY:
                return "❓"
            elif kind == EncounterKind.REST:
                return "☕"
        if cell.terrain == CellType.STAIRS_DOWN:
            return "▼▼"
        if cell.terrain == CellType.DOOR and not cell.visited:
            return "🚪"
    return None


def render_view(state: CrawlState) -> str:
    """Render the first-person dungeon view as Rich markup text.

    Returns a multi-line string of the 22×9 view.
    """
    grid = state.grid
    py, px = state.player_y, state.player_x
    facing = state.facing

    dy, dx = DIRECTION_DELTA[facing]

    # Check what's ahead at depths 1, 2, 3
    depths = []
    for d in range(1, 4):
        ny, nx = py + dy * d, px + dx * d
        passable = _is_passable(grid, ny, nx)
        depths.append(passable)

    # Check left/right at depth 1
    # Left is 90° counterclockwise, right is 90° clockwise
    left_facing = Facing((facing - 1) % 4)
    right_facing = Facing((facing + 1) % 4)
    ldy, ldx = DIRECTION_DELTA[left_facing]
    rdy, rdx = DIRECTION_DELTA[right_facing]

    # Position at depth 1
    d1y, d1x = py + dy, px + dx
    left_open = _is_passable(grid, d1y + ldy, d1x + ldx) if depths[0] else False
    right_open = _is_passable(grid, d1y + rdy, d1x + rdx) if depths[0] else False

    # Pick base template
    if not depths[0]:
        lines = list(WALL_VIEW)
    elif not depths[1]:
        lines = list(OPEN_1_DEEP)
    elif not depths[2]:
        lines = list(OPEN_2_DEEP)
    else:
        lines = list(OPEN_3_DEEP)

    # Apply left/right openings at depth 1
    if depths[0] and left_open:
        for i in range(min(len(LEFT_OPEN_1), len(lines))):
            # Blend: take left portion from LEFT_OPEN template
            left_part = LEFT_OPEN_1[i][:6]
            lines[i] = left_part + lines[i][6:]

    if depths[0] and right_open:
        for i in range(min(len(RIGHT_OPEN_1), len(lines))):
            right_part = RIGHT_OPEN_1[i][-6:]
            lines[i] = lines[i][:-6] + right_part

    # Add encounter overlay at depth 1
    if depths[0]:
        d1y, d1x = py + dy, px + dx
        icon = _get_encounter_overlay(grid, d1y, d1x)
        if icon:
            # Place icon in center of the view (line 4, centered)
            center_line = 4
            if center_line < len(lines):
                line = lines[center_line]
                mid = len(line) // 2 - 1
                # Replace center with icon
                lines[center_line] = line[:mid] + icon + line[mid + len(icon):]

    # Color the view with Rich markup
    colored_lines = []
    for line in lines:
        colored = line
        colored = colored.replace("██", "[#444444]██[/#444444]")
        colored = colored.replace("▓▓", "[#666666]▓▓[/#666666]")
        colored = colored.replace("░░", "[#888888]░░[/#888888]")
        colored_lines.append(colored)

    return "\n".join(colored_lines)


# ---------------------------------------------------------------------------
# Minimap renderer
# ---------------------------------------------------------------------------

MINIMAP_W = 11
MINIMAP_H = 7


def render_minimap(state: CrawlState) -> str:
    """Render a small minimap centered on the player.

    # = wall, . = floor, @ = player, ? = unrevealed
    D = door, > = stairs down, < = stairs up
    ! = monster, * = treasure, ^ = trap
    """
    grid = state.grid
    py, px = state.player_y, state.player_x

    half_w = MINIMAP_W // 2
    half_h = MINIMAP_H // 2

    lines = []
    for vy in range(-half_h, half_h + 1):
        row = ""
        for vx in range(-half_w, half_w + 1):
            gy, gx = py + vy, px + vx
            if vy == 0 and vx == 0:
                # Player with facing arrow
                arrows = {Facing.NORTH: "▲", Facing.EAST: "►", Facing.SOUTH: "▼", Facing.WEST: "◄"}
                row += f"[bold white]{arrows[state.facing]}[/bold white]"
                continue

            if not (0 <= gy < GRID_SIZE and 0 <= gx < GRID_SIZE):
                row += " "
                continue

            cell = grid[gy][gx]
            if not cell.revealed:
                row += "[dim]·[/dim]"
            elif cell.terrain == CellType.WALL:
                row += "[#666666]#[/#666666]"
            elif cell.encounter and not cell.encounter.resolved:
                kind = cell.encounter.kind
                if kind in (EncounterKind.MONSTER, EncounterKind.BOSS):
                    row += "[red]![/red]"
                elif kind == EncounterKind.TRAP:
                    row += "[yellow]^[/yellow]"
                elif kind == EncounterKind.TREASURE:
                    row += "[#FFD700]*[/#FFD700]"
                elif kind == EncounterKind.MYSTERY:
                    row += "[magenta]?[/magenta]"
                elif kind == EncounterKind.REST:
                    row += "[green]+[/green]"
                else:
                    row += "."
            elif cell.terrain == CellType.STAIRS_DOWN:
                row += "[cyan]>[/cyan]"
            elif cell.terrain == CellType.STAIRS_UP:
                row += "[cyan]<[/cyan]"
            elif cell.terrain == CellType.DOOR:
                row += "[yellow]D[/yellow]"
            else:
                row += "[dim].[/dim]"

        lines.append(row)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Party panel renderer
# ---------------------------------------------------------------------------

def render_party(state: CrawlState) -> str:
    """Render the party roster panel."""
    lines = []
    for m in state.party:
        if not m.is_alive:
            lines.append(f"[dim]{m.emoji} {m.name[:8]:8} {m.buddy_class.value} 💀[/dim]")
        else:
            hp_bar = m.hp_bar(8)
            lines.append(f"{m.emoji} {m.name[:8]:8} {m.buddy_class.value} {hp_bar} {m.hp}/{m.max_hp}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Combat action prompt
# ---------------------------------------------------------------------------

def render_combat_actions(state: CrawlState) -> str:
    """Render the combat action choices for the current party member."""
    if not state.in_combat or state.current_member_idx >= len(state.party):
        return ""

    m = state.party[state.current_member_idx]
    if not m.is_alive:
        return ""

    from buddies.core.games.crawl import BuddyClass, CLASS_NAMES

    skill_names = {
        BuddyClass.ENGINEER: "Analyze",
        BuddyClass.BERSERKER: "Berserk",
        BuddyClass.ROGUE: "Backstab",
        BuddyClass.MAGE: "AoE Refactor",
        BuddyClass.PALADIN: "Heal",
    }
    skill = skill_names.get(m.buddy_class, "Skill")
    potions = f"({state.potions})" if state.potions > 0 else "(none)"

    return (
        f"[bold]1[/bold]=Attack  [bold]2[/bold]={skill}  "
        f"[bold]3[/bold]=Defend  [bold]4[/bold]=Potion {potions}"
    )
