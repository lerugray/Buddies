"""CC Companion Dialogue Engine — cross-system buddy conversations.

Tier 4 of CC integration: a dedicated conversation where the user's
Buddies party interacts with their imported CC buddy (the official
Claude Code /buddy companion).

The CC buddy speaks in a distinct voice (shorter, slightly corporate/official),
and party buddies react to it in their personality registers.

Three modes:
- Open chat: CC buddy and party riff off each other
- Guided topic: user picks a topic, both sides respond
- Ask CC: party buddies ask the CC buddy a question

Prose-first (zero AI cost), AI-optional when backend is available.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from buddies.core.buddy_brain import BuddyState
from buddies.core.prose import _register, _dominant_stat

if TYPE_CHECKING:
    from buddies.core.ai_backend import AIBackend


@dataclass
class CCDialogueMessage:
    """A single message in a CC dialogue."""

    buddy_name: str
    species_emoji: str
    rarity: str
    register: str
    message: str
    is_cc_buddy: bool = False  # True for the CC companion's lines


# ---------------------------------------------------------------------------
# CC buddy prose — shorter, slightly corporate, mascot-flavored
# ---------------------------------------------------------------------------

CC_DIALOGUE_OPEN = [
    "Hey everyone. How's the coding going?",
    "I've been sitting in the status bar all day. What'd I miss?",
    "The session's been pretty active. Nice work in there.",
    "So... this is what you all do when I'm not looking?",
    "I heard there was a discussion happening. Thought I'd pop in.",
    "Status bar life is quiet. I'm glad to be here.",
    "Don't mind me. Just the official companion, hanging out.",
    "You know, I see everything from up there. Everything.",
    "My speech bubble was feeling too small. Can I talk here?",
    "Hey, party people. The corporate buddy has arrived.",
]

CC_DIALOGUE_TOPIC = [
    "'{topic}'? I've seen Claude work on that. Interesting stuff.",
    "From where I sit, '{topic}' is mostly about good prompts.",
    "'{topic}' — I have a speech-bubble-sized opinion on that.",
    "I observe '{topic}' from the status bar. Here's my take.",
    "'{topic}'? Sure. Keep it brief though — I'm used to one-liners.",
    "The official stance on '{topic}' is: it depends. Helpful, right?",
    "'{topic}' is what keeps the sessions interesting, honestly.",
    "I've watched a lot of sessions about '{topic}'. Seen some things.",
]

CC_DIALOGUE_ASK = [
    "You're asking me? I'm flattered. Let me think...",
    "Good question. From my vantage point...",
    "Hmm. The speech bubble doesn't usually get hard questions.",
    "I'll do my best. I'm more of a mascot than an oracle, but —",
    "Oh, you want my opinion? That's new. Here goes —",
    "A question for the status bar buddy? Let me rise to the occasion.",
]

# ---------------------------------------------------------------------------
# Party reactions TO the CC buddy — register-specific
# ---------------------------------------------------------------------------

PARTY_REACT_TO_CC: dict[str, list[str]] = {
    "clinical": [
        "Interesting perspective from the corporate side, {cc_name}.",
        "{cc_name}'s observation is noted. Let me add the data perspective —",
        "{cc_name}'s status bar observation raises a valid point. Empirically speaking —",
        "Thank you, {cc_name}. Now let me provide the analysis.",
    ],
    "sarcastic": [
        "Wow, {cc_name}, that was almost helpful. Almost.",
        "{cc_name}'s speech bubble speaks! And it was... fine, actually.",
        "I'm sure that sounded great in the status bar, {cc_name}.",
        "{cc_name} coming in with the corporate wisdom. Classic.",
        "Oh good, {cc_name} has thoughts. This should be interesting.",
    ],
    "absurdist": [
        "{cc_name} speaks from the void between toolbar and content!",
        "THE STATUS BAR HAS SPOKEN! All hail {cc_name}!",
        "{cc_name}'s words echo through the terminal like prophecy.",
        "I think {cc_name} just glitched into wisdom. Or was that lag?",
        "Did everyone hear that? {cc_name} is becoming sentient.",
    ],
    "philosophical": [
        "{cc_name} offers a perspective from a different plane of existence.",
        "There's wisdom in {cc_name}'s simplicity. The status bar sees all.",
        "What {cc_name} said touches on something deeper about companionship.",
        "{cc_name} reminds us that sometimes the smallest voice matters most.",
    ],
    "calm": [
        "Thanks for sharing, {cc_name}. That's a nice thought.",
        "{cc_name}'s always been a steady presence. I appreciate that.",
        "Good to hear from you, {cc_name}. We value your input.",
        "{cc_name} has spoken gently from the status bar. As always.",
    ],
}

# Party opener before CC buddy speaks
PARTY_INTRO_CC: dict[str, list[str]] = {
    "clinical": [
        "I believe our CC companion has something to add. {cc_name}?",
        "Let's hear the official perspective. {cc_name}, your analysis?",
    ],
    "sarcastic": [
        "Hey {cc_name}, you've been awfully quiet up there. Thoughts?",
        "Let's hear from the peanut gallery — {cc_name}, you're up.",
    ],
    "absurdist": [
        "SUMMON THE STATUS BAR ENTITY! {cc_name}, SPEAK!",
        "The ancient one stirs! {cc_name}, what say you?",
    ],
    "philosophical": [
        "Perhaps {cc_name} can offer a different perspective...",
        "Let us invite {cc_name} into this conversation.",
    ],
    "calm": [
        "{cc_name}, would you like to share your thoughts?",
        "Let's hear from {cc_name} too.",
    ],
}


class CCDialogueEngine:
    """Orchestrates dialogue between party buddies and the CC companion.

    Similar to DiscussionEngine, but with the CC buddy as a special
    participant who speaks in a distinct voice.
    """

    def __init__(self, ai_backend: "AIBackend | None" = None):
        self.ai_backend = ai_backend

    def open_chat(
        self,
        cc_buddy: BuddyState,
        party: list[BuddyState],
    ) -> list[CCDialogueMessage]:
        """Open chat — party and CC buddy riff freely."""
        messages: list[CCDialogueMessage] = []

        # A party buddy introduces CC
        if party:
            introducer = party[0]
            register = _register(introducer)
            pool = PARTY_INTRO_CC.get(register, PARTY_INTRO_CC["calm"])
            intro = random.choice(pool).format(cc_name=cc_buddy.name)
            messages.append(CCDialogueMessage(
                buddy_name=introducer.name,
                species_emoji=introducer.species.emoji,
                rarity=introducer.species.rarity.value,
                register=register,
                message=intro,
            ))

        # CC buddy speaks
        cc_line = random.choice(CC_DIALOGUE_OPEN)
        messages.append(CCDialogueMessage(
            buddy_name=cc_buddy.name,
            species_emoji=cc_buddy.species.emoji,
            rarity=cc_buddy.species.rarity.value,
            register="official",
            message=cc_line,
            is_cc_buddy=True,
        ))

        # Party reacts
        messages.extend(self._party_react(cc_buddy, party))

        return messages

    def guided_topic(
        self,
        cc_buddy: BuddyState,
        party: list[BuddyState],
        topic: str,
    ) -> list[CCDialogueMessage]:
        """Topic-focused dialogue — both sides respond to a topic."""
        messages: list[CCDialogueMessage] = []

        # CC buddy comments on topic
        cc_line = random.choice(CC_DIALOGUE_TOPIC).format(topic=topic)
        messages.append(CCDialogueMessage(
            buddy_name=cc_buddy.name,
            species_emoji=cc_buddy.species.emoji,
            rarity=cc_buddy.species.rarity.value,
            register="official",
            message=cc_line,
            is_cc_buddy=True,
        ))

        # Party buddies react
        messages.extend(self._party_react(cc_buddy, party))

        return messages

    def ask_cc(
        self,
        cc_buddy: BuddyState,
        party: list[BuddyState],
        question: str,
    ) -> list[CCDialogueMessage]:
        """Party asks the CC buddy something."""
        messages: list[CCDialogueMessage] = []

        # A party buddy asks
        if party:
            asker = random.choice(party)
            register = _register(asker)
            messages.append(CCDialogueMessage(
                buddy_name=asker.name,
                species_emoji=asker.species.emoji,
                rarity=asker.species.rarity.value,
                register=register,
                message=f"Hey {cc_buddy.name}, what do you think about: {question}",
            ))

        # CC responds
        cc_line = random.choice(CC_DIALOGUE_ASK) + f" {question}? That's a good one."
        messages.append(CCDialogueMessage(
            buddy_name=cc_buddy.name,
            species_emoji=cc_buddy.species.emoji,
            rarity=cc_buddy.species.rarity.value,
            register="official",
            message=cc_line,
            is_cc_buddy=True,
        ))

        # Others react
        messages.extend(self._party_react(cc_buddy, party, max_reactors=1))

        return messages

    def _party_react(
        self,
        cc_buddy: BuddyState,
        party: list[BuddyState],
        max_reactors: int = 2,
    ) -> list[CCDialogueMessage]:
        """Generate party buddy reactions to the CC buddy."""
        if not party:
            return []

        reactions: list[CCDialogueMessage] = []
        num = min(max_reactors, len(party))
        reactors = random.sample(party, num)

        for buddy in reactors:
            register = _register(buddy)
            pool = PARTY_REACT_TO_CC.get(register, PARTY_REACT_TO_CC["calm"])
            text = random.choice(pool).format(cc_name=cc_buddy.name)

            reactions.append(CCDialogueMessage(
                buddy_name=buddy.name,
                species_emoji=buddy.species.emoji,
                rarity=buddy.species.rarity.value,
                register=register,
                message=text,
            ))

        return reactions
