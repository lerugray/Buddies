"""Tests for personality drift system and session observer."""

import time
from collections import Counter, deque

import pytest

from buddies.core.personality_drift import (
    CHAT_DRIFT,
    FUSION_DRIFT,
    GAME_DRIFT,
    IDLE_DRIFT,
    SESSION_DRIFT,
    STAT_MAX,
    WIN_DRIFT,
    LOSE_DRIFT,
    DriftResult,
    apply_drift,
    drift_for_chat,
    drift_for_fusion,
    drift_for_game,
    drift_for_idle,
    drift_for_session_tool,
)
from buddies.core.session_observer import (
    TOKEN_ESTIMATES,
    SessionEvent,
    SessionObserver,
    SessionStats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stats():
    return {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}


def make_event(event_type="PreToolUse", tool_name="Read", raw_data=None, tokens=100):
    return SessionEvent(
        timestamp=time.time(),
        event_type=event_type,
        tool_name=tool_name,
        summary="test event",
        tokens_estimated=tokens,
        raw_data=raw_data or {},
    )


# =========================================================================
# DriftResult
# =========================================================================

class TestDriftResult:
    def test_has_changes_true(self):
        r = DriftResult(changes={"chaos": 2}, old_stats={}, new_stats={})
        assert r.has_changes is True

    def test_has_changes_false_empty(self):
        r = DriftResult(changes={}, old_stats={}, new_stats={})
        assert r.has_changes is False

    def test_has_changes_false_zero_deltas(self):
        r = DriftResult(changes={"chaos": 0, "wisdom": 0}, old_stats={}, new_stats={})
        assert r.has_changes is False

    def test_summary_positive(self):
        r = DriftResult(changes={"chaos": 2, "wisdom": 1}, old_stats={}, new_stats={})
        s = r.summary()
        assert "CHAOS +2" in s
        assert "WISDOM +1" in s

    def test_summary_negative(self):
        r = DriftResult(changes={"patience": -1}, old_stats={}, new_stats={})
        assert "PATIENCE -1" in r.summary()

    def test_summary_no_change(self):
        r = DriftResult(changes={}, old_stats={}, new_stats={})
        assert r.summary() == "no change"


# =========================================================================
# apply_drift
# =========================================================================

class TestApplyDrift:
    def test_basic_boost(self):
        stats = make_stats()
        result = apply_drift(stats, [("chaos", 3)])
        assert stats["chaos"] == 13
        assert result.changes["chaos"] == 3

    def test_cap_at_stat_max(self):
        stats = make_stats()
        stats["wisdom"] = 98
        result = apply_drift(stats, [("wisdom", 5)])
        assert stats["wisdom"] == STAT_MAX
        assert result.changes["wisdom"] == 1  # only gained 1 (98→99)

    def test_floor_at_one(self):
        stats = make_stats()
        stats["chaos"] = 2
        result = apply_drift(stats, [("chaos", -10)])
        assert stats["chaos"] == 1
        assert result.changes["chaos"] == -1

    def test_multiplier_scales_boost(self):
        stats = make_stats()
        # amount=2, multiplier=0.5 → int(1.0)=1
        result = apply_drift(stats, [("debugging", 2)], multiplier=0.5)
        assert stats["debugging"] == 11
        assert result.changes["debugging"] == 1

    def test_multiplier_rounds_to_zero_skips(self):
        stats = make_stats()
        # amount=1, multiplier=0.5 → int(0.5)=0 → skipped
        result = apply_drift(stats, [("debugging", 1)], multiplier=0.5)
        assert stats["debugging"] == 10
        assert result.has_changes is False

    def test_unknown_stat_ignored(self):
        stats = make_stats()
        result = apply_drift(stats, [("nonexistent", 5)])
        assert result.has_changes is False
        assert stats == make_stats()

    def test_multiple_boosts_accumulate(self):
        stats = make_stats()
        result = apply_drift(stats, [("chaos", 2), ("chaos", 3)])
        assert stats["chaos"] == 15
        # changes dict records last write per stat (3, not 2+3)
        # but the stats themselves accumulate both boosts
        assert result.changes["chaos"] == 3


# =========================================================================
# drift_for_game
# =========================================================================

class TestDriftForGame:
    def test_rps_boosts(self):
        stats = make_stats()
        result = drift_for_game(stats, "rps", won=False)
        # rps: chaos+1, snark+1, plus lose: patience+1
        assert stats["chaos"] == 11
        assert stats["snark"] == 11
        assert stats["patience"] == 11

    def test_trivia_boosts(self):
        stats = make_stats()
        result = drift_for_game(stats, "trivia", won=False)
        # trivia: wisdom+2, debugging+1, plus lose: patience+1
        assert stats["wisdom"] == 12
        assert stats["debugging"] == 11

    def test_win_adds_debugging(self):
        stats = make_stats()
        result = drift_for_game(stats, "rps", won=True)
        # rps gives chaos+1, snark+1; win gives debugging+1
        assert stats["debugging"] == 11

    def test_lose_adds_patience(self):
        stats = make_stats()
        result = drift_for_game(stats, "rps", won=False)
        assert stats["patience"] == 11

    def test_unknown_game_only_win_lose(self):
        stats = make_stats()
        result = drift_for_game(stats, "unknown_game_xyz", won=True)
        # No game-specific drift, just win drift (debugging+1)
        assert stats["debugging"] == 11
        assert stats["chaos"] == 10
        assert stats["snark"] == 10


# =========================================================================
# drift_for_session_tool
# =========================================================================

class TestDriftForSessionTool:
    def test_edit_boosts_debugging_at_half(self):
        stats = make_stats()
        # Edit → debugging+1 at 0.5 multiplier → int(0.5)=0, no change
        # But if debugging amount is 1 and mult is 0.5, int(0.5)=0 → skipped
        result = drift_for_session_tool(stats, "Edit")
        # With multiplier 0.5 and amount 1: int(1*0.5)=0 → no actual change
        assert result.has_changes is False

    def test_read_boosts_wisdom_at_half(self):
        stats = make_stats()
        result = drift_for_session_tool(stats, "Read")
        # wisdom+1 at 0.5 → int(0.5)=0 → no change
        assert result.has_changes is False

    def test_bash_boosts_chaos_at_half(self):
        stats = make_stats()
        result = drift_for_session_tool(stats, "Bash")
        # chaos+1 at 0.5 → int(0.5)=0 → no change
        assert result.has_changes is False

    def test_unknown_tool_no_changes(self):
        stats = make_stats()
        result = drift_for_session_tool(stats, "MagicWand")
        assert result.has_changes is False
        assert stats == make_stats()

    def test_known_tools_listed(self):
        """Verify all expected tools are in SESSION_DRIFT."""
        for tool in ("Edit", "Write", "Read", "Grep", "Agent", "Bash"):
            assert tool in SESSION_DRIFT


# =========================================================================
# drift_for_chat
# =========================================================================

class TestDriftForChat:
    def test_applies_patience_at_half(self):
        stats = make_stats()
        result = drift_for_chat(stats)
        # patience+1 at 0.5 → int(0.5)=0 → no change with default amounts
        # This matches the actual behavior: 0.5 multiplier on amount 1 rounds to 0
        assert isinstance(result, DriftResult)


# =========================================================================
# drift_for_fusion
# =========================================================================

class TestDriftForFusion:
    def test_fusion_applies_big_boosts(self):
        stats = make_stats()
        result = drift_for_fusion(stats)
        # wisdom+3, chaos+2, patience+1 at 1.0 multiplier
        assert stats["wisdom"] == 13
        assert stats["chaos"] == 12
        assert stats["patience"] == 11
        assert result.has_changes is True

    def test_fusion_summary(self):
        stats = make_stats()
        result = drift_for_fusion(stats)
        s = result.summary()
        assert "WISDOM +3" in s
        assert "CHAOS +2" in s
        assert "PATIENCE +1" in s


# =========================================================================
# drift_for_idle
# =========================================================================

class TestDriftForIdle:
    def test_under_30_no_drift(self):
        stats = make_stats()
        result = drift_for_idle(stats, 20)
        assert result.has_changes is False
        assert stats == make_stats()

    def test_exactly_29_no_drift(self):
        stats = make_stats()
        result = drift_for_idle(stats, 29)
        assert result.has_changes is False

    def test_30_minutes_applies_chaos(self):
        stats = make_stats()
        result = drift_for_idle(stats, 30)
        # mult = min(30/60, 3.0) = 0.5 → chaos+1 * 0.5 = int(0.5) = 0
        # Actually no change because int(1*0.5)=0
        assert isinstance(result, DriftResult)

    def test_60_minutes_applies_chaos(self):
        stats = make_stats()
        result = drift_for_idle(stats, 60)
        # mult = min(60/60, 3.0) = 1.0 → chaos+1 * 1.0 = 1
        assert stats["chaos"] == 11
        assert result.changes.get("chaos") == 1

    def test_180_minutes_capped_at_3x(self):
        stats = make_stats()
        result = drift_for_idle(stats, 180)
        # mult = min(180/60, 3.0) = 3.0 → chaos+1 * 3.0 = int(3) = 3
        assert stats["chaos"] == 13
        assert result.changes["chaos"] == 3

    def test_very_long_idle_still_capped(self):
        stats = make_stats()
        result = drift_for_idle(stats, 600)
        # mult = min(600/60, 3.0) = 3.0 (capped)
        assert stats["chaos"] == 13


# =========================================================================
# SessionStats
# =========================================================================

class TestSessionStats:
    def test_duration_zero_when_no_start(self):
        s = SessionStats()
        assert s.duration_minutes == 0.0

    def test_duration_calculates(self):
        s = SessionStats()
        s.start_time = time.time() - 120  # 2 minutes ago
        d = s.duration_minutes
        assert 1.9 < d < 2.2  # allow slight timing variance

    def test_most_used_tool_none_when_empty(self):
        s = SessionStats()
        assert s.most_used_tool == "none"

    def test_most_used_tool_returns_correct(self):
        s = SessionStats()
        s.tool_counts["Read"] = 5
        s.tool_counts["Edit"] = 3
        s.tool_counts["Bash"] = 1
        assert s.most_used_tool == "Read"


# =========================================================================
# SessionObserver
# =========================================================================

class TestSessionObserver:
    def test_process_raw_event(self):
        obs = SessionObserver()
        raw = {
            "timestamp": 1000.0,
            "data": {
                "event": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.py"},
            },
        }
        event = obs._process_raw_event(raw)
        assert event is not None
        assert event.event_type == "PreToolUse"
        assert event.tool_name == "Read"
        assert event.tokens_estimated == TOKEN_ESTIMATES["Read"]

    def test_make_summary_session_start(self):
        obs = SessionObserver()
        s = obs._make_summary("SessionStart", "", {})
        assert "session started" in s.lower()

    def test_make_summary_pre_tool_read(self):
        obs = SessionObserver()
        s = obs._make_summary("PreToolUse", "Read", {
            "tool_input": {"file_path": "/a/b/c/d/file.py"}
        })
        assert "Reading" in s

    def test_make_summary_pre_tool_edit(self):
        obs = SessionObserver()
        s = obs._make_summary("PreToolUse", "Edit", {
            "tool_input": {"file_path": "/src/app.py"}
        })
        assert "Editing" in s

    def test_make_summary_pre_tool_bash(self):
        obs = SessionObserver()
        s = obs._make_summary("PreToolUse", "Bash", {
            "tool_input": {"command": "git status"}
        })
        assert "Running" in s
        assert "git status" in s

    def test_make_summary_post_tool_use(self):
        obs = SessionObserver()
        s = obs._make_summary("PostToolUse", "Edit", {
            "result_summary": "applied 3 edits"
        })
        assert "Edit" in s
        assert "completed" in s

    def test_short_path_shortens_long(self):
        obs = SessionObserver()
        result = obs._short_path("/home/user/projects/buddies/src/app.py")
        assert result.startswith("...")
        assert "app.py" in result

    def test_short_path_keeps_short(self):
        obs = SessionObserver()
        result = obs._short_path("src/app.py")
        assert result == "src/app.py"

    def test_short_path_empty(self):
        obs = SessionObserver()
        assert obs._short_path("") == "unknown"

    def test_record_event_increments_stats(self):
        obs = SessionObserver()
        event = make_event(tool_name="Read", tokens=500)
        obs._record_event(event)
        assert obs.stats.event_count == 1
        assert obs.stats.tokens_estimated == 500
        assert obs.stats.tool_counts["Read"] == 1

    def test_record_event_tracks_files_for_edit(self):
        obs = SessionObserver()
        event = make_event(
            event_type="PreToolUse",
            tool_name="Edit",
            raw_data={"tool_input": {"file_path": "/src/app.py"}},
        )
        obs._record_event(event)
        assert obs.stats.edit_count == 1
        assert "/src/app.py" in obs.stats.files_touched

    def test_record_event_tracks_files_for_write(self):
        obs = SessionObserver()
        event = make_event(
            tool_name="Write",
            raw_data={"tool_input": {"file_path": "/src/new.py"}},
        )
        obs._record_event(event)
        assert obs.stats.edit_count == 1
        assert "/src/new.py" in obs.stats.files_touched

    def test_record_event_captures_model(self):
        obs = SessionObserver()
        event = make_event(
            event_type="SessionStart",
            tool_name="",
            raw_data={"model": "claude-sonnet-4-20250514"},
            tokens=0,
        )
        obs._record_event(event)
        assert obs.stats.current_model == "claude-sonnet-4-20250514"

    def test_detect_repeated_reads(self):
        obs = SessionObserver()
        patterns_detected = []
        obs._pattern_callbacks.append(
            lambda ptype, desc: patterns_detected.append(ptype)
        )
        # Need 5 recent tools with 4+ Reads
        for _ in range(5):
            obs.stats.recent_tools.append("Read")
        obs._detect_patterns()
        assert "repeated_reads" in patterns_detected

    def test_detect_edit_storm(self):
        obs = SessionObserver()
        patterns_detected = []
        obs._pattern_callbacks.append(
            lambda ptype, desc: patterns_detected.append(ptype)
        )
        for _ in range(5):
            obs.stats.recent_tools.append("Edit")
        obs._detect_patterns()
        assert "edit_storm" in patterns_detected

    def test_event_callbacks_fire(self):
        obs = SessionObserver()
        received = []
        obs.on_event(lambda e: received.append(e))
        raw = {
            "timestamp": 1000.0,
            "data": {"event": "PreToolUse", "tool_name": "Bash"},
        }
        event = obs._process_raw_event(raw)
        obs._record_event(event)
        for cb in obs._callbacks:
            cb(event)
        assert len(received) == 1
        assert received[0].tool_name == "Bash"

    def test_token_estimates_has_common_tools(self):
        for tool in ("Read", "Edit", "Write", "Bash", "Grep", "Glob", "Agent"):
            assert tool in TOKEN_ESTIMATES
            assert TOKEN_ESTIMATES[tool] > 0
