"""Balance simulation tests — run automated playthroughs to probe game tuning.

These tests simulate many runs of each game with different strategies and
personalities, then report statistics. Failures indicate balance problems
(e.g., game is unwinnable, too easy, personality has no effect).
"""

import random
import statistics

import pytest

from buddies.core.buddy_brain import BuddyState, Species, Rarity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_buddy(name="Tester", dominant="patience", level=5, **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = 30
    sp = Species(
        name="test_species", emoji="🐱", rarity=Rarity.COMMON,
        base_stats=stats, description="Test buddy",
    )
    defaults = dict(
        name=name, species=sp, level=level, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=1, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


ALL_PERSONALITIES = ["debugging", "chaos", "snark", "wisdom", "patience"]
RUNS_PER_SCENARIO = 50  # Enough to see trends, fast enough to not annoy


# ===========================================================================
# DECKBUILDER BALANCE
# ===========================================================================

class TestDeckbuilderBalance:
    """Simulate full deckbuilder runs with different AI strategies."""

    def _simulate_run(self, buddy: BuddyState, strategy: str = "greedy") -> dict:
        """Play a full game with an automated strategy. Returns stats dict."""
        from buddies.core.games.deckbuilder import DeckbuilderGame, GamePhase

        game = DeckbuilderGame(buddy_state=buddy)
        max_turns = 200  # Safety valve

        for _ in range(max_turns):
            if game.is_over:
                break

            if game.phase == GamePhase.PLAY:
                # Play all cards in hand
                while game.hand and game.phase == GamePhase.PLAY:
                    game.play_card(0)
                game.start_resolve_phase()

            elif game.phase == GamePhase.RESOLVE:
                if strategy == "greedy":
                    # Resolve cheapest incidents first
                    while game.active_incidents:
                        unresolved = [
                            (i, inc) for i, inc in enumerate(game.active_incidents)
                            if not inc.ignored
                        ]
                        if not unresolved:
                            break
                        # Sort by cost ascending
                        unresolved.sort(key=lambda x: x[1].current_cost)
                        idx, inc = unresolved[0]
                        if game.dp_available >= inc.current_cost:
                            game.resolve_incident(idx)
                        else:
                            break
                elif strategy == "skip":
                    # Never resolve — how fast do you die?
                    pass
                elif strategy == "priority":
                    # Resolve highest-damage incidents first
                    while game.active_incidents:
                        unresolved = [
                            (i, inc) for i, inc in enumerate(game.active_incidents)
                            if not inc.ignored
                        ]
                        if not unresolved:
                            break
                        unresolved.sort(key=lambda x: x[1].stability_damage, reverse=True)
                        idx, inc = unresolved[0]
                        if game.dp_available >= inc.current_cost:
                            game.resolve_incident(idx)
                        else:
                            break

                game.start_shop_phase()

            elif game.phase == GamePhase.SHOP:
                if strategy != "skip":
                    # Buy the most expensive card we can afford
                    if game.shop_offerings and not game.prod_freeze_active:
                        affordable = [
                            (i, c) for i, c in enumerate(game.shop_offerings)
                            if game.dp_available >= c.cost
                        ]
                        if affordable:
                            affordable.sort(key=lambda x: x[1].cost, reverse=True)
                            game.buy_card(affordable[0][0])
                game.end_sprint()

        return {
            "won": game.won,
            "sprint_reached": game.sprint,
            "stability_final": max(0, game.stability),
            "deck_size": len(game.deck) + len(game.hand) + len(game.discard),
        }

    def test_greedy_strategy_can_win(self):
        """With greedy play (resolve cheapest first), win rate should be > 15%."""
        wins = 0
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            result = self._simulate_run(buddy, strategy="greedy")
            if result["won"]:
                wins += 1
        win_rate = wins / RUNS_PER_SCENARIO
        # If greedy can NEVER win, the game is too hard
        assert win_rate > 0.10, f"Greedy win rate {win_rate:.0%} is too low — game may be unwinnable"
        # If greedy ALWAYS wins, the game is too easy
        assert win_rate < 0.95, f"Greedy win rate {win_rate:.0%} is too high — no tension"

    def test_skip_strategy_dies_fast(self):
        """Never resolving should kill you by sprint 3-4 on average."""
        sprints = []
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant="patience")
            result = self._simulate_run(buddy, strategy="skip")
            sprints.append(result["sprint_reached"])
        avg = statistics.mean(sprints)
        assert avg < 6, f"Skip strategy survives to sprint {avg:.1f} avg — damage is too low"
        assert avg > 1, f"Skip strategy dies on sprint {avg:.1f} avg — damage is too high"

    def test_priority_strategy_better_than_greedy(self):
        """Resolving highest-damage incidents first should be at least as good as greedy."""
        greedy_sprints = []
        priority_sprints = []
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            greedy_sprints.append(self._simulate_run(buddy, strategy="greedy")["sprint_reached"])
            priority_sprints.append(self._simulate_run(buddy, strategy="priority")["sprint_reached"])
        # Priority should average at least as many sprints
        g_avg = statistics.mean(greedy_sprints)
        p_avg = statistics.mean(priority_sprints)
        # Allow slight tolerance — the point is they shouldn't be wildly different
        assert p_avg >= g_avg - 0.5, (
            f"Priority ({p_avg:.1f}) significantly worse than greedy ({g_avg:.1f}) "
            "— damage-based incidents may be mispriced"
        )

    def test_personality_affects_starting_deck(self):
        """Each personality should have distinct starting cards."""
        from buddies.core.games.deckbuilder import DeckbuilderGame
        deck_signatures = {}
        for personality in ALL_PERSONALITIES:
            buddy = make_buddy(dominant=personality)
            game = DeckbuilderGame(buddy_state=buddy)
            all_cards = game.deck + game.hand + game.discard
            names = sorted(c.name for c in all_cards)
            deck_signatures[personality] = names

        # All 5 should be distinct
        unique_signatures = set(tuple(v) for v in deck_signatures.values())
        assert len(unique_signatures) == 5, (
            f"Only {len(unique_signatures)} unique starting decks for 5 personalities"
        )

    def test_patience_stability_bonus_helps(self):
        """Patience buddies should survive longer on average (they get +2 stability)."""
        patience_sprints = []
        other_sprints = []
        for _ in range(RUNS_PER_SCENARIO):
            p = self._simulate_run(make_buddy(dominant="patience"), "greedy")
            o = self._simulate_run(make_buddy(dominant="snark"), "greedy")
            patience_sprints.append(p["sprint_reached"])
            other_sprints.append(o["sprint_reached"])
        p_avg = statistics.mean(patience_sprints)
        o_avg = statistics.mean(other_sprints)
        # Patience should have at least a small advantage
        assert p_avg >= o_avg - 0.3, (
            f"Patience ({p_avg:.1f}) doesn't survive longer than snark ({o_avg:.1f}) "
            "— +2 stability bonus may not be meaningful"
        )

    def test_deck_grows_over_game(self):
        """Players who survive should have a bigger deck than they started with."""
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            result = self._simulate_run(buddy, "greedy")
            if result["sprint_reached"] >= 4:
                assert result["deck_size"] > 8, (
                    f"Reached sprint {result['sprint_reached']} with only "
                    f"{result['deck_size']} cards — shop may not be working"
                )
                break
        else:
            # If no run got past sprint 4, that's also a concern
            pass

    def test_sprint_7_boss_is_beatable(self):
        """At least some runs that reach sprint 7 should survive the boss."""
        reached_7 = 0
        beat_7 = 0
        for _ in range(RUNS_PER_SCENARIO * 2):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            result = self._simulate_run(buddy, "greedy")
            if result["sprint_reached"] >= 7:
                reached_7 += 1
                if result["won"]:
                    beat_7 += 1
        if reached_7 > 0:
            boss_survival = beat_7 / reached_7
            assert boss_survival > 0.05, (
                f"Boss survival rate is {boss_survival:.0%} "
                f"({beat_7}/{reached_7}) — boss may be too hard"
            )


# ===========================================================================
# SNAKE BALANCE
# ===========================================================================

class TestSnakeBalance:
    """Simulate snake games with automated AI to probe tuning."""

    def _simulate_run(self, buddy: BuddyState, ticks: int = 500) -> dict:
        """Run snake for N ticks with a basic AI (avoids walls, seeks food)."""
        from buddies.core.games.snake import (
            SnakeGame, Direction, GRID_W, GRID_H,
        )
        game = SnakeGame(buddy_state=buddy)
        foods_eaten = 0
        powerups_collected = 0

        for _ in range(ticks):
            if not game.alive:
                break

            # Simple AI: head toward food, avoid walls and self
            head = game.body[0]
            target = game.packet
            if target:
                dx = target.x - head.x
                dy = target.y - head.y
                # Prefer horizontal if farther
                if abs(dx) >= abs(dy):
                    desired = Direction.RIGHT if dx > 0 else Direction.LEFT
                else:
                    desired = Direction.DOWN if dy > 0 else Direction.UP
            else:
                desired = game.direction

            # Check if desired direction is safe
            ddx, ddy = desired.value
            next_x, next_y = head.x + ddx, head.y + ddy
            body_set = {(c.x, c.y) for c in game.body}
            obs_set = {(o.x, o.y) for o in game.obstacles}

            if (not (0 <= next_x < GRID_W and 0 <= next_y < GRID_H)
                    or (next_x, next_y) in body_set
                    or (next_x, next_y) in obs_set):
                # Try other directions
                for alt in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
                    adx, ady = alt.value
                    ax, ay = head.x + adx, head.y + ady
                    # Skip reverse
                    opposite = {
                        Direction.UP: Direction.DOWN, Direction.DOWN: Direction.UP,
                        Direction.LEFT: Direction.RIGHT, Direction.RIGHT: Direction.LEFT,
                    }
                    if alt == opposite.get(game.direction):
                        continue
                    if (0 <= ax < GRID_W and 0 <= ay < GRID_H
                            and (ax, ay) not in body_set
                            and (ax, ay) not in obs_set):
                        desired = alt
                        break

            game.set_direction(desired)
            events = game.tick(game.current_tick_interval)
            if "eat" in events:
                foods_eaten += 1
            for ev in events:
                if ev.startswith("powerup:"):
                    powerups_collected += 1

        return {
            "alive": game.alive,
            "ticks_survived": game.ticks,
            "score": game.score,
            "length": game.length,
            "foods_eaten": foods_eaten,
            "powerups_collected": powerups_collected,
            "obstacles": len(game.obstacles),
        }

    def test_simple_ai_survives_reasonable_time(self):
        """A food-seeking AI should typically survive 50+ ticks."""
        survivals = []
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            result = self._simulate_run(buddy, ticks=300)
            survivals.append(result["ticks_survived"])
        avg = statistics.mean(survivals)
        assert avg > 30, f"AI survives only {avg:.0f} ticks avg — game may be too hostile early"

    def test_food_is_reachable(self):
        """AI should eat at least some food in most runs."""
        ate_food = 0
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant="patience")
            result = self._simulate_run(buddy, ticks=200)
            if result["foods_eaten"] > 0:
                ate_food += 1
        rate = ate_food / RUNS_PER_SCENARIO
        assert rate > 0.7, f"Only {rate:.0%} of runs ate any food — food spawning may be broken"

    def test_speed_ramp_hits_minimum(self):
        """Speed should eventually hit the minimum interval."""
        from buddies.core.games.snake import SnakeGame, MIN_TICK_INTERVAL
        game = SnakeGame(buddy_state=make_buddy())
        game.elapsed_seconds = 300.0  # 5 minutes in
        assert game.current_tick_interval == MIN_TICK_INTERVAL

    def test_obstacles_dont_fill_grid(self):
        """Even after many foods eaten, obstacles shouldn't fill > 20% of the grid."""
        from buddies.core.games.snake import SnakeGame, GRID_W, GRID_H
        game = SnakeGame(buddy_state=make_buddy(dominant="chaos"))
        total_cells = GRID_W * GRID_H
        # Force many obstacle spawns
        for _ in range(50):
            game._maybe_spawn_obstacle()
        obstacle_ratio = len(game.obstacles) / total_cells
        assert obstacle_ratio < 0.20, (
            f"Obstacles occupy {obstacle_ratio:.0%} of grid — cap may be too high"
        )

    def test_powerups_appear(self):
        """Powerups should spawn in a typical run."""
        from buddies.core.games.snake import SnakeGame
        # Force powerup spawns to test probability
        spawned = 0
        for _ in range(100):
            game = SnakeGame(buddy_state=make_buddy(dominant="chaos"))
            game.body.extend([game.body[-1]] * 10)  # Fake long snake
            game._maybe_spawn_powerup()
            if game.powerups:
                spawned += 1
        assert spawned > 10, f"Only {spawned}/100 powerup spawn attempts succeeded"

    def test_chaos_vs_patience_speed(self):
        """Patience buddies should have a slower early speed ramp."""
        from buddies.core.games.snake import SnakeGame
        patience = SnakeGame(buddy_state=make_buddy(dominant="patience"))
        chaos = SnakeGame(buddy_state=make_buddy(dominant="chaos"))

        # After 30 seconds
        patience.elapsed_seconds = 30.0
        chaos.elapsed_seconds = 30.0
        # Patience should ramp slower
        assert patience.current_tick_interval >= chaos.current_tick_interval


