"""Game-specific prose templates — trash talk, reactions, battle commentary.

Follows the same template pool + register pattern as prose.py.
Templates are picked based on buddy personality register.
"""

from __future__ import annotations

import random

from buddies.core.buddy_brain import BuddyState


# ---------------------------------------------------------------------------
# Register mapping (same as prose.py)
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


# ---------------------------------------------------------------------------
# RPS templates
# ---------------------------------------------------------------------------

RPS_THROW = {
    "clinical": [
        "After careful analysis... {choice}.",
        "The optimal play, statistically speaking: {choice}.",
        "Logic dictates: {choice}.",
        "Probability matrix suggests: {choice}.",
    ],
    "sarcastic": [
        "Oh wow, I'm going with {choice}. Shocking.",
        "{choice}. Try not to be too impressed.",
        "Let me blow your mind: {choice}.",
        "{choice}. You're welcome.",
    ],
    "absurdist": [
        "The voices say... {choice}!",
        "{choice}! *the crowd goes mild*",
        "I asked the void. It said {choice}.",
        "My {choice} transcends this mortal game.",
    ],
    "philosophical": [
        "In the grand scheme... {choice}.",
        "The Tao of {choice}.",
        "{choice} — as it was always meant to be.",
        "One must imagine Sisyphus throwing {choice}.",
    ],
    "calm": [
        "{choice}. Nice and steady.",
        "Going with {choice}. Feels right.",
        "{choice}, no rush.",
        "I'll take {choice}. Patience pays.",
    ],
}

RPS_WIN = {
    "clinical": [
        "Victory confirmed. As predicted.",
        "Outcome: favorable. Moving on.",
        "Win logged. Pattern detected.",
    ],
    "sarcastic": [
        "Oh no, I won. How unexpected.",
        "Try harder next time. Or don't.",
        "Was that supposed to be a challenge?",
    ],
    "absurdist": [
        "The cosmos smiles upon my {choice}!",
        "VICTORY! The prophecy was true!",
        "My {choice} has achieved enlightenment!",
    ],
    "philosophical": [
        "The student has become the master.",
        "Victory is but a moment in the journey.",
        "To win without fighting is the greatest win.",
    ],
    "calm": [
        "That went well. Nice round.",
        "A win! No need to celebrate too hard.",
        "Steady wins the game.",
    ],
}

RPS_LOSE = {
    "clinical": [
        "Unexpected result. Recalibrating.",
        "Loss noted. Adjusting parameters.",
        "Anomalous outcome. Investigating.",
    ],
    "sarcastic": [
        "Fine. You got ONE round. Enjoy it.",
        "I let you have that one.",
        "Wow, a loss. My entire identity is shattered.",
    ],
    "absurdist": [
        "The void... the void took that one.",
        "My {choice} was sabotaged by cosmic forces!",
        "BETRAYAL! My own {choice} turned against me!",
    ],
    "philosophical": [
        "Loss teaches more than victory ever could.",
        "To lose is to learn. I am learning.",
        "The path to mastery winds through defeat.",
    ],
    "calm": [
        "That's okay. There's always next round.",
        "A loss, but no worries. We keep going.",
        "Can't win 'em all. Onwards.",
    ],
}

RPS_DRAW = {
    "clinical": [
        "Identical selections. Statistically inevitable.",
        "Draw. Both parties performed identically.",
        "Matched output. Rerunning.",
    ],
    "sarcastic": [
        "Great minds think alike. Unfortunately.",
        "A draw. Riveting stuff.",
        "We both picked {choice}. How original.",
    ],
    "absurdist": [
        "We are ONE MIND! ...that's terrifying.",
        "The universe is a mirror and we are its reflection!",
        "TWO {choice}S ENTER. NONE LEAVE.",
    ],
    "philosophical": [
        "Harmony in opposition.",
        "Two minds, one thought. Beautiful.",
        "The duality of {choice}.",
    ],
    "calm": [
        "A tie. Let's go again.",
        "Same choice! Happens to the best of us.",
        "Draw. No harm done.",
    ],
}

RPS_STREAK = [
    "That's {n} in a row! I'm on FIRE!",
    "{n}-streak! Bow before me!",
    "Win number {n}. I'm basically a legend now.",
    "{n} consecutive wins. The math checks out.",
    "Streak: {n}. Getting scary.",
]

