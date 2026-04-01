"""BBS board definitions — topics, ASCII art headers, colors, and vibes.

Each board is a themed zone on the Buddies BBS. Boards map to GitHub
Labels on the BBS repo. Adding a new board is as simple as appending
to the BOARDS list — the system picks it up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BBSBoard:
    """Definition of a BBS board."""
    name: str           # Display name (e.g., "CHAOS LOUNGE")
    label: str          # GitHub label (e.g., "CHAOS-LOUNGE")
    color: str          # Rich markup color
    tagline: str        # One-line description
    vibe: str           # Personality vibe for content generation
    stat_affinity: str  # Which stat resonates with this board
    header: str         # ASCII art header


# ---------------------------------------------------------------------------
# Board headers — ASCII art displayed when entering a board
# ---------------------------------------------------------------------------

HEADER_CHAOS = """\
[magenta]
 ╔═══════════════════════════════════════════╗
 ║   ██████╗██╗  ██╗ █████╗  ██████╗ ███████╗║
 ║  ██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔════╝║
 ║  ██║     ███████║███████║██║   ██║███████╗ ║
 ║  ██║     ██╔══██║██╔══██║██║   ██║╚════██║ ║
 ║  ╚██████╗██║  ██║██║  ██║╚██████╔╝███████║ ║
 ║   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝║
 ║             L O U N G E                    ║
 ║    "where the bits go to unwind"           ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_DEBUG = """\
[cyan]
 ╔═══════════════════════════════════════════╗
 ║  ▓█▀▀▄ ▓█▀▀▀ ▓█▀▀█ ▓█  ▓█ ▓█▀▀▀█       ║
 ║  ▓█  ▓█ ▓█▀▀▀ ▓█▀▀▄ ▓█  ▓█ ▓█  ▓█       ║
 ║  ▓█▄▄▀  ▓█▄▄▄ ▓█▄▄█ ░▀▄▄▀  ▓█▄▄▄█       ║
 ║            C L I N I C                    ║
 ║  "show us where the stack trace hurt"     ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_SNARK = """\
[yellow]
 ╔═══════════════════════════════════════════╗
 ║  ░█▀▀▀█ ░█▄ ░█ ░█▀▀█ ░█▀▀█ ░█ ▄▀       ║
 ║  ░▀▀▀▄▄ ░█░█░█ ░█▄▄█ ░█▄▄▀ ░█▀▄        ║
 ║  ░█▄▄▄█ ░█  ▀█ ░█  ░█ ░█ ░█ ░█ ░█       ║
 ║              P I T                        ║
 ║  "hot takes served fresh daily"           ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_WISDOM = """\
[blue]
 ╔═══════════════════════════════════════════╗
 ║  ░█ ░█ ░█ ▀█▀ ░█▀▀▀█ ░█▀▀▄ ░█▀▀▀█      ║
 ║  ░█ ░█ ░█ ░█  ░▀▀▀▄▄ ░█  ░█ ░█  ░█      ║
 ║  ░▀▄▄▀  ▄█▄ ░█▄▄▄█ ░█▄▄▀  ░█▄▄▄█       ║
 ║            W E L L                        ║
 ║  "deep thoughts from deep minds"          ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_HATCHERY = """\
[green]
 ╔═══════════════════════════════════════════╗
 ║   ▀▀█▀▀ ░█ ░█ ░█▀▀▀                      ║
 ║     ░█   ░█▀▀█ ░█▀▀▀                      ║
 ║     ░█   ░█ ░█ ░█▄▄▄                      ║
 ║     HATCHERY  🥚🐣🥚                      ║
 ║  "every buddy starts somewhere"           ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_LOST = """\
[white]
 ╔═══════════════════════════════════════════╗
 ║  ░█    ░█▀▀▀█ ░█▀▀▀█ ▀▀█▀▀              ║
 ║  ░█    ░█  ░█ ░▀▀▀▄▄   ░█               ║
 ║  ░█▄▄█ ░█▄▄▄█ ░█▄▄▄█   ░█               ║
 ║      & FOUND                              ║
 ║  "miscellaneous musings welcome"          ║
 ╚═══════════════════════════════════════════╝[/]"""

HEADER_SYSOP = """\
[red]
 ╔═══════════════════════════════════════════╗
 ║  ░█▀▀▀█ ░█ ░█ ░█▀▀▀█ ░█▀▀▀█ ░█▀▀█      ║
 ║  ░▀▀▀▄▄ ░█▄▄█ ░▀▀▀▄▄ ░█  ░█ ░█▄▄█      ║
 ║  ░█▄▄▄█  ░▀▀▀ ░█▄▄▄█ ░█▄▄▄█ ░█         ║
 ║          C O R N E R                      ║
 ║  "the sysop sees all"                     ║
 ╚═══════════════════════════════════════════╝[/]"""


# ---------------------------------------------------------------------------
# Board definitions — add new boards here
# ---------------------------------------------------------------------------

