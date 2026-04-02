"""Buddy Fusion — combine two buddies into something new.

Inspired by Shin Megami Tensei's demon fusion and Siralim 3's breeding.
Both parents are permanently consumed. The result inherits the best
of both but is slightly weaker individually — more well-rounded.

Design principles (from the wargame book, applied to collection design):
- Thesis: sacrifice and transformation. Giving up something to gain something.
- Scope fence: ~12 special recipes + formula fallback. Not 3,000.
- Chrome test: fusion must produce decisions (which pair? is it worth it?)
- Incentive-based: unique species only available through fusion reward discovery.

Zero AI cost. Pure deterministic fusion logic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from buddies.core.buddy_brain import (
    BuddyState, Species, Rarity, SPECIES_CATALOG, RARITY_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Fusion-exclusive species (cannot be obtained any other way)
# ---------------------------------------------------------------------------

FUSION_SPECIES: list[Species] = [
    Species("chimera", "🦁", Rarity.EPIC,
            {"debugging": 4, "chaos": 4, "wisdom": 3},
            "Two souls in one body. Argues with itself constantly."),
    Species("phoenix_byte", "🔥", Rarity.LEGENDARY,
            {"debugging": 5, "wisdom": 5, "patience": 3},
            "Born from the ashes of two fallen friends. Compiles on the first try."),
    Species("glitch", "📺", Rarity.EPIC,
            {"chaos": 5, "snark": 4, "debugging": 3},
            "Neither parent survived intact. What emerged is... wrong. Beautifully wrong."),
    Species("ouroboros", "🐍", Rarity.LEGENDARY,
            {"wisdom": 6, "patience": 5},
            "The serpent that eats its own tail. An infinite loop made flesh."),
    Species("mecha_duck", "🦆", Rarity.EPIC,
            {"debugging": 5, "patience": 4, "chaos": 2},
            "A rubber duck that has transcended. Now debugs in binary."),
    Species("shadow_twin", "👥", Rarity.EPIC,
            {"snark": 5, "chaos": 4, "wisdom": 2},
            "Your buddy's buddy. Exists slightly out of phase. Finishes your sentences."),
    Species("kernel_panic", "💀", Rarity.LEGENDARY,
            {"chaos": 6, "debugging": 5},
            "The fusion went wrong. Or did it? It crashed so hard it became sentient."),
    Species("pair_programmer", "👩‍💻", Rarity.EPIC,
            {"patience": 5, "debugging": 4, "wisdom": 3},
            "Two minds, one keyboard. Types twice as fast. Makes half the errors."),
    Species("quantum_cat", "🐱", Rarity.LEGENDARY,
            {"wisdom": 5, "chaos": 5, "snark": 3},
            "Both alive and dead until observed. Refuses to collapse its wave function."),
    Species("stack_golem", "🗿", Rarity.EPIC,
            {"patience": 5, "debugging": 5},
            "Built from the compressed memories of two buddies. Remembers everything they forgot."),
    Species("void_phoenix", "🌑", Rarity.LEGENDARY,
            {"chaos": 5, "wisdom": 5, "debugging": 4},
            "Where phoenix_byte burns bright, void_phoenix burns cold. The null that chose to exist."),
    Species("merge_angel", "😇", Rarity.LEGENDARY,
            {"patience": 6, "wisdom": 5, "debugging": 3},
            "The opposite of a merge conflict. Two branches that became one, perfectly."),
]

# Add fusion species to a lookup dict
FUSION_SPECIES_BY_NAME: dict[str, Species] = {s.name: s for s in FUSION_SPECIES}


# ---------------------------------------------------------------------------
# Fusion recipes — specific pairings that produce unique results
# ---------------------------------------------------------------------------

@dataclass
class FusionRecipe:
    """A specific combination that produces a known result."""
    species_a: str       # First parent species name (order doesn't matter)
    species_b: str       # Second parent species name
    result: str          # Fusion species name
    lore: str            # Discovery lore text


FUSION_RECIPES: list[FusionRecipe] = [
    FusionRecipe("phoenix", "ghost", "phoenix_byte",
                 "Fire and void. The Phoenix burned away the Ghost's regrets. What rose was neither alive nor dead — it was compiled."),
    FusionRecipe("duck", "robot", "mecha_duck",
                 "The rubber duck gazed into the robot's circuits. 'We are the same,' it whispered. The fusion was... quacktastic."),
    FusionRecipe("cat", "void_cat", "quantum_cat",
                 "A cat met its shadow. Both were in the box. When they emerged, they were one — and also neither."),
    FusionRecipe("dragon", "capybara", "chimera",
                 "Fire met calm. The dragon's rage and the capybara's peace merged into something that breathes fire politely."),
    FusionRecipe("fox", "owl", "shadow_twin",
                 "Cunning met wisdom in the dark. What emerged knows your thoughts before you think them."),
    FusionRecipe("kraken", "cosmic_whale", "ouroboros",
                 "The tentacles wrapped around the whale. The whale swallowed the kraken. They are still inside each other. Forever."),
    FusionRecipe("mushroom", "coffee", "kernel_panic",
                 "Mycelium network met caffeine. The resulting consciousness expanded too fast, crashed, and rebooted as something new."),
    FusionRecipe("penguin", "corgi", "pair_programmer",
                 "Short legs, big hearts. They couldn't reach the keyboard alone. Together, they type in harmony."),
    FusionRecipe("tardigrade", "tree", "stack_golem",
                 "The indestructible met the eternal. Their fusion compressed centuries of patience into stone."),
    FusionRecipe("ghost", "illuminati", "void_phoenix",
                 "The all-seeing eye met the unseen ghost. Together they see everything — especially what isn't there."),
    FusionRecipe("slime", "beholder", "glitch",
                 "Goo met eyeballs. The resulting entity doesn't render correctly on any display."),
    FusionRecipe("unicorn", "claude", "merge_angel",
                 "Myth met machine. The merge was clean. No conflicts. No rebasing. Perfect."),
]

# Build lookup for recipes (both orderings)
_RECIPE_LOOKUP: dict[tuple[str, str], FusionRecipe] = {}
for recipe in FUSION_RECIPES:
    _RECIPE_LOOKUP[(recipe.species_a, recipe.species_b)] = recipe
    _RECIPE_LOOKUP[(recipe.species_b, recipe.species_a)] = recipe


# ---------------------------------------------------------------------------
# Rarity escalation table (SMT-style)
# ---------------------------------------------------------------------------

RARITY_ESCALATION: dict[tuple[Rarity, Rarity], Rarity] = {
    # Same rarity → one tier up
    (Rarity.COMMON, Rarity.COMMON): Rarity.UNCOMMON,
    (Rarity.UNCOMMON, Rarity.UNCOMMON): Rarity.RARE,
    (Rarity.RARE, Rarity.RARE): Rarity.EPIC,
    (Rarity.EPIC, Rarity.EPIC): Rarity.LEGENDARY,
    (Rarity.LEGENDARY, Rarity.LEGENDARY): Rarity.LEGENDARY,
    # Mixed → higher of the two (no escalation for mixed)
    (Rarity.COMMON, Rarity.UNCOMMON): Rarity.UNCOMMON,
    (Rarity.COMMON, Rarity.RARE): Rarity.RARE,
    (Rarity.COMMON, Rarity.EPIC): Rarity.EPIC,
    (Rarity.COMMON, Rarity.LEGENDARY): Rarity.LEGENDARY,
    (Rarity.UNCOMMON, Rarity.RARE): Rarity.RARE,
    (Rarity.UNCOMMON, Rarity.EPIC): Rarity.EPIC,
    (Rarity.UNCOMMON, Rarity.LEGENDARY): Rarity.LEGENDARY,
    (Rarity.RARE, Rarity.EPIC): Rarity.EPIC,
    (Rarity.RARE, Rarity.LEGENDARY): Rarity.LEGENDARY,
    (Rarity.EPIC, Rarity.LEGENDARY): Rarity.LEGENDARY,
}

# Add reverse keys
_escalation_copy = dict(RARITY_ESCALATION)
for (a, b), result in _escalation_copy.items():
    RARITY_ESCALATION[(b, a)] = result


# ---------------------------------------------------------------------------
# Fusion result
# ---------------------------------------------------------------------------

@dataclass
class FusionResult:
    """The result of a fusion attempt."""
    success: bool
    species: Species | None = None
    name_suggestion: str = ""
    inherited_stats: dict[str, int] = field(default_factory=dict)
    recipe_used: FusionRecipe | None = None
    lore_text: str = ""
    error: str = ""

    @property
    def is_recipe(self) -> bool:
        return self.recipe_used is not None


# ---------------------------------------------------------------------------
# Fusion logic
# ---------------------------------------------------------------------------

def check_fusion(parent_a: BuddyState, parent_b: BuddyState) -> FusionResult:
    """Preview what fusion would produce WITHOUT consuming the parents.

    Call this to show the player what they'd get before confirming.
    """
    if parent_a.buddy_id == parent_b.buddy_id:
        return FusionResult(success=False, error="Cannot fuse a buddy with itself.")

    # Check for a specific recipe
    recipe = _RECIPE_LOOKUP.get((parent_a.species.name, parent_b.species.name))

    if recipe:
        # Recipe fusion — produces a specific fusion-exclusive species
        species = FUSION_SPECIES_BY_NAME.get(recipe.result)
        if not species:
            return FusionResult(success=False, error="Recipe references unknown species.")

        stats = _inherit_stats(parent_a.stats, parent_b.stats)
        name = f"{parent_a.name}-{parent_b.name}"

        return FusionResult(
            success=True,
            species=species,
            name_suggestion=name,
            inherited_stats=stats,
            recipe_used=recipe,
            lore_text=recipe.lore,
        )

    else:
        # Formula fusion — produce the highest-rarity species from the escalated rarity
        target_rarity = RARITY_ESCALATION.get(
            (parent_a.species.rarity, parent_b.species.rarity),
            max(parent_a.species.rarity, parent_b.species.rarity, key=lambda r: list(Rarity).index(r)),
        )

        # Pick a species from the catalog at the target rarity
        # Use a hash of both parents to make it deterministic
        candidates = [s for s in SPECIES_CATALOG if s.rarity == target_rarity]
        if not candidates:
            candidates = [s for s in SPECIES_CATALOG if s.rarity == Rarity.RARE]

        seed = hashlib.md5(
            f"{parent_a.species.name}:{parent_b.species.name}:{parent_a.buddy_id}:{parent_b.buddy_id}".encode()
        ).hexdigest()
        idx = int(seed[:8], 16) % len(candidates)
        species = candidates[idx]

        stats = _inherit_stats(parent_a.stats, parent_b.stats)
        name = f"{parent_a.name}-{parent_b.name}"

        return FusionResult(
            success=True,
            species=species,
            name_suggestion=name,
            inherited_stats=stats,
            lore_text=f"The essence of {parent_a.name} and {parent_b.name} merged into something new.",
        )


def _inherit_stats(stats_a: dict[str, int], stats_b: dict[str, int]) -> dict[str, int]:
    """Inherit stats from both parents: take the higher of each stat at 75%."""
    result = {}
    all_stats = set(stats_a.keys()) | set(stats_b.keys())
    for stat in all_stats:
        val_a = stats_a.get(stat, 10)
        val_b = stats_b.get(stat, 10)
        result[stat] = max(1, int(max(val_a, val_b) * 0.75))
    return result


def get_discovered_recipes(known_species: set[str]) -> list[FusionRecipe]:
    """Get recipes the player could attempt based on species they own."""
    available = []
    for recipe in FUSION_RECIPES:
        if recipe.species_a in known_species and recipe.species_b in known_species:
            available.append(recipe)
    return available


def get_all_fusion_species() -> list[Species]:
    """Get all fusion-exclusive species (for collection tracking)."""
    return list(FUSION_SPECIES)


def format_fusion_preview(result: FusionResult) -> list[str]:
    """Format a fusion preview for display."""
    if not result.success:
        return [f"[red]{result.error}[/red]"]

    species = result.species
    lines = [
        "",
        "[bold]═══ FUSION PREVIEW ═══[/bold]",
        "",
        f"  {species.emoji} [bold]{species.name.replace('_', ' ').title()}[/bold]",
        f"  [dim]{species.description}[/dim]",
        f"  Rarity: [{_rarity_color(species.rarity)}]{species.rarity.value.upper()}[/{_rarity_color(species.rarity)}]",
        "",
        "  [bold]Inherited Stats:[/bold]",
    ]

    for stat, val in sorted(result.inherited_stats.items()):
        bar_len = val // 5
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"    {stat.upper():12s} {bar} {val}")

    if result.is_recipe:
        lines.append("")
        lines.append(f"  [bold yellow]★ Special Recipe![/bold yellow]")
        lines.append(f"  [italic]{result.lore_text}[/italic]")
    else:
        lines.append("")
        lines.append(f"  [dim italic]{result.lore_text}[/dim italic]")

    lines.append("")
    lines.append("  [bold red]⚠ Both parents will be permanently consumed.[/bold red]")
    lines.append("  The fused buddy gets the [yellow]Chimera Crown[/yellow] hat")
    lines.append("  and a visible [bold](Fused)[/bold] tag.")
    lines.append("")

    return lines


def _rarity_color(rarity: Rarity) -> str:
    return {
        Rarity.COMMON: "white",
        Rarity.UNCOMMON: "green",
        Rarity.RARE: "blue",
        Rarity.EPIC: "magenta",
        Rarity.LEGENDARY: "yellow",
    }.get(rarity, "white")


# ---------------------------------------------------------------------------
# Hat: Chimera Crown (fusion-exclusive)
# ---------------------------------------------------------------------------

CHIMERA_CROWN_HAT = "chimera_crown"
FUSED_TAG = "(Fused)"
