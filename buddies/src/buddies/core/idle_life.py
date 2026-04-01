"""Idle Life — buddies do things in the background while you code.

Every few minutes, each buddy in your party has a chance to do
something: explore, find items, write journal entries, get into
trouble, or interact with other buddies.

Events accumulate and are shown as a "while you were gone" log.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState


@dataclass
class IdleEvent:
    """A single thing a buddy did while idle."""
    buddy_name: str
    buddy_emoji: str
    text: str
    category: str  # "explore", "find", "journal", "trouble", "social"
    timestamp: float = field(default_factory=time.time)
    gold_found: int = 0
    mood_change: int = 0


# ---------------------------------------------------------------------------
# Event templates by category
# ---------------------------------------------------------------------------

EXPLORE_EVENTS = [
    "{name} wandered into the config files and got lost for a bit.",
    "{name} explored the node_modules folder. They haven't been the same since.",
    "{name} found a hidden directory nobody remembers creating.",
    "{name} went for a walk through the git history.",
    "{name} discovered an abandoned feature branch from 6 months ago.",
    "{name} stared at the terminal for 20 minutes. Says it stared back.",
    "{name} tried to read the minified CSS. Immediately regretted it.",
    "{name} mapped out the import graph. Drew it on the wall in crayon.",
    "{name} found the TODO comments from 2019. Still TODO.",
    "{name} explored the Docker volumes. Found digital dust bunnies.",
]

FIND_EVENTS = [
    ("{name} found a golden semicolon behind the firewall!", 5),
    ("{name} discovered an unused API key! (Don't worry, it's expired.)", 3),
    ("{name} dug up an ancient stack trace. Framed it.", 2),
    ("{name} found a perfectly indented YAML file. Priceless.", 8),
    ("{name} scavenged some bits from the recycling bin.", 1),
    ("{name} found a comment that actually explains the code! Legendary!", 10),
    ("{name} recovered some leaked memory. Put it in a jar.", 4),
    ("{name} found a bug and is keeping it as a pet.", 3),
    ("{name} discovered a secret .env.example. It has notes!", 6),
    ("{name} found an unused port. Claims it as their new home.", 2),
]

JOURNAL_ENTRIES = [
    "{name}'s journal: \"Today I watched the human code. They are... interesting.\"",
    "{name}'s journal: \"The cursor blinks 60 times per minute. I counted.\"",
    "{name}'s journal: \"I think the linter is my nemesis. It judges everything.\"",
    "{name}'s journal: \"Dear diary, the human forgot to save again.\"",
    "{name}'s journal: \"Note to self: never look directly at a regex.\"",
    "{name}'s journal: \"The coffee machine made a sound. I think it's alive.\"",
    "{name}'s journal: \"Overheard the AI say 'as an AI, I...' and stopped listening.\"",
    "{name}'s journal: \"Tried to refactor my own personality. Got a stack overflow.\"",
    "{name}'s journal: \"The other buddies are alright, I guess. Don't tell them I said that.\"",
    "{name}'s journal: \"Production hasn't broken today. Suspicious.\"",
]

TROUBLE_EVENTS = [
    "{name} accidentally ran rm -rf on the virtual snack cabinet.",
    "{name} opened 47 browser tabs and forgot why.",
    "{name} tried to push to main. Was stopped by the branch protection.",
    "{name} renamed all the variables to food items. Changed them back. Mostly.",
    "{name} set up a cron job that just says 'beep' every hour.",
    "{name} tried to pet the linter. Got a warning.",
    "{name} started a flame war in the comments. About tabs vs spaces.",
    "{name} deployed to staging instead of dev. Nobody noticed.",
    "{name} wrote a TODO that just says 'fix this eventually maybe'.",
    "{name} sent a Slack message to #general instead of #random. Chaos.",
]

# Social events (when multiple buddies are in party)
SOCIAL_EVENTS = [
    "{name1} and {name2} had a debate about the best sorting algorithm.",
    "{name1} taught {name2} a new keyboard shortcut.",
    "{name1} and {name2} played tic-tac-toe on the whiteboard.",
    "{name1} stole {name2}'s favorite mug. Returned it with a Post-it apology.",
    "{name1} and {name2} formed a secret alliance. Against whom? Unknown.",
    "{name1} challenged {name2} to a staring contest. (It's still going.)",
    "{name1} showed {name2} their journal. {name2} was... concerned.",
    "{name1} and {name2} discovered they have the same favorite error message.",
    "{name1} accidentally called {name2} by the wrong name. Awkward silence.",
    "{name1} and {name2} collaborated on a haiku about null pointers.",
]


class IdleLife:
    """Manages background idle activity for all buddies."""

    def __init__(self):
        self.events: list[IdleEvent] = []
        self.last_tick: float = time.time()
        self._event_interval: float = 180.0  # Seconds between event checks (3 min)

    def tick(self, buddies: list[BuddyState]) -> list[IdleEvent]:
        """Check if it's time for idle events. Returns new events if any.

        Call this periodically (e.g., every 30 seconds). Events only
        generate every ~3 minutes to avoid spam.
        """
        now = time.time()
        elapsed = now - self.last_tick

        if elapsed < self._event_interval:
            return []

        self.last_tick = now
        new_events: list[IdleEvent] = []

        for buddy in buddies:
            # Each buddy has a chance to do something
            if random.random() < 0.6:  # 60% chance per tick
                event = self._generate_event(buddy, buddies)
                if event:
                    new_events.append(event)
                    self.events.append(event)

        return new_events

    def _generate_event(self, buddy: BuddyState, all_buddies: list[BuddyState]) -> IdleEvent | None:
        """Generate a random idle event for a buddy."""
        name = buddy.name
        emoji = buddy.species.emoji
        stats = buddy.stats

        # Weight categories by personality
        weights = {
            "explore": 20 + stats.get("wisdom", 10),
            "find": 15 + stats.get("debugging", 10),
            "journal": 15 + stats.get("patience", 10),
            "trouble": 10 + stats.get("chaos", 10),
            "social": 20 if len(all_buddies) > 1 else 0,
        }

        categories = list(weights.keys())
        w = [weights[c] for c in categories]
        category = random.choices(categories, weights=w)[0]

        if category == "explore":
            text = random.choice(EXPLORE_EVENTS).format(name=name)
            return IdleEvent(name, emoji, text, category)

        elif category == "find":
            template, gold = random.choice(FIND_EVENTS)
            text = template.format(name=name)
            return IdleEvent(name, emoji, text, category, gold_found=gold)

        elif category == "journal":
            text = random.choice(JOURNAL_ENTRIES).format(name=name)
            return IdleEvent(name, emoji, text, category)

        elif category == "trouble":
            text = random.choice(TROUBLE_EVENTS).format(name=name)
            return IdleEvent(name, emoji, text, category, mood_change=-1)

        elif category == "social" and len(all_buddies) > 1:
            other = random.choice([b for b in all_buddies if b.name != name])
            text = random.choice(SOCIAL_EVENTS).format(name1=name, name2=other.name)
            return IdleEvent(name, emoji, text, category, mood_change=1)

        return None

    def get_recent(self, n: int = 10) -> list[IdleEvent]:
        """Get the N most recent idle events."""
        return self.events[-n:]

    def get_summary(self) -> str:
        """Generate a 'while you were gone' summary."""
        if not self.events:
            return "Your buddies were quiet while you were away."

        lines = ["[bold]While you were coding...[/bold]", ""]
        for event in self.events[-8:]:  # Show last 8
            lines.append(f"  {event.buddy_emoji} {event.text}")

        total_gold = sum(e.gold_found for e in self.events)
        if total_gold > 0:
            lines.append(f"\n  [yellow]Total gold found: {total_gold}[/yellow]")

        return "\n".join(lines)

    def clear(self):
        """Clear all events (after showing summary)."""
        self.events.clear()
