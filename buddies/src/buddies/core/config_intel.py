"""Config Intelligence — CLAUDE.md health, linting, scaffolding, and session learning.

Analyzes Claude Code configuration files and suggests improvements.
Design principle: CLAUDE.md should be a routing file (<150 lines),
not a knowledge dump. Buddy enforces this.
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data classes for scan results
# ---------------------------------------------------------------------------

@dataclass
class Section:
    """A markdown section found in CLAUDE.md."""
    title: str
    level: int  # heading level (1-6)
    line_start: int
    line_count: int
    has_routing: bool  # points to .claude/rules/ or other files


@dataclass
class ClaudeMdReport:
    """Results of scanning a CLAUDE.md file."""
    exists: bool = False
    path: Path | None = None
    line_count: int = 0
    is_bloated: bool = False  # >150 lines
    sections: list[Section] = field(default_factory=list)
    bloated_sections: list[Section] = field(default_factory=list)  # >30 lines, no routing
    has_routing: bool = False  # any section points to rules/
    suggestions: list[str] = field(default_factory=list)
    grade: str = "?"  # A/B/C/D/F


@dataclass
class RulesDirReport:
    """Results of scanning .claude/rules/ directory."""
    claude_dir_exists: bool = False
    rules_dir_exists: bool = False
    rule_files: list[str] = field(default_factory=list)
    settings_exists: bool = False
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ConfigReport:
    """Combined config health report."""
    claude_md: ClaudeMdReport = field(default_factory=ClaudeMdReport)
    rules_dir: RulesDirReport = field(default_factory=RulesDirReport)
    overall_grade: str = "?"
    summary: str = ""


# ---------------------------------------------------------------------------
# Recommended sections and routing patterns
# ---------------------------------------------------------------------------

RECOMMENDED_SECTIONS = [
    "project",
    "key files",
    "commands",
    "rules",
    "architecture",
    "dependencies",
]

ROUTING_PATTERNS = [
    r"\.claude/rules/",
    r"\.claude/",
    r"@import",
    r"see\s+[\w./]+\.md",
    r"refer\s+to\s+[\w./]+",
    r"defined\s+in\s+[\w./]+",
]


# ---------------------------------------------------------------------------
# Config Intelligence — the main scanner
# ---------------------------------------------------------------------------

class ConfigIntelligence:
    """Scans and analyzes Claude Code configuration health."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or self._find_project_root()

    def _find_project_root(self) -> Path:
        """Walk up from CWD looking for .claude/ or CLAUDE.md."""
        cwd = Path.cwd()
        for p in [cwd, *cwd.parents]:
            if (p / ".claude").is_dir() or (p / "CLAUDE.md").is_file():
                return p
        return cwd

    def scan(self) -> ConfigReport:
        """Run full config health scan."""
        report = ConfigReport()
        report.claude_md = self.scan_claude_md()
        report.rules_dir = self.scan_rules_dir()
        report.overall_grade = self._compute_grade(report)
        report.summary = self._build_summary(report)
        return report

    def scan_claude_md(self) -> ClaudeMdReport:
        """Analyze CLAUDE.md for health issues."""
        report = ClaudeMdReport()
        claude_md = self.project_path / "CLAUDE.md"

        if not claude_md.is_file():
            report.suggestions.append(
                "No CLAUDE.md found. Create one to help Claude understand your project."
            )
            report.grade = "F"
            return report

        report.exists = True
        report.path = claude_md

        try:
            content = claude_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            report.suggestions.append("Could not read CLAUDE.md — check file encoding.")
            report.grade = "D"
            return report

        lines = content.splitlines()
        report.line_count = len(lines)
        report.is_bloated = report.line_count > 150

        # Parse sections
        report.sections = self._parse_sections(lines)

        # Check for routing patterns
        routing_re = re.compile("|".join(ROUTING_PATTERNS), re.IGNORECASE)
        report.has_routing = bool(routing_re.search(content))

        # Find bloated sections (>30 lines without routing)
        for section in report.sections:
            section_text = "\n".join(
                lines[section.line_start : section.line_start + section.line_count]
            )
            section.has_routing = bool(routing_re.search(section_text))
            if section.line_count > 30 and not section.has_routing:
                report.bloated_sections.append(section)

        # Generate suggestions
        if report.is_bloated:
            report.suggestions.append(
                f"CLAUDE.md is {report.line_count} lines — aim for <150. "
                "Move detailed knowledge into .claude/rules/ files."
            )

        for bs in report.bloated_sections:
            report.suggestions.append(
                f'Section "{bs.title}" is {bs.line_count} lines with no routing. '
                f"Extract to .claude/rules/{self._slugify(bs.title)}.md"
            )

        # Check for recommended sections
        section_titles_lower = {s.title.lower() for s in report.sections}
        for rec in RECOMMENDED_SECTIONS:
            if not any(rec in t for t in section_titles_lower):
                report.suggestions.append(
                    f'Consider adding a "{rec.title()}" section (or route to a rules file).'
                )

        if not report.has_routing and report.line_count > 50:
            report.suggestions.append(
                "No routing found. Add references to .claude/rules/ files "
                "to keep CLAUDE.md lean."
            )

        # Grade
        report.grade = self._grade_claude_md(report)
        return report

    def scan_rules_dir(self) -> RulesDirReport:
        """Check .claude/ and .claude/rules/ directory status."""
        report = RulesDirReport()

        claude_dir = self.project_path / ".claude"
        report.claude_dir_exists = claude_dir.is_dir()

        if report.claude_dir_exists:
            report.settings_exists = (claude_dir / "settings.json").is_file()

        rules_dir = claude_dir / "rules"
        report.rules_dir_exists = rules_dir.is_dir()

        if report.rules_dir_exists:
            report.rule_files = sorted(
                f.name for f in rules_dir.iterdir()
                if f.is_file() and f.suffix == ".md"
            )

        # Suggestions
        if not report.claude_dir_exists:
            report.suggestions.append(
                "No .claude/ directory found. Create one to store project config."
            )
        if not report.rules_dir_exists:
            report.suggestions.append(
                "No .claude/rules/ directory. Create it to organize project knowledge."
            )
        elif not report.rule_files:
            report.suggestions.append(
                ".claude/rules/ exists but is empty. Add rule files to guide Claude."
            )

        return report

    def generate_scaffold(self) -> dict[str, str]:
        """Generate recommended .claude/rules/ structure.

        Returns dict of {relative_path: file_content} — does NOT write files.
        Skips files that already exist.
        """
        scaffold = {}
        rules_dir = self.project_path / ".claude" / "rules"

        files = {
            "preferences.md": (
                "# User Preferences\n\n"
                "<!-- Add your coding preferences, style guidelines, and workflow notes here -->\n"
                "<!-- Example: 'Always use type hints in Python', 'Prefer functional style' -->\n"
            ),
            "decisions.md": (
                "# Architecture Decisions\n\n"
                "<!-- Record key architecture and design decisions here -->\n"
                "<!-- Example: 'Using SQLite for local storage because no server needed' -->\n"
            ),
            "buddy-learned.md": (
                "# Buddy-Learned Rules\n\n"
                "<!-- Auto-populated by Buddy when it detects repeated corrections -->\n"
                "<!-- You can also add rules manually here -->\n"
            ),
            "project-context.md": (
                "# Project Context\n\n"
                "<!-- Key context about this project that Claude should know -->\n"
                "<!-- Example: 'This is a Python TUI app using Textual framework' -->\n"
            ),
            "model-routing.md": (
                "# Model Routing Preferences\n\n"
                "When choosing which model to use for different tasks:\n\n"
                "- **Commits, git operations, simple file reads**: prefer Haiku (fast, cheap)\n"
                "- **Implementation after a plan is established**: prefer Sonnet (capable, moderate cost)\n"
                "- **Architecture planning, design discussions, complex debugging**: prefer Opus (best quality)\n"
                "- **Exploring codebase, searching for patterns**: prefer Sonnet\n\n"
                "If the user seems to be in a different work phase than what the current model is suited for,\n"
                "suggest switching models with `/model <model-name>`.\n"
            ),
        }

        for filename, content in files.items():
            filepath = rules_dir / filename
            if not filepath.exists():
                scaffold[f".claude/rules/{filename}"] = content

        # Generate a routing CLAUDE.md if none exists
        claude_md = self.project_path / "CLAUDE.md"
        if not claude_md.exists():
            scaffold["CLAUDE.md"] = (
                "# Project Rules\n\n"
                "## Quick Reference\n"
                "See `.claude/rules/` for detailed guidance:\n"
                "- `preferences.md` — coding style and workflow\n"
                "- `decisions.md` — architecture decisions\n"
                "- `project-context.md` — project background\n"
                "- `buddy-learned.md` — auto-learned rules from sessions\n"
            )

        return scaffold

    def _parse_sections(self, lines: list[str]) -> list[Section]:
        """Parse markdown headings into sections."""
        sections: list[Section] = []
        for i, line in enumerate(lines):
            match = re.match(r"^(#{1,6})\s+(.+)", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                sections.append(Section(
                    title=title,
                    level=level,
                    line_start=i,
                    line_count=0,
                    has_routing=False,
                ))

        # Calculate line counts (each section runs until the next heading)
        for i, section in enumerate(sections):
            if i + 1 < len(sections):
                section.line_count = sections[i + 1].line_start - section.line_start
            else:
                section.line_count = len(lines) - section.line_start

        return sections

    def _grade_claude_md(self, report: ClaudeMdReport) -> str:
        score = 100

        if report.line_count > 200:
            score -= 40
        elif report.line_count > 150:
            score -= 20
        elif report.line_count == 0:
            score -= 50

        score -= len(report.bloated_sections) * 10

        if not report.has_routing and report.line_count > 50:
            score -= 15

        if len(report.sections) < 2:
            score -= 10

        if score >= 90:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        return "F"

    def _compute_grade(self, report: ConfigReport) -> str:
        md_score = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}.get(report.claude_md.grade, 0)
        rules_score = 3  # neutral
        if report.rules_dir.rules_dir_exists and report.rules_dir.rule_files:
            rules_score = 5
        elif report.rules_dir.rules_dir_exists:
            rules_score = 3
        elif not report.rules_dir.claude_dir_exists:
            rules_score = 1

        avg = (md_score + rules_score) / 2
        if avg >= 4.5:
            return "A"
        elif avg >= 3.5:
            return "B"
        elif avg >= 2.5:
            return "C"
        elif avg >= 1.5:
            return "D"
        return "F"

    def _build_summary(self, report: ConfigReport) -> str:
        parts = []
        md = report.claude_md
        if md.exists:
            parts.append(f"CLAUDE.md: {md.line_count} lines, grade {md.grade}")
        else:
            parts.append("CLAUDE.md: missing")

        rd = report.rules_dir
        if rd.rules_dir_exists:
            parts.append(f".claude/rules/: {len(rd.rule_files)} files")
        else:
            parts.append(".claude/rules/: missing")

        return " | ".join(parts)

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# Session Learner — detects repeated corrections and auto-writes rules
# ---------------------------------------------------------------------------

