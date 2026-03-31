"""Register Buddy's MCP server with Claude Code.

Adds the Buddy MCP server to Claude Code's settings so Claude can
use buddy_status, buddy_note, session_stats, and ask_buddy tools.

Usage:
    python -m buddies.setup_mcp
    python -m buddies.setup_mcp remove
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get_claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def setup_mcp():
    """Register Buddy MCP server with Claude Code."""
    settings_path = get_claude_settings_path()

    if not settings_path.exists():
        print(f"Claude Code settings not found at {settings_path}")
        return False

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    mcp_servers = settings.get("mcpServers", {})

    python_path = sys.executable.replace("\\", "/")

    mcp_servers["buddy"] = {
        "command": python_path,
        "args": ["-m", "buddies.mcp.server"],
        "env": {
            "PYTHONPATH": str(Path(__file__).parent.parent.resolve()).replace("\\", "/"),
        },
    }

    settings["mcpServers"] = mcp_servers
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"Buddy MCP server registered in {settings_path}")
    print("Claude Code will now have access to buddy tools!")
    print("\nTools available:")
    print("  - buddy_status: Check buddy's mood, stats, and level")
    print("  - buddy_note: Leave notes for the user via buddy")
    print("  - session_stats: View session token usage and tool counts")
    print("  - ask_buddy: Delegate simple questions to local AI")
    print("  - get_buddy_notes: Read unread notes")
    return True


def remove_mcp():
    """Remove Buddy MCP server from Claude Code."""
    settings_path = get_claude_settings_path()
    if not settings_path.exists():
        return

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    mcp_servers = settings.get("mcpServers", {})

    if "buddy" in mcp_servers:
        del mcp_servers["buddy"]
        settings["mcpServers"] = mcp_servers
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print("Buddy MCP server removed from Claude Code settings.")
    else:
        print("Buddy MCP server not found in settings — nothing to remove.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_mcp()
    else:
        setup_mcp()
