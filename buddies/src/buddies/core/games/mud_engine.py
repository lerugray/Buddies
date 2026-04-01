"""MUD Game Engine — command parsing, combat, and game loop.

Handles player commands (look, go, talk, take, attack, etc.),
NPC combat using the battle system, shopping, quests, and
buddy commentary on everything that happens.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state
from buddies.core.games.mud_world import (
    Room, NPC, Item, Quest, QuestStatus, QuestType, QuestObjective,
    NPCDisposition, ItemType, RoomExit, MudInventory,
    build_starter_items, build_starter_npcs, build_starter_rooms, build_starter_quests,
)


# ---------------------------------------------------------------------------
# Combat state (simplified from battle.py for MUD context)
# ---------------------------------------------------------------------------

@dataclass
class MudCombatant:
    """A participant in MUD combat."""
    name: str
    emoji: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    is_player: bool = False

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def hp_bar(self, width: int = 15) -> str:
        filled = int((self.hp / self.max_hp) * width) if self.max_hp > 0 else 0
        empty = width - filled
        color = "green" if self.hp > self.max_hp * 0.5 else "yellow" if self.hp > self.max_hp * 0.25 else "red"
        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}] {self.hp}/{self.max_hp}"


@dataclass
class CombatState:
    """Active combat encounter."""
    player: MudCombatant
    enemy: MudCombatant
    npc_id: str
    turn: int = 0
    log: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.player.alive and self.enemy.alive


# ---------------------------------------------------------------------------
# Main MUD state
# ---------------------------------------------------------------------------

@dataclass
class MudState:
    """Complete MUD game state."""
    rooms: dict[str, Room]
    npcs: dict[str, NPC]
    items: dict[str, Item]
    quests: dict[str, Quest]
    inventory: MudInventory
    current_room: str = "lobby"
    party: list[BuddyState] = field(default_factory=list)
    combat: CombatState | None = None
    # Stats
    rooms_visited: int = 0
    npcs_talked: int = 0
    npcs_defeated: int = 0
    items_collected: int = 0
    quests_completed: int = 0
    gold_earned: int = 0
    turns: int = 0
    # Flags
    game_over: bool = False


def create_mud_game(party: list[BuddyState]) -> MudState:
    """Create a new MUD game with the starter world."""
    items = build_starter_items()
    npcs = build_starter_npcs(items)
    rooms = build_starter_rooms()
    quests = build_starter_quests()

    return MudState(
        rooms=rooms,
        npcs=npcs,
        items=items,
        quests=quests,
        inventory=MudInventory(gold=10),
        party=party,
    )


# ---------------------------------------------------------------------------
# Command parsing
# ---------------------------------------------------------------------------

DIRECTION_ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "up": "up", "down": "down",
}


def parse_command(raw: str) -> tuple[str, str]:
    """Parse raw input into (command, argument)."""
    raw = raw.strip().lower()
    if not raw:
        return "", ""

    # Direction shortcuts
    if raw in DIRECTION_ALIASES:
        return "go", DIRECTION_ALIASES[raw]

    parts = raw.split(None, 1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    # Aliases
    aliases = {
        "l": "look", "look": "look",
        "go": "go", "move": "go", "walk": "go",
        "examine": "examine", "x": "examine", "inspect": "examine",
        "talk": "talk", "t": "talk", "speak": "talk", "chat": "talk",
        "take": "take", "get": "take", "grab": "take", "pick": "take",
        "drop": "drop",
        "use": "use", "drink": "use", "eat": "use",
        "attack": "attack", "fight": "attack", "kill": "attack", "hit": "attack",
        "inventory": "inventory", "inv": "inventory", "i": "inventory",
        "buy": "buy", "shop": "buy", "purchase": "buy",
        "quest": "quest", "quests": "quest", "q": "quest",
        "help": "help", "h": "help", "?": "help",
        "map": "map",
        "flee": "flee", "run": "flee", "escape": "flee",
        "wait": "wait",
    }

    cmd = aliases.get(cmd, cmd)

    # "go north" → go + north
    if cmd == "go" and arg in DIRECTION_ALIASES:
        arg = DIRECTION_ALIASES[arg]

    return cmd, arg


# ---------------------------------------------------------------------------
# Buddy commentary system
# ---------------------------------------------------------------------------

BUDDY_COMMENTARY: dict[str, dict[str, list[str]]] = {
    "enter_room": {
        "clinical": [
            "{name}: \"Mapping this location. Structural integrity: questionable.\"",
            "{name}: \"New room detected. Scanning for threats.\"",
        ],
        "sarcastic": [
            "{name}: \"Oh great. Another room. How thrilling.\"",
            "{name}: \"Wow, look at this place. It's almost as messy as your code.\"",
        ],
        "absurdist": [
            "{name}: \"I'm pretty sure this room didn't exist until we looked at it.\"",
            "{name}: \"The walls are made of... code? No. Worse. Meetings.\"",
        ],
        "philosophical": [
            "{name}: \"Every room is a metaphor. This one represents... something.\"",
            "{name}: \"We shape the dungeon, and the dungeon shapes us.\"",
        ],
        "calm": [
            "{name}: \"A new place. Let's take our time and look around.\"",
            "{name}: \"I have a good feeling about this room.\"",
        ],
    },
    "combat_start": {
        "clinical": [
            "{name}: \"Threat detected. Engaging combat protocols.\"",
            "{name}: \"Hostile entity. Calculating optimal approach.\"",
        ],
        "sarcastic": [
            "{name}: \"Oh look, something wants to kill us. What a surprise.\"",
            "{name}: \"Another day, another fight. Yawn.\"",
        ],
        "absurdist": [
            "{name}: \"Quick, distract it with a code review!\"",
            "{name}: \"I'm not saying we should run but MY LEGS SAY RUN.\"",
        ],
        "philosophical": [
            "{name}: \"In conflict, we find our true selves.\"",
            "{name}: \"This battle was inevitable. As all battles are.\"",
        ],
        "calm": [
            "{name}: \"Stay focused. We can handle this together.\"",
            "{name}: \"Deep breaths. We've got this.\"",
        ],
    },
    "combat_win": {
        "clinical": ["{name}: \"Target eliminated. Threat assessment complete.\""],
        "sarcastic": ["{name}: \"Well THAT was anticlimactic.\""],
        "absurdist": ["{name}: \"Did... did we just debug it to death?\""],
        "philosophical": ["{name}: \"Victory. But at what cost? (Probably some HP.)\""],
        "calm": ["{name}: \"Well done. Let's rest a moment.\""],
    },
    "combat_lose": {
        "clinical": ["{name}: \"Mission failure. Recommending retreat.\""],
        "sarcastic": ["{name}: \"That went exactly as badly as I expected.\""],
        "absurdist": ["{name}: \"We didn't lose, we just... unalived. Temporarily.\""],
        "philosophical": ["{name}: \"Even in defeat, there are lessons.\""],
        "calm": ["{name}: \"It's okay. We'll try again when we're ready.\""],
    },
    "find_item": {
        "clinical": ["{name}: \"Item acquired. Adding to inventory.\""],
        "sarcastic": ["{name}: \"Oh nice, free stuff. My favorite kind.\""],
        "absurdist": ["{name}: \"It was just... sitting there? In this economy?\""],
        "philosophical": ["{name}: \"We don't find items. Items find us.\""],
        "calm": ["{name}: \"A useful find. This could come in handy.\""],
    },
    "shop": {
        "clinical": ["{name}: \"Reviewing available inventory. Optimizing purchase strategy.\""],
        "sarcastic": ["{name}: \"Sure, let's spend our hard-earned gold on... stuff.\""],
        "absurdist": ["{name}: \"Money is fake anyway. Especially this money.\""],
        "philosophical": ["{name}: \"Commerce: the eternal dance of want and have.\""],
        "calm": ["{name}: \"Take your time. No rush.\""],
    },
    "quest_start": {
        "clinical": ["{name}: \"New objective logged. Tracking progress.\""],
        "sarcastic": ["{name}: \"Oh good, more work. Just what I wanted.\""],
        "absurdist": ["{name}: \"A quest! Like in the video games! Wait...\""],
        "philosophical": ["{name}: \"Every quest is a journey of self-discovery.\""],
        "calm": ["{name}: \"A worthy goal. Let's do our best.\""],
    },
    "quest_complete": {
        "clinical": ["{name}: \"Quest objective achieved. Filing completion report.\""],
        "sarcastic": ["{name}: \"We did it! Can we go home now?\""],
        "absurdist": ["{name}: \"Achievement unlocked: Did A Thing!\""],
        "philosophical": ["{name}: \"The real treasure was the bugs we fixed along the way.\""],
        "calm": ["{name}: \"Well done. I'm proud of us.\""],
    },
}

REGISTERS = {
    "debugging": "clinical",
    "snark": "sarcastic",
    "chaos": "absurdist",
    "wisdom": "philosophical",
    "patience": "calm",
}


def _buddy_comment(party: list[BuddyState], context: str) -> str | None:
    """Get a random buddy comment for the current situation."""
    if not party:
        return None
    buddy = random.choice(party)
    dominant = max(buddy.stats, key=buddy.stats.get)
    register = REGISTERS.get(dominant, "calm")
    pool = BUDDY_COMMENTARY.get(context, {}).get(register, [])
    if not pool:
        return None
    return random.choice(pool).format(name=buddy.name, emoji=buddy.species.emoji)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _handle_look(state: MudState, arg: str) -> list[str]:
    """Look at the current room or a specific thing."""
    room = state.rooms[state.current_room]
    lines = []

    if arg:
        # Look at a specific NPC or item
        return _handle_examine(state, arg)

    # Room header
    lines.append(f"\n[bold]{room.emoji} {room.name}[/bold]")
    lines.append(f"{'─' * 50}")

    # Description
    if room.visited and room.short_description:
        lines.append(room.short_description)
    else:
        lines.append(room.description)

    # NPCs
    alive_npcs = [state.npcs[nid] for nid in room.npcs if nid in state.npcs and not state.npcs[nid].defeated]
    if alive_npcs:
        lines.append("")
        lines.append("[bold]You see:[/bold]")
        for npc in alive_npcs:
            disp_color = {
                NPCDisposition.FRIENDLY: "green",
                NPCDisposition.NEUTRAL: "white",
                NPCDisposition.HOSTILE: "red",
                NPCDisposition.MERCHANT: "yellow",
                NPCDisposition.QUEST_GIVER: "cyan",
            }.get(npc.disposition, "white")
            lines.append(f"  {npc.emoji} [{disp_color}]{npc.name}[/{disp_color}] — {npc.title}")

    # Items on the ground
    ground_items = [state.items[iid] for iid in room.items if iid in state.items]
    if ground_items:
        lines.append("")
        lines.append("[bold]On the ground:[/bold]")
        for item in ground_items:
            lines.append(f"  {item.emoji} {item.name}")

    # Exits
    lines.append("")
    exits_text = []
    for ex in room.exits:
        if ex.hidden:
            continue
        if ex.locked:
            exits_text.append(f"[dim]{ex.direction} (🔒 locked)[/dim]")
        else:
            exits_text.append(f"[bold cyan]{ex.direction}[/bold cyan]")
    lines.append(f"[bold]Exits:[/bold] {', '.join(exits_text) if exits_text else '[dim]none[/dim]'}")

    # Ambient
    if room.ambient and random.random() < 0.6:
        lines.append(f"\n[dim italic]{random.choice(room.ambient)}[/dim italic]")

    return lines


def _handle_go(state: MudState, direction: str) -> list[str]:
    """Move to another room."""
    if not direction:
        return ["Go where? Try: [bold]go north[/bold], [bold]go south[/bold], etc."]

    room = state.rooms[state.current_room]
    direction = DIRECTION_ALIASES.get(direction, direction)

    # Find the exit
    exit_match = None
    for ex in room.exits:
        if ex.direction == direction:
            exit_match = ex
            break

    if not exit_match:
        return [f"There's no exit to the {direction}."]

    if exit_match.locked:
        # Check for key
        if exit_match.key_item and state.inventory.has_item(exit_match.key_item):
            key = state.items.get(exit_match.key_item)
            key_name = key.name if key else exit_match.key_item
            exit_match.locked = False
            lines = [f"You use the {key_name} to unlock the way {direction}."]
        else:
            key = state.items.get(exit_match.key_item)
            key_hint = f" You need: {key.name}" if key else ""
            return [f"The way {direction} is locked.{key_hint}"]

    # Move
    old_room = state.current_room
    state.current_room = exit_match.destination
    new_room = state.rooms[state.current_room]

    lines = []
    if exit_match.description:
        lines.append(f"[dim]{exit_match.description}[/dim]")

    if not new_room.visited:
        new_room.visited = True
        state.rooms_visited += 1

    lines.extend(_handle_look(state, ""))

    # Buddy commentary
    comment = _buddy_comment(state.party, "enter_room")
    if comment and random.random() < 0.4:
        lines.append(f"\n{comment}")

    state.turns += 1
    return lines


def _handle_examine(state: MudState, target: str) -> list[str]:
    """Examine an NPC, item, or room feature."""
    if not target:
        return ["Examine what?"]

    target_lower = target.lower()
    room = state.rooms[state.current_room]

    # Check NPCs in room
    for nid in room.npcs:
        npc = state.npcs.get(nid)
        if npc and not npc.defeated and target_lower in npc.name.lower():
            lines = [
                f"\n[bold]{npc.emoji} {npc.name} — {npc.title}[/bold]",
                npc.description,
            ]
            if npc.disposition == NPCDisposition.HOSTILE:
                lines.append(f"\n[red]HP: {npc.hp_bar()}[/red]" if hasattr(npc, 'hp') and npc.hp > 0 else "")
                lines.append("[dim]This one looks hostile. You could [bold]attack[/bold] or [bold]flee[/bold].[/dim]")
            elif npc.disposition == NPCDisposition.MERCHANT:
                lines.append("[dim]Type [bold]buy[/bold] to see their wares.[/dim]")
            else:
                lines.append("[dim]Type [bold]talk[/bold] to speak with them.[/dim]")
            return lines

    # Check items on ground
    for iid in room.items:
        item = state.items.get(iid)
        if item and target_lower in item.name.lower():
            return [
                f"\n{item.emoji} [bold]{item.name}[/bold]",
                item.description,
                f"[dim]Type: {item.item_type.value} | Value: {item.value}g[/dim]",
            ]

    # Check inventory items
    for item in state.inventory.items:
        if target_lower in item.name.lower():
            lines = [
                f"\n{item.emoji} [bold]{item.name}[/bold]",
                item.description,
                f"[dim]Type: {item.item_type.value} | Value: {item.value}g[/dim]",
            ]
            if item.attack_bonus:
                lines.append(f"[dim]Attack bonus: +{item.attack_bonus}[/dim]")
            if item.defense_bonus:
                lines.append(f"[dim]Defense bonus: +{item.defense_bonus}[/dim]")
            if item.heal_amount:
                lines.append(f"[dim]Heals: {item.heal_amount} HP[/dim]")
            return lines

    return [f"You don't see '{target}' here."]


def _handle_talk(state: MudState, target: str) -> list[str]:
    """Talk to an NPC."""
    room = state.rooms[state.current_room]

    # Find NPC — if no target, talk to first non-hostile NPC
    npc = None
    if target:
        for nid in room.npcs:
            n = state.npcs.get(nid)
            if n and not n.defeated and target.lower() in n.name.lower():
                npc = n
                break
    else:
        for nid in room.npcs:
            n = state.npcs.get(nid)
            if n and not n.defeated and n.disposition != NPCDisposition.HOSTILE:
                npc = n
                break

    if not npc:
        if target:
            return [f"There's nobody named '{target}' here to talk to."]
        return ["There's nobody here to talk to."]

    if npc.disposition == NPCDisposition.HOSTILE:
        return [f"{npc.emoji} {npc.name} doesn't seem interested in conversation. Try [bold]attack[/bold] instead."]

    # Determine which dialogue to use based on quest state
    lines = []
    lines.append(f"\n{npc.emoji} [bold]{npc.name}[/bold]:")

    dialogue = None

    # Check quest-related dialogue first
    for key, dl in npc.dialogue.items():
        if dl.condition:
            if dl.condition.startswith("quest:"):
                parts = dl.condition.split(":")
                if len(parts) >= 3:
                    quest_id, req_status = parts[1], parts[2]
                    quest = state.quests.get(quest_id)
                    if quest:
                        if req_status == "active" and quest.status == QuestStatus.ACTIVE:
                            dialogue = dl
                            break
                        elif req_status == "complete_ready" and quest.status == QuestStatus.ACTIVE and quest.all_complete:
                            dialogue = dl
                            break
            elif dl.condition.startswith("has_item:"):
                item_id = dl.condition.split(":", 1)[1]
                if state.inventory.has_item(item_id):
                    dialogue = dl
                    break

    # Fall back to greeting or post_quest
    if not dialogue:
        if npc.talked_to and "idle" in npc.dialogue:
            dialogue = npc.dialogue["idle"]
        elif npc.talked_to and "post_quest" in npc.dialogue:
            dialogue = npc.dialogue["post_quest"]
        elif "greeting" in npc.dialogue:
            dialogue = npc.dialogue["greeting"]

    if not dialogue:
        lines.append("\"...\"  (They don't seem to have anything to say.)")
        return lines

    lines.append(dialogue.text)
    npc.talked_to = True
    state.npcs_talked += 1

    # Handle dialogue effects
    if dialogue.starts_quest:
        quest = state.quests.get(dialogue.starts_quest)
        if quest and quest.status == QuestStatus.UNKNOWN:
            quest.status = QuestStatus.ACTIVE
            lines.append(f"\n[bold cyan]📋 New Quest: {quest.name}[/bold cyan]")
            lines.append(f"[dim]{quest.description}[/dim]")
            comment = _buddy_comment(state.party, "quest_start")
            if comment:
                lines.append(f"\n{comment}")

    if dialogue.gives_item:
        item = state.items.get(dialogue.gives_item)
        if item and not state.inventory.has_item(item.id):
            state.inventory.add_item(item)
            state.items_collected += 1
            lines.append(f"\n[green]Received: {item.emoji} {item.name}[/green]")
            comment = _buddy_comment(state.party, "find_item")
            if comment:
                lines.append(f"\n{comment}")
            # Check if this completes a quest objective
            _check_quest_progress(state, "fetch", item.id)

    if dialogue.completes_quest:
        quest = state.quests.get(dialogue.completes_quest)
        if quest and quest.status == QuestStatus.ACTIVE:
            quest.status = QuestStatus.COMPLETED
            state.quests_completed += 1
            lines.append(f"\n[bold green]✅ Quest Complete: {quest.name}[/bold green]")
            if quest.gold_reward:
                state.inventory.gold += quest.gold_reward
                state.gold_earned += quest.gold_reward
                lines.append(f"[yellow]+{quest.gold_reward} gold[/yellow]")
            if quest.xp_reward:
                lines.append(f"[cyan]+{quest.xp_reward} XP[/cyan]")
            comment = _buddy_comment(state.party, "quest_complete")
            if comment:
                lines.append(f"\n{comment}")

    return lines


def _handle_take(state: MudState, target: str) -> list[str]:
    """Pick up an item from the ground."""
    if not target:
        return ["Take what?"]

    room = state.rooms[state.current_room]
    target_lower = target.lower()

    for i, iid in enumerate(room.items):
        item = state.items.get(iid)
        if item and target_lower in item.name.lower():
            if state.inventory.add_item(item):
                room.items.pop(i)
                state.items_collected += 1
                lines = [f"[green]Picked up: {item.emoji} {item.name}[/green]"]
                comment = _buddy_comment(state.party, "find_item")
                if comment:
                    lines.append(comment)
                # Check quest progress
                _check_quest_progress(state, "fetch", item.id)
                return lines
            else:
                return ["Your inventory is full! Drop something first."]

    return [f"There's no '{target}' here to pick up."]


def _handle_drop(state: MudState, target: str) -> list[str]:
    """Drop an item from inventory."""
    if not target:
        return ["Drop what?"]

    target_lower = target.lower()
    for item in state.inventory.items:
        if target_lower in item.name.lower():
            state.inventory.remove_item(item.id)
            room = state.rooms[state.current_room]
            room.items.append(item.id)
            return [f"Dropped: {item.emoji} {item.name}"]

    return [f"You don't have '{target}' in your inventory."]


def _handle_use(state: MudState, target: str) -> list[str]:
    """Use a consumable item."""
    if not target:
        return ["Use what?"]

    target_lower = target.lower()
    for item in state.inventory.items:
        if target_lower in item.name.lower():
            if item.item_type == ItemType.CONSUMABLE and item.heal_amount > 0:
                state.inventory.remove_item(item.id)
                # Heal party
                heal_text = f"Used {item.emoji} {item.name}. "
                if state.combat and state.combat.player.alive:
                    old_hp = state.combat.player.hp
                    state.combat.player.hp = min(state.combat.player.max_hp, state.combat.player.hp + item.heal_amount)
                    healed = state.combat.player.hp - old_hp
                    heal_text += f"Restored {healed} HP!"
                else:
                    heal_text += f"(Would restore {item.heal_amount} HP in combat.)"
                return [f"[green]{heal_text}[/green]"]
            elif item.item_type == ItemType.KEY:
                return [f"The {item.name} is a key item. It will be used automatically."]
            else:
                return [f"You can't use {item.name} right now."]

    return [f"You don't have '{target}'."]


def _handle_inventory(state: MudState, _arg: str) -> list[str]:
    """Show player inventory."""
    lines = ["\n[bold]📦 Inventory[/bold]", f"{'─' * 40}"]
    lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")

    if not state.inventory.items:
        lines.append("[dim]Empty — go find some loot![/dim]")
        return lines

    # Group by type
    by_type: dict[str, list[Item]] = {}
    for item in state.inventory.items:
        key = item.item_type.value.title()
        by_type.setdefault(key, []).append(item)

    for type_name, items in sorted(by_type.items()):
        lines.append(f"\n[bold]{type_name}:[/bold]")
        for item in items:
            extras = []
            if item.attack_bonus:
                extras.append(f"+{item.attack_bonus} ATK")
            if item.defense_bonus:
                extras.append(f"+{item.defense_bonus} DEF")
            if item.heal_amount:
                extras.append(f"+{item.heal_amount} HP")
            extra_str = f" [dim]({', '.join(extras)})[/dim]" if extras else ""
            lines.append(f"  {item.emoji} {item.name}{extra_str}")

    lines.append(f"\n[dim]{len(state.inventory.items)}/{state.inventory.max_items} slots used[/dim]")
    return lines


def _handle_buy(state: MudState, target: str) -> list[str]:
    """Buy from a merchant NPC."""
    room = state.rooms[state.current_room]

    # Find merchant
    merchant = None
    for nid in room.npcs:
        npc = state.npcs.get(nid)
        if npc and not npc.defeated and npc.disposition == NPCDisposition.MERCHANT:
            merchant = npc
            break

    if not merchant:
        return ["There's no shop here."]

    if not target:
        # Show shop
        lines = [f"\n[bold]{merchant.emoji} {merchant.name}'s Shop[/bold]", f"{'─' * 40}"]
        lines.append(f"[yellow]Your gold: {state.inventory.gold}g[/yellow]\n")

        for i, iid in enumerate(merchant.shop_items, 1):
            item = state.items.get(iid)
            if item:
                extras = []
                if item.attack_bonus:
                    extras.append(f"+{item.attack_bonus} ATK")
                if item.defense_bonus:
                    extras.append(f"+{item.defense_bonus} DEF")
                if item.heal_amount:
                    extras.append(f"+{item.heal_amount} HP")
                extra_str = f" ({', '.join(extras)})" if extras else ""
                lines.append(f"  [bold cyan]{i}[/bold cyan]. {item.emoji} {item.name} — [yellow]{item.value}g[/yellow]{extra_str}")

        lines.append(f"\n[dim]Type [bold]buy <item name>[/bold] to purchase.[/dim]")
        comment = _buddy_comment(state.party, "shop")
        if comment:
            lines.append(f"\n{comment}")
        return lines

    # Buy specific item
    target_lower = target.lower()
    for iid in merchant.shop_items:
        item = state.items.get(iid)
        if item and target_lower in item.name.lower():
            if state.inventory.gold < item.value:
                return [f"You can't afford {item.name}. Need {item.value}g, have {state.inventory.gold}g."]
            # Create a copy of the item for the player
            bought = Item(
                id=item.id + f"_{random.randint(100,999)}",
                name=item.name, description=item.description,
                item_type=item.item_type, value=item.value,
                attack_bonus=item.attack_bonus, defense_bonus=item.defense_bonus,
                heal_amount=item.heal_amount, emoji=item.emoji,
            )
            if state.inventory.add_item(bought):
                state.inventory.gold -= item.value
                return [f"[green]Bought: {item.emoji} {item.name} for {item.value}g[/green]",
                        f"[yellow]Gold remaining: {state.inventory.gold}g[/yellow]"]
            else:
                return ["Your inventory is full!"]

    return [f"The shop doesn't have '{target}'."]


def _handle_quest(state: MudState, _arg: str) -> list[str]:
    """Show active and completed quests."""
    lines = ["\n[bold]📋 Quest Log[/bold]", f"{'─' * 40}"]

    active = [q for q in state.quests.values() if q.status == QuestStatus.ACTIVE]
    completed = [q for q in state.quests.values() if q.status == QuestStatus.COMPLETED]

    if not active and not completed:
        lines.append("[dim]No quests yet. Talk to NPCs to find quests![/dim]")
        return lines

    if active:
        lines.append("\n[bold yellow]Active:[/bold yellow]")
        for q in active:
            lines.append(f"  [bold]{q.name}[/bold]")
            obj = q.current_objective
            if obj:
                status = "✅" if obj.complete else "⬜"
                lines.append(f"    {status} {obj.description}")

    if completed:
        lines.append("\n[bold green]Completed:[/bold green]")
        for q in completed:
            lines.append(f"  ✅ {q.name}")

    return lines


def _handle_map(state: MudState, _arg: str) -> list[str]:
    """Show a simple world map."""
    lines = ["\n[bold]🗺️ Map of StackHaven[/bold]", f"{'─' * 50}"]

    # Simple text map
    zone_emoji = {"town": "🏢", "depths": "📚", "server_room": "🖥️", "cloud": "☁️"}

    for zone_name in ["town", "depths", "server_room", "cloud"]:
        zone_rooms = [r for r in state.rooms.values() if r.zone == zone_name]
        if not zone_rooms:
            continue
        lines.append(f"\n[bold]{zone_emoji.get(zone_name, '📍')} {zone_name.replace('_', ' ').title()}:[/bold]")
        for r in zone_rooms:
            marker = "[bold green]► [/bold green]" if r.id == state.current_room else "  "
            visited = "✓" if r.visited else "?"
            lines.append(f"  {marker}{r.emoji} {r.name} [{visited}]")

    lines.append(f"\n[dim]Rooms explored: {state.rooms_visited}/{len(state.rooms)}[/dim]")
    return lines


def _handle_wait(state: MudState, _arg: str) -> list[str]:
    """Wait a turn — just get ambient text."""
    room = state.rooms[state.current_room]
    state.turns += 1
    if room.ambient:
        return [f"[dim italic]{random.choice(room.ambient)}[/dim italic]"]
    return ["You wait. Nothing happens. This is fine."]


def _handle_help(state: MudState, _arg: str) -> list[str]:
    """Show available commands."""
    return [
        "\n[bold]📖 MUD Commands[/bold]",
        f"{'─' * 50}",
        "",
        "[bold cyan]Movement:[/bold cyan]",
        "  [bold]go[/bold] <direction>  — Move (north/south/east/west/up/down)",
        "  [bold]n/s/e/w/u/d[/bold]    — Direction shortcuts",
        "",
        "[bold cyan]Interaction:[/bold cyan]",
        "  [bold]look[/bold] (l)        — Look around the room",
        "  [bold]examine[/bold] (x)     — Examine an NPC or item",
        "  [bold]talk[/bold] (t)        — Talk to an NPC",
        "  [bold]take[/bold]            — Pick up an item",
        "  [bold]drop[/bold]            — Drop an item",
        "  [bold]use[/bold]             — Use a consumable",
        "",
        "[bold cyan]Combat:[/bold cyan]",
        "  [bold]attack[/bold]          — Fight a hostile NPC",
        "  [bold]flee[/bold]            — Run from combat",
        "",
        "[bold cyan]Commerce:[/bold cyan]",
        "  [bold]buy[/bold]             — Browse/buy from merchants",
        "",
        "[bold cyan]Status:[/bold cyan]",
        "  [bold]inventory[/bold] (i)   — Check your items",
        "  [bold]quest[/bold] (q)       — View quest log",
        "  [bold]map[/bold]             — Show world map",
        "",
        "[dim]Press Esc to exit the MUD[/dim]",
    ]


# ---------------------------------------------------------------------------
# Combat system
# ---------------------------------------------------------------------------

def _start_combat(state: MudState, npc_id: str) -> list[str]:
    """Initiate combat with a hostile NPC."""
    npc = state.npcs.get(npc_id)
    if not npc:
        return ["That NPC doesn't exist."]

    # Calculate player stats from party
    total_attack = 5
    total_defense = 2
    total_hp = 30

    for buddy in state.party:
        stats = buddy.stats
        total_attack += stats.get("debugging", 10) // 5 + stats.get("chaos", 10) // 6
        total_defense += stats.get("patience", 10) // 6
        total_hp += stats.get("patience", 10) // 3

    # Equipment bonuses
    weapon = state.inventory.weapon
    armor = state.inventory.armor
    if weapon:
        total_attack += weapon.attack_bonus
    if armor:
        total_defense += armor.defense_bonus

    player = MudCombatant(
        name="Party", emoji="⚔️",
        hp=total_hp, max_hp=total_hp,
        attack=total_attack, defense=total_defense,
        is_player=True,
    )

    enemy = MudCombatant(
        name=npc.name, emoji=npc.emoji,
        hp=npc.hp, max_hp=npc.max_hp,
        attack=npc.attack, defense=npc.defense,
    )

    state.combat = CombatState(player=player, enemy=enemy, npc_id=npc_id)

    lines = [
        f"\n[bold red]⚔️ COMBAT: {npc.emoji} {npc.name} — {npc.title}[/bold red]",
        f"{'─' * 50}",
    ]

    # Enemy dialogue
    combat_dl = npc.dialogue.get("combat")
    if combat_dl:
        lines.append(f"{npc.emoji} {combat_dl.text}")

    # Status
    lines.append(f"\n  You:  {player.hp_bar()}")
    lines.append(f"  {npc.emoji}: {enemy.hp_bar()}")
    lines.append(f"\n[dim]Commands: [bold]attack[/bold] — strike | [bold]use[/bold] <item> — heal | [bold]flee[/bold] — run away[/dim]")

    comment = _buddy_comment(state.party, "combat_start")
    if comment:
        lines.append(f"\n{comment}")

    return lines


def _handle_attack(state: MudState, target: str) -> list[str]:
    """Attack in combat or initiate combat with a hostile NPC."""
    # If already in combat
    if state.combat and state.combat.active:
        return _combat_round(state)

    # Find hostile NPC to fight
    room = state.rooms[state.current_room]
    npc = None

    if target:
        for nid in room.npcs:
            n = state.npcs.get(nid)
            if n and not n.defeated and target.lower() in n.name.lower():
                npc = n
                break
    else:
        for nid in room.npcs:
            n = state.npcs.get(nid)
            if n and not n.defeated and n.disposition == NPCDisposition.HOSTILE:
                npc = n
                break

    if not npc:
        if target:
            return [f"There's nobody named '{target}' to fight here."]
        return ["There's nothing to fight here."]

    return _start_combat(state, npc.id)


def _combat_round(state: MudState) -> list[str]:
    """Execute one round of combat."""
    if not state.combat or not state.combat.active:
        return ["You're not in combat."]

    combat = state.combat
    combat.turn += 1
    lines = []

    # Player attacks
    variance = random.uniform(0.8, 1.2)
    player_dmg = max(1, int((combat.player.attack - combat.enemy.defense * 0.5) * variance))
    crit = random.random() < 0.15
    if crit:
        player_dmg = int(player_dmg * 1.5)

    combat.enemy.hp = max(0, combat.enemy.hp - player_dmg)
    crit_text = " [bold yellow]CRITICAL![/bold yellow]" if crit else ""
    lines.append(f"⚔️ You strike {combat.enemy.emoji} {combat.enemy.name} for [bold]{player_dmg}[/bold] damage!{crit_text}")

    if not combat.enemy.alive:
        return lines + _combat_victory(state)

    # Enemy attacks
    variance = random.uniform(0.8, 1.2)
    enemy_dmg = max(1, int((combat.enemy.attack - combat.player.defense * 0.5) * variance))
    crit = random.random() < 0.1
    if crit:
        enemy_dmg = int(enemy_dmg * 1.5)

    combat.player.hp = max(0, combat.player.hp - enemy_dmg)
    crit_text = " [bold red]CRITICAL![/bold red]" if crit else ""
    lines.append(f"{combat.enemy.emoji} {combat.enemy.name} hits you for [bold red]{enemy_dmg}[/bold red] damage!{crit_text}")

    if not combat.player.alive:
        return lines + _combat_defeat(state)

    # Status update
    lines.append(f"\n  You:  {combat.player.hp_bar()}")
    lines.append(f"  {combat.enemy.emoji}: {combat.enemy.hp_bar()}")

    return lines


def _combat_victory(state: MudState) -> list[str]:
    """Handle winning combat."""
    combat = state.combat
    npc = state.npcs.get(combat.npc_id)
    lines = [
        f"\n[bold green]🎉 Victory! {combat.enemy.emoji} {combat.enemy.name} has been defeated![/bold green]",
    ]

    if npc:
        npc.defeated = True
        state.npcs_defeated += 1

        # Drop loot
        for loot_id in npc.loot:
            item = state.items.get(loot_id)
            if item:
                if state.inventory.add_item(item):
                    lines.append(f"[green]Looted: {item.emoji} {item.name}[/green]")
                    state.items_collected += 1
                    _check_quest_progress(state, "fetch", item.id)

        # Gold drop
        gold_drop = random.randint(5, 20)
        state.inventory.gold += gold_drop
        state.gold_earned += gold_drop
        lines.append(f"[yellow]+{gold_drop} gold[/yellow]")

        # Check kill quest progress
        _check_quest_progress(state, "kill", combat.npc_id)

    comment = _buddy_comment(state.party, "combat_win")
    if comment:
        lines.append(f"\n{comment}")

    state.combat = None
    return lines


def _combat_defeat(state: MudState) -> list[str]:
    """Handle losing combat."""
    lines = [
        f"\n[bold red]💀 Defeat! Your party has been overwhelmed.[/bold red]",
        "[dim]You wake up back in the lobby, a bit worse for wear.[/dim]",
    ]

    comment = _buddy_comment(state.party, "combat_lose")
    if comment:
        lines.append(f"\n{comment}")

    # Restore enemy HP for re-attempts
    if state.combat:
        npc = state.npcs.get(state.combat.npc_id)
        if npc:
            npc.hp = npc.max_hp

    # Reset to lobby, keep inventory
    state.current_room = "lobby"
    state.combat = None

    return lines


def _handle_flee(state: MudState, _arg: str) -> list[str]:
    """Flee from combat."""
    if not state.combat or not state.combat.active:
        return ["You're not in combat. (But the existential dread is real.)"]

    # 70% chance to flee
    if random.random() < 0.7:
        npc = state.npcs.get(state.combat.npc_id)
        if npc:
            npc.hp = npc.max_hp  # Reset enemy HP
        state.combat = None
        return ["[yellow]You flee from combat![/yellow] The shame will linger longer than the wounds."]
    else:
        # Failed flee — enemy gets a free hit
        combat = state.combat
        enemy_dmg = max(1, combat.enemy.attack - combat.player.defense)
        combat.player.hp = max(0, combat.player.hp - enemy_dmg)
        lines = [
            f"[red]You try to flee but {combat.enemy.name} blocks your escape![/red]",
            f"{combat.enemy.emoji} Hits you for [bold red]{enemy_dmg}[/bold red] as you stumble!",
        ]
        if not combat.player.alive:
            lines.extend(_combat_defeat(state))
        return lines


# ---------------------------------------------------------------------------
# Quest progress tracking
# ---------------------------------------------------------------------------

def _check_quest_progress(state: MudState, action_type: str, target_id: str):
    """Check if an action advances any quest objectives."""
    for quest in state.quests.values():
        if quest.status != QuestStatus.ACTIVE:
            continue
        for obj in quest.objectives:
            if obj.complete:
                continue
            if action_type == "kill" and obj.quest_type == QuestType.KILL and obj.target == target_id:
                obj.current += 1
            elif action_type == "fetch" and obj.quest_type == QuestType.FETCH and obj.target == target_id:
                if state.inventory.has_item(target_id):
                    obj.current += 1
            elif action_type == "talk" and obj.quest_type == QuestType.TALK and obj.target == target_id:
                obj.current += 1
            elif action_type == "visit" and obj.quest_type == QuestType.EXPLORE and obj.target == target_id:
                obj.current += 1


# ---------------------------------------------------------------------------
# Main command dispatch
# ---------------------------------------------------------------------------

COMMAND_HANDLERS = {
    "look": _handle_look,
    "go": _handle_go,
    "examine": _handle_examine,
    "talk": _handle_talk,
    "take": _handle_take,
    "drop": _handle_drop,
    "use": _handle_use,
    "inventory": _handle_inventory,
    "buy": _handle_buy,
    "quest": _handle_quest,
    "map": _handle_map,
    "wait": _handle_wait,
    "help": _handle_help,
    "attack": _handle_attack,
    "flee": _handle_flee,
}


def process_command(state: MudState, raw_input: str) -> list[str]:
    """Process a player command and return output lines."""
    cmd, arg = parse_command(raw_input)

    if not cmd:
        return ["Type [bold]help[/bold] for a list of commands."]

    # In combat, restrict commands
    if state.combat and state.combat.active:
        if cmd not in ("attack", "flee", "use", "inventory", "help"):
            return ["You're in combat! [bold]attack[/bold], [bold]use[/bold] <item>, or [bold]flee[/bold]."]

    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        return handler(state, arg)

    return [f"Unknown command: '{cmd}'. Type [bold]help[/bold] for options."]


def get_intro_text(state: MudState) -> list[str]:
    """Get the MUD intro/welcome text."""
    lines = [
        "[bold]╔══════════════════════════════════════════════════╗[/bold]",
        "[bold]║         🏢 STACKHAVEN MUD 🏢                    ║[/bold]",
        "[bold]║  A Text Adventure in a Tech Company Gone Wrong   ║[/bold]",
        "[bold]╚══════════════════════════════════════════════════╝[/bold]",
        "",
        "[dim]You are an adventurer in StackHaven, a tech company where",
        "the code has become sentient, the meetings never end, and",
        "the coffee machine has opinions. Explore rooms, talk to NPCs,",
        "fight bugs (literally), and complete quests.[/dim]",
        "",
        "[dim]Your buddies accompany you, offering commentary and moral",
        "support of varying quality.[/dim]",
        "",
        "[dim]Type [bold]help[/bold] for commands, or just start exploring.[/dim]",
    ]

    # Party info
    if state.party:
        lines.append("")
        lines.append("[bold]Your party:[/bold]")
        for b in state.party:
            lines.append(f"  {b.species.emoji} {b.name} (Lv.{b.level} {b.species.name})")

    lines.append("")
    lines.extend(_handle_look(state, ""))

    return lines


def get_game_result(state: MudState, buddy_id: int) -> GameResult:
    """Generate a GameResult from the current MUD state."""
    # Determine outcome based on quests and exploration
    if state.quests_completed >= 2:
        outcome = GameOutcome.WIN
    elif state.rooms_visited >= 5:
        outcome = GameOutcome.DRAW
    else:
        outcome = GameOutcome.LOSE

    xp = (
        state.rooms_visited * 2
        + state.npcs_talked * 3
        + state.npcs_defeated * 8
        + state.quests_completed * 15
        + state.items_collected * 1
    )

    return GameResult(
        game_type=GameType.MUD,
        outcome=outcome,
        buddy_id=buddy_id,
        score={
            "rooms_visited": state.rooms_visited,
            "npcs_talked": state.npcs_talked,
            "npcs_defeated": state.npcs_defeated,
            "quests_completed": state.quests_completed,
            "gold_earned": state.gold_earned,
            "turns": state.turns,
        },
        xp_earned=xp,
        mood_delta=state.quests_completed * 3 + state.npcs_defeated * 2,
    )
