"""Headless mode — runs Buddy as a pure MCP server without the TUI.

Use this with Claude Desktop, Claude.ai, or any MCP-compatible client.
Buddy still watches sessions, tracks stats, generates code maps, and
provides all MCP tools — just without the terminal UI.

Usage:
    buddy --headless
    python -m buddies --headless

Configure in Claude Desktop (claude_desktop_config.json):
    {
        "mcpServers": {
            "buddies": {
                "command": "buddy",
                "args": ["--headless"]
            }
        }
    }
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from buddies.config import BuddyConfig
from buddies.core.code_map import write_project_map
from buddies.core.session_observer import SessionObserver
from buddies.core.token_guardian import TokenGuardian


async def _background_services():
    """Run background services alongside the MCP server."""
    config = BuddyConfig.load()
    project_path = Path.cwd()
    observer = SessionObserver()
    guardian = TokenGuardian(project_path)

    # Generate/refresh code map on startup if stale
    try:
        map_path = project_path / ".claude" / "rules" / "project-map.md"
        if not map_path.exists() or (time.time() - map_path.stat().st_mtime > 3600):
            write_project_map(project_path)
    except Exception:
        pass

    # Start session observer
    try:
        await observer.start()
    except asyncio.CancelledError:
        pass


def run_headless():
    """Run Buddy in headless mode — MCP server only, no TUI."""
    # Import here to fail fast if mcp isn't installed
    try:
        from buddies.mcp.server import mcp
    except ImportError:
        print(
            "Error: MCP package not installed.\n"
            "Install with: pip install buddies[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Start background services in a separate task
    loop = asyncio.new_event_loop()

    # The MCP server's run() blocks, so start background first
    # via a thread, then run MCP
    import threading

    def _run_background():
        bg_loop = asyncio.new_event_loop()
        try:
            bg_loop.run_until_complete(_background_services())
        except Exception:
            pass
        finally:
            bg_loop.close()

    bg_thread = threading.Thread(target=_run_background, daemon=True)
    bg_thread.start()

    # Run the MCP server (blocks until client disconnects)
    mcp.run(transport="stdio")
