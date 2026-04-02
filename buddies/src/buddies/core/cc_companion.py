"""CC Companion integration — bridge between Claude Code's /buddy and Buddies.

Maps CC companion species/stats into the Buddies party system so the
official CC buddy can coexist with your collection.
"""

from __future__ import annotations

from buddies.core.buddy_brain import SPECIES_CATALOG, Species, Rarity

# ---------------------------------------------------------------------------
# Species mapping: CC's 18 species → closest Buddies species
# ---------------------------------------------------------------------------

CC_SPECIES_MAP: dict[str, str] = {
    "duck": "duck",
    "goose": "duck",         # closest waterfowl
    "blob": "slime",         # gooey things
    "cat": "cat",
    "dragon": "dragon",
    "octopus": "octopus",
    "owl": "owl",
    "penguin": "penguin",
    "turtle": "coopa",       # turtle troopa
    "snail": "snail",
    "ghost": "ghost",
    "axolotl": "axolotl",
    "capybara": "capybara",
    "cactus": "tree",        # closest plant life
    "robot": "robot",
    "rabbit": "hamster",     # small fluffy creature
    "mushroom": "mushroom",
    "chonk": "chonk",
}

CC_RARITY_MAP: dict[str, str] = {
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "epic": "epic",
    "legendary": "legendary",
}


def map_cc_species(cc_species: str) -> str:
    """Map a CC companion species name to the closest Buddies species."""
    return CC_SPECIES_MAP.get(cc_species.lower(), "duck")


def get_species_obj(species_name: str) -> Species:
    """Look up a Buddies Species object by name."""
    for s in SPECIES_CATALOG:
        if s.name == species_name:
            return s
    return SPECIES_CATALOG[0]  # fallback to duck


def map_cc_rarity(cc_rarity: str) -> str:
    """Map a CC rarity string to Buddies rarity."""
    return CC_RARITY_MAP.get(cc_rarity.lower(), "common")


def clamp_stat(value: int | float) -> int:
    """Clamp a stat value to the valid 1-99 range."""
    return max(1, min(99, int(value)))


def build_cc_buddy_data(
    name: str,
    cc_species: str,
    cc_rarity: str = "common",
    stats: dict[str, int] | None = None,
    personality: str = "",
    shiny: bool = False,
) -> dict:
    """Build the data dict for creating a CC-imported buddy in the DB.

    Returns a dict ready to pass to BuddyStore.create_cc_buddy().
    """
    buddies_species = map_cc_species(cc_species)
    species_obj = get_species_obj(buddies_species)

    # Use provided stats or derive from species base stats
    if stats:
        final_stats = {
            "debugging": clamp_stat(stats.get("debugging", 10)),
            "patience": clamp_stat(stats.get("patience", 10)),
            "chaos": clamp_stat(stats.get("chaos", 10)),
            "wisdom": clamp_stat(stats.get("wisdom", 10)),
            "snark": clamp_stat(stats.get("snark", 10)),
        }
    else:
        final_stats = {
            "debugging": 10 + species_obj.base_stats.get("debugging", 0) * 3,
            "patience": 10 + species_obj.base_stats.get("patience", 0) * 3,
            "chaos": 10 + species_obj.base_stats.get("chaos", 0) * 3,
            "wisdom": 10 + species_obj.base_stats.get("wisdom", 0) * 3,
            "snark": 10 + species_obj.base_stats.get("snark", 0) * 3,
        }

    soul = personality or f"Imported from Claude Code's /buddy system. Originally a {cc_species}."
    if cc_species.lower() != buddies_species:
        soul += f" (CC species: {cc_species})"

    return {
        "species": buddies_species,
        "name": name,
        "shiny": shiny,
        "stats": final_stats,
        "soul_description": soul,
        "source": "cc_companion",
    }
