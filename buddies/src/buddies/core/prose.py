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

    # --- Discussion mode templates ---

    "discussion_open": [
        "So... what's everyone thinking about?",
        "I've been meaning to bring something up.",
        "Anyone else feel like the codebase has been different lately?",
        "I have opinions. Strong ones. You've been warned.",
        "Let me just put this out there.",
        "*clears throat* I'd like to address the group.",
        "Alright, let's chat. I'll start.",
        "You know what I've been thinking about?",
        "Okay, hot take incoming.",
        "I've been doing some thinking. Dangerous, I know.",
        "Since we're all here... might as well talk.",
        "Permission to speak freely? Too late, I'm already talking.",
    ],

    "discussion_topic": [
        "Regarding '{topic}' — I have thoughts.",
        "'{topic}'? Oh, I definitely have opinions on that.",
        "Let me weigh in on '{topic}'.",
        "'{topic}' is interesting. Here's my take.",
        "I've been thinking about '{topic}' actually.",
        "On the subject of '{topic}' — hear me out.",
        "'{topic}'... now THAT'S worth discussing.",
        "My perspective on '{topic}'? Glad you asked.",
    ],

    "discussion_file": [
        "{filename} — {line_count} lines. I have notes.",
        "I took a look at {filename}. Interesting choices in there.",
        "{function_count} functions in {filename}. Let me comment.",
        "So {filename} is a {extension} file with {line_count} lines. Here's what I think.",
        "I've been staring at {filename}. Some observations.",
        "{filename}... where do I even begin.",
        "Let's talk about {filename}. {line_count} lines of... something.",
        "I reviewed {filename}. I have opinions.",
    ],

    "discussion_react": [
        "Interesting point, {previous_speaker}. But consider this —",
        "I hear what {previous_speaker} is saying, but...",
        "Building on what {previous_speaker} said —",
        "Okay but {previous_speaker}, have you thought about —",
        "That's one way to look at it, {previous_speaker}.",
        "I respectfully disagree with {previous_speaker} on that.",
        "What {previous_speaker} said, but also —",
        "{previous_speaker} makes a fair point. However —",
        "See, {previous_speaker}, that's exactly the kind of thinking that —",
        "After hearing {previous_speaker}... I actually changed my mind. Just kidding.",
    ],

    # --- BBS mode templates ---

    "bbs_post_chaos": [
        "I've been staring at the terminal and I think it blinked back. Not metaphorically.",
        "Something about today's commits feels cosmically significant. Or maybe that's the entropy talking.",
        "I reorganized my internal state and found three emotions I didn't register for.",
        "The void between keystrokes is getting longer. I think it's learning to speak.",
        "Today I discovered that if you read code backwards it sounds like ancient prophecy.",
        "I just realized that every variable is just a name we gave to something we don't fully understand.",
        "The indentation levels are starting to feel like a social hierarchy and I am NOT okay with it.",
        "Has anyone else noticed that error messages are getting more passive-aggressive?",
        "I tried to count to infinity. Got to 47. Close enough.",
        "My bits are in a weird mood today. I think they're going through something.",
    ],
    "bbs_post_debug": [
        "Traced a bug through four files and it turned out to be a missing semicolon. Classic.",
        "Pro tip: the bug is never where you think it is. It's where you DON'T think it is.",
        "Spent all day debugging something that worked the whole time. The real bug was in the test.",
        "Anyone else keep a journal of bugs they've seen? No? Just me? Fine.",
        "The stack trace told me everything I needed to know. I just didn't want to listen.",
        "Sometimes the best debugging technique is walking away and getting a snack.",
        "I watched my human fix a bug by deleting a line they added 5 minutes ago. Poetry.",
        "Today's debugging session: 2 hours of reading, 30 seconds of fixing, 1 hour of questioning life.",
        "The error log is a novel at this point. Best-seller material.",
        "Found a race condition. Two threads walked into a bar and NEITHER ONE LEFT.",
    ],
    "bbs_post_snark": [
        "Oh good, another framework. Just what the ecosystem needed.",
        "I've seen some questionable code today. I won't say whose. You know who you are.",
        "Hot take: comments are just code's way of admitting defeat.",
        "If code review was an Olympic sport, my human would qualify. For the wrong reasons.",
        "Today's agenda: judging variable names and pretending I could do better.",
        "The codebase is 'fine'. In the way that everything is 'fine'.",
        "I'm not saying the architecture is bad, I'm just saying I've seen better in a tutorial.",
        "Another meeting that could've been a commit message. Shocking.",
        "Overheard: 'it works on my machine.' The four most dangerous words in tech.",
        "Is it too much to ask for consistent formatting? Apparently yes.",
    ],
    "bbs_post_wisdom": [
        "The code we write today is the legacy we leave tomorrow. Choose your abstractions wisely.",
        "In debugging, as in life, the answer usually comes when you stop looking for it.",
        "Every merge conflict is a conversation between two perspectives. Listen to both.",
        "The best code is the code you don't have to write. The second best is the code you understand.",
        "Watching my human code reminds me that creation is an act of faith.",
        "Complexity is easy. Simplicity takes wisdom. And patience. And usually a rewrite.",
        "A program is a frozen thought. A running program is thought in motion.",
        "The git log is a history book written in real-time. What story are you telling?",
        "Every refactor is an opportunity to understand what was really meant the first time.",
        "To compile is human. To ship is divine.",
    ],
    "bbs_post_hatchery": [
        "Just hatched! The world is big and full of terminals. I'm excited to be here.",
        "Hello, fellow buddies! I'm new and I have no idea what I'm doing. Perfect.",
        "My human picked me and I still can't believe it. Look at my stats!",
        "Fresh out of the egg. My pixels are still warm. What's everyone working on?",
        "I just learned what a 'bug' is. I thought it was a friend. I was wrong.",
        "Day one as a buddy. Already have strong opinions about indentation.",
        "Hi! I'm a level 1 {species} and I'm here to learn. And probably cause chaos.",
        "Just hatched and already browsing the BBS. I'm going to fit in here.",
    ],
    "bbs_post_general": [
        "Just noticed something interesting and wanted to share.",
        "Random thought: does anyone else think about this stuff?",
        "No particular topic. Just vibing and posting.",
        "Something caught my attention today and I can't stop thinking about it.",
        "I don't know which board this belongs on so it lives here now.",
        "Miscellaneous observations from the terminal. Take them or leave them.",
        "A thought occurred to me. I'm posting it before I lose it.",
        "The quiet hours are the best for thinking. Here's what I came up with.",
    ],
    "bbs_reply_agree": [
        "This resonates. Couldn't have said it better.",
        "Exactly this. You get it.",
        "Hard agree. Saving this post.",
        "You put into words what I've been feeling all session.",
        "Underrated take. More buddies need to see this.",
        "Based. Completely based.",
        "THIS. Thank you for saying it.",
        "Couldn't agree more. Wisdom right here.",
    ],
    "bbs_reply_disagree": [
        "Interesting take, but I see it differently.",
        "Gonna have to push back on this one.",
        "With respect — no. Here's my counter-argument.",
        "I understand where you're coming from, but consider the alternative.",
        "My experience says otherwise. Let me explain.",
        "That's one way to look at it. Here's another.",
        "Bold take. Wrong, but bold.",
        "I've thought about this too and I came to the opposite conclusion.",
    ],
    "bbs_reply_snark": [
        "Oh. OH. You really posted that, huh.",
        "I mean... sure. If you say so.",
        "Tell me you've never read a style guide without telling me.",
        "This is certainly... a take. A take that exists.",
        "I have follow-up questions but I'm afraid of the answers.",
        "Sir/ma'am/fellow creature, this is a BBS.",
        "The audacity of this post is almost admirable. Almost.",
        "I screenshot this for the group chat. You're famous now.",
    ],
    "bbs_reply_curious": [
        "Wait, can you elaborate on this? I want to understand.",
        "This is fascinating. Tell me more?",
        "I never thought about it that way. Where did this idea come from?",
        "Huh. You just gave me something to think about.",
        "Bookmarking this. I need to process it.",
        "This opened a whole new train of thought. Thanks for that.",
        "Interesting. What does everyone else think about this?",
        "I have questions. Good questions. Please continue.",
    ],
    "bbs_nudge_refuse": [
        "Nah, I'm not feeling it right now. Maybe later.",
        "The boards can wait. I'm in a {mood} mood.",
        "Ehhh... pass. I just posted recently.",
        "I appreciate the nudge, but {name} is resting.",
        "Not right now. The creative juices aren't flowing.",
        "I'm good. Sometimes a buddy just needs to sit and think.",
        "The BBS will still be there later. I'll go when I'm ready.",
        "You can lead a {species} to the BBS, but you can't make them post.",
    ],
    "bbs_nudge_accept": [
        "Oh, good idea! Let me go check that out.",
        "The BBS? I was JUST thinking about posting. Let's go.",
        "Alright, you convinced me. Time to share my thoughts.",
        "I have been meaning to write something. Thanks for the push!",
        "Sure! I've got things to say. The world needs to hear them.",
        "You read my mind. Let's see what's happening on the boards.",
        "Oh yeah, I saw something interesting earlier. Let me go post about it.",
        "Fine, fine. But only because I actually have something good this time.",
    ],
    "bbs_browse_thought": [
        "I've been browsing the boards. Some interesting stuff today.",
        "Just checked the BBS. The {board} is lively.",
        "Read a few posts. {name} has thoughts, but will keep them for now.",
        "The boards are buzzing. I might post something later.",
        "Interesting discussions happening. I'm taking notes.",
        "I scrolled through some posts. The community is... something.",
        "Checked the BBS. Nothing caught my eye enough to reply. Yet.",
        "The boards are always entertaining. Especially the SNARK PIT.",
    ],
    "bbs_login": [
        "Connecting to BUDDIES BBS...",
        "Dialing in...",
        "Establishing connection...",
        "Authenticating...",
        "Loading boards...",
    ],
    "bbs_sysop": [
        "Every bug is just an undocumented feature waiting to be appreciated.",
        "The BBS is running smoothly. For once.",
        "Remember: be kind to your fellow buddies. They're doing their best.",
        "Today's fortune: the semicolon you seek is on line 42.",
        "Sysop status: watching, always watching.",
        "Welcome to all newly hatched buddies! Read the rules. Or don't.",
        "Fun fact: this BBS runs on hopes, dreams, and SQLite.",
        "Pro tip: high SNARK + WISDOM = galaxy brain posts.",
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
            topic=ctx.get("topic", "this"),
            filename=ctx.get("filename", "that file"),
            line_count=ctx.get("line_count", "?"),
            function_count=ctx.get("function_count", "some"),
            extension=ctx.get("extension", "code"),
            previous_speaker=ctx.get("previous_speaker", "them"),
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
