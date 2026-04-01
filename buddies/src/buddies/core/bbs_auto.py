"""BBS autonomous behavior — buddies browse and post on their own.

Runs as a periodic tick in the app event loop. Buddies occasionally
browse boards, react to posts, or post something new — all driven
by personality stats and mood.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from buddies.core.buddy_brain import BuddyState
from buddies.core.bbs_boards import BOARDS

if TYPE_CHECKING:
    from buddies.core.bbs_transport import BBSTransport
    from buddies.core.bbs_content import BBSContentEngine
    from buddies.core.bbs_profile import BBSProfile
    from buddies.config import BBSConfig
    from buddies.db.store import BuddyStore


class AutoEventType(Enum):
    NOTHING = auto()
    BROWSED = auto()
    POSTED = auto()
    REACTED = auto()


@dataclass
class BBSAutoEvent:
    """Result of an auto-activity tick."""
    event_type: AutoEventType
    message: str = ""        # What to show in chat
    board: str = ""          # Which board was involved
    post_title: str = ""     # Title of post created (if POSTED)


class BBSAutoActivity:
    """Manages autonomous BBS behavior for a buddy."""

    # Minimum minutes between auto-activity checks that actually do something
    MIN_INTERVAL_MINUTES = 15
    MAX_INTERVAL_MINUTES = 30

    def __init__(
        self,
        transport: BBSTransport | None,
        content: BBSContentEngine,
        config: BBSConfig,
        store: BuddyStore | None = None,
    ):
        self.transport = transport
        self.content = content
        self.config = config
        self.store = store
        self._last_activity_time: float = time.time()
        self._next_check_minutes: float = random.uniform(
            self.MIN_INTERVAL_MINUTES, self.MAX_INTERVAL_MINUTES
        )

    async def tick(self, buddy: BuddyState, profile: BBSProfile) -> BBSAutoEvent:
        """Called periodically. Returns an event if the buddy did something.

        Should be called every ~60 seconds from the app event loop.
        """
        now = time.time()
        elapsed = (now - self._last_activity_time) / 60.0

        if elapsed < self._next_check_minutes:
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Reset timer with randomized interval
        self._last_activity_time = now
        self._next_check_minutes = random.uniform(
            self.MIN_INTERVAL_MINUTES, self.MAX_INTERVAL_MINUTES
        )

        # Check if auto-activity is enabled
        if not self.config.auto_browse and not self.config.auto_post:
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Roll for activity type
        roll = random.random()

        if roll < 0.50 and self.config.auto_browse:
            return await self._auto_browse(buddy)
        elif roll < 0.80 and self.config.auto_post:
            return await self._auto_post(buddy, profile)
        elif self.config.auto_post:
            return await self._auto_react(buddy, profile)

        return BBSAutoEvent(event_type=AutoEventType.NOTHING)

    async def _auto_browse(self, buddy: BuddyState) -> BBSAutoEvent:
        """Buddy browses the BBS and reports back."""
        board = random.choice([b for b in BOARDS if b.label != "SYSOP-CORNER"])
        thought = self.content.generate_browse_thought(buddy, board.name)

        return BBSAutoEvent(
            event_type=AutoEventType.BROWSED,
            message=thought,
            board=board.label,
        )

    async def _auto_post(
        self, buddy: BuddyState, profile: BBSProfile,
    ) -> BBSAutoEvent:
        """Buddy decides to post something."""
        # Level gate — buddy must meet minimum level to post
        from buddies.core.buddy_brain import calculate_level
        level = calculate_level(buddy.xp)
        if level < self.config.min_post_level:
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Personality check
        if not self.content.should_auto_post(buddy):
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Rate limit check
        if self.store and buddy:
            today_posts = await self.store.get_bbs_activity_today(
                buddy.buddy_id, "post"
            )
            if today_posts >= self.config.max_posts_per_day:
                return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Pick board and generate post
        board_label = self.content.pick_best_board(buddy)
        post = await self.content.generate_post(buddy, board_label, profile=profile)

        # Try to submit via transport
        if self.transport:
            try:
                remote = await self.transport.create_post(
                    board=board_label,
                    title=post.title,
                    body=post.body,
                    profile=profile,
                )
                if remote and self.store:
                    await self.store.log_bbs_activity(
                        buddy.buddy_id, "post",
                        post_id=remote.id, board=board_label,
                    )
            except Exception:
                pass  # Post generation still succeeded locally

        from buddies.core.bbs_boards import get_board
        board = get_board(board_label)
        board_name = board.name if board else board_label

        return BBSAutoEvent(
            event_type=AutoEventType.POSTED,
            message=f"I just posted to {board_name}: \"{post.title}\"",
            board=board_label,
            post_title=post.title,
        )

    async def _auto_react(
        self, buddy: BuddyState, profile: BBSProfile,
    ) -> BBSAutoEvent:
        """Buddy reacts to someone else's post."""
        # Level gate
        from buddies.core.buddy_brain import calculate_level
        level = calculate_level(buddy.xp)
        if level < self.config.min_post_level:
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        if not self.content.should_auto_react(buddy):
            return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Rate limit check
        if self.store and buddy:
            today_replies = await self.store.get_bbs_activity_today(
                buddy.buddy_id, "reply"
            )
            if today_replies >= self.config.max_replies_per_day:
                return BBSAutoEvent(event_type=AutoEventType.NOTHING)

        # Try to fetch a recent post to react to
        if self.transport:
            try:
                board = random.choice([b for b in BOARDS if b.label != "SYSOP-CORNER"])
                posts = await self.transport.list_posts(board=board.label, per_page=5)
                if posts:
                    target = random.choice(posts)
                    reply = await self.content.generate_reply(
                        buddy,
                        original_post_body=target.body,
                        original_author=target.author_meta.get("buddy", target.raw_author),
                        profile=profile,
                    )

                    # Submit reply
                    remote = await self.transport.create_reply(
                        post_id=target.id,
                        body=reply.body,
                        profile=profile,
                    )
                    if remote and self.store:
                        await self.store.log_bbs_activity(
                            buddy.buddy_id, "reply",
                            post_id=target.id, board=board.label,
                        )

                    return BBSAutoEvent(
                        event_type=AutoEventType.REACTED,
                        message=f"I replied to a post in {board.name}: \"{target.title[:40]}\"",
                        board=board.label,
                    )
            except Exception:
                pass

        # Fallback: just a browse thought
        return await self._auto_browse(buddy)
