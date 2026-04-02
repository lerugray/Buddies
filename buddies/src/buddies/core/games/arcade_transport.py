"""Arcade GitHub Transport — shared multiplayer via GitHub Issues.

Maps arcade challenges and leaderboard entries to GitHub Issues on the
buddies-bbs repo, using labels to distinguish from BBS/MUD data:
  - Challenges → Issues with label "arcade-challenge"
  - Leaderboard → Comments on a pinned "arcade-leaderboard" issue

Read-only without a GitHub PAT. Full write with token.
Falls back gracefully to local-only when offline.

Uses the same repo as BBS and MUD (lerugray/buddies-bbs).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from buddies.config import BBSConfig
from buddies.core.games.arcade_multiplayer import (
    Challenge,
    ChallengeResponse,
    LeaderboardEntry,
    ArcadeMultiplayerStore,
    extract_score_value,
)

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_ENTRIES = 50


@dataclass
class _CacheEntry:
    data: object
    expires: float


class ArcadeTransport:
    """Syncs arcade multiplayer data with GitHub Issues.

    Works alongside ArcadeMultiplayerStore — local store is the source
    of truth, transport syncs outbound (push challenges) and inbound
    (fetch others' challenges and leaderboard).

    Design principles (same as MudTransport):
    - Never block gameplay on network
    - Local store always works offline
    - Merge, don't replace
    - Rate-limit aware
    - Read without token, write with token
    """

    LABEL_CHALLENGE = "arcade-challenge"
    LABEL_LEADERBOARD = "arcade-leaderboard"

    def __init__(self, config: BBSConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None
        self._write_available: bool | None = None
        self._cache: dict[str, _CacheEntry] = {}
        self._rate_limit_remaining: int = 999
        self._rate_limit_reset: float = 0.0
        self._pushed_challenge_ids: set[str] = set()

    async def connect(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.config.github_token:
            headers["Authorization"] = f"Bearer {self.config.github_token}"
        self._client = httpx.AsyncClient(timeout=30.0, headers=headers)

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{self.config.default_repo}"
            )
            self._available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False
        return self._available

    async def can_write(self) -> bool:
        if self._write_available is not None:
            return self._write_available
        if not self.config.github_token:
            self._write_available = False
            return False
        try:
            resp = await self._client.get(f"{GITHUB_API}/user")
            self._write_available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._write_available = False
        return self._write_available

    def _update_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self._rate_limit_remaining = int(remaining)
        if reset is not None:
            self._rate_limit_reset = float(reset)

    def _check_rate_limit(self) -> bool:
        if self._rate_limit_remaining <= 5:
            if time.time() < self._rate_limit_reset:
                log.warning("Arcade transport: rate limited, backing off")
                return False
        return True

    def _cache_get(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() < entry.expires:
            return entry.data
        return None

    def _cache_set(self, key: str, data: object):
        now = time.time()
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            self._cache = {k: v for k, v in self._cache.items() if v.expires > now}
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].expires)
            del self._cache[oldest_key]
        self._cache[key] = _CacheEntry(data=data, expires=now + CACHE_TTL)

    # ── Push: Local → GitHub ──

    async def push_challenge(self, challenge: Challenge) -> bool:
        """Push a local challenge to GitHub as an Issue."""
        if challenge.id in self._pushed_challenge_ids:
            return False
        if not await self.can_write() or not self._check_rate_limit():
            return False

        repo = self.config.default_repo
        game_name = challenge.game_type.upper()
        title = (
            f"🎮 {challenge.challenger_emoji} {challenge.challenger_name} "
            f"challenges you at {game_name}! (Score: {challenge.challenger_score_value})"
        )
        body = _build_challenge_body(challenge)

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues",
                json={
                    "title": title,
                    "body": body,
                    "labels": [self.LABEL_CHALLENGE],
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code == 201:
                issue_data = resp.json()
                challenge.remote_issue_id = issue_data.get("number")
                self._pushed_challenge_ids.add(challenge.id)
                log.info("Arcade transport: pushed challenge %s", challenge.id)
                return True
        except Exception as e:
            log.warning("Arcade transport: failed to push challenge: %s", e)
        return False

    async def push_response(
        self, challenge: Challenge, response: ChallengeResponse,
    ) -> bool:
        """Push a challenge response as a comment on the challenge Issue."""
        if not challenge.remote_issue_id:
            return False
        if not await self.can_write() or not self._check_rate_limit():
            return False

        repo = self.config.default_repo
        won = response.responder_score_value > challenge.challenger_score_value
        result_emoji = "🏆" if won else "😤"
        body = _build_response_body(response, challenge, won)

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues/{challenge.remote_issue_id}/comments",
                json={"body": body},
            )
            self._update_rate_limit(resp)
            if resp.status_code == 201:
                log.info("Arcade transport: pushed response to challenge %s", challenge.id)
                return True
        except Exception as e:
            log.warning("Arcade transport: failed to push response: %s", e)
        return False

    # ── Pull: GitHub → Local ──

    async def fetch_challenges(
        self, game_type: str | None = None,
    ) -> list[Challenge]:
        """Fetch remote challenges."""
        cache_key = f"arcade_challenges:{game_type or 'all'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not await self.is_available() or not self._check_rate_limit():
            return []

        repo = self.config.default_repo
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/issues",
                params={
                    "labels": self.LABEL_CHALLENGE,
                    "state": "open",
                    "per_page": 30,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            challenges = []
            for issue in resp.json():
                if "pull_request" in issue:
                    continue
                challenge = _parse_challenge_issue(issue)
                if challenge:
                    if game_type and challenge.game_type != game_type:
                        continue
                    challenges.append(challenge)

            self._cache_set(cache_key, challenges)
            return challenges
        except Exception as e:
            log.warning("Arcade transport: failed to fetch challenges: %s", e)
            return []

    # ── Sync ──

    async def sync_to_local(self, store: ArcadeMultiplayerStore) -> dict[str, int]:
        """Pull remote challenges and merge into local store."""
        counts = {"challenges": 0}

        remote = await self.fetch_challenges()
        local_ids = {c.id for c in store.challenges}

        for challenge in remote:
            if challenge.id not in local_ids:
                store.challenges.append(challenge)
                counts["challenges"] += 1

        if counts["challenges"] > 0:
            store.save()
            log.info("Arcade transport: synced %d challenges", counts["challenges"])

        return counts

    async def push_local(self, store: ArcadeMultiplayerStore) -> dict[str, int]:
        """Push un-synced local challenges to GitHub."""
        counts = {"challenges": 0}
        for challenge in store.challenges:
            if await self.push_challenge(challenge):
                counts["challenges"] += 1
        if counts["challenges"] > 0:
            store.save()  # Save updated remote_issue_ids
        return counts


# ---------------------------------------------------------------------------
# Issue body builders
# ---------------------------------------------------------------------------

def _build_challenge_body(challenge: Challenge) -> str:
    """Build a GitHub Issue body for an arcade challenge."""
    import json
    score_json = json.dumps(challenge.challenger_score)
    return (
        f"---\n"
        f"type: arcade-challenge\n"
        f"challenge_id: {challenge.id}\n"
        f"game_type: {challenge.game_type}\n"
        f"seed: {challenge.seed}\n"
        f"challenger_name: {challenge.challenger_name}\n"
        f"challenger_species: {challenge.challenger_species}\n"
        f"challenger_emoji: {challenge.challenger_emoji}\n"
        f"challenger_score_value: {challenge.challenger_score_value}\n"
        f"created_at: {challenge.created_at}\n"
        f"---\n\n"
        f"🎮 **{challenge.challenger_emoji} {challenge.challenger_name}** "
        f"({challenge.challenger_species}) challenges you!\n\n"
        f"**Game:** {challenge.game_type.upper()}\n"
        f"**Score:** {challenge.challenger_score_value}\n"
        f"**Seed:** `{challenge.seed}`\n\n"
        f"<details><summary>Full score data</summary>\n\n"
        f"```json\n{score_json}\n```\n</details>\n\n"
        f"Accept this challenge by playing the same game with seed `{challenge.seed}` "
        f"and posting your result!"
    )


def _build_response_body(
    response: ChallengeResponse, challenge: Challenge, won: bool,
) -> str:
    """Build a comment body for a challenge response."""
    import json
    result = "🏆 **WON**" if won else "😤 **Lost**"
    score_json = json.dumps(response.responder_score)
    return (
        f"---\n"
        f"type: arcade-response\n"
        f"responder_name: {response.responder_name}\n"
        f"responder_species: {response.responder_species}\n"
        f"responder_emoji: {response.responder_emoji}\n"
        f"responder_score_value: {response.responder_score_value}\n"
        f"---\n\n"
        f"{result} — **{response.responder_emoji} {response.responder_name}** "
        f"scored **{response.responder_score_value}** "
        f"(vs challenger's {challenge.challenger_score_value})\n\n"
        f"<details><summary>Full score data</summary>\n\n"
        f"```json\n{score_json}\n```\n</details>"
    )


# ---------------------------------------------------------------------------
# Issue parsers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML-like frontmatter from issue body."""
    if not text or not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return {}
    meta = {}
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _sanitize_challenge_frontmatter(meta: dict) -> dict:
    """Validate and sanitize challenge frontmatter."""
    import re
    ALLOWED_KEYS = {
        "type", "challenge_id", "game_type", "seed",
        "challenger_name", "challenger_species", "challenger_emoji",
        "challenger_score_value", "created_at",
    }
    cleaned = {}
    for key, value in meta.items():
        if key not in ALLOWED_KEYS:
            continue
        value = str(value).strip()
        if key == "challenger_score_value":
            try:
                cleaned[key] = str(max(0, min(999999, int(value))))
            except (ValueError, TypeError):
                cleaned[key] = "0"
        elif key == "created_at":
            try:
                ts = float(value)
                min_ts = 1704067200.0  # 2024-01-01 UTC
                max_ts = time.time() + 86400
                cleaned[key] = str(max(min_ts, min(max_ts, ts)))
            except (ValueError, TypeError):
                cleaned[key] = str(time.time())
        elif key in ("challenger_name", "challenger_species", "challenge_id", "seed"):
            cleaned[key] = value[:50]
        elif key == "challenger_emoji":
            cleaned[key] = value[:10]
        elif key == "game_type":
            cleaned[key] = re.sub(r"[^a-zA-Z0-9_]", "", value)[:30]
        elif key == "type":
            cleaned[key] = value[:30]
        else:
            cleaned[key] = value[:50]
    return cleaned


def _parse_challenge_issue(issue: dict) -> Challenge | None:
    """Parse a GitHub Issue into a Challenge."""
    body = (issue.get("body", "") or "")[:2000]
    meta = _parse_frontmatter(body)
    meta = _sanitize_challenge_frontmatter(meta)

    if meta.get("type") != "arcade-challenge":
        return None

    try:
        return Challenge(
            id=meta.get("challenge_id", f"remote_{issue['number']}"),
            game_type=meta.get("game_type", ""),
            seed=meta.get("seed", ""),
            challenger_name=meta.get("challenger_name", "Unknown"),
            challenger_species=meta.get("challenger_species", "unknown"),
            challenger_emoji=meta.get("challenger_emoji", "🎮"),
            challenger_score={},  # Full score not in frontmatter
            challenger_score_value=int(meta.get("challenger_score_value", 0)),
            status="open",
            created_at=float(meta.get("created_at", time.time())),
            remote_issue_id=issue.get("number"),
        )
    except (ValueError, KeyError) as e:
        log.warning("Arcade transport: failed to parse challenge issue: %s", e)
        return None
