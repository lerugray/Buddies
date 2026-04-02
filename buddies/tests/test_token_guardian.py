"""Tests for the Token Guardian — token warnings, rolling summaries, and session handoff.

Covers TokenWarning dataclass, threshold detection, event tracking,
summary timing, file writing, and context export.
"""

import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from buddies.core.token_guardian import (
    CONTEXT_WINDOW,
    TOKEN_INFLATION,
    WARN_THRESHOLDS,
    TokenGuardian,
    TokenWarning,
)
from buddies.core.buddy_brain import Rarity, Species


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class MockStats:
    """Minimal stand-in for SessionStats."""
    duration_minutes: float = 10.0
    event_count: int = 50
    tokens_estimated: int = 5000
    tool_counts: Counter = field(default_factory=Counter)
    files_touched: set = field(default_factory=set)


@dataclass
class MockBuddy:
    """Minimal buddy state for context export / handoff tests."""
    name: str = "TestBuddy"
    species: Species = field(default_factory=lambda: Species(
        "duck", "🦆", Rarity.COMMON,
        {"patience": 3, "snark": 2}, "A test duck",
    ))
    level: int = 3
    mood: str = "happy"


def make_guardian(tmp_path: Path | None = None) -> TokenGuardian:
    return TokenGuardian(project_path=tmp_path or Path.cwd())


# ---------------------------------------------------------------------------
# TokenWarning dataclass
# ---------------------------------------------------------------------------

class TestTokenWarning:
    def test_creation(self):
        w = TokenWarning(threshold=0.50, message="half full")
        assert w.threshold == 0.50
        assert w.message == "half full"

    def test_default_triggered_at(self):
        w = TokenWarning(threshold=0.70, message="seventy")
        assert w.triggered_at == 0.0


# ---------------------------------------------------------------------------
# check_token_warning
# ---------------------------------------------------------------------------

class TestCheckTokenWarning:
    def test_below_all_thresholds(self):
        g = make_guardian()
        # Need tokens * 3.5 / 1_000_000 < 0.50 → tokens < ~142_857
        assert g.check_token_warning(10_000) is None

    def test_crossing_50_percent(self):
        g = make_guardian()
        # 150_000 * 3.5 = 525_000 → 52.5%
        w = g.check_token_warning(150_000)
        assert w is not None
        assert w.threshold == 0.50

    def test_crossing_70_percent(self):
        g = make_guardian()
        # Fire 50% first
        g.check_token_warning(150_000)
        # 210_000 * 3.5 = 735_000 → 73.5%
        w = g.check_token_warning(210_000)
        assert w is not None
        assert w.threshold == 0.70

    def test_crossing_90_percent(self):
        g = make_guardian()
        g.check_token_warning(150_000)
        g.check_token_warning(210_000)
        # 270_000 * 3.5 = 945_000 → 94.5%
        w = g.check_token_warning(270_000)
        assert w is not None
        assert w.threshold == 0.90

    def test_same_threshold_not_fired_twice(self):
        g = make_guardian()
        w1 = g.check_token_warning(150_000)
        assert w1 is not None
        # Same tokens again — 50% already fired, 70% not reached
        w2 = g.check_token_warning(150_000)
        assert w2 is None

    def test_progressive_thresholds(self):
        g = make_guardian()
        w1 = g.check_token_warning(150_000)
        assert w1.threshold == 0.50
        w2 = g.check_token_warning(210_000)
        assert w2.threshold == 0.70

    def test_exact_boundary_50_percent(self):
        """tokens * 3.5 / 1_000_000 >= 0.50 → tokens >= 142_857.14..."""
        g = make_guardian()
        # Just below: 142_857 * 3.5 = 499_999.5 → 49.99995% < 50%
        assert g.check_token_warning(142_857) is None
        # At boundary: 142_858 * 3.5 = 500_003 → 50.0003% >= 50%
        w = g.check_token_warning(142_858)
        assert w is not None
        assert w.threshold == 0.50

    def test_message_includes_estimated_tokens(self):
        g = make_guardian()
        w = g.check_token_warning(150_000)
        assert "150,000" in w.message


# ---------------------------------------------------------------------------
# observe_user_message
# ---------------------------------------------------------------------------

