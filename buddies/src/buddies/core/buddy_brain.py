"""Buddy's personality, stats, species, and evolution logic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum


class Rarity(Enum):
    COMMON = "common"        # 40%
    UNCOMMON = "uncommon"    # 30%
    RARE = "rare"            # 18%
    EPIC = "epic"            # 9%
    LEGENDARY = "legendary"  # 3%


@dataclass
class Species:
    name: str
    emoji: str
    rarity: Rarity
    base_stats: dict[str, int]  # Base stat modifiers
    description: str


# All available species
SPECIES_CATALOG: list[Species] = [
    # Common (40%)
    Species("duck", "🦆", Rarity.COMMON, {"patience": 3, "snark": 2}, "A steadfast rubber duck debugger."),
    Species("cat", "🐱", Rarity.COMMON, {"chaos": 3, "wisdom": 2}, "Knocks things off the stack."),
    Species("frog", "🐸", Rarity.COMMON, {"patience": 2, "debugging": 3}, "Catches bugs. Literally."),
    Species("hamster", "🐹", Rarity.COMMON, {"patience": 3, "chaos": 2}, "Runs in circles but gets there eventually."),
    # Uncommon (30%)
    Species("owl", "🦉", Rarity.UNCOMMON, {"wisdom": 4, "patience": 2}, "Sees what others miss in the dark."),
    Species("fox", "🦊", Rarity.UNCOMMON, {"snark": 3, "debugging": 3}, "Clever. Suspiciously clever."),
    Species("axolotl", "🦎", Rarity.UNCOMMON, {"patience": 4, "chaos": 1}, "Regenerates from any setback."),
    Species("penguin", "🐧", Rarity.UNCOMMON, {"debugging": 3, "wisdom": 2}, "Thrives in cold, hostile environments."),
    # Rare (18%)
    Species("dragon", "🐉", Rarity.RARE, {"chaos": 4, "debugging": 3}, "Burns bad code to ash."),
    Species("capybara", "🦫", Rarity.RARE, {"patience": 5, "wisdom": 3}, "Everyone gets along with capybara."),
    Species("mushroom", "🍄", Rarity.RARE, {"wisdom": 4, "chaos": 3}, "Networked intelligence. Mycelium mind."),
    # Epic (9%)
    Species("phoenix", "🔥", Rarity.EPIC, {"debugging": 5, "wisdom": 4}, "Rises from the ashes of failed builds."),
    Species("kraken", "🦑", Rarity.EPIC, {"chaos": 5, "snark": 4}, "Tentacles in every codebase."),
    Species("unicorn", "🦄", Rarity.EPIC, {"wisdom": 5, "patience": 3}, "Mythically productive."),
    # Legendary (3%)
    Species("ghost", "👻", Rarity.LEGENDARY, {"chaos": 5, "debugging": 5}, "Haunts your codebase. Finds dead code."),
    Species("cosmic_whale", "🐋", Rarity.LEGENDARY, {"wisdom": 6, "patience": 5}, "Swims through the void between commits."),
    # Additional species (Phase 5+)
    Species("bee", "🐝", Rarity.COMMON, {"patience": 3, "chaos": 2}, "Busy little helper. Productive but chaotic."),
    Species("slime", "🫧", Rarity.COMMON, {"chaos": 3, "snark": 2}, "Gooey. Literally flows through problems."),
    Species("raccoon", "🦝", Rarity.UNCOMMON, {"snark": 3, "chaos": 3}, "Sneaky troublemaker. Clever and mischievous."),
    Species("parrot", "🦜", Rarity.UNCOMMON, {"snark": 3, "wisdom": 2}, "Repeats everything but with personality."),
    Species("octopus", "🐙", Rarity.RARE, {"wisdom": 4, "debugging": 3}, "Multi-tasking maestro. Tentacles everywhere."),
    Species("wolf", "🐺", Rarity.RARE, {"debugging": 3, "patience": 2}, "Pack hunter. Methodical and focused."),
    Species("robot", "🤖", Rarity.EPIC, {"debugging": 5, "wisdom": 4}, "Perfectly logical. Almost sentient."),
    Species("tree", "🌳", Rarity.LEGENDARY, {"patience": 6, "wisdom": 5}, "Ancient and grounded. Roots run deep."),
    Species("void_cat", "🐈‍⬛", Rarity.LEGENDARY, {"chaos": 5, "snark": 5}, "From the void itself. Exists slightly off-phase."),
]

# Rarity weights for the gacha
RARITY_WEIGHTS: dict[Rarity, float] = {
    Rarity.COMMON: 0.40,
    Rarity.UNCOMMON: 0.30,
    Rarity.RARE: 0.18,
    Rarity.EPIC: 0.09,
    Rarity.LEGENDARY: 0.03,
}

MOODS = {
    "ecstatic": (80, 100),
    "happy": (60, 79),
    "neutral": (40, 59),
    "bored": (20, 39),
    "grumpy": (0, 19),
}


def mulberry32(seed: int) -> float:
    """Mulberry32 PRNG — deterministic float from seed."""
    seed = (seed + 0x6D2B79F5) & 0xFFFFFFFF
    t = (seed ^ (seed >> 15)) * (seed | 1)
    t = (t ^ (t + (t ^ (t >> 7)) * (t | 61))) & 0xFFFFFFFF
    return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 0xFFFFFFFF


def hash_seed(user_seed: str, salt: str = "buddy-2026") -> int:
    """Hash a user seed string to a 32-bit integer."""
    h = 0
    for char in f"{salt}:{user_seed}":
        h = ((h << 5) - h + ord(char)) & 0xFFFFFFFF
    return h


def pick_species(user_seed: str) -> tuple[Species, bool]:
    """Deterministically pick a species and shiny status from a user seed.

    Returns (species, is_shiny).
    """
    seed = hash_seed(user_seed)

    # Roll for rarity
    rarity_roll = mulberry32(seed)
    cumulative = 0.0
    chosen_rarity = Rarity.COMMON
    for rarity, weight in RARITY_WEIGHTS.items():
        cumulative += weight
        if rarity_roll <= cumulative:
            chosen_rarity = rarity
            break

    # Filter species by rarity and pick one
    candidates = [s for s in SPECIES_CATALOG if s.rarity == chosen_rarity]
    species_roll = mulberry32(seed ^ 0xDEADBEEF)
    idx = int(species_roll * len(candidates)) % len(candidates)
    species = candidates[idx]

    # 5% chance of shiny
    shiny_roll = mulberry32(seed ^ 0xCAFEBABE)
    is_shiny = shiny_roll < 0.05

    return species, is_shiny


def get_mood(mood_value: int) -> str:
    """Get mood name from mood value (0-100)."""
    for mood, (low, high) in MOODS.items():
        if low <= mood_value <= high:
            return mood
    return "neutral"


def calculate_level(xp: int) -> int:
    """Calculate level from XP. Each level needs more XP."""
    level = 1
    xp_needed = 100
    remaining = xp
    while remaining >= xp_needed:
        remaining -= xp_needed
        level += 1
        xp_needed = int(xp_needed * 1.5)
    return level


def xp_for_next_level(level: int) -> int:
    """Calculate total XP needed to reach the next level."""
    xp = 0
    xp_needed = 100
    for _ in range(1, level):
        xp += xp_needed
        xp_needed = int(xp_needed * 1.5)
    return xp + xp_needed


# Hat unlock rules based on dominant stat and level
HAT_UNLOCK_RULES: dict[str, dict] = {
    "crown": {"dominant_stat": "debugging", "min_level": 5},
    "wizard": {"dominant_stat": "wisdom", "min_level": 5},
    "propeller": {"dominant_stat": "chaos", "min_level": 5},
    "tinyduck": {"dominant_stat": None, "min_level": 0},  # Given at hatch
}


def check_hat_unlock(state: BuddyState) -> list[str]:
    """Check which hats are newly unlocked for this buddy state.

    Returns list of hat names that are newly unlocked (not yet owned).
    """
    newly_unlocked = []

    for hat_name, rules in HAT_UNLOCK_RULES.items():
        # tinyduck is given at hatch, not earned
        if hat_name == "tinyduck":
            continue

        # Check if already owned
        if hat_name in state.hats_owned:
            continue

        # Check level requirement
        if state.level < rules["min_level"]:
            continue

        # Check dominant stat requirement
        dominant_stat = rules["dominant_stat"]
        if dominant_stat:
            max_stat = max(state.stats.values())
            if state.stats[dominant_stat] != max_stat:
                continue

        newly_unlocked.append(hat_name)

    return newly_unlocked


@dataclass
class BuddyState:
    """Runtime representation of the buddy's current state."""

    buddy_id: int
    species: Species
    name: str
    shiny: bool
    stats: dict[str, int]
    xp: int
    level: int
    mood: str
    mood_value: int
    soul_description: str
    hat: str | None
    hats_owned: list[str]

    @classmethod
    def from_db(cls, data: dict) -> BuddyState:
        species_obj = next(
            (s for s in SPECIES_CATALOG if s.name == data["species"]),
            SPECIES_CATALOG[0],
        )
        return cls(
            buddy_id=data["id"],
            species=species_obj,
            name=data["name"],
            shiny=bool(data["shiny"]),
            stats={
                "debugging": data["stat_debugging"],
                "patience": data["stat_patience"],
                "chaos": data["stat_chaos"],
                "wisdom": data["stat_wisdom"],
                "snark": data["stat_snark"],
            },
            xp=data["xp"],
            level=data["level"],
            mood=data["mood"],
            mood_value=data["mood_value"],
            soul_description=data["soul_description"],
            hat=data.get("hat"),
            hats_owned=json.loads(data.get("hats_owned", "[]")),
        )

    def gain_xp(self, amount: int) -> bool:
        """Add XP and return True if leveled up."""
        old_level = self.level
        self.xp += amount
        self.level = calculate_level(self.xp)
        return self.level > old_level

    def adjust_mood(self, delta: int):
        """Shift mood value by delta, clamped 0-100."""
        self.mood_value = max(0, min(100, self.mood_value + delta))
        self.mood = get_mood(self.mood_value)

    def stat_total(self) -> int:
        return sum(self.stats.values())