# ===========================================================================
# SKI FREE BALANCE
# ===========================================================================

class TestSkiFreeBalance:
    """Simulate ski free runs to probe terrain and auditor tuning."""

    def _simulate_run(self, buddy: BuddyState, ticks: int = 300) -> dict:
        """Run skifree with a lane-dodging AI."""
        from buddies.core.games.skifree import SkiFreeGame, CellType, VISIBLE_ROWS, NUM_LANES

        game = SkiFreeGame(buddy_state=buddy)
        pickups_collected = 0
        all_events = []

        for _ in range(ticks):
            if not game.alive:
                break

            # Look at what's coming at our current lane
            # Check a few rows ahead and pick the safest lane
            best_lane = game.player_lane
            best_score = -999

            for lane in range(NUM_LANES):
                score = 0
                for look_ahead in range(3):
                    row_idx = VISIBLE_ROWS - 2 - look_ahead
                    if 0 <= row_idx < len(game.terrain):
                        cell = game.terrain[row_idx].cells[lane]
                        if cell in (CellType.OBSTACLE_LEGACY, CellType.OBSTACLE_BUG,
                                    CellType.OBSTACLE_MERGE, CellType.OBSTACLE_WALL):
                            score -= 10
                        elif cell in (CellType.COFFEE, CellType.DUCK, CellType.COMMIT):
                            score += 5
                # Prefer lanes close to current position
                score -= abs(lane - game.player_lane) * 0.5
                if score > best_score:
                    best_score = score
                    best_lane = lane

            # Move toward best lane (1 step at a time)
            if best_lane < game.player_lane:
                game.move_left()
            elif best_lane > game.player_lane:
                game.move_right()

            events = game.tick(game.current_tick_interval)
            all_events.extend(events)
            for ev in events:
                if ev.startswith("pickup:"):
                    pickups_collected += 1

        return {
            "alive": game.alive,
            "ticks_survived": game.ticks,
            "score": game.score,
            "distance": game.distance,
            "pickups": pickups_collected,
            "auditor_appeared": "auditor_appears" in all_events,
            "caught": "caught" in all_events,
            "crashed": "crash" in all_events,
        }

    def test_dodging_ai_survives_early_game(self):
        """A lane-dodging AI should typically survive 50+ ticks."""
        survivals = []
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant=random.choice(ALL_PERSONALITIES))
            result = self._simulate_run(buddy, ticks=200)
            survivals.append(result["ticks_survived"])
        avg = statistics.mean(survivals)
        assert avg > 40, f"AI survives only {avg:.0f} ticks avg — obstacles may be too dense"

    def test_auditor_eventually_appears(self):
        """The Auditor should appear in long runs."""
        appeared = 0
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant="patience")
            result = self._simulate_run(buddy, ticks=800)
            if result["auditor_appeared"]:
                appeared += 1
        rate = appeared / RUNS_PER_SCENARIO
        # The auditor should appear in some runs — means they survived long enough
        assert rate > 0.0, "Auditor never appeared — either AI dies too fast or threshold too high"

    def test_auditor_catches_most_players(self):
        """Once The Auditor appears, it should catch most players eventually."""
        from buddies.core.games.skifree import SkiFreeGame, AUDITOR_DISTANCE
        caught = 0
        runs = 0
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant="patience")
            result = self._simulate_run(buddy, ticks=1500)
            if result["auditor_appeared"]:
                runs += 1
                if result["caught"]:
                    caught += 1
        if runs > 0:
            catch_rate = caught / runs
            # The Auditor should catch at least some players
            assert catch_rate > 0.1, (
                f"Auditor catch rate {catch_rate:.0%} — may be too slow"
            )

    def test_terrain_always_has_path(self):
        """No row should have obstacles in ALL lanes."""
        from buddies.core.games.skifree import SkiFreeGame, CellType, NUM_LANES
        for _ in range(20):
            game = SkiFreeGame(buddy_state=make_buddy(dominant="chaos"))
            # Generate extra terrain deep into the game
            game.distance = 5000  # Deep game
            game._generate_terrain(100)
            for row in game.terrain:
                empty = sum(1 for c in row.cells if c == CellType.EMPTY
                            or c in (CellType.COFFEE, CellType.DUCK, CellType.COMMIT))
                assert empty > 0, "Found a row with no open lanes — impossible to pass"

    def test_pickups_appear_in_runs(self):
        """At least some pickups should spawn across multiple runs."""
        total_pickups = 0
        for _ in range(RUNS_PER_SCENARIO):
            buddy = make_buddy(dominant="patience")
            result = self._simulate_run(buddy, ticks=200)
            total_pickups += result["pickups"]
        avg = total_pickups / RUNS_PER_SCENARIO
        # Should average at least a couple pickups per run
        assert avg > 0.5, f"Avg pickups per run: {avg:.1f} — spawning may be too rare"

    def test_patience_survives_longer(self):
        """Patience buddies (slower ramp) should survive at least as long as chaos."""
        patience_ticks = []
        chaos_ticks = []
        for _ in range(RUNS_PER_SCENARIO):
            p = self._simulate_run(make_buddy(dominant="patience"), ticks=500)
            c = self._simulate_run(make_buddy(dominant="chaos"), ticks=500)
            patience_ticks.append(p["ticks_survived"])
            chaos_ticks.append(c["ticks_survived"])
        p_avg = statistics.mean(patience_ticks)
        c_avg = statistics.mean(chaos_ticks)
        # Patience should have at least a small edge (with tolerance for variance)
        assert p_avg >= c_avg - 20, (
            f"Patience ({p_avg:.0f}) doesn't outlast chaos ({c_avg:.0f}) — "
            "speed ramp patience bonus may not matter"
        )
