"""MUD Async Multiplayer — Dark Souls-style notes, bloodstains, and phantoms.

Phase 1: Local storage (JSON file). All features work offline.
Phase 2: GitHub Issues transport for cross-user sharing.

Inspired by Dark Souls' soapstone messages, bloodstains, and phantoms.
Messages are built from template fragments (coding-themed), not freetext,
to keep things funny and prevent abuse.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from buddies.config import get_data_dir


# ---------------------------------------------------------------------------
# Soapstone Note System
# ---------------------------------------------------------------------------

# Template fragments — players combine a TEMPLATE with a SUBJECT to make notes.
# Just like Dark Souls: "Try jumping" / "Be wary of right"

TEMPLATES = [
    "Try {subject}",
    "Be wary of {subject}",
    "{subject} ahead",
    "If only I had {subject}...",
    "Praise the {subject}!",
    "Don't give up, {subject}!",
    "No {subject} ahead",
    "Behold, {subject}!",
    "Could this be {subject}?",
    "Why is it always {subject}?",
    "Didn't expect {subject}",
    "Time for {subject}",
    "Seek {subject}",
    "Still no {subject}...",
    "Ahh, {subject}...",
    "{subject} required ahead",
    "First off, {subject}",
    "Let there be {subject}",
    "Likely {subject}",
    "Offer {subject}",
]

SUBJECTS = [
    # Actions
    "debugging", "refactoring", "coffee", "deploying",
    "turning it off and on again", "reading the docs",
    "asking Stack Overflow", "rubber duck debugging",
    "git blame", "reverting", "pair programming",
    "taking a break", "updating dependencies",
    "writing tests", "checking the logs",
    "prayer", "sudo", "sleep",

    # Things
    "merge conflicts", "scope creep", "technical debt",
    "a rubber duck", "root access", "more coffee",
    "better error messages", "documentation",
    "a senior developer", "a working build",
    "the CI/CD pipeline", "a code review",
    "a quiet meeting room", "pizza",
    "an incident report", "a VPN token",
    "type safety", "the cloud",

    # Adjectives + Nouns
    "hidden treasure", "a trap", "an ambush",
    "strong enemy", "boss", "shortcut",
    "secret path", "dead end", "loot",
    "a friend", "sadness", "joy",
    "a miracle", "despair", "victory",
    "legacy code", "spaghetti code", "clean code",
]

# Pre-seeded phantom notes from "other adventurers"
PHANTOM_AUTHORS = [
    ("GeraldBot", "🧔"), ("SkylerXD", "👶"), ("MiriamOG", "👩‍💻"),
    ("CoffeeMachine", "☕"), ("DuckSage", "🦆"), ("404User", "👻"),
    ("ProdDown", "🔥"), ("GitGuru", "🌿"), ("NullRef", "⬛"),
    ("K8sKid", "☸️"), ("YAMLord", "📃"), ("PagerDuty", "📟"),
]


@dataclass
class SoapstoneNote:
    """A message left by a player in a room."""
    id: str
    room_id: str
    message: str
    author_name: str
    author_emoji: str
    timestamp: float = field(default_factory=time.time)
    upvotes: int = 0
    downvotes: int = 0
    is_phantom: bool = False  # Pre-seeded/NPC note

    @property
    def rating(self) -> int:
        return self.upvotes - self.downvotes

    @property
    def rating_text(self) -> str:
        r = self.rating
        if r > 5:
            return "[green]★★★[/green]"
        elif r > 2:
            return "[green]★★[/green]"
        elif r > 0:
            return "[green]★[/green]"
        elif r == 0:
            return "[dim]☆[/dim]"
        else:
            return "[red]✗[/red]"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SoapstoneNote:
        return cls(**d)


@dataclass
class Bloodstain:
    """A death marker left where a player's party was defeated."""
    id: str
    room_id: str
    cause_of_death: str  # NPC name or description
    buddy_name: str
    buddy_emoji: str
    buddy_level: int
    timestamp: float = field(default_factory=time.time)
    is_phantom: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Bloodstain:
        return cls(**d)


@dataclass
class Phantom:
    """A ghostly trace of another player's buddy spotted in a room."""
    room_id: str
    buddy_name: str
    buddy_emoji: str
    buddy_species: str
    action: str  # What they were doing
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Phantom:
        return cls(**d)


# ---------------------------------------------------------------------------
# Phantom actions — what ghosts are doing when you see them
# ---------------------------------------------------------------------------

PHANTOM_ACTIONS = [
    "examining the walls",
    "pacing nervously",
    "searching for something",
    "sitting quietly",
    "gesturing at nothing",
    "reading a terminal",
    "fighting an invisible enemy",
    "celebrating a victory",
    "resting against the wall",
    "scribbling a note",
    "running past at full speed",
    "standing perfectly still, staring at you",
    "debugging something only they can see",
    "arguing with the air",
    "doing a little dance",
]


# ---------------------------------------------------------------------------
# Storage — local JSON for Phase 1
# ---------------------------------------------------------------------------

