"""Token Guardian — rolling session summaries, token warnings, and session handoff.

The key insight: don't wait until the session ends to save state.
Write continuously in the background so nothing is lost when CC
compacts, clears, or the user hits token limits.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from buddies.config import get_data_dir


# ---------------------------------------------------------------------------
# Token usage thresholds and estimates
# ---------------------------------------------------------------------------

# CC context window size (1M tokens for Opus)
CONTEXT_WINDOW = 1_000_000

# Warning thresholds as fraction of estimated context usage
WARN_THRESHOLDS = [
    (0.50, "⚠️ ~50% context used — still plenty of room."),
    (0.70, "⚠️ ~70% context used — consider wrapping up soon or compacting."),
    (0.90, "🚨 ~90% context! Save your work and start a fresh session."),
]

# Multiplier: observed tokens are a rough undercount of actual context usage
# Tool results, system prompts, and conversation history inflate real usage
TOKEN_INFLATION = 3.5


@dataclass
class TokenWarning:
    """A token usage warning that was triggered."""
    threshold: float
    message: str
    triggered_at: float = 0.0


# ---------------------------------------------------------------------------
# Token Guardian — watches usage and writes rolling state
# ---------------------------------------------------------------------------

class TokenGuardian:
    """Monitors token usage, writes rolling summaries, generates handoff files."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self._warnings_fired: set[float] = set()
        self._last_summary_write: float = 0
        self._summary_interval: float = 60  # Write rolling summary every 60s
        self._session_topics: list[str] = []
        self._files_mentioned: set[str] = set()
        self._key_events: list[str] = []  # Important events to preserve

    def check_token_warning(self, tokens_estimated: int) -> TokenWarning | None:
        """Check if any token warning threshold has been crossed.

        Returns a TokenWarning if a new threshold was just crossed, None otherwise.
        """
        estimated_actual = tokens_estimated * TOKEN_INFLATION
        usage_fraction = estimated_actual / CONTEXT_WINDOW

        for threshold, message in WARN_THRESHOLDS:
            if usage_fraction >= threshold and threshold not in self._warnings_fired:
                self._warnings_fired.add(threshold)
                pct = int(usage_fraction * 100)
                return TokenWarning(
                    threshold=threshold,
                    message=f"{message}\n"
                            f"[dim](Est. {tokens_estimated:,} observed → "
                            f"~{int(estimated_actual):,} actual, "
                            f"~{pct}% of {CONTEXT_WINDOW:,} window)[/]",
                    triggered_at=time.time(),
                )
        return None

    def observe_user_message(self, message: str) -> None:
        """Track user messages for topic extraction."""
        # Keep short summaries of what the user talked about
        short = message[:100].strip()
        if short:
            self._session_topics.append(short)
            # Cap at 50 topics
            if len(self._session_topics) > 50:
                self._session_topics = self._session_topics[-50:]

    def observe_event(self, tool_name: str, summary: str, raw_data: dict) -> None:
        """Track notable events for the rolling summary."""
        # Track files being edited
        file_path = raw_data.get("tool_input", {}).get("file_path", "")
        if file_path and tool_name in ("Edit", "Write", "Read"):
            self._files_mentioned.add(file_path)

        # Track key events (agent spawns, session starts, errors)
        if tool_name == "Agent":
            desc = raw_data.get("tool_input", {}).get("description", summary)
            self._key_events.append(f"Agent: {desc[:80]}")
        elif tool_name == "Bash":
            cmd = raw_data.get("tool_input", {}).get("command", "")[:60]
            if any(w in cmd.lower() for w in ["test", "build", "deploy", "push", "commit"]):
                self._key_events.append(f"Bash: {cmd}")

        # Cap key events
        if len(self._key_events) > 30:
            self._key_events = self._key_events[-30:]

    def should_write_summary(self) -> bool:
        """Check if it's time to write a rolling summary."""
        return time.time() - self._last_summary_write >= self._summary_interval

    def write_rolling_summary(self, observer_stats, convo_messages=None) -> Path:
        """Write a rolling session summary to disk. Called periodically.

        This is the continuous background save — the file is always up-to-date
        so nothing is lost if CC compacts or the session ends abruptly.
        """
        self._last_summary_write = time.time()
        summary = self._build_rolling_summary(observer_stats, convo_messages)
        path = get_data_dir() / "rolling-session.md"
        try:
            path.write_text(summary, encoding="utf-8")
        except OSError:
            pass
        return path

    def write_session_handoff(self, observer_stats, buddy_state=None,
                               convo_messages=None) -> Path | None:
        """Write a session handoff file to .claude/rules/buddy-session-state.md.

        This file auto-loads into the next CC session and tells Claude
        what we were doing and where we left off.
        """
        handoff = self._build_handoff(observer_stats, buddy_state, convo_messages)
        rules_dir = self.project_path / ".claude" / "rules"
        try:
            rules_dir.mkdir(parents=True, exist_ok=True)
            path = rules_dir / "buddy-session-state.md"
            path.write_text(handoff, encoding="utf-8")
            return path
        except OSError:
            return None

    def quick_save(self, observer_stats, buddy_state=None,
                   convo_messages=None) -> tuple[Path, Path | None]:
        """Quick-save: write both rolling summary and session handoff immediately.

        Returns (summary_path, handoff_path).
        """
        summary_path = self.write_rolling_summary(observer_stats, convo_messages)
        handoff_path = self.write_session_handoff(
            observer_stats, buddy_state, convo_messages
        )
        return summary_path, handoff_path

    def build_context_export(self, stats, buddy_state=None, convo_messages=None) -> str:
        """Build a clipboard-friendly context block for pasting into claude.ai.

        Compact format designed to quickly bring another Claude instance
        up to speed on what this CC session has been doing.
        """
        now = datetime.now()
        lines = [
            "--- CONTEXT FROM CLAUDE CODE SESSION ---",
            f"Exported: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {stats.duration_minutes:.0f} min | "
            f"Events: {stats.event_count} | "
            f"Est. tokens: ~{stats.tokens_estimated:,}",
        ]

        if buddy_state:
            lines.append(
                f"Buddy: {buddy_state.name} ({buddy_state.species.name}, "
                f"L{buddy_state.level}, {buddy_state.mood})"
            )

        # Project path
        lines.append(f"Project: {self.project_path}")
        lines.append("")

        # What we're working on
        if self._session_topics:
            lines.append("RECENT TOPICS:")
            for topic in self._session_topics[-5:]:
                short = topic[:120] + "..." if len(topic) > 120 else topic
                lines.append(f"  - {short}")
            lines.append("")

        # Files in play
        all_files = stats.files_touched | self._files_mentioned
        if all_files:
            lines.append(f"FILES TOUCHED ({len(all_files)}):")
            for f in sorted(all_files)[:15]:
                short = "/".join(Path(f).parts[-3:]) if len(Path(f).parts) > 3 else f
                lines.append(f"  - {short}")
            if len(all_files) > 15:
                lines.append(f"  ...and {len(all_files) - 15} more")
            lines.append("")

        # Key events
        if self._key_events:
            lines.append("KEY EVENTS:")
            for evt in self._key_events[-8:]:
                lines.append(f"  - {evt}")
            lines.append("")

        # Recent conversation (last 5 messages)
        if convo_messages:
            lines.append("RECENT CONVERSATION:")
            recent = convo_messages[-5:] if len(convo_messages) > 5 else convo_messages
            for msg in recent:
                role = msg.get("role", "?")
                content = msg.get("content", "")[:150]
                lines.append(f"  [{role}] {content}")
            lines.append("")

        lines.append("--- END CONTEXT ---")
        return "\n".join(lines)

    def _build_rolling_summary(self, stats, convo_messages=None) -> str:
        """Build the rolling summary content."""
        now = datetime.now()
        lines = [
            "# Rolling Session Summary",
            f"*Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            f"**Duration:** {stats.duration_minutes:.0f} min",
            f"**Events:** {stats.event_count}",
            f"**Est. Tokens:** ~{stats.tokens_estimated:,}",
            "",
        ]

        # Tool usage
        if stats.tool_counts:
            lines.append("## Tools")
            for tool, count in stats.tool_counts.most_common(10):
                lines.append(f"- {tool}: {count}")
            lines.append("")

        # Files touched
        all_files = stats.files_touched | self._files_mentioned
        if all_files:
            lines.append(f"## Files ({len(all_files)})")
            for f in sorted(all_files)[:20]:
                short = "/".join(Path(f).parts[-3:]) if len(Path(f).parts) > 3 else f
                lines.append(f"- {short}")
            if len(all_files) > 20:
                lines.append(f"  ...and {len(all_files) - 20} more")
            lines.append("")

        # Key events
        if self._key_events:
            lines.append("## Key Events")
            for evt in self._key_events[-15:]:
                lines.append(f"- {evt}")
            lines.append("")

        # Topics
        if self._session_topics:
            lines.append("## User Topics")
            for topic in self._session_topics[-10:]:
                short = topic[:80] + "..." if len(topic) > 80 else topic
                lines.append(f'- "{short}"')
            lines.append("")

        return "\n".join(lines)

    def _build_handoff(self, stats, buddy_state=None, convo_messages=None) -> str:
        """Build the session handoff content for .claude/rules/."""
        now = datetime.now()
        lines = [
            "# Buddy Session State",
            f"*Written by Buddy at {now.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "<!-- This file is auto-generated by Buddy's Token Guardian. -->",
            "<!-- It helps Claude pick up where the last session left off. -->",
            "",
        ]

        # Session stats
        lines.append("## Last Session")
        lines.append(f"- Duration: {stats.duration_minutes:.0f} min")
        lines.append(f"- Events: {stats.event_count}")
        lines.append(f"- Est. tokens: ~{stats.tokens_estimated:,}")
        if stats.tool_counts:
            top_tools = ", ".join(
                f"{t}({c})" for t, c in stats.tool_counts.most_common(5)
            )
            lines.append(f"- Top tools: {top_tools}")
        lines.append("")

        # Active buddy
        if buddy_state:
            lines.append("## Active Buddy")
            lines.append(
                f"- {buddy_state.name} ({buddy_state.species.name}, "
                f"{buddy_state.species.rarity.value})"
            )
            lines.append(f"- Level {buddy_state.level}, mood: {buddy_state.mood}")
            lines.append("")

        # What we were working on
        if self._session_topics:
            lines.append("## What We Were Doing")
            # Show the last few topics as context
            for topic in self._session_topics[-5:]:
                short = topic[:100] + "..." if len(topic) > 100 else topic
                lines.append(f'- "{short}"')
            lines.append("")

        # Files that were active
        all_files = stats.files_touched | self._files_mentioned
        if all_files:
            lines.append("## Files In Play")
            for f in sorted(all_files)[:15]:
                short = "/".join(Path(f).parts[-3:]) if len(Path(f).parts) > 3 else f
                lines.append(f"- {short}")
            lines.append("")

        # Key events
        if self._key_events:
            lines.append("## Recent Activity")
            for evt in self._key_events[-10:]:
                lines.append(f"- {evt}")
            lines.append("")

        return "\n".join(lines)
