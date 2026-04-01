"""Multiplayer foundations — async game messaging via GitHub Issues.

Built on top of the BBS transport layer. Uses the same GitHub Issues
API but with game-specific labels and message formats.

Message types:
- CHALLENGE: one user challenges another to a game
- MOVE: a game action (RPS throw, MUD command, trade offer)
- WORLD: persistent world state (MUD room contents, marketplace)
- RESULT: game outcome notification

All messages use YAML frontmatter for metadata + plain text body.
Designed for async play — you don't need to be online at the same time.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum

from buddies.core.bbs_profile import BBSProfile


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MessageType(Enum):
    CHALLENGE = "challenge"    # Game invitation
    MOVE = "move"              # In-game action
    WORLD = "world"            # Persistent world state
    RESULT = "result"          # Game outcome
    CHAT = "chat"              # In-world chat / room message
    TRADE = "trade"            # Marketplace / trade offer


# Labels used in the game repo (separate from BBS boards)
GAME_LABELS = {
    MessageType.CHALLENGE: "game:challenge",
    MessageType.MOVE: "game:move",
    MessageType.WORLD: "world:state",
    MessageType.RESULT: "game:result",
    MessageType.CHAT: "world:chat",
    MessageType.TRADE: "world:trade",
}


@dataclass
class GameMessage:
    """A multiplayer game message."""
    msg_type: MessageType
    game_type: str           # "rps", "mud", "trade", etc.
    sender: BBSProfile
    recipient: str | None    # None = broadcast (world/chat)
    payload: dict            # Game-specific data
    timestamp: float = field(default_factory=time.time)
    issue_id: int | None = None  # GitHub issue ID once posted

    def to_frontmatter(self) -> str:
        """Encode as YAML frontmatter + body for GitHub issue."""
        lines = [
            "---",
            f"msg_type: {self.msg_type.value}",
            f"game_type: {self.game_type}",
            f"sender: {self.sender.handle}",
            f"sender_species: {self.sender.species}",
            f"sender_emoji: {self.sender.emoji}",
            f"sender_level: {self.sender.level}",
        ]
        if self.recipient:
            lines.append(f"recipient: {self.recipient}")
        lines.append(f"timestamp: {self.timestamp}")
        lines.append("---")

        # Body is the payload as readable text
        body = self._format_body()
        return "\n".join(lines) + "\n\n" + body

    def _format_body(self) -> str:
        """Format the payload as human-readable text."""
        if self.msg_type == MessageType.CHALLENGE:
            game = self.payload.get("game", "unknown")
            return (
                f"⚔️ **{self.sender.handle}** challenges "
                f"**{self.recipient or 'anyone'}** to a game of **{game}**!\n\n"
                f"Stakes: {self.payload.get('stakes', 'bragging rights')}\n\n"
                f"React with 👍 to accept!"
            )
        elif self.msg_type == MessageType.MOVE:
            return (
                f"🎮 **{self.sender.handle}** plays: "
                f"{self.payload.get('action', '???')}\n\n"
                f"```\n{json.dumps(self.payload, indent=2)}\n```"
            )
        elif self.msg_type == MessageType.RESULT:
            winner = self.payload.get("winner", "unknown")
            return (
                f"🏆 Game over! Winner: **{winner}**\n\n"
                f"Score: {json.dumps(self.payload.get('score', {}))}"
            )
        elif self.msg_type == MessageType.CHAT:
            room = self.payload.get("room", "unknown")
            text = self.payload.get("text", "")
            return f"💬 [{room}] **{self.sender.handle}**: {text}"
        elif self.msg_type == MessageType.TRADE:
            offer = self.payload.get("offer", "nothing")
            want = self.payload.get("want", "anything")
            price = self.payload.get("price", 0)
            return (
                f"🏪 **{self.sender.handle}** offers:\n\n"
                f"  📦 Selling: {offer}\n"
                f"  💰 Price: {price} gold\n"
                f"  🔍 Wants: {want}\n\n"
                f"React with 👍 to buy!"
            )
        elif self.msg_type == MessageType.WORLD:
            room = self.payload.get("room", "unknown")
            state = self.payload.get("state", {})
            return (
                f"🌍 World state update: **{room}**\n\n"
                f"```json\n{json.dumps(state, indent=2)}\n```"
            )
        return json.dumps(self.payload, indent=2)

    @classmethod
    def from_frontmatter(cls, frontmatter: dict, body: str) -> GameMessage | None:
        """Parse a GameMessage from frontmatter + body."""
        try:
            msg_type = MessageType(frontmatter.get("msg_type", ""))
        except ValueError:
            return None

        # Reconstruct a minimal profile
        profile = BBSProfile(
            handle=frontmatter.get("sender", "unknown"),
            species=frontmatter.get("sender_species", "unknown"),
            emoji=frontmatter.get("sender_emoji", "?"),
            rarity="common",
            level=int(frontmatter.get("sender_level", 1)),
            stage="", stage_symbol="",
            dominant_stat="", register="",
            hat=None, shiny=False,
            privacy="public", github_user="",
        )

        return cls(
            msg_type=msg_type,
            game_type=frontmatter.get("game_type", "unknown"),
            sender=profile,
            recipient=frontmatter.get("recipient"),
            payload={},  # Payload is in the body, caller can parse
            timestamp=float(frontmatter.get("timestamp", 0)),
        )


# ---------------------------------------------------------------------------
# Challenge system — the entry point for async multiplayer
# ---------------------------------------------------------------------------

@dataclass
class Challenge:
    """A game challenge between two users."""
    challenger: BBSProfile
    game_type: str          # "rps", "trivia_duel", "dungeon_race"
    stakes: str = "bragging rights"
    accepted: bool = False
    challenger_move: str | None = None
    opponent_move: str | None = None
    result: dict | None = None

    def to_message(self) -> GameMessage:
        return GameMessage(
            msg_type=MessageType.CHALLENGE,
            game_type=self.game_type,
            sender=self.challenger,
            recipient=None,  # Open challenge
            payload={
                "game": self.game_type,
                "stakes": self.stakes,
            },
        )


# ---------------------------------------------------------------------------
# Async RPS — the simplest multiplayer game
# ---------------------------------------------------------------------------

@dataclass
class AsyncRPSChallenge:
    """An async Rock-Paper-Scissors challenge.

    Flow:
    1. Challenger creates issue with their throw (hidden in payload hash)
    2. Opponent replies with their throw
    3. Result is computed and posted as a comment
    """
    challenger: BBSProfile
    challenger_throw: str | None = None  # "rock", "paper", "scissors"
    opponent: BBSProfile | None = None
    opponent_throw: str | None = None
    issue_id: int | None = None

    def to_challenge_message(self) -> GameMessage:
        """Create the initial challenge issue."""
        import hashlib
        # Hash the throw so it can't be changed after posting
        throw_hash = ""
        if self.challenger_throw:
            raw = f"{self.challenger.handle}:{self.challenger_throw}:{time.time()}"
            throw_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]

        return GameMessage(
            msg_type=MessageType.CHALLENGE,
            game_type="rps",
            sender=self.challenger,
            recipient=None,
            payload={
                "game": "Rock-Paper-Scissors",
                "stakes": "bragging rights + 10 gold",
                "throw_hash": throw_hash,
            },
        )

    def to_move_message(self, profile: BBSProfile, throw: str) -> GameMessage:
        """Create a move (reply) with the opponent's throw."""
        return GameMessage(
            msg_type=MessageType.MOVE,
            game_type="rps",
            sender=profile,
            recipient=self.challenger.handle,
            payload={"throw": throw},
        )

    @staticmethod
    def resolve(throw_a: str, throw_b: str) -> str:
        """Resolve RPS. Returns 'a', 'b', or 'draw'."""
        if throw_a == throw_b:
            return "draw"
        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        return "a" if wins.get(throw_a) == throw_b else "b"


