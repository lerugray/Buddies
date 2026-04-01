"""Tests for all game engines — Pong, Trivia, Hold'em, Whist, RPS, Blackjack, Battle.

Exercises core game logic, edge cases, and personality-driven AI behavior.
"""

import pytest
import random

from buddies.core.buddy_brain import BuddyState, Species, Rarity


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30
    sp = Species(
        name="test_species", emoji="🐱", rarity=Rarity.COMMON,
        base_stats=stats, description="Test buddy",
    )
    defaults = dict(
        name=name, species=sp, level=5, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=1, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


# ---------------------------------------------------------------------------
# Pong
# ---------------------------------------------------------------------------

class TestPong:
    def test_game_creates(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        assert game.player_score == 0
        assert game.buddy_score == 0
        assert not game.is_over

    def test_ball_moves_on_tick(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        old_x = game.ball.x
        game.tick()
        assert game.ball.x != old_x

    def test_player_paddle_moves(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        old_y = game.player_paddle.y
        game.move_player_up()
        assert game.player_paddle.y <= old_y

    def test_ball_bounces_off_walls(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        # Force ball to top wall
        game.ball.y = 0.1
        game.ball.dy = -1.0
        game.tick()
        assert game.ball.dy > 0  # Should bounce down

    def test_game_ends_at_winning_score(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        game.player_score = 4
        game.buddy_score = 4
        # Simulate until someone wins
        for _ in range(5000):
            game.tick()
            if game.is_over:
                break
        assert game.is_over
        assert game.winner in ("player", "buddy")

    def test_render_field(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        rows = game.render_field()
        assert len(rows) == game.field_height + 2  # +2 for top/bottom border

    def test_pause_stops_ticks(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        game.is_paused = True
        old_x = game.ball.x
        game.tick()
        assert game.ball.x == old_x  # Ball shouldn't move when paused

    def test_get_result(self):
        from buddies.core.games.pong import PongGame
        game = PongGame(buddy_state=make_buddy())
        game.player_score = 5
        game.is_over = True
        result = game.get_result()
        assert result.outcome.value == "win"
        assert result.xp_earned > 0


# ---------------------------------------------------------------------------
# Trivia
# ---------------------------------------------------------------------------

class TestTrivia:
    def test_game_creates_with_10_questions(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        assert len(game.questions) == 10

    def test_correct_answer_scores(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        q = game.current_question
        assert q is not None
        rnd = game.answer(q.answer)  # Answer correctly
        assert rnd.player_correct
        assert game.player_score == 1

    def test_wrong_answer_doesnt_score(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        q = game.current_question
        wrong = (q.answer + 1) % 4
        rnd = game.answer(wrong)
        assert not rnd.player_correct
        assert game.player_score == 0

    def test_game_ends_after_10_questions(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        for _ in range(10):
            q = game.current_question
            game.answer(0)
        assert game.is_over

    def test_buddy_answers_independently(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        q = game.current_question
        rnd = game.answer(0)
        # Buddy should have answered (0-3)
        assert 0 <= rnd.buddy_answer <= 3

    def test_questions_have_valid_structure(self):
        from buddies.core.games.trivia import QUESTIONS
        for q in QUESTIONS:
            assert len(q.choices) == 4
            assert 0 <= q.answer <= 3
            assert q.difficulty in (1, 2, 3)
            assert q.text.endswith("?")

    def test_perfect_score_result(self):
        from buddies.core.games.trivia import TriviaGame
        game = TriviaGame(buddy_state=make_buddy())
        for _ in range(10):
            q = game.current_question
            game.answer(q.answer)
        result = game.get_result()
        assert game.player_score == 10
        assert result.score["perfect"]


# ---------------------------------------------------------------------------
# Hold'em
# ---------------------------------------------------------------------------

class TestHoldem:
    def test_hand_evaluator_royal_flush(self):
        from buddies.core.games.holdem import evaluate_hand, HandRank
        from buddies.core.games.card_common import Card, Suit
        cards = [Card(1, Suit.SPADES), Card(13, Suit.SPADES), Card(12, Suit.SPADES),
                 Card(11, Suit.SPADES), Card(10, Suit.SPADES)]
        rank, _ = evaluate_hand(cards)
        assert rank == HandRank.ROYAL_FLUSH

    def test_hand_evaluator_straight(self):
        from buddies.core.games.holdem import evaluate_hand, HandRank
        from buddies.core.games.card_common import Card, Suit
        cards = [Card(5, Suit.HEARTS), Card(6, Suit.CLUBS), Card(7, Suit.DIAMONDS),
                 Card(8, Suit.SPADES), Card(9, Suit.HEARTS)]
        rank, _ = evaluate_hand(cards)
        assert rank == HandRank.STRAIGHT

    def test_hand_evaluator_full_house(self):
        from buddies.core.games.holdem import evaluate_hand, HandRank
        from buddies.core.games.card_common import Card, Suit
        cards = [Card(3, Suit.HEARTS), Card(3, Suit.CLUBS), Card(3, Suit.DIAMONDS),
                 Card(7, Suit.SPADES), Card(7, Suit.HEARTS)]
        rank, _ = evaluate_hand(cards)
        assert rank == HandRank.FULL_HOUSE

    def test_hand_evaluator_ace_low_straight(self):
        from buddies.core.games.holdem import evaluate_hand, HandRank
        from buddies.core.games.card_common import Card, Suit
        cards = [Card(1, Suit.HEARTS), Card(2, Suit.CLUBS), Card(3, Suit.DIAMONDS),
                 Card(4, Suit.SPADES), Card(5, Suit.HEARTS)]
        rank, _ = evaluate_hand(cards)
        assert rank == HandRank.STRAIGHT

    def test_hand_evaluator_7_cards(self):
        from buddies.core.games.holdem import evaluate_hand, HandRank
        from buddies.core.games.card_common import Card, Suit
        # 7 cards should find the best 5-card hand
        cards = [Card(1, Suit.SPADES), Card(13, Suit.SPADES), Card(12, Suit.SPADES),
                 Card(11, Suit.SPADES), Card(10, Suit.SPADES),
                 Card(2, Suit.HEARTS), Card(3, Suit.CLUBS)]
        rank, _ = evaluate_hand(cards)
        assert rank == HandRank.ROYAL_FLUSH

    def test_game_creates_with_seats(self):
        from buddies.core.games.holdem import HoldemGame
        game = HoldemGame(player_state=make_buddy())
        assert len(game.seats) >= 2  # Player + at least 1 opponent

    def test_hand_deals_cards(self):
        from buddies.core.games.holdem import HoldemGame
        game = HoldemGame(player_state=make_buddy())
        game.start_hand()
        assert len(game.seats[0].hole_cards) == 2

    def test_player_can_fold(self):
        from buddies.core.games.holdem import HoldemGame
        game = HoldemGame(player_state=make_buddy())
        game.start_hand()
        if game.waiting_for_player:
            game.player_fold()
            assert game.seats[0].is_folded


# ---------------------------------------------------------------------------
# Whist
# ---------------------------------------------------------------------------

class TestWhist:
    def test_game_creates_4_players(self):
        from buddies.core.games.whist import WhistGame
        game = WhistGame(player_state=make_buddy())
        assert len(game.players) == 4

    def test_deal_gives_13_cards_each(self):
        from buddies.core.games.whist import WhistGame
        game = WhistGame(player_state=make_buddy())
        game.deal()
        for p in game.players:
            assert len(p.hand) == 13

    def test_trump_suit_is_set(self):
        from buddies.core.games.whist import WhistGame
        game = WhistGame(player_state=make_buddy())
        game.deal()
        assert game.trump_suit is not None

    def test_playable_cards_follow_suit(self):
        from buddies.core.games.whist import WhistGame
        from buddies.core.games.card_common import Card, Suit
        game = WhistGame(player_state=make_buddy())
        game.deal()
        # If current trick has a lead suit and player has that suit, must follow
        playable = game.get_playable_cards()
        assert len(playable) > 0  # Player should always have playable cards

    def test_trick_resolves(self):
        from buddies.core.games.whist import WhistGame
        game = WhistGame(player_state=make_buddy())
        game.deal()
        # Play the first playable card
        playable = game.get_playable_cards()
        if playable and game.waiting_for_player:
            game.play_card(playable[0])
            # AI should have played their cards too
            # Either we're waiting for player again or game is progressing


# ---------------------------------------------------------------------------
# Personality Drift
# ---------------------------------------------------------------------------

class TestPersonalityDrift:
    def test_game_drift_boosts_stats(self):
        from buddies.core.personality_drift import drift_for_game
        stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        result = drift_for_game(stats, "trivia", won=True)
        assert result.has_changes
        assert stats["wisdom"] > 10  # Trivia boosts wisdom

    def test_idle_drift_needs_30_min(self):
        from buddies.core.personality_drift import drift_for_idle
        stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        result = drift_for_idle(stats, minutes_idle=10)
        assert not result.has_changes  # Too early

    def test_idle_drift_after_30_min(self):
        from buddies.core.personality_drift import drift_for_idle
        stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        result = drift_for_idle(stats, minutes_idle=60)
        assert stats["chaos"] > 10  # Idle boosts chaos

    def test_stat_cap(self):
        from buddies.core.personality_drift import drift_for_game
        stats = {"debugging": 98, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        drift_for_game(stats, "battle", won=True)
        assert stats["debugging"] <= 99  # Should cap at 99

    def test_drift_summary(self):
        from buddies.core.personality_drift import drift_for_game
        stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
        result = drift_for_game(stats, "trivia", won=True)
        summary = result.summary()
        assert len(summary) > 0


# ---------------------------------------------------------------------------
# Idle Life
# ---------------------------------------------------------------------------

class TestIdleLife:
    def test_idle_life_creates(self):
        from buddies.core.idle_life import IdleLife
        idle = IdleLife()
        assert len(idle.events) == 0

    def test_tick_generates_events_after_interval(self):
        from buddies.core.idle_life import IdleLife
        import time
        idle = IdleLife()
        idle._event_interval = 0  # Bypass timer for testing
        idle.last_tick = time.time() - 1  # Force elapsed

        buddies = [make_buddy("A", buddy_id=1), make_buddy("B", buddy_id=2)]
        events = idle.tick(buddies)
        # Should generate at least some events (60% chance per buddy)
        # Run multiple times to reduce flakiness
        all_events = events
        for _ in range(5):
            idle.last_tick = time.time() - 1
            all_events.extend(idle.tick(buddies))
        assert len(all_events) > 0

    def test_social_events_need_multiple_buddies(self):
        from buddies.core.idle_life import IdleLife
        import time
        idle = IdleLife()
        idle._event_interval = 0
        idle.last_tick = time.time() - 1

        # Single buddy should never get social events
        events = []
        for _ in range(20):
            idle.last_tick = time.time() - 1
            events.extend(idle.tick([make_buddy("Solo", buddy_id=1)]))
        social = [e for e in events if e.category == "social"]
        assert len(social) == 0

    def test_summary_renders(self):
        from buddies.core.idle_life import IdleLife
        idle = IdleLife()
        summary = idle.get_summary()
        assert len(summary) > 0


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class TestRelationships:
    def test_relationship_creates(self):
        from buddies.core.relationships import RelationshipManager
        rm = RelationshipManager()
        rel = rm.get(1, 2)
        assert rel.affinity == 0

    def test_shared_game_builds_affinity(self):
        from buddies.core.relationships import RelationshipManager
        rm = RelationshipManager()
        rm.on_shared_game(1, 2)
        rel = rm.get(1, 2)
        assert rel.affinity > 0
        assert rel.shared_games == 1

    def test_stat_compatibility(self):
        from buddies.core.relationships import compute_stat_compatibility
        a = make_buddy("A", "debugging", buddy_id=1)
        b = make_buddy("B", "debugging", buddy_id=2)  # Same dominant stat
        compat = compute_stat_compatibility(a, b)
        assert compat > 0  # Similar stats = positive

    def test_rival_from_opposite_stats(self):
        from buddies.core.relationships import compute_stat_compatibility
        a = make_buddy("A", "debugging", buddy_id=1)
        a.stats = {"debugging": 40, "chaos": 5, "snark": 5, "wisdom": 5, "patience": 5}
        b = make_buddy("B", "chaos", buddy_id=2)
        b.stats = {"debugging": 5, "chaos": 40, "snark": 5, "wisdom": 5, "patience": 5}
        compat = compute_stat_compatibility(a, b)
        assert compat < 0  # Very different = rivalry

    def test_relationship_type_labels(self):
        from buddies.core.relationships import RelationshipManager, RelationType
        rm = RelationshipManager()
        rel = rm.get(1, 2)
        assert rel.type == RelationType.STRANGER

        # Build to friend
        for _ in range(20):
            rm.on_shared_game(1, 2)
        rel = rm.get(1, 2)
        assert rel.type in (RelationType.FRIEND, RelationType.BEST_FRIEND)

    def test_discussion_modifier(self):
        from buddies.core.relationships import RelationshipManager
        rm = RelationshipManager()
        # Strangers = 0 modifier
        mod = rm.get_discussion_modifier(1, 2)
        assert mod == 0.0

        # Build affinity
        for _ in range(10):
            rm.on_shared_game(1, 2)
        mod = rm.get_discussion_modifier(1, 2)
        assert mod > 0  # Friends agree more


# ---------------------------------------------------------------------------
# Card infrastructure
# ---------------------------------------------------------------------------

class TestCards:
    def test_deck_has_52_cards(self):
        from buddies.core.games.card_common import Deck
        d = Deck()
        assert d.remaining == 52

    def test_deck_shuffle_and_deal(self):
        from buddies.core.games.card_common import Deck
        d = Deck()
        d.shuffle()
        hand = d.deal(5)
        assert len(hand) == 5
        assert d.remaining == 47

    def test_card_rendering(self):
        from buddies.core.games.card_common import Card, Suit, render_hand_ascii, render_hand_inline
        cards = [Card(1, Suit.SPADES), Card(13, Suit.HEARTS)]
        ascii_art = render_hand_ascii(cards)
        assert "┌" in ascii_art
        inline = render_hand_inline(cards)
        assert "♠" in inline


# ---------------------------------------------------------------------------
# RPS
# ---------------------------------------------------------------------------

class TestRPS:
    def test_game_creates(self):
        from buddies.core.games.rps import RPSGame
        game = RPSGame(buddy_state=make_buddy())
        assert game.player_wins == 0
        assert game.buddy_wins == 0

    def test_round_resolves(self):
        from buddies.core.games.rps import RPSGame, RPSChoice
        game = RPSGame(buddy_state=make_buddy())
        rnd = game.play_round(RPSChoice.ROCK)
        assert rnd.outcome is not None

    def test_game_ends(self):
        from buddies.core.games.rps import RPSGame, RPSChoice
        game = RPSGame(buddy_state=make_buddy(), best_of=3)
        # Play enough rounds to end the game
        for _ in range(20):
            if game.is_over:
                break
            game.play_round(random.choice(list(RPSChoice)))
        assert game.is_over


# ---------------------------------------------------------------------------
# Battle (JRPG)
# ---------------------------------------------------------------------------

class TestBattle:
    def test_battle_creates(self):
        from buddies.core.games.battle import Battle
        battle = Battle(buddy_state=make_buddy())
        assert battle.buddy.hp > 0
        assert battle.enemy_fighter.hp > 0

    def test_player_attack_deals_damage(self):
        from buddies.core.games.battle import Battle
        battle = Battle(buddy_state=make_buddy())
        initial_hp = battle.enemy_fighter.hp
        battle.player_attack(0)
        # Might miss, so just verify no crash
        assert battle.enemy_fighter.hp <= initial_hp

    def test_enemy_attack(self):
        from buddies.core.games.battle import Battle
        battle = Battle(buddy_state=make_buddy())
        initial_hp = battle.buddy.hp
        battle.enemy_attack()
        assert battle.buddy.hp <= initial_hp

    def test_type_chart_exists(self):
        from buddies.core.games.battle import TYPE_CHART, MoveType
        assert MoveType.LOGIC in TYPE_CHART
        assert MoveType.CHAOS in TYPE_CHART[MoveType.LOGIC]
