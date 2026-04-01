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
        self._safety_gates: SafetyGates | None = None

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

        # Run through safety gates if available
        if self._safety_gates:
            validated = []
            for s in new_suggestions:
                result = self._safety_gates.validate(s)
                if result.passed:
                    validated.append(s)
            new_suggestions = validated

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
        """Mark a suggestion as accepted and add to golden suite."""
        await self.store.db.execute(
            "UPDATE rule_suggestions SET status = 'accepted' WHERE rule_content = ?",
            (suggestion.config_snippet,),
        )
        await self.store.db.commit()

        # Add to golden suite
        if self._safety_gates:
            await self._safety_gates.add_to_golden_suite(suggestion)

    def set_safety_gates(self, gates: SafetyGates):
        """Attach safety gates for validation."""
        self._safety_gates = gates


# ---------------------------------------------------------------------------
# Safety Gates — validate rules before auto-application
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of running a suggestion through safety gates."""
    passed: bool
    gate_results: dict[str, bool]  # gate_name -> passed
    reason: str = ""


@dataclass
class GoldenRule:
    """A successful rule application stored for reference."""
    rule_type: str
    content: str
    reason: str
    applied_at: str
    effectiveness: float  # 0.0-1.0


class SafetyGates:
    """Validates rule suggestions through multiple safety checks before application.

    Five gates:
    1. Duplicate check — is this rule already in the config?
    2. Conflict check — does this contradict an existing rule?
    3. Size check — will this make CLAUDE.md too large?
    4. Golden suite check — is this consistent with known-good rules?
    5. Scope check — is this change small enough to auto-apply?
    """

    def __init__(self, project_path: Path | None = None, store: BuddyStore | None = None):
        self.project_path = project_path or Path.cwd()
        self.store = store
        self._golden_suite: list[GoldenRule] = []

    async def load_golden_suite(self):
        """Load golden rules from DB."""
        if not self.store:
            return
        try:
            async with self.store.db.execute(
                "SELECT rule_type, rule_content, reason, timestamp FROM rule_suggestions "
                "WHERE status = 'accepted' ORDER BY timestamp DESC LIMIT 50"
            ) as cursor:
                rows = await cursor.fetchall()
                self._golden_suite = [
                    GoldenRule(
                        rule_type=row[0],
                        content=row[1],
                        reason=row[2],
                        applied_at=row[3],
                        effectiveness=1.0,
                    )
                    for row in rows
                ]
        except Exception:
            pass

    def validate(self, suggestion: RuleSuggestion) -> ValidationResult:
        """Run a suggestion through all safety gates."""
        gates = {}

        gates["duplicate"] = self._gate_duplicate(suggestion)
        gates["conflict"] = self._gate_conflict(suggestion)
        gates["size"] = self._gate_size(suggestion)
        gates["golden"] = self._gate_golden_consistency(suggestion)
        gates["scope"] = self._gate_scope(suggestion)

        passed = all(gates.values())
        failed_gates = [name for name, ok in gates.items() if not ok]

        reason = ""
        if not passed:
            reason = f"Failed gates: {', '.join(failed_gates)}"

        return ValidationResult(passed=passed, gate_results=gates, reason=reason)

    def _gate_duplicate(self, suggestion: RuleSuggestion) -> bool:
        """Gate 1: Check if this rule already exists in the config."""
        if suggestion.rule_type == "tip":
            return True  # Tips aren't applied to files

        if suggestion.rule_type == "claude_md":
            claude_md = self.project_path / "CLAUDE.md"
            if claude_md.exists():
                content = claude_md.read_text(encoding="utf-8", errors="replace")
                # Check if the core content is already present
                snippet_lines = suggestion.config_snippet.strip().split("\n")
                for line in snippet_lines:
                    line = line.strip()
                    if line and len(line) > 10 and line in content:
                        return False  # Duplicate found

        if suggestion.rule_type == "settings":
            settings_path = self.project_path / ".claude" / "settings.json"
            if settings_path.exists():
                try:
                    existing = json.loads(settings_path.read_text(encoding="utf-8"))
                    snippet = json.loads(suggestion.config_snippet)
                    # Check if all keys in snippet already exist with same values
                    if all(existing.get(k) == v for k, v in snippet.items()):
                        return False
                except (json.JSONDecodeError, ValueError):
                    pass

        return True  # Not a duplicate

    def _gate_conflict(self, suggestion: RuleSuggestion) -> bool:
        """Gate 2: Check if this rule contradicts existing rules."""
        rules_dir = self.project_path / ".claude" / "rules"
        if not rules_dir.exists():
            return True  # No rules to conflict with

        snippet_lower = suggestion.config_snippet.lower()

        # Read all existing rule files
        for rule_file in rules_dir.glob("*.md"):
            try:
                content = rule_file.read_text(encoding="utf-8", errors="replace").lower()

                # Simple heuristic: look for contradictory directives
                # "always X" vs "never X", "use X" vs "don't use X"
                for keyword in _extract_action_keywords(snippet_lower):
                    negated = f"don't {keyword}" if f"don't {keyword}" not in snippet_lower else keyword
                    if negated in content and keyword in snippet_lower:
                        return False  # Potential conflict
            except OSError:
                continue

        return True  # No conflicts detected

    def _gate_size(self, suggestion: RuleSuggestion) -> bool:
        """Gate 3: Will applying this make CLAUDE.md too large?"""
        if suggestion.rule_type != "claude_md":
            return True

        claude_md = self.project_path / "CLAUDE.md"
        current_lines = 0
        if claude_md.exists():
            current_lines = len(claude_md.read_text(encoding="utf-8", errors="replace").split("\n"))

        new_lines = len(suggestion.config_snippet.split("\n"))
        return (current_lines + new_lines) < 150  # CLAUDE.md should stay under 150 lines

    def _gate_golden_consistency(self, suggestion: RuleSuggestion) -> bool:
        """Gate 4: Is this consistent with the golden suite?"""
        if not self._golden_suite:
            return True  # No golden rules yet, pass by default

        # Check if any golden rule explicitly contradicts this suggestion
        snippet_lower = suggestion.config_snippet.lower()
        for golden in self._golden_suite:
            golden_lower = golden.content.lower()
            # Very simple: if golden says "use X" and suggestion says "don't use X" (or vice versa)
            for keyword in _extract_action_keywords(snippet_lower):
                negated = f"don't {keyword}"
                if negated in golden_lower and keyword in snippet_lower:
                    return False
                if keyword in golden_lower and negated in snippet_lower:
                    return False

        return True

    def _gate_scope(self, suggestion: RuleSuggestion) -> bool:
        """Gate 5: Is this change small enough to auto-apply?"""
        if suggestion.rule_type == "tip":
            return True  # Tips are just messages

        # Reject large config snippets
        line_count = len(suggestion.config_snippet.split("\n"))
        return line_count <= 20  # Max 20 lines for auto-application

    async def add_to_golden_suite(self, suggestion: RuleSuggestion):
        """Add a successfully accepted rule to the golden suite."""
        self._golden_suite.append(GoldenRule(
            rule_type=suggestion.rule_type,
            content=suggestion.config_snippet,
            reason=suggestion.reason,
            applied_at=time.strftime("%Y-%m-%d %H:%M"),
            effectiveness=1.0,
        ))

    def get_golden_suite(self) -> list[GoldenRule]:
        """Get the current golden suite for display."""
        return self._golden_suite.copy()


def _extract_action_keywords(text: str) -> list[str]:
    """Extract action-oriented keywords from a rule text for conflict detection."""
    import re
    # Look for "use X", "prefer X", "always X", "avoid X", "never X"
    patterns = [
        r"(?:use|prefer|always|require)\s+(\w+)",
        r"(?:avoid|never|don't use|skip)\s+(\w+)",
    ]
    keywords = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            keywords.append(match.group(1))
    return keywords