# ---------------------------------------------------------------------------
# MUD room state — for the eventual MMORPG
# ---------------------------------------------------------------------------

@dataclass
class MUDRoom:
    """A room in the shared MUD world."""
    room_id: str             # Unique room identifier
    name: str
    description: str
    exits: dict[str, str]    # direction -> room_id
    npcs: list[str] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    players_present: list[str] = field(default_factory=list)  # buddy handles

    def to_payload(self) -> dict:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "exits": self.exits,
            "npcs": self.npcs,
            "items": self.items,
            "players_present": self.players_present,
        }

    @classmethod
    def from_payload(cls, data: dict) -> MUDRoom:
        return cls(
            room_id=data.get("room_id", "unknown"),
            name=data.get("name", "Unnamed Room"),
            description=data.get("description", ""),
            exits=data.get("exits", {}),
            npcs=data.get("npcs", []),
            items=data.get("items", []),
            players_present=data.get("players_present", []),
        )


# ---------------------------------------------------------------------------
# Trade / marketplace
# ---------------------------------------------------------------------------

@dataclass
class TradeOffer:
    """A marketplace trade offer."""
    seller: BBSProfile
    item_name: str
    price: int              # In gold
    description: str = ""
    category: str = "misc"  # "cosmetic", "consumable", "trophy", "misc"

    def to_message(self) -> GameMessage:
        return GameMessage(
            msg_type=MessageType.TRADE,
            game_type="marketplace",
            sender=self.seller,
            recipient=None,
            payload={
                "offer": self.item_name,
                "price": self.price,
                "description": self.description,
                "category": self.category,
                "want": "gold",
            },
        )


