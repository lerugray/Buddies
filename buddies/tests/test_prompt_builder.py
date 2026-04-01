"""Tests for the layered prompt assembly system."""

import pytest

from buddies.core.buddy_brain import BuddyState, Species, Rarity
from buddies.core.prompt_builder import (
    PromptBuilder,
    build_chat_prompt,
    build_discussion_prompt,
    build_review_prompt,
    build_mcp_prompt,
    build_agent_prompt,
    REGISTER_INSTRUCTIONS,
    TASK_PRESETS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", level=5, **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30
    sp = Species(
        name="test_species", emoji="🐱", rarity=Rarity.COMMON,
        base_stats=stats, description="Test buddy",
    )
    defaults = dict(
        name=name, species=sp, level=level, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=1, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


# ---------------------------------------------------------------------------
# PromptBuilder basics
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_empty_build(self):
        """Empty builder returns empty string."""
        prompt = PromptBuilder().build()
        assert prompt == ""

    def test_identity_layer(self):
        buddy = make_buddy(name="Sparkle")
        prompt = PromptBuilder().with_identity(buddy).build()
        assert "Sparkle" in prompt
        assert "test_species" in prompt
        assert "level 5" in prompt

    def test_identity_shiny(self):
        buddy = make_buddy(shiny=True)
        prompt = PromptBuilder().with_identity(buddy).build()
        assert "shiny" in prompt.lower()

    def test_identity_hat(self):
        buddy = make_buddy(hat="crown")
        prompt = PromptBuilder().with_identity(buddy).build()
        assert "crown" in prompt

    def test_personality_layer_dominant_stat(self):
        buddy = make_buddy(dominant="debugging")
        prompt = PromptBuilder().with_personality(buddy).build()
        assert "analytical" in prompt.lower()

    def test_personality_layer_chaos(self):
        buddy = make_buddy(dominant="chaos")
        prompt = PromptBuilder().with_personality(buddy).build()
        assert "surreal" in prompt.lower()

    def test_personality_layer_snark(self):
        buddy = make_buddy(dominant="snark")
        prompt = PromptBuilder().with_personality(buddy).build()
        assert "sarcastic" in prompt.lower()

    def test_personality_high_chaos_adds_weirdness(self):
        stats = {"debugging": 10, "chaos": 75, "snark": 10, "wisdom": 10, "patience": 10}
        buddy = make_buddy(dominant="chaos", stats=stats)
        prompt = PromptBuilder().with_personality(buddy).build()
        assert "fourth wall" in prompt.lower() or "surreal" in prompt.lower()

    def test_context_layer(self):
        buddy = make_buddy()
        prompt = (
            PromptBuilder()
            .with_context(buddy, recent_files=["app.py", "config.py"])
            .build()
        )
        assert "app.py" in prompt
        assert "happy" in prompt

    def test_context_with_events(self):
        buddy = make_buddy()
        prompt = (
            PromptBuilder()
            .with_context(buddy, session_events=["3 edits", "1 bash command"])
            .build()
        )
        assert "3 edits" in prompt

    def test_task_layer_preset(self):
        prompt = PromptBuilder().with_task("chat").build()
        assert "concise" in prompt.lower()

    def test_task_layer_custom(self):
        prompt = PromptBuilder().with_task("You are a pirate. Say arrr.").build()
        assert "pirate" in prompt

    def test_full_chain(self):
        buddy = make_buddy(name="Blaze", dominant="chaos")
        prompt = (
            PromptBuilder()
            .with_identity(buddy)
            .with_personality(buddy)
            .with_context(buddy, recent_files=["main.py"])
            .with_task("chat")
            .build()
        )
        assert "Blaze" in prompt
        assert "surreal" in prompt.lower()
        assert "main.py" in prompt
        assert "concise" in prompt.lower()

    def test_compact_build(self):
        buddy = make_buddy(name="Tiny")
        prompt = (
            PromptBuilder()
            .with_identity(buddy)
            .with_personality(buddy)
            .with_task("chat")
            .build_compact()
        )
        # Compact is shorter — single paragraph
        assert "\n\n" not in prompt
        assert "Tiny" in prompt

    def test_memory_raw_layer(self):
        prompt = (
            PromptBuilder()
            .with_memory_raw("You know: the user prefers dark themes.")
            .build()
        )
        assert "dark themes" in prompt

    def test_layers_are_separated(self):
        buddy = make_buddy()
        prompt = (
            PromptBuilder()
            .with_identity(buddy)
            .with_task("chat")
            .build()
        )
        # Layers separated by double newline
        assert "\n\n" in prompt


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_build_chat_prompt(self):
        buddy = make_buddy(dominant="wisdom")
        prompt = build_chat_prompt(buddy)
        assert "thoughtful" in prompt.lower()
        assert "concise" in prompt.lower()

    def test_build_discussion_prompt(self):
        buddy = make_buddy(dominant="snark")
        prompt = build_discussion_prompt(buddy)
        assert "discussion" in prompt.lower() or "react" in prompt.lower()
        assert "sarcastic" in prompt.lower()

    def test_build_review_prompt(self):
        buddy = make_buddy(dominant="debugging")
        prompt = build_review_prompt(buddy)
        assert "analyz" in prompt.lower() or "code" in prompt.lower()

    def test_build_mcp_prompt(self):
        prompt = build_mcp_prompt()
        assert "coding assistant" in prompt.lower() or "delegated" in prompt.lower()

    def test_build_agent_prompt(self):
        buddy = make_buddy(dominant="patience")
        prompt = build_agent_prompt(buddy)
        assert "tool" in prompt.lower()
        assert "patient" in prompt.lower() or "calm" in prompt.lower()

    def test_different_buddies_get_different_prompts(self):
        chaos_buddy = make_buddy(dominant="chaos")
        calm_buddy = make_buddy(dominant="patience")
        assert build_chat_prompt(chaos_buddy) != build_chat_prompt(calm_buddy)


# ---------------------------------------------------------------------------
# Register coverage
# ---------------------------------------------------------------------------

class TestRegisters:
    def test_all_registers_have_instructions(self):
        for stat in ["debugging", "snark", "chaos", "wisdom", "patience"]:
            buddy = make_buddy(dominant=stat)
            prompt = PromptBuilder().with_personality(buddy).build()
            assert len(prompt) > 20, f"Register for {stat} should produce content"

    def test_all_task_presets_exist(self):
        for task in ["chat", "code_review", "discussion", "file_analysis", "mcp_delegate", "agent"]:
            assert task in TASK_PRESETS
            assert len(TASK_PRESETS[task]) > 20
