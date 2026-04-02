"""Tests for arcade GitHub transport — challenge/leaderboard sync.

Tests data formatting, parsing, and frontmatter roundtrips.
Does NOT hit the real GitHub API.
"""

import time
import pytest

from buddies.core.games.arcade_multiplayer import Challenge, ChallengeResponse
from buddies.core.games.arcade_transport import (
    ArcadeTransport,
    _build_challenge_body,
    _build_response_body,
    _parse_challenge_issue,
    _parse_frontmatter,
    _sanitize_challenge_frontmatter,
)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class TestFrontmatter:
    def test_parse_valid(self):
        text = "---\ntype: arcade-challenge\ngame_type: trivia\n---\n\nBody"
        meta = _parse_frontmatter(text)
        assert meta["type"] == "arcade-challenge"
        assert meta["game_type"] == "trivia"

    def test_parse_empty(self):
        assert _parse_frontmatter("") == {}
        assert _parse_frontmatter("no frontmatter") == {}

    def test_parse_no_closing(self):
        text = "---\nkey: value\nstill going..."
        assert _parse_frontmatter(text) == {}

    def test_parse_colon_in_value(self):
        text = "---\nchallenger_name: Test: The Brave\n---\n"
        meta = _parse_frontmatter(text)
        assert meta["challenger_name"] == "Test: The Brave"


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

class TestSanitization:
    def test_valid_data_passes(self):
        meta = {
            "type": "arcade-challenge",
            "challenge_id": "ch_abc123",
            "game_type": "trivia",
            "seed": "seed_001",
            "challenger_name": "TestBuddy",
            "challenger_score_value": "8",
        }
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert cleaned["type"] == "arcade-challenge"
        assert cleaned["challenger_score_value"] == "8"

    def test_score_clamping(self):
        meta = {"challenger_score_value": "99999999"}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert int(cleaned["challenger_score_value"]) <= 999999

    def test_negative_score(self):
        meta = {"challenger_score_value": "-10"}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert int(cleaned["challenger_score_value"]) >= 0

    def test_invalid_score(self):
        meta = {"challenger_score_value": "not_a_number"}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert cleaned["challenger_score_value"] == "0"

    def test_name_truncation(self):
        meta = {"challenger_name": "A" * 100}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert len(cleaned["challenger_name"]) <= 50

    def test_game_type_sanitized(self):
        meta = {"game_type": "trivia; DROP TABLE"}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert ";" not in cleaned["game_type"]
        assert " " not in cleaned["game_type"]

    def test_unknown_keys_stripped(self):
        meta = {"type": "arcade-challenge", "evil_key": "payload"}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert "evil_key" not in cleaned

    def test_timestamp_bounds(self):
        meta = {"created_at": "0"}  # Way before 2024
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert float(cleaned["created_at"]) >= 1704067200.0  # 2024-01-01

    def test_future_timestamp_capped(self):
        future = str(time.time() + 999999)
        meta = {"created_at": future}
        cleaned = _sanitize_challenge_frontmatter(meta)
        assert float(cleaned["created_at"]) <= time.time() + 86401


# ---------------------------------------------------------------------------
# Challenge body building + parsing roundtrip
# ---------------------------------------------------------------------------

class TestChallengeRoundtrip:
    def _make_challenge(self, **overrides):
        defaults = dict(
            id="ch_test123",
            game_type="trivia",
            seed="seed_abc",
            challenger_name="TestBuddy",
            challenger_species="duck",
            challenger_emoji="🦆",
            challenger_score={"player": 8, "buddy": 5},
            challenger_score_value=8,
            status="open",
            created_at=time.time(),
        )
        defaults.update(overrides)
        return Challenge(**defaults)

    def test_build_body_contains_frontmatter(self):
        ch = self._make_challenge()
        body = _build_challenge_body(ch)
        assert body.startswith("---")
        assert "type: arcade-challenge" in body
        assert "challenge_id: ch_test123" in body
        assert "game_type: trivia" in body
        assert "seed: seed_abc" in body

    def test_roundtrip_parse(self):
        ch = self._make_challenge()
        body = _build_challenge_body(ch)

        issue = {
            "number": 42,
            "body": body,
        }
        parsed = _parse_challenge_issue(issue)
        assert parsed is not None
        assert parsed.id == "ch_test123"
        assert parsed.game_type == "trivia"
        assert parsed.seed == "seed_abc"
        assert parsed.challenger_name == "TestBuddy"
        assert parsed.challenger_score_value == 8
        assert parsed.remote_issue_id == 42

    def test_parse_invalid_type(self):
        issue = {
            "number": 1,
            "body": "---\ntype: not-a-challenge\n---\n",
        }
        assert _parse_challenge_issue(issue) is None

    def test_parse_empty_body(self):
        assert _parse_challenge_issue({"number": 1, "body": ""}) is None
        assert _parse_challenge_issue({"number": 1, "body": None}) is None

    def test_parse_truncates_body(self):
        # Body over 2000 chars should not crash
        long_body = "---\ntype: arcade-challenge\n---\n" + "x" * 3000
        result = _parse_challenge_issue({"number": 1, "body": long_body})
        # Should parse the frontmatter even though body is long
        assert result is not None


# ---------------------------------------------------------------------------
# Response body building
# ---------------------------------------------------------------------------

class TestResponseBody:
    def test_build_win_response(self):
        ch = Challenge(
            id="ch_1", game_type="trivia", seed="s",
            challenger_name="A", challenger_species="duck",
            challenger_emoji="🦆", challenger_score={},
            challenger_score_value=5,
        )
        resp = ChallengeResponse(
            responder_name="B", responder_species="cat",
            responder_emoji="🐱", responder_score={"player": 8},
            responder_score_value=8,
        )
        body = _build_response_body(resp, ch, won=True)
        assert "WON" in body
        assert "B" in body
        assert "8" in body

    def test_build_loss_response(self):
        ch = Challenge(
            id="ch_1", game_type="trivia", seed="s",
            challenger_name="A", challenger_species="duck",
            challenger_emoji="🦆", challenger_score={},
            challenger_score_value=10,
        )
        resp = ChallengeResponse(
            responder_name="B", responder_species="cat",
            responder_emoji="🐱", responder_score={"player": 3},
            responder_score_value=3,
        )
        body = _build_response_body(resp, ch, won=False)
        assert "Lost" in body
