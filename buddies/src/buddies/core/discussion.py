"""Multi-buddy discussion engine — party focus group conversations.

Orchestrates discussions between multiple buddies, each speaking through
their personality register. Three modes:
- Open chat: buddies riff off each other (pure prose, zero cost)
- Guided topic: user provides a topic, each buddy responds in-character
- File focus: buddies comment on a file using metadata or AI analysis

No AI required. Falls back to prose engine for everything.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.prose import ProseEngine, _register, _dominant_stat


@dataclass
class DiscussionMessage:
    """A single message in a discussion."""

    buddy_name: str
    species_emoji: str
    rarity: str
    register: str
    message: str


def _extract_file_meta(file_path: str) -> dict:
    """Extract basic metadata from a file for prose templates."""
    path = Path(file_path)
    meta = {
        "filename": path.name,
        "extension": path.suffix.lstrip(".") or "unknown",
        "line_count": 0,
        "function_count": 0,
    }

    if not path.exists() or not path.is_file():
        return meta

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        meta["line_count"] = len(lines)

        # Count function/method definitions across common languages
        func_pattern = re.compile(
            r"(?:^|\s)(?:def |function |fn |func |public |private |protected )"
            r"\w+\s*\(",
            re.MULTILINE,
        )
        meta["function_count"] = len(func_pattern.findall(content))
    except (OSError, UnicodeDecodeError):
        pass

    return meta


# Register-flavored commentary for when no AI is available.
# These provide stat-specific takes on code/topics beyond what
# the generic prose templates give.

REGISTER_COMMENTARY: dict[str, dict[str, list[str]]] = {
    "clinical": {
        "open": [
            "I've been running diagnostics on our recent patterns. The data is... interesting.",
            "Let me present my findings. I've prepared a brief analysis.",
            "From a purely analytical standpoint, things could be more optimal.",
        ],
        "topic": [
            "The data on '{topic}' suggests several actionable conclusions.",
            "I've analyzed '{topic}' from multiple angles. Here's the breakdown.",
            "Regarding '{topic}' — the metrics tell an interesting story.",
        ],
        "file": [
            "{line_count} lines, {function_count} functions. The ratio concerns me.",
            "The structure of {filename} has some measurable inefficiencies.",
            "My analysis of {filename}: organizationally sound, but {function_count} functions may indicate scope creep.",
        ],
        "react": [
            "Setting aside {previous_speaker}'s... colorful interpretation, the data shows —",
            "While {previous_speaker}'s hypothesis is creative, my analysis suggests otherwise.",
            "I'll table {previous_speaker}'s point and note that empirically —",
        ],
    },
    "sarcastic": {
        "open": [
            "Oh good, a group meeting. My absolute favorite thing.",
            "So are we actually doing this or can I go back to judging code silently?",
            "I have SO many opinions. You're all going to love them. Probably.",
        ],
        "topic": [
            "'{topic}'? Oh, I have THOUGHTS about that. Buckle up.",
            "Sure, let's talk about '{topic}'. This should be entertaining.",
            "'{topic}' — a topic I definitely didn't roll my eyes at. Definitely.",
        ],
        "file": [
            "{filename}? {line_count} lines of... choices. Bold choices.",
            "I see {function_count} functions in {filename}. Some of them even have names that make sense.",
            "Ah yes, {filename}. A {extension} file. How quaint.",
        ],
        "react": [
            "Wow, {previous_speaker}. That was certainly... a take.",
            "I love how confidently {previous_speaker} said something so debatable.",
            "{previous_speaker} makes a point, but let me make a better one.",
        ],
    },
    "absurdist": {
        "open": [
            "I just had a vision of the code becoming sentient. Anyway, what's up?",
            "THE VARIABLES DEMAND REPRESENTATION! ...sorry, where were we?",
            "I consulted the cosmic stack trace and it said we should talk.",
        ],
        "topic": [
            "'{topic}' is what the electrons were whispering about last night.",
            "I dreamed about '{topic}'. The semicolons were involved somehow.",
            "'{topic}' — a concept that exists in at least three parallel branches.",
        ],
        "file": [
            "{filename} is {line_count} lines of raw, unfiltered reality. I've seen things.",
            "I'm pretty sure {filename} achieved sentience around line {function_count}0.",
            "The {extension} files have been gossiping about {filename} again.",
        ],
        "react": [
            "{previous_speaker} speaks the language of the void. I approve.",
            "What {previous_speaker} said, but imagine it sung by a choir of error messages.",
            "{previous_speaker} gets it. Or doesn't. Either way, I'm on board.",
        ],
    },
    "philosophical": {
        "open": [
            "Have you ever considered what the code thinks about us?",
            "In the grand architecture of things, where do we fit?",
            "Every function has a purpose. Do we know ours?",
        ],
        "topic": [
            "'{topic}' — at its core, this is really about the nature of abstraction.",
            "When we discuss '{topic}', we're really asking deeper questions about design.",
            "'{topic}' reveals something fundamental about how we approach problems.",
        ],
        "file": [
            "{filename} tells a story. {line_count} lines of accumulated intention.",
            "Each of those {function_count} functions represents a decision. Were they the right ones?",
            "{filename} is a reflection of its authors. What does it say about them?",
        ],
        "react": [
            "{previous_speaker} raises an interesting philosophical point, whether they meant to or not.",
            "Building on {previous_speaker}'s wisdom — there's a deeper pattern here.",
            "What {previous_speaker} said connects to something larger...",
        ],
    },
    "calm": {
        "open": [
            "No rush, but I've been thinking about a few things.",
            "When the moment feels right... I had some thoughts to share.",
            "Let's take a breath and think about where we are.",
        ],
        "topic": [
            "'{topic}' is worth taking our time with. Let's think it through.",
            "There's no rush on '{topic}'. Let's explore it gently.",
            "'{topic}' — let me share my thoughts. No pressure.",
        ],
        "file": [
            "{filename} has {line_count} lines. That's okay. It'll grow when it needs to.",
            "Every one of those {function_count} functions has its place. Patience with the structure.",
            "{filename} is doing its best. Let's see where it wants to go.",
        ],
        "react": [
            "{previous_speaker} has a point. Let's sit with that for a moment.",
            "I appreciate what {previous_speaker} said. Let me add something gentle —",
            "Taking in what {previous_speaker} shared... yes, and also —",
        ],
    },
}


class DiscussionEngine:
    """Orchestrates multi-buddy discussions using the prose engine."""

    def __init__(self, prose: ProseEngine):
        self.prose = prose

    def open_chat(self, participants: list[BuddyState]) -> list[DiscussionMessage]:
        """Generate a round of open discussion — buddies riff freely."""
        messages: list[DiscussionMessage] = []

        # First round: each buddy speaks
        for buddy in participants:
            register = _register(buddy)
            commentary = REGISTER_COMMENTARY.get(register, REGISTER_COMMENTARY["calm"])
            pool = commentary["open"]

            # Try prose engine first, fall back to register commentary
            text = self.prose.thought("discussion_open", buddy)
            if not text:
                import random
                text = random.choice(pool)

            messages.append(DiscussionMessage(
                buddy_name=buddy.name,
                species_emoji=buddy.species.emoji,
                rarity=buddy.species.rarity.value,
                register=register,
                message=text,
            ))

        # Second round: reactions (if 2+ participants)
        if len(participants) >= 2:
            messages.extend(self._react_round(participants, messages))

        return messages

    def guided_topic(
        self, participants: list[BuddyState], topic: str
    ) -> list[DiscussionMessage]:
        """Generate a round of topic-focused discussion."""
        messages: list[DiscussionMessage] = []

        for buddy in participants:
            register = _register(buddy)
            commentary = REGISTER_COMMENTARY.get(register, REGISTER_COMMENTARY["calm"])

            # Try prose engine with topic context
            text = self.prose.thought(
                "discussion_topic", buddy, {"topic": topic}
            )
            if not text:
                import random
                text = random.choice(commentary["topic"]).format(
                    topic=topic,
                )

            messages.append(DiscussionMessage(
                buddy_name=buddy.name,
                species_emoji=buddy.species.emoji,
                rarity=buddy.species.rarity.value,
                register=register,
                message=text,
            ))

        # Reactions
        if len(participants) >= 2:
            messages.extend(self._react_round(participants, messages))

        return messages

    def file_focus(
        self, participants: list[BuddyState], file_path: str
    ) -> list[DiscussionMessage]:
        """Generate commentary on a specific file."""
        meta = _extract_file_meta(file_path)
        messages: list[DiscussionMessage] = []

        for buddy in participants:
            register = _register(buddy)
            commentary = REGISTER_COMMENTARY.get(register, REGISTER_COMMENTARY["calm"])

            # Try prose engine with file context
            text = self.prose.thought("discussion_file", buddy, meta)
            if not text:
                import random
                text = random.choice(commentary["file"]).format(**meta)

            messages.append(DiscussionMessage(
                buddy_name=buddy.name,
                species_emoji=buddy.species.emoji,
                rarity=buddy.species.rarity.value,
                register=register,
                message=text,
            ))

        # Reactions
        if len(participants) >= 2:
            messages.extend(self._react_round(participants, messages))

        return messages

    def _react_round(
        self,
        participants: list[BuddyState],
        first_round: list[DiscussionMessage],
    ) -> list[DiscussionMessage]:
        """Generate reaction messages — buddies respond to each other.

        Only a subset react (not everyone every time) to keep it natural.
        """
        import random

        reactions: list[DiscussionMessage] = []

        # Pick 1-2 reactors (not the same as who they're reacting to)
        num_reactors = min(2, len(participants) - 1)
        reactors = random.sample(participants, min(num_reactors, len(participants)))

        for reactor in reactors:
            # Pick someone else's message to react to
            others = [m for m in first_round if m.buddy_name != reactor.name]
            if not others:
                continue
            target = random.choice(others)

            register = _register(reactor)
            commentary = REGISTER_COMMENTARY.get(register, REGISTER_COMMENTARY["calm"])

            ctx = {
                "previous_speaker": target.buddy_name,
                "previous_register": target.register,
            }
            text = self.prose.thought("discussion_react", reactor, ctx)
            if not text:
                text = random.choice(commentary["react"]).format(
                    previous_speaker=target.buddy_name,
                )

            reactions.append(DiscussionMessage(
                buddy_name=reactor.name,
                species_emoji=reactor.species.emoji,
                rarity=reactor.species.rarity.value,
                register=register,
                message=text,
            ))

        return reactions