class TestObserveUserMessage:
    def test_stores_topic(self):
        g = make_guardian()
        g.observe_user_message("Fix the login bug")
        assert len(g._session_topics) == 1
        assert "Fix the login bug" in g._session_topics[0]

    def test_caps_at_50_topics(self):
        g = make_guardian()
        for i in range(60):
            g.observe_user_message(f"Topic {i}")
        assert len(g._session_topics) == 50

    def test_empty_message_not_stored(self):
        g = make_guardian()
        g.observe_user_message("")
        assert len(g._session_topics) == 0


# ---------------------------------------------------------------------------
# observe_event
# ---------------------------------------------------------------------------

class TestObserveEvent:
    def test_edit_tracks_file(self):
        g = make_guardian()
        g.observe_event("Edit", "edited file", {
            "tool_input": {"file_path": "/src/app.py"},
        })
        assert "/src/app.py" in g._files_mentioned

    def test_write_tracks_file(self):
        g = make_guardian()
        g.observe_event("Write", "wrote file", {
            "tool_input": {"file_path": "/src/new.py"},
        })
        assert "/src/new.py" in g._files_mentioned

    def test_agent_tracks_key_event(self):
        g = make_guardian()
        g.observe_event("Agent", "spawned agent", {
            "tool_input": {"description": "Research the codebase"},
        })
        assert len(g._key_events) == 1
        assert "Agent:" in g._key_events[0]

    def test_bash_test_tracks_key_event(self):
        g = make_guardian()
        g.observe_event("Bash", "ran tests", {
            "tool_input": {"command": "pytest test_app.py"},
        })
        assert len(g._key_events) == 1
        assert "Bash:" in g._key_events[0]

    def test_key_events_capped_at_30(self):
        g = make_guardian()
        for i in range(35):
            g.observe_event("Agent", f"task {i}", {
                "tool_input": {"description": f"Agent task {i}"},
            })
        assert len(g._key_events) == 30


# ---------------------------------------------------------------------------
# should_write_summary
# ---------------------------------------------------------------------------

class TestShouldWriteSummary:
    def test_true_when_enough_time_passed(self):
        g = make_guardian()
        g._last_summary_write = time.time() - 120  # 2 minutes ago
        assert g.should_write_summary() is True

    def test_false_when_too_soon(self):
        g = make_guardian()
        g._last_summary_write = time.time()
        assert g.should_write_summary() is False


# ---------------------------------------------------------------------------
# build_context_export
# ---------------------------------------------------------------------------

class TestBuildContextExport:
    def test_contains_header_and_footer(self):
        g = make_guardian()
        text = g.build_context_export(MockStats())
        assert "--- CONTEXT FROM" in text
        assert "--- END CONTEXT ---" in text

    def test_includes_buddy_info(self):
        g = make_guardian()
        buddy = MockBuddy()
        text = g.build_context_export(MockStats(), buddy_state=buddy)
        assert "TestBuddy" in text
        assert "duck" in text

    def test_includes_topics_and_files(self):
        g = make_guardian()
        g.observe_user_message("Add new species")
        g.observe_event("Edit", "edited", {
            "tool_input": {"file_path": "/src/species.py"},
        })
        stats = MockStats(files_touched={"/src/app.py"})
        text = g.build_context_export(stats)
        assert "Add new species" in text
        assert "species.py" in text


# ---------------------------------------------------------------------------
# write methods (file I/O)
# ---------------------------------------------------------------------------

class TestWriteMethods:
    def test_write_rolling_summary_creates_file(self, tmp_path, monkeypatch):
        # Redirect get_data_dir to tmp_path
        monkeypatch.setattr(
            "buddies.core.token_guardian.get_data_dir", lambda: tmp_path
        )
        g = make_guardian(tmp_path)
        path = g.write_rolling_summary(MockStats())
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Rolling Session Summary" in content

    def test_write_session_handoff_creates_file(self, tmp_path):
        g = make_guardian(tmp_path)
        path = g.write_session_handoff(MockStats())
        assert path is not None
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Buddy Session State" in content
        # Verify it landed in .claude/rules/
        assert ".claude" in str(path)
        assert "rules" in str(path)
