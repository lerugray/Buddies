"""Claude Code hook receiver.

This script is invoked by Claude Code's hook system. It receives event data
on stdin as JSON and writes it to a shared event log that the Buddy TUI watches.

Hook events are written as JSONL to: <data_dir>/events.jsonl

Usage in .claude/settings.json:
    "hooks": {
        "PreToolUse": [{"type": "command", "command": "python -m buddy.core.hooks PreToolUse"}],
        ...
    }
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from buddy.config import get_data_dir


EVENTS_FILE = "events.jsonl"


def get_events_path() -> Path:
    return get_data_dir() / EVENTS_FILE


def write_event(event_type: str, data: dict | None = None):
    """Append an event to the shared event log."""
    events_path = get_events_path()
    event = {
        "timestamp": time.time(),
        "type": event_type,
        "data": data or {},
    }
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def main():
    """Hook entry point — called by Claude Code."""
    if len(sys.argv) < 2:
        return

    event_type = sys.argv[1]

    # Try to read JSON payload from stdin
    data = {}
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
    except (json.JSONDecodeError, EOFError):
        pass

    # Extract useful info based on event type
    event_data = {
        "event": event_type,
        "tool_name": data.get("tool_name", ""),
        "tool_input": _summarize_input(data.get("tool_input", {})),
        "session_id": data.get("session_id", ""),
    }

    # For PostToolUse, include result summary
    if event_type == "PostToolUse":
        result = data.get("tool_result", data.get("result", ""))
        if isinstance(result, str) and len(result) > 200:
            result = result[:200] + "..."
        event_data["result_summary"] = str(result)[:200]

    write_event(event_type, event_data)


def _summarize_input(tool_input: dict) -> dict:
    """Summarize tool input, truncating large values."""
    if not isinstance(tool_input, dict):
        return {}
    summary = {}
    for key, value in tool_input.items():
        if isinstance(value, str) and len(value) > 150:
            summary[key] = value[:150] + "..."
        else:
            summary[key] = value
    return summary


if __name__ == "__main__":
    main()
