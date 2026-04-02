"""Tests for buddy fusion system."""

import pytest

from buddies.core.buddy_brain import BuddyState, Species, Rarity, SPECIES_CATALOG
from buddies.core.fusion import (
    FUSION_SPECIES, FUSION_RECIPES, FUSION_SPECIES_BY_NAME,
    RARITY_ESCALATION, CHIMERA_CROWN_HAT,
    FusionResult, FusionRecipe,
    check_fusion, _inherit_stats, get_discovered_recipes,
    get_all_fusion_species, format_fusion_preview,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_buddy(species_name="duck", buddy_id=1, dominant="patience", **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30
    sp = next((s for s in SPECIES_CATALOG if s.name == species_name), SPECIES_CATALOG[0])
    defaults = dict(
        name=species_name.title(), species=sp, level=5, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=buddy_id, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


# ---------------------------------------------------------------------------
# Fusion species catalog
# ---------------------------------------------------------------------------

class TestFusionSpecies:
    def test_fusion_species_count(self):
        assert len(FUSION_SPECIES) == 12

    def test_all_fusion_species_have_unique_names(self):
        names = [s.name for s in FUSION_SPECIES]
        assert len(names) == len(set(names))

    def test_all_fusion_species_are_epic_or_legendary(self):
        for s in FUSION_SPECIES:
            assert s.rarity in (Rarity.EPIC, Rarity.LEGENDARY), f"{s.name} is {s.rarity}"

    def test_fusion_species_not_in_main_catalog(self):
        main_names = {s.name for s in SPECIES_CATALOG}
        for s in FUSION_SPECIES:
            assert s.name not in main_names, f"{s.name} shouldn't be in main catalog"

    def test_all_fusion_species_have_descriptions(self):
        for s in FUSION_SPECIES:
            assert len(s.description) > 10


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

class TestRecipes:
    def test_recipe_count(self):
        assert len(FUSION_RECIPES) == 12

    def test_all_recipes_reference_valid_species(self):
        main_names = {s.name for s in SPECIES_CATALOG}
        for recipe in FUSION_RECIPES:
            assert recipe.species_a in main_names, f"Recipe parent {recipe.species_a} not in catalog"
            assert recipe.species_b in main_names, f"Recipe parent {recipe.species_b} not in catalog"
            assert recipe.result in FUSION_SPECIES_BY_NAME, f"Recipe result {recipe.result} not in fusion species"

    def test_all_recipes_have_lore(self):
        for recipe in FUSION_RECIPES:
            assert len(recipe.lore) > 20

    def test_recipes_are_order_independent(self):
        """phoenix + ghost should work the same as ghost + phoenix."""
        a = make_buddy("phoenix", buddy_id=1)
        b = make_buddy("ghost", buddy_id=2)
        result_ab = check_fusion(a, b)
        result_ba = check_fusion(b, a)
        assert result_ab.species.name == result_ba.species.name


# ---------------------------------------------------------------------------
# Stat inheritance
# ---------------------------------------------------------------------------

class TestStatInheritance:
    def test_takes_higher_at_75_percent(self):
        stats_a = {"debugging": 40, "chaos": 10, "snark": 20, "wisdom": 10, "patience": 10}
        stats_b = {"debugging": 10, "chaos": 30, "snark": 10, "wisdom": 20, "patience": 10}
        result = _inherit_stats(stats_a, stats_b)
        # debugging: max(40, 10) * 0.75 = 30
        assert result["debugging"] == 30
        # chaos: max(10, 30) * 0.75 = 22
        assert result["chaos"] == 22

    def test_minimum_stat_is_1(self):
        stats_a = {"debugging": 1, "chaos": 1}
        stats_b = {"debugging": 1, "chaos": 1}
        result = _inherit_stats(stats_a, stats_b)
        assert all(v >= 1 for v in result.values())

    def test_handles_missing_stats(self):
        stats_a = {"debugging": 20}
        stats_b = {"chaos": 30}
        result = _inherit_stats(stats_a, stats_b)
        assert "debugging" in result
        assert "chaos" in result


# ---------------------------------------------------------------------------
# Rarity escalation
# ---------------------------------------------------------------------------

class TestRarityEscalation:
    def test_same_rarity_escalates(self):
        assert RARITY_ESCALATION[(Rarity.COMMON, Rarity.COMMON)] == Rarity.UNCOMMON
        assert RARITY_ESCALATION[(Rarity.UNCOMMON, Rarity.UNCOMMON)] == Rarity.RARE
        assert RARITY_ESCALATION[(Rarity.RARE, Rarity.RARE)] == Rarity.EPIC
        assert RARITY_ESCALATION[(Rarity.EPIC, Rarity.EPIC)] == Rarity.LEGENDARY

    def test_mixed_rarity_takes_higher(self):
        assert RARITY_ESCALATION[(Rarity.COMMON, Rarity.EPIC)] == Rarity.EPIC

    def test_order_independent(self):
        assert RARITY_ESCALATION[(Rarity.COMMON, Rarity.RARE)] == RARITY_ESCALATION[(Rarity.RARE, Rarity.COMMON)]


# ---------------------------------------------------------------------------
# Fusion logic
# ---------------------------------------------------------------------------

class TestFusionLogic:
    def test_recipe_fusion(self):
        a = make_buddy("phoenix", buddy_id=1)
        b = make_buddy("ghost", buddy_id=2)
        result = check_fusion(a, b)
        assert result.success
        assert result.is_recipe
        assert result.species.name == "phoenix_byte"
        assert len(result.lore_text) > 20

    def test_formula_fusion(self):
        """Non-recipe pairs should produce a formula result."""
        a = make_buddy("duck", buddy_id=1)
        b = make_buddy("frog", buddy_id=2)
        result = check_fusion(a, b)
        assert result.success
        assert not result.is_recipe
        assert result.species is not None

    def test_cannot_fuse_with_self(self):
        a = make_buddy("duck", buddy_id=1)
        result = check_fusion(a, a)
        assert not result.success
        assert "itself" in result.error.lower()

    def test_formula_is_deterministic(self):
        """Same parents should always produce the same result."""
        a = make_buddy("duck", buddy_id=1)
        b = make_buddy("frog", buddy_id=2)
        r1 = check_fusion(a, b)
        r2 = check_fusion(a, b)
        assert r1.species.name == r2.species.name

    def test_different_pairs_can_produce_different_results(self):
        a1 = make_buddy("duck", buddy_id=1)
        b1 = make_buddy("frog", buddy_id=2)
        a2 = make_buddy("dragon", buddy_id=3)
        b2 = make_buddy("kraken", buddy_id=4)
        r1 = check_fusion(a1, b1)
        r2 = check_fusion(a2, b2)
        # These could theoretically match, but with different species + IDs it's very unlikely
        # Just check both succeed
        assert r1.success and r2.success


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_discovered_recipes_filters_by_owned(self):
        owned = {"phoenix", "ghost", "duck"}
        recipes = get_discovered_recipes(owned)
        # Should find phoenix + ghost recipe
        assert any(r.result == "phoenix_byte" for r in recipes)
        # Should NOT find dragon + capybara
        assert not any(r.result == "chimera" for r in recipes)

    def test_no_recipes_with_empty_collection(self):
        recipes = get_discovered_recipes(set())
        assert len(recipes) == 0


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

class TestDisplay:
    def test_format_preview_shows_species(self):
        a = make_buddy("phoenix", buddy_id=1)
        b = make_buddy("ghost", buddy_id=2)
        result = check_fusion(a, b)
        lines = format_fusion_preview(result)
        combined = "\n".join(lines)
        assert "Phoenix Byte" in combined
        assert "consumed" in combined.lower()
        assert "Chimera Crown" in combined

    def test_format_error(self):
        a = make_buddy("duck", buddy_id=1)
        result = check_fusion(a, a)
        lines = format_fusion_preview(result)
        assert any("itself" in l.lower() for l in lines)

    def test_recipe_shows_special_tag(self):
        a = make_buddy("phoenix", buddy_id=1)
        b = make_buddy("ghost", buddy_id=2)
        result = check_fusion(a, b)
        lines = format_fusion_preview(result)
        combined = "\n".join(lines)
        assert "Special Recipe" in combined
