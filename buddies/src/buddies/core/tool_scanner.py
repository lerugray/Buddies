"""Scans for installed MCP servers and Claude Code skills.

Reads configuration files to build a browsable list of available tools.
Zero AI cost — pure file reading.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolInfo:
    """A discovered MCP server or skill."""

    name: str
    tool_type: str  # "mcp" or "skill"
    source: str  # "project" or "global"
    description: str
    command: str = ""

    @property
    def icon(self) -> str:
        return "🔧" if self.tool_type == "mcp" else "📜"


def _find_project_root() -> Path | None:
    """Walk up from CWD to find a directory containing .claude/."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
        if (parent / ".git").is_dir():
            return parent
    return current


def _scan_mcp_from_settings(settings_path: Path, source: str) -> list[ToolInfo]:
    """Parse mcpServers from a settings.json file."""
    tools: list[ToolInfo] = []

    if not settings_path.exists():
        return tools

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return tools

    servers = data.get("mcpServers", {})
    for name, config in servers.items():
        command = ""
        if isinstance(config, dict):
            cmd_parts = [config.get("command", "")]
            args = config.get("args", [])
            if isinstance(args, list):
                cmd_parts.extend(str(a) for a in args[:3])
            command = " ".join(cmd_parts).strip()

        tools.append(ToolInfo(
            name=name,
            tool_type="mcp",
            source=source,
            description=f"MCP server: {command[:60]}" if command else "MCP server",
            command=command,
        ))

    return tools


def _scan_skills_from_dir(commands_dir: Path, source: str) -> list[ToolInfo]:
    """Scan a .claude/commands/ directory for skill definitions."""
    tools: list[ToolInfo] = []

    if not commands_dir.is_dir():
        return tools

    for md_file in sorted(commands_dir.glob("*.md")):
        name = md_file.stem

        # Try to extract a description from the first non-empty line
        description = f"Skill: {name}"
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("---"):
                    description = line[:80]
                    break
        except OSError:
            pass

        tools.append(ToolInfo(
            name=name,
            tool_type="skill",
            source=source,
            description=description,
        ))

    return tools


def scan_all_tools() -> list[ToolInfo]:
    """Scan for all MCP servers and skills (project + global).

    Returns a combined list sorted by type then name.
    """
    tools: list[ToolInfo] = []

    # Global config
    home = Path.home()
    global_settings = home / ".claude" / "settings.json"
    global_commands = home / ".claude" / "commands"

    tools.extend(_scan_mcp_from_settings(global_settings, "global"))
    tools.extend(_scan_skills_from_dir(global_commands, "global"))

    # Project config
    project_root = _find_project_root()
    if project_root:
        project_settings = project_root / ".claude" / "settings.json"
        project_commands = project_root / ".claude" / "commands"

        tools.extend(_scan_mcp_from_settings(project_settings, "project"))
        tools.extend(_scan_skills_from_dir(project_commands, "project"))

    # Sort: MCP first, then skills, alphabetically within each
    tools.sort(key=lambda t: (t.tool_type, t.name.lower()))

    return tools
