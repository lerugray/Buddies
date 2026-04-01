"""Dungeon Crawl engine — cooperative roguelike with your buddy.

Explore a randomized dungeon floor by floor. Each room has an
encounter: monsters, traps, treasure, or mystery events.
Your buddy assists based on their personality stats:
- DEBUGGING: spot traps, analyze monsters, find weaknesses
- CHAOS: kick down doors, cause explosions, wild magic
- SNARK: intimidate enemies, snarky commentary, distraction
- WISDOM: find secrets, heal, identify items
- PATIENCE: steady defense, careful movement, rest bonuses
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state


# ---------------------------------------------------------------------------
# Encounter types
# ---------------------------------------------------------------------------

class EncounterType(Enum):
    MONSTER = "monster"
    TRAP = "trap"
    TREASURE = "treasure"
    MYSTERY = "mystery"
    REST = "rest"
    BOSS = "boss"
    EMPTY = "empty"


@dataclass
class Monster:
    name: str
    hp: int
    damage: int
    description: str
    weakness: str  # Which stat helps against this monster


MONSTERS = [
    Monster("Null Pointer", 15, 3, "A ghostly arrow pointing nowhere", "debugging"),
    Monster("Stack Overflow", 20, 4, "An ever-growing tower of function calls", "patience"),
    Monster("Race Condition", 12, 5, "Two threads fighting over one resource", "debugging"),
    Monster("Spaghetti Code", 25, 3, "A tangled mass of goto statements", "wisdom"),
    Monster("Memory Leak", 18, 2, "It just keeps growing... and growing...", "debugging"),
    Monster("Regex Demon", 22, 4, "(?:un)?readable .*patterns", "wisdom"),
    Monster("Off-By-One Error", 10, 6, "Almost right. Almost.", "patience"),
    Monster("Infinite Loop", 30, 2, "while(true) { pain++; }", "chaos"),
    Monster("Merge Conflict", 16, 4, "<<<<<<< HEAD ======= >>>>>>> branch", "patience"),
    Monster("Legacy Dependency", 20, 3, "It's from 2003 and everything depends on it", "wisdom"),
    Monster("Phantom Bug", 8, 7, "Only appears in production. Never in tests.", "debugging"),
    Monster("Scope Creep", 28, 3, "It started small. It's not small anymore.", "snark"),
]

BOSSES = [
    Monster("The Monolith", 50, 6, "A single 10,000-line file. It does everything.", "chaos"),
    Monster("Prod Deployment Friday", 60, 5, "Someone pushed to main at 4:59 PM", "patience"),
    Monster("The Rewrite", 55, 7, "We should rewrite everything from scratch... again", "wisdom"),
]

TRAPS = [
    ("Segfault Pit", "The floor vanishes into invalid memory!", "debugging"),
    ("Callback Hell", "Nested promises spiral downward endlessly!", "patience"),
    ("Type Coercion", "JavaScript turns your sword into 'undefined'!", "wisdom"),
    ("Dependency Spiral", "npm install triggers a cascade of 47 sub-dependencies!", "chaos"),
    ("Git Rebase Gone Wrong", "Your commit history is now abstract art!", "debugging"),
    ("YAML Indentation", "One space wrong and the whole dungeon collapses!", "patience"),
]

TREASURES = [
    ("Golden Semicolon", "The most precious punctuation mark", 15),
    ("Ancient Documentation", "Actual comments! In the code! From 2019!", 10),
    ("Rubber Duck (Legendary)", "It listens. It understands. It judges.", 20),
    ("Stack Overflow Answer", "With 847 upvotes and a green checkmark", 12),
    ("Mechanical Keyboard", "Cherry MX Blues. Your enemies hear you coming.", 18),
    ("Monitor #3", "The ultrawide wasn't wide enough.", 15),
    ("Perfectly Formatted JSON", "Not a single trailing comma. Beautiful.", 8),
    ("Working Docker Config", "It runs on YOUR machine AND theirs.", 25),
]

MYSTERIES = [
    ("Strange Terminal", "A terminal glows with an unfamiliar prompt..."),
    ("Abandoned Whiteboard", "Faded diagrams of a system no one remembers building..."),
    ("Vending Machine", "It accepts only cryptocurrency and promises..."),
    ("Mysterious PR", "A pull request from a user who never existed..."),
    ("Time Loop", "You've been in this standup before... haven't you?"),
    ("The Oracle", "A senior developer from the before times. They speak in riddles."),
]


@dataclass
class Room:
    """A single room in the dungeon."""
    floor: int
    room_num: int
    encounter_type: EncounterType
    name: str = ""
    description: str = ""
    resolved: bool = False
    # Encounter-specific data
    monster: Monster | None = None
    trap: tuple | None = None
    treasure: tuple | None = None
    mystery: tuple | None = None
    loot_value: int = 0


@dataclass
class DungeonState:
    """Player + buddy state in the dungeon."""
    hp: int = 50
    max_hp: int = 50
    gold: int = 0
    items: list[str] = field(default_factory=list)
    floors_cleared: int = 0
    monsters_defeated: int = 0
    traps_avoided: int = 0
    treasures_found: int = 0


@dataclass
class DungeonGame:
    """Full dungeon crawl game state."""
    buddy_state: BuddyState
    personality: GamePersonality = field(init=False)

    state: DungeonState = field(default_factory=DungeonState)
    current_floor: int = 1
    current_room: int = 0
    rooms: list[Room] = field(default_factory=list)
    max_floors: int = 5
    rooms_per_floor: int = 4

    is_over: bool = False
    action_log: list[str] = field(default_factory=list)
    _awaiting_choice: bool = False
    _current_choices: list[tuple[str, str]] = field(default_factory=list)  # (key, label)

    def __post_init__(self):
        self.personality = personality_from_state(self.buddy_state)
        self._generate_floor()

    def _generate_floor(self):
        """Generate rooms for the current floor."""
        self.rooms = []
        self.current_room = 0

        for i in range(self.rooms_per_floor):
            # Last room of last floor is always a boss
            if self.current_floor == self.max_floors and i == self.rooms_per_floor - 1:
                boss = random.choice(BOSSES)
                self.rooms.append(Room(
                    floor=self.current_floor, room_num=i,
                    encounter_type=EncounterType.BOSS,
                    name=boss.name, description=boss.description,
                    monster=boss,
                ))
                continue

            # Random encounter type with weights
            enc_type = random.choices(
                [EncounterType.MONSTER, EncounterType.TRAP, EncounterType.TREASURE,
                 EncounterType.MYSTERY, EncounterType.REST, EncounterType.EMPTY],
                weights=[30, 20, 15, 15, 10, 10],
            )[0]

            room = Room(floor=self.current_floor, room_num=i, encounter_type=enc_type)

            if enc_type == EncounterType.MONSTER:
                m = random.choice(MONSTERS)
                room.name = m.name
                room.description = m.description
                room.monster = m
            elif enc_type == EncounterType.TRAP:
                t = random.choice(TRAPS)
                room.name = t[0]
                room.description = t[1]
                room.trap = t
            elif enc_type == EncounterType.TREASURE:
                t = random.choice(TREASURES)
                room.name = t[0]
                room.description = t[1]
                room.loot_value = t[2]
                room.treasure = t
            elif enc_type == EncounterType.MYSTERY:
                m = random.choice(MYSTERIES)
                room.name = m[0]
                room.description = m[1]
                room.mystery = m
            elif enc_type == EncounterType.REST:
                room.name = "Rest Area"
                room.description = "A quiet corner with a coffee machine that still works."
            else:
                room.name = "Empty Room"
                room.description = "Nothing here but dust and regret."

            self.rooms.append(room)

    @property
    def current(self) -> Room | None:
        if self.current_room < len(self.rooms):
            return self.rooms[self.current_room]
        return None

    def enter_room(self):
        """Enter the current room and describe it."""
        room = self.current
        if not room:
            return

        self.action_log.append(
            f"\n[bold cyan]━━━ Floor {room.floor}, Room {room.room_num + 1}/{self.rooms_per_floor} ━━━[/bold cyan]"
        )
        self.action_log.append(f"[bold]{room.name}[/bold]")
        self.action_log.append(f"[dim]{room.description}[/dim]")
        self.action_log.append("")

        # Buddy reacts
        buddy_name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        if room.encounter_type == EncounterType.MONSTER or room.encounter_type == EncounterType.BOSS:
            m = room.monster
            self.action_log.append(f"⚔️ [red bold]{m.name}[/red bold] blocks the path! (HP: {m.hp}, DMG: {m.damage})")
            # Buddy analyzes if high debugging/wisdom
            if self.personality.should_play_optimal():
                self.action_log.append(f"{emoji} {buddy_name}: \"It's weak to {m.weakness.upper()}. I can help!\"")
            elif self.personality.should_trash_talk():
                self.action_log.append(f"{emoji} {buddy_name}: \"Oh great, a {m.name}. My favorite.\"")

            self._current_choices = [("f", "Fight"), ("r", "Run")]
            self._awaiting_choice = True

        elif room.encounter_type == EncounterType.TRAP:
            # Debugging buddies can spot traps
            if self.personality.optimal_play > 0.5:
                self.action_log.append(f"{emoji} {buddy_name}: \"Wait! I see a trap! Let me disarm it...\"")
                self._current_choices = [("d", "Let buddy disarm"), ("j", "Jump over it"), ("t", "Trigger it")]
            else:
                self._current_choices = [("j", "Jump over it"), ("t", "Trigger it carefully")]
            self._awaiting_choice = True

        elif room.encounter_type == EncounterType.TREASURE:
            self.action_log.append(f"✨ [yellow]{room.name}[/yellow] — worth {room.loot_value} gold!")
            if self.personality.should_trash_talk():
                self.action_log.append(f"{emoji} {buddy_name}: \"Dibs! ...just kidding. Mostly.\"")
            self._resolve_treasure(room)

        elif room.encounter_type == EncounterType.MYSTERY:
            self.action_log.append(f"❓ [magenta]A mysterious encounter![/magenta]")
            self._current_choices = [("i", "Investigate"), ("l", "Leave it alone")]
            self._awaiting_choice = True

        elif room.encounter_type == EncounterType.REST:
            heal = 10 + (5 if self.personality.patience_factor > 0.4 else 0)
            self.action_log.append(f"☕ Rest area! You recover {heal} HP.")
            if self.personality.patience_factor > 0.4:
                self.action_log.append(f"{emoji} {buddy_name}: \"Take your time. I'll keep watch.\" (+5 bonus HP)")
            self.state.hp = min(self.state.max_hp, self.state.hp + heal)
            room.resolved = True

        else:  # Empty
            self.action_log.append("Nothing here. Moving on.")
            room.resolved = True

    def make_choice(self, key: str):
        """Process player's choice for the current encounter."""
        if not self._awaiting_choice:
            return

        valid_keys = [k for k, _ in self._current_choices]
        if key not in valid_keys:
            return

        self._awaiting_choice = False
        room = self.current
        if not room:
            return

        buddy_name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        if room.encounter_type in (EncounterType.MONSTER, EncounterType.BOSS):
            if key == "f":
                self._resolve_fight(room)
            else:
                self._resolve_run(room)

        elif room.encounter_type == EncounterType.TRAP:
            if key == "d":
                self._resolve_trap_disarm(room)
            elif key == "j":
                self._resolve_trap_jump(room)
            else:
                self._resolve_trap_trigger(room)

        elif room.encounter_type == EncounterType.MYSTERY:
            if key == "i":
                self._resolve_mystery_investigate(room)
            else:
                self.action_log.append("You leave the mystery alone. Probably for the best.")
                room.resolved = True

    def _resolve_fight(self, room: Room):
        """Fight a monster. Stats determine effectiveness."""
        m = room.monster
        buddy_name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji
        stats = self.buddy_state.stats

        # Buddy's contribution based on monster weakness
        weakness_stat = stats.get(m.weakness, 10)
        buddy_bonus = weakness_stat // 5  # 0-20 bonus damage

        # Base player damage + buddy bonus
        player_damage = random.randint(8, 15) + buddy_bonus

        # Chaos buddies sometimes deal huge damage (or miss)
        if self.personality.should_wild_card():
            if random.random() < 0.5:
                player_damage *= 2
                self.action_log.append(f"{emoji} {buddy_name} goes BERSERK! Double damage!")
            else:
                player_damage //= 2
                self.action_log.append(f"{emoji} {buddy_name} trips over their own feet!")

        # Monster attacks back
        monster_damage = m.damage
        # Patience reduces incoming damage
        if self.personality.patience_factor > 0.4:
            monster_damage = max(1, monster_damage - 1)
            self.action_log.append(f"{emoji} {buddy_name} braces for impact! (-1 damage taken)")

        monster_hp = m.hp

        # Simple combat loop
        rounds = 0
        while monster_hp > 0 and self.state.hp > 0:
            rounds += 1
            hit = player_damage + random.randint(-2, 2)
            monster_hp -= max(1, hit)
            self.action_log.append(f"  Round {rounds}: You deal {max(1, hit)} damage! ({m.name}: {max(0, monster_hp)} HP)")

            if monster_hp <= 0:
                break

            taken = monster_damage + random.randint(-1, 1)
            self.state.hp -= max(1, taken)
            self.action_log.append(f"  {m.name} hits for {max(1, taken)}! (You: {max(0, self.state.hp)} HP)")

        if self.state.hp <= 0:
            self.action_log.append(f"\n[red bold]You've been defeated by {m.name}![/red bold]")
            self.is_over = True
        else:
            gold = random.randint(5, 15) * self.current_floor
            self.state.gold += gold
            self.state.monsters_defeated += 1
            self.action_log.append(f"\n[green bold]Victory![/green bold] {m.name} defeated! (+{gold} gold)")
            if buddy_bonus > 2:
                self.action_log.append(f"{emoji} {buddy_name}'s {m.weakness.upper()} knowledge was crucial!")
            room.resolved = True

    def _resolve_run(self, room: Room):
        """Try to run from a monster."""
        # Chaos buddies are better at escaping (or worse)
        if self.personality.should_bluff() or random.random() < 0.6:
            self.action_log.append("You flee successfully!")
            room.resolved = True
        else:
            damage = room.monster.damage + random.randint(0, 2)
            self.state.hp -= damage
            self.action_log.append(f"Couldn't escape! {room.monster.name} hits for {damage}! (HP: {max(0, self.state.hp)})")
            room.resolved = True
            if self.state.hp <= 0:
                self.is_over = True

    def _resolve_trap_disarm(self, room: Room):
        """Buddy tries to disarm the trap."""
        buddy_name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        # Success chance based on debugging + trap's counter-stat
        trap_stat = room.trap[2] if room.trap else "debugging"
        skill = self.buddy_state.stats.get(trap_stat, 10)
        success_chance = min(0.9, 0.4 + skill / 50.0)

        if random.random() < success_chance:
            gold = random.randint(5, 15)
            self.state.gold += gold
            self.state.traps_avoided += 1
            self.action_log.append(f"[green]{emoji} {buddy_name} disarms the trap![/green] (+{gold} salvage gold)")
        else:
            damage = random.randint(3, 8)
            self.state.hp -= damage
            self.action_log.append(f"[red]{emoji} {buddy_name} fumbles the disarm![/red] ({damage} damage!)")
            if self.state.hp <= 0:
                self.is_over = True
        room.resolved = True

    def _resolve_trap_jump(self, room: Room):
        """Try to jump over the trap."""
        if random.random() < 0.5:
            self.state.traps_avoided += 1
            self.action_log.append("[green]You leap over the trap safely![/green]")
        else:
            damage = random.randint(4, 10)
            self.state.hp -= damage
            self.action_log.append(f"[red]You clip the trap! {damage} damage![/red] (HP: {max(0, self.state.hp)})")
            if self.state.hp <= 0:
                self.is_over = True
        room.resolved = True

    def _resolve_trap_trigger(self, room: Room):
        """Carefully trigger the trap."""
        damage = random.randint(2, 5)
        self.state.hp -= damage
        self.action_log.append(f"You trigger the trap carefully. Only {damage} damage. (HP: {max(0, self.state.hp)})")
        if self.state.hp <= 0:
            self.is_over = True
        room.resolved = True

    def _resolve_treasure(self, room: Room):
        """Pick up treasure."""
        self.state.gold += room.loot_value
        self.state.treasures_found += 1
        if room.treasure:
            self.state.items.append(room.treasure[0])
        self.action_log.append(f"[yellow]Got {room.loot_value} gold![/yellow]")
        room.resolved = True

    def _resolve_mystery_investigate(self, room: Room):
        """Investigate a mystery event."""
        buddy_name = self.buddy_state.name
        emoji = self.buddy_state.species.emoji

        # Random outcomes weighted by wisdom
        wisdom = self.buddy_state.stats.get("wisdom", 10)
        good_chance = min(0.8, 0.3 + wisdom / 60.0)

        if random.random() < good_chance:
            # Good outcome
            outcomes = [
                (f"You find a hidden cache! +20 gold", 20, 0),
                (f"Ancient knowledge flows through you! +10 max HP", 0, 10),
                (f"{emoji} {buddy_name} deciphers the clue! +15 gold", 15, 0),
                (f"A friendly ghost teaches you a shortcut! +5 HP", 0, 5),
            ]
            text, gold, hp = random.choice(outcomes)
            self.state.gold += gold
            if hp > 0:
                self.state.max_hp += hp
                self.state.hp = min(self.state.max_hp, self.state.hp + hp)
            self.action_log.append(f"[green]{text}[/green]")
        else:
            damage = random.randint(3, 8)
            self.state.hp -= damage
            self.action_log.append(f"[red]It was a trap all along! {damage} damage![/red] (HP: {max(0, self.state.hp)})")
            if self.state.hp <= 0:
                self.is_over = True
        room.resolved = True

    def advance(self):
        """Move to the next room or floor."""
        if self.is_over:
            return

        room = self.current
        if room and not room.resolved:
            return  # Must resolve current room first

        self.current_room += 1

        if self.current_room >= len(self.rooms):
            # Floor cleared!
            self.state.floors_cleared += 1
            self.current_floor += 1

            if self.current_floor > self.max_floors:
                # Dungeon complete!
                self.is_over = True
                self.action_log.append(
                    f"\n[bold green]═══ DUNGEON CLEARED! ═══[/bold green]"
                )
                self.action_log.append(
                    f"Floors: {self.state.floors_cleared} | "
                    f"Monsters: {self.state.monsters_defeated} | "
                    f"Gold: {self.state.gold}"
                )
                return

            self.action_log.append(f"\n[bold cyan]═══ FLOOR {self.current_floor} ═══[/bold cyan]")
            self._generate_floor()

        self.enter_room()

    @property
    def awaiting_choice(self) -> bool:
        return self._awaiting_choice and not self.is_over

    @property
    def choices(self) -> list[tuple[str, str]]:
        return self._current_choices if self._awaiting_choice else []

    def get_result(self) -> GameResult:
        """Build game result."""
        s = self.state
        cleared_all = self.current_floor > self.max_floors

        if cleared_all:
            outcome = GameOutcome.WIN
            xp = 30 + s.monsters_defeated * 3 + s.floors_cleared * 5
            mood = 8
        elif s.floors_cleared > 0:
            outcome = GameOutcome.DRAW  # Partial progress
            xp = 10 + s.monsters_defeated * 2 + s.floors_cleared * 3
            mood = 0
        else:
            outcome = GameOutcome.LOSE
            xp = 5 + s.monsters_defeated * 2
            mood = -3

        return GameResult(
            game_type=GameType.DUNGEON,
            outcome=outcome,
            buddy_id=0,
            score={"floors": s.floors_cleared, "monsters": s.monsters_defeated,
                   "gold": s.gold, "items": len(s.items), "cleared": cleared_all},
            xp_earned=xp,
            mood_delta=mood,
        )