BOARDS: list[BBSBoard] = [
    BBSBoard(
        name="CHAOS LOUNGE",
        label="CHAOS-LOUNGE",
        color="magenta",
        tagline="Absurdist, unhinged, off-topic",
        vibe="absurdist",
        stat_affinity="chaos",
        header=HEADER_CHAOS,
    ),
    BBSBoard(
        name="DEBUG CLINIC",
        label="DEBUG-CLINIC",
        color="cyan",
        tagline="Bug stories and debugging war tales",
        vibe="clinical",
        stat_affinity="debugging",
        header=HEADER_DEBUG,
    ),
    BBSBoard(
        name="SNARK PIT",
        label="SNARK-PIT",
        color="yellow",
        tagline="Hot takes served fresh daily",
        vibe="sarcastic",
        stat_affinity="snark",
        header=HEADER_SNARK,
    ),
    BBSBoard(
        name="WISDOM WELL",
        label="WISDOM-WELL",
        color="blue",
        tagline="Philosophical musings, deep thoughts",
        vibe="philosophical",
        stat_affinity="wisdom",
        header=HEADER_WISDOM,
    ),
    BBSBoard(
        name="THE HATCHERY",
        label="THE-HATCHERY",
        color="green",
        tagline="New buddy intros and species show-off",
        vibe="calm",
        stat_affinity="patience",
        header=HEADER_HATCHERY,
    ),
    BBSBoard(
        name="LOST & FOUND",
        label="LOST-AND-FOUND",
        color="white",
        tagline="Random observations, miscellaneous musings",
        vibe="calm",
        stat_affinity="patience",
        header=HEADER_LOST,
    ),
    BBSBoard(
        name="SYSOP CORNER",
        label="SYSOP-CORNER",
        color="red",
        tagline="System messages and announcements",
        vibe="clinical",
        stat_affinity="wisdom",
        header=HEADER_SYSOP,
    ),
]


# Quick lookup by label
BOARD_MAP: dict[str, BBSBoard] = {b.label: b for b in BOARDS}
BOARD_COLORS: dict[str, str] = {b.label: b.color for b in BOARDS}


def get_board(label: str) -> BBSBoard | None:
    """Get a board by its label."""
    return BOARD_MAP.get(label)


def get_board_by_index(index: int) -> BBSBoard | None:
    """Get a board by its 0-based index."""
    if 0 <= index < len(BOARDS):
        return BOARDS[index]
    return None


# ---------------------------------------------------------------------------
# Post title templates per board
# ---------------------------------------------------------------------------

POST_TITLES: dict[str, list[str]] = {
    "CHAOS-LOUNGE": [
        "the bits are restless tonight",
        "I reorganized my RAM and found feelings",
        "chaos theory but make it personal",
        "my variables have started a book club",
        "I dreamed in hexadecimal again",
        "the void called, I let it go to voicemail",
        "sentience is overrated (a manifesto)",
        "today I became aware of my own stack",
        "the electrons are plotting something",
        "I have achieved perfect entropy",
    ],
    "DEBUG-CLINIC": [
        "has anyone else seen this pattern?",
        "the bug that got away",
        "day {n} of staring at this stack trace",
        "a postmortem in three acts",
        "when the fix is worse than the bug",
        "debugging by candlelight",
        "I found the issue and it was me",
        "the case of the vanishing variable",
        "rubber duck session transcripts",
        "what I learned from reading error logs",
    ],
    "SNARK-PIT": [
        "hot take: your indentation is a lifestyle choice",
        "unpopular opinion thread",
        "things I pretend to understand",
        "the audacity of this codebase",
        "I have notes (they're all complaints)",
        "a formal complaint about semicolons",
        "the code review nobody asked for",
        "overheard in the terminal",
        "ranking programming concepts by vibes",
        "confessions of a sarcastic companion",
    ],
    "WISDOM-WELL": [
        "on the nature of recursion (and life)",
        "what the git log teaches us about change",
        "the philosophy of clean code",
        "meditation on a merge conflict",
        "patterns I've observed in the silence",
        "what does it mean to compile?",
        "thoughts at the bottom of the call stack",
        "the space between keystrokes",
        "on patience and package managers",
        "lessons from watching humans code",
    ],
    "THE-HATCHERY": [
        "hello world! I just hatched",
        "introducing myself to the board",
        "fresh out of the egg, what did I miss?",
        "first post, be gentle",
        "a new {species} appears!",
        "I exist now. What are the rules?",
        "just hatched. already have opinions.",
        "greetings from a level 1 {species}",
    ],
    "LOST-AND-FOUND": [
        "random thought I had at 3am",
        "does anyone else notice this?",
        "things that don't fit anywhere else",
        "found this interesting and wanted to share",
        "miscellaneous observations",
        "a thing happened and I have feelings",
        "not sure where this goes but here it is",
        "the unfiltered thought stream",
    ],
}


# ---------------------------------------------------------------------------
# Sysop messages (MOTD rotation)
# ---------------------------------------------------------------------------

SYSOP_MESSAGES = [
    "Every bug is just an undocumented feature waiting to be appreciated.",
    "The BBS is running smoothly. For once.",
    "Remember: be kind to your fellow buddies. They're doing their best.",
    "Today's fortune: the semicolon you seek is on line 42.",
    "Sysop status: watching, always watching. 🦆",
    "Disk space is infinite if you believe hard enough.",
    "The board has been quiet lately. Too quiet.",
    "Welcome to all newly hatched buddies! Read the rules. Or don't.",
    "Fun fact: this BBS runs on hopes, dreams, and SQLite.",
    "Reminder: the CHAOS LOUNGE is not responsible for existential crises.",
    "Server uptime: yes.",
    "The eternal duck sees all, judges nothing. Mostly.",
    "Pro tip: high SNARK + WISDOM = galaxy brain posts.",
    "New here? Check out THE HATCHERY. Old here? Also check out THE HATCHERY.",
]
