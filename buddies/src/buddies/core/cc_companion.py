"""CC Companion integration — bridge between Claude Code's /buddy and Buddies.

Maps CC companion species/stats into the Buddies party system so the
official CC buddy can coexist with your collection.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from buddies.core.buddy_brain import SPECIES_CATALOG, Species, Rarity

log = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Tier 3: Auto-detect CC buddy from config
# ---------------------------------------------------------------------------

# Possible locations where CC might store buddy config
CC_CONFIG_PATHS = [
    Path.home() / ".claude" / "buddy.json",
    Path.home() / ".claude" / "companion.json",
    Path.home() / ".claude" / "cache" / "buddy.json",
]


def _read_cc_config_file() -> dict | None:
    """Try to read CC buddy data from known config file locations."""
    for path in CC_CONFIG_PATHS:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "name" in data:
                    log.info("Found CC buddy config at %s", path)
                    return data
            except (json.JSONDecodeError, OSError) as e:
                log.debug("Failed to read %s: %s", path, e)
    return None


def _read_cc_settings_buddy() -> dict | None:
    """Check CC's settings.json for a buddy/companion key."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        # Check for buddy or companion keys
        for key in ("buddy", "companion", "pet"):
            if key in data and isinstance(data[key], dict):
                buddy_data = data[key]
                if "name" in buddy_data:
                    log.info("Found CC buddy in settings.json under '%s'", key)
                    return buddy_data
    except (json.JSONDecodeError, OSError) as e:
        log.debug("Failed to read CC settings: %s", e)
    return None


def _read_manual_override() -> dict | None:
    """Read CC buddy override from Buddies' own config.json."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    config_path = base / "buddy" / "config.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        cc_data = data.get("cc_buddy")
        if isinstance(cc_data, dict) and cc_data.get("name"):
            log.info("Found CC buddy manual override in Buddies config")
            return cc_data
    except (json.JSONDecodeError, OSError) as e:
        log.debug("Failed to read Buddies config for CC override: %s", e)
    return None


def detect_cc_buddy() -> dict | None:
    """Try all detection methods to find a CC companion.

    Returns a dict with keys: name, species, rarity, stats, personality, shiny
    or None if no CC buddy detected.

    Detection priority:
    1. Manual override in Buddies' config.json (most reliable)
    2. CC's dedicated buddy config file (if it exists)
    3. CC's settings.json buddy key (if present)
    """
    # Priority 1: Manual override
    data = _read_manual_override()
    if data:
        return _normalize_cc_data(data)

    # Priority 2: Dedicated CC config file
    data = _read_cc_config_file()
    if data:
        return _normalize_cc_data(data)

    # Priority 3: CC settings.json
    data = _read_cc_settings_buddy()
    if data:
        return _normalize_cc_data(data)

    return None


def _normalize_cc_data(raw: dict) -> dict:
    """Normalize raw CC buddy data into a standard format."""
    # Support both flat stats and nested stats dict
    stats = raw.get("stats", {})
    if not stats:
        stats = {
            "debugging": raw.get("debugging", raw.get("DEBUGGING", 10)),
            "patience": raw.get("patience", raw.get("PATIENCE", 10)),
            "chaos": raw.get("chaos", raw.get("CHAOS", 10)),
            "wisdom": raw.get("wisdom", raw.get("WISDOM", 10)),
            "snark": raw.get("snark", raw.get("SNARK", 10)),
        }

    return {
        "name": str(raw.get("name", "CC Buddy"))[:50],
        "species": str(raw.get("species", "duck"))[:30],
        "rarity": str(raw.get("rarity", "common"))[:20],
        "stats": {k: clamp_stat(v) for k, v in stats.items()},
        "personality": str(raw.get("personality", ""))[:500],
        "shiny": bool(raw.get("shiny", False)),
    }
