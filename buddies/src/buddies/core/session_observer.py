"""Session observer — watches Claude Code events and detects patterns.

Reads the events.jsonl file written by hooks.py, processes events,
detects patterns, and provides them to the TUI.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from buddies.core.hooks import get_events_path


@dataclass
class SessionEvent:
    """A processed session event."""

    timestamp: float
    event_type: str
    tool_name: str
    summary: str
    tokens_estimated: int = 0
    raw_data: dict = field(default_factory=dict)


@dataclass
class SessionStats:
    """Running statistics for the current session."""

    start_time: float = 0.0
    event_count: int = 0
    tokens_estimated: int = 0
    tool_counts: Counter = field(default_factory=Counter)
    recent_tools: deque = field(default_factory=lambda: deque(maxlen=20))
    error_count: int = 0
    edit_count: int = 0
    files_touched: set = field(default_factory=set)

    @property
    def duration_minutes(self) -> float:
        if self.start_time == 0:
            return 0.0
        return (time.time() - self.start_time) / 60

    @property
    def most_used_tool(self) -> str:
        if not self.tool_counts:
            return "none"
        return self.tool_counts.most_common(1)[0][0]


# Rough token estimates per tool type
TOKEN_ESTIMATES = {
    "Read": 500,
    "Edit": 300,
    "Write": 400,
    "Bash": 200,
    "Grep": 150,
    "Glob": 100,
    "WebSearch": 800,
    "WebFetch": 1000,
    "Agent": 2000,
}


class SessionObserver:
    """Watches the event log and processes events in real-time."""

    def __init__(self):
        self.stats = SessionStats()
        self._last_position = 0
        self._events_path = get_events_path()
        self._callbacks: list[Callable[[SessionEvent], None]] = []
        self._pattern_callbacks: list[Callable[[str, str], None]] = []
        self._running = False
        self._recent_events: deque[SessionEvent] = deque(maxlen=100)

    def on_event(self, callback: Callable[[SessionEvent], None]):
        """Register a callback for new events."""
        self._callbacks.append(callback)

    def on_pattern(self, callback: Callable[[str, str], None]):
        """Register a callback for detected patterns. Args: (pattern_type, description)."""
        self._pattern_callbacks.append(callback)

    async def start(self):
        """Start watching the event log."""
        self._running = True
        self.stats.start_time = time.time()

        # Skip to end of existing file
        if self._events_path.exists():
            self._last_position = self._events_path.stat().st_size

        while self._running:
            await self._poll_events()
            await asyncio.sleep(0.5)

    def stop(self):
        self._running = False

    async def _poll_events(self):
        """Check for new events in the log file."""
        if not self._events_path.exists():
            return

        current_size = self._events_path.stat().st_size
        if current_size <= self._last_position:
            return

        try:
            with open(self._events_path, "r", encoding="utf-8") as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()
        except (OSError, IOError):
            return

        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                event = self._process_raw_event(raw)
                if event:
                    self._record_event(event)
                    for cb in self._callbacks:
                        cb(event)
            except json.JSONDecodeError:
                continue

    def _process_raw_event(self, raw: dict) -> SessionEvent | None:
        """Convert raw event JSON to a SessionEvent."""
        data = raw.get("data", {})
        event_type = data.get("event", raw.get("type", "unknown"))
        tool_name = data.get("tool_name", "")

        summary = self._make_summary(event_type, tool_name, data)
        tokens = TOKEN_ESTIMATES.get(tool_name, 100) if tool_name else 0

        return SessionEvent(
            timestamp=raw.get("timestamp", time.time()),
            event_type=event_type,
            tool_name=tool_name,
            summary=summary,
            tokens_estimated=tokens,
            raw_data=data,
        )

    def _make_summary(self, event_type: str, tool_name: str, data: dict) -> str:
        """Create a human-readable summary of an event."""
        tool_input = data.get("tool_input", {})

        if event_type == "SessionStart":
            return "Claude Code session started"
        elif event_type == "SessionEnd":
            return "Claude Code session ended"
        elif event_type == "UserPromptSubmit":
            return "You sent a message to Claude"

        if event_type == "PreToolUse":
            if tool_name == "Read":
                path = tool_input.get("file_path", "a file")
                return f"Reading {self._short_path(path)}"
            elif tool_name == "Edit":
                path = tool_input.get("file_path", "a file")
                return f"Editing {self._short_path(path)}"
            elif tool_name == "Write":
                path = tool_input.get("file_path", "a file")
                return f"Writing {self._short_path(path)}"
            elif tool_name == "Bash":
                cmd = tool_input.get("command", "")
                if len(cmd) > 60:
                    cmd = cmd[:60] + "..."
                return f"Running: {cmd}"
            elif tool_name == "Grep":
                pattern = tool_input.get("pattern", "")
                return f"Searching for '{pattern}'"
            elif tool_name == "Glob":
                pattern = tool_input.get("pattern", "")
                return f"Finding files: {pattern}"
            elif tool_name == "Agent":
                desc = tool_input.get("description", "a task")
                return f"Spawning agent: {desc}"
            elif tool_name == "WebSearch":
                query = tool_input.get("query", "")
                return f"Web search: {query}"
            else:
                return f"Using tool: {tool_name}"

        elif event_type == "PostToolUse":
            result = data.get("result_summary", "")
            if tool_name and result:
                return f"{tool_name} completed: {result[:80]}"
            elif tool_name:
                return f"{tool_name} completed"

        return f"{event_type}: {tool_name or 'system event'}"

    def _short_path(self, path: str) -> str:
        """Shorten a file path for display."""
        if not path:
            return "unknown"
        parts = path.replace("\\", "/").split("/")
        if len(parts) > 3:
            return "/".join(["...", *parts[-3:]])
        return path

    def _record_event(self, event: SessionEvent):
        """Record an event and check for patterns."""
        self.stats.event_count += 1
        self.stats.tokens_estimated += event.tokens_estimated
        self._recent_events.append(event)

        if event.tool_name:
            self.stats.tool_counts[event.tool_name] += 1
            self.stats.recent_tools.append(event.tool_name)

        # Track file edits
        if event.tool_name in ("Edit", "Write"):
            self.stats.edit_count += 1
            file_path = event.raw_data.get("tool_input", {}).get("file_path", "")
            if file_path:
                self.stats.files_touched.add(file_path)

        # Pattern detection
        self._detect_patterns()

    def _detect_patterns(self):
        """Check recent events for notable patterns."""
        recent = list(self.stats.recent_tools)
        if len(recent) < 5:
            return

        last_5 = recent[-5:]

        # Pattern: Reading the same file repeatedly
        if last_5.count("Read") >= 4:
            self._emit_pattern(
                "repeated_reads",
                "Claude is reading a lot of files — might be searching for something. "
                "Consider adding file paths to CLAUDE.md so it knows where to look."
            )

        # Pattern: Many edits in a row
        if last_5.count("Edit") >= 4:
            self._emit_pattern(
                "edit_storm",
                "Claude is making many edits — large refactor in progress. "
                "Might be worth reviewing before it gets too far."
            )

        # Pattern: Agent spam
        if last_5.count("Agent") >= 3:
            self._emit_pattern(
                "agent_heavy",
                "Claude is spawning lots of subagents — this uses more tokens. "
                "Could some of these tasks be handled by a simpler approach?"
            )

        # Pattern: Alternating Read/Edit (good pattern)
        read_edit = sum(1 for t in last_5 if t in ("Read", "Edit"))
        if read_edit >= 4 and "Read" in last_5 and "Edit" in last_5:
            self._emit_pattern(
                "careful_editing",
                "Claude is reading before editing — good practice! 👍"
            )

    def _emit_pattern(self, pattern_type: str, description: str):
        for cb in self._pattern_callbacks:
            cb(pattern_type, description)
