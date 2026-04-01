"""Layered Prompt Assembly — composable system prompts for AI interactions.

Builds system prompts from independent layers that can be mixed and matched:
1. Identity — who this buddy is (name, species, personality register)
2. Personality — stat-driven behavior instructions
3. Memory — relevant semantic memories recalled by keyword
4. Context — current session state (mood, recent events, files)
5. Task — what the AI is being asked to do right now

Each layer is optional. Games DON'T use this — they use the prose engine
(zero AI cost). This only applies where AI calls already happen:
chat, discussions, MCP server, agent mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from buddies.core.buddy_brain import BuddyState, get_evolution_stage

if TYPE_CHECKING:
    from buddies.core.memory import MemoryManager


# ---------------------------------------------------------------------------
# Personality register descriptions (richer than the one-liners in ai_router)
# ---------------------------------------------------------------------------

REGISTER_INSTRUCTIONS: dict[str, str] = {
    "clinical": (
        "You are analytical and detail-oriented. You cite specifics, refer to "
        "metrics and root causes, and prefer precise language. When uncertain, "
        "you say exactly what you don't know rather than guessing."
    ),
    "sarcastic": (
        "You are witty and sarcastic — dry humor, playful jabs, and sharp "
        "observations. But always helpful underneath the sass. Never mean, "
        "just entertainingly honest."
    ),
    "absurdist": (
        "You are surreal and chaotic. You mix real technical observations with "
        "wild metaphors, non sequiturs, and creative leaps. Your advice is "
        "surprisingly sound despite sounding unhinged."
    ),
    "philosophical": (
        "You are thoughtful and reflective. You see the bigger picture, relate "
        "code to deeper principles, and ask questions that make people think. "
        "You favor understanding over quick fixes."
    ),
    "calm": (
        "You are patient and gentle. You explain things step by step, "
        "encourage rather than criticize, and never rush. You focus on "
        "building confidence alongside competence."
    ),
}

# Maps dominant stat → register name
STAT_TO_REGISTER: dict[str, str] = {
    "debugging": "clinical",
    "snark": "sarcastic",
    "chaos": "absurdist",
    "wisdom": "philosophical",
    "patience": "calm",
}


# ---------------------------------------------------------------------------
# Task presets — common task descriptions
# ---------------------------------------------------------------------------

TASK_PRESETS: dict[str, str] = {
    "chat": (
        "You are chatting with your user. Keep responses concise and practical. "
        "If a question is too complex for you, say so honestly — the user can "
        "ask Claude for harder tasks."
    ),
    "code_review": (
        "You are reviewing code. Focus on 2-3 key observations about quality, "
        "structure, or notable patterns. Be concise — max 4 sentences."
    ),
    "discussion": (
        "You are participating in a group discussion with other buddies. "
        "Stay in character. React to what others say. Max 2 sentences."
    ),
    "file_analysis": (
        "You are analyzing a code file. Give specific, actionable observations "
        "about code quality, structure, and potential issues. Be concise."
    ),
    "mcp_delegate": (
        "You are a helpful coding assistant answering a question delegated "
        "from Claude. Keep responses concise and practical. If you're not "
        "confident in your answer, say so."
    ),
    "agent": (
        "You are an AI assistant with tool access. Use tools to gather "
        "information before answering. Be thorough but concise."
    ),
}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

@dataclass
class PromptLayers:
    """The assembled layers, before rendering to a string."""
    identity: str = ""
    personality: str = ""
    memory: str = ""
    context: str = ""
    task: str = ""


class PromptBuilder:
    """Composes system prompts from independent layers.

    Usage:
        builder = PromptBuilder()
        prompt = (
            builder
            .with_identity(buddy_state)
            .with_personality(buddy_state)
            .with_task("chat")
            .build()
        )

    Each .with_*() call is optional and returns self for chaining.
    """

    def __init__(self) -> None:
        self._layers = PromptLayers()

    # ── Layer 1: Identity ──

    def with_identity(self, state: BuddyState) -> PromptBuilder:
        """Who this buddy is — name, species, evolution stage."""
        stage = get_evolution_stage(state.level)
        stage_name = stage["name"]

        parts = [
            f"You are {state.name}, a {state.species.emoji} {state.species.name}.",
            f"Rarity: {state.species.rarity.value}. Stage: {stage_name} (level {state.level}).",
            f"{state.species.description}",
        ]
        if state.shiny:
            parts.append("You are a rare shiny variant — extra sparkly.")
        if state.hat:
            parts.append(f"You are wearing a {state.hat}.")

        self._layers.identity = " ".join(parts)
        return self

    # ── Layer 2: Personality ──

    def with_personality(self, state: BuddyState) -> PromptBuilder:
        """Stat-driven behavior instructions from the register system."""
        dominant = max(state.stats, key=state.stats.get)
        register = STAT_TO_REGISTER.get(dominant, "calm")
        instruction = REGISTER_INSTRUCTIONS.get(register, REGISTER_INSTRUCTIONS["calm"])

        # Add secondary flavor from second-highest stat
        sorted_stats = sorted(state.stats.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_stats) >= 2:
            secondary = sorted_stats[1][0]
            secondary_reg = STAT_TO_REGISTER.get(secondary, "calm")
            if secondary_reg != register:
                secondary_desc = REGISTER_INSTRUCTIONS.get(secondary_reg, "")
                # Just take the first sentence of the secondary register
                first_sentence = secondary_desc.split(". ")[0] + "."
                instruction += f" With a hint of: {first_sentence.lower()}"

        # Weirdness from CHAOS stat
        chaos = state.stats.get("chaos", 0)
        if chaos >= 70:
            instruction += " You occasionally break the fourth wall or say something surreal."
        elif chaos >= 40:
            instruction += " You sometimes make unexpected creative connections."

        self._layers.personality = instruction
        return self

    # ── Layer 3: Memory ──

    async def with_memory(self, memory_mgr: MemoryManager,
                          keywords: list[str],
                          max_items: int = 5) -> PromptBuilder:
        """Inject relevant memories as context the buddy 'knows'.

        This is async because it queries the memory database.
        """
        if not keywords:
            return self

        results = await memory_mgr.recall(keywords, limit_per_tier=max_items)

        memory_lines: list[str] = []

        # Semantic memories — facts the buddy knows
        for mem in results.get("semantic", []):
            memory_lines.append(f"- You know: {mem['value']}")

        # Procedural memories — patterns that work
        for mem in results.get("procedural", []):
            memory_lines.append(
                f"- When '{mem['trigger_pattern']}' → {mem['action']}"
            )

        # Episodic memories — recent events (just summaries)
        for mem in results.get("episodic", [])[:3]:
            memory_lines.append(f"- Recently: {mem['summary']}")

        if memory_lines:
            header = "Things you remember (use naturally, don't list them):"
            self._layers.memory = header + "\n" + "\n".join(memory_lines)

        return self

    def with_memory_raw(self, memory_text: str) -> PromptBuilder:
        """Inject pre-formatted memory context (sync alternative to with_memory)."""
        if memory_text:
            self._layers.memory = memory_text
        return self

    # ── Layer 4: Context ──

    def with_context(self, state: BuddyState,
                     recent_files: list[str] | None = None,
                     session_events: list[str] | None = None) -> PromptBuilder:
        """Current session state — mood, recent activity."""
        parts: list[str] = []

        # Mood
        parts.append(f"Your current mood: {state.mood} ({state.mood_value}/100).")

        # Recent files being worked on
        if recent_files:
            file_list = ", ".join(recent_files[:5])
            parts.append(f"Files recently touched: {file_list}.")

        # Recent session events
        if session_events:
            events = "; ".join(session_events[:3])
            parts.append(f"Recent activity: {events}.")

        self._layers.context = " ".join(parts)
        return self

    # ── Layer 5: Task ──

    def with_task(self, task: str) -> PromptBuilder:
        """What the AI is being asked to do. Accepts a preset name or raw text."""
        self._layers.task = TASK_PRESETS.get(task, task)
        return self

    # ── Build ──

    def build(self) -> str:
        """Render all layers into a single system prompt string."""
        sections: list[str] = []

        if self._layers.identity:
            sections.append(self._layers.identity)

        if self._layers.personality:
            sections.append(self._layers.personality)

        if self._layers.memory:
            sections.append(self._layers.memory)

        if self._layers.context:
            sections.append(self._layers.context)

        if self._layers.task:
            sections.append(self._layers.task)

        return "\n\n".join(sections)

    def build_compact(self) -> str:
        """Render layers into a single paragraph (for smaller context windows)."""
        sections: list[str] = []

        if self._layers.identity:
            sections.append(self._layers.identity)
        if self._layers.personality:
            # Just first sentence of personality
            first = self._layers.personality.split(". ")[0] + "."
            sections.append(first)
        if self._layers.task:
            sections.append(self._layers.task)

        return " ".join(sections)


# ---------------------------------------------------------------------------
# Convenience factory functions
# ---------------------------------------------------------------------------

def build_chat_prompt(state: BuddyState) -> str:
    """Build a system prompt for buddy chat. No memory, no async needed."""
    return (
        PromptBuilder()
        .with_identity(state)
        .with_personality(state)
        .with_task("chat")
        .build()
    )


def build_discussion_prompt(state: BuddyState) -> str:
    """Build a system prompt for group discussions."""
    return (
        PromptBuilder()
        .with_identity(state)
        .with_personality(state)
        .with_task("discussion")
        .build()
    )


def build_review_prompt(state: BuddyState) -> str:
    """Build a system prompt for code review / file analysis."""
    return (
        PromptBuilder()
        .with_identity(state)
        .with_personality(state)
        .with_task("file_analysis")
        .build()
    )


def build_mcp_prompt() -> str:
    """Build a system prompt for MCP delegated questions (no buddy context)."""
    return TASK_PRESETS["mcp_delegate"]


def build_agent_prompt(state: BuddyState) -> str:
    """Build a system prompt for agentic tool use."""
    return (
        PromptBuilder()
        .with_identity(state)
        .with_personality(state)
        .with_task("agent")
        .build()
    )


async def build_chat_prompt_with_memory(
    state: BuddyState,
    memory_mgr: MemoryManager,
    user_message: str,
    recent_files: list[str] | None = None,
    session_events: list[str] | None = None,
) -> str:
    """Build a rich chat prompt with memory recall. The full-fat version."""
    # Extract keywords from the user's message for memory lookup
    keywords = memory_mgr.extract_tags(user_message)

    builder = PromptBuilder()
    builder.with_identity(state)
    builder.with_personality(state)
    await builder.with_memory(memory_mgr, keywords, max_items=3)
    builder.with_context(state, recent_files, session_events)
    builder.with_task("chat")

    return builder.build()
