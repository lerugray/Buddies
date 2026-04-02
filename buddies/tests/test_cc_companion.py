"""Tests for the CC Companion auto-detection module."""

import json
import pytest

from buddies.core.cc_companion import (
    map_cc_species, get_species_obj, map_cc_rarity, clamp_stat,
    build_cc_buddy_data, detect_cc_buddy, _normalize_cc_data,
    _read_manual_override, _read_cc_config_file, _read_cc_settings_buddy,
    CC_SPECIES_MAP, CC_RARITY_MAP,
)
from buddies.core.buddy_brain import SPECIES_CATALOG


# ---------------------------------------------------------------------------
# Species mapping tests
# ---------------------------------------------------------------------------

class TestSpeciesMapping:
    def test_map_cc_species_known(self):
        assert map_cc_species("duck") == "duck"
        assert map_cc_species("blob") == "slime"
        assert map_cc_species("turtle") == "coopa"
        assert map_cc_species("cactus") == "tree"

    def test_map_cc_species_unknown(self):
        assert map_cc_species("unicorn") == "duck"
        assert map_cc_species("") == "duck"
        assert map_cc_species("xyzzy") == "duck"

    def test_map_cc_species_case_insensitive(self):
        assert map_cc_species("Duck") == "duck"
        assert map_cc_species("BLOB") == "slime"


# ---------------------------------------------------------------------------
# Rarity mapping tests
# ---------------------------------------------------------------------------

class TestRarityMapping:
    def test_map_cc_rarity_all(self):
        assert map_cc_rarity("common") == "common"
        assert map_cc_rarity("uncommon") == "uncommon"
        assert map_cc_rarity("rare") == "rare"
        assert map_cc_rarity("epic") == "epic"
        assert map_cc_rarity("legendary") == "legendary"

    def test_map_cc_rarity_unknown(self):
        assert map_cc_rarity("mythic") == "common"
        assert map_cc_rarity("") == "common"
        assert map_cc_rarity("SUPER_RARE") == "common"


# ---------------------------------------------------------------------------
# Stat clamping tests
# ---------------------------------------------------------------------------

class TestClampStat:
    def test_clamp_stat_range(self):
        assert clamp_stat(50) == 50
        assert clamp_stat(1) == 1
        assert clamp_stat(99) == 99

    def test_clamp_stat_below(self):
        assert clamp_stat(0) == 1
        assert clamp_stat(-10) == 1

    def test_clamp_stat_above(self):
        assert clamp_stat(100) == 99
        assert clamp_stat(999) == 99

    def test_clamp_stat_float(self):
        assert clamp_stat(50.7) == 50
        assert clamp_stat(0.5) == 1


# ---------------------------------------------------------------------------
# Species object lookup tests
# ---------------------------------------------------------------------------

class TestGetSpeciesObj:
    def test_get_species_obj_found(self):
        species = get_species_obj("duck")
        assert species.name == "duck"

    def test_get_species_obj_unknown(self):
        species = get_species_obj("nonexistent_species")
        assert species == SPECIES_CATALOG[0]


# ---------------------------------------------------------------------------
# Build CC buddy data tests
# ---------------------------------------------------------------------------

class TestBuildCCBuddyData:
    def test_build_cc_buddy_data_basic(self):
        data = build_cc_buddy_data(name="Quackers", cc_species="duck")
        assert data["name"] == "Quackers"
        assert data["species"] == "duck"
        assert data["source"] == "cc_companion"
        assert "stats" in data
        assert "soul_description" in data
        assert "shiny" in data

    def test_build_cc_buddy_data_with_stats(self):
        stats = {"debugging": 50, "patience": 200, "chaos": -5, "wisdom": 30, "snark": 10}
        data = build_cc_buddy_data(name="Statsy", cc_species="duck", stats=stats)
        assert data["stats"]["debugging"] == 50
        assert data["stats"]["patience"] == 99   # clamped
        assert data["stats"]["chaos"] == 1        # clamped
        assert data["stats"]["wisdom"] == 30
        assert data["stats"]["snark"] == 10

    def test_build_cc_buddy_data_without_stats(self):
        data = build_cc_buddy_data(name="NoStats", cc_species="duck")
        # Stats should be derived from species base_stats
        for stat in ["debugging", "patience", "chaos", "wisdom", "snark"]:
            assert stat in data["stats"]
            assert isinstance(data["stats"][stat], int)

    def test_build_cc_buddy_data_species_mapping(self):
        data = build_cc_buddy_data(name="Blobby", cc_species="blob")
        assert data["species"] == "slime"
        # Soul description should mention the original CC species when remapped
        assert "blob" in data["soul_description"].lower()

    def test_build_cc_buddy_data_same_species_no_cc_note(self):
        data = build_cc_buddy_data(name="Ducky", cc_species="duck")
        # When species maps to same name, no "(CC species: ...)" suffix
        assert "(CC species:" not in data["soul_description"]

    def test_build_cc_buddy_data_personality(self):
        data = build_cc_buddy_data(name="Pers", cc_species="duck", personality="Very snarky")
        assert data["soul_description"] == "Very snarky"


