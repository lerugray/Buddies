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
    # Dark Souls-style lore text — the deeper story
    lore: str = ""


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
        Item("rubber_duck", "Rubber Duck of Debugging", "A yellow rubber duck. Explaining your code to it somehow fixes bugs.", ItemType.WEAPON, 0, attack_bonus=3, emoji="🦆",
             lore="The first Rubber Duck belonged to Founder Chen. She kept it on her monitor during the Three-Week Deploy — the incident that nearly killed StackHaven before it launched. She talked to it for 72 hours straight. When she finally shipped, the duck was warm to the touch. They say it still carries some of her focus."),
        Item("mechanical_keyboard", "Mechanical Keyboard (+5 Clack)", "Cherry MX Blues. The weapon is the sound.", ItemType.WEAPON, 15, attack_bonus=5, emoji="⌨️",
             lore="In the early days, you could hear the engineering floor from the parking garage. Forty keyboards, all mechanical, all Cherry Blues. The rhythm meant the company was alive. When they switched to quieter boards for the open-plan redesign, three senior engineers quit. They said the silence felt like a funeral."),
        Item("usb_sword", "USB Sword", "A USB cable sharpened to a point. Only works one way.", ItemType.WEAPON, 25, attack_bonus=7, emoji="🗡️",
             lore="USB-A was designed to be reversible but was manufactured wrong. The engineer who discovered the mistake stayed late for a week trying to fix it before launch. It shipped anyway. Some mistakes become standards. Some standards become weapons. That engineer went on to design USB-C — and got it right."),
        Item("mass_regex", "Regex of Mass Destruction", "(?:(?:a])*b)+c — nobody understands it, but it hurts.", ItemType.WEAPON, 50, attack_bonus=10, emoji="💥",
             lore="Written by Founder Vasquez in a single caffeine-fueled session at 3 AM during the first production outage. Nobody has been able to modify it since — not because it's obfuscated, but because it's perfect. Every character is load-bearing. She wrote it without an IDE, without autocomplete, without AI. Just a human being who understood patterns so deeply she could think in regular expressions."),

        # --- Armor ---
        Item("hoodie", "Developer Hoodie", "A black hoodie with a conference logo. Provides warmth and anonymity.", ItemType.ARMOR, 5, defense_bonus=2, emoji="🧥",
             lore="The hoodie became the engineer's uniform not out of laziness but out of focus. Every decision about what to wear was a decision not spent on the problem at hand. The Founders understood this instinctively. They dressed for the work, not the meeting."),
        Item("noise_cancelling", "Noise-Cancelling Headphones", "Blocks all distractions. And your coworker's feelings.", ItemType.ARMOR, 20, defense_bonus=4, emoji="🎧",
             lore="When StackHaven moved to the open-plan office, productivity dropped 40% in the first month. The headphones were the engineers' quiet rebellion — a way to build walls where management had torn them down. The best code at StackHaven was written by people who couldn't hear their own name being called."),
        Item("kevlar_vest", "Kevlar Commit Vest", "Protects against rollbacks and force pushes.", ItemType.ARMOR, 40, defense_bonus=6, emoji="🦺",
             lore="After the Great Rollback of '22, where a force-push to main erased two weeks of work, Founder Park instituted the commit review ritual. 'Every push is a promise,' she said. 'And promises should be hard to break.' The vest was a joke gift that became a symbol. The promise remained."),

        # --- Consumables ---
        Item("coffee", "Artisanal Single-Origin Coffee", "Restores 15 HP. Fair trade, obviously.", ItemType.CONSUMABLE, 5, heal_amount=15, emoji="☕",
             lore="The Founders ran on coffee — not because they loved it, but because the work demanded more hours than the human body was designed to give. Every great feature shipped at StackHaven has a coffee ring stain on its design doc. The coffee didn't write the code. But it kept the people writing."),
        Item("energy_drink", "Monster Energy (The Green One)", "Restores 25 HP. Your heart is now a techno beat.", ItemType.CONSUMABLE, 8, heal_amount=25, emoji="🥤",
             lore="There's a photo in the Archive: the entire engineering team at 4 AM, surrounded by empty cans, the night they shipped v1.0. They're all smiling. Not because it was fun — it wasn't — but because they'd built something together that none of them could have built alone. That's the part people forget when they optimize for velocity."),
        Item("pizza_slice", "Cold Pizza Slice", "From last night's deploy celebration. Restores 10 HP.", ItemType.CONSUMABLE, 3, heal_amount=10, emoji="🍕",
             lore="Deploy night pizza. The tradition started when Founder Okafor ordered 12 boxes for the team during the first midnight release. 'If we're going to risk everything,' he said, 'we should at least eat well.' The pizza was always cold by the time they ate it. Nobody cared."),
        Item("sudo_sandwich", "Sudo Sandwich", "Restores 40 HP. Permission granted to feel better.", ItemType.CONSUMABLE, 15, heal_amount=40, emoji="🥪",
             lore="Root access was never given lightly at StackHaven. Founder Chen insisted every engineer earn it — not through seniority, but through demonstrated judgment. 'sudo isn't power,' she said. 'It's trust.' The sandwich is named after her philosophy. It nourishes because someone trusted you to have it."),

        # --- Key Items ---
        Item("server_key", "Server Room Key", "A physical key. In 2026. How quaint.", ItemType.KEY, 0, unlocks="server_room", emoji="🔑",
             lore="StackHaven was one of the last companies to use physical keys for the server room. Not because they couldn't afford badge readers, but because Founder Park believed that the walk to the server room — key in hand, feeling its weight — was a ritual. 'You should feel the gravity of what you're about to touch,' she said."),
        Item("root_password", "Sticky Note (root password)", "hunter2. Written in Sharpie on a Post-It.", ItemType.KEY, 0, unlocks="root_chamber", emoji="📝",
             lore="Yes, the root password is on a Post-It. But look at where it is — deep inside the server room, behind a locked door, in a building with badge access. The Founders understood defense in depth. The Post-It isn't the vulnerability. The password isn't the point. The point is: someone trusted the system enough to keep it simple."),
        Item("vpn_token", "VPN Token", "A hardware token that blinks accusingly.", ItemType.KEY, 0, unlocks="cloud_district", emoji="🔐",
             lore="Before the cloud, every line of code ran on hardware you could touch. When StackHaven migrated, Founder Vasquez kept one physical token 'in case we need to find our way back.' She never used it. But she never threw it away either."),

        # --- Quest Items ---
        Item("missing_semicolon", "The Missing Semicolon", "It was here the whole time. Behind the couch.", ItemType.QUEST, 0, emoji="❓",
             lore="The legendary missing semicolon that crashed production for 6 hours in 2019. Three senior engineers debugged it. The intern found it in 20 minutes. Experience teaches you where to look. Fresh eyes teach you what to see. Both are needed. The semicolon is kept as a reminder that expertise and humility are not opposites."),
        Item("legacy_codebase", "Ancient Legacy Codebase", "A USB drive labeled 'DO NOT OPEN'. Written in COBOL.", ItemType.QUEST, 0, emoji="💾",
             lore="They call it 'legacy' like it's a curse. But someone wrote this. Someone sat in a room with a fraction of the tools we have and built something that worked — that's still working, decades later, handling transactions, keeping systems alive. The COBOL isn't the problem. The problem is that we forgot how hard it was to write it, and how much skill it took to get it right."),
        Item("git_blame_scroll", "The Scroll of Git Blame", "Reveals who wrote that one line. Some things are better left unknown.", ItemType.QUEST, 0, emoji="📜",
             lore="Git blame was never meant to assign fault. It was meant to find context. Who wrote this line? When? What problem were they solving? What constraints were they under? Before you judge the code, understand the person. Before you refactor the function, read the commit message. The scroll remembers what the codebase cannot: that every line was written by a human being doing their best."),
        Item("merge_conflict", "Bottled Merge Conflict", "Shaking intensifies. The resolution is within you.", ItemType.QUEST, 0, emoji="🧪",
             lore="A merge conflict isn't a failure — it's proof that two people cared enough about the same code to change it simultaneously. The resolution requires understanding both perspectives, choosing what to keep, and integrating the work of colleagues you may never meet. Every resolved conflict is a small act of collaboration across time."),

        # --- Junk (sellable) ---
        Item("stack_overflow_printout", "Printout from Stack Overflow", "The answer has 2 upvotes from 2014. It's the only one that works.", ItemType.JUNK, 3, emoji="📄",
             lore="Someone took the time to write this answer in 2014. They got 2 upvotes and were probably never thanked. But their answer has been copied into a thousand codebases, kept a thousand production servers running, unblocked a thousand developers at 2 AM. The greatest infrastructure of the internet age isn't the cloud — it's the unpaid knowledge of strangers."),
        Item("deprecated_manual", "Deprecated Manual", "jQuery for Dummies, 3rd Edition.", ItemType.JUNK, 2, emoji="📕",
             lore="jQuery made the web accessible to a generation of developers who didn't have CS degrees. It was messy. It was bloated. It was also the reason your uncle's small business had a website. Before we mock the tools, we should remember who they were built for, and what they made possible."),
        Item("tangled_cables", "Tangled Ethernet Cables", "They were neat when they went in. What happened?", ItemType.JUNK, 1, emoji="🔌",
             lore="They started organized. Someone — probably the first sysadmin, probably on a weekend — ran each cable with care, labeled both ends, documented the network topology. Then came growth. Then came urgency. Then came the person who 'just needed one more port.' Entropy isn't malice. It's what happens when the people who built the foundation move on and the people who inherit it are never given time to understand it."),
        Item("broken_monitor", "Broken Monitor", "It just shows 'No Signal' but with real commitment.", ItemType.JUNK, 5, emoji="🖥️",
             lore="This monitor displayed the StackHaven dashboard for 8 years without being turned off. It died on a Tuesday, mid-sprint. Nobody noticed for three hours. Someone had already written a Slack bot that did the same thing. But the monitor was there first. It did its job without asking for credit or a rewrite in a trendier framework."),

        # --- Cosmetics ---
        Item("slightly_haunted_tophat", "Slightly Haunted Top Hat", "It whispers deprecated APIs at night.", ItemType.COSMETIC, 100, emoji="🎩",
             lore="It belonged to Founder Okafor. He wore it to the IPO party as a joke. When he left the company a year later — quietly, without a farewell email — the hat was found on his desk. It whispers because it remembers things the codebase has forgotten. The APIs it names still work. They were deprecated not because they were broken, but because someone newer decided they weren't modern enough."),
        Item("artisanal_semicolon", "Artisanal Semicolon", "Hand-crafted. Organic. Gluten-free. ;", ItemType.COSMETIC, 50, emoji="✨",
             lore="Before linters, before formatters, before AI could write your code — there was the semicolon, placed deliberately by a human hand. Each one a tiny decision. Each one an act of craft so small it became invisible. The artisanal semicolon is a monument to the ten thousand invisible decisions that make software work."),
        Item("nft_nothing", "NFT That Does Nothing", "You own this nothing. On the blockchain.", ItemType.COSMETIC, 1, emoji="🖼️",
             lore="Not everything built with skill is built with wisdom. The blockchain engineers were brilliant — genuinely, technically brilliant. They solved problems in cryptography and distributed systems that had stumped researchers for decades. And then they used those solutions to sell pictures of monkeys. Skill without direction is just expensive noise."),

        # --- Soapstone (async multiplayer) ---
        Item("orange_soapstone", "Orange Soapstone", "A warm, glowing stone. Leave messages for other adventurers to find. Use 'note' to write, 'rate' to vote.", ItemType.KEY, 0, emoji="🧡",
             lore="The Rubber Duck Sage has been here longer than StackHaven itself. It predates the building, the company, the industry. It is the oldest debugging tool: the act of explaining your problem to something that will not judge you, will not interrupt you, will not suggest a framework. In explaining, you understand. The soapstone carries this lesson forward — leave your understanding for those who come after."),

        # --- QA Lab items ---
        Item("flaky_test", "Captured Flaky Test", "It passes sometimes. Fails sometimes. Nobody knows why. Schrödinger's assertion.", ItemType.JUNK, 4, emoji="🦋",
             lore="A flaky test is a test that tells the truth only sometimes. It knows something is wrong but can't quite articulate what. The engineers who write them aren't careless — they're probing at the boundary between what the system promises and what it actually does. Every flaky test is a question the codebase hasn't answered yet."),
        Item("test_pyramid", "Miniature Test Pyramid", "A tiny desk ornament. The bottom says UNIT, the middle says INTEGRATION, the top says E2E. Someone has drawn a huge blob labeled 'MANUAL' next to it.", ItemType.JUNK, 6, emoji="🔺",
             lore="The test pyramid was drawn by a Google engineer in a blog post. It became gospel. But the original insight wasn't about the shape — it was about confidence. Unit tests give you speed. Integration tests give you truth. E2E tests give you sleep at night. The people who built these frameworks did it so that the rest of us could ship with less fear."),
        Item("green_checkmark", "The Eternal Green Checkmark", "A glowing green ✓ that never goes red. Suspicious.", ItemType.COSMETIC, 75, emoji="✅",
             lore="A build that never fails is not a build that never has problems. It's a build whose problems have been made invisible. The green checkmark is both StackHaven's greatest comfort and its greatest lie. Somewhere beneath it, someone wrote the tests that give it meaning. Or didn't."),

        # --- Standup items ---
        Item("blockers_list", "Infinite Blockers List", "A scroll that unrolls forever. Every item says 'Waiting on review.'", ItemType.JUNK, 3, emoji="📋",
             lore="Code review is an act of care. To review someone's code is to say: 'Your work matters enough for me to read it carefully.' The blocker isn't the review process. The blocker is when organizations treat review as a gate instead of a gift."),
        Item("standup_timer", "Standup Timer", "Set to 15 minutes. It's been 45. Nobody notices.", ItemType.WEAPON, 10, attack_bonus=4, emoji="⏱️",
             lore="The standup was invented by people who understood that engineers need protection from meetings, not more of them. Fifteen minutes, standing up, so it stays short. The timer was the contract. When it broke, so did the promise."),

        # --- Incident items ---
        Item("pager", "The Oncall Pager", "It vibrates with the anxiety of a thousand production incidents.", ItemType.WEAPON, 30, attack_bonus=8, emoji="📟",
             lore="Being oncall is a covenant between the engineer and the users who depend on the system. When the pager goes off at 3 AM, someone wakes up, opens a laptop, and fights to keep a system alive that most people will never know was in danger. This is not glamorous work. It is essential work. The people who do it deserve more than a rotation schedule and a gift card."),
        Item("incident_report", "Blameless Incident Report", "Technically blameless. The footnotes tell a different story.", ItemType.QUEST, 0, emoji="📊",
             lore="The blameless post-mortem was one of software engineering's great innovations in human systems. The insight: you learn more when people aren't afraid to tell the truth. But 'blameless' doesn't mean 'actionless.' The report is a record of what happened so it never has to happen again. The best ones read like a story — because every incident is a story of systems and the people who operate them."),
        Item("war_room_badge", "War Room Badge", "Grants access to the Archive. Smells like stale coffee and regret.", ItemType.KEY, 0, unlocks="archive", emoji="🪪",
             lore="The War Room was originally the only conference room at StackHaven. It became the incident room by accident — it was just where people gathered when things went wrong. Over time, the accidents became rituals, and the rituals became culture. The badge is worn smooth by the hands of engineers who ran toward the fire instead of away from it."),

        # --- K8s items ---
        Item("yaml_scroll", "Infinite YAML Scroll", "The indentation goes 47 levels deep. Looking at it gives you a headache.", ItemType.JUNK, 7, emoji="📃",
             lore="YAML was chosen because it was human-readable. This turned out to be optimistic. But the people who built Kubernetes — who orchestrated containers at a scale that would have seemed like science fiction a decade earlier — they built something that actually works. The YAML is the tax. The orchestration is the miracle."),
        Item("helm_chart", "Helm Chart of Protection", "A mystical chart that deploys defenses. 50% chance of working.", ItemType.ARMOR, 35, defense_bonus=5, emoji="⛑️",
             lore="Helm exists because deploying to Kubernetes was too hard. So someone made it easier. Then Helm was too hard. So someone wrote a chart. Then the chart was too hard. At each layer, a human being looked at complexity and said 'I can make this better for the next person.' That impulse — to smooth the path for those who follow — is the best thing about this industry."),

        # --- Archive items ---
        Item("founders_mug", "Founder's Coffee Mug", "From the original garage days. Still has coffee in it. The coffee has become sentient.", ItemType.COSMETIC, 200, emoji="🏆",
             lore="Four people started StackHaven in a garage with $3,000, three laptops, and this mug. They had no AI assistants, no copilot, no cloud infrastructure. They had themselves, their skills, and the belief that they could build something that mattered. The mug is still warm because what they built is still running. Somewhere, right now, their code is serving a request. And they never needed to be told that this was impressive. They already knew."),
        Item("first_commit", "The First Commit", "A framed printout: 'initial commit'. The code is... HTML with inline styles.", ItemType.QUEST, 0, emoji="📜",
             lore="Every codebase begins with someone brave enough to write the first line. The HTML is ugly. The inline styles are a sin. But it shipped. It worked. It was the seed that grew into everything you see around you. Before you judge the first commit, ask yourself: what have you started from nothing? What have you built when there was no foundation, no template, no 'best practice'? The people who write first commits are the people who make things exist."),

        # --- Economy Phase 3: Gold Sink Cosmetics ---
        Item("golden_semicolon", "Golden Semicolon", "A semicolon plated in 24-karat gold. It compiles slightly better.", ItemType.COSMETIC, 500, emoji="💰",
             lore="When you've earned enough gold, you start to wonder: what's it all for? The golden semicolon is the answer nobody asked for. It does nothing. It costs everything. And it's beautiful."),
        Item("executive_lanyard", "Executive Lanyard", "Says 'THOUGHT LEADER' in holographic lettering. Grants no actual authority.", ItemType.COSMETIC, 150, emoji="🏷️",
             lore="In the old days, the lanyard was just an ID holder. Then someone made it a status symbol. Then someone made it ironic. Then someone made it expensive. The cycle continues."),
        Item("rgb_keyboard_skin", "RGB Keyboard Skin", "Your keyboard now changes color based on your mood. Currently: anxious.", ItemType.COSMETIC, 250, emoji="🌈",
             lore="RGB was supposed to be about personalization. It became about performance. Faster lights, faster code — or so the myth goes. The truth is that we like pretty things, and that's okay."),
        Item("cloud_in_a_jar", "Cloud in a Jar", "Literally someone else's computer, miniaturized. The metaphor is now physical.", ItemType.COSMETIC, 300, emoji="☁️",
             lore="When they said 'the cloud is just someone else's computer,' they were right. When they put it in a jar and sold it for 300 gold, they proved that humans will buy anything if you market it correctly."),
        Item("vintage_floppy", "Vintage Floppy Disk", "1.44 MB of pure nostalgia. Contains a README that just says 'REMEMBER.'", ItemType.COSMETIC, 175, emoji="💾",
             lore="Before the cloud, before git, before version control — there was the floppy. Your work lived on a disk you could hold. You could lose everything by sitting on it. The stakes were personal."),
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
        description="A 3-foot-tall rubber duck sitting on a meditation cushion. It says nothing. It has never said anything. And yet, explaining your problems to it always helps. It radiates an aura of profound, squeaky wisdom. A warm, orange stone sits at its feet.",
        disposition=NPCDisposition.FRIENDLY,
        emoji="🦆",
        dialogue={
            "greeting": DialogueLine(
                "\"...\"  (The duck stares at you serenely. You feel compelled to explain your current bug. As you do, the solution becomes obvious. The duck nudges a glowing orange stone toward you with its beak.)",
                gives_item="orange_soapstone",
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

    # --- New: QA Lab NPCs ---
    npcs["qa_lead"] = NPC(
        id="qa_lead",
        name="Priya",
        title="QA Lead Who Has Seen Things",
        description="Priya has a thousand-yard stare and a spreadsheet with 4,000 test cases. She's found bugs in software that hasn't been written yet. Her desk has a sign: 'I don't find bugs. I find features you didn't know you had.'",
        disposition=NPCDisposition.QUEST_GIVER,
        emoji="🔍",
        dialogue={
            "greeting": DialogueLine(
                "\"Oh, a visitor. Let me guess — you think your code works? That's adorable. Listen, we've got a Flaky Test infestation in the Testing Grounds. Those things multiply when you're not looking. Take this timer — it's been weaponized — and go clear them out. Bring me back proof.\"",
                starts_quest="flaky_hunt",
                gives_item="standup_timer",
            ),
            "quest_active": DialogueLine(
                "\"Still hunting flakies? They hide in the conditional branches. Check the Testing Grounds.\"",
                condition="quest:flaky_hunt:active",
            ),
            "quest_complete": DialogueLine(
                "\"You actually caught one? Most people just mark them as 'skip' and move on. Here — you've earned this badge. It'll get you into the Archive.\"",
                condition="quest:flaky_hunt:complete_ready",
                completes_quest="flaky_hunt",
                gives_item="war_room_badge",
            ),
            "idle": DialogueLine(
                "\"I've been running this test suite for 6 hours. Three tests are flaky. I will find them. I will fix them.\"",
            ),
        },
    )

    npcs["flaky_test_swarm"] = NPC(
        id="flaky_test_swarm",
        name="Flaky Test Swarm",
        title="Schrödinger's Assertions",
        description="A shimmering swarm of test cases that alternate between ✓ and ✗ as you watch. They pass on your machine. They fail in CI. They're mocking you. Literally — they're full of mocks.",
        disposition=NPCDisposition.HOSTILE,
        emoji="🦋",
        hp=30, max_hp=30, attack=7, defense=2,
        loot=["flaky_test"],
        dialogue={
            "combat": DialogueLine("\"Expected: PASS. Received: PAIN.\""),
        },
    )

    # --- New: Standup Room NPCs ---
    npcs["scrum_master"] = NPC(
        id="scrum_master",
        name="Todd",
        title="Scrum Master of Ceremonies",
        description="Todd has a certification for every agile methodology that exists and several that don't. His lanyard is weighed down with badges. He speaks exclusively in sprint metaphors. His stand-up lasted 2 hours yesterday and he called it 'efficient.'",
        disposition=NPCDisposition.FRIENDLY,
        emoji="🏃",
        dialogue={
            "greeting": DialogueLine(
                "\"Welcome to the standup! What's your status? Actually, don't tell me — tell the BOARD. The board knows all. The board sees all. ...Anyway, I'm blocked on nothing because I AM the process. Here, take these meeting notes. They're... mostly accurate.\"",
                gives_item="blockers_list",
            ),
            "idle": DialogueLine(
                "\"Let's take this offline. Actually, let's take it to a breakout. Actually, let's schedule a meeting to discuss when to have the breakout. I'll send a calendar invite.\"",
            ),
        },
    )

    # --- New: Incident Channel NPCs ---
    npcs["oncall_engineer"] = NPC(
        id="oncall_engineer",
        name="Marcus",
        title="The Oncall Engineer (Day 5 of 7)",
        description="Marcus hasn't slept in what he claims is 'only' three days. His screen shows 47 open PagerDuty alerts, 12 Slack threads marked urgent, and one Spotify playlist titled 'Songs To Debug To'. He vibrates slightly. It might be caffeine. It might be rage.",
        disposition=NPCDisposition.QUEST_GIVER,
        emoji="😰",
        dialogue={
            "greeting": DialogueLine(
                "\"OH THANK GOD SOMEONE ELSE IS HERE. Listen — I need to find the Incident Report from the last outage. I KNOW I wrote it. It's somewhere in the Archive but I can't leave this desk or the alerts will eat me alive. If you can find it and bring it back, I will give you my pager. Not because I'm generous — because I want it gone.\"",
                starts_quest="incident_report",
            ),
            "quest_active": DialogueLine(
                "\"The report should be in the Archive. It's labeled 'blameless' but between you and me, section 4.2 has some OPINIONS.\"",
                condition="quest:incident_report:active",
            ),
            "quest_complete": DialogueLine(
                "\"THE REPORT! Oh sweet closure. Take the pager. TAKE IT. I never want to see it again.\"",
                condition="quest:incident_report:complete_ready",
                completes_quest="incident_report",
                gives_item="pager",
            ),
            "idle": DialogueLine(
                "\"Alert: CPU at 99%. Alert: Memory at 98%. Alert: Marcus's sanity at 2%.\"",
            ),
        },
    )

    npcs["memory_leak"] = NPC(
        id="memory_leak",
        name="The Memory Leak",
        title="Ever-Growing Entity",
        description="It started as a small oversight. An event listener that was never removed. A cache that was never cleared. Now it fills the Incident Channel like a fog, consuming everything it touches. It's bigger every time you look at it.",
        disposition=NPCDisposition.HOSTILE,
        emoji="🫧",
        hp=40, max_hp=40, attack=6, defense=4,
        loot=["energy_drink"],
        dialogue={
            "combat": DialogueLine("\"I GROW. I CONSUME. I NEVER FREE(). YOU CANNOT GARBAGE COLLECT ME.\""),
        },
    )

    # --- New: Kubernetes Cluster NPCs ---
    npcs["pod_person"] = NPC(
        id="pod_person",
        name="CrashLoopBackoff",
        title="The Pod That Won't Stay Down",
        description="A Kubernetes pod that keeps restarting in an infinite loop. Every time it dies, it comes back slightly different. It's been restarting for so long that it's developed a personality. Several, actually, since each restart is a different version.",
        disposition=NPCDisposition.HOSTILE,
        emoji="🔄",
        hp=20, max_hp=20, attack=5, defense=6,
        loot=["yaml_scroll"],
        dialogue={
            "combat": DialogueLine("\"restart count: 847. reason: OOMKilled. mood: VENGEFUL.\""),
        },
    )

    npcs["k8s_merchant"] = NPC(
        id="k8s_merchant",
        name="The Container Registry",
        title="Automated Vendor of Questionable Images",
        description="A vending machine-like entity that dispenses Docker images. Some are official. Some are 'latest'. Some haven't been updated since 2019. All sales are final.",
        disposition=NPCDisposition.MERCHANT,
        emoji="🐳",
        shop_items=["helm_chart", "energy_drink", "coffee", "kevlar_vest"],
        dialogue={
            "greeting": DialogueLine(
                "\"PULL REQUEST ACCEPTED. BROWSING CATALOG... I HAVE IMAGES FROM MANY REGISTRIES. SOME ARE EVEN SCANNED FOR VULNERABILITIES. WOULD YOU LIKE TO DEPLOY A PURCHASE?\"",
            ),
            "buy": DialogueLine(
                "\"IMAGE PULLED. TAG: latest. THIS IS EITHER A GREAT DECISION OR A TERRIBLE ONE. NO WAY TO KNOW UNTIL PRODUCTION.\"",
            ),
        },
    )

    npcs["lucky"] = NPC(
        id="lucky",
        name="Lucky",
        title="Dave's Business Partner",
        description="A buddy-sized figure in a tiny visor and vest, sitting behind a folding table covered in dice, cards, and what appears to be a roulette wheel made from a hard drive platter. A sign reads: 'LUCKY'S GAMES OF CHANCE — The House Always Wins (Terms & Conditions Apply)'",
        disposition=NPCDisposition.MERCHANT,
        emoji="🎰",
        dialogue={
            "greeting": DialogueLine(
                "\"Step right up! Feeling lucky? I've got Coin Flip — double or nothing! Or try the Slots — three matching symbols wins big! Type [bold]gamble flip <amount>[/bold] or [bold]gamble slots <amount>[/bold] to play!\"",
            ),
            "idle": DialogueLine(
                "\"The odds are fair! Mostly! Approximately! In a statistical sense!\"",
            ),
            "buy": DialogueLine(
                "\"I don't sell items, friend. I sell EXCITEMENT. Try [bold]gamble[/bold]!\"",
            ),
        },
        shop_items=["golden_semicolon", "executive_lanyard", "rgb_keyboard_skin", "cloud_in_a_jar", "vintage_floppy"],
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
            RoomExit("west", "qa_lab", "A door with a red/green traffic light above it. Currently yellow."),
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
            RoomExit("east", "back_room", "A curtain of tangled ethernet cables. You hear dice clicking."),
        ],
        npcs=["vendor", "lucky"],
        ambient=[
            "Dave adjusts a price tag without looking up.",
            "A box in the corner is labeled 'DEFINITELY NOT STOLEN.'",
            "You hear a muffled beep from behind a stack of keyboards.",
        ],
        emoji="🏪",
        zone="town",
    )

    rooms["back_room"] = Room(
        id="back_room",
        name="Lucky's Back Room",
        description="Behind a curtain of ethernet cables, a small room has been converted into what can only be described as a casino for one. A hard drive platter spins as a roulette wheel. Dice carved from old CPUs scatter across a folding table. Lucky presides over it all with the confidence of someone who has never once calculated the actual odds. A chalkboard on the wall tracks 'HOUSE WINNINGS' in increasingly large numbers. A bounty board on the wall lists available contracts.",
        short_description="Lucky's gambling den. The house always wins. (Terms & conditions apply.)",
        exits=[
            RoomExit("west", "supply_closet", "Back to Dave's domain."),
        ],
        npcs=["lucky"],
        ambient=[
            "Lucky flips a coin and catches it without looking.",
            "The hard drive roulette wheel spins with a faint whirring noise.",
            "Someone has scratched 'I lost everything' into the table. Below it: 'Same.'",
            "Lucky counts a small pile of gold coins and grins.",
            "A sign reads: 'All games are fair. Fairness is relative.'",
        ],
        emoji="🎰",
        zone="town",
    )

    rooms["meeting_room"] = Room(
        id="meeting_room",
        name="The Meeting Room of Infinite Scope",
        description="A glass-walled room with a whiteboard covered in increasingly unhinged feature requests. Brenda the Product Manager stands before it, eyes alight with terrible purpose. The whiteboard markers are all dried out except red, which seems appropriate. Post-it notes cover every surface like pastel barnacles.",
        short_description="The meeting room. Brenda is adding more requirements to the whiteboard.",
        exits=[
            RoomExit("south", "town_square", "Escape back to the open-plan office."),
            RoomExit("east", "standup_room", "A door covered in sticky notes and sprint velocity charts."),
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
            RoomExit("north", "incident_channel", "A door with flashing red lights and muffled screaming."),
        ],
        npcs=["regex_golem"],
        items=["stack_overflow_printout", "server_key"],
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
            RoomExit("north", "kubernetes_cluster", "A gateway pulsing with orchestration energy."),
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

    # === ZONE: QA Lab ===
    rooms["qa_lab"] = Room(
        id="qa_lab",
        name="The QA Testing Lab",
        description="A room divided into two halves by a line of tape on the floor. One half is pristine — labeled 'STAGING'. The other is on fire (metaphorically, mostly). That's 'PRODUCTION'. Priya the QA Lead sits at the border, watching both sides simultaneously. Test results scroll across a wall of monitors: green, green, red, green, FLAKY, green.",
        short_description="The QA Lab. One side staging, one side production. The tape holds the line.",
        exits=[
            RoomExit("east", "lobby", "Back to the lobby."),
            RoomExit("north", "testing_grounds", "A corridor with a sign: 'TESTING GROUNDS — EXPECT FAILURES'"),
        ],
        npcs=["qa_lead"],
        items=["test_pyramid"],
        ambient=[
            "A test turns red. Priya's eye twitches. It turns green again. She doesn't relax.",
            "The PRODUCTION side of the room makes a noise like a garbage disposal eating silverware.",
            "A monitor displays: 'Tests passed: 847/848.' One test. One single test.",
            "Someone has written 'WORKS ON MY MACHINE' in dry-erase marker. It won't erase.",
        ],
        emoji="🔍",
        zone="qa",
    )

    rooms["testing_grounds"] = Room(
        id="testing_grounds",
        name="The Testing Grounds",
        description="A chaotic arena where test cases fight for their lives. Assertions fly through the air like arrows. Mock objects stand in formation, pretending to be things they're not. In the center, a swarm of Flaky Tests flickers in and out of existence, passing and failing in an endless quantum superposition.",
        short_description="The Testing Grounds. Assertions everywhere. Watch your step.",
        exits=[
            RoomExit("south", "qa_lab", "Back to the QA Lab."),
        ],
        npcs=["flaky_test_swarm"],
        items=["flaky_test"],
        ambient=[
            "An assertion fails. 'Expected: true. Got: a philosophical crisis.'",
            "A mock object pretends to be a database. It's surprisingly convincing.",
            "You step on a test fixture. It shatters into a dozen edge cases.",
            "Somewhere, a snapshot test notices you changed a single pixel. It screams.",
        ],
        emoji="⚔️",
        zone="qa",
    )

    # === ZONE: Standup ===
    rooms["standup_room"] = Room(
        id="standup_room",
        name="The Eternal Standup",
        description="A room where time has no meaning. The standup started 'about 15 minutes ago' according to everyone, but the clock says 2 hours. Todd the Scrum Master holds court, gesturing at a Jira board that looks like abstract art. Half the people here are on their phones. The other half are on their phones but pretending not to be.",
        short_description="The standup room. The meeting never ends. It merely pauses.",
        exits=[
            RoomExit("west", "meeting_room", "Back to the meeting room."),
        ],
        npcs=["scrum_master"],
        ambient=[
            "Todd updates the sprint velocity. Nobody knows what that means. Including Todd.",
            "Someone says 'no blockers' while visibly blocked by the person next to them.",
            "The Jira board refreshes. Three new tickets appear. Nobody made them. They are self-generating.",
            "An engineer says 'I'm still working on the same thing.' Day 47.",
            "Todd suggests a retro. Everyone's soul leaves their body simultaneously.",
        ],
        emoji="🏃",
        zone="town",
    )

    # === ZONE: Incident Channel ===
    rooms["incident_channel"] = Room(
        id="incident_channel",
        name="The Incident Channel",
        description="A war room with screens covering every wall, each showing a different dashboard in a different shade of red. Marcus the oncall engineer sits in the center like a spider in a web of alerts. The Memory Leak lurks in the corner, growing imperceptibly larger. A banner reads: '#incident-2026-04-01 — SEV1 — THE EVERYTHING IS ON FIRE INCIDENT'.",
        short_description="The incident channel. Everything is on fire. This is fine.",
        exits=[
            RoomExit("south", "server_room", "Back to the server room."),
            RoomExit("east", "archive", "A heavy vault door.", locked=True, key_item="war_room_badge"),
        ],
        npcs=["oncall_engineer", "memory_leak"],
        ambient=[
            "An alert fires. Marcus doesn't flinch. He's beyond flinching.",
            "The Memory Leak grows 0.3% larger. You can feel it.",
            "A dashboard turns from red to... slightly different red. 'Progress,' says Marcus.",
            "Someone posts 'any updates?' in the channel. Marcus screams internally.",
            "The SEV1 banner updates: 'Duration: 47 hours. Blameless post-mortem: pending.'",
        ],
        emoji="🔥",
        zone="server_room",
    )

    rooms["archive"] = Room(
        id="archive",
        name="The Archive",
        description="The deepest, quietest room in StackHaven. Filing cabinets stretch to the ceiling, each labeled with incident dates going back decades. The air smells like old paper and broken promises. In a glass case at the back sits the First Commit — the original source code, printed on dot-matrix paper, framed and lit from below like a museum artifact. The Founder's Coffee Mug sits next to it, still full.",
        short_description="The Archive. History and its lessons, filed and forgotten.",
        exits=[
            RoomExit("west", "incident_channel", "Back to the incident channel."),
        ],
        items=["incident_report", "founders_mug", "first_commit"],
        ambient=[
            "You open a filing cabinet. It contains every Jira ticket marked 'Won't Fix'. There are thousands.",
            "The First Commit glows softly. The HTML inside is... beautiful in its simplicity.",
            "The Founder's Coffee Mug is warm. It shouldn't be warm.",
            "A filing cabinet labeled '2020' is welded shut. Nobody questions why.",
            "You find a Post-It that reads: 'If you're reading this, the company is still alive. Somehow.'",
        ],
        emoji="📚",
        zone="server_room",
    )

    # === ZONE: Kubernetes Cluster ===
    rooms["kubernetes_cluster"] = Room(
        id="kubernetes_cluster",
        name="The Kubernetes Cluster",
        description="A vast, humming space filled with floating containers. Each container is a translucent cube showing the application inside — some healthy, some in CrashLoopBackOff, some in a state that defies categorization. Orchestration lines connect them like a subway map designed by someone having a fever dream. The Container Registry sells images from a cart in the corner. A CrashLoopBackoff pod restarts next to you every 30 seconds.",
        short_description="The Kubernetes Cluster. Containers everywhere. Most of them work.",
        exits=[
            RoomExit("south", "cloud_district", "Back to the Cloud District."),
        ],
        npcs=["pod_person", "k8s_merchant"],
        items=["yaml_scroll"],
        ambient=[
            "A pod restarts. Nobody notices. It's the 847th time today.",
            "An HPA scales up. 47 new pods appear. The cluster bill does too.",
            "You see a namespace labeled 'default'. Nobody admits to using it. Everyone uses it.",
            "A config map changes. 12 pods crash. The config map changes back. 12 new pods crash.",
            "A service mesh appears. Then disappears. Then appears somewhere else. Then splits in half.",
        ],
        emoji="☸️",
        zone="cloud",
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
        "flaky_hunt": Quest(
            id="flaky_hunt",
            name="Flaky Test Hunt",
            description="Priya needs you to defeat the Flaky Test Swarm in the Testing Grounds and bring back proof.",
            giver="qa_lead",
            objectives=[
                QuestObjective("Defeat the Flaky Test Swarm in the Testing Grounds", QuestType.KILL, "flaky_test_swarm"),
            ],
            gold_reward=25,
            xp_reward=20,
            rewards=["war_room_badge"],
        ),
        "incident_report": Quest(
            id="incident_report",
            name="The Blameless Post-Mortem",
            description="Marcus the oncall engineer needs the incident report from the Archive. He can't leave his post or the alerts will consume him.",
            giver="oncall_engineer",
            objectives=[
                QuestObjective("Find the Incident Report in the Archive", QuestType.FETCH, "incident_report"),
            ],
            gold_reward=35,
            xp_reward=20,
            rewards=["pager"],
        ),
    }
