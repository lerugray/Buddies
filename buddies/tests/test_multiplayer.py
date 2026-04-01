"""Tests for multiplayer foundations — message types, challenges, MUD rooms."""

import pytest

from buddies.core.bbs_profile import BBSProfile
from buddies.core.multiplayer import (
    GameMessage, MessageType, Challenge, AsyncRPSChallenge,
    MUDRoom, TradeOffer, STARTER_WORLD, STARTER_WORLD_MAP,
    GAME_LABELS,
)


def make_profile(name="Tester"):
    return BBSProfile(
        handle=name, species="phoenix", emoji="F", rarity="epic",
        level=5, stage="Adult", stage_symbol="A",
        dominant_stat="debugging", register="clinical",
        hat=None, shiny=False, privacy="public", github_user="",
    )


class TestGameMessage:
    def test_challenge_message_format(self):
        msg = GameMessage(
            msg_type=MessageType.CHALLENGE,
            game_type="rps",
            sender=make_profile("Alice"),
            recipient="Bob",
            payload={"game": "Rock-Paper-Scissors", "stakes": "10 gold"},
        )
        text = msg.to_frontmatter()
        assert "msg_type: challenge" in text
        assert "Alice" in text
        assert "Bob" in text
        assert "Rock-Paper-Scissors" in text

    def test_move_message_format(self):
        msg = GameMessage(
            msg_type=MessageType.MOVE,
            game_type="rps",
            sender=make_profile("Alice"),
            recipient="Bob",
            payload={"action": "throw rock"},
        )
        text = msg.to_frontmatter()
        assert "msg_type: move" in text
        assert "throw rock" in text

    def test_chat_message_format(self):
        msg = GameMessage(
            msg_type=MessageType.CHAT,
            game_type="mud",
            sender=make_profile("Alice"),
            recipient=None,
            payload={"room": "town_square", "text": "Hello world!"},
        )
        text = msg.to_frontmatter()
        assert "Hello world!" in text
        assert "town_square" in text

    def test_trade_message_format(self):
        msg = GameMessage(
            msg_type=MessageType.TRADE,
            game_type="marketplace",
            sender=make_profile("Alice"),
            recipient=None,
            payload={"offer": "Golden Semicolon", "price": 50, "want": "gold"},
        )
        text = msg.to_frontmatter()
        assert "Golden Semicolon" in text
        assert "50" in text

    def test_from_frontmatter(self):
        fm = {
            "msg_type": "challenge",
            "game_type": "rps",
            "sender": "Alice",
            "sender_species": "phoenix",
            "sender_emoji": "F",
            "sender_level": "5",
            "recipient": "Bob",
            "timestamp": "1234567890",
        }
        msg = GameMessage.from_frontmatter(fm, "some body")
        assert msg is not None
        assert msg.msg_type == MessageType.CHALLENGE
        assert msg.sender.handle == "Alice"
        assert msg.recipient == "Bob"

    def test_from_frontmatter_invalid_type(self):
        fm = {"msg_type": "invalid_type"}
        msg = GameMessage.from_frontmatter(fm, "body")
        assert msg is None


class TestAsyncRPS:
    def test_resolve_rock_beats_scissors(self):
        assert AsyncRPSChallenge.resolve("rock", "scissors") == "a"

    def test_resolve_scissors_beats_paper(self):
        assert AsyncRPSChallenge.resolve("scissors", "paper") == "a"

    def test_resolve_paper_beats_rock(self):
        assert AsyncRPSChallenge.resolve("paper", "rock") == "a"

    def test_resolve_draw(self):
        assert AsyncRPSChallenge.resolve("rock", "rock") == "draw"

    def test_resolve_loss(self):
        assert AsyncRPSChallenge.resolve("rock", "paper") == "b"

    def test_challenge_message_has_hash(self):
        challenge = AsyncRPSChallenge(
            challenger=make_profile("Alice"),
            challenger_throw="rock",
        )
        msg = challenge.to_challenge_message()
        assert msg.payload.get("throw_hash")
        assert len(msg.payload["throw_hash"]) == 12

    def test_move_message(self):
        challenge = AsyncRPSChallenge(challenger=make_profile("Alice"))
        msg = challenge.to_move_message(make_profile("Bob"), "paper")
        assert msg.payload["throw"] == "paper"
        assert msg.msg_type == MessageType.MOVE


class TestMUDWorld:
    def test_starter_world_has_rooms(self):
        assert len(STARTER_WORLD) >= 6

    def test_all_rooms_have_exits(self):
        for room in STARTER_WORLD:
            assert len(room.exits) > 0, f"{room.name} has no exits"

    def test_exits_are_bidirectional(self):
        """Every exit should lead to a room that exists."""
        for room in STARTER_WORLD:
            for direction, target_id in room.exits.items():
                assert target_id in STARTER_WORLD_MAP, (
                    f"{room.name} exit '{direction}' leads to unknown room '{target_id}'"
                )

    def test_town_square_is_hub(self):
        ts = STARTER_WORLD_MAP["town_square"]
        assert len(ts.exits) >= 4  # Hub should connect to many rooms

    def test_room_serialization(self):
        room = STARTER_WORLD[0]
        payload = room.to_payload()
        restored = MUDRoom.from_payload(payload)
        assert restored.room_id == room.room_id
        assert restored.name == room.name
        assert restored.exits == room.exits

    def test_rooms_have_npcs(self):
        total_npcs = sum(len(r.npcs) for r in STARTER_WORLD)
        assert total_npcs >= 8, "World should have several NPCs"

    def test_rooms_have_items(self):
        total_items = sum(len(r.items) for r in STARTER_WORLD)
        assert total_items >= 5, "World should have items to find"


class TestTradeOffer:
    def test_trade_creates_message(self):
        offer = TradeOffer(
            seller=make_profile("Merchant"),
            item_name="Slightly Haunted Top Hat",
            price=25,
            description="It whispers CSS at night.",
            category="cosmetic",
        )
        msg = offer.to_message()
        assert msg.msg_type == MessageType.TRADE
        assert msg.payload["offer"] == "Slightly Haunted Top Hat"
        assert msg.payload["price"] == 25


class TestGameLabels:
    def test_all_message_types_have_labels(self):
        for mt in MessageType:
            assert mt in GAME_LABELS, f"{mt} missing from GAME_LABELS"
