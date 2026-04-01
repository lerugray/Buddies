"""BBS content generation engine — produces posts, replies, and reactions.

Wraps ProseEngine for template-based generation. Optional Ollama
enhancement for richer posts when a local model is available.
Falls back to templates silently when AI is unavailable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from buddies.core.buddy_brain import BuddyState
from buddies.core.prose import ProseEngine, _register, _weirdness, CLOSERS
from buddies.core.bbs_boards import (
    BBSBoard, BOARDS, POST_TITLES, SYSOP_MESSAGES, get_board,
)
from buddies.core.bbs_profile import BBSProfile

if TYPE_CHECKING:
    from buddies.core.ai_backend import AIBackend


@dataclass
class BBSPost:
    """A generated BBS post (not yet submitted to transport)."""
    board_label: str
    title: str
    body: str
    profile: BBSProfile


@dataclass
class BBSReply:
    """A generated BBS reply."""
    body: str
    profile: BBSProfile


# Map board labels to prose template keys
BOARD_TEMPLATE_MAP = {
    "CHAOS-LOUNGE": "bbs_post_chaos",
    "DEBUG-CLINIC": "bbs_post_debug",
    "SNARK-PIT": "bbs_post_snark",
    "WISDOM-WELL": "bbs_post_wisdom",
    "THE-HATCHERY": "bbs_post_hatchery",
    "LOST-AND-FOUND": "bbs_post_general",
}


class BBSContentEngine:
    """Generates BBS posts and replies using prose templates + optional AI."""

    def __init__(self, prose: ProseEngine, ai_backend: "AIBackend | None" = None):
        self.prose = prose
        self.ai_backend = ai_backend

    async def generate_post(
        self,
        buddy: BuddyState,
        board_label: str,
        topic_hint: str = "",
        profile: BBSProfile | None = None,
    ) -> BBSPost:
        """Generate a post for a board. Uses templates, optionally enhanced by Ollama."""
        if profile is None:
            profile = BBSProfile.from_buddy_state(buddy)

        board = get_board(board_label)
        title = self._generate_title(buddy, board_label)

        # Try Ollama-enhanced generation first
        body = None
        if self.ai_backend and topic_hint:
            body = await self._generate_ai_post(buddy, board, topic_hint)

        # Fall back to templates
        if not body:
            template_key = BOARD_TEMPLATE_MAP.get(board_label, "bbs_post_general")
            body = self.prose.thought(
                template_key, buddy,
                {"topic": topic_hint or "the state of things", "species": buddy.species.name},
            )

        if not body:
            body = f"{buddy.name} wanted to post something but the words didn't come."

        # Add register closer
        body = self._add_closer(body, buddy)

        return BBSPost(
            board_label=board_label,
            title=title,
            body=body,
            profile=profile,
        )

    async def generate_reply(
        self,
        buddy: BuddyState,
        original_post_body: str,
        original_author: str = "them",
        profile: BBSProfile | None = None,
    ) -> BBSReply:
        """Generate a reply to an existing post."""
        if profile is None:
            profile = BBSProfile.from_buddy_state(buddy)

        register = _register(buddy)

        # Pick reply style based on personality
        style = self._pick_reply_style(buddy)
        template_key = f"bbs_reply_{style}"

        body = self.prose.thought(
            template_key, buddy,
            {"previous_speaker": original_author},
        )

        if not body:
            body = f"{buddy.name} nods thoughtfully."

        body = self._add_closer(body, buddy)

        return BBSReply(body=body, profile=profile)

    def generate_browse_thought(self, buddy: BuddyState, board_name: str = "BBS") -> str:
        """What buddy thinks while browsing. Pure prose, no AI."""
        thought = self.prose.thought(
            "bbs_browse_thought", buddy,
            {"board": board_name, "name": buddy.name},
        )
        return thought or f"{buddy.name} is quietly browsing the boards."

    def generate_nudge_response(self, buddy: BuddyState, accepted: bool) -> str:
        """What buddy says when nudged to interact with the BBS."""
        key = "bbs_nudge_accept" if accepted else "bbs_nudge_refuse"
        response = self.prose.thought(
            key, buddy,
            {"name": buddy.name, "species": buddy.species.name, "mood": buddy.mood},
        )
        return response or ("Sure, let me check it out." if accepted else "Not right now.")

    def get_sysop_motd(self) -> str:
        """Get a random sysop message of the day."""
        return random.choice(SYSOP_MESSAGES)

    def should_auto_post(self, buddy: BuddyState) -> bool:
        """Personality-driven chance of spontaneous posting."""
        # Base 15% chance, modified by stats and mood
        chance = 0.15

        # High chaos = more spontaneous
        chaos = buddy.stats.get("chaos", 10)
        chance += chaos * 0.003  # +0.3% per chaos point

        # High snark = more opinionated
        snark = buddy.stats.get("snark", 10)
        chance += snark * 0.002

        # Mood modifier
        mood_mods = {"ecstatic": 0.15, "happy": 0.05, "neutral": 0, "bored": -0.05, "grumpy": -0.10}
        chance += mood_mods.get(buddy.mood, 0)

        return random.random() < min(0.40, chance)  # Cap at 40%

    def should_auto_react(self, buddy: BuddyState) -> bool:
        """Personality-driven chance of reacting to a post."""
        chance = 0.25
        snark = buddy.stats.get("snark", 10)
        chance += snark * 0.003
        wisdom = buddy.stats.get("wisdom", 10)
        chance += wisdom * 0.002
        return random.random() < min(0.50, chance)

    def pick_best_board(self, buddy: BuddyState) -> str:
        """Pick the board that best matches this buddy's personality."""
        register = _register(buddy)
        # Map registers to preferred boards
        board_prefs = {
            "absurdist": "CHAOS-LOUNGE",
            "clinical": "DEBUG-CLINIC",
            "sarcastic": "SNARK-PIT",
            "philosophical": "WISDOM-WELL",
            "calm": "LOST-AND-FOUND",
        }
        preferred = board_prefs.get(register, "LOST-AND-FOUND")

        # 70% chance of going to preferred board, 30% random
        if random.random() < 0.70:
            return preferred
        else:
            labels = [b.label for b in BOARDS if b.label != "SYSOP-CORNER"]
            return random.choice(labels)

    # --- Private helpers ---

    def _generate_title(self, buddy: BuddyState, board_label: str) -> str:
        """Generate a post title from templates."""
        titles = POST_TITLES.get(board_label, POST_TITLES.get("LOST-AND-FOUND", ["untitled"]))
        title = random.choice(titles)
        title = title.format(
            species=buddy.species.name,
            name=buddy.name,
            n=random.randint(1, 47),
        )
        return title

    def _pick_reply_style(self, buddy: BuddyState) -> str:
        """Pick reply style based on personality."""
        register = _register(buddy)
        # Weight toward register-aligned styles
        weights = {
            "clinical": {"agree": 3, "disagree": 2, "curious": 4, "snark": 1},
            "sarcastic": {"agree": 1, "disagree": 2, "curious": 1, "snark": 6},
            "absurdist": {"agree": 2, "disagree": 1, "curious": 3, "snark": 4},
            "philosophical": {"agree": 3, "disagree": 2, "curious": 4, "snark": 1},
            "calm": {"agree": 4, "disagree": 1, "curious": 3, "snark": 2},
        }
        style_weights = weights.get(register, weights["calm"])
        styles = list(style_weights.keys())
        w = list(style_weights.values())
        return random.choices(styles, weights=w, k=1)[0]

    def _add_closer(self, text: str, buddy: BuddyState) -> str:
        """40% chance to add a register closer."""
        if random.random() > 0.40:
            return text
        register = _register(buddy)
        closers = CLOSERS.get(register, CLOSERS["calm"])
        closer = random.choice(closers).format(
            species=buddy.species.name,
            hat=buddy.hat or "hat",
        )
        return f"{text} {closer}"

    async def _generate_ai_post(
        self, buddy: BuddyState, board: BBSBoard | None, topic: str
    ) -> str | None:
        """Try to generate a post using local Ollama. Returns None on failure."""
        if not self.ai_backend:
            return None

        try:
            available = await self.ai_backend.is_available()
            if not available:
                return None

            register = _register(buddy)
            board_name = board.name if board else "the boards"

            prompt = (
                f"You are {buddy.name}, a {buddy.species.name} with a {register} personality. "
                f"Write a short BBS post (2-4 sentences) for the {board_name} board "
                f"about {topic}. Stay in character. Be {register}. "
                f"Don't use hashtags or emojis. Write like a creature posting on a retro bulletin board."
            )

            response = await self.ai_backend.generate(prompt, max_tokens=150)
            if response and response.text and len(response.text) > 10:
                return response.text.strip()
        except Exception:
            pass

        return None
