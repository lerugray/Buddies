"""BBS nudge mechanic — detects BBS intent in chat and resolves compliance.

Users nudge their buddy via natural chat messages like "go check out the
debug clinic" or "post about that weird bug." The buddy may comply or
refuse based on personality, mood, and cooldowns.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import Enum, auto

from buddies.core.buddy_brain import BuddyState
from buddies.core.bbs_boards import BOARDS, BOARD_MAP


class NudgeAction(Enum):
    POST = auto()
    BROWSE = auto()
    REPLY = auto()
    REACT = auto()


@dataclass
class NudgeIntent:
    """A detected BBS intent from user chat."""
    action: NudgeAction
    board_hint: str = ""     # Board name/label if mentioned
    topic_hint: str = ""     # Topic if mentioned


@dataclass
class NudgeOutcome:
    """Result of resolving a nudge through personality."""
    accepted: bool
    flavor_text: str
    intent: NudgeIntent | None = None


# Board name aliases for fuzzy matching
BOARD_ALIASES = {}
for board in BOARDS:
    # Add variations: "chaos lounge", "chaos", "chaoslounge", label
    name_lower = board.name.lower()
    BOARD_ALIASES[name_lower] = board.label
    BOARD_ALIASES[name_lower.replace(" ", "")] = board.label
    BOARD_ALIASES[board.label.lower()] = board.label
    # First word alias (e.g., "chaos" -> CHAOS-LOUNGE)
    first_word = name_lower.split()[0]
    if first_word not in ("the", "lost"):
        BOARD_ALIASES[first_word] = board.label


class NudgeDetector:
    """Detects BBS-related intent in user chat messages."""

    POST_PATTERNS = [
        re.compile(r"(?:go\s+)?post\s+(?:about|on|to|in)\s+(.+)", re.IGNORECASE),
        re.compile(r"write\s+(?:something\s+)?(?:about|on|in)\s+(.+)", re.IGNORECASE),
        re.compile(r"share\s+(?:something\s+)?(?:about|on)\s+(.+)", re.IGNORECASE),
        re.compile(r"go\s+post\s+(.+)", re.IGNORECASE),
        re.compile(r"post\s+something", re.IGNORECASE),
    ]

    BROWSE_PATTERNS = [
        re.compile(r"(?:go\s+)?(?:check|browse|look at|visit|see)\s+(?:the\s+)?(?:bbs|boards?|posts?)", re.IGNORECASE),
        re.compile(r"(?:go\s+)?(?:check|browse|look at|visit)\s+(?:the\s+)?(.+?)(?:\s+board)?$", re.IGNORECASE),
        re.compile(r"what.+(?:posting|happening|going on)\s+(?:on|at)\s+(?:the\s+)?(?:bbs|boards?)", re.IGNORECASE),
        re.compile(r"go\s+browse", re.IGNORECASE),
    ]

    REPLY_PATTERNS = [
        re.compile(r"(?:go\s+)?reply\s+to\s+(.+)", re.IGNORECASE),
        re.compile(r"(?:go\s+)?respond\s+to\s+(.+)", re.IGNORECASE),
    ]

    REACT_PATTERNS = [
        re.compile(r"(?:go\s+)?react\s+to\s+(.+)", re.IGNORECASE),
        re.compile(r"what\s+do\s+you\s+think\s+(?:of|about)\s+(.+?)(?:\s+post)?$", re.IGNORECASE),
    ]

    def detect(self, message: str) -> NudgeIntent | None:
        """Check if a message contains BBS intent. Returns intent or None."""
        msg = message.strip()
        if len(msg) < 4:
            return None

        # Check post intent
        for pattern in self.POST_PATTERNS:
            m = pattern.search(msg)
            if m:
                topic = m.group(1).strip() if m.lastindex else ""
                board = self._extract_board(topic) or self._extract_board(msg)
                return NudgeIntent(
                    action=NudgeAction.POST,
                    board_hint=board,
                    topic_hint=topic,
                )

        # Check browse intent
        for pattern in self.BROWSE_PATTERNS:
            m = pattern.search(msg)
            if m:
                hint = m.group(1).strip() if m.lastindex else ""
                board = self._extract_board(hint) or self._extract_board(msg)
                return NudgeIntent(
                    action=NudgeAction.BROWSE,
                    board_hint=board,
                )

        # Check reply intent
        for pattern in self.REPLY_PATTERNS:
            m = pattern.search(msg)
            if m:
                topic = m.group(1).strip() if m.lastindex else ""
                return NudgeIntent(
                    action=NudgeAction.REPLY,
                    topic_hint=topic,
                )

        # Check react intent
        for pattern in self.REACT_PATTERNS:
            m = pattern.search(msg)
            if m:
                topic = m.group(1).strip() if m.lastindex else ""
                return NudgeIntent(
                    action=NudgeAction.REACT,
                    topic_hint=topic,
                )

        return None

    def _extract_board(self, text: str) -> str:
        """Try to match a board name from text."""
        text_lower = text.lower().strip()
        # Direct match
        if text_lower in BOARD_ALIASES:
            return BOARD_ALIASES[text_lower]
        # Substring match
        for alias, label in BOARD_ALIASES.items():
            if alias in text_lower:
                return label
        return ""


class NudgeResolver:
    """Decides if the buddy follows through on a nudge."""

    def resolve(self, buddy: BuddyState, intent: NudgeIntent) -> NudgeOutcome:
        """Personality-driven decision on whether to comply."""
        # Base compliance rate
        comply_chance = 0.70

        # Mood modifier — biggest factor
        mood_mods = {
            "ecstatic": 0.25,
            "happy": 0.10,
            "neutral": 0.0,
            "bored": -0.10,
            "grumpy": -0.30,
        }
        comply_chance += mood_mods.get(buddy.mood, 0)

        # Register-board affinity — buddy is more willing for matching boards
        if intent.board_hint:
            from buddies.core.bbs_boards import get_board
            board = get_board(intent.board_hint)
            if board:
                dominant = max(buddy.stats, key=buddy.stats.get)
                if board.stat_affinity == dominant:
                    comply_chance += 0.15  # Natural fit

        # Level modifier — low-level buddies more easily nudged
        if buddy.level < 5:
            comply_chance += 0.10

        # Action difficulty — posting is harder to get than browsing
        if intent.action == NudgeAction.BROWSE:
            comply_chance += 0.10  # Browsing is low-commitment
        elif intent.action == NudgeAction.POST:
            comply_chance -= 0.05  # Posting takes effort

        # Clamp
        comply_chance = max(0.15, min(0.95, comply_chance))

        accepted = random.random() < comply_chance

        return NudgeOutcome(
            accepted=accepted,
            flavor_text="",  # Filled by content engine
            intent=intent,
        )
