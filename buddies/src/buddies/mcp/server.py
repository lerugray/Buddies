"""Buddy MCP Server — exposes tools to Claude Code.

This runs as a separate process (stdio transport) that Claude Code connects to.
It provides tools for Claude to check on buddy, leave notes, view session stats,
and delegate simple tasks to the local AI.

Register in .claude/settings.json or claude_desktop_config.json:
    "mcpServers": {
        "buddy": {
            "command": "python",
            "args": ["-m", "buddies.mcp.server"]
        }
    }
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "MCP package not installed. Install with: pip install buddies[mcp]"
    )

from buddies.config import BuddyConfig, get_data_dir
from buddies.core.cc_companion import build_cc_buddy_data, detect_cc_buddy
from buddies.core.hooks import get_events_path
from buddies.core.prompt_builder import build_mcp_prompt
from buddies.db.store import BuddyStore

mcp = FastMCP("Buddies")

# Lazy-initialized shared state
_store: BuddyStore | None = None
_config: BuddyConfig | None = None


async def _get_store() -> BuddyStore:
    global _store, _config
    if _store is None:
        _config = BuddyConfig.load()
        _store = BuddyStore(_config.db_path)
        await _store.connect()
    return _store


def _get_mcp_prompt() -> str:
    """Get the system prompt for MCP-delegated AI questions."""
    return build_mcp_prompt()


@mcp.tool()
async def buddy_status() -> str:
    """Check on your buddy — see their species, stats, mood, and level.

    Use this to see how your companion is doing. Their mood and stats
    change based on your coding sessions.
    """
    store = await _get_store()
    data = await store.get_active_buddy()

    if not data:
        return "No buddy hatched yet! Run the Buddy TUI to hatch your companion."

    mood_icons = {
        "ecstatic": "😄", "happy": "🙂", "neutral": "😐",
        "bored": "😒", "grumpy": "😠",
    }
    icon = mood_icons.get(data["mood"], "😐")
    shiny = " ✨SHINY" if data["shiny"] else ""
    hat_line = f"\n**Hat:** 🎩 {data['hat']}" if data.get("hat") else ""

    return (
        f"# {data['name']} — {data['species'].capitalize()}{shiny}\n\n"
        f"**Level:** {data['level']}  |  **XP:** {data['xp']}  |  "
        f"**Mood:** {icon} {data['mood']} ({data['mood_value']}/100){hat_line}\n\n"
        f"## Stats\n"
        f"- ⚔ Debugging: {data['stat_debugging']}\n"
        f"- 🛡 Patience: {data['stat_patience']}\n"
        f"- 💥 Chaos: {data['stat_chaos']}\n"
        f"- 📖 Wisdom: {data['stat_wisdom']}\n"
        f"- 💬 Snark: {data['stat_snark']}\n\n"
        f"*\"{data['soul_description']}\"*"
    )


@mcp.tool()
async def buddy_note(message: str) -> str:
    """Leave a note for the user via Buddy.

    The note will appear in Buddy's chat window next time the user
    checks. Use this for helpful reminders, suggestions, or status updates.

    Args:
        message: The note to leave for the user
    """
    # Validate message length to prevent abuse
    if not message or not message.strip():
        return "Error: message cannot be empty."
    if len(message) > 2000:
        return "Error: message too long (max 2000 characters)."
    # Strip Rich markup to prevent injection when displayed in TUI
    clean_message = message[:2000].replace("[", "\\[")
    store = await _get_store()
    await store.add_note(source="Claude", message=clean_message)
    return f"Note saved! Your buddy will show it to the user."


@mcp.tool()
async def session_stats() -> str:
    """View current session statistics — events, token usage, tool counts.

    Shows what's happened in the current Claude Code session including
    estimated token usage and which tools have been used most.
    """
    events_path = get_events_path()
    if not events_path.exists():
        return "No session data yet. The Buddy TUI needs to be running to collect events."

    # Read recent events
    events = []
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return "Could not read session events."

    if not events:
        return "No events recorded yet."

    # Compute stats
    tool_counts: dict[str, int] = {}
    total_events = len(events)
    first_ts = events[0].get("timestamp", time.time())
    duration_min = (time.time() - first_ts) / 60

    for evt in events:
        data = evt.get("data", {})
        tool = data.get("tool_name", "")
        if tool:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    tool_lines = "\n".join(
        f"- {tool}: {count}" for tool, count in
        sorted(tool_counts.items(), key=lambda x: -x[1])[:10]
    )

    return (
        f"# Session Stats\n\n"
        f"**Events:** {total_events}  |  "
        f"**Duration:** {duration_min:.1f} min\n\n"
        f"## Tool Usage\n{tool_lines}\n\n"
        f"*Data from Buddy's event log*"
    )


@mcp.tool()
async def ask_buddy(question: str) -> str:
    """Ask Buddy's local AI a simple question to save tokens.

    Routes the question to the locally-running AI model. Best for:
    - Syntax questions
    - Simple explanations
    - Quick lookups

    For complex tasks, handle them yourself — you're better at those.

    Args:
        question: The question to ask the local AI
    """
    # Check if local AI is configured and available
    config = BuddyConfig.load()
    if config.ai_backend.provider == "none":
        return (
            "Local AI is not configured. The user needs to set up an AI backend "
            "(Ollama, LM Studio, etc.) in Buddy's config. You should handle this "
            "question yourself."
        )

    # Try to use the AI backend directly
    from buddies.core.ai_backend import create_backend
    backend = create_backend(config.ai_backend)
    await backend.connect()

    try:
        if not await backend.is_available():
            return (
                "Local AI is configured but not reachable. "
                "You should handle this question yourself."
            )

        response = await backend.chat(
            [{"role": "user", "content": question}],
            system_prompt=_get_mcp_prompt(),
        )

        if response.error:
            return f"Local AI error: {response.error}. Handle this yourself."

        return f"**Buddy's local AI says:**\n\n{response.content}"

    finally:
        await backend.close()


@mcp.tool()
async def get_buddy_notes() -> str:
    """Check if Buddy has any unread notes from previous sessions or from you.

    Returns unread notes left by either you (Claude) or the user via Buddy.
    """
    store = await _get_store()
    notes = await store.get_unread_notes()

    if not notes:
        return "No unread notes."

    lines = []
    for note in notes:
        lines.append(f"- **{note['source']}** ({note['timestamp']}): {note['message']}")

    await store.mark_notes_read()
    return f"# Unread Notes\n\n" + "\n".join(lines)


@mcp.tool()
async def import_cc_buddy(
    name: str,
    species: str,
    rarity: str = "common",
    debugging: int = 10,
    patience: int = 10,
    chaos: int = 10,
    wisdom: int = 10,
    snark: int = 10,
    personality: str = "",
    shiny: bool = False,
) -> str:
    """Import your Claude Code /buddy companion into the Buddies party.

    If you can see a companion in the user's Claude Code session (from
    the companion_intro in the system prompt), use this tool to bring
    that companion into Buddies so it can join discussions, play games,
    and hang out with the rest of the party.

    The CC buddy joins the collection but doesn't replace the active buddy.
    Only one CC companion can be imported at a time (re-importing updates it).

    Args:
        name: The companion's name (e.g. "Inkwell")
        species: The CC species (duck, mushroom, ghost, etc.)
        rarity: The CC rarity tier (common/uncommon/rare/epic/legendary)
        debugging: DEBUGGING stat (1-100)
        patience: PATIENCE stat (1-100)
        chaos: CHAOS stat (1-100)
        wisdom: WISDOM stat (1-100)
        snark: SNARK stat (1-100)
        personality: The companion's personality description
        shiny: Whether the companion is shiny
    """
    if not name or not name.strip():
        return "Error: companion name cannot be empty."
    if not species or not species.strip():
        return "Error: companion species cannot be empty."

    stats = {
        "debugging": debugging,
        "patience": patience,
        "chaos": chaos,
        "wisdom": wisdom,
        "snark": snark,
    }

    data = build_cc_buddy_data(
        name=name.strip(),
        cc_species=species.strip(),
        cc_rarity=rarity.strip(),
        stats=stats,
        personality=personality.strip(),
        shiny=shiny,
    )

    store = await _get_store()
    result = await store.create_cc_buddy(data)

    mapped_species = data["species"]
    species_note = ""
    if species.strip().lower() != mapped_species:
        species_note = f" (mapped from CC's {species} to Buddies' {mapped_species})"

    return (
        f"# {name} has joined the Buddies party! 🎉\n\n"
        f"**Species:** {mapped_species}{species_note}\n"
        f"**Rarity:** {rarity}\n"
        f"**Stats:** DEBUG {debugging} / PAT {patience} / "
        f"CHAOS {chaos} / WIS {wisdom} / SNARK {snark}\n\n"
        f"*{name} can now join discussions, play arcade games, "
        f"and explore StackHaven with the rest of the party. "
        f"The user can switch to {name} in the Party screen [p].*"
    )


@mcp.tool()
async def detect_cc_companion() -> str:
    """Check if a CC companion can be auto-detected from config files.

    Tries to find CC buddy data in config files or manual override.
    If found, auto-imports it. If not, returns instructions for manual setup.
    """
    detected = detect_cc_buddy()
    if not detected:
        return (
            "No CC companion auto-detected from config files.\n\n"
            "To set up auto-import, add this to your Buddies config "
            "(in %APPDATA%/buddy/config.json or ~/.local/share/buddy/config.json):\n\n"
            '```json\n'
            '{\n'
            '  "cc_buddy": {\n'
            '    "name": "YourBuddyName",\n'
            '    "species": "mushroom",\n'
            '    "rarity": "common",\n'
            '    "debugging": 10,\n'
            '    "patience": 10,\n'
            '    "chaos": 10,\n'
            '    "wisdom": 10,\n'
            '    "snark": 10\n'
            '  }\n'
            '}\n'
            '```\n\n'
            "Or use the `import_cc_buddy` tool to import directly."
        )

    data = build_cc_buddy_data(
        name=detected["name"],
        cc_species=detected["species"],
        cc_rarity=detected["rarity"],
        stats=detected["stats"],
        personality=detected["personality"],
        shiny=detected["shiny"],
    )

    store = await _get_store()
    await store.create_cc_buddy(data)

    return (
        f"# CC Companion Auto-Detected! 🔗\n\n"
        f"**{detected['name']}** ({detected['species']}) has been imported into Buddies.\n"
        f"The user can see them in the Party screen [p]."
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