class MudMultiplayerStore:
    """Persistent storage for async multiplayer data."""

    def __init__(self):
        self.data_dir = get_data_dir() / "mud_multiplayer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._notes_file = self.data_dir / "notes.json"
        self._bloodstains_file = self.data_dir / "bloodstains.json"
        self._phantoms_file = self.data_dir / "phantoms.json"
        self._rated_notes: set[str] = set()  # Note IDs we've already rated

        # Load or initialize
        self.notes: list[SoapstoneNote] = self._load_notes()
        self.bloodstains: list[Bloodstain] = self._load_bloodstains()
        self.phantoms: list[Phantom] = self._load_phantoms()

        # Seed phantom notes if empty
        if not self.notes:
            self._seed_phantom_notes()
        if not self.bloodstains:
            self._seed_phantom_bloodstains()

    def _load_notes(self) -> list[SoapstoneNote]:
        if self._notes_file.exists():
            try:
                data = json.loads(self._notes_file.read_text())
                return [SoapstoneNote.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return []

    def _load_bloodstains(self) -> list[Bloodstain]:
        if self._bloodstains_file.exists():
            try:
                data = json.loads(self._bloodstains_file.read_text())
                return [Bloodstain.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return []

    def _load_phantoms(self) -> list[Phantom]:
        if self._phantoms_file.exists():
            try:
                data = json.loads(self._phantoms_file.read_text())
                return [Phantom.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return []

    def save(self):
        """Persist all data to disk."""
        self._notes_file.write_text(json.dumps([n.to_dict() for n in self.notes], indent=2))
        self._bloodstains_file.write_text(json.dumps([b.to_dict() for b in self.bloodstains], indent=2))
        self._phantoms_file.write_text(json.dumps([p.to_dict() for p in self.phantoms], indent=2))

    # --- Notes ---

    def add_note(self, note: SoapstoneNote):
        self.notes.append(note)
        self.save()

    def get_notes_for_room(self, room_id: str, limit: int = 3) -> list[SoapstoneNote]:
        """Get notes for a room, sorted by rating, limited."""
        room_notes = [n for n in self.notes if n.room_id == room_id]
        room_notes.sort(key=lambda n: n.rating, reverse=True)
        return room_notes[:limit]

    def rate_note(self, note_id: str, upvote: bool) -> bool:
        """Rate a note. Returns False if already rated."""
        if note_id in self._rated_notes:
            return False
        for note in self.notes:
            if note.id == note_id:
                if upvote:
                    note.upvotes += 1
                else:
                    note.downvotes += 1
                self._rated_notes.add(note_id)
                self.save()
                return True
        return False

    # --- Bloodstains ---

    def add_bloodstain(self, stain: Bloodstain):
        self.bloodstains.append(stain)
        # Keep only last 50 bloodstains
        if len(self.bloodstains) > 50:
            self.bloodstains = self.bloodstains[-50:]
        self.save()

    def get_bloodstains_for_room(self, room_id: str, limit: int = 2) -> list[Bloodstain]:
        room_stains = [b for b in self.bloodstains if b.room_id == room_id]
        room_stains.sort(key=lambda b: b.timestamp, reverse=True)
        return room_stains[:limit]

    # --- Phantoms ---

    def add_phantom(self, phantom: Phantom):
        self.phantoms.append(phantom)
        if len(self.phantoms) > 100:
            self.phantoms = self.phantoms[-100:]
        self.save()

    def get_phantom_for_room(self, room_id: str) -> Phantom | None:
        """Maybe see a phantom in this room (~30% chance)."""
        room_phantoms = [p for p in self.phantoms if p.room_id == room_id]
        if room_phantoms and random.random() < 0.30:
            return random.choice(room_phantoms)
        return None

    # --- Seeding ---

    def _seed_phantom_notes(self):
        """Pre-seed notes from 'other adventurers' so the world feels alive."""
        seeds = [
            ("lobby", "Be wary of scope creep"),
            ("lobby", "First off, coffee"),
            ("town_square", "Praise the CI/CD pipeline!"),
            ("town_square", "If only I had a quiet meeting room..."),
            ("break_room", "Try coffee"),
            ("break_room", "Ahh, coffee..."),
            ("meeting_room", "No escape ahead"),
            ("meeting_room", "Why is it always scope creep?"),
            ("supply_closet", "Seek a rubber duck"),
            ("codebase_ruins", "Be wary of legacy code"),
            ("codebase_ruins", "Didn't expect sadness"),
            ("repository_depths", "Be wary of merge conflicts"),
            ("repository_depths", "Boss ahead"),
            ("dead_code_garden", "Still no documentation..."),
            ("dead_code_garden", "Ahh, sadness..."),
            ("server_room", "Try turning it off and on again"),
            ("server_room", "Strong enemy ahead"),
            ("root_chamber", "Be wary of technical debt"),
            ("root_chamber", "If only I had root access..."),
            ("cloud_district", "Could this be the cloud?"),
            ("cloud_district", "Likely despair"),
            ("parking_garage", "Hidden treasure ahead"),
            ("parking_garage", "Why is it always sadness?"),
            ("qa_lab", "Try writing tests"),
            ("testing_grounds", "Be wary of a trap"),
            ("standup_room", "Time for prayer"),
            ("incident_channel", "Don't give up, debugging!"),
            ("incident_channel", "If only I had sleep..."),
            ("archive", "Behold, legacy code!"),
            ("archive", "Praise the documentation!"),
            ("kubernetes_cluster", "Be wary of the cloud"),
            ("kubernetes_cluster", "Try reverting"),
        ]

        for room_id, message in seeds:
            author, emoji = random.choice(PHANTOM_AUTHORS)
            note = SoapstoneNote(
                id=f"phantom_{room_id}_{len(self.notes)}",
                room_id=room_id,
                message=message,
                author_name=author,
                author_emoji=emoji,
                timestamp=time.time() - random.randint(3600, 86400 * 7),
                upvotes=random.randint(0, 12),
                downvotes=random.randint(0, 3),
                is_phantom=True,
            )
            self.notes.append(note)

        self.save()

    def _seed_phantom_bloodstains(self):
        """Pre-seed death markers from 'other adventurers'."""
        seeds = [
            ("repository_depths", "The Merge Conflict Demon", "BranchHero", "🌿", 3),
            ("repository_depths", "The Merge Conflict Demon", "GitGuru", "🧙", 5),
            ("dead_code_garden", "The Null Pointer", "RefCounter", "🔢", 4),
            ("server_room", "Regex Golem", "PatternMatcher", "🔮", 6),
            ("server_room", "Regex Golem", "404User", "👻", 2),
            ("root_chamber", "The Technical Debt Dragon", "DebtPayer", "💳", 8),
            ("root_chamber", "The Technical Debt Dragon", "Refactorer", "🔧", 7),
            ("root_chamber", "The Technical Debt Dragon", "InternPrime", "👶", 3),
            ("testing_grounds", "Flaky Test Swarm", "QATester", "🔍", 5),
            ("incident_channel", "The Memory Leak", "HeapHunter", "🫧", 6),
            ("kubernetes_cluster", "CrashLoopBackoff", "PodWhisperer", "☸️", 4),
        ]

        for room_id, cause, name, emoji, level in seeds:
            stain = Bloodstain(
                id=f"phantom_blood_{room_id}_{len(self.bloodstains)}",
                room_id=room_id,
                cause_of_death=cause,
                buddy_name=name,
                buddy_emoji=emoji,
                buddy_level=level,
                timestamp=time.time() - random.randint(3600, 86400 * 7),
                is_phantom=True,
            )
            self.bloodstains.append(stain)

        self.save()


# ---------------------------------------------------------------------------
# Note construction helpers
# ---------------------------------------------------------------------------

def build_note_message(template_idx: int, subject_idx: int) -> str:
    """Build a soapstone note from template + subject indices."""
    if 0 <= template_idx < len(TEMPLATES) and 0 <= subject_idx < len(SUBJECTS):
        return TEMPLATES[template_idx].format(subject=SUBJECTS[subject_idx])
    return ""


def get_template_list() -> list[str]:
    """Get displayable list of templates with indices."""
    return [f"  [bold cyan]{i:2d}[/bold cyan]. {t.format(subject='___')}" for i, t in enumerate(TEMPLATES)]


def get_subject_list() -> list[str]:
    """Get displayable list of subjects with indices."""
    return [f"  [bold cyan]{i:2d}[/bold cyan]. {s}" for i, s in enumerate(SUBJECTS)]


def format_note_display(note: SoapstoneNote) -> str:
    """Format a note for room display."""
    age = time.time() - note.timestamp
    if age < 3600:
        age_str = "just now"
    elif age < 86400:
        age_str = f"{int(age / 3600)}h ago"
    else:
        age_str = f"{int(age / 86400)}d ago"

    phantom_tag = " [dim](phantom)[/dim]" if note.is_phantom else ""
    return (
        f"  [yellow]📜[/yellow] \"{note.message}\" "
        f"— {note.author_emoji} {note.author_name}{phantom_tag} "
        f"{note.rating_text} [dim]({age_str})[/dim]"
    )


def format_bloodstain_display(stain: Bloodstain) -> str:
    """Format a bloodstain for room display."""
    age = time.time() - stain.timestamp
    if age < 3600:
        age_str = "just now"
    elif age < 86400:
        age_str = f"{int(age / 3600)}h ago"
    else:
        age_str = f"{int(age / 86400)}d ago"

    return (
        f"  [red]💀[/red] {stain.buddy_emoji} {stain.buddy_name} (Lv.{stain.buddy_level}) "
        f"fell to [bold red]{stain.cause_of_death}[/bold red] [dim]({age_str})[/dim]"
    )


def format_phantom_display(phantom: Phantom) -> str:
    """Format a phantom sighting."""
    return (
        f"  [dim]👻 A faint apparition of {phantom.buddy_emoji} {phantom.buddy_name} "
        f"({phantom.buddy_species}) appears, {phantom.action}...[/dim]"
    )