# ---------------------------------------------------------------------------
# Normalize CC data tests
# ---------------------------------------------------------------------------

class TestNormalizeCCData:
    def test_normalize_cc_data_flat_stats(self):
        raw = {"name": "Flat", "species": "duck", "debugging": 25, "patience": 30}
        result = _normalize_cc_data(raw)
        assert result["stats"]["debugging"] == 25
        assert result["stats"]["patience"] == 30

    def test_normalize_cc_data_nested_stats(self):
        raw = {"name": "Nested", "species": "duck", "stats": {"debugging": 40, "chaos": 55}}
        result = _normalize_cc_data(raw)
        assert result["stats"]["debugging"] == 40
        assert result["stats"]["chaos"] == 55

    def test_normalize_cc_data_caps_stats(self):
        raw = {"name": "Caps", "species": "duck", "DEBUGGING": 33, "WISDOM": 44}
        result = _normalize_cc_data(raw)
        assert result["stats"]["debugging"] == 33
        assert result["stats"]["wisdom"] == 44

    def test_normalize_cc_data_string_limits(self):
        raw = {"name": "A" * 200, "species": "B" * 100, "personality": "C" * 1000}
        result = _normalize_cc_data(raw)
        assert len(result["name"]) <= 50
        assert len(result["species"]) <= 30
        assert len(result["personality"]) <= 500

    def test_normalize_cc_data_defaults(self):
        raw = {}
        result = _normalize_cc_data(raw)
        assert result["name"] == "CC Buddy"
        assert result["species"] == "duck"
        assert result["rarity"] == "common"
        assert result["shiny"] is False


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

class TestDetectCCBuddy:
    def test_detect_cc_buddy_no_config(self, tmp_path, monkeypatch):
        """Returns None when no config files exist."""
        monkeypatch.setattr("buddies.core.cc_companion.CC_CONFIG_PATHS", [
            tmp_path / "buddy.json",
            tmp_path / "companion.json",
        ])
        monkeypatch.setattr("buddies.core.cc_companion.Path.home", lambda: tmp_path)
        # Also stub out _read_manual_override to return None
        monkeypatch.setattr("buddies.core.cc_companion._read_manual_override", lambda: None)
        monkeypatch.setattr("buddies.core.cc_companion._read_cc_settings_buddy", lambda: None)
        result = detect_cc_buddy()
        assert result is None

    def test_read_manual_override_with_config(self, tmp_path, monkeypatch):
        """Reads cc_buddy from Buddies config when present."""
        config_dir = tmp_path / "buddy"
        config_dir.mkdir()
        config_data = {
            "cc_buddy": {
                "name": "Override",
                "species": "cat",
                "rarity": "rare",
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config_data), encoding="utf-8")

        # Redirect where the function looks for the config
        if __import__("os").name == "nt":
            monkeypatch.setenv("APPDATA", str(tmp_path))
        else:
            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

        result = _read_manual_override()
        assert result is not None
        assert result["name"] == "Override"
        assert result["species"] == "cat"

    def test_read_cc_config_file_missing(self, tmp_path, monkeypatch):
        """Returns None when no CC config files exist."""
        monkeypatch.setattr("buddies.core.cc_companion.CC_CONFIG_PATHS", [
            tmp_path / "nonexistent1.json",
            tmp_path / "nonexistent2.json",
        ])
        result = _read_cc_config_file()
        assert result is None

    def test_read_cc_config_file_found(self, tmp_path, monkeypatch):
        """Reads CC buddy from a config file when present."""
        config_path = tmp_path / "buddy.json"
        config_path.write_text(json.dumps({"name": "Found", "species": "owl"}), encoding="utf-8")
        monkeypatch.setattr("buddies.core.cc_companion.CC_CONFIG_PATHS", [config_path])
        result = _read_cc_config_file()
        assert result is not None
        assert result["name"] == "Found"
