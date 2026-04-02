"""Three-tier memory system — episodic, semantic, and procedural.

Episodic: what happened (sessions, events, conversations)
Semantic: what we know (facts, preferences, project info) with contradiction detection
Procedural: what works (patterns, rules, learned behaviors)

All backed by SQLite. No vector DB or embeddings needed — uses keyword/tag matching.
Works fully offline; AI backend can optionally enhance tag extraction.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from buddies.db.store import BuddyStore


# Keywords to strip from tag extraction
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "if", "then", "else", "when", "up", "out", "so", "than",
    "too", "very", "just", "about", "it", "its", "this", "that", "these",
    "those", "my", "your", "his", "her", "our", "their", "i", "you", "he",
    "she", "we", "they", "me", "him", "us", "them", "what", "which", "who",
    "whom", "how", "where", "why", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "only", "own", "same",
    "don't", "doesn't", "didn't", "won't", "wouldn't", "couldn't",
    "shouldn't", "use", "using", "used", "like", "also", "get", "got",
    "make", "made", "need", "want", "try", "thing", "things",
}

# Patterns for detecting semantic statements in chat
PREFERENCE_PATTERNS = [
    re.compile(r"^i\s+prefer\s+(.+)", re.IGNORECASE),
    re.compile(r"^i\s+(?:always|usually|normally)\s+(?:use|do|want)\s+(.+)", re.IGNORECASE),
    re.compile(r"^i\s+(?:like|love)\s+(?:to\s+)?(?:use\s+)?(.+)", re.IGNORECASE),
    re.compile(r"^i\s+(?:don'?t|never)\s+(?:like|want|use)\s+(.+)", re.IGNORECASE),
]

PROJECT_PATTERNS = [
    re.compile(r"(?:this|the)\s+project\s+uses?\s+(.+)", re.IGNORECASE),
    re.compile(r"we\s+use\s+(.+?)(?:\s+for\s+(.+))?$", re.IGNORECASE),
]

REMEMBER_PATTERNS = [
    re.compile(r"^(?:remember|note|btw|fyi)[\s:]+(.+)", re.IGNORECASE),
]


@dataclass
class MemoryEvent:
    """Buffered event waiting to be flushed to episodic memory."""
    event_type: str
    summary: str
    details: str = ""
    tags: list[str] = field(default_factory=list)
    importance: int = 5


class MemoryManager:
    """Manages three-tier memory: episodic, semantic, and procedural."""

    def __init__(self, store: BuddyStore):
        self.store = store
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._event_buffer: deque[MemoryEvent] = deque(maxlen=200)
        self._flush_lock = asyncio.Lock()

    # ── Episodic Memory ──

    async def add_episodic(self, event_type: str, summary: str,
                           details: str = "", tags: list[str] | None = None,
                           importance: int = 5) -> int:
        """Store an episodic memory directly (bypasses buffer)."""
        tag_list = tags or self.extract_tags(summary)
        return await self.store.add_episodic(
            session_id=self.session_id,
            event_type=event_type,
            summary=summary,
            details=details,
            tags=json.dumps(tag_list),
            importance=importance,
        )

    def buffer_event(self, event_type: str, summary: str,
                     details: str = "", tags: list[str] | None = None,
                     importance: int = 5) -> None:
        """Buffer an event for batch flushing (non-async, called from callbacks)."""
        self._event_buffer.append(MemoryEvent(
            event_type=event_type,
            summary=summary,
            details=details,
            tags=tags or self.extract_tags(summary),
            importance=importance,
        ))

    async def flush_buffer(self) -> int:
        """Flush buffered events to episodic memory. Returns count flushed."""
        async with self._flush_lock:
            count = 0
            while self._event_buffer:
                event = self._event_buffer.popleft()
                await self.store.add_episodic(
                    session_id=self.session_id,
                    event_type=event.event_type,
                    summary=event.summary,
                    details=event.details,
                    tags=json.dumps(event.tags),
                    importance=event.importance,
                )
                count += 1
            return count

    async def query_episodic(self, keyword: str = "", limit: int = 20) -> list[dict]:
        """Search episodic memories."""
        return await self.store.query_episodic(keyword=keyword, limit=limit)

    # ── Semantic Memory ──

    async def add_semantic(self, topic: str, key: str, value: str,
                           source: str = "observed", confidence: float = 0.5,
                           tags: list[str] | None = None) -> tuple[int, dict | None]:
        """Store a semantic fact with contradiction detection.

        Returns (new_id, old_record) — old_record is set if a contradiction was found.
        """
        tag_list = tags or self.extract_tags(f"{topic} {key} {value}")

        # Check for existing fact with same topic+key
        existing = await self.store.get_active_semantic(topic=topic, key=key)

        if existing:
            old = existing[0]
            if old["value"].strip().lower() == value.strip().lower():
                # Same fact — bump confidence
                await self.store.bump_semantic_confidence(old["id"])
                return old["id"], None
            else:
                # Contradiction — supersede old, insert new
                new_id = await self.store.add_semantic(
                    topic=topic, key=key, value=value,
                    source=source, confidence=confidence,
                    tags=json.dumps(tag_list),
                )
                await self.store.supersede_semantic(old["id"], new_id)
                return new_id, old
        else:
            # New fact
            new_id = await self.store.add_semantic(
                topic=topic, key=key, value=value,
                source=source, confidence=confidence,
                tags=json.dumps(tag_list),
            )
            return new_id, None

    async def query_semantic(self, keyword: str = "", limit: int = 20) -> list[dict]:
        """Search active semantic memories."""
        return await self.store.query_semantic(keyword=keyword, limit=limit)

    async def get_contradictions(self) -> list[dict]:
        """Get pairs where a fact was superseded by a new value."""
        return await self.store.get_contradictions()

    # ── Procedural Memory ──

    async def add_procedural(self, trigger_pattern: str, action: str,
                             outcome: str = "", source: str = "observed",
                             tags: list[str] | None = None) -> int:
        """Store a procedural memory (pattern → action)."""
        tag_list = tags or self.extract_tags(f"{trigger_pattern} {action}")

        # Check if similar procedure already exists
        existing = await self.store.query_procedural(keyword=trigger_pattern, limit=5)
        for proc in existing:
            if (proc["trigger_pattern"].lower() == trigger_pattern.lower()
                    and proc["action"].lower() == action.lower()):
                # Same procedure — record as success
                await self.store.record_procedural_outcome(proc["id"], success=True)
                return proc["id"]

        return await self.store.add_procedural(
            trigger_pattern=trigger_pattern,
            action=action,
            outcome=outcome,
            source=source,
            tags=json.dumps(tag_list),
        )

    async def query_procedural(self, keyword: str = "", limit: int = 20) -> list[dict]:
        """Search active procedural memories."""
        return await self.store.query_procedural(keyword=keyword, limit=limit)

    # ── Cross-Tier Recall ──

    async def recall(self, keywords: list[str], limit_per_tier: int = 5) -> dict[str, list[dict]]:
        """Search all three tiers by keywords. The main 'what do I know about X?' method."""
        search = " ".join(keywords)
        episodic = await self.store.query_episodic(keyword=search, limit=limit_per_tier)
        semantic = await self.store.query_semantic(keyword=search, limit=limit_per_tier)
        procedural = await self.store.query_procedural(keyword=search, limit=limit_per_tier)

        # Bump access counts (procedural table doesn't have access_count column)
        for mem in episodic:
            await self.store.bump_access("memory_episodic", mem["id"])
        for mem in semantic:
            await self.store.bump_access("memory_semantic", mem["id"])

        return {
            "episodic": episodic,
            "semantic": semantic,
            "procedural": procedural,
        }

    # ── Semantic Statement Detection ──

    def check_semantic_statement(self, message: str) -> tuple[str, str, str] | None:
        """Check if a chat message contains a semantic fact.

        Returns (topic, key, value) or None.
        """
        msg = message.strip()
        if len(msg) < 5 or len(msg) > 500:
            return None

        # "Remember X" / "Note: X"
        for pattern in REMEMBER_PATTERNS:
            m = pattern.match(msg)
            if m:
                content = m.group(1).strip()
                key = self._extract_key(content)
                return "user_note", key, content

        # "I prefer X" / "I always use X"
        for pattern in PREFERENCE_PATTERNS:
            m = pattern.match(msg)
            if m:
                content = m.group(1).strip()
                key = self._extract_key(content)
                return "user_preference", key, content

        # "This project uses X"
        for pattern in PROJECT_PATTERNS:
            m = pattern.search(msg)
            if m:
                content = m.group(1).strip()
                key = self._extract_key(content)
                return "project_tech", key, content

        return None

    # ── Memory Decay ──

    async def decay(self) -> tuple[int, int]:
        """Run memory decay/cleanup. Returns (episodic_deleted, procedural_deactivated)."""
        ep = await self.store.decay_episodic(days_threshold=90)
        pr = await self.store.decay_procedural(days_threshold=60)
        return ep, pr

    # ── Memory Stats ──

    async def get_stats(self) -> dict:
        """Get counts for each memory tier."""
        return {
            "episodic": await self.store.count_episodic(),
            "semantic": await self.store.count_semantic(),
            "procedural": await self.store.count_procedural(),
            "contradictions": len(await self.store.get_contradictions()),
        }

    # ── Tag Extraction ──

    def extract_tags(self, text: str) -> list[str]:
        """Extract keyword tags from text. No AI required."""
        # Lowercase and split
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())

        # Filter stop words and short words
        tags = []
        seen = set()
        for word in words:
            if word in STOP_WORDS or len(word) < 3 or word in seen:
                continue
            seen.add(word)
            tags.append(word)

        # Also extract file extensions and paths
        paths = re.findall(r"[\w/\\]+\.\w{1,5}", text)
        for p in paths:
            ext = p.rsplit(".", 1)[-1].lower()
            if ext not in seen:
                seen.add(ext)
                tags.append(ext)

        return tags[:10]  # Cap at 10 tags

    # ── Private Helpers ──

    def _extract_key(self, text: str) -> str:
        """Extract a short key from a text phrase."""
        # Take first 3 meaningful words
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        meaningful = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
        return "_".join(meaningful[:3]) if meaningful else "note"
