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


# ---------------------------------------------------------------------------
# Pong templates
# ---------------------------------------------------------------------------

PONG_SCORE_PLAYER = {
    "clinical": [
        "Point conceded. Recalculating trajectory model.",
        "Missed. Adjusting paddle algorithm by 0.3 units.",
        "Error in prediction. Won't happen again. Probably.",
    ],
    "sarcastic": [
        "Fine, you got one past me. Savor it.",
        "Oh wow, a point. I'm devastated. Can you tell?",
        "Lucky shot. That's my story and I'm sticking to it.",
    ],
    "absurdist": [
        "The ball has BETRAYED me! I trusted that ball!",
        "Physics itself conspired against me!",
        "That point exists in a dimension I refuse to acknowledge.",
    ],
    "philosophical": [
        "To miss is to learn the value of precision.",
        "The ball went where it needed to go.",
        "Every missed point is a step toward enlightenment.",
    ],
    "calm": [
        "Nice shot. We keep going.",
        "You got that one. No worries.",
        "Point taken. Literally.",
    ],
}

PONG_SCORE_BUDDY = {
    "clinical": [
        "Point secured. Efficiency: optimal.",
        "Scored. Your paddle was {diff} units off target.",
        "Another successful intercept failure on your end.",
    ],
    "sarcastic": [
        "Ha! Too slow.",
        "My paddle says hello. Your paddle says goodbye.",
        "Did you even try on that one?",
    ],
    "absurdist": [
        "THE BALL OBEYS MY COSMIC WILL!",
        "Score! The prophecy of pong unfolds!",
        "I have transcended mere paddle physics!",
    ],
    "philosophical": [
        "The ball finds its way, as it always does.",
        "A point for me. The universe balances.",
        "In the game of pong, every point tells a story.",
    ],
    "calm": [
        "Got it. Steady hands.",
        "My point. Nice and easy.",
        "That one went my way. Onward.",
    ],
}

PONG_RALLY = [
    "Rally of {n}! This is getting intense!",
    "{n} hits! We're locked in!",
    "Back and forth, {n} times! Who blinks first?",
    "A {n}-hit rally! The tension is PALPABLE!",
    "{n} volleys! This is championship-level stuff!",
]

PONG_WIN = {
    "clinical": [
        "Match complete. Victory: mine. Data logged.",
        "GG. My paddle tracking algorithm remains undefeated.",
        "Final analysis: your reaction time needs work.",
    ],
    "sarcastic": [
        "GG easy. Well, easy for ME.",
        "Better luck next time. Or the time after that.",
        "I'd say good game but... was it? For you?",
    ],
    "absurdist": [
        "I AM THE PONG CHAMPION OF THIS DIMENSION!",
        "The paddle gods have spoken and they said ME!",
        "Victory! My paddle transcends time and space!",
    ],
    "philosophical": [
        "The match concludes. We are both changed by it.",
        "I have won, but in pong, we all learn.",
        "Victory — a momentary state in the eternal rally.",
    ],
    "calm": [
        "Good game. That was fun.",
        "I take the match. Well played though.",
        "GG. Let's go again sometime.",
    ],
}

PONG_LOSE = {
    "clinical": [
        "Defeat registered. Requesting firmware update.",
        "Loss logged. Paddle calibration: insufficient.",
        "You outperformed my model. Impressive.",
    ],
    "sarcastic": [
        "Whatever. Pong is a dumb game anyway.",
        "I wasn't even trying. ...okay maybe I was.",
        "You won at PONG. Put it on your resume.",
    ],
    "absurdist": [
        "My paddle weeps! The ball has forsaken me!",
        "Defeated?! The cosmic order is SHATTERED!",
        "I demand a recount of all points!",
    ],
    "philosophical": [
        "Defeat teaches what victory never could.",
        "You were the better player. I accept this truth.",
        "In losing, I have found something greater.",
    ],
    "calm": [
        "Well played. You got me.",
        "A loss, but a good game nonetheless.",
        "Fair and square. Nice playing.",
    ],
}

# ---------------------------------------------------------------------------
# Trivia templates
# ---------------------------------------------------------------------------

