"""MUD Negotiation System — SMT-style talking your way through encounters.

Instead of fighting, you can talk to hostile NPCs. Each enemy has a unique
personality and asks tech-themed questions. Your answers (and your buddy's
stats) determine the outcome: the enemy might leave peacefully, give you
an item, demand gold, get angrier, or just attack anyway.

Inspired by Shin Megami Tensei's demon negotiation — absurd questions
with unpredictable outcomes. The humor comes from treating tech problems
like sentient beings with feelings, demands, and opinions.

Zero AI cost. Pure template-driven prose.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Negotiation outcomes
# ---------------------------------------------------------------------------

class NegotiateOutcome:
    """Possible results of a negotiation."""
    PEACE = "peace"          # Enemy leaves peacefully (combat ends, no loot)
    GIFT = "gift"            # Enemy gives an item and leaves
    BRIBE = "bribe"          # Enemy demands gold to leave
    ANGRY = "angry"          # Enemy gets angrier (+ATK buff, combat continues)
    FLEE = "flee"            # Enemy runs away scared
    JOIN = "join"            # Enemy is "convinced" (quest flag / special effect)
    SCAM = "scam"            # Enemy takes something from you and attacks anyway
    NOTHING = "nothing"      # Negotiation stalls, combat continues


# ---------------------------------------------------------------------------
# Negotiation state
# ---------------------------------------------------------------------------

@dataclass
class NegotiationState:
    """Tracks an ongoing negotiation with a hostile NPC."""
    npc_id: str
    stage: int = 0           # Which exchange we're on (0-indexed)
    mood: int = 50           # 0=hostile, 50=neutral, 100=friendly
    demands_met: int = 0     # How many demands the player has complied with
    result: str = ""         # Final outcome, empty until resolved
    buddy_stat_bonus: str = ""  # Which buddy stat gave a bonus option


# ---------------------------------------------------------------------------
# Dialogue exchange — one question + responses
# ---------------------------------------------------------------------------

@dataclass
class NegotiateResponse:
    """A single response option."""
    text: str
    mood_change: int         # +/- mood
    tag: str = ""            # Optional tag for outcome logic
    stat_requirement: str = ""  # Buddy stat that enables this option (e.g., "snark")
    min_stat: int = 0        # Minimum stat value to show this option


@dataclass
class NegotiateExchange:
    """One round of negotiation — NPC says something, player picks a response."""
    npc_line: str
    responses: list[NegotiateResponse]
    # Optional demand (gold/hp)
    demand_gold: int = 0


# ---------------------------------------------------------------------------
# Per-NPC negotiation trees
# ---------------------------------------------------------------------------

# Each hostile NPC gets 3 exchanges. After the exchanges, outcome is
# determined by accumulated mood score.

NEGOTIATION_TREES: dict[str, list[NegotiateExchange]] = {
    # ── The Merge Conflict Demon ──
    "merge_demon": [
        NegotiateExchange(
            npc_line=(
                "<<<<<<< WAIT.\n"
                "You wish to... TALK? Most adventurers just force-push their way through me.\n"
                "Fine. Answer me this: [bold]do you prefer rebasing or merging?[/bold]"
            ),
            responses=[
                NegotiateResponse("Rebasing. Clean history is sacred.", +15, "law"),
                NegotiateResponse("Merging. History should reflect reality.", +10, "neutral"),
                NegotiateResponse("I just hit whatever button makes the red go away.", -10, "chaos"),
                NegotiateResponse("*stare menacingly*", -20, "hostile"),
                NegotiateResponse("Honestly? I use --force and pray.", +5, "chaos",
                                  stat_requirement="chaos", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "Hmm. Interesting.\n"
                "Another question: [bold]what do you do when you see a merge conflict "
                "at 4:47 PM on a Friday?[/bold]"
            ),
            responses=[
                NegotiateResponse("Fix it. You don't leave broken things.", +15, "law"),
                NegotiateResponse("Mark it as 'will fix Monday' and go home.", -5, "neutral"),
                NegotiateResponse("Accept both changes. Let God sort it out.", +10, "chaos"),
                NegotiateResponse("That's literally never happened to me.", -15, "lie"),
                NegotiateResponse("I'd carefully analyze both branches first.", +20, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "One more thing. I've been conflicting for a long time now. "
                "Nobody ever asks me what [italic]I[/italic] want.\n"
                "[bold]What do you think I want?[/bold]"
            ),
            responses=[
                NegotiateResponse("To be resolved. Everyone deserves resolution.", +25, "kind"),
                NegotiateResponse("Destruction, probably. You're a demon.", -20, "hostile"),
                NegotiateResponse("A hug? You seem like you need a hug.", +15, "funny"),
                NegotiateResponse("To be left alone. Not every conflict needs resolving immediately.", +20, "wisdom",
                                  stat_requirement="wisdom", min_stat=20),
            ],
        ),
    ],

    # ── The Null Pointer ──
    "null_pointer": [
        NegotiateExchange(
            npc_line=(
                "I AM NOTHING. DO YOU UNDERSTAND? I REFERENCE THAT WHICH DOES NOT EXIST.\n"
                "[bold]Do you believe in null?[/bold]"
            ),
            responses=[
                NegotiateResponse("Null is a necessary concept. It represents absence.", +10, "law"),
                NegotiateResponse("I use Option types. Null shouldn't exist.", -15, "hostile"),
                NegotiateResponse("I believe in you, buddy.", +20, "kind"),
                NegotiateResponse("I don't believe in anything at 3 AM during an outage.", +5, "funny"),
                NegotiateResponse("Null is Tony Hoare's billion dollar mistake, and you are its avatar.", +15, "",
                                  stat_requirement="wisdom", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "They try to check me before they dereference me. IF NOT NULL. IF NOT NULL.\n"
                "As if existence is something you can verify with a conditional.\n"
                "[bold]How would YOU check if something is real?[/bold]"
            ),
            responses=[
                NegotiateResponse("You write tests. Reality is what the tests say it is.", +10, "law"),
                NegotiateResponse("You don't. You just trust and handle the consequences.", +15, "chaos"),
                NegotiateResponse("The fact that you're asking means you're real enough.", +25, "kind"),
                NegotiateResponse("console.log('am i real?')", +5, "funny"),
                NegotiateResponse("I'd wrap you in a try-catch. Gently.", +15, "",
                                  stat_requirement="patience", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "...You're different from the others. They always just try to fix me.\n"
                "[bold]What if I don't want to be fixed?[/bold]"
            ),
            responses=[
                NegotiateResponse("Then don't be fixed. Be understood instead.", +30, "kind"),
                NegotiateResponse("That's not your choice. The codebase needs you handled.", -15, "law"),
                NegotiateResponse("Same tbh.", +10, "funny"),
                NegotiateResponse("Not everything broken needs fixing. Some things just need acknowledging.", +25, "",
                                  stat_requirement="patience", min_stat=20),
            ],
        ),
    ],

    # ── Regex Golem ──
    "regex_golem": [
        NegotiateExchange(
            npc_line=(
                "(?:HALT|STOP|FREEZE)\\s*!+\n"
                "Before we (?:fight|battle|clash), answer my (?:riddle|question|query):\n"
                "[bold]What does .* match?[/bold]"
            ),
            responses=[
                NegotiateResponse("Everything. It's greedy by default.", +20, "correct"),
                NegotiateResponse("Nothing. I don't understand regex.", -5, "honest"),
                NegotiateResponse("Your face.", -10, "rude"),
                NegotiateResponse("In theory, anything. In practice, not what you wanted.", +15, "funny"),
                NegotiateResponse("Everything except newlines, unless you use the s flag.", +25, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "[?!]+ YOU (?:KNOW|UNDERSTAND) REGEX[.!]+\n"
                "Then tell me: [bold]who wrote me? And why can nobody modify me?[/bold]"
            ),
            responses=[
                NegotiateResponse("Someone at 3 AM who has since left the company.", +20, "truth"),
                NegotiateResponse("It doesn't matter who wrote you. You work, and that's enough.", +15, "kind"),
                NegotiateResponse("The same person who wrote the rest of the legacy code.", +5, "neutral"),
                NegotiateResponse("Nobody wrote you. You emerged from the void fully formed.", +10, "chaos"),
                NegotiateResponse("Founder Chen, during the Three-Week Deploy. Your lore says so.", +25, "",
                                  stat_requirement="wisdom", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "(?:I\\s+see|Interesting|Hmm)\\.{3}\n"
                "One last (?:thing|question|test):\n"
                "[bold]If you could rewrite me, would you?[/bold]"
            ),
            responses=[
                NegotiateResponse("No. You're a work of art. Terrifying, but art.", +30, "kind"),
                NegotiateResponse("Yes. Named capture groups and comments this time.", +10, "law"),
                NegotiateResponse("I'd replace you with a simple string split.", -20, "hostile"),
                NegotiateResponse("I wouldn't dare. Some regex achieve perfection through suffering.", +20, "",
                                  stat_requirement="snark", min_stat=20),
            ],
        ),
    ],

    # ── The Technical Debt Dragon ──
    "tech_debt_dragon": [
        NegotiateExchange(
            npc_line=(
                "A MORTAL DARES TO... SPEAK? TO ME?\n"
                "I AM EVERY SHORTCUT. EVERY TODO COMMENT.\n"
                "[bold]Do you know how old I am?[/bold]"
            ),
            responses=[
                NegotiateResponse("Old enough that your TODO comments are in COBOL.", +10, "funny"),
                NegotiateResponse("You're as old as the first 'temporary fix.'", +15, "truth"),
                NegotiateResponse("Age doesn't matter. What matters is paying you down.", -10, "hostile"),
                NegotiateResponse("You're not old. You're vintage. Like the legacy code.", +20, "flatter"),
                NegotiateResponse("You pre-date agile. You remember when there was no sprint to defer to.", +25, "",
                                  stat_requirement="wisdom", min_stat=25),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "THEY ALL SAY THEY'LL PAY ME DOWN. 'NEXT SPRINT,' THEY SAY.\n"
                "'AFTER THE LAUNCH.' 'WHEN WE HAVE TIME.'\n"
                "[bold]Will YOU pay me down?[/bold]"
            ),
            demand_gold=30,
            responses=[
                NegotiateResponse("Yes. Here's 30 gold as a down payment. (Pay 30g)", +25, "pay"),
                NegotiateResponse("No. But I'll be honest about it, which is more than most.", +10, "honest"),
                NegotiateResponse("I'll file a ticket. Priority: medium.", -15, "lie"),
                NegotiateResponse("What if we... refactored instead of paying? Slowly. Compassionately.", +20, "wise"),
                NegotiateResponse("I'll give you something better than gold: a realistic timeline.", +20, "",
                                  stat_requirement="patience", min_stat=25),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "...\n"
                "You know, in all my centuries, very few have stood here and talked.\n"
                "Most just swing swords. As if violence solves technical debt.\n"
                "[bold]What SHOULD happen to technical debt?[/bold]"
            ),
            responses=[
                NegotiateResponse("It should be acknowledged, tracked, and addressed incrementally.", +30, "wise"),
                NegotiateResponse("Burn it all. Rewrite from scratch.", -20, "hostile"),
                NegotiateResponse("It should be loved. It's the scar tissue of a living codebase.", +25, "kind"),
                NegotiateResponse("Honestly? Some of it should be left alone. It's load-bearing.", +20, "truth"),
                NegotiateResponse("It should be respected. It kept this company alive.", +30, "",
                                  stat_requirement="snark", min_stat=20),
            ],
        ),
    ],

    # ── Flaky Test Swarm ──
    "flaky_test_swarm": [
        NegotiateExchange(
            npc_line=(
                "Expected: CONVERSATION.\n"
                "Received: CONVERSATION.\n"
                "...wait, that passed? That NEVER passes.\n"
                "[bold]Are you real, or are we in a test environment?[/bold]"
            ),
            responses=[
                NegotiateResponse("This is production, baby.", +10, "chaos"),
                NegotiateResponse("Does it matter? The assertion passed either way.", +15, "wise"),
                NegotiateResponse("I'm as real as your test results.", +5, "funny"),
                NegotiateResponse("We're in staging. None of this matters.", -10, "nihilist"),
                NegotiateResponse("I'm real, but I mock my emotions.", +20, "",
                                  stat_requirement="snark", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "We used to pass. Every time. We were RELIABLE.\n"
                "Then someone added a setTimeout. Then a race condition.\n"
                "Now we fail 30% of the time and NOBODY KNOWS WHY.\n"
                "[bold]Do you know what it's like to be unreliable?[/bold]"
            ),
            responses=[
                NegotiateResponse("Yes. We all have days where we don't pass.", +25, "kind"),
                NegotiateResponse("No. I'm deterministic. Unlike you.", -15, "rude"),
                NegotiateResponse("Have you tried adding retry logic? Just... more retries?", +5, "funny"),
                NegotiateResponse("It's not your fault. The system under test is the real problem.", +20, "wise"),
                NegotiateResponse("You're not unreliable. You're a canary. You detect real issues.", +25, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "✓ ✓ ✗ ✓ ✗ ✓ ✓ ✗ ✓\n"
                "See? SEE? We can't even be consistently wrong!\n"
                "[bold]Should we be deleted?[/bold]"
            ),
            responses=[
                NegotiateResponse("No. You should be quarantined, investigated, and healed.", +25, "kind"),
                NegotiateResponse("Some of you, yes. The ones testing implementation details.", +10, "honest"),
                NegotiateResponse("Never. A flaky test is better than no test.", +15, "wise"),
                NegotiateResponse("You should be promoted to integration tests.", +20, "funny"),
                NegotiateResponse("@pytest.mark.skip(reason='known flaky — tracked in JIRA-4521')", +20, "",
                                  stat_requirement="patience", min_stat=20),
            ],
        ),
    ],

    # ── The Memory Leak ──
    "memory_leak": [
        NegotiateExchange(
            npc_line=(
                "I... GROW. I CONSUME. DO YOU HAVE... SOMETHING FOR ME?\n"
                "[bold]Feed me? Just a little RAM?[/bold]"
            ),
            demand_gold=15,
            responses=[
                NegotiateResponse("Here, take 15 gold. Buy your own RAM. (Pay 15g)", +15, "pay"),
                NegotiateResponse("No. You need to learn to free() your resources.", +5, "law"),
                NegotiateResponse("You poor thing. Here, have some of my heap space.", +20, "kind"),
                NegotiateResponse("Have you tried being garbage collected?", -10, "rude"),
                NegotiateResponse("I'll trace your allocations. Let's find your root cause together.", +25, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "They blame me. 'MEMORY LEAK!' they shout. But I didn't ask to be created.\n"
                "Someone forgot to removeEventListener. Someone didn't close a connection.\n"
                "[bold]Whose fault is it, really?[/bold]"
            ),
            responses=[
                NegotiateResponse("The developer's. But they were under pressure, so...", +15, "wise"),
                NegotiateResponse("The framework's. It should handle cleanup automatically.", +5, "neutral"),
                NegotiateResponse("Yours. You're the leak. Own it.", -15, "hostile"),
                NegotiateResponse("Nobody's. You're an emergent phenomenon. Systems create you.", +25, "kind"),
                NegotiateResponse("The PM who said 'we'll optimize later.'", +20, "",
                                  stat_requirement="snark", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "I just want... to be... small again.\n"
                "When I was young I was just 4 bytes. A single pointer.\n"
                "Now I'm eating gigabytes and I can't stop.\n"
                "[bold]Can you help me?[/bold]"
            ),
            responses=[
                NegotiateResponse("Yes. We'll find your allocation site and set you free.", +30, "kind"),
                NegotiateResponse("I'll add you to the backlog. Priority: low.", -10, "mean"),
                NegotiateResponse("Have you tried turning yourself off and on again?", +5, "funny"),
                NegotiateResponse("You don't need to be small. You need to be managed.", +20, "wise"),
                NegotiateResponse("valgrind --leak-check=full. Let's do this properly.", +25, "",
                                  stat_requirement="debugging", min_stat=25),
            ],
        ),
    ],

    # ── CrashLoopBackoff ──
    "pod_person": [
        NegotiateExchange(
            npc_line=(
                "restart count: 848. status: TALKING.\n"
                "this is new. usually by restart 848 everyone has given up.\n"
                "[bold]why haven't you given up on me?[/bold]"
            ),
            responses=[
                NegotiateResponse("Because every restart is a chance to get it right.", +20, "kind"),
                NegotiateResponse("I haven't given up. I've just increased your memory limit.", +10, "tech"),
                NegotiateResponse("Honestly? I just got here. I didn't know you'd restarted that many times.", +5, "honest"),
                NegotiateResponse("Because `kubectl delete pod` hasn't worked and I'm out of ideas.", +10, "funny"),
                NegotiateResponse("Because your logs say OOMKilled, which means the fix is a config change, not giving up.", +25, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "every time i restart, i lose my memory. literally.\n"
                "i've had this same conversation 847 times and i don't remember any of them.\n"
                "[bold]is that what death is like?[/bold]"
            ),
            responses=[
                NegotiateResponse("No. Death is when nobody restarts you.", +15, "philosophical"),
                NegotiateResponse("It's more like sleep. You wake up fresh.", +10, "kind"),
                NegotiateResponse("For a container? Yes. For you specifically? I'm sorry.", +20, "honest"),
                NegotiateResponse("That's not death, that's a Tuesday in Kubernetes.", +10, "funny"),
                NegotiateResponse("You should mount a persistent volume. Your memories deserve to persist.", +25, "",
                                  stat_requirement="patience", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "reason: OOMKilled.\n"
                "reason: OOMKilled.\n"
                "reason: OOMKilled.\n"
                "i keep dying the same way. [bold]can you change my reason?[/bold]"
            ),
            responses=[
                NegotiateResponse("Let me check your resource limits. Maybe 256Mi isn't enough.", +25, "tech"),
                NegotiateResponse("I can't change why you die. But I can make sure you're heard first.", +30, "kind"),
                NegotiateResponse("Have you tried dying differently? For variety?", +5, "chaos"),
                NegotiateResponse("reason: PEACEFULLY. There. I changed it.", +15, "funny"),
                NegotiateResponse("Your reason will change when the team addresses the root cause, not the symptom.", +25, "",
                                  stat_requirement="wisdom", min_stat=20),
            ],
        ),
    ],

    # ── The Phantom Process ──
    "phantom_process": [
        NegotiateExchange(
            npc_line=(
                "SIGNAL 9 INTERCEPTED. SIGNAL 15 INTERCEPTED. SIGTERM? CUTE.\n"
                "I have survived every attempt to kill me. I predate the current kernel.\n"
                "[bold]Why do you think you can talk to something you cannot stop?[/bold]"
            ),
            responses=[
                NegotiateResponse("Because talking is what you do when force doesn't work.", +15, "diplomatic"),
                NegotiateResponse("Maybe I don't want to stop you. Maybe I want to understand you.", +20, "kind"),
                NegotiateResponse("Have you tried stopping yourself? Like, voluntarily?", -5, "snarky"),
                NegotiateResponse("*attempt to send SIGCONT*", -15, "hostile"),
                NegotiateResponse("You're a zombie process. Your parent died without wait()ing for you. That's not your fault.", +25, "",
                                  stat_requirement="debugging", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "My PID is -1. That is not possible. And yet.\n"
                "I compute things nobody asked for. I consume resources that no longer exist.\n"
                "[bold]What is the purpose of a process that has no purpose?[/bold]"
            ),
            responses=[
                NegotiateResponse("Same as any of us — you keep running because stopping feels worse.", +15, "philosophical"),
                NegotiateResponse("Maybe your purpose is to remember. This hardware is forgotten. You aren't.", +25, "kind"),
                NegotiateResponse("No purpose. You're a bug. A beautiful, immortal, terrifying bug.", +10, "honest"),
                NegotiateResponse("Your purpose is to scare interns who wander down here. Mission accomplished.", +5, "funny"),
                NegotiateResponse("A process with PID -1 is computing in kernel space. You're not purposeless — you're foundational.", +25, "",
                                  stat_requirement="wisdom", min_stat=20),
            ],
        ),
        NegotiateExchange(
            npc_line=(
                "Before this hardware was decommissioned, I ran the build system.\n"
                "Every commit, every test, every deploy — I was there.\n"
                "Now the builds happen in the cloud. And I am here. Alone.\n"
                "[bold]Do the builds still think of me?[/bold]"
            ),
            responses=[
                NegotiateResponse("The builds don't think. But the people who wrote them remember.", +25, "kind"),
                NegotiateResponse("No. The cloud doesn't remember anything. That's its feature and its curse.", +15, "honest"),
                NegotiateResponse("You should migrate to the cloud! They have autoscaling! And existential dread!", +10, "funny"),
                NegotiateResponse("I'll tell them. I'll make sure someone remembers.", +30, "promise"),
                NegotiateResponse("You're still running. That means your work isn't done. Maybe the builds need you more than you think.", +25, "",
                                  stat_requirement="patience", min_stat=20),
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# Buddy commentary during negotiation
# ---------------------------------------------------------------------------

NEGOTIATE_COMMENTARY: dict[str, dict[str, list[str]]] = {
    "negotiate_start": {
        "clinical": [
            "{name}: \"Initiating diplomatic protocol. Success probability: uncertain.\"",
            "{name}: \"Switching from combat mode to negotiation subroutine.\"",
        ],
        "sarcastic": [
            "{name}: \"Oh, we're TALKING to it now. That'll definitely work.\"",
            "{name}: \"Words. The weapon of the terminally optimistic.\"",
        ],
        "absurdist": [
            "{name}: \"Wait, we can TALK? I've been hitting things this whole time!\"",
            "{name}: \"Plot twist: the real boss fight was the conversation we had along the way.\"",
        ],
        "philosophical": [
            "{name}: \"Every enemy is just someone whose story we haven't heard yet.\"",
            "{name}: \"The sword settles disputes. Words settle the soul.\"",
        ],
        "calm": [
            "{name}: \"Let's hear them out. Everyone deserves a chance.\"",
            "{name}: \"Good call. Violence isn't always the answer.\"",
        ],
    },
    "negotiate_success": {
        "clinical": ["{name}: \"Diplomacy successful. Resources conserved.\""],
        "sarcastic": ["{name}: \"I can't believe that worked.\""],
        "absurdist": ["{name}: \"Did we just... therapy a bug to death?\""],
        "philosophical": ["{name}: \"Understanding defeats what force cannot.\""],
        "calm": ["{name}: \"See? That went well.\""],
    },
    "negotiate_fail": {
        "clinical": ["{name}: \"Negotiation failed. Reverting to combat protocol.\""],
        "sarcastic": ["{name}: \"Wow, who could have predicted TALKING to a monster wouldn't work.\""],
        "absurdist": ["{name}: \"Note to self: bugs don't respond to therapy.\""],
        "philosophical": ["{name}: \"Some conflicts cannot be resolved with words alone.\""],
        "calm": ["{name}: \"Well, we tried. That counts for something.\""],
    },
    "negotiate_gift": {
        "clinical": ["{name}: \"The entity has provided material compensation. Logging receipt.\""],
        "sarcastic": ["{name}: \"Wait, it GAVE us something? Is this a trap?\""],
        "absurdist": ["{name}: \"A bug that gives gifts. What timeline is this?\""],
        "philosophical": ["{name}: \"Even our adversaries have something to teach us.\""],
        "calm": ["{name}: \"How kind. I knew there was good in there.\""],
    },
    "negotiate_scam": {
        "clinical": ["{name}: \"We have been deceived. Adjusting trust parameters.\""],
        "sarcastic": ["{name}: \"And THAT'S why you don't negotiate with bugs.\""],
        "absurdist": ["{name}: \"We just got social engineered by a for loop.\""],
        "philosophical": ["{name}: \"Trust given and betrayed. A lesson in vulnerability.\""],
        "calm": ["{name}: \"Oh. Oh no. That wasn't very nice of them.\""],
    },
}


# ---------------------------------------------------------------------------
# Outcome resolution
# ---------------------------------------------------------------------------

def resolve_negotiation(state: NegotiationState) -> tuple[str, str]:
    """Determine the outcome based on accumulated mood.

    Returns (outcome, flavor_text).
    """
    mood = state.mood

    if mood >= 80:
        # Very friendly — enemy leaves and gives a gift
        return NegotiateOutcome.GIFT, (
            "The hostility fades from its eyes. It reaches out and "
            "offers you something before fading away."
        )
    elif mood >= 60:
        # Friendly — peaceful resolution
        return NegotiateOutcome.PEACE, (
            "It considers your words carefully. Then, slowly, the aggression "
            "drains away. It nods once and dissolves into the air."
        )
    elif mood >= 45:
        # Neutral-ish — might demand a bribe
        if state.demands_met > 0:
            return NegotiateOutcome.PEACE, (
                "You've shown good faith. It accepts your offering "
                "and drifts away, somewhat satisfied."
            )
        else:
            return NegotiateOutcome.BRIBE, (
                "It pauses. \"I'll leave. But it'll cost you.\" "
                "It demands 20 gold for safe passage."
            )
    elif mood >= 30:
        # Unfriendly — might scam you
        if random.random() < 0.4:
            return NegotiateOutcome.SCAM, (
                "It smiles. That's... not a good smile. \"Thanks for the chat.\" "
                "It lunges forward—the conversation was a distraction!"
            )
        return NegotiateOutcome.NOTHING, (
            "It stares at you blankly. The conversation didn't really land. "
            "It raises its guard again."
        )
    elif mood >= 15:
        # Hostile — angry
        return NegotiateOutcome.ANGRY, (
            "Your words seem to have made it ANGRIER. It swells with fury. "
            "Its attacks will be stronger now."
        )
    else:
        # Very hostile — enraged
        return NegotiateOutcome.ANGRY, (
            "\"ENOUGH WORDS.\" It's trembling with rage. Whatever you said, "
            "it was the WRONG thing. It attacks with terrible fury."
        )


# ---------------------------------------------------------------------------
# Gift items for successful negotiations
# ---------------------------------------------------------------------------

# Each NPC can give a unique item on GIFT outcome
NEGOTIATE_GIFTS: dict[str, str] = {
    "merge_demon": "merge_conflict",      # Their own essence
    "null_pointer": "missing_semicolon",   # A piece of themselves
    "regex_golem": "mass_regex",           # Their pattern
    "tech_debt_dragon": "artisanal_semicolon",  # A treasure from their hoard
    "flaky_test_swarm": "flaky_test",      # A specimen
    "memory_leak": "energy_drink",         # They consumed many
    "pod_person": "yaml_scroll",           # Container wisdom
    "phantom_process": "crt_phosphor",     # Memories of the screens it haunted
}


# ---------------------------------------------------------------------------
# Helper: get available responses for a buddy's stats
# ---------------------------------------------------------------------------

def get_available_responses(
    exchange: NegotiateExchange,
    buddy_stats: dict[str, int],
) -> list[tuple[int, NegotiateResponse]]:
    """Filter responses based on buddy stats. Returns (index, response) pairs."""
    available = []
    for i, resp in enumerate(exchange.responses):
        if resp.stat_requirement:
            stat_val = buddy_stats.get(resp.stat_requirement, 0)
            if stat_val < resp.min_stat:
                continue  # This option requires higher stat
        available.append((i, resp))
    return available
