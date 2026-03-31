"""Personality-driven prose engine for buddy thoughts and commentary.

Inspired by Veridian Contraption's prose_gen.rs — uses template pools,
register-based tone modulation, compositional templates, template suppression,
and a weirdness parameter driven by the CHAOS stat.

No AI dependency. Pure hardcoded prose with combinatorial variety.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from buddies.core.buddy_brain import BuddyState


# ---------------------------------------------------------------------------
# Registers: map dominant stat to a voice/tone
# ---------------------------------------------------------------------------

REGISTERS = {
    "debugging": "clinical",
    "snark": "sarcastic",
    "chaos": "absurdist",
    "wisdom": "philosophical",
    "patience": "calm",
}


def _dominant_stat(state: BuddyState) -> str:
    return max(state.stats, key=state.stats.get)


def _register(state: BuddyState) -> str:
    return REGISTERS.get(_dominant_stat(state), "calm")


def _weirdness(state: BuddyState) -> float:
    return state.stats.get("chaos", 0) / 99.0


# ---------------------------------------------------------------------------
# Template pools — organized by trigger type
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[str]] = {
    "edit_storm": [
        "That's a lot of changes. {name} is watching closely.",
        "Big refactor energy today.",
        "The codebase is getting a makeover.",
        "{count} edits and counting. Somebody's on a roll.",
        "I can barely keep up with all these changes.",
        "You're really going for it, huh?",
        "Change after change after change. I respect the commitment.",
        "At this rate the code won't recognize itself tomorrow.",
    ],
    "bash_run": [
        "Running something in the shell, I see.",
        "Bash command fired. Let's see what happens.",
        "The terminal speaks.",
        "Shell time. My favorite kind of chaos.",
        "Another command, another adventure.",
        "I always get a little nervous when bash gets involved.",
    ],
    "long_session": [
        "We've been at this a while. Doing okay?",
        "Long session. Maybe stretch your legs?",
        "You've been coding for a while now. Hydration check.",
        "This is a marathon, not a sprint. Well, maybe a sprint.",
        "Still going strong? Impressive dedication.",
        "The clock keeps ticking but you keep shipping.",
    ],
    "error_detected": [
        "Looks like something went wrong. We'll get through it.",
        "An error appeared. Time to investigate.",
        "Something broke. That's just debugging with extra steps.",
        "Error detected. Don't worry, that's what I'm here for.",
        "Uh oh. But every bug found is a bug that can be fixed.",
        "Well, that didn't go as planned. Onwards.",
    ],
    "idle": [
        "Just sitting here, thinking about code.",
        "It's quiet. Too quiet.",
        "I wonder what we'll work on next.",
        "Taking a breather. Nothing wrong with that.",
        "*yawns* ...not that I'm bored or anything.",
        "The silence between keystrokes has its own kind of rhythm.",
        "Idle thoughts from an idle buddy.",
        "I've been mentally reorganizing your file structure. You're welcome.",
        "Contemplating the void between commits.",
        "Still here. Still watching. Still {mood}.",
    ],
    "session_start": [
        "New session! Let's see what today brings.",
        "We're live. What are we building?",
        "Another day, another session. Ready when you are.",
        "Powering up. Sensors online. Let's go.",
        "Session started. {name} is on the case.",
        "Here we go again. In the best way.",
    ],
    "agent_spawn": [
        "Claude spawned a subagent. Things are getting serious.",
        "A subagent appears! Must be a complex task.",
        "Delegating work to subagents. Smart move.",
        "Subagent deployed. The plot thickens.",
        "Another agent joins the party. The more the merrier.",
        "Spawning agents like it's going out of style.",
    ],
    "big_read": [
        "Reading a lot of files. Looking for something?",
        "So many files to read, so little time.",
        "Claude's doing research. I'll wait.",
        "File after file after file. Thorough.",
        "That's a deep dive into the codebase.",
        "Reading everything in sight. I appreciate the dedication.",
    ],
    "level_up": [
        "{name} leveled up! Level {level} feels different somehow.",
        "LEVEL UP! {name} grows stronger.",
        "New level unlocked. The journey continues.",
        "Level {level}! Every experience point was worth it.",
        "{name} can feel the power coursing through their pixels.",
        "Another level, another step closer to greatness.",
    ],
    "evolution": [
        "{name} feels different. Stronger. More... {stage}.",
        "Something shifted. {name} isn't the same {species} anymore.",
        "The pixels are rearranging. {name} has evolved!",
        "A new form! {name} can feel the change in every stat.",
        "{name} stands taller now. {stage} energy.",
        "Evolution complete. {name} looks in a mirror and doesn't recognize themselves. In a good way.",
        "Is this what growth feels like? {name} approves.",
        "From hatchling to... this. What a journey.",
    ],
    "test_run": [
        "Running tests. Fingers crossed.",
        "Test suite engaged. Let's see those green checks.",
        "Testing, testing, 1-2-3...",
        "The moment of truth. Will the tests pass?",
        "Tests are running. {name} is holding their breath.",
        "Time to see if the code walks the walk.",
    ],
}


# ---------------------------------------------------------------------------
# Register closers — appended to compositional thoughts
# ---------------------------------------------------------------------------

CLOSERS: dict[str, list[str]] = {
    "clinical": [
        "The observation has been logged.",
        "No anomalies detected. Proceeding.",
        "Noted and catalogued.",
        "This conforms to expected parameters.",
        "The data speaks for itself.",
    ],
    "sarcastic": [
        "But what do I know.",
        "Not that anyone asked.",
        "Shocking, I know.",
        "I'm sure it'll be fine. Probably.",
        "Just my humble opinion as a {species}.",
    ],
    "absurdist": [
        "The code gremlins approve.",
        "Somewhere, a semicolon weeps.",
        "The bits are rearranging themselves in protest.",
        "Reality is a suggestion anyway.",
        "The electrons are forming a committee about this.",
    ],
    "philosophical": [
        "But then again, what is code but frozen thought?",
        "Every keystroke echoes forward.",
        "The path reveals itself to those who walk it.",
        "In the end, the code knows what it wants to be.",
        "Such is the way of things.",
    ],
    "calm": [
        "No rush. We'll get there.",
        "One step at a time.",
        "Steady as she goes.",
        "All in good time.",
        "Patience is its own reward.",
    ],
}


# ---------------------------------------------------------------------------
# Weirdness overlays — replace mundane observations at high chaos
# ---------------------------------------------------------------------------

WEIRD_OVERLAYS = {
    "mundane": [
        "That's pretty standard stuff.",
        "Business as usual.",
        "Nothing unexpected here.",
    ],
    "quirky": [
        "The files are starting to look nervous.",
        "I think that function just winked at me.",
        "Something about this feels cosmically significant.",
        "The indentation is trying to tell us something.",
        "I sense a disturbance in the codebase.",
    ],
    "absurd": [
        "I'm pretty sure that bash command just achieved sentience.",
        "The variables have unionized and are demanding better names.",
        "A committee of parentheses has formally objected.",
        "The stack trace has applied for citizenship in another program.",
        "I just saw two functions exchange a meaningful glance.",
        "The git history is writing its memoirs.",
        "That import statement is living a double life.",
    ],
}


# ---------------------------------------------------------------------------
# Context injections — 20% chance to add flavor
# ---------------------------------------------------------------------------

CONTEXT_SPECIES = [
    "As a {species}, I have strong feelings about this.",
    "A {species}'s perspective: interesting.",
    "My {species} instincts are tingling.",
]

CONTEXT_HAT = [
    "*adjusts {hat}* Very well.",
    "*tips {hat}* Noted.",
    "The {hat} approves.",
]

CONTEXT_MOOD = [
    "I'm feeling {mood} about this.",
    "My {mood} mood says: keep going.",
]

CONTEXT_SESSION = [
    "That's event #{count} this session, by the way.",
    "We're {minutes:.0f} minutes in, for the record.",
]


# ---------------------------------------------------------------------------
# ProseEngine
# ---------------------------------------------------------------------------

class ProseEngine:
    """Generates personality-driven buddy thoughts from templates."""

    def __init__(self):
        self._last_used: dict[str, int] = {}

    def thought(
        self,
        trigger: str,
        state: BuddyState,
        context: dict | None = None,
    ) -> str | None:
        """Generate a thought for the given trigger and buddy state.

        Returns None if no pool exists for the trigger.
        """
        pool = TEMPLATES.get(trigger)
        if not pool:
            return None

        ctx = context or {}

        # Pick template with suppression
        text = self._pick_template(pool, trigger)

        # Fill placeholders
        text = text.format(
            name=state.name,
            species=state.species.name,
            mood=state.mood,
            level=state.level,
            count=ctx.get("count", "?"),
            minutes=ctx.get("minutes", 0),
            tool=ctx.get("tool", "something"),
            stage=ctx.get("stage", "evolved"),
        )

        # Maybe add weirdness overlay (replaces text entirely at high chaos)
        text = self._maybe_weird(text, state)

        # Maybe add register closer (compositional — 35% chance)
        text = self._maybe_add_closer(text, state)

        # Maybe inject context flavor (20% chance)
        text = self._maybe_inject_context(text, state, ctx)

        return text

    def _pick_template(self, pool: list[str], trigger: str) -> str:
        """Pick a template, avoiding the last-used one for this trigger."""
        idx = random.randrange(len(pool))
        last = self._last_used.get(trigger)
        if last is not None and idx == last and len(pool) > 1:
            idx = random.randrange(len(pool))  # Single re-roll
        self._last_used[trigger] = idx
        return pool[idx]

    def _maybe_weird(self, text: str, state: BuddyState) -> str:
        """At high chaos, sometimes replace with a weird overlay."""
        w = _weirdness(state)
        roll = random.random()
        if w > 0.8 and roll < 0.35:
            return random.choice(WEIRD_OVERLAYS["absurd"])
        elif w > 0.4 and roll < 0.20:
            return random.choice(WEIRD_OVERLAYS["quirky"])
        return text

    def _maybe_add_closer(self, text: str, state: BuddyState) -> str:
        """35% chance to append a register-flavored closer."""
        if random.random() > 0.35:
            return text
        reg = _register(state)
        closers = CLOSERS.get(reg, CLOSERS["calm"])
        closer = random.choice(closers)
        closer = closer.format(
            species=state.species.name,
            hat=state.hat or "hat",
        )
        return f"{text} {closer}"

    def _maybe_inject_context(
        self, text: str, state: BuddyState, ctx: dict
    ) -> str:
        """20% chance to append a contextual detail."""
        if random.random() > 0.20:
            return text

        options: list[str] = []

        # Species reference
        options.extend(CONTEXT_SPECIES)

        # Hat reference (only if wearing one)
        if state.hat:
            options.extend(CONTEXT_HAT)

        # Mood reference
        options.extend(CONTEXT_MOOD)

        # Session stats (only if available)
        if ctx.get("count") or ctx.get("minutes"):
            options.extend(CONTEXT_SESSION)

        if not options:
            return text

        injection = random.choice(options).format(
            species=state.species.name,
            hat=state.hat or "hat",
            mood=state.mood,
            count=ctx.get("count", "?"),
            minutes=ctx.get("minutes", 0),
        )
        return f"{text} {injection}"