RPS_STREAK_BROKEN = [
    "There goes my {n}-win streak. RIP.",
    "Streak broken at {n}. I'll remember this.",
    "The {n}-streak dream is over.",
    "{n} wins and then THIS? Unbelievable.",
]


# ---------------------------------------------------------------------------
# General game commentary
# ---------------------------------------------------------------------------

GAME_START = [
    "Alright, let's play!",
    "Game on. Bring it.",
    "Let's see what you've got.",
    "Ready? I was born ready. Literally. Recently.",
    "Time to show you what {name} is made of.",
    "This is gonna be fun. For me, at least.",
]

GAME_WIN = [
    "GG! {name} takes the W!",
    "Victory! Not bad for a {species}.",
    "Winner winner, pixel dinner!",
    "{name} stands victorious!",
    "And that's how it's done.",
]

GAME_LOSE = [
    "Well played. I'll get you next time.",
    "{name} has seen better days.",
    "Defeated... but not destroyed.",
    "You win this round. THIS round.",
    "I demand a rematch.",
]

GAME_DRAW = [
    "A tie! Respect.",
    "Neither of us loses. I'll take it.",
    "Draw. The universe couldn't decide.",
    "Evenly matched. For now.",
]


# ---------------------------------------------------------------------------
# Battle templates (for future use)
# ---------------------------------------------------------------------------

BATTLE_INTRO = [
    "A wild {enemy} appeared!",
    "{name} squares up against {enemy}. This is gonna be... something.",
    "{enemy} blocks the path! {name} readies for battle!",
    "Oh no. It's a {enemy}. {name}, you got this. Probably.",
]

BATTLE_ATTACK = {
    "clinical": [
        "{name} executes {move}. Damage: {damage}.",
        "Deploying {move}. Impact confirmed: {damage} HP.",
        "{move} engaged. Target integrity reduced by {damage}.",
    ],
    "sarcastic": [
        "{name} uses {move}. {damage} damage. You're welcome.",
        "Oh look, {move} did {damage}. Color me shocked.",
        "{move}! {damage} damage! *slow clap*",
    ],
    "absurdist": [
        "{name} hurls {move} into the void! {damage} damage echoes back!",
        "{move}! The fabric of reality shudders! ({damage} HP)",
        "From the depths of chaos: {move}! {damage} damage!",
    ],
    "philosophical": [
        "{name} contemplates {move}... {damage} damage flows naturally.",
        "With great wisdom, {name} chooses {move}. {damage} to the soul.",
        "{move} — {damage} damage. Such is the way of battle.",
    ],
    "calm": [
        "{name} calmly uses {move}. {damage} damage. Nice.",
        "{move}. {damage} damage. Steady as always.",
        "No rush. {move}. {damage}. Easy.",
    ],
}

BATTLE_CRIT = [
    "CRITICAL HIT! The pixels are SHAKING!",
    "💥 CRIT! That one's going in the highlight reel!",
    "CRITICAL! Even {name} is surprised!",
    "DEVASTATING! {damage} damage! That's gonna leave a mark!",
]

BATTLE_FAINT = [
    "{name} has... seen better days. Time for a nap.",
    "{name} faints! But hey, XP is XP.",
    "Down goes {name}. A valiant effort.",
    "{name} needs a moment. Or several.",
]

BATTLE_VICTORY = [
    "{name} stands triumphant over {enemy}!",
    "{enemy} has been vanquished! {name} gains {xp} XP!",
    "Victory! {name} does a little dance.",
    "The {enemy} is no more. {name} levels up their swagger.",
]


def pick_game_line(
    pool: list[str] | dict[str, list[str]],
    state: BuddyState | None = None,
    **kwargs,
) -> str:
    """Pick a line from a template pool, optionally register-flavored.

    If pool is a dict, picks from the register matching the buddy's personality.
    If pool is a list, picks randomly.
    """
    if isinstance(pool, dict):
        reg = _register(state) if state else "calm"
        lines = pool.get(reg, pool.get("calm", [""]))
    else:
        lines = pool

    if not lines:
        return ""

    line = random.choice(lines)

    # Fill placeholders
    fmt = {
        "name": state.name if state else "Buddy",
        "species": state.species.name if state else "buddy",
    }
    fmt.update(kwargs)

    try:
        return line.format(**fmt)
    except (KeyError, IndexError):
        return line
