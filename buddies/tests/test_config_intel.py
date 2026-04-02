"""Tests for Config Intelligence and README Intelligence systems."""

import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest

from buddies.core.config_intel import (
    ConfigIntelligence,
    SessionLearner,
    compact_handoff,
    generate_session_summary,
)
from buddies.core.readme_intel import scan_readme, scaffold_readme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class FakeObserverStats:
    """Minimal stand-in for SessionStats."""
    duration_minutes: float = 25.0
    event_count: int = 42
    tokens_estimated: int = 8500
    tool_counts: Counter | None = None
    files_touched: set | None = None


# ===================================================================
# ConfigIntelligence — scan_claude_md
# ===================================================================


class TestScanClaudeMd:
    """Tests for ConfigIntelligence.scan_claude_md."""

    def test_missing_claude_md_grade_f(self, tmp_path):
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.grade == "F"
        assert any("No CLAUDE.md" in s for s in report.suggestions)

    def test_empty_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.exists is True
        assert report.line_count == 0

    def test_short_claude_md_not_bloated(self, tmp_path):
        content = "# Project\n\nSome info.\n\n## Commands\n\nRun it.\n"
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.is_bloated is False

    def test_bloated_claude_md(self, tmp_path):
        lines = ["# Big File"] + [f"Line {i}" for i in range(200)]
        (tmp_path / "CLAUDE.md").write_text("\n".join(lines), encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.is_bloated is True
        assert any("lines" in s for s in report.suggestions)

    def test_routing_pattern_detected(self, tmp_path):
        content = "# Project\n\nSee `.claude/rules/` for details.\n"
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.has_routing is True
        # The section containing the routing text should also flag has_routing
        routing_sections = [s for s in report.sections if s.has_routing]
        assert len(routing_sections) >= 1

    def test_bloated_section_no_routing(self, tmp_path):
        # Section with >30 lines and no routing pattern
        section_lines = ["## Big Section"] + [f"Detail line {i}" for i in range(35)]
        content = "# Title\n\n" + "\n".join(section_lines)
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert len(report.bloated_sections) >= 1
        assert report.bloated_sections[0].title == "Big Section"

    def test_recommended_sections_suggestions(self, tmp_path):
        content = "# Title\n\nJust a title, nothing else.\n"
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        # Should suggest missing recommended sections
        assert len(report.suggestions) > 0

    def test_grade_a_short_with_routing_and_sections(self, tmp_path):
        content = (
            "# Project\n\n"
            "## Key Files\n\nSee `.claude/rules/` for guidance.\n\n"
            "## Commands\n\n`python main.py`\n\n"
            "## Rules\n\nCheck `.claude/rules/preferences.md`\n\n"
            "## Architecture\n\nModular design.\n\n"
            "## Dependencies\n\nPython 3.11+\n"
        )
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.grade == "A"

    def test_grade_d_or_f_long_no_routing_no_sections(self, tmp_path):
        # >200 lines, no sections beyond title, no routing
        lines = ["# Dump"] + [f"Random info line {i}" for i in range(250)]
        (tmp_path / "CLAUDE.md").write_text("\n".join(lines), encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        assert report.grade in ("D", "F")

    def test_sections_parsed_correctly(self, tmp_path):
        content = "# Title\n\nIntro.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"
        (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_claude_md()
        titles = [s.title for s in report.sections]
        assert "Title" in titles
        assert "Section A" in titles
        assert "Section B" in titles


# ===================================================================
# ConfigIntelligence — scan_rules_dir
# ===================================================================


class TestScanRulesDir:
    """Tests for ConfigIntelligence.scan_rules_dir."""

    def test_no_claude_dir(self, tmp_path):
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_rules_dir()
        assert report.claude_dir_exists is False
        assert any("No .claude/" in s for s in report.suggestions)

    def test_claude_dir_no_rules(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_rules_dir()
        assert report.claude_dir_exists is True
        assert report.rules_dir_exists is False
        assert any("No .claude/rules/" in s for s in report.suggestions)

    def test_rules_dir_empty(self, tmp_path):
        (tmp_path / ".claude" / "rules").mkdir(parents=True)
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_rules_dir()
        assert report.rules_dir_exists is True
        assert report.rule_files == []
        assert any("empty" in s for s in report.suggestions)

    def test_rules_dir_with_md_files(self, tmp_path):
        rules = tmp_path / ".claude" / "rules"
        rules.mkdir(parents=True)
        (rules / "preferences.md").write_text("# Prefs", encoding="utf-8")
        (rules / "decisions.md").write_text("# Decisions", encoding="utf-8")
        (rules / "not-md.txt").write_text("skip me", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_rules_dir()
        assert report.rule_files == ["decisions.md", "preferences.md"]

    def test_settings_json_detected(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan_rules_dir()
        assert report.settings_exists is True


# ===================================================================
# ConfigIntelligence — generate_scaffold
# ===================================================================


class TestGenerateScaffold:
    """Tests for ConfigIntelligence.generate_scaffold."""

    def test_returns_dict_of_paths(self, tmp_path):
        ci = ConfigIntelligence(tmp_path)
        scaffold = ci.generate_scaffold()
        assert isinstance(scaffold, dict)
        assert all(isinstance(k, str) for k in scaffold)
        assert all(isinstance(v, str) for v in scaffold.values())

    def test_skips_existing_files(self, tmp_path):
        rules = tmp_path / ".claude" / "rules"
        rules.mkdir(parents=True)
        (rules / "preferences.md").write_text("existing", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        scaffold = ci.generate_scaffold()
        assert ".claude/rules/preferences.md" not in scaffold

    def test_includes_claude_md_when_missing(self, tmp_path):
        ci = ConfigIntelligence(tmp_path)
        scaffold = ci.generate_scaffold()
        assert "CLAUDE.md" in scaffold

    def test_generated_files_have_expected_content(self, tmp_path):
        ci = ConfigIntelligence(tmp_path)
        scaffold = ci.generate_scaffold()
        assert "preferences" in scaffold.get(".claude/rules/preferences.md", "").lower()
        assert "decisions" in scaffold.get(".claude/rules/decisions.md", "").lower()
        assert ".claude/rules/project-context.md" in scaffold
        assert ".claude/rules/buddy-learned.md" in scaffold


# ===================================================================
# ConfigIntelligence — scan() full
# ===================================================================


class TestScanFull:
    """Tests for ConfigIntelligence.scan()."""

    def test_returns_config_report_with_grade(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan()
        assert report.overall_grade in ("A", "B", "C", "D", "F")

    def test_summary_includes_status(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        rules = tmp_path / ".claude" / "rules"
        rules.mkdir(parents=True)
        (rules / "prefs.md").write_text("# P", encoding="utf-8")
        ci = ConfigIntelligence(tmp_path)
        report = ci.scan()
        assert "CLAUDE.md" in report.summary
        assert "1 files" in report.summary


# ===================================================================
# SessionLearner
# ===================================================================


class TestSessionLearner:
    """Tests for the SessionLearner auto-rule system."""

    def test_non_correction_returns_none(self, tmp_path):
        sl = SessionLearner(tmp_path)
        assert sl.observe("Great job, looks good!") is None

    def test_single_correction_returns_none(self, tmp_path):
        sl = SessionLearner(tmp_path)
        assert sl.observe("Don't use tabs for indentation") is None

    def test_three_corrections_same_keyword_returns_rule(self, tmp_path):
        sl = SessionLearner(tmp_path)
        sl.observe("Don't use semicolons in Python")
        sl.observe("Stop adding semicolons everywhere")
        result = sl.observe("Never put semicolons at end of lines")
        assert result is not None
        assert "semicolons" in result.lower()

    def test_rule_contains_keyword(self, tmp_path):
        sl = SessionLearner(tmp_path)
        sl.observe("Don't use global variables")
        sl.observe("Stop using global state")
        result = sl.observe("Never rely on global variables")
        assert result is not None
        assert "global" in result.lower()

    def test_same_keyword_not_triggered_twice(self, tmp_path):
        sl = SessionLearner(tmp_path)
        sl.observe("Don't use semicolons in Python")
        sl.observe("Stop adding semicolons everywhere")
        first = sl.observe("Never put semicolons at end of lines")
        assert first is not None
        # Fourth mention should not trigger again
        second = sl.observe("Always remove semicolons please")
        assert second is None

    def test_extract_keywords_skips_stop_words(self, tmp_path):
        sl = SessionLearner(tmp_path)
        keywords = sl._extract_keywords("the code should always use type hints")
        assert "the" not in keywords
        assert "should" not in keywords
        assert "always" not in keywords
        # "code", "type", "hints" should survive
        assert "code" in keywords
        assert "type" in keywords
        assert "hints" in keywords

    def test_write_rule_creates_file(self, tmp_path):
        sl = SessionLearner(tmp_path)
        result = sl.write_rule("Always use type hints")
        assert result is True
        learned = tmp_path / ".claude" / "rules" / "buddy-learned.md"
        assert learned.exists()
        content = learned.read_text(encoding="utf-8")
        assert "Always use type hints" in content

    def test_write_rule_creates_directory(self, tmp_path):
        sl = SessionLearner(tmp_path)
        assert not (tmp_path / ".claude").exists()
        sl.write_rule("Test rule")
        assert (tmp_path / ".claude" / "rules").is_dir()


# ===================================================================
# generate_session_summary
# ===================================================================


class TestGenerateSessionSummary:
    """Tests for generate_session_summary."""

    def test_includes_duration_events_tokens(self):
        stats = FakeObserverStats()
        output = generate_session_summary(stats)
        assert "25" in output  # duration
        assert "42" in output  # events
        assert "8,500" in output  # tokens

    def test_includes_tool_counts(self):
        stats = FakeObserverStats(tool_counts=Counter({"Read": 10, "Edit": 5}))
        output = generate_session_summary(stats)
        assert "Read" in output
        assert "10" in output
        assert "Edit" in output

    def test_includes_files_touched(self):
        stats = FakeObserverStats(files_touched={"src/app.py", "src/config.py"})
        output = generate_session_summary(stats)
        assert "app.py" in output
        assert "config.py" in output


# ===================================================================
# compact_handoff
# ===================================================================


class TestCompactHandoff:
    """Tests for compact_handoff."""

    def test_under_600_lines_no_change(self, tmp_path):
        handoff = tmp_path / "HANDOFF.md"
        handoff.write_text("# Handoff\n\nShort file.\n", encoding="utf-8")
        assert compact_handoff(tmp_path) is False

    def test_over_600_lines_compacts_old_sessions(self, tmp_path):
        # Build a file >600 lines with 5 session sections
        parts = ["# Handoff\n\nIntro text.\n"]
        for i in range(5):
            section = [f"## Session Notes {i+1}\n"]
            for j in range(130):
                marker = "- item" if j % 3 != 0 else "- item done"
                section.append(marker)
            parts.append("\n".join(section))
        handoff = tmp_path / "HANDOFF.md"
        handoff.write_text("\n".join(parts), encoding="utf-8")
        original_len = len(handoff.read_text(encoding="utf-8").split("\n"))
        assert original_len > 600
        result = compact_handoff(tmp_path, max_session_notes=3)
        assert result is True
        new_content = handoff.read_text(encoding="utf-8")
        assert "Session History (Compacted)" in new_content

    def test_keeps_max_session_notes_recent(self, tmp_path):
        parts = ["# Handoff\n\nIntro.\n"]
        for i in range(5):
            section = [f"## Session Notes {i+1}\n"]
            for j in range(130):
                section.append(f"- line {j}")
            parts.append("\n".join(section))
        handoff = tmp_path / "HANDOFF.md"
        handoff.write_text("\n".join(parts), encoding="utf-8")
        compact_handoff(tmp_path, max_session_notes=2)
        content = handoff.read_text(encoding="utf-8")
        # The last 2 sessions should survive verbatim
        assert "## Session Notes 4" in content
        assert "## Session Notes 5" in content

    def test_no_session_sections_returns_false(self, tmp_path):
        lines = ["# Handoff"] + [f"Line {i}" for i in range(700)]
        handoff = tmp_path / "HANDOFF.md"
        handoff.write_text("\n".join(lines), encoding="utf-8")
        assert compact_handoff(tmp_path) is False


# ===================================================================
# README Intel — scan_readme
# ===================================================================


class TestScanReadme:
    """Tests for scan_readme."""

    def test_no_readme_grade_f(self, tmp_path):
        report = scan_readme(tmp_path)
        assert report.grade == "F"

    def test_readme_with_title(self, tmp_path):
        (tmp_path / "README.md").write_text("# My Project\n\nDescription here that is long enough.\n", encoding="utf-8")
        report = scan_readme(tmp_path)
        assert report.has_title is True

    def test_readme_with_badges(self, tmp_path):
        content = (
            "# Proj\n\n"
            "[![Build](https://img.shields.io/badge/build-passing-green.svg)](https://ci)\n\n"
            "A project description that is definitely long enough.\n"
        )
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        report = scan_readme(tmp_path)
        assert report.has_badges is True

    def test_readme_with_install(self, tmp_path):
        content = "# Proj\n\n## Install\n\n```bash\npip install myproj\n```\n"
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        report = scan_readme(tmp_path)
        assert report.has_install is True

    def test_readme_with_collapsible(self, tmp_path):
        content = "# Proj\n\n<details>\n<summary>More</summary>\nHidden content.\n</details>\n"
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        report = scan_readme(tmp_path)
        assert report.has_collapsible is True

    def test_full_readme_grades_well(self, tmp_path):
        content = (
            "# My Project\n\n"
            "[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)\n\n"
            "A comprehensive tool for doing great things in the world.\n\n"
            "## Quick Start\n\n```bash\npip install myproj\n```\n\n"
            "## Usage\n\n```python\nimport myproj\nmyproj.run()\n```\n\n"
            "## License\n\nMIT\n\n"
            "![Screenshot](screenshot.png)\n\n"
            "![Demo](demo.gif)\n\n"
            "## Contributing\n\nPRs welcome!\n"
        )
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        report = scan_readme(tmp_path)
        assert report.grade in ("A", "B")

    def test_sections_parsed(self, tmp_path):
        content = "# Title\n\nIntro.\n\n## Install\n\nSteps.\n\n## Usage\n\nExamples.\n"
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        report = scan_readme(tmp_path)
        titles = [s.title for s in report.sections]
        assert "Title" in titles
        assert "Install" in titles
        assert "Usage" in titles

    def test_suggestions_for_missing_elements(self, tmp_path):
        (tmp_path / "README.md").write_text("# Bare\n", encoding="utf-8")
        report = scan_readme(tmp_path)
        # Should suggest adding description, badges, install, usage, etc.
        assert len(report.suggestions) >= 3


# ===================================================================
# README Intel — scaffold_readme
# ===================================================================


class TestScaffoldReadme:
    """Tests for scaffold_readme."""

    def test_python_project_pip_install(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
        output = scaffold_readme(tmp_path)
        assert "pip install" in output

    def test_node_project_npm_install(self, tmp_path):
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        output = scaffold_readme(tmp_path)
        assert "npm install" in output

    def test_output_has_expected_sections(self, tmp_path):
        output = scaffold_readme(tmp_path)
        assert output.startswith("#")
        assert "Quick Start" in output
        assert "License" in output
