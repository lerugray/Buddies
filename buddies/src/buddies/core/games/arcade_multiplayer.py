"""Arcade Multiplayer — challenges, leaderboards, and shared scores.

Local-first storage for arcade challenges and high scores.
GitHub Issues sync handled by ArcadeTransport (separate module).

Game categorization:
- CHALLENGEABLE: Trivia, StackWars (seeded RNG, same game, compare scores)
- LEADERBOARD: Snake, Ski Free, Deckbuilder, Hold'em, Whist (post high scores)
- EXCLUDED: Pong (real-time), MUD (own multiplayer), Crawl, Fusion
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from buddies.config import get_data_dir
from buddies.core.games import GameType

log = logging.getLogger(__name__)

# Games that support direct seeded challenges (same seed = same game)
CHALLENGEABLE_GAMES = {GameType.TRIVIA, GameType.STACKWARS}

# Games that support leaderboard score posting
LEADERBOARD_GAMES = {
    GameType.TRIVIA, GameType.STACKWARS,
    GameType.SNAKE, GameType.SKIFREE, GameType.DECKBUILDER,
    GameType.HOLDEM, GameType.WHIST,
}


@dataclass
class Challenge:
    """A multiplayer challenge — one player posts a score, others try to beat it."""

    id: str
    game_type: str                # GameType.value
    seed: str                     # For seeded games (trivia question set, etc.)
    challenger_name: str
    challenger_species: str
    challenger_emoji: str
    challenger_score: dict        # Game-specific score dict
    challenger_score_value: int   # Single int for comparison (e.g., trivia correct count)
    status: str = "open"          # "open", "completed"
    created_at: float = field(default_factory=time.time)
    responses: list[ChallengeResponse] = field(default_factory=list)
    remote_issue_id: int | None = None

    @staticmethod
    def new_id() -> str:
        return f"ch_{uuid.uuid4().hex[:12]}"


@dataclass
class ChallengeResponse:
    """A response to a challenge — someone accepted and played."""

    responder_name: str
    responder_species: str
    responder_emoji: str
    responder_score: dict
    responder_score_value: int
    timestamp: float = field(default_factory=time.time)

    @property
    def is_winner(self) -> bool:
        """Did this response beat the original challenge?"""
        # Stored on the Challenge, checked externally
        return False  # Comparison done at lookup time


@dataclass
class LeaderboardEntry:
    """A single high score on the global leaderboard."""

    game_type: str           # GameType.value
    buddy_name: str
    buddy_species: str
    buddy_emoji: str
    score: dict              # Full game-specific score
    score_value: int         # Single int for ranking
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Score extraction — pull a single comparable int from game result scores
# ---------------------------------------------------------------------------

def extract_score_value(game_type: str, score: dict) -> int:
    """Extract a single integer score value for ranking/comparison.

    Each game type has its own scoring logic.
    """
    gt = game_type.lower()
    if gt == "trivia":
        return score.get("player", 0)
    elif gt == "snake":
        return score.get("score", 0)
    elif gt == "skifree":
        return score.get("distance", 0)
    elif gt == "deckbuilder":
        # Survived sprints * 100 + remaining stability
        sprints = score.get("sprints_survived", 0)
        stability = score.get("stability", 0)
        return sprints * 100 + stability
    elif gt == "holdem":
        return score.get("chips", 0)
    elif gt == "whist":
        return score.get("tricks_won", 0)
    elif gt == "stackwars":
        return score.get("score", score.get("territories", 0))
    return 0


# ---------------------------------------------------------------------------
# Local store — JSON file for challenges and leaderboard
# ---------------------------------------------------------------------------

class ArcadeMultiplayerStore:
    """Local JSON storage for arcade multiplayer data.

    Follows same pattern as MudMultiplayerStore — local is source of truth,
    transport syncs to/from GitHub.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_data_dir()
        self.store_path = self.data_dir / "arcade_multiplayer.json"
        self.challenges: list[Challenge] = []
        self.leaderboard: list[LeaderboardEntry] = []
        self.load()

    def load(self):
        """Load from JSON file."""
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            self.challenges = [
                Challenge(
                    id=c["id"],
                    game_type=c["game_type"],
                    seed=c.get("seed", ""),
                    challenger_name=c["challenger_name"],
                    challenger_species=c["challenger_species"],
                    challenger_emoji=c.get("challenger_emoji", "🎮"),
                    challenger_score=c.get("challenger_score", {}),
                    challenger_score_value=c.get("challenger_score_value", 0),
                    status=c.get("status", "open"),
                    created_at=c.get("created_at", 0),
                    responses=[
                        ChallengeResponse(
                            responder_name=r["responder_name"],
                            responder_species=r["responder_species"],
                            responder_emoji=r.get("responder_emoji", "🎮"),
                            responder_score=r.get("responder_score", {}),
                            responder_score_value=r.get("responder_score_value", 0),
                            timestamp=r.get("timestamp", 0),
                        )
                        for r in c.get("responses", [])
                    ],
                    remote_issue_id=c.get("remote_issue_id"),
                )
                for c in data.get("challenges", [])
            ]
            self.leaderboard = [
                LeaderboardEntry(
                    game_type=e["game_type"],
                    buddy_name=e["buddy_name"],
                    buddy_species=e["buddy_species"],
                    buddy_emoji=e.get("buddy_emoji", "🎮"),
                    score=e.get("score", {}),
                    score_value=e.get("score_value", 0),
                    timestamp=e.get("timestamp", 0),
                )
                for e in data.get("leaderboard", [])
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Failed to load arcade multiplayer data: %s", e)

    def save(self):
        """Persist to JSON file."""
        data = {
            "challenges": [
                {
                    "id": c.id,
                    "game_type": c.game_type,
                    "seed": c.seed,
                    "challenger_name": c.challenger_name,
                    "challenger_species": c.challenger_species,
                    "challenger_emoji": c.challenger_emoji,
                    "challenger_score": c.challenger_score,
                    "challenger_score_value": c.challenger_score_value,
                    "status": c.status,
                    "created_at": c.created_at,
                    "responses": [
                        {
                            "responder_name": r.responder_name,
                            "responder_species": r.responder_species,
                            "responder_emoji": r.responder_emoji,
                            "responder_score": r.responder_score,
                            "responder_score_value": r.responder_score_value,
                            "timestamp": r.timestamp,
                        }
                        for r in c.responses
                    ],
                    "remote_issue_id": c.remote_issue_id,
                }
                for c in self.challenges
            ],
            "leaderboard": [
                {
                    "game_type": e.game_type,
                    "buddy_name": e.buddy_name,
                    "buddy_species": e.buddy_species,
                    "buddy_emoji": e.buddy_emoji,
                    "score": e.score,
                    "score_value": e.score_value,
                    "timestamp": e.timestamp,
                }
                for e in self.leaderboard
            ],
        }
        self.store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_challenge(
        self,
        game_type: str,
        seed: str,
        buddy_name: str,
        buddy_species: str,
        buddy_emoji: str,
        score: dict,
    ) -> Challenge:
        """Create a new challenge from a game result."""
        challenge = Challenge(
            id=Challenge.new_id(),
            game_type=game_type,
            seed=seed,
            challenger_name=buddy_name,
            challenger_species=buddy_species,
            challenger_emoji=buddy_emoji,
            challenger_score=score,
            challenger_score_value=extract_score_value(game_type, score),
        )
        self.challenges.append(challenge)
        # Cap at 100 challenges
        if len(self.challenges) > 100:
            self.challenges = self.challenges[-100:]
        self.save()
        return challenge

    def respond_to_challenge(
        self,
        challenge_id: str,
        responder_name: str,
        responder_species: str,
        responder_emoji: str,
        score: dict,
    ) -> ChallengeResponse | None:
        """Add a response to an existing challenge."""
        challenge = next((c for c in self.challenges if c.id == challenge_id), None)
        if not challenge:
            return None
        response = ChallengeResponse(
            responder_name=responder_name,
            responder_species=responder_species,
            responder_emoji=responder_emoji,
            responder_score=score,
            responder_score_value=extract_score_value(challenge.game_type, score),
        )
        challenge.responses.append(response)
        challenge.status = "completed"
        self.save()
        return response

    def get_open_challenges(self, game_type: str | None = None) -> list[Challenge]:
        """Get open (unanswered) challenges, optionally filtered by game type."""
        results = [c for c in self.challenges if c.status == "open"]
        if game_type:
            results = [c for c in results if c.game_type == game_type]
        return sorted(results, key=lambda c: c.created_at, reverse=True)

    def add_leaderboard_entry(
        self,
        game_type: str,
        buddy_name: str,
        buddy_species: str,
        buddy_emoji: str,
        score: dict,
    ) -> LeaderboardEntry:
        """Add a score to the leaderboard."""
        entry = LeaderboardEntry(
            game_type=game_type,
            buddy_name=buddy_name,
            buddy_species=buddy_species,
            buddy_emoji=buddy_emoji,
            score=score,
            score_value=extract_score_value(game_type, score),
        )
        self.leaderboard.append(entry)
        # Cap at 500 entries
        if len(self.leaderboard) > 500:
            self.leaderboard = self.leaderboard[-500:]
        self.save()
        return entry

    def get_leaderboard(
        self, game_type: str | None = None, limit: int = 10,
    ) -> list[LeaderboardEntry]:
        """Get top scores, optionally filtered by game type."""
        entries = self.leaderboard
        if game_type:
            entries = [e for e in entries if e.game_type == game_type]
        return sorted(entries, key=lambda e: e.score_value, reverse=True)[:limit]

    def get_personal_bests(self, buddy_name: str) -> dict[str, LeaderboardEntry]:
        """Get this buddy's best score per game type."""
        bests: dict[str, LeaderboardEntry] = {}
        for entry in self.leaderboard:
            if entry.buddy_name == buddy_name:
                existing = bests.get(entry.game_type)
                if not existing or entry.score_value > existing.score_value:
                    bests[entry.game_type] = entry
        return bests

    @property
    def challenge_count(self) -> int:
        return len(self.challenges)

    @property
    def total_scores(self) -> int:
        return len(self.leaderboard)
