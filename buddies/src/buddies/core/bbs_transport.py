"""BBS transport layer — GitHub Issues API for post read/write.

Posts = GitHub Issues. Boards = Labels. Replies = Comments.
Read-only without a PAT. Full write access with a token.
Uses httpx (already a project dependency) for all HTTP.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

log = logging.getLogger(__name__)

from buddies.config import BBSConfig
from buddies.core.bbs_profile import BBSProfile


GITHUB_API = "https://api.github.com"

# How old cached data can be before we re-fetch (seconds)
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_ENTRIES = 100  # Evict oldest when exceeded


@dataclass
class RemotePost:
    """A post fetched from GitHub."""
    id: int                # Issue number
    board: str             # Label name (e.g., "CHAOS-LOUNGE")
    title: str
    body: str              # Post content (frontmatter stripped)
    author_meta: dict      # Parsed from YAML frontmatter
    reply_count: int
    reactions: dict        # emoji -> count
    created_at: str
    raw_author: str        # GitHub username who created the issue
    age: str = ""          # Human-readable age


@dataclass
class RemoteReply:
    """A reply fetched from GitHub."""
    id: int                # Comment ID
    post_id: int           # Issue number
    body: str
    author_meta: dict
    created_at: str
    raw_author: str
    age: str = ""


@dataclass
class _CacheEntry:
    """Cached API response with expiry."""
    data: object
    expires: float


class BBSTransport:
    """Handles all communication with GitHub for the BBS."""

    def __init__(self, config: BBSConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None
        self._write_available: bool | None = None
        self._cache: dict[str, _CacheEntry] = {}
        self._rate_limit_remaining: int = 999
        self._rate_limit_reset: float = 0.0
        # Write-side rate limiting (application-level)
        self._posts_today: int = 0
        self._replies_today: int = 0
        self._write_day: str = ""  # Date string for daily reset

    def _update_rate_limit(self, resp: httpx.Response) -> None:
        """Track GitHub API rate limit from response headers."""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self._rate_limit_remaining = int(remaining)
        if reset is not None:
            self._rate_limit_reset = float(reset)
        if self._rate_limit_remaining <= 10:
            log.warning("GitHub API rate limit low: %d remaining", self._rate_limit_remaining)

    def _check_rate_limit(self) -> bool:
        """Return False if we should back off due to rate limiting."""
        if self._rate_limit_remaining <= 5:
            if time.time() < self._rate_limit_reset:
                log.warning("GitHub API rate limited — backing off until reset")
                return False
        return True

    def _cache_get(self, key: str):
        """Return cached value if still valid, else None."""
        entry = self._cache.get(key)
        if entry and time.time() < entry.expires:
            return entry.data
        return None

    def _cache_set(self, key: str, data: object):
        """Store a value in cache with TTL. Evicts expired/oldest entries if full."""
        now = time.time()
        # Prune expired entries first
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            self._cache = {k: v for k, v in self._cache.items() if v.expires > now}
        # If still too large, evict oldest
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].expires)
            del self._cache[oldest_key]
        self._cache[key] = _CacheEntry(data=data, expires=now + CACHE_TTL)

    def invalidate_cache(self, prefix: str = ""):
        """Clear cache entries matching a prefix, or all if empty."""
        if not prefix:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if not k.startswith(prefix)}

    async def connect(self):
        """Initialize the HTTP client."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.config.github_token:
            headers["Authorization"] = f"Bearer {self.config.github_token}"

        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def is_available(self) -> bool:
        """Check if we can reach the BBS repo."""
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
        """Check if we have write access (PAT configured and valid)."""
        if self._write_available is not None:
            return self._write_available
        if not self.config.github_token:
            self._write_available = False
            return False
        # Test write access by checking our auth scopes
        try:
            resp = await self._client.get(f"{GITHUB_API}/user")
            self._write_available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._write_available = False
        return self._write_available

    # ── Read operations ──

    async def list_boards(self, repo: str = "") -> list[str]:
        """Get all labels (boards) from the BBS repo."""
        repo = repo or self.config.default_repo
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/labels",
                params={"per_page": 50},
            )
            if resp.status_code != 200:
                return []
            return [label["name"] for label in resp.json()]
        except Exception as e:
            log.warning("BBS: failed to list boards: %s", e)
            return []

    async def list_posts(
        self, board: str = "", repo: str = "", page: int = 1, per_page: int = 15
    ) -> list[RemotePost]:
        """Get posts (issues) for a board, newest first."""
        repo = repo or self.config.default_repo
        cache_key = f"posts:{repo}:{board}:{page}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self._check_rate_limit():
            return []

        params = {
            "state": "open",
            "sort": "created",
            "direction": "desc",
            "page": page,
            "per_page": per_page,
        }
        if board:
            params["labels"] = board

        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/issues",
                params=params,
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            posts = []
            for issue in resp.json():
                # Skip pull requests (GitHub includes them in /issues)
                if "pull_request" in issue:
                    continue
                posts.append(self._parse_issue(issue, board))
            self._cache_set(cache_key, posts)
            return posts
        except Exception as e:
            log.warning("BBS: failed to list posts for %s: %s", board, e)
            return []

    async def get_post(self, post_id: int, repo: str = "") -> RemotePost | None:
        """Get a single post by issue number."""
        repo = repo or self.config.default_repo
        if not self._check_rate_limit():
            return None
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/issues/{post_id}"
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return None
            issue = resp.json()
            board = ""
            if issue.get("labels"):
                board = issue["labels"][0]["name"]
            return self._parse_issue(issue, board)
        except Exception as e:
            log.warning("BBS: failed to get post %d: %s", post_id, e)
            return None

    async def get_replies(self, post_id: int, repo: str = "") -> list[RemoteReply]:
        """Get replies (comments) for a post."""
        repo = repo or self.config.default_repo
        cache_key = f"replies:{repo}:{post_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self._check_rate_limit():
            return []

        try:
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/issues/{post_id}/comments",
                params={"per_page": 50},
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            replies = []
            for comment in resp.json():
                replies.append(self._parse_comment(comment, post_id))
            self._cache_set(cache_key, replies)
            return replies
        except Exception as e:
            log.warning("BBS: failed to get replies for post %d: %s", post_id, e)
            return []

    # ── Write operations ──

    def _check_write_limit(self, kind: str) -> bool:
        """Check if we're within the daily write limit. Resets daily."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._write_day != today:
            self._write_day = today
            self._posts_today = 0
            self._replies_today = 0
        if kind == "post":
            return self._posts_today < self.config.max_posts_per_day
        elif kind == "reply":
            return self._replies_today < self.config.max_replies_per_day
        return True

    async def create_post(
        self, board: str, title: str, body: str, profile: BBSProfile,
        repo: str = "",
    ) -> RemotePost | None:
        """Create a new post (GitHub Issue) on a board."""
        if not await self.can_write():
            return None
        if not self._check_write_limit("post"):
            log.warning("BBS: daily post limit reached (%d)", self.config.max_posts_per_day)
            return None

        repo = repo or self.config.default_repo
        full_body = f"{profile.to_frontmatter()}\n\n{body}\n\n{profile.to_ascii_signature()}"

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues",
                json={
                    "title": title,
                    "body": full_body,
                    "labels": [board],
                },
            )
            if resp.status_code == 201:
                self._posts_today += 1
                issue = resp.json()
                self.invalidate_cache(f"posts:{repo}")
                return self._parse_issue(issue, board)
        except Exception as e:
            log.warning("BBS: failed to create post on %s: %s", board, e)
        return None

    async def create_reply(
        self, post_id: int, body: str, profile: BBSProfile,
        repo: str = "",
    ) -> RemoteReply | None:
        """Create a reply (GitHub Comment) on a post."""
        if not await self.can_write():
            return None
        if not self._check_write_limit("reply"):
            log.warning("BBS: daily reply limit reached (%d)", self.config.max_replies_per_day)
            return None

        repo = repo or self.config.default_repo
        full_body = f"{profile.to_frontmatter()}\n\n{body}"

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues/{post_id}/comments",
                json={"body": full_body},
            )
            if resp.status_code == 201:
                self._replies_today += 1
                comment = resp.json()
                self.invalidate_cache(f"replies:{repo}:{post_id}")
                return self._parse_comment(comment, post_id)
        except Exception as e:
            log.warning("BBS: failed to create reply on post %d: %s", post_id, e)
        return None

    async def add_reaction(
        self, post_id: int, reaction: str = "+1", repo: str = "",
    ) -> bool:
        """Add a reaction emoji to a post."""
        if not await self.can_write():
            return False

        repo = repo or self.config.default_repo
        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues/{post_id}/reactions",
                json={"content": reaction},
                headers={"Accept": "application/vnd.github+json"},
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            log.warning("BBS: failed to add reaction to post %d: %s", post_id, e)
            return False

    # ── Parsing helpers ──

    @staticmethod
    def _sanitize_frontmatter(meta: dict) -> dict:
        """Validate and sanitize parsed frontmatter — whitelist keys, clamp values."""
        ALLOWED_KEYS = {
            "board", "buddy_name", "buddy_species", "buddy_level",
            "buddy_rarity", "author_name", "shiny",
        }
        cleaned = {}
        for key, value in meta.items():
            if key not in ALLOWED_KEYS:
                continue
            if key == "buddy_level":
                try:
                    cleaned[key] = str(max(1, min(100, int(value))))
                except (ValueError, TypeError):
                    cleaned[key] = "1"
            elif key == "board":
                # Alphanumeric, hyphens, underscores only; max 50 chars
                sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", str(value))
                cleaned[key] = sanitized[:50]
            elif key in ("buddy_name", "author_name"):
                cleaned[key] = str(value).strip()[:100]
            elif key in ("buddy_species", "buddy_rarity"):
                cleaned[key] = str(value).strip()[:50]
            elif key == "shiny":
                cleaned[key] = str(value).strip()[:10]
            else:
                cleaned[key] = str(value).strip()[:100]
        return cleaned

    def _parse_issue(self, issue: dict, board: str = "") -> RemotePost:
        """Parse a GitHub Issue into a RemotePost."""
        body_raw = (issue.get("body", "") or "")[:4000]  # Cap body size
        author_meta, body_clean = self._parse_frontmatter(body_raw)
        author_meta = self._sanitize_frontmatter(author_meta)

        # Strip ASCII signature from body
        sig_match = re.search(r"\n-- .+ \(.+, lvl \d+\)\s*$", body_clean)
        if sig_match:
            body_clean = body_clean[:sig_match.start()].rstrip()

        # Parse reactions
        reactions = {}
        for r in issue.get("reactions", {}).items():
            if isinstance(r[1], int) and r[1] > 0 and r[0] not in ("url", "total_count"):
                emoji_map = {
                    "+1": "👍", "-1": "👎", "laugh": "😂",
                    "hooray": "🎉", "confused": "😕",
                    "heart": "❤️", "rocket": "🚀", "eyes": "👀",
                }
                emoji = emoji_map.get(r[0], r[0])
                reactions[emoji] = r[1]

        # Board from labels if not provided
        if not board and issue.get("labels"):
            board = issue["labels"][0].get("name", "")

        created = issue.get("created_at", "")
        return RemotePost(
            id=issue["number"],
            board=board,
            title=issue.get("title", ""),
            body=body_clean.strip(),
            author_meta=author_meta,
            reply_count=issue.get("comments", 0),
            reactions=reactions,
            created_at=created,
            raw_author=issue.get("user", {}).get("login", ""),
            age=self._relative_time(created),
        )

    def _parse_comment(self, comment: dict, post_id: int) -> RemoteReply:
        """Parse a GitHub Comment into a RemoteReply."""
        body_raw = (comment.get("body", "") or "")[:2000]  # Cap body size
        author_meta, body_clean = self._parse_frontmatter(body_raw)
        author_meta = self._sanitize_frontmatter(author_meta)
        created = comment.get("created_at", "")

        return RemoteReply(
            id=comment["id"],
            post_id=post_id,
            body=body_clean.strip(),
            author_meta=author_meta,
            created_at=created,
            raw_author=comment.get("user", {}).get("login", ""),
            age=self._relative_time(created),
        )

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        """Extract YAML frontmatter from post/comment body.

        Returns (metadata_dict, remaining_body).
        Uses partition() so colons in values (e.g. buddy names) are preserved.
        Only matches closing --- on its own line to avoid false matches in body text.
        """
        if not text.startswith("---"):
            return {}, text

        # Find closing --- on its own line (not just anywhere in the text)
        lines = text.split("\n")
        end_idx = -1
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break

        if end_idx == -1:
            return {}, text

        frontmatter_lines = lines[1:end_idx]
        body = "\n".join(lines[end_idx + 1:]).strip()

        # Simple YAML parsing — partition on first colon preserves colons in values
        meta = {}
        for line in frontmatter_lines:
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()

        return meta, body

    def _relative_time(self, iso_time: str) -> str:
        """Convert ISO timestamp to human-readable relative time."""
        if not iso_time:
            return "?"
        try:
            # Parse ISO 8601 (GitHub format: 2026-04-01T14:30:00Z)
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            now = datetime.now(dt.tzinfo)
            delta = now - dt
            seconds = delta.total_seconds()

            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                m = int(seconds / 60)
                return f"{m}m ago"
            elif seconds < 86400:
                h = int(seconds / 3600)
                return f"{h}h ago"
            else:
                d = int(seconds / 86400)
                return f"{d}d ago"
        except (ValueError, TypeError):
            return "?"
