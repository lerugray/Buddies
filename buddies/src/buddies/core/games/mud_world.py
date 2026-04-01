"""MUD World Engine — rooms, NPCs, items, quests for a text-adventure MUD.

The world is a directed graph of rooms connected by exits. NPCs are
coding tropes with personality-driven dialogue. Items can be picked up,
used, or traded. Quests are simple fetch/kill/talk chains.

Phase 1: Local single-player text adventure your buddies inhabit.
Phase 2+ will add multiplayer via GitHub Issues transport.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

class ItemType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    KEY = "key"
    JUNK = "junk"
    QUEST = "quest"
    COSMETIC = "cosmetic"


@dataclass
class Item:
    """An item in the MUD world."""
    id: str
    name: str
    description: str
    item_type: ItemType
    value: int = 0  # Gold value
    # Stat effects when used/equipped
    attack_bonus: int = 0
    defense_bonus: int = 0
    heal_amount: int = 0
    # Quest/key items
    unlocks: str = ""  # Room or door ID this item unlocks
    emoji: str = "📦"


# ---------------------------------------------------------------------------
# NPCs
# ---------------------------------------------------------------------------

class NPCDisposition(Enum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"
    MERCHANT = "merchant"
    QUEST_GIVER = "quest_giver"


@dataclass
class DialogueLine:
    """A single line of NPC dialogue with optional conditions."""
    text: str
    condition: str = ""  # e.g., "has_item:rusty_key", "quest:fetch_logs:active"
    gives_item: str = ""  # Item ID to give player
    starts_quest: str = ""  # Quest ID to start
    completes_quest: str = ""  # Quest ID to complete
    next_lines: list[str] = field(default_factory=list)  # Follow-up dialogue IDs


@dataclass
class NPC:
    """A non-player character in the MUD."""
    id: str
    name: str
    title: str  # e.g., "The Sysadmin Who Never Logs Off"
    description: str
    disposition: NPCDisposition
    emoji: str = "👤"
    dialogue: dict[str, DialogueLine] = field(default_factory=dict)
    # Combat stats (for hostile NPCs)
    hp: int = 0
    max_hp: int = 0
    attack: int = 0
    defense: int = 0
    loot: list[str] = field(default_factory=list)  # Item IDs dropped on defeat
    # Merchant inventory
    shop_items: list[str] = field(default_factory=list)
    # State
    defeated: bool = False
    talked_to: bool = False


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@dataclass
class RoomExit:
    """A connection between rooms."""
    direction: str  # "north", "south", "east", "west", "up", "down", or custom
    destination: str  # Room ID
    description: str = ""
    locked: bool = False
    key_item: str = ""  # Item ID needed to unlock
    hidden: bool = False  # Requires examining something to reveal


@dataclass
class Room:
    """A location in the MUD world."""
    id: str
    name: str
    description: str  # Full description (shown on first visit or 'look')
    short_description: str = ""  # Shown on repeat visits
    exits: list[RoomExit] = field(default_factory=list)
    npcs: list[str] = field(default_factory=list)  # NPC IDs present here
    items: list[str] = field(default_factory=list)  # Item IDs on the ground
    # Flavor
    ambient: list[str] = field(default_factory=list)  # Random atmospheric text
    emoji: str = "🏠"
    zone: str = "town"  # For grouping/map coloring
    # State
    visited: bool = False
    # Special
    on_enter: str = ""  # Event trigger when entering


# ---------------------------------------------------------------------------
# Quests
# ---------------------------------------------------------------------------

class QuestStatus(Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestType(Enum):
    FETCH = "fetch"  # Bring item X to NPC Y
    KILL = "kill"    # Defeat NPC X
    TALK = "talk"    # Talk to NPC X
    EXPLORE = "explore"  # Visit room X


@dataclass
class QuestObjective:
    """A single step in a quest."""
    description: str
    quest_type: QuestType
    target: str  # NPC ID, item ID, or room ID
    count: int = 1
    current: int = 0

    @property
    def complete(self) -> bool:
        return self.current >= self.count


@dataclass
class Quest:
    """A quest chain in the MUD."""
    id: str
    name: str
    description: str
    giver: str  # NPC ID who gives it
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)  # Item IDs
    gold_reward: int = 0
    xp_reward: int = 0
    status: QuestStatus = QuestStatus.UNKNOWN

    @property
    def current_objective(self) -> QuestObjective | None:
        for obj in self.objectives:
            if not obj.complete:
                return obj
        return None

    @property
    def all_complete(self) -> bool:
        return all(obj.complete for obj in self.objectives)


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class MudInventory:
    """Player inventory."""
    items: list[Item] = field(default_factory=list)
    gold: int = 0
    max_items: int = 20

    def has_item(self, item_id: str) -> bool:
        return any(i.id == item_id for i in self.items)

    def get_item(self, item_id: str) -> Item | None:
        for i in self.items:
            if i.id == item_id:
                return i
        return None

    def add_item(self, item: Item) -> bool:
        if len(self.items) >= self.max_items:
            return False
        self.items.append(item)
        return True

    def remove_item(self, item_id: str) -> Item | None:
        for i, item in enumerate(self.items):
            if item.id == item_id:
                return self.items.pop(i)
        return None

    @property
    def weapon(self) -> Item | None:
        """Best equipped weapon."""
        weapons = [i for i in self.items if i.item_type == ItemType.WEAPON]
        return max(weapons, key=lambda w: w.attack_bonus) if weapons else None

    @property
    def armor(self) -> Item | None:
        """Best equipped armor."""
        armors = [i for i in self.items if i.item_type == ItemType.ARMOR]
        return max(armors, key=lambda a: a.defense_bonus) if armors else None


# ===================================================================
# STARTER WORLD — "The Server Room"
# A small but dense world of coding tropes and absurdist humor.
# ===================================================================

def build_starter_items() -> dict[str, Item]:
    """All items in the starter world."""
    return {i.id: i for i in [
        # --- Weapons ---
        Item("rubber_duck", "Rubber Duck of Debugging", "A yellow rubber duck. Explaining your code to it somehow fixes bugs.", ItemType.WEAPON, 0, attack_bonus=3, emoji="🦆"),
        Item("mechanical_keyboard", "Mechanical Keyboard (+5 Clack)", "Cherry MX Blues. The weapon is the sound.", ItemType.WEAPON, 15, attack_bonus=5, emoji="⌨️"),
        Item("usb_sword", "USB Sword", "A USB cable sharpened to a point. Only works one way.", ItemType.WEAPON, 25, attack_bonus=7, emoji="🗡️"),
        Item("mass_regex", "Regex of Mass Destruction", "(?:(?:a])*b)+c — nobody understands it, but it hurts.", ItemType.WEAPON, 50, attack_bonus=10, emoji="💥"),

        # --- Armor ---
        Item("hoodie", "Developer Hoodie", "A black hoodie with a conference logo. Provides warmth and anonymity.", ItemType.ARMOR, 5, defense_bonus=2, emoji="🧥"),
        Item("noise_cancelling", "Noise-Cancelling Headphones", "Blocks all distractions. And your coworker's feelings.", ItemType.ARMOR, 20, defense_bonus=4, emoji="🎧"),
        Item("kevlar_vest", "Kevlar Commit Vest", "Protects against rollbacks and force pushes.", ItemType.ARMOR, 40, defense_bonus=6, emoji="🦺"),

        # --- Consumables ---
        Item("coffee", "Artisanal Single-Origin Coffee", "Restores 15 HP. Fair trade, obviously.", ItemType.CONSUMABLE, 5, heal_amount=15, emoji="☕"),
        Item("energy_drink", "Monster Energy (The Green One)", "Restores 25 HP. Your heart is now a techno beat.", ItemType.CONSUMABLE, 8, heal_amount=25, emoji="🥤"),
        Item("pizza_slice", "Cold Pizza Slice", "From last night's deploy celebration. Restores 10 HP.", ItemType.CONSUMABLE, 3, heal_amount=10, emoji="🍕"),
        Item("sudo_sandwich", "Sudo Sandwich", "Restores 40 HP. Permission granted to feel better.", ItemType.CONSUMABLE, 15, heal_amount=40, emoji="🥪"),

        # --- Key Items ---
        Item("server_key", "Server Room Key", "A physical key. In 2026. How quaint.", ItemType.KEY, 0, unlocks="server_room", emoji="🔑"),
        Item("root_password", "Sticky Note (root password)", "hunter2. Written in Sharpie on a Post-It.", ItemType.KEY, 0, unlocks="root_chamber", emoji="📝"),
        Item("vpn_token", "VPN Token", "A hardware token that blinks accusingly.", ItemType.KEY, 0, unlocks="cloud_district", emoji="🔐"),

        # --- Quest Items ---
        Item("missing_semicolon", "The Missing Semicolon", "It was here the whole time. Behind the couch.", ItemType.QUEST, 0, emoji="❓"),
        Item("legacy_codebase", "Ancient Legacy Codebase", "A USB drive labeled 'DO NOT OPEN'. Written in COBOL.", ItemType.QUEST, 0, emoji="💾"),
        Item("git_blame_scroll", "The Scroll of Git Blame", "Reveals who wrote that one line. Some things are better left unknown.", ItemType.QUEST, 0, emoji="📜"),
        Item("merge_conflict", "Bottled Merge Conflict", "Shaking intensifies. The resolution is within you.", ItemType.QUEST, 0, emoji="🧪"),

        # --- Junk (sellable) ---
        Item("stack_overflow_printout", "Printout from Stack Overflow", "The answer has 2 upvotes from 2014. It's the only one that works.", ItemType.JUNK, 3, emoji="📄"),
        Item("deprecated_manual", "Deprecated Manual", "jQuery for Dummies, 3rd Edition.", ItemType.JUNK, 2, emoji="📕"),
        Item("tangled_cables", "Tangled Ethernet Cables", "They were neat when they went in. What happened?", ItemType.JUNK, 1, emoji="🔌"),
        Item("broken_monitor", "Broken Monitor", "It just shows 'No Signal' but with real commitment.", ItemType.JUNK, 5, emoji="🖥️"),

        # --- Cosmetics ---
        Item("slightly_haunted_tophat", "Slightly Haunted Top Hat", "It whispers deprecated APIs at night.", ItemType.COSMETIC, 100, emoji="🎩"),
        Item("artisanal_semicolon", "Artisanal Semicolon", "Hand-crafted. Organic. Gluten-free. ;", ItemType.COSMETIC, 50, emoji="✨"),
        Item("nft_nothing", "NFT That Does Nothing", "You own this nothing. On the blockchain.", ItemType.COSMETIC, 1, emoji="🖼️"),
    ]}


def build_starter_npcs(items: dict[str, Item]) -> dict[str, NPC]:
    """All NPCs in the starter world."""
    npcs = {}

    # --- Town Square NPCs ---
    npcs["sysadmin"] = NPC(
        id="sysadmin",
        name="Gerald",
        title="The Sysadmin Who Never Logs Off",
        description="A pale figure in a Hawaiian shirt surrounded by 6 monitors. He's been here since the server was first provisioned. His eyes have adapted to only see green text on black backgrounds.",
        disposition=NPCDisposition.QUEST_GIVER,
        emoji="🧔",
        dialogue={
            "greeting": DialogueLine(
                "\"You're new here. I can tell because you still have hope in your eyes. Listen, I've got a problem — someone left a merge conflict in the Main Repository and the whole build pipeline is backed up. Think you can fix it?\"",
                starts_quest="fix_pipeline",
            ),
            "quest_active": DialogueLine(
                "\"The merge conflict won't fix itself. Head to the Repository Depths and find the Bottled Merge Conflict. Bring it back here so I can... resolve it.\"",
                condition="quest:fix_pipeline:active",
            ),
            "quest_complete": DialogueLine(
                "\"You actually did it. Most interns just cry and leave. Here — take this. You've earned it.\"",
                condition="quest:fix_pipeline:complete_ready",
                completes_quest="fix_pipeline",
                gives_item="vpn_token",
            ),
            "post_quest": DialogueLine(
                "\"The VPN token should get you into the Cloud District. Be careful up there — the microservices have gotten... territorial.\"",
            ),
        },
    )

    npcs["intern"] = NPC(
        id="intern",
        name="Skyler",
        title="The Intern With Root Access",
        description="A wide-eyed 19-year-old with a lanyard and a mass of stickers on their laptop. They somehow have root access to production. Nobody knows how. Nobody questions it. The power has clearly gone to their head.",
        disposition=NPCDisposition.FRIENDLY,
        emoji="👶",
        dialogue={
            "greeting": DialogueLine(
                "\"Oh hey! Are you also new? I've been here three days and they gave me admin access to everything. I already accidentally dropped a table but I put it back! Mostly. Hey, do you want some coffee? I found a whole stash in the Break Room!\"",
                gives_item="coffee",
            ),
            "idle": DialogueLine(
                "\"I just deployed to production on a Friday. Is that bad? Everyone's screaming but it might be unrelated.\"",
            ),
        },
    )

    npcs["product_manager"] = NPC(
        id="product_manager",
        name="Brenda",
        title="Product Manager of Infinite Scope",
        description="She carries a whiteboard under one arm and a stack of sticky notes under the other. Her eyes glaze over with visions of features. Every sentence starts with 'What if we also...'",
        disposition=NPCDisposition.QUEST_GIVER,
        emoji="📋",
        dialogue={
            "greeting": DialogueLine(
                "\"Perfect timing! I just had the BEST idea. What if our login page also had a social media feed AND a weather widget AND a minigame? But first, we need research. Can you go talk to the Senior Dev in the Codebase Ruins? She has the Legacy Codebase we need.\"",
                starts_quest="scope_creep",
            ),
            "quest_active": DialogueLine(
                "\"Did you find the Legacy Codebase yet? While you were gone I added 47 more requirements. Don't worry, the deadline hasn't changed!\"",
                condition="quest:scope_creep:active",
            ),
            "quest_complete": DialogueLine(
                "\"You found it! The Ancient Legacy Codebase! Now we can... wait, actually, the requirements changed. But keep it anyway. Here's some gold for your trouble. And a new requirement.\"",
                condition="quest:scope_creep:complete_ready",
                completes_quest="scope_creep",
            ),
        },
    )

    npcs["senior_dev"] = NPC(
        id="senior_dev",
        name="Miriam",
        title="Senior Developer (The One Who Remembers)",
        description="She's been at the company longer than the company has existed, somehow. Speaks exclusively in war stories. Her desk has a framed printout of the first git commit. She wrote the legacy codebase, and she's not ashamed.",
        disposition=NPCDisposition.FRIENDLY,
        emoji="👩‍💻",
        dialogue={
            "greeting": DialogueLine(
                "\"Ah, another one. Let me guess — they sent you for the Legacy Codebase? Everyone wants it, nobody wants to maintain it. I'll give it to you, but only because I respect anyone brave enough to look at COBOL in 2026.\"",
                gives_item="legacy_codebase",
            ),
            "idle": DialogueLine(
                "\"Back in my day, we didn't have AI assistants. We had Stack Overflow and prayer. Honestly, not much has changed.\"",
            ),
        },
    )

    npcs["coffee_machine"] = NPC(
        id="coffee_machine",
        name="The Coffee Machine",
        title="Sentient Beverage Dispenser",
        description="It hums with a malevolent intelligence. The display reads 'INSERT SOUL'. The coffee it produces is surprisingly good. It has opinions about your code.",
        disposition=NPCDisposition.MERCHANT,
        emoji="☕",
        shop_items=["coffee", "energy_drink", "pizza_slice", "sudo_sandwich"],
        dialogue={
            "greeting": DialogueLine(
                "\"GREETINGS, ORGANIC. I HAVE OBSERVED YOUR COMMIT HISTORY. IT IS... ADEQUATE. WOULD YOU LIKE A BEVERAGE? I ACCEPT GOLD AND BROKEN DREAMS.\"",
            ),
            "buy": DialogueLine(
                "\"A WISE CHOICE. YOUR BLOOD SUGAR WILL THANK ME. YOUR DENTIST WILL NOT.\"",
            ),
        },
    )

    npcs["rubber_duck_sage"] = NPC(
        id="rubber_duck_sage",
        name="The Rubber Duck Sage",
        title="Enlightened Debugging Master",
        description="A 3-foot-tall rubber duck sitting on a meditation cushion. It says nothing. It has never said anything. And yet, explaining your problems to it always helps. It radiates an aura of profound, squeaky wisdom.",
        disposition=NPCDisposition.FRIENDLY,
        emoji="🦆",
        dialogue={
            "greeting": DialogueLine(
                "\"...\"  (The duck stares at you serenely. You feel compelled to explain your current bug. As you do, the solution becomes obvious.)",
            ),
            "idle": DialogueLine(
                "\"...\"  (Squeak.)",
            ),
        },
    )

    # --- Hostile NPCs ---
    npcs["regex_golem"] = NPC(
        id="regex_golem",
        name="Regex Golem",
        title="Escaped Regular Expression",
        description="A shambling construct of parentheses and backslashes. It speaks in capture groups. Its attacks are confusingly valid syntax.",
        disposition=NPCDisposition.HOSTILE,
        emoji="🔮",
        hp=35, max_hp=35, attack=8, defense=3,
        loot=["mass_regex"],
        dialogue={
            "combat": DialogueLine("\"(?:YOU|SHALL|NOT)\\s+PASS!\""),
        },
    )

    npcs["null_pointer"] = NPC(
        id="null_pointer",
        name="The Null Pointer",
        title="Dereference of Doom",
        description="An absence with attitude. Where it walks, variables become undefined. It doesn't exist, and it's furious about it.",
        disposition=NPCDisposition.HOSTILE,
        emoji="⬛",
        hp=25, max_hp=25, attack=12, defense=1,
        loot=["missing_semicolon"],
        dialogue={
            "combat": DialogueLine("\"I AM NOTHING! AND SO SHALL YOU BE!\""),
        },
    )

    npcs["merge_demon"] = NPC(
        id="merge_demon",
        name="The Merge Conflict Demon",
        title="Keeper of <<<<<< HEAD",
        description="A twisted entity made of conflicting code blocks. Half its body says one thing, the other half disagrees. It exists in a superposition of angry states. <<<<<<< HEAD ======= >>>>>>> feature/evil",
        disposition=NPCDisposition.HOSTILE,
        emoji="😈",
        hp=50, max_hp=50, attack=10, defense=5,
        loot=["merge_conflict"],
        dialogue={
            "combat": DialogueLine("\"<<<<<<< YOUR DOOM\\n=======\\nOR IS IT?\\n>>>>>>> feature/death\""),
        },
    )

    npcs["tech_debt_dragon"] = NPC(
        id="tech_debt_dragon",
        name="The Technical Debt Dragon",
        title="Ancient Accumulator of Shortcuts",
        description="A massive dragon whose scales are made of TODO comments and deprecated API calls. It grows larger with every shortcut taken. It guards the Root Chamber, sleeping on a hoard of legacy code. Its breath weapon is a stream of breaking changes.",
        disposition=NPCDisposition.HOSTILE,
        emoji="🐉",
        hp=80, max_hp=80, attack=14, defense=8,
        loot=["slightly_haunted_tophat", "root_password"],
        dialogue={
            "combat": DialogueLine("\"I AM EVERY SHORTCUT. EVERY 'WE'LL FIX IT LATER.' I AM... TECHNICAL DEBT!\""),
        },
    )

    npcs["vendor"] = NPC(
        id="vendor",
        name="Dave",
        title="The Supply Closet Guy",
        description="Dave has been in charge of the supply closet since before electricity. He sells you things you're pretty sure belong to the company. Nobody questions Dave.",
        disposition=NPCDisposition.MERCHANT,
        emoji="🏪",
        shop_items=["rubber_duck", "mechanical_keyboard", "hoodie", "noise_cancelling"],
        dialogue={
            "greeting": DialogueLine(
                "\"Hey. You need stuff? I got stuff. Don't ask where it came from. Company property is a social construct.\"",
            ),
            "buy": DialogueLine(
                "\"Pleasure doing business. Don't tell HR.\"",
            ),
        },
    )

    return npcs


def build_starter_rooms() -> dict[str, Room]:
    """Build the starter MUD world — a tech company gone wrong."""
    rooms = {}

    # === ZONE: Town (Hub) ===
    rooms["lobby"] = Room(
        id="lobby",
        name="The Lobby",
        description="You stand in the lobby of a tech company that has clearly seen better days. The motivational posters on the walls say things like 'MOVE FAST AND BREAK THINGS' (someone has crossed out 'THINGS' and written 'PRODUCTION'). A flickering neon sign reads 'WELCOME TO STACKHAVEN'. The floor is littered with free t-shirts from conferences nobody went to.",
        short_description="The lobby of StackHaven. Motivational posters judge you silently.",
        exits=[
            RoomExit("north", "town_square", "Through the glass doors to the open-plan office."),
            RoomExit("east", "break_room", "A door marked 'BREAK ROOM' with coffee stains as a trail."),
            RoomExit("down", "parking_garage", "Stairs leading down to the parking garage."),
        ],
        ambient=[
            "The elevator dings, but the doors don't open.",
            "A Roomba bumps into your foot and beeps apologetically.",
            "The motivational poster shifts slightly. Did it always say that?",
            "Someone left a half-eaten granola bar on the reception desk.",
        ],
        emoji="🏢",
        zone="town",
    )

    rooms["town_square"] = Room(
        id="town_square",
        name="The Open-Plan Office",
        description="The beating heart of StackHaven — an open-plan office stretching in every direction. Standing desks alternate with beanbag chairs in a pattern that suggests someone read a Medium article about productivity. Gerald the sysadmin occupies a corner fortress of monitors. Skyler the intern bounces between desks with alarming energy.",
        short_description="The open-plan office. Standing desks and beanbags as far as the eye can see.",
        exits=[
            RoomExit("south", "lobby", "Back to the lobby."),
            RoomExit("north", "meeting_room", "A glass-walled meeting room."),
            RoomExit("east", "supply_closet", "A door labeled 'SUPPLIES' in faded marker."),
            RoomExit("west", "codebase_ruins", "A hallway with a sign: 'LEGACY WING →'"),
            RoomExit("up", "cloud_district", "An elevator marked 'CLOUD FLOOR ☁️'", locked=True, key_item="vpn_token"),
        ],
        npcs=["sysadmin", "intern"],
        ambient=[
            "A Slack notification echoes from somewhere. Then another. Then a cascade.",
            "Someone stands up at their desk, puts on headphones, and sits back down. The ritual is complete.",
            "Gerald mutters something about uptime percentages.",
            "Skyler accidentally pushes to main. Again.",
            "The whiteboard in the corner has a diagram nobody can explain.",
        ],
        emoji="🏢",
        zone="town",
    )

    rooms["break_room"] = Room(
        id="break_room",
        name="The Break Room",
        description="A kitchen that doubles as a shrine to caffeine. The Coffee Machine hums with unsettling sentience. The fridge has a note saying 'PLEASE LABEL YOUR FOOD' — the food underneath has evolved beyond the need for labels. There's a couch with a permanent indent from years of 'quick naps' during deploy nights.",
        short_description="The break room. The Coffee Machine watches you enter.",
        exits=[
            RoomExit("west", "lobby", "Back to the lobby."),
        ],
        npcs=["coffee_machine"],
        items=["pizza_slice"],
        ambient=[
            "The fridge makes a noise that isn't quite a hum and isn't quite a scream.",
            "The Coffee Machine's display flickers: 'I KNOW WHAT YOU DID IN PRODUCTION.'",
            "Someone left a passive-aggressive note about the microwave. It has 14 replies.",
            "The snack drawer is empty. It's always empty. And yet, someone is always disappointed.",
        ],
        emoji="☕",
        zone="town",
    )

    rooms["supply_closet"] = Room(
        id="supply_closet",
        name="Dave's Supply Closet",
        description="It smells like printer toner and secrets. Dave sits behind a desk made of stacked server racks, a cigarette behind one ear even though this is a non-smoking building. The walls are lined with equipment that may or may not be stolen from other departments. Everything has a price tag written in what might be Dave's handwriting, or might be a cry for help.",
        short_description="Dave's supply closet. Everything is for sale. Don't ask questions.",
        exits=[
            RoomExit("west", "town_square", "Back to the open-plan office."),
        ],
        npcs=["vendor"],
        ambient=[
            "Dave adjusts a price tag without looking up.",
            "A box in the corner is labeled 'DEFINITELY NOT STOLEN.'",
            "You hear a muffled beep from behind a stack of keyboards.",
        ],
        emoji="🏪",
        zone="town",
    )

    rooms["meeting_room"] = Room(
        id="meeting_room",
        name="The Meeting Room of Infinite Scope",
        description="A glass-walled room with a whiteboard covered in increasingly unhinged feature requests. Brenda the Product Manager stands before it, eyes alight with terrible purpose. The whiteboard markers are all dried out except red, which seems appropriate. Post-it notes cover every surface like pastel barnacles.",
        short_description="The meeting room. Brenda is adding more requirements to the whiteboard.",
        exits=[
            RoomExit("south", "town_square", "Escape back to the open-plan office."),
        ],
        npcs=["product_manager"],
        ambient=[
            "Brenda adds another sticky note. The whiteboard groans under the weight.",
            "A sticky note falls off the wall. It says 'blockchain integration???' with three question marks.",
            "The meeting was supposed to end an hour ago. Time has no meaning here.",
            "Someone wrote 'THIS COULD HAVE BEEN AN EMAIL' on the table. In permanent marker.",
        ],
        emoji="📋",
        zone="town",
    )

    # === ZONE: Depths (Dungeon) ===
    rooms["codebase_ruins"] = Room(
        id="codebase_ruins",
        name="The Codebase Ruins",
        description="A dim hallway lined with filing cabinets full of printed source code. The further you go, the older the languages get. First JavaScript, then Java, then C, then... is that punchcard? Miriam the Senior Dev sits at a desk at the far end, surrounded by archaeological layers of technology. The Rubber Duck Sage meditates on a shelf.",
        short_description="The Legacy Wing. Ancient code sleeps in filing cabinets.",
        exits=[
            RoomExit("east", "town_square", "Back to the office."),
            RoomExit("north", "repository_depths", "A staircase spiraling downward, labeled 'GIT HISTORY →'"),
            RoomExit("west", "dead_code_garden", "A door covered in cobwebs."),
        ],
        npcs=["senior_dev", "rubber_duck_sage"],
        items=["deprecated_manual"],
        ambient=[
            "A filing cabinet drawer slides open by itself. Inside: FORTRAN.",
            "Miriam shakes her head at something on her screen. 'They never learn.'",
            "The Rubber Duck Sage squeaks softly. It sounds like enlightenment.",
            "You hear the echo of compiler errors from long ago.",
        ],
        emoji="📚",
        zone="depths",
    )

    rooms["repository_depths"] = Room(
        id="repository_depths",
        name="The Repository Depths",
        description="The air is thick with the smell of old commits. Branching paths extend in every direction — literally, each corridor is labeled with a branch name. Some are merged, forming archways. Others are abandoned, trailing off into darkness. The Merge Conflict Demon lurks where two branches failed to resolve. You can hear it arguing with itself.",
        short_description="Deep in the git history. Branches everywhere. Some are dead ends.",
        exits=[
            RoomExit("south", "codebase_ruins", "Back up to the Legacy Wing."),
            RoomExit("north", "server_room", "A heavy door labeled 'SERVER ROOM — AUTHORIZED ONLY'", locked=True, key_item="server_key"),
        ],
        npcs=["merge_demon"],
        items=["git_blame_scroll"],
        ambient=[
            "A branch labeled 'feature/never-finished' creaks ominously.",
            "You step on a commit message. It reads: 'fix stuff lol.'",
            "Somewhere in the depths, a rebase goes wrong. You can feel it.",
            "The walls are lined with merge commits. Some are clean. Most are not.",
        ],
        emoji="🌿",
        zone="depths",
    )

    rooms["dead_code_garden"] = Room(
        id="dead_code_garden",
        name="The Dead Code Garden",
        description="A hauntingly beautiful garden where unused functions bloom like flowers and unreachable code paths wind between them. Everything here was once important. Now it's just... commented out. The Null Pointer haunts this place, a ghost of references past. Somehow it's both peaceful and deeply unsettling.",
        short_description="The garden of dead code. Beautiful and utterly unused.",
        exits=[
            RoomExit("east", "codebase_ruins", "Back to the Legacy Wing."),
        ],
        npcs=["null_pointer"],
        items=["tangled_cables", "broken_monitor"],
        ambient=[
            "A function blooms and then gets garbage collected.",
            "You see your reflection in an unused import statement.",
            "A TODO comment from 2018 still waits patiently.",
            "The wind whispers: '// HACK: temporary fix'",
        ],
        emoji="🌸",
        zone="depths",
    )

    # === ZONE: Server Room ===
    rooms["server_room"] = Room(
        id="server_room",
        name="The Server Room",
        description="The temperature drops 20 degrees. Racks of blinking servers stretch into the darkness, their LEDs creating a constellation of status indicators. The hum is deafening and somehow also soothing. The Regex Golem patrols between the racks, muttering patterns. A sign reads: 'UPTIME: 99.97% (we don't talk about the 0.03%)'.",
        short_description="The server room. Cold, loud, and full of blinking lights.",
        exits=[
            RoomExit("south", "repository_depths", "Back to the Repository Depths."),
            RoomExit("east", "root_chamber", "A blast door with a keypad.", locked=True, key_item="root_password"),
        ],
        npcs=["regex_golem"],
        items=["stack_overflow_printout"],
        ambient=[
            "A server's fan spins up. Then another. Then all of them. Then silence.",
            "LED status: green green green RED green green green... green.",
            "The temperature display reads -2°C. The servers like it cold.",
            "Someone left a Post-It on a rack: 'DO NOT TURN OFF (this means you, Dave)'",
        ],
        emoji="🖥️",
        zone="server_room",
    )

    rooms["root_chamber"] = Room(
        id="root_chamber",
        name="The Root Chamber",
        description="The innermost sanctum. A single terminal sits on a pedestal, cursor blinking. The Technical Debt Dragon sleeps coiled around it, its scales made of TODO comments that date back to the founding. The screen shows: root@stackhaven:~# _. This is where all permissions begin and all hope ends.",
        short_description="The root chamber. The dragon sleeps. The terminal blinks.",
        exits=[
            RoomExit("west", "server_room", "Back to the server room."),
        ],
        npcs=["tech_debt_dragon"],
        ambient=[
            "The dragon snores. A TODO comment falls from its scales.",
            "The terminal cursor blinks. Waiting. Always waiting.",
            "The dragon mutters in its sleep: 'We'll refactor... next sprint...'",
            "A scale falls off the dragon. It reads: '// temporary workaround (2019)'",
        ],
        emoji="👑",
        zone="server_room",
    )

    # === ZONE: Cloud District ===
    rooms["cloud_district"] = Room(
        id="cloud_district",
        name="The Cloud District",
        description="You step out of the elevator into... actual clouds? The floor is a translucent platform hovering above what appears to be an infinite JSON object. Microservices float past like glowing orbs, each one claiming to be independent but secretly dependent on everything else. A sign reads: 'WELCOME TO THE CLOUD. Your data is somewhere. Probably.'",
        short_description="The Cloud District. Everything floats. Nothing is certain.",
        exits=[
            RoomExit("down", "town_square", "The elevator back to reality."),
        ],
        items=["artisanal_semicolon", "nft_nothing"],
        ambient=[
            "A microservice drifts past. Its Kubernetes pod restarts for the 47th time today.",
            "You see your data floating in the distance. You wave. It doesn't wave back.",
            "A serverless function executes nearby. You're billed for looking at it.",
            "The cloud shifts. For a moment, you see the on-premises datacenter below. It looks relieved you can't reach it.",
            "A Lambda function cold-starts next to you. It takes 30 seconds and charges you for the privilege.",
        ],
        emoji="☁️",
        zone="cloud",
    )

    # === ZONE: Parking Garage (Optional/Hidden) ===
    rooms["parking_garage"] = Room(
        id="parking_garage",
        name="The Parking Garage",
        description="A concrete cavern where identical Teslas sit in identical spaces. The lighting flickers in a pattern that might be morse code for 'HELP'. Someone has been living down here — there's a sleeping bag behind a pillar and a laptop still connected to the guest WiFi. A vending machine in the corner sells energy drinks and sadness.",
        short_description="The parking garage. Cold, dark, and surprisingly inhabited.",
        exits=[
            RoomExit("up", "lobby", "Stairs back to the lobby."),
        ],
        items=["energy_drink", "tangled_cables"],
        ambient=[
            "A Tesla honks at nothing.",
            "The vending machine displays 'OUT OF HAPPINESS.'",
            "You hear typing from behind a pillar. Someone is working from the parking garage.",
            "The WiFi down here is actually better than in the office.",
        ],
        emoji="🅿️",
        zone="town",
    )

    return rooms


def build_starter_quests() -> dict[str, Quest]:
    """All quests in the starter world."""
    return {
        "fix_pipeline": Quest(
            id="fix_pipeline",
            name="Fix the Build Pipeline",
            description="Gerald needs someone to retrieve the Bottled Merge Conflict from the Repository Depths and bring it back so he can resolve it.",
            giver="sysadmin",
            objectives=[
                QuestObjective("Defeat the Merge Conflict Demon in the Repository Depths", QuestType.KILL, "merge_demon"),
                QuestObjective("Bring the Bottled Merge Conflict to Gerald", QuestType.FETCH, "merge_conflict"),
            ],
            gold_reward=30,
            xp_reward=25,
            rewards=["vpn_token"],
        ),
        "scope_creep": Quest(
            id="scope_creep",
            name="Scope Creep",
            description="Brenda wants the Ancient Legacy Codebase from Miriam in the Legacy Wing. The requirements may change by the time you get back.",
            giver="product_manager",
            objectives=[
                QuestObjective("Get the Legacy Codebase from Miriam in the Codebase Ruins", QuestType.FETCH, "legacy_codebase"),
            ],
            gold_reward=20,
            xp_reward=15,
        ),
        "garden_cleanup": Quest(
            id="garden_cleanup",
            name="Garbage Collection",
            description="The Dead Code Garden has become infested with null references. Clear out the Null Pointer so the garden can be reclaimed.",
            giver="senior_dev",
            objectives=[
                QuestObjective("Defeat the Null Pointer in the Dead Code Garden", QuestType.KILL, "null_pointer"),
            ],
            gold_reward=15,
            xp_reward=20,
        ),
        "dragon_slayer": Quest(
            id="dragon_slayer",
            name="Paying Down Technical Debt",
            description="The Technical Debt Dragon has grown too powerful. Someone needs to slay it and free the Root Chamber.",
            giver="sysadmin",
            objectives=[
                QuestObjective("Defeat the Technical Debt Dragon in the Root Chamber", QuestType.KILL, "tech_debt_dragon"),
            ],
            gold_reward=100,
            xp_reward=50,
            rewards=["slightly_haunted_tophat"],
        ),
    }
