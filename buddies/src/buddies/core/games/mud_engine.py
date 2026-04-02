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
from buddies.core.games.mud_multiplayer import (
    MudMultiplayerStore, SoapstoneNote, Bloodstain, Phantom,
    TEMPLATES, SUBJECTS, PHANTOM_ACTIONS,
    build_note_message, get_template_list, get_subject_list,
    format_note_display, format_bloodstain_display, format_phantom_display,
)
from buddies.core.games.mud_transport import MudTransport
from buddies.core.games.mud_negotiate import (
    NEGOTIATION_TREES, NEGOTIATE_COMMENTARY, NEGOTIATE_GIFTS,
    NegotiationState, NegotiateOutcome,
    resolve_negotiation, get_available_responses,
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
    gold_spent: int = 0
    gold_gambled: int = 0
    gold_won_gambling: int = 0
    tips_given: int = 0
    bounties_completed: int = 0
    turns: int = 0
    notes_left: int = 0
    notes_rated: int = 0
    # Flags
    game_over: bool = False
    # Negotiation
    negotiation: NegotiationState | None = None
    # Async multiplayer
    mp_store: MudMultiplayerStore | None = None
    mp_transport: MudTransport | None = None
    # Sync stats (shown to player)
    remote_notes_synced: int = 0
    remote_stains_synced: int = 0


def create_mud_game(party: list[BuddyState]) -> MudState:
    """Create a new MUD game with the starter world."""
    items = build_starter_items()
    npcs = build_starter_npcs(items)
    rooms = build_starter_rooms()
    quests = build_starter_quests()

    # Try to load multiplayer store (fails gracefully if data dir unavailable)
    mp_store = None
    try:
        mp_store = MudMultiplayerStore()
    except Exception:
        pass

    return MudState(
        rooms=rooms,
        npcs=npcs,
        items=items,
        quests=quests,
        inventory=MudInventory(gold=10),
        party=party,
        mp_store=mp_store,
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
        "sell": "sell",
        "lore": "lore",
        "note": "note", "write": "note", "message": "note",
        "rate": "rate", "upvote": "rate", "downvote": "rate",
        "notes": "notes", "messages": "notes",
        "bloodstain": "bloodstain", "bloodstains": "bloodstain", "deaths": "bloodstain",
        "rumors": "rumors", "rumor": "rumors", "news": "rumors", "network": "rumors",
        "quest": "quest", "quests": "quest", "q": "quest",
        "help": "help", "h": "help", "?": "help",
        "map": "map",
        "flee": "flee", "run": "flee", "escape": "flee",
        "wait": "wait",
        "gamble": "gamble", "bet": "gamble", "wager": "gamble",
        "wealth": "wealth", "balance": "wealth", "money": "wealth",
        "tip": "tip",
        "bounty": "bounty", "bounties": "bounty", "contracts": "bounty",
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


# Room-specific buddy reactions — personality × location = unique flavor
ROOM_REACTIONS: dict[str, dict[str, list[str]]] = {
    "server_room": {
        "debugging": ["{name}: \"Finally, my element. Look at those status LEDs. Beautiful.\""],
        "chaos": ["{name}: \"So many blinking lights... what happens if I pull this cable?\"", "{name}: \"BLINKY LIGHTS! I want to touch ALL of them!\""],
        "snark": ["{name}: \"Ah yes, the room where 'it works on my machine' comes to die.\""],
        "wisdom": ["{name}: \"The hum of servers... like a digital monastery.\""],
        "patience": ["{name}: \"It's cold in here. But kind of peaceful.\""],
    },
    "root_chamber": {
        "debugging": ["{name}: \"root access... I can feel the power. And the responsibility.\""],
        "chaos": ["{name}: \"sudo rm -rf /  ...just kidding. ...unless?\""],
        "snark": ["{name}: \"hunter2? THAT'S the root password? We deserve to be hacked.\""],
        "wisdom": ["{name}: \"With great root access comes great sudo responsibility.\""],
        "patience": ["{name}: \"Let's... be very careful what we type here.\""],
    },
    "cloud_district": {
        "debugging": ["{name}: \"The abstractions here go all the way down. There is no bottom.\""],
        "chaos": ["{name}: \"Nothing is real up here! I love it! Everything is VIBES!\""],
        "snark": ["{name}: \"The cloud is just someone else's computer. And they charge by the second.\""],
        "wisdom": ["{name}: \"Somewhere beneath all this... there's still a computer in a room.\""],
        "patience": ["{name}: \"It's actually quite serene up here. If you ignore the billing.\""],
    },
    "dead_code_garden": {
        "debugging": ["{name}: \"All this code... perfectly functional. Never called. Tragic.\""],
        "chaos": ["{name}: \"I bet if we un-commented this one function the whole app would—\" \"NO.\""],
        "snark": ["{name}: \"'Temporary fix from 2019.' It's been here longer than most employees.\""],
        "wisdom": ["{name}: \"Even dead code was written with hope. Remember that.\""],
        "patience": ["{name}: \"It's quiet here. Even the bugs have moved on.\""],
    },
    "break_room": {
        "debugging": ["{name}: \"The fridge... I could optimize the food placement algorithm.\""],
        "chaos": ["{name}: \"I'm going to microwave fish. I don't care about the consequences.\""],
        "snark": ["{name}: \"The passive-aggressive notes on the fridge are the real codebase.\""],
        "wisdom": ["{name}: \"Coffee: the true fuel of all software. Respect the bean.\""],
        "patience": ["{name}: \"A break room. Finally, somewhere to just... be.\""],
    },
    "meeting_room": {
        "debugging": ["{name}: \"This whiteboard... it's like a stack trace for ideas. All wrong.\""],
        "chaos": ["{name}: \"WHAT IF we added blockchain? And AI? And a social component? AND—\""],
        "snark": ["{name}: \"This meeting could have been an email. Or better yet, nothing.\""],
        "wisdom": ["{name}: \"The ambition on this whiteboard is... aspirational.\""],
        "patience": ["{name}: \"I'll just sit quietly until this is over.\""],
    },
    "qa_lab": {
        "debugging": ["{name}: \"A QA lab! Where broken things get found before they break worse.\""],
        "chaos": ["{name}: \"Tests?! I don't need tests! I AM the test! Ship it!\""],
        "snark": ["{name}: \"848 tests. One failure. And THAT'S the one everyone will remember.\""],
        "wisdom": ["{name}: \"The test pyramid... a philosophy as much as a practice.\""],
        "patience": ["{name}: \"Every test is a promise. Let's make sure they're kept.\""],
    },
    "testing_grounds": {
        "debugging": ["{name}: \"This is a controlled environment. Sort of. If you squint.\""],
        "chaos": ["{name}: \"FLAKY TESTS! My favorite! They're like little chaotic butterflies!\""],
        "snark": ["{name}: \"The tests don't lie. They just... mislead occasionally.\""],
        "wisdom": ["{name}: \"A test that sometimes fails is worse than no test at all.\""],
        "patience": ["{name}: \"These poor test cases. Let's put them to rest.\""],
    },
    "standup_room": {
        "debugging": ["{name}: \"'No blockers.' Everyone says 'no blockers.' Everyone has blockers.\""],
        "chaos": ["{name}: \"I'm blocked on everything and nothing simultaneously!\""],
        "snark": ["{name}: \"Standups: where 15 minutes becomes 2 hours of people talking.\""],
        "wisdom": ["{name}: \"The ritual of the standup... it brings order to chaos. Theoretically.\""],
        "patience": ["{name}: \"I'll wait. I have all day. Apparently so does this meeting.\""],
    },
    "incident_channel": {
        "debugging": ["{name}: \"SEV1. Time to focus. What are the error logs saying?\""],
        "chaos": ["{name}: \"EVERYTHING IS ON FIRE THIS IS FINE I'M HAVING A GREAT TIME\""],
        "snark": ["{name}: \"'Blameless post-mortem.' Sure. And I'm a natural blonde.\""],
        "wisdom": ["{name}: \"Every incident is a lesson. This one... is a master class.\""],
        "patience": ["{name}: \"Deep breaths. We'll get through this. One alert at a time.\""],
    },
    "archive": {
        "debugging": ["{name}: \"The First Commit... HTML with inline styles. We've come so far. Sort of.\""],
        "chaos": ["{name}: \"What happens if I rm -rf the archive? HYPOTHETICALLY.\""],
        "snark": ["{name}: \"'Won't Fix' filing cabinet? That's not a cabinet, that's a graveyard.\""],
        "wisdom": ["{name}: \"History sleeps here. And with it, all the lessons we keep not learning.\""],
        "patience": ["{name}: \"It's peaceful in here. Like a library for broken dreams.\""],
    },
    "kubernetes_cluster": {
        "debugging": ["{name}: \"Container orchestration. It's like herding cats, but the cats are on fire.\""],
        "chaos": ["{name}: \"SCALE TO INFINITY! SPIN UP ALL THE PODS! THE BILLING CAN'T CATCH ME!\""],
        "snark": ["{name}: \"'Kubernetes makes things simpler.' That's what they said. They lied.\""],
        "wisdom": ["{name}: \"The cluster is a living organism. It breathes. It scales. It crashes.\""],
        "patience": ["{name}: \"Let's just... not touch anything. It's working. Somehow.\""],
    },
    "parking_garage": {
        "debugging": ["{name}: \"The WiFi signal is stronger down here. That's... concerning.\""],
        "chaos": ["{name}: \"I bet I could hotwire one of these Teslas. For science.\""],
        "snark": ["{name}: \"Someone is literally living in the parking garage. Peak tech culture.\""],
        "wisdom": ["{name}: \"Even the parking garage tells a story. A sad, concrete story.\""],
        "patience": ["{name}: \"Nobody comes down here. It's... kind of nice, actually.\""],
    },
}


def _room_reaction(party: list[BuddyState], room_id: str) -> str | None:
    """Get a room-specific buddy reaction (higher priority than generic)."""
    if not party:
        return None
    room_pool = ROOM_REACTIONS.get(room_id)
    if not room_pool:
        return None
    buddy = random.choice(party)
    dominant = max(buddy.stats, key=buddy.stats.get)
    lines = room_pool.get(dominant, [])
    if not lines:
        return None
    return random.choice(lines).format(name=buddy.name, emoji=buddy.species.emoji)


# ---------------------------------------------------------------------------
# Random world events — things that happen as you explore
# ---------------------------------------------------------------------------

WORLD_EVENTS = [
    # Company-wide announcements
    "[dim italic]📢 ANNOUNCEMENT: The snack drawer has been restocked. This is not a drill.[/dim italic]",
    "[dim italic]📢 ANNOUNCEMENT: Please stop microwaving fish in the break room. You know who you are.[/dim italic]",
    "[dim italic]📢 ANNOUNCEMENT: The parking garage WiFi is now faster than the office WiFi. This is 'by design.'[/dim italic]",
    "[dim italic]📢 ANNOUNCEMENT: Reminder that 'works on my machine' is not a valid deploy strategy.[/dim italic]",
    "[dim italic]📢 ANNOUNCEMENT: The CI/CD pipeline is paused for 'maintenance.' It's actually just resting.[/dim italic]",

    # Slack-like interruptions
    "[dim italic]💬 #general: does anyone know why the staging server is playing music?[/dim italic]",
    "[dim italic]💬 #random: who left a rubber duck in the server room? ...actually, leave it. uptime improved 3%.[/dim italic]",
    "[dim italic]💬 #engineering: whoever force-pushed to main, please report to Gerald. bring snacks. you'll need them.[/dim italic]",
    "[dim italic]💬 #incidents: false alarm, the fire was metaphorical[/dim italic]",
    "[dim italic]💬 #standup: standup is postponed because we're in a meeting about having too many meetings[/dim italic]",

    # Strange occurrences
    "[dim italic]You hear a distant deploy siren. Someone whispers 'not on a Friday...'[/dim italic]",
    "[dim italic]The lights flicker. Somewhere, a database query takes 30 seconds instead of 30 milliseconds.[/dim italic]",
    "[dim italic]A Post-It note drifts past. It reads: 'TODO: remove this TODO'[/dim italic]",
    "[dim italic]You step on a cable. Three services go down. You carefully step off. They come back up.[/dim italic]",
    "[dim italic]A notification pops up on a nearby screen: 'Your free trial of functioning code has expired.'[/dim italic]",
    "[dim italic]You see someone sprinting with a laptop. They yell 'THE DEMO IS IN FIVE MINUTES' as they pass.[/dim italic]",
    "[dim italic]A printer somewhere prints a single page that says 'HELP' and then jams.[/dim italic]",
    "[dim italic]You hear a distant keyboard being furiously typed on. Then silence. Then a very quiet 'oh no.'[/dim italic]",
    "[dim italic]An intern walks past carrying a production database backup on a USB stick. In a ziplock bag.[/dim italic]",
    "[dim italic]The office plants look healthier than the production servers. The correlation is unclear.[/dim italic]",
]


def _maybe_world_event() -> str | None:
    """~20% chance of a random world event occurring."""
    if random.random() < 0.20:
        return random.choice(WORLD_EVENTS)
    return None


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

    # Async multiplayer: notes, bloodstains, phantoms
    if state.mp_store:
        # Notes
        notes = state.mp_store.get_notes_for_room(room.id, limit=2)
        if notes:
            lines.append("")
            for note in notes:
                lines.append(format_note_display(note))

        # Bloodstains
        stains = state.mp_store.get_bloodstains_for_room(room.id, limit=1)
        if stains:
            for stain in stains:
                lines.append(format_bloodstain_display(stain))

        # Phantom sighting
        phantom = state.mp_store.get_phantom_for_room(room.id)
        if phantom:
            lines.append(format_phantom_display(phantom))

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

    # Record phantom trace of our presence
    if state.mp_store and state.party:
        buddy = state.party[0]
        phantom = Phantom(
            room_id=state.current_room,
            buddy_name=buddy.name,
            buddy_emoji=buddy.species.emoji,
            buddy_species=buddy.species.name,
            action=random.choice(PHANTOM_ACTIONS),
        )
        state.mp_store.add_phantom(phantom)

    # Buddy commentary — room-specific reactions first, then generic
    reaction = _room_reaction(state.party, state.current_room)
    if reaction and random.random() < 0.6:
        lines.append(f"\n{reaction}")
    elif random.random() < 0.3:
        comment = _buddy_comment(state.party, "enter_room")
        if comment:
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
            lines = [
                f"\n{item.emoji} [bold]{item.name}[/bold]",
                item.description,
                f"[dim]Type: {item.item_type.value} | Value: {item.value}g[/dim]",
            ]
            if item.lore:
                lines.append(f"\n[italic]{item.lore}[/italic]")
            return lines

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
            if item.lore:
                lines.append(f"\n[italic]{item.lore}[/italic]")
            return lines

    return [f"You don't see '{target}' here."]


def _handle_talk(state: MudState, target: str) -> list[str]:
    """Talk to an NPC. During combat, negotiate with the enemy."""
    # If in combat, negotiate with the current enemy
    if state.combat and state.combat.active:
        if state.negotiation:
            return ["You're already negotiating! Pick a numbered response."]
        npc = state.npcs.get(state.combat.npc_id)
        if npc:
            return _start_negotiation(state, npc)
        return ["There's nobody to talk to in this fight."]

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
        return _start_negotiation(state, npc)

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
                state.gold_spent += item.value
                return [f"[green]Bought: {item.emoji} {item.name} for {item.value}g[/green]",
                        f"[yellow]Gold remaining: {state.inventory.gold}g[/yellow]"]
            else:
                return ["Your inventory is full!"]

    return [f"The shop doesn't have '{target}'."]


def _handle_sell(state: MudState, target: str) -> list[str]:
    """Sell an item to a merchant."""
    room = state.rooms[state.current_room]

    # Check for merchant
    merchant = None
    for nid in room.npcs:
        npc = state.npcs.get(nid)
        if npc and not npc.defeated and npc.disposition == NPCDisposition.MERCHANT:
            merchant = npc
            break

    if not merchant:
        return ["There's no merchant here to sell to."]

    if not target:
        # Show sellable items
        sellable = [i for i in state.inventory.items if i.value > 0 and i.item_type not in (ItemType.KEY, ItemType.QUEST)]
        if not sellable:
            return ["You don't have anything worth selling."]
        lines = [f"\n[bold]💰 Sellable Items[/bold]", f"{'─' * 40}"]
        for item in sellable:
            sell_price = max(1, item.value // 2)
            lines.append(f"  {item.emoji} {item.name} — [yellow]{sell_price}g[/yellow]")
        lines.append(f"\n[dim]Type [bold]sell <item name>[/bold] to sell. Items sell for half value.[/dim]")
        return lines

    # Sell specific item
    target_lower = target.lower()
    for item in state.inventory.items:
        if target_lower in item.name.lower():
            if item.item_type in (ItemType.KEY, ItemType.QUEST):
                return [f"You can't sell the {item.name}. It's too important."]
            sell_price = max(1, item.value // 2)
            state.inventory.remove_item(item.id)
            state.inventory.gold += sell_price
            state.gold_earned += sell_price
            return [
                f"[green]Sold: {item.emoji} {item.name} for {sell_price}g[/green]",
                f"[yellow]Gold: {state.inventory.gold}g[/yellow]",
            ]

    return [f"You don't have '{target}' to sell."]


# ---------------------------------------------------------------------------
# Lore command
# ---------------------------------------------------------------------------

def _handle_lore(state: MudState, arg: str) -> list[str]:
    """View collected lore from items — a codex of StackHaven's history."""
    lore_items = [i for i in state.inventory.items if i.lore]

    if arg:
        # Show lore for a specific item
        target_lower = arg.lower()
        for item in lore_items:
            if target_lower in item.name.lower():
                return [
                    f"\n{item.emoji} [bold]{item.name}[/bold]",
                    f"{'─' * 50}",
                    f"[italic]{item.lore}[/italic]",
                ]
        return [f"No lore found for '{arg}'. Try [bold]lore[/bold] to see all collected lore."]

    if not lore_items:
        lines = [
            "\n[bold]📖 Lore Codex[/bold]",
            f"{'─' * 50}",
            "[dim]No lore collected yet. Examine items to discover the hidden history of StackHaven.[/dim]",
            "[dim]Items with lore show it when you [bold]examine[/bold] them. Collect items to build your codex.[/dim]",
        ]
        return lines

    lines = [
        "\n[bold]📖 Lore Codex — The History of StackHaven[/bold]",
        f"{'─' * 50}",
        f"[dim]{len(lore_items)} fragment(s) collected[/dim]",
        "",
    ]
    for item in lore_items:
        lines.append(f"  {item.emoji} [bold]{item.name}[/bold]")

    lines.append(f"\n[dim]Type [bold]lore <item name>[/bold] to read a specific entry.[/dim]")
    return lines


# ---------------------------------------------------------------------------
# Async multiplayer command handlers
# ---------------------------------------------------------------------------

def _handle_note(state: MudState, arg: str) -> list[str]:
    """Leave a soapstone note in the current room."""
    if not state.mp_store:
        return ["[dim]Multiplayer features unavailable.[/dim]"]

    if not state.inventory.has_item("orange_soapstone"):
        return ["You need the [bold]Orange Soapstone[/bold] to leave notes. The Rubber Duck Sage in the Codebase Ruins might have one."]

    if not arg:
        # Show note builder
        lines = [
            "\n[bold]🧡 Soapstone Note[/bold]",
            f"{'─' * 50}",
            "Build a message by combining a template with a subject.",
            "",
            "[bold]Step 1:[/bold] Type [bold]note <template#> <subject#>[/bold]",
            "",
            "[bold]Templates:[/bold]",
        ]
        lines.extend(get_template_list())
        lines.append("")
        lines.append("[bold]Subjects:[/bold]")
        lines.extend(get_subject_list())
        lines.append("")
        lines.append("[dim]Example: [bold]note 0 2[/bold] → \"Try coffee\"[/dim]")
        return lines

    # Parse template and subject indices
    parts = arg.split()
    if len(parts) != 2:
        return ["Usage: [bold]note <template#> <subject#>[/bold]. Type [bold]note[/bold] to see options."]

    try:
        t_idx = int(parts[0])
        s_idx = int(parts[1])
    except ValueError:
        return ["Both arguments must be numbers. Type [bold]note[/bold] to see options."]

    message = build_note_message(t_idx, s_idx)
    if not message:
        return ["Invalid template or subject number. Type [bold]note[/bold] to see options."]

    # Get author info from first party buddy
    if state.party:
        author_name = state.party[0].name
        author_emoji = state.party[0].species.emoji
    else:
        author_name = "Anonymous"
        author_emoji = "👤"

    import time as _time
    note = SoapstoneNote(
        id=f"player_{state.current_room}_{int(_time.time())}",
        room_id=state.current_room,
        message=message,
        author_name=author_name,
        author_emoji=author_emoji,
    )
    state.mp_store.add_note(note)
    state.notes_left += 1

    return [
        f"\n[yellow]🧡 You inscribed a message on the ground:[/yellow]",
        f"  [bold]\"{message}\"[/bold]",
        "[dim]Other adventurers may find this note.[/dim]",
    ]


def _handle_rate(state: MudState, arg: str) -> list[str]:
    """Rate a soapstone note in the current room."""
    if not state.mp_store:
        return ["[dim]Multiplayer features unavailable.[/dim]"]

    notes = state.mp_store.get_notes_for_room(state.current_room, limit=10)
    if not notes:
        return ["There are no notes here to rate."]

    if not arg:
        lines = [
            "\n[bold]Rate a Note[/bold]",
            f"{'─' * 40}",
            "",
        ]
        for i, note in enumerate(notes):
            lines.append(f"  [bold cyan]{i}[/bold cyan]. {format_note_display(note)}")
        lines.append("")
        lines.append("[dim]Type [bold]rate <#> up[/bold] or [bold]rate <#> down[/bold][/dim]")
        return lines

    parts = arg.split()
    if len(parts) < 2:
        return ["Usage: [bold]rate <note#> up[/bold] or [bold]rate <note#> down[/bold]"]

    try:
        note_idx = int(parts[0])
    except ValueError:
        return ["First argument must be a note number."]

    if note_idx < 0 or note_idx >= len(notes):
        return [f"Invalid note number. Valid range: 0-{len(notes) - 1}"]

    upvote = parts[1].lower() in ("up", "upvote", "good", "yes", "+", "helpful")
    note = notes[note_idx]

    if state.mp_store.rate_note(note.id, upvote):
        state.notes_rated += 1
        emoji = "👍" if upvote else "👎"
        return [f"{emoji} You rated the note \"{note.message}\" — {note.rating_text}"]
    else:
        return ["You've already rated this note."]


def _handle_notes(state: MudState, _arg: str) -> list[str]:
    """View all notes in the current room."""
    if not state.mp_store:
        return ["[dim]Multiplayer features unavailable.[/dim]"]

    notes = state.mp_store.get_notes_for_room(state.current_room, limit=10)
    if not notes:
        return ["There are no notes in this room."]

    lines = ["\n[bold]📜 Notes in this room[/bold]", f"{'─' * 50}"]
    for i, note in enumerate(notes):
        lines.append(f"  [bold cyan]{i}[/bold cyan]. {format_note_display(note)}")
    lines.append(f"\n[dim]Type [bold]rate <#> up/down[/bold] to rate a note.[/dim]")
    return lines


def _handle_bloodstain(state: MudState, _arg: str) -> list[str]:
    """View bloodstains (death markers) in the current room."""
    if not state.mp_store:
        return ["[dim]Multiplayer features unavailable.[/dim]"]

    stains = state.mp_store.get_bloodstains_for_room(state.current_room, limit=5)
    if not stains:
        return ["No adventurers have fallen here. Yet."]

    lines = ["\n[bold red]💀 Bloodstains[/bold red]", f"{'─' * 50}"]
    for stain in stains:
        lines.append(format_bloodstain_display(stain))
    return lines


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
    zone_emoji = {"town": "🏢", "depths": "📚", "server_room": "🖥️", "cloud": "☁️", "qa": "🔍"}

    for zone_name in ["town", "depths", "server_room", "cloud", "qa"]:
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


def _handle_rumors(state: MudState, _arg: str) -> list[str]:
    """Hear rumors of other adventurers from across the network."""
    if not state.mp_store:
        return ["[dim]Multiplayer features unavailable.[/dim]"]

    lines = [
        "\n[bold]🌐 Rumors from the Network[/bold]",
        f"{'─' * 50}",
    ]

    # Gather stats about remote/phantom data
    total_notes = len(state.mp_store.notes)
    phantom_notes = sum(1 for n in state.mp_store.notes if n.is_phantom)
    player_notes = total_notes - phantom_notes
    total_stains = len(state.mp_store.bloodstains)
    total_phantoms = len(state.mp_store.phantoms)

    # Unique rooms with notes
    rooms_with_notes = len(set(n.room_id for n in state.mp_store.notes))
    # Most dangerous room (most bloodstains)
    room_deaths: dict[str, int] = {}
    for s in state.mp_store.bloodstains:
        room_deaths[s.room_id] = room_deaths.get(s.room_id, 0) + 1
    deadliest = max(room_deaths.items(), key=lambda x: x[1]) if room_deaths else None
    # Most popular note
    top_note = max(state.mp_store.notes, key=lambda n: n.rating) if state.mp_store.notes else None
    # Most feared enemy
    enemy_kills: dict[str, int] = {}
    for s in state.mp_store.bloodstains:
        enemy_kills[s.cause_of_death] = enemy_kills.get(s.cause_of_death, 0) + 1
    deadliest_enemy = max(enemy_kills.items(), key=lambda x: x[1]) if enemy_kills else None

    lines.append("")

    if state.remote_notes_synced > 0 or state.remote_stains_synced > 0:
        lines.append(
            f"[bold cyan]📡 Connected to the network.[/bold cyan] "
            f"Synced {state.remote_notes_synced} note(s), "
            f"{state.remote_stains_synced} bloodstain(s) from other adventurers."
        )
    else:
        lines.append("[dim]Local data only — use [bold]sync[/bold] to connect to other adventurers.[/dim]")

    lines.append("")
    lines.append(f"[yellow]📜 {total_notes} soapstone messages[/yellow] across {rooms_with_notes} rooms")
    if player_notes > 0:
        lines.append(f"   ({player_notes} from real adventurers, {phantom_notes} from phantoms)")
    lines.append(f"[red]💀 {total_stains} bloodstains[/red] mark where adventurers fell")
    lines.append(f"[dim]👻 {total_phantoms} phantom traces[/dim] linger in the halls")

    if deadliest:
        room_name = deadliest[0].replace("_", " ").title()
        lines.append(f"\n[bold red]Most dangerous room:[/bold red] {room_name} ({deadliest[1]} deaths)")

    if deadliest_enemy:
        lines.append(f"[bold red]Most feared foe:[/bold red] {deadliest_enemy[0]} ({deadliest_enemy[1]} kills)")

    if top_note and top_note.rating > 0:
        lines.append(f"\n[bold yellow]Most helpful message:[/bold yellow]")
        lines.append(f"  \"{top_note.message}\" {top_note.rating_text}")
        lines.append(f"  — {top_note.author_emoji} {top_note.author_name}")

    # Flavor text
    flavor = [
        "\n[dim italic]The network hums. Somewhere, another adventurer just left a note.[/dim italic]",
        "\n[dim italic]You feel a faint connection to adventurers past and present.[/dim italic]",
        "\n[dim italic]The bloodstains tell stories. Not happy ones, but stories nonetheless.[/dim italic]",
        "\n[dim italic]In StackHaven, nobody truly adventures alone.[/dim italic]",
        "\n[dim italic]The phantoms remember what the living have forgotten.[/dim italic]",
    ]
    lines.append(random.choice(flavor))

    return lines


# ---------------------------------------------------------------------------
# Negotiation system (SMT-style)
# ---------------------------------------------------------------------------

def _negotiate_comment(party: list, context: str) -> str | None:
    """Get a buddy commentary line for negotiation events."""
    if not party:
        return None
    buddy = random.choice(party)
    from buddies.core.prose import REGISTERS
    dominant = max(buddy.stats, key=buddy.stats.get)
    register = REGISTERS.get(dominant, "calm")
    pool = NEGOTIATE_COMMENTARY.get(context, {}).get(register, [])
    if not pool:
        return None
    line = random.choice(pool)
    return line.format(name=f"{buddy.species.emoji} {buddy.name}")


def _start_negotiation(state: MudState, npc) -> list[str]:
    """Begin negotiation with a hostile NPC."""
    tree = NEGOTIATION_TREES.get(npc.id)
    if not tree:
        return [f"{npc.emoji} {npc.name} snarls at you. It doesn't seem like the talking type."]

    # Create negotiation state
    state.negotiation = NegotiationState(npc_id=npc.id)

    lines = [
        f"\n[bold yellow]🗣️ NEGOTIATION: {npc.emoji} {npc.name}[/bold yellow]",
        f"{'─' * 50}",
    ]

    comment = _negotiate_comment(state.party, "negotiate_start")
    if comment:
        lines.append(comment)
        lines.append("")

    # Show first exchange
    lines.extend(_show_negotiate_exchange(state))

    return lines


def _show_negotiate_exchange(state: MudState) -> list[str]:
    """Display the current negotiation exchange."""
    if not state.negotiation:
        return []

    tree = NEGOTIATION_TREES.get(state.negotiation.npc_id, [])
    stage = state.negotiation.stage

    if stage >= len(tree):
        return _finish_negotiation(state)

    exchange = tree[stage]
    npc = state.npcs.get(state.negotiation.npc_id)
    npc_emoji = npc.emoji if npc else "❓"

    lines = [f"\n{npc_emoji} {exchange.npc_line}", ""]

    # Get buddy stats for filtering responses
    buddy_stats = {}
    if state.party:
        # Use the party leader's stats for stat-gated options
        for stat, val in state.party[0].stats.items():
            # Use max across party so any buddy's strength helps
            buddy_stats[stat] = max(val, buddy_stats.get(stat, 0))
        for buddy in state.party[1:]:
            for stat, val in buddy.stats.items():
                buddy_stats[stat] = max(val, buddy_stats.get(stat, 0))

    available = get_available_responses(exchange, buddy_stats)

    lines.append("[bold]Your response:[/bold]")
    for display_idx, (_, resp) in enumerate(available):
        stat_tag = ""
        if resp.stat_requirement:
            stat_name = resp.stat_requirement.upper()
            stat_tag = f" [dim cyan][{stat_name}][/dim cyan]"
        lines.append(f"  [bold cyan]{display_idx + 1}[/bold cyan]. {resp.text}{stat_tag}")

    lines.append("")
    lines.append("[dim]Type a number to respond, or [bold]attack[/bold] to fight instead.[/dim]")

    return lines


def _handle_negotiate_response(state: MudState, choice: int) -> list[str]:
    """Handle the player's numbered response during negotiation."""
    if not state.negotiation:
        return [f"You're not negotiating with anyone. (Did you mean something else?)"]

    tree = NEGOTIATION_TREES.get(state.negotiation.npc_id, [])
    stage = state.negotiation.stage

    if stage >= len(tree):
        return _finish_negotiation(state)

    exchange = tree[stage]

    # Get available responses (filtered by stats)
    buddy_stats = {}
    if state.party:
        for buddy in state.party:
            for stat, val in buddy.stats.items():
                buddy_stats[stat] = max(val, buddy_stats.get(stat, 0))

    available = get_available_responses(exchange, buddy_stats)

    # Validate choice (1-indexed from player's perspective)
    idx = choice - 1
    if idx < 0 or idx >= len(available):
        return [f"Choose a number between 1 and {len(available)}."]

    _, resp = available[idx]
    lines = []

    # Show player's choice
    lines.append(f"\n[bold green]> \"{resp.text}\"[/bold green]")

    # Apply mood change
    state.negotiation.mood += resp.mood_change

    # Handle gold demands
    if exchange.demand_gold > 0 and resp.tag == "pay":
        if state.inventory.gold >= exchange.demand_gold:
            state.inventory.gold -= exchange.demand_gold
            state.negotiation.demands_met += 1
            lines.append(f"[yellow]-{exchange.demand_gold} gold[/yellow]")
        else:
            lines.append("[red]You don't have enough gold![/red]")
            state.negotiation.mood -= 10  # Broken promise

    # Mood feedback
    if resp.mood_change >= 20:
        npc = state.npcs.get(state.negotiation.npc_id)
        emoji = npc.emoji if npc else "❓"
        lines.append(f"\n[dim]{emoji} seems genuinely moved by your words.[/dim]")
    elif resp.mood_change >= 10:
        lines.append("[dim]That seemed to resonate.[/dim]")
    elif resp.mood_change <= -15:
        lines.append("[dim]That... did not go well.[/dim]")
    elif resp.mood_change <= -5:
        lines.append("[dim]It narrows its eyes.[/dim]")

    # Advance to next stage
    state.negotiation.stage += 1

    # Show next exchange or resolve
    if state.negotiation.stage >= len(tree):
        lines.extend(_finish_negotiation(state))
    else:
        lines.extend(_show_negotiate_exchange(state))

    return lines


def _finish_negotiation(state: MudState) -> list[str]:
    """Resolve the negotiation and apply its outcome."""
    if not state.negotiation:
        return []

    outcome, flavor = resolve_negotiation(state.negotiation)
    npc_id = state.negotiation.npc_id
    npc = state.npcs.get(npc_id)

    lines = [
        "",
        f"{'─' * 50}",
        f"[italic]{flavor}[/italic]",
    ]

    if outcome == NegotiateOutcome.GIFT:
        # Enemy gives an item and leaves
        gift_id = NEGOTIATE_GIFTS.get(npc_id)
        gift_item = state.items.get(gift_id) if gift_id else None
        if gift_item and state.inventory.add_item(gift_item):
            lines.append(f"\n[green]Received: {gift_item.emoji} {gift_item.name}[/green]")
            state.items_collected += 1
        if npc:
            npc.defeated = True
            state.npcs_defeated += 1
        gold_gift = random.randint(5, 15)
        state.inventory.gold += gold_gift
        state.gold_earned += gold_gift
        lines.append(f"[yellow]+{gold_gift} gold[/yellow]")
        lines.append(f"\n[bold green]🕊️ {npc.emoji if npc else ''} {npc.name if npc else 'The enemy'} departs peacefully.[/bold green]")
        comment = _negotiate_comment(state.party, "negotiate_gift")
        if comment:
            lines.append(f"\n{comment}")
        # Check quest progress
        if gift_id:
            _check_quest_progress(state, "fetch", gift_id)
        _check_quest_progress(state, "kill", npc_id)
        state.combat = None

    elif outcome == NegotiateOutcome.PEACE:
        if npc:
            npc.defeated = True
            state.npcs_defeated += 1
        lines.append(f"\n[bold green]🕊️ {npc.emoji if npc else ''} {npc.name if npc else 'The enemy'} departs peacefully.[/bold green]")
        comment = _negotiate_comment(state.party, "negotiate_success")
        if comment:
            lines.append(f"\n{comment}")
        _check_quest_progress(state, "kill", npc_id)
        state.combat = None

    elif outcome == NegotiateOutcome.BRIBE:
        # Offer to pay 20 gold for peace
        if state.inventory.gold >= 20:
            state.inventory.gold -= 20
            lines.append("[yellow]-20 gold[/yellow]")
            if npc:
                npc.defeated = True
                state.npcs_defeated += 1
            lines.append(f"\n[bold green]🕊️ {npc.emoji if npc else ''} {npc.name if npc else 'The enemy'} takes the gold and leaves.[/bold green]")
            _check_quest_progress(state, "kill", npc_id)
            state.combat = None
        else:
            lines.append("[red]You can't afford the bribe! It attacks![/red]")
            outcome = NegotiateOutcome.ANGRY  # Fall through to angry

    elif outcome == NegotiateOutcome.SCAM:
        # Takes gold and attacks anyway
        stolen = min(state.inventory.gold, random.randint(10, 25))
        if stolen > 0:
            state.inventory.gold -= stolen
            lines.append(f"[red]-{stolen} gold stolen![/red]")
        lines.append("\n[bold red]⚔️ It was a trap! Combat resumes![/bold red]")
        comment = _negotiate_comment(state.party, "negotiate_scam")
        if comment:
            lines.append(f"\n{comment}")
        # Combat continues — enemy gets a free hit
        if state.combat and state.combat.active:
            enemy_dmg = max(1, state.combat.enemy.attack - state.combat.player.defense)
            state.combat.player.hp = max(0, state.combat.player.hp - enemy_dmg)
            lines.append(f"{state.combat.enemy.emoji} Sucker-punches you for [bold red]{enemy_dmg}[/bold red] damage!")
            if not state.combat.player.alive:
                lines.extend(_combat_defeat(state))

    if outcome == NegotiateOutcome.ANGRY:
        # Enemy gets attack buff
        if state.combat:
            state.combat.enemy.attack = int(state.combat.enemy.attack * 1.3)
            lines.append(f"\n[bold red]⚔️ {npc.emoji if npc else ''} is ENRAGED! (+30% ATK)[/bold red]")
        elif npc:
            # Start combat with the now-angry enemy (if not in combat yet)
            lines.append("\n[bold red]⚔️ It attacks![/bold red]")
            lines.extend(_start_combat(state, npc_id))
            if state.combat:
                state.combat.enemy.attack = int(state.combat.enemy.attack * 1.3)
                lines.append(f"[bold red]{npc.emoji} is ENRAGED! (+30% ATK)[/bold red]")
        comment = _negotiate_comment(state.party, "negotiate_fail")
        if comment:
            lines.append(f"\n{comment}")

    elif outcome == NegotiateOutcome.NOTHING:
        lines.append("\n[yellow]The negotiation fizzled. Combat continues.[/yellow]")
        comment = _negotiate_comment(state.party, "negotiate_fail")
        if comment:
            lines.append(f"\n{comment}")

    # Clear negotiation state
    state.negotiation = None

    return lines


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
        "  [bold]talk[/bold]            — Negotiate with hostile NPCs (SMT-style!)",
        "  [bold]flee[/bold]            — Run from combat",
        "",
        "[bold cyan]Commerce:[/bold cyan]",
        "  [bold]buy[/bold]             — Browse/buy from merchants",
        "  [bold]sell[/bold]            — Sell items to merchants (half value)",
        "  [bold]gamble[/bold]          — Games of chance (coin flip, slots)",
        "  [bold]tip[/bold]             — Tip an NPC",
        "  [bold]bounty[/bold]          — View/claim bounty contracts",
        "  [bold]wealth[/bold]          — View economy stats",
        "",
        "[bold cyan]Multiplayer:[/bold cyan]",
        "  [bold]note[/bold]            — Leave a soapstone message (needs Orange Soapstone)",
        "  [bold]notes[/bold]           — View notes in this room",
        "  [bold]rate[/bold]            — Rate a note (up/down)",
        "  [bold]bloodstain[/bold]      — View death markers in this room",
        "  [bold]rumors[/bold]          — Hear what other adventurers are up to",
        "",
        "[bold cyan]Status:[/bold cyan]",
        "  [bold]inventory[/bold] (i)   — Check your items",
        "  [bold]quest[/bold] (q)       — View quest log",
        "  [bold]map[/bold]             — Show world map",
        "  [bold]lore[/bold]            — Read collected lore fragments",
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
    lines.append(f"\n[dim]Commands: [bold]attack[/bold] — strike | [bold]talk[/bold] — negotiate | [bold]use[/bold] <item> — heal | [bold]flee[/bold] — run away[/dim]")

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

    # Leave a bloodstain
    if state.combat and state.mp_store and state.party:
        import time as _time
        buddy = state.party[0]
        stain = Bloodstain(
            id=f"death_{state.current_room}_{int(_time.time())}",
            room_id=state.current_room,
            cause_of_death=state.combat.enemy.name,
            buddy_name=buddy.name,
            buddy_emoji=buddy.species.emoji,
            buddy_level=buddy.level,
        )
        state.mp_store.add_bloodstain(stain)
        lines.append("[dim]💀 A bloodstain marks where you fell...[/dim]")

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
# Economy Phase 3: Gambling, Tipping, Bounties, Wealth
# ---------------------------------------------------------------------------

def _handle_gamble(state: MudState, arg: str) -> list[str]:
    """Gamble gold at Lucky's games of chance."""
    # Must be in a room with Lucky
    room = state.rooms[state.current_room]
    if "lucky" not in room.npcs:
        return ["There's nobody here to gamble with. Find Lucky in the supply area."]

    parts = arg.strip().split()
    if len(parts) < 2:
        return [
            "\n[bold]🎰 Lucky's Games of Chance[/bold]",
            f"{'─' * 40}",
            f"[yellow]Your gold: {state.inventory.gold}g[/yellow]",
            "",
            "[bold]Games:[/bold]",
            "  [bold]gamble flip <amount>[/bold]  — Coin flip, double or nothing (50/50)",
            "  [bold]gamble slots <amount>[/bold] — Slot machine, 3x payout (1 in 5 chance)",
            "",
            "[dim]Minimum bet: 5g. Maximum bet: 100g.[/dim]",
        ]

    game_type = parts[0].lower()
    try:
        amount = int(parts[1])
    except ValueError:
        return ["That's not a valid bet. Use a number, like [bold]gamble flip 10[/bold]."]

    if amount < 5:
        return ["Minimum bet is 5 gold. Even Lucky has standards."]
    if amount > 100:
        return ["Maximum bet is 100 gold. Lucky doesn't want to bankrupt you. (That's a lie. He just doesn't have enough gold to cover it.)"]
    if amount > state.inventory.gold:
        return [f"You only have {state.inventory.gold}g. Can't bet what you don't have."]

    state.inventory.gold -= amount
    state.gold_spent += amount
    state.gold_gambled += amount

    if game_type == "flip":
        return _gamble_flip(state, amount)
    elif game_type in ("slots", "slot"):
        return _gamble_slots(state, amount)
    else:
        state.inventory.gold += amount  # Refund
        state.gold_spent -= amount
        state.gold_gambled -= amount
        return [f"Unknown game '{game_type}'. Try [bold]flip[/bold] or [bold]slots[/bold]."]


def _gamble_flip(state: MudState, amount: int) -> list[str]:
    """Coin flip — 50/50 double or nothing."""
    lines = [f"\n[bold]🪙 Coin Flip — {amount}g bet[/bold]"]
    lines.append("Lucky flips the coin high into the air...")

    if random.random() < 0.5:
        winnings = amount * 2
        state.inventory.gold += winnings
        state.gold_won_gambling += winnings
        lines.append(f"[bold green]✨ HEADS! You win {winnings}g![/bold green]")
        lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")
        comment = _buddy_comment(state.party, "shop")
        if comment:
            lines.append(comment)
    else:
        lines.append(f"[bold red]💀 TAILS! You lose {amount}g![/bold red]")
        lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")
        lines.append("[dim]Lucky pockets the gold with practiced efficiency.[/dim]")

    return lines


def _gamble_slots(state: MudState, amount: int) -> list[str]:
    """Slot machine — 1 in 5 for 3x payout, small consolation prizes."""
    symbols = ["🍒", "🔔", "💎", "7️⃣", "🍀", "⭐", "🎯"]
    reels = [random.choice(symbols) for _ in range(3)]
    lines = [f"\n[bold]🎰 Slot Machine — {amount}g bet[/bold]"]
    lines.append(f"  ┃ {reels[0]} ┃ {reels[1]} ┃ {reels[2]} ┃")

    if reels[0] == reels[1] == reels[2]:
        # Jackpot! 5x payout
        winnings = amount * 5
        state.inventory.gold += winnings
        state.gold_won_gambling += winnings
        lines.append(f"[bold green]🎉 JACKPOT! Three {reels[0]}! You win {winnings}g![/bold green]")
        lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        # Two matching — return bet
        state.inventory.gold += amount
        state.gold_won_gambling += amount
        lines.append(f"[yellow]Two matching! You get your {amount}g back.[/yellow]")
        lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")
    else:
        lines.append(f"[red]No match. You lose {amount}g.[/red]")
        lines.append(f"[yellow]Gold: {state.inventory.gold}g[/yellow]")
        lines.append("[dim]Lucky whistles innocently.[/dim]")

    return lines


def _handle_wealth(state: MudState, _arg: str) -> list[str]:
    """Show economy statistics."""
    net = state.inventory.gold
    lines = [
        "\n[bold]💰 Wealth Report[/bold]",
        f"{'─' * 40}",
        f"[yellow]Current Gold: {net}g[/yellow]",
        "",
        "[bold]Earnings:[/bold]",
        f"  Quest rewards: {state.gold_earned}g",
        f"  Gambling wins: {state.gold_won_gambling}g",
        "",
        "[bold]Spending:[/bold]",
        f"  Items purchased: {state.gold_spent - state.gold_gambled}g",
        f"  Gold gambled: {state.gold_gambled}g",
        f"  Tips given: {state.tips_given}g",
        "",
        f"[bold]Bounties completed:[/bold] {state.bounties_completed}",
    ]

    # Fun titles based on wealth
    if net >= 500:
        lines.append("\n[bold magenta]Title: Venture Capitalist[/bold magenta]")
    elif net >= 200:
        lines.append("\n[bold cyan]Title: Senior Engineer (with stock options)[/bold cyan]")
    elif net >= 50:
        lines.append("\n[bold green]Title: Mid-Level (pays rent, barely)[/bold green]")
    elif net >= 10:
        lines.append("\n[bold yellow]Title: Junior Developer[/bold yellow]")
    else:
        lines.append("\n[bold red]Title: Unpaid Intern[/bold red]")

    return lines


def _handle_tip(state: MudState, arg: str) -> list[str]:
    """Tip an NPC for flavor text."""
    room = state.rooms[state.current_room]
    if not arg:
        if room.npcs:
            npc_names = [state.npcs[nid].name for nid in room.npcs if nid in state.npcs]
            return [f"Tip who? NPCs here: {', '.join(npc_names)}. Usage: [bold]tip <name> <amount>[/bold]"]
        return ["There's nobody here to tip."]

    parts = arg.strip().split()
    if len(parts) < 2:
        return ["Usage: [bold]tip <name> <amount>[/bold] (e.g., tip gerald 5)"]

    npc_name = parts[0].lower()
    try:
        tip_amount = int(parts[1])
    except ValueError:
        return ["That's not a valid amount."]

    if tip_amount < 1:
        return ["At least tip 1 gold. Have some dignity."]
    if tip_amount > state.inventory.gold:
        return [f"You only have {state.inventory.gold}g."]

    # Find NPC by name
    target_npc = None
    for nid in room.npcs:
        if nid in state.npcs and state.npcs[nid].name.lower() == npc_name:
            target_npc = state.npcs[nid]
            break

    if not target_npc:
        return [f"There's no '{npc_name}' here to tip."]

    state.inventory.gold -= tip_amount
    state.tips_given += tip_amount

    # Fun responses by NPC
    tip_responses = {
        "sysadmin": f"Gerald pockets the {tip_amount}g without breaking eye contact with his monitors. \"Uptime just went up 0.001%.\"",
        "intern": f"Skyler's eyes go wide. \"{tip_amount} gold?! I'm gonna buy SO many energy drinks!\"",
        "product_manager": f"Brenda accepts the {tip_amount}g and immediately starts a new Jira ticket titled 'Revenue Stream: Tips.'",
        "coffee_machine": f"The Coffee Machine absorbs the {tip_amount}g. Its display reads: 'GRATITUDE.EXE LOADED. ERROR: EMOTION NOT FOUND.'",
        "vendor": f"Dave bites the gold to check if it's real. It is. \"Pleasure doing business.\"",
        "lucky": f"Lucky grins. \"{tip_amount}g? Want to put that on a coin flip instead?\"",
        "rubber_duck_sage": f"The Rubber Duck Sage accepts the {tip_amount}g with a gentle quack. You feel enlightened. Probably.",
        "senior_dev": f"Miriam glances at the {tip_amount}g. \"I don't need gold. I need someone to read the documentation. But thanks.\"",
        "scrum_master": f"Todd writes '{tip_amount}g received' on a sticky note and puts it on the sprint board.",
        "oncall_engineer": f"Marcus looks at the {tip_amount}g with dead eyes. \"Does this mean I can go home?\"",
        "qa_lead": f"Priya examines the {tip_amount}g. \"Is this gold tested? Does it have unit tests? I'm not accepting untested gold.\"",
    }

    response = tip_responses.get(target_npc.id,
        f"{target_npc.name} accepts the {tip_amount}g with a nod.")

    return [
        f"[yellow]-{tip_amount}g[/yellow]",
        f"[green]{response}[/green]",
        f"[yellow]Gold: {state.inventory.gold}g[/yellow]",
    ]


# Bounty definitions (repeatable mini-quests)
BOUNTIES = [
    {"id": "bounty_explore", "name": "Explorer's Survey", "description": "Visit 5 different rooms", "goal_type": "rooms_visited", "goal_count": 5, "reward": 15},
    {"id": "bounty_fighter", "name": "Bug Bounty (Literal)", "description": "Defeat 3 hostile NPCs", "goal_type": "npcs_defeated", "goal_count": 3, "reward": 25},
    {"id": "bounty_talker", "name": "Social Networking", "description": "Talk to 5 NPCs", "goal_type": "npcs_talked", "goal_count": 5, "reward": 10},
    {"id": "bounty_collector", "name": "Hoarder's Delight", "description": "Collect 5 items", "goal_type": "items_collected", "goal_count": 5, "reward": 20},
    {"id": "bounty_tourist", "name": "Grand Tour", "description": "Visit 12 different rooms", "goal_type": "rooms_visited", "goal_count": 12, "reward": 40},
]


def _handle_bounty(state: MudState, arg: str) -> list[str]:
    """View and claim bounty rewards."""
    lines = [
        "\n[bold]📋 Bounty Board[/bold]",
        f"{'─' * 40}",
        "[dim]Complete objectives to earn gold rewards.[/dim]",
        "",
    ]

    for bounty in BOUNTIES:
        current = getattr(state, bounty["goal_type"], 0)
        goal = bounty["goal_count"]
        done = current >= goal
        status = "[bold green]✅ COMPLETE[/bold green]" if done else f"[dim]{current}/{goal}[/dim]"

        lines.append(f"  [bold]{bounty['name']}[/bold] — {bounty['description']}")
        lines.append(f"    Progress: {status}  |  Reward: [yellow]{bounty['reward']}g[/yellow]")

    # Check if claiming
    if arg.strip().lower() in ("claim", "collect"):
        claimed = 0
        for bounty in BOUNTIES:
            bid = bounty["id"]
            current = getattr(state, bounty["goal_type"], 0)
            if current >= bounty["goal_count"]:
                # Check if already claimed (use a set on the state)
                if not hasattr(state, '_bounties_claimed'):
                    state._bounties_claimed = set()
                if bid not in state._bounties_claimed:
                    state._bounties_claimed.add(bid)
                    state.inventory.gold += bounty["reward"]
                    state.gold_earned += bounty["reward"]
                    state.bounties_completed += 1
                    claimed += bounty["reward"]
                    lines.append(f"\n[bold green]Claimed: {bounty['name']} — +{bounty['reward']}g![/bold green]")

        if claimed:
            lines.append(f"\n[yellow]Total claimed: +{claimed}g | Gold: {state.inventory.gold}g[/yellow]")
        else:
            lines.append("\n[dim]No unclaimed bounties. Complete more objectives![/dim]")
    else:
        lines.append(f"\n[dim]Type [bold]bounty claim[/bold] to collect completed bounties.[/dim]")

    return lines


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
    "sell": _handle_sell,
    "lore": _handle_lore,
    "note": _handle_note,
    "rate": _handle_rate,
    "notes": _handle_notes,
    "bloodstain": _handle_bloodstain,
    "quest": _handle_quest,
    "map": _handle_map,
    "wait": _handle_wait,
    "rumors": _handle_rumors,
    "help": _handle_help,
    "attack": _handle_attack,
    "flee": _handle_flee,
    "gamble": _handle_gamble,
    "wealth": _handle_wealth,
    "tip": _handle_tip,
    "bounty": _handle_bounty,
}


def process_command(state: MudState, raw_input: str) -> list[str]:
    """Process a player command and return output lines."""
    cmd, arg = parse_command(raw_input)

    if not cmd:
        return ["Type [bold]help[/bold] for a list of commands."]

    # In combat, restrict commands
    if state.combat and state.combat.active:
        # Allow numbered responses during negotiation
        if state.negotiation and cmd.isdigit():
            return _handle_negotiate_response(state, int(cmd))
        if cmd not in ("attack", "flee", "use", "inventory", "help", "talk"):
            return ["You're in combat! [bold]attack[/bold], [bold]talk[/bold], [bold]use[/bold] <item>, or [bold]flee[/bold]."]

    # Handle numbered responses during negotiation (outside combat too)
    if state.negotiation and cmd.isdigit():
        return _handle_negotiate_response(state, int(cmd))

    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        result = handler(state, arg)
        # Random world events after non-meta commands
        if cmd not in ("help", "inventory", "quest", "map", "lore", "note", "notes", "rate", "bloodstain") and not state.combat:
            event = _maybe_world_event()
            if event:
                result.append(f"\n{event}")
        return result

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
            "gold_spent": state.gold_spent,
            "gold_gambled": state.gold_gambled,
            "bounties_completed": state.bounties_completed,
            "turns": state.turns,
        },
        xp_earned=xp,
        mood_delta=state.quests_completed * 3 + state.npcs_defeated * 2,
    )