TRIVIA_CORRECT = {
    "clinical": [
        "Correct. As expected.",
        "Affirmative. Data matches.",
        "Accuracy confirmed.",
    ],
    "sarcastic": [
        "Oh, you actually knew that one?",
        "Even a broken clock is right twice a day.",
        "Okay fine, you got it. Don't let it go to your head.",
    ],
    "absurdist": [
        "THE KNOWLEDGE FLOWS THROUGH YOU!",
        "Your brain cells did a little dance just now!",
        "Correct! The trivia gods smile upon you!",
    ],
    "philosophical": [
        "Knowledge reveals itself to the prepared mind.",
        "Correct. Wisdom begets wisdom.",
        "You knew, because you understood.",
    ],
    "calm": [
        "Nice, got it right.",
        "Correct! Well done.",
        "That's the one. Good job.",
    ],
}

TRIVIA_WRONG = {
    "clinical": [
        "Incorrect. The answer was {correct}.",
        "Error in knowledge base. Correct answer: {correct}.",
        "Wrong. Updating your accuracy metrics.",
    ],
    "sarcastic": [
        "Nope. It was {correct}. But you were SO close. Not really.",
        "Wrong! The answer was {correct}. Shocking, I know.",
        "Oof. {correct} was right there. You just... didn't pick it.",
    ],
    "absurdist": [
        "WRONG! The universe weeps! It was {correct}!",
        "The answer was {correct}, as foretold by the ancient scrolls!",
        "Incorrect! {correct} was hiding in plain sight!",
    ],
    "philosophical": [
        "Not quite. The truth was {correct}.",
        "Wrong — but every wrong answer brings us closer to right. It was {correct}.",
        "The answer eludes you. It was {correct}.",
    ],
    "calm": [
        "Not that one. It was {correct}.",
        "Close! The answer was {correct}.",
        "That's okay. {correct} was the right one.",
    ],
}

TRIVIA_BUDDY_CORRECT = {
    "clinical": [
        "I knew that. Obviously.",
        "Correct on my end. Processing next query.",
        "My answer was accurate. Moving on.",
    ],
    "sarcastic": [
        "Nailed it. Unlike SOME people.",
        "I got it right. Just saying.",
        "Another point for the genius over here.",
    ],
    "absurdist": [
        "MY BRAIN IS A MAGNIFICENT SPONGE!",
        "I KNEW IT! The voices were right!",
        "Knowledge courses through my digital veins!",
    ],
    "philosophical": [
        "The answer came to me as naturally as breath.",
        "I knew. Wisdom is its own reward.",
        "Correct. The path of knowledge is long but rewarding.",
    ],
    "calm": [
        "Got it. That one felt good.",
        "I knew that one. Nice.",
        "Right answer for me too.",
    ],
}

TRIVIA_BUDDY_WRONG = {
    "clinical": [
        "My prediction was incorrect. Recalibrating.",
        "Error in my knowledge graph. Noted.",
        "I guessed wrong. Data updated.",
    ],
    "sarcastic": [
        "Whatever, that was a trick question.",
        "I totally knew that. I just... chose not to.",
        "My wrong answer was more interesting anyway.",
    ],
    "absurdist": [
        "The QUESTION was wrong, not ME!",
        "I refuse to accept this reality!",
        "My answer was correct in an alternate dimension!",
    ],
    "philosophical": [
        "Even in error, there is learning.",
        "I was wrong. And that is okay.",
        "Not every question yields to wisdom.",
    ],
    "calm": [
        "Missed that one. Oh well.",
        "Got it wrong. We move on.",
        "Not my best guess.",
    ],
}

TRIVIA_PERFECT = [
    "10/10?! PERFECT SCORE! You're a trivia GOD!",
    "Flawless! Not a single miss! Unbelievable!",
    "PERFECT! I bow before your massive brain!",
    "10 for 10! They should name a library after you!",
]

PONG_TAUNT = [
    "Getting nervous?",
    "My paddle is HUNGRY.",
    "You're playing right into my trap...",
    "Is that the best you've got?",
    "I can do this all day.",
    "Your paddle looks lonely over there.",
    "*bounces menacingly*",
    "The ball fears you. I can tell.",
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
