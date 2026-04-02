"""MUD GitHub Transport — shared multiplayer via GitHub Issues.

Maps MUD multiplayer data to GitHub Issues on the buddies-bbs repo:
  - Soapstone notes → Issues with label "mud-soapstone"
  - Bloodstains → Issues with label "mud-bloodstain"
  - Votes → Reactions on Issues (+1 for upvote, -1 for downvote)

Read-only without a GitHub PAT. Full write with token.
Falls back gracefully to local-only when offline.

Uses the same repo as the BBS (lerugray/buddies-bbs) — the MUD
multiplayer data lives alongside the BBS posts, distinguished by labels.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from buddies.config import BBSConfig
from buddies.core.games.mud_multiplayer import (
    SoapstoneNote,
    Bloodstain,
    Phantom,
    PHANTOM_ACTIONS,
    MudMultiplayerStore,
)

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
CACHE_TTL = 300  # 5 minutes — same as BBS
MAX_CACHE_ENTRIES = 50  # Evict oldest when exceeded


@dataclass
class _CacheEntry:
    data: object
    expires: float


class MudTransport:
    """Syncs MUD multiplayer data with GitHub Issues.

    Works alongside MudMultiplayerStore — local store is the source of truth,
    transport syncs outbound (push your notes/bloodstains) and inbound
    (fetch other players' data and merge into local).

    Design principles:
    - Never block gameplay on network — all sync is best-effort
    - Local store always works, even offline
    - Merge, don't replace — combine remote data with local
    - Rate-limit aware — backs off when GitHub says so
    - Read without token, write with token (same as BBS)
    """

    LABEL_SOAPSTONE = "mud-soapstone"
    LABEL_BLOODSTAIN = "mud-bloodstain"

    def __init__(self, config: BBSConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None
        self._write_available: bool | None = None
        self._cache: dict[str, _CacheEntry] = {}
        self._rate_limit_remaining: int = 999
        self._rate_limit_reset: float = 0.0
        # Track which local items we've already pushed
        self._pushed_note_ids: set[str] = set()
        self._pushed_stain_ids: set[str] = set()

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
                log.warning("MUD transport: rate limited, backing off")
                return False
        return True

    def _cache_get(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() < entry.expires:
            return entry.data
        return None

    def _cache_set(self, key: str, data: object):
        now = time.time()
        # Prune expired entries first
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            self._cache = {k: v for k, v in self._cache.items() if v.expires > now}
        # If still too large, evict oldest
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].expires)
            del self._cache[oldest_key]
        self._cache[key] = _CacheEntry(data=data, expires=now + CACHE_TTL)

    # ── Push: Local → GitHub ──

    async def push_note(self, note: SoapstoneNote) -> bool:
        """Push a local soapstone note to GitHub as an Issue."""
        if note.is_phantom or note.id in self._pushed_note_ids:
            return False
        if not await self.can_write() or not self._check_rate_limit():
            return False

        repo = self.config.default_repo
        title = f"📜 {note.author_emoji} {note.author_name} — {note.message[:50]}"
        body = _build_note_body(note)

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues",
                json={
                    "title": title,
                    "body": body,
                    "labels": [self.LABEL_SOAPSTONE],
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code == 201:
                self._pushed_note_ids.add(note.id)
                log.info("MUD transport: pushed note %s", note.id)
                return True
        except Exception as e:
            log.warning("MUD transport: failed to push note: %s", e)
        return False

    async def push_bloodstain(self, stain: Bloodstain) -> bool:
        """Push a local bloodstain to GitHub as an Issue."""
        if stain.is_phantom or stain.id in self._pushed_stain_ids:
            return False
        if not await self.can_write() or not self._check_rate_limit():
            return False

        repo = self.config.default_repo
        title = (
            f"💀 {stain.buddy_emoji} {stain.buddy_name} (Lv.{stain.buddy_level}) "
            f"fell to {stain.cause_of_death}"
        )
        body = _build_bloodstain_body(stain)

        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues",
                json={
                    "title": title,
                    "body": body,
                    "labels": [self.LABEL_BLOODSTAIN],
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code == 201:
                self._pushed_stain_ids.add(stain.id)
                log.info("MUD transport: pushed bloodstain %s", stain.id)
                return True
        except Exception as e:
            log.warning("MUD transport: failed to push bloodstain: %s", e)
        return False

    async def vote_note(self, issue_number: int, upvote: bool) -> bool:
        """Vote on a remote note via GitHub reaction."""
        if not await self.can_write() or not self._check_rate_limit():
            return False

        repo = self.config.default_repo
        reaction = "+1" if upvote else "-1"
        try:
            resp = await self._client.post(
                f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/reactions",
                json={"content": reaction},
            )
            self._update_rate_limit(resp)
            return resp.status_code in (200, 201)
        except Exception as e:
            log.warning("MUD transport: failed to vote: %s", e)
            return False

    # ── Pull: GitHub → Local ──

    async def fetch_notes_for_room(self, room_id: str) -> list[SoapstoneNote]:
        """Fetch remote soapstone notes for a specific room."""
        cache_key = f"mud_notes:{room_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not await self.is_available() or not self._check_rate_limit():
            return []

        repo = self.config.default_repo
        try:
            # Search issues by label + room_id in body
            resp = await self._client.get(
                f"{GITHUB_API}/repos/{repo}/issues",
                params={
                    "labels": self.LABEL_SOAPSTONE,
                    "state": "open",
                    "per_page": 20,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            notes = []
            for issue in resp.json():
                if "pull_request" in issue:
                    continue
                note = _parse_note_issue(issue)
                if note and note.room_id == room_id:
                    notes.append(note)

            self._cache_set(cache_key, notes)
            return notes
        except Exception as e:
            log.warning("MUD transport: failed to fetch notes: %s", e)
            return []

    async def fetch_bloodstains_for_room(self, room_id: str) -> list[Bloodstain]:
        """Fetch remote bloodstains for a specific room."""
        cache_key = f"mud_stains:{room_id}"
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
                    "labels": self.LABEL_BLOODSTAIN,
                    "state": "open",
                    "per_page": 20,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            stains = []
            for issue in resp.json():
                if "pull_request" in issue:
                    continue
                stain = _parse_bloodstain_issue(issue)
                if stain and stain.room_id == room_id:
                    stains.append(stain)

            self._cache_set(cache_key, stains)
            return stains
        except Exception as e:
            log.warning("MUD transport: failed to fetch bloodstains: %s", e)
            return []

    async def fetch_all_notes(self) -> list[SoapstoneNote]:
        """Fetch all remote notes (for full sync). Cached."""
        cache_key = "mud_notes:all"
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
                    "labels": self.LABEL_SOAPSTONE,
                    "state": "open",
                    "per_page": 50,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            notes = []
            for issue in resp.json():
                if "pull_request" in issue:
                    continue
                note = _parse_note_issue(issue)
                if note:
                    notes.append(note)

            self._cache_set(cache_key, notes)
            return notes
        except Exception as e:
            log.warning("MUD transport: failed to fetch all notes: %s", e)
            return []

    async def fetch_all_bloodstains(self) -> list[Bloodstain]:
        """Fetch all remote bloodstains (for full sync). Cached."""
        cache_key = "mud_stains:all"
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
                    "labels": self.LABEL_BLOODSTAIN,
                    "state": "open",
                    "per_page": 50,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []

            stains = []
            for issue in resp.json():
                if "pull_request" in issue:
                    continue
                stain = _parse_bloodstain_issue(issue)
                if stain:
                    stains.append(stain)

            self._cache_set(cache_key, stains)
            return stains
        except Exception as e:
            log.warning("MUD transport: failed to fetch all bloodstains: %s", e)
            return []

    # ── Sync: Merge remote into local ──

    async def sync_to_local(self, store: MudMultiplayerStore) -> dict[str, int]:
        """Pull remote data and merge into local store.

        Returns counts of new items merged: {"notes": N, "bloodstains": M}
        """
        counts = {"notes": 0, "bloodstains": 0}

        remote_notes = await self.fetch_all_notes()
        remote_stains = await self.fetch_all_bloodstains()

        # Merge notes — skip any with IDs we already have, cap at 200
        local_ids = {n.id for n in store.notes}
        for note in remote_notes:
            if note.id not in local_ids:
                store.notes.append(note)
                counts["notes"] += 1
        # Cap total notes to prevent unbounded growth
        if len(store.notes) > 200:
            store.notes = store.notes[-200:]

        # Merge bloodstains, cap at 50
        local_stain_ids = {b.id for b in store.bloodstains}
        for stain in remote_stains:
            if stain.id not in local_stain_ids:
                store.bloodstains.append(stain)
                counts["bloodstains"] += 1
        if len(store.bloodstains) > 50:
            store.bloodstains = store.bloodstains[-50:]

        # Generate phantoms from remote data, cap at 100
        # Other players' buddies become phantom traces
        for note in remote_notes:
            if note.id not in local_ids:
                phantom = Phantom(
                    room_id=note.room_id,
                    buddy_name=note.author_name,
                    buddy_emoji=note.author_emoji,
                    buddy_species="adventurer",
                    action=_phantom_action_from_note(note.message),
                    timestamp=note.timestamp,
                )
                store.phantoms.append(phantom)
        if len(store.phantoms) > 100:
            store.phantoms = store.phantoms[-100:]

        if counts["notes"] > 0 or counts["bloodstains"] > 0:
            store.save()
            log.info(
                "MUD transport: synced %d notes, %d bloodstains from remote",
                counts["notes"], counts["bloodstains"],
            )

        return counts

    async def push_local(self, store: MudMultiplayerStore) -> dict[str, int]:
        """Push un-synced local data to GitHub.

        Returns counts of items pushed: {"notes": N, "bloodstains": M}
        """
        counts = {"notes": 0, "bloodstains": 0}

        for note in store.notes:
            if await self.push_note(note):
                counts["notes"] += 1

        for stain in store.bloodstains:
            if await self.push_bloodstain(stain):
                counts["bloodstains"] += 1

        return counts


# ---------------------------------------------------------------------------
# Issue body builders — YAML frontmatter for structured data
# ---------------------------------------------------------------------------

def _build_note_body(note: SoapstoneNote) -> str:
    """Build a GitHub Issue body for a soapstone note."""
    return (
        f"---\n"
        f"type: soapstone\n"
        f"note_id: {note.id}\n"
        f"room_id: {note.room_id}\n"
        f"message: {note.message}\n"
        f"author_name: {note.author_name}\n"
        f"author_emoji: {note.author_emoji}\n"
        f"timestamp: {note.timestamp}\n"
        f"---\n\n"
        f"📜 *\"{note.message}\"*\n\n"
        f"Left by {note.author_emoji} **{note.author_name}** "
        f"in **{note.room_id.replace('_', ' ').title()}**\n\n"
        f"👍 = helpful  |  👎 = not helpful"
    )


def _build_bloodstain_body(stain: Bloodstain) -> str:
    """Build a GitHub Issue body for a bloodstain."""
    return (
        f"---\n"
        f"type: bloodstain\n"
        f"stain_id: {stain.id}\n"
        f"room_id: {stain.room_id}\n"
        f"cause_of_death: {stain.cause_of_death}\n"
        f"buddy_name: {stain.buddy_name}\n"
        f"buddy_emoji: {stain.buddy_emoji}\n"
        f"buddy_level: {stain.buddy_level}\n"
        f"timestamp: {stain.timestamp}\n"
        f"---\n\n"
        f"💀 **{stain.buddy_emoji} {stain.buddy_name}** (Lv.{stain.buddy_level}) "
        f"fell to **{stain.cause_of_death}**\n\n"
        f"in *{stain.room_id.replace('_', ' ').title()}*"
    )


# ---------------------------------------------------------------------------
# Issue parsers — extract structured data from GitHub Issues
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


def _sanitize_note_frontmatter(meta: dict) -> dict:
    """Validate and sanitize soapstone note frontmatter."""
    import re
    ALLOWED_KEYS = {
        "type", "note_id", "room_id", "message", "author_name",
        "author_emoji", "buddy_name", "buddy_species", "buddy_level",
        "timestamp", "rating",
    }
    cleaned = {}
    for key, value in meta.items():
        if key not in ALLOWED_KEYS:
            continue
        value = str(value).strip()
        if key == "room_id":
            sanitized = re.sub(r"[^a-zA-Z0-9_]", "", value)
            cleaned[key] = sanitized[:50]
        elif key == "buddy_level":
            try:
                cleaned[key] = str(max(1, min(100, int(value))))
            except (ValueError, TypeError):
                cleaned[key] = "1"
        elif key == "timestamp":
            try:
                ts = float(value)
                # Not before 2024-01-01, not more than 1 day in the future
                min_ts = 1704067200.0  # 2024-01-01 UTC
                max_ts = time.time() + 86400
                cleaned[key] = str(max(min_ts, min(max_ts, ts)))
            except (ValueError, TypeError):
                cleaned[key] = str(time.time())
        elif key == "rating":
            try:
                cleaned[key] = str(max(0, min(100, int(value))))
            except (ValueError, TypeError):
                cleaned[key] = "0"
        elif key == "message":
            cleaned[key] = value[:200]
        elif key in ("author_name", "buddy_name", "buddy_species", "note_id"):
            cleaned[key] = value[:50]
        elif key == "author_emoji":
            cleaned[key] = value[:10]
        elif key == "type":
            cleaned[key] = value[:20]
        else:
            cleaned[key] = value[:50]
    return cleaned


def _sanitize_bloodstain_frontmatter(meta: dict) -> dict:
    """Validate and sanitize bloodstain frontmatter."""
    import re
    ALLOWED_KEYS = {
        "type", "stain_id", "room_id", "cause_of_death", "author_name",
        "buddy_name", "buddy_emoji", "buddy_species", "buddy_level",
        "timestamp",
    }
    cleaned = {}
    for key, value in meta.items():
        if key not in ALLOWED_KEYS:
            continue
        value = str(value).strip()
        if key == "room_id":
            sanitized = re.sub(r"[^a-zA-Z0-9_]", "", value)
            cleaned[key] = sanitized[:50]
        elif key == "buddy_level":
            try:
                cleaned[key] = str(max(1, min(100, int(value))))
            except (ValueError, TypeError):
                cleaned[key] = "1"
        elif key == "timestamp":
            try:
                ts = float(value)
                min_ts = 1704067200.0  # 2024-01-01 UTC
                max_ts = time.time() + 86400
                cleaned[key] = str(max(min_ts, min(max_ts, ts)))
            except (ValueError, TypeError):
                cleaned[key] = str(time.time())
        elif key in ("buddy_name", "author_name", "buddy_species",
                      "cause_of_death", "stain_id"):
            cleaned[key] = value[:50]
        elif key == "buddy_emoji":
            cleaned[key] = value[:10]
        elif key == "type":
            cleaned[key] = value[:20]
        else:
            cleaned[key] = value[:50]
    return cleaned


def _parse_note_issue(issue: dict) -> SoapstoneNote | None:
    """Parse a GitHub Issue into a SoapstoneNote."""
    body = (issue.get("body", "") or "")[:1000]  # Cap body size
    meta = _parse_frontmatter(body)
    meta = _sanitize_note_frontmatter(meta)

    if meta.get("type") != "soapstone":
        return None

    # Count reactions as votes
    reactions = issue.get("reactions", {})
    upvotes = reactions.get("+1", 0)
    downvotes = reactions.get("-1", 0)

    try:
        return SoapstoneNote(
            id=meta.get("note_id", f"remote_{issue['number']}"),
            room_id=meta.get("room_id", ""),
            message=meta.get("message", ""),
            author_name=meta.get("author_name", "Unknown"),
            author_emoji=meta.get("author_emoji", "👻"),
            timestamp=float(meta.get("timestamp", time.time())),
            upvotes=upvotes,
            downvotes=downvotes,
            is_phantom=False,
        )
    except (ValueError, KeyError) as e:
        log.warning("MUD transport: failed to parse note issue: %s", e)
        return None


def _parse_bloodstain_issue(issue: dict) -> Bloodstain | None:
    """Parse a GitHub Issue into a Bloodstain."""
    body = (issue.get("body", "") or "")[:1000]  # Cap body size
    meta = _parse_frontmatter(body)
    meta = _sanitize_bloodstain_frontmatter(meta)

    if meta.get("type") != "bloodstain":
        return None

    try:
        return Bloodstain(
            id=meta.get("stain_id", f"remote_{issue['number']}"),
            room_id=meta.get("room_id", ""),
            cause_of_death=meta.get("cause_of_death", "unknown"),
            buddy_name=meta.get("buddy_name", "Unknown"),
            buddy_emoji=meta.get("buddy_emoji", "👻"),
            buddy_level=int(meta.get("buddy_level", 1)),
            timestamp=float(meta.get("timestamp", time.time())),
            is_phantom=False,
        )
    except (ValueError, KeyError) as e:
        log.warning("MUD transport: failed to parse bloodstain issue: %s", e)
        return None


def _phantom_action_from_note(message: str) -> str:
    """Generate a phantom action that relates to the note they left."""
    msg_lower = message.lower()
    if "coffee" in msg_lower:
        return "clutching a coffee mug"
    elif "debug" in msg_lower:
        return "staring intently at invisible code"
    elif "wary" in msg_lower or "trap" in msg_lower:
        return "looking around nervously"
    elif "praise" in msg_lower:
        return "celebrating a victory"
    elif "sadness" in msg_lower or "despair" in msg_lower:
        return "sitting quietly"
    elif "boss" in msg_lower or "enemy" in msg_lower:
        return "fighting an invisible enemy"
    elif "shortcut" in msg_lower or "secret" in msg_lower:
        return "searching for something"
    else:
        import random
        return random.choice(PHANTOM_ACTIONS)