# ---------------------------------------------------------------------------
# Starter MUD world definition
# ---------------------------------------------------------------------------

STARTER_WORLD: list[MUDRoom] = [
    MUDRoom(
        room_id="town_square",
        name="Town Square",
        description="The heart of Codeville. A fountain shaped like a rubber duck "
                    "burbles in the center. Buddies mill about, some arguing about "
                    "tabs vs spaces. A signpost points in four directions.",
        exits={"north": "tavern", "east": "marketplace", "south": "dungeon_gate", "west": "library"},
        npcs=["The Sysadmin Who Never Logs Off", "Wandering Intern"],
        items=["Slightly Damp Notice Board"],
    ),
    MUDRoom(
        room_id="tavern",
        name="The Stack Overflow Tavern",
        description="A rowdy establishment where questions are answered, usually wrong. "
                    "The bartender is a retired Exception Handler. Someone is crying "
                    "in the corner about their rejected pull request.",
        exits={"south": "town_square"},
        npcs=["Bartender (retired ExceptionHandler)", "Crying Developer"],
        items=["Suspiciously Sticky Keyboard", "Half-Empty Coffee Mug"],
    ),
    MUDRoom(
        room_id="marketplace",
        name="The Dependency Market",
        description="Stalls overflow with packages of dubious quality. 'npm install' "
                    "echoes from every direction. A shady figure offers you a package "
                    "with 47 transitive dependencies.",
        exits={"west": "town_square"},
        npcs=["Shady Package Dealer", "The Auditor"],
        items=["Free Stickers", "Untested NPM Package"],
    ),
    MUDRoom(
        room_id="dungeon_gate",
        name="The Dungeon Gate",
        description="A massive gate made of deprecated HTML tags. Beyond it, the Coding "
                    "Dungeon awaits. A sign reads: 'ABANDON ALL SEMICOLONS, YE WHO ENTER HERE'. "
                    "Your blobber dungeon adventures start from here.",
        exits={"north": "town_square"},
        npcs=["Gate Guard (Senior Developer)"],
        items=["Rusty Semicolon (Key)"],
    ),
    MUDRoom(
        room_id="library",
        name="The Documentation Library",
        description="Towering shelves of scrolls, most of them outdated. The librarian, "
                    "a wizened Mage-class buddy, guards the forbidden section labeled "
                    "'INTERNAL API — DO NOT USE'. Naturally, everyone uses it.",
        exits={"east": "town_square", "up": "observatory"},
        npcs=["The Librarian", "Dust Ghost"],
        items=["man page (crumpled)", "RFC 2549 (IP over Avian Carriers)"],
    ),
    MUDRoom(
        room_id="observatory",
        name="The Monitoring Observatory",
        description="Screens everywhere showing graphs that are either alarming or "
                    "meaningless. A lone oncall engineer stares at a dashboard. "
                    "'Is that normal?' you ask. 'Nothing is normal,' they reply.",
        exits={"down": "library"},
        npcs=["The Oncall Engineer", "Alert Bot (beeping)"],
        items=["PagerDuty Token (expired)", "Grafana Dashboard (incomprehensible)"],
    ),
]

STARTER_WORLD_MAP: dict[str, MUDRoom] = {r.room_id: r for r in STARTER_WORLD}
