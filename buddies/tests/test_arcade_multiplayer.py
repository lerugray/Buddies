"""Tests for arcade multiplayer data models and local store.

Tests challenge creation, response handling, leaderboard entries,
score extraction, and local JSON persistence.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from buddies.core.games.arcade_multiplayer import (
    Challenge,
    ChallengeResponse,
    LeaderboardEntry,
    ArcadeMultiplayerStore,
    extract_score_value,
    CHALLENGEABLE_GAMES,
    LEADERBOARD_GAMES,
)
from buddies.core.games import GameType


# ---------------------------------------------------------------------------
# Score extraction
# ---------------------------------------------------------------------------

class TestScoreExtraction:
    def test_trivia_score(self):
        assert extract_score_value("trivia", {"player": 8, "buddy": 5}) == 8

    def test_snake_score(self):
        assert extract_score_value("snake", {"score": 750}) == 750

    def test_skifree_score(self):
        assert extract_score_value("skifree", {"distance": 2500}) == 2500

    def test_deckbuilder_score(self):
        # 5 sprints * 100 + 6 stability = 506
        score = extract_score_value("deckbuilder", {"sprints_survived": 5, "stability": 6})
        assert score == 506

    def test_holdem_score(self):
        assert extract_score_value("holdem", {"chips": 1200}) == 1200

    def test_whist_score(self):
        assert extract_score_value("whist", {"tricks_won": 9}) == 9

    def test_stackwars_score(self):
        assert extract_score_value("stackwars", {"score": 42}) == 42

    def test_unknown_game(self):
        assert extract_score_value("unknown", {"whatever": 99}) == 0

    def test_missing_keys(self):
        assert extract_score_value("trivia", {}) == 0
        assert extract_score_value("snake", {}) == 0


# ---------------------------------------------------------------------------
# Game categorization
# ---------------------------------------------------------------------------

class TestGameCategories:
    def test_challengeable_games(self):
        assert GameType.TRIVIA in CHALLENGEABLE_GAMES
        assert GameType.STACKWARS in CHALLENGEABLE_GAMES
        assert GameType.PONG not in CHALLENGEABLE_GAMES
        assert GameType.MUD not in CHALLENGEABLE_GAMES

    def test_leaderboard_games(self):
        assert GameType.SNAKE in LEADERBOARD_GAMES
        assert GameType.SKIFREE in LEADERBOARD_GAMES
        assert GameType.TRIVIA in LEADERBOARD_GAMES
        assert GameType.PONG not in LEADERBOARD_GAMES
        assert GameType.CRAWL not in LEADERBOARD_GAMES


# ---------------------------------------------------------------------------
# Challenge dataclass
# ---------------------------------------------------------------------------

class TestChallenge:
    def test_new_id_unique(self):
        id1 = Challenge.new_id()
        id2 = Challenge.new_id()
        assert id1 != id2
        assert id1.startswith("ch_")

    def test_challenge_creation(self):
        ch = Challenge(
            id="ch_test123",
            game_type="trivia",
            seed="seed_abc",
            challenger_name="TestBuddy",
            challenger_species="duck",
            challenger_emoji="🦆",
            challenger_score={"player": 8},
            challenger_score_value=8,
        )
        assert ch.status == "open"
        assert ch.responses == []
        assert ch.remote_issue_id is None


# ---------------------------------------------------------------------------
# Local store
# ---------------------------------------------------------------------------

class TestArcadeMultiplayerStore:
    def _make_store(self, tmp_path: Path) -> ArcadeMultiplayerStore:
        return ArcadeMultiplayerStore(data_dir=tmp_path)

    def test_create_challenge(self, tmp_path):
        store = self._make_store(tmp_path)
        ch = store.create_challenge(
            game_type="trivia",
            seed="test_seed",
            buddy_name="Quackers",
            buddy_species="duck",
            buddy_emoji="🦆",
            score={"player": 7},
        )
        assert ch.id.startswith("ch_")
        assert ch.challenger_score_value == 7
        assert ch.status == "open"
        assert store.challenge_count == 1

    def test_respond_to_challenge(self, tmp_path):
        store = self._make_store(tmp_path)
        ch = store.create_challenge(
            game_type="trivia", seed="s1",
            buddy_name="A", buddy_species="duck", buddy_emoji="🦆",
            score={"player": 5},
        )
        resp = store.respond_to_challenge(
            challenge_id=ch.id,
            responder_name="B",
            responder_species="cat",
            responder_emoji="🐱",
            score={"player": 8},
        )
        assert resp is not None
        assert resp.responder_score_value == 8
        assert ch.status == "completed"

    def test_respond_nonexistent(self, tmp_path):
        store = self._make_store(tmp_path)
        resp = store.respond_to_challenge(
            challenge_id="fake_id",
            responder_name="B", responder_species="cat", responder_emoji="🐱",
            score={"player": 1},
        )
        assert resp is None

    def test_get_open_challenges(self, tmp_path):
        store = self._make_store(tmp_path)
        store.create_challenge(
            game_type="trivia", seed="s1",
            buddy_name="A", buddy_species="duck", buddy_emoji="🦆",
            score={"player": 5},
        )
        store.create_challenge(
            game_type="snake", seed="s2",
            buddy_name="B", buddy_species="cat", buddy_emoji="🐱",
            score={"score": 300},
        )
        assert len(store.get_open_challenges()) == 2
        assert len(store.get_open_challenges("trivia")) == 1
        assert len(store.get_open_challenges("pong")) == 0

    def test_leaderboard_entry(self, tmp_path):
        store = self._make_store(tmp_path)
        entry = store.add_leaderboard_entry(
            game_type="snake",
            buddy_name="Speedster",
            buddy_species="cat",
            buddy_emoji="🐱",
            score={"score": 999},
        )
        assert entry.score_value == 999
        assert store.total_scores == 1

    def test_leaderboard_sorting(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add_leaderboard_entry("snake", "A", "duck", "🦆", {"score": 100})
        store.add_leaderboard_entry("snake", "B", "cat", "🐱", {"score": 500})
        store.add_leaderboard_entry("snake", "C", "owl", "🦉", {"score": 300})

        top = store.get_leaderboard("snake", limit=2)
        assert len(top) == 2
        assert top[0].buddy_name == "B"
        assert top[1].buddy_name == "C"

    def test_personal_bests(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add_leaderboard_entry("snake", "A", "duck", "🦆", {"score": 100})
        store.add_leaderboard_entry("snake", "A", "duck", "🦆", {"score": 500})
        store.add_leaderboard_entry("trivia", "A", "duck", "🦆", {"player": 7})

        bests = store.get_personal_bests("A")
        assert "snake" in bests
        assert bests["snake"].score_value == 500
        assert "trivia" in bests

    def test_persistence_roundtrip(self, tmp_path):
        store1 = self._make_store(tmp_path)
        store1.create_challenge(
            game_type="trivia", seed="persist_test",
            buddy_name="A", buddy_species="duck", buddy_emoji="🦆",
            score={"player": 9},
        )
        store1.add_leaderboard_entry("snake", "B", "cat", "🐱", {"score": 777})

        # Load fresh
        store2 = self._make_store(tmp_path)
        assert store2.challenge_count == 1
        assert store2.challenges[0].seed == "persist_test"
        assert store2.total_scores == 1
        assert store2.leaderboard[0].score_value == 777

    def test_challenge_cap(self, tmp_path):
        store = self._make_store(tmp_path)
        for i in range(110):
            store.create_challenge(
                game_type="trivia", seed=f"s{i}",
                buddy_name="A", buddy_species="duck", buddy_emoji="🦆",
                score={"player": i},
            )
        assert store.challenge_count <= 100

    def test_leaderboard_cap(self, tmp_path):
        store = self._make_store(tmp_path)
        for i in range(510):
            store.add_leaderboard_entry("snake", "A", "duck", "🦆", {"score": i})
        assert store.total_scores <= 500