# Correction signal words
CORRECTION_SIGNALS = [
    "don't", "dont", "stop", "never", "always", "wrong", "no,",
    "not that", "instead", "should be", "supposed to", "please don't",
    "i told you", "i said", "remember to", "make sure",
]


class SessionLearner:
    """Watches user messages for repeated corrections and suggests rules."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self._corrections: list[str] = []  # raw correction messages
        self._keyword_counts: Counter = Counter()
        self._rules_written: set[str] = set()

    def observe(self, message: str) -> str | None:
        """Process a user message. Returns a rule suggestion if pattern detected.

        Call this with every user message. Returns None most of the time.
        When it detects 3+ corrections about similar topics, returns a
        suggested rule string.
        """
        msg_lower = message.lower()

        # Check if this looks like a correction
        if not any(signal in msg_lower for signal in CORRECTION_SIGNALS):
            return None

        self._corrections.append(message)

        # Extract keywords (nouns/verbs, skip common words)
        keywords = self._extract_keywords(msg_lower)
        self._keyword_counts.update(keywords)

        # Check for repeated themes (3+ corrections mentioning same keyword)
        for keyword, count in self._keyword_counts.most_common(5):
            if count >= 3 and keyword not in self._rules_written:
                # Find the corrections that mention this keyword
                relevant = [
                    c for c in self._corrections
                    if keyword in c.lower()
                ]
                if len(relevant) >= 3:
                    rule = self._synthesize_rule(keyword, relevant)
                    self._rules_written.add(keyword)
                    return rule

        return None

    def write_rule(self, rule_text: str) -> bool:
        """Append a learned rule to .claude/rules/buddy-learned.md.

        Creates the file and directory if needed. Returns True on success.
        """
        rules_dir = self.project_path / ".claude" / "rules"
        try:
            rules_dir.mkdir(parents=True, exist_ok=True)
            learned_file = rules_dir / "buddy-learned.md"
            if not learned_file.exists():
                learned_file.write_text(
                    "# Buddy-Learned Rules\n\n"
                    "<!-- Auto-populated by Buddy from session observations -->\n\n",
                    encoding="utf-8",
                )
            with open(learned_file, "a", encoding="utf-8") as f:
                f.write(f"\n- {rule_text}\n")
            return True
        except OSError:
            return False

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from a message."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "it", "its", "this", "that", "these", "those", "i", "you",
            "we", "they", "he", "she", "my", "your", "our", "me",
            "not", "no", "don't", "dont", "stop", "never", "always",
            "and", "or", "but", "if", "then", "so", "just", "also",
            "about", "up", "out", "what", "when", "where", "how", "why",
        }
        words = re.findall(r"[a-z][a-z_]+", text)
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _synthesize_rule(self, keyword: str, corrections: list[str]) -> str:
        """Create a rule from repeated corrections about the same topic."""
        # Use the most recent correction as the basis
        latest = corrections[-1].strip()
        # Clean it up — remove "don't" → "Do not" style
        rule = latest
        if len(rule) > 120:
            rule = rule[:120] + "..."
        return f"[auto-learned, keyword: {keyword}] {rule}"


# ---------------------------------------------------------------------------
# Session Summary — generates compact summary at session end
# ---------------------------------------------------------------------------

def generate_session_summary(
    observer_stats,
    convo_messages: list[dict] | None = None,
    rules_suggested: list[str] | None = None,
) -> str:
    """Generate a compact session summary.

    Args:
        observer_stats: SessionStats from the observer
        convo_messages: Optional list of conversation messages
        rules_suggested: Optional list of rule suggestions made during session
    """
    lines = ["# Session Summary", ""]

    # Duration and events
    duration = observer_stats.duration_minutes
    lines.append(f"**Duration:** {duration:.0f} minutes")
    lines.append(f"**Events:** {observer_stats.event_count}")
    lines.append(f"**Est. Tokens:** ~{observer_stats.tokens_estimated:,}")
    lines.append("")

    # Tool usage
    if observer_stats.tool_counts:
        lines.append("**Tools Used:**")
        for tool, count in observer_stats.tool_counts.most_common(10):
            lines.append(f"- {tool}: {count}")
        lines.append("")

    # Files touched
    if observer_stats.files_touched:
        lines.append(f"**Files Modified:** {len(observer_stats.files_touched)}")
        for f in sorted(observer_stats.files_touched)[:15]:
            short = "/".join(Path(f).parts[-3:]) if len(Path(f).parts) > 3 else f
            lines.append(f"- {short}")
        if len(observer_stats.files_touched) > 15:
            lines.append(f"  ...and {len(observer_stats.files_touched) - 15} more")
        lines.append("")

    # Topics from conversation
    if convo_messages:
        user_msgs = [m.get("text", "") for m in convo_messages if m.get("role") == "you"]
        if user_msgs:
            lines.append(f"**User Messages:** {len(user_msgs)}")
            # Show first few as topic hints
            for msg in user_msgs[:5]:
                short = msg[:80] + "..." if len(msg) > 80 else msg
                lines.append(f'- "{short}"')
            lines.append("")

    # Rules suggested
    if rules_suggested:
        lines.append("**Rules Suggested:**")
        for rule in rules_suggested:
            lines.append(f"- {rule}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Working Memory Compaction
# ---------------------------------------------------------------------------

def compact_handoff(project_path: Path | None = None, max_session_notes: int = 3) -> bool:
    """Compact HANDOFF.md by summarizing old session notes.

    Keeps the most recent `max_session_notes` session blocks verbatim.
    Older session blocks are compressed to a one-line summary each.
    Only triggers when file exceeds 600 lines to avoid unnecessary rewrites.

    Returns True if the file was modified, False otherwise.
    """
    project = project_path or Path.cwd()
    handoff_path = project / "HANDOFF.md"
    if not handoff_path.exists():
        return False

    content = handoff_path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    # Only compact when file is getting large
    if len(lines) < 600:
        return False

    # Find all "## Session Notes" sections
    session_sections: list[dict] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("## Session Notes"):
            title = lines[i]
            start = i
            i += 1
            # Find the end of this section (next ## or EOF)
            while i < len(lines) and not (lines[i].startswith("## ") and i > start):
                i += 1
            session_sections.append({
                "title": title,
                "start": start,
                "end": i,
                "lines": lines[start:i],
            })
        else:
            i += 1

    if len(session_sections) <= max_session_notes:
        return False  # Nothing to compact

    # Split: old sections to compress, recent sections to keep
    old_sections = session_sections[:-max_session_notes]
    keep_sections = session_sections[-max_session_notes:]

    # Summarize old sections into one-liners
    summaries = []
    for sec in old_sections:
        title = sec["title"].lstrip("#").strip()
        # Count completed items
        completed = sum(1 for ln in sec["lines"] if "✅" in ln)
        # Extract key highlights (first 3 completed items, shortened)
        highlights = []
        for ln in sec["lines"]:
            if "✅" in ln and len(highlights) < 3:
                clean = ln.strip().lstrip("-").strip()
                clean = clean.replace("✅ ", "").strip()
                if len(clean) > 60:
                    clean = clean[:57] + "..."
                highlights.append(clean)
        highlight_text = "; ".join(highlights) if highlights else "session work"
        summaries.append(f"- **{title}** ({completed} items): {highlight_text}")

    # Rebuild the file
    # 1. Everything before the first session section
    first_session_start = session_sections[0]["start"]
    before = lines[:first_session_start]

    # 2. Compressed history section
    compressed = [
        "## Session History (Compacted)",
        "",
        *summaries,
        "",
    ]

    # 3. Recent session sections (verbatim)
    recent_lines = []
    for sec in keep_sections:
        recent_lines.extend(sec["lines"])

    # 4. Everything after the last session section
    last_session_end = session_sections[-1]["end"]
    after = lines[last_session_end:]

    new_content = "\n".join(before + compressed + recent_lines + after)

    # Only write if we actually reduced size
    if len(new_content) >= len(content):
        return False

    handoff_path.write_text(new_content, encoding="utf-8")
    return True
