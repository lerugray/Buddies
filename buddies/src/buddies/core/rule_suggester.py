"""Rule suggestion engine — detects patterns and suggests Claude Code config improvements.

Watches session history for repeated behaviors and generates actionable
suggestions for .claude/settings.json rules and CLAUDE.md additions.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from buddies.core.session_observer import SessionObserver, SessionStats
from buddies.db.store import BuddyStore


@dataclass
class RuleSuggestion:
    """A suggested rule or config change."""
    rule_type: str  # "settings", "claude_md", "tip"
    title: str
    description: str
    config_snippet: str  # Ready-to-apply JSON or text
    reason: str
    confidence: float  # 0.0-1.0, how confident we are this is useful
    pattern_count: int  # How many times the pattern was observed


class RuleSuggester:
    """Analyzes session patterns and suggests improvements."""

    def __init__(self, store: BuddyStore):
        self.store = store
        self._suggestions_made: set[str] = set()  # Track what we've already suggested
        self._dismissed: set[str] = set()  # Track dismissed suggestions

    async def load_dismissed(self):
        """Load previously dismissed suggestions from DB."""
        # Check DB for dismissed rules
        try:
            async with self.store.db.execute(
                "SELECT rule_content FROM rule_suggestions WHERE status = 'dismissed'"
            ) as cursor:
                rows = await cursor.fetchall()
                self._dismissed = {row[0] for row in rows}
        except Exception:
            pass

    async def analyze(self, stats: SessionStats) -> list[RuleSuggestion]:
        """Analyze current session stats and generate suggestions."""
        suggestions = []

        suggestions.extend(self._check_repeated_reads(stats))
        suggestions.extend(self._check_high_token_usage(stats))
        suggestions.extend(self._check_tool_patterns(stats))
        suggestions.extend(self._check_file_patterns(stats))

        # Filter out already-suggested and dismissed
        new_suggestions = [
            s for s in suggestions
            if s.title not in self._suggestions_made
            and s.config_snippet not in self._dismissed
            and s.confidence >= 0.5
        ]

        # Save new suggestions to DB
        for s in new_suggestions:
            self._suggestions_made.add(s.title)
            await self.store.db.execute(
                "INSERT INTO rule_suggestions (rule_type, rule_content, reason, status) "
                "VALUES (?, ?, ?, 'pending')",
                (s.rule_type, s.config_snippet, s.reason),
            )
            await self.store.db.commit()

        return new_suggestions

    def _check_repeated_reads(self, stats: SessionStats) -> list[RuleSuggestion]:
        """Detect when Claude reads the same types of files repeatedly."""
        suggestions = []

        if stats.tool_counts.get("Read", 0) > 10:
            read_ratio = stats.tool_counts["Read"] / max(stats.event_count, 1)
            if read_ratio > 0.4:
                suggestions.append(RuleSuggestion(
                    rule_type="claude_md",
                    title="Add file location hints to CLAUDE.md",
                    description=(
                        "Claude is spending a lot of time reading files — "
                        "probably searching for things. Adding key file paths "
                        "to CLAUDE.md will save time and tokens."
                    ),
                    config_snippet=(
                        "# Key Files\n"
                        "- Main entry: src/...\n"
                        "- Config: ...\n"
                        "- Tests: tests/...\n"
                    ),
                    reason=f"Read tool used {stats.tool_counts['Read']} times "
                           f"({read_ratio:.0%} of all tool uses)",
                    confidence=min(0.9, 0.5 + read_ratio),
                    pattern_count=stats.tool_counts["Read"],
                ))

        return suggestions

    def _check_high_token_usage(self, stats: SessionStats) -> list[RuleSuggestion]:
        """Suggest optimizations when token usage is high."""
        suggestions = []

        if stats.tokens_estimated > 50000 and stats.duration_minutes > 0:
            tokens_per_min = stats.tokens_estimated / stats.duration_minutes
            if tokens_per_min > 5000:
                suggestions.append(RuleSuggestion(
                    rule_type="tip",
                    title="High token burn rate",
                    description=(
                        f"This session is using ~{tokens_per_min:.0f} tokens/min. "
                        "Consider breaking complex tasks into smaller steps, "
                        "or adding more context to CLAUDE.md to reduce exploration."
                    ),
                    config_snippet="",
                    reason=f"~{stats.tokens_estimated:,} tokens in {stats.duration_minutes:.1f} min",
                    confidence=0.7,
                    pattern_count=1,
                ))

        return suggestions

    def _check_tool_patterns(self, stats: SessionStats) -> list[RuleSuggestion]:
        """Detect inefficient tool usage patterns."""
        suggestions = []

        # Too many Agents
        agent_count = stats.tool_counts.get("Agent", 0)
        if agent_count > 5:
            suggestions.append(RuleSuggestion(
                rule_type="tip",
                title="Heavy subagent usage",
                description=(
                    f"Claude spawned {agent_count} subagents this session. "
                    "Each one uses significant tokens. If you see repeated "
                    "explore agents, adding paths to CLAUDE.md could help."
                ),
                config_snippet="",
                reason=f"{agent_count} Agent spawns in one session",
                confidence=0.6,
                pattern_count=agent_count,
            ))

        # Many Bash calls
        bash_count = stats.tool_counts.get("Bash", 0)
        if bash_count > 15:
            suggestions.append(RuleSuggestion(
                rule_type="tip",
                title="Many shell commands",
                description=(
                    f"Claude ran {bash_count} shell commands. If many are similar "
                    "(like repeated test runs), consider asking Claude to write "
                    "a script instead."
                ),
                config_snippet="",
                reason=f"{bash_count} Bash calls in one session",
                confidence=0.5,
                pattern_count=bash_count,
            ))

        return suggestions

    def _check_file_patterns(self, stats: SessionStats) -> list[RuleSuggestion]:
        """Detect when many files are being touched."""
        suggestions = []

        if len(stats.files_touched) > 10:
            suggestions.append(RuleSuggestion(
                rule_type="tip",
                title="Large change scope",
                description=(
                    f"Claude has touched {len(stats.files_touched)} files. "
                    "Large changes are harder to review. Consider asking Claude "
                    "to commit incrementally or explain the plan before continuing."
                ),
                config_snippet="",
                reason=f"{len(stats.files_touched)} files modified",
                confidence=0.6,
                pattern_count=len(stats.files_touched),
            ))

        return suggestions

    async def dismiss(self, config_snippet: str):
        """Mark a suggestion as dismissed so it won't be shown again."""
        self._dismissed.add(config_snippet)
        await self.store.db.execute(
            "UPDATE rule_suggestions SET status = 'dismissed' WHERE rule_content = ?",
            (config_snippet,),
        )
        await self.store.db.commit()

    async def accept(self, suggestion: RuleSuggestion):
        """Mark a suggestion as accepted."""
        await self.store.db.execute(
            "UPDATE rule_suggestions SET status = 'accepted' WHERE rule_content = ?",
            (suggestion.config_snippet,),
        )
        await self.store.db.commit()
