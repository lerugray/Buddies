"""Buddy — Main Textual TUI application."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Input, Footer

from buddies.config import BuddyConfig
from buddies.core.buddy_brain import (
    BuddyState,
    pick_species,
    SPECIES_CATALOG,
    check_hat_unlock,
    check_evolution,
    get_mood_modifier,
)
from buddies.core.ai_backend import create_backend
from buddies.core.prose import ProseEngine
from buddies.core.ai_router import AIRouter
from buddies.core.rule_suggester import RuleSuggester
from buddies.core.session_observer import SessionObserver, SessionEvent
from buddies.db.store import BuddyStore
from buddies.first_run import HatchScreen
from buddies.widgets.buddy_display import BuddyDisplay, SpriteDisplay
from buddies.widgets.chat import ChatWindow
from buddies.widgets.session_monitor import SessionMonitor

from buddies.screens.party import PartyScreen


CSS_PATH = Path(__file__).parent / "styles" / "buddy.tcss"


class BuddyApp(App):
    """The main Buddy companion application."""

    TITLE = "🐾 BUDDIES"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "help", "Help", show=True),
        Binding("f5", "refresh", "Refresh", show=True),
        Binding("r", "hatch_new", "Hatch New", show=True),
        Binding("p", "party", "Party", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.config = BuddyConfig.load()
        self.store = BuddyStore(self.config.db_path)
        self.buddy_state: BuddyState | None = None
        self.observer = SessionObserver()
        self.ai_backend = create_backend(self.config.ai_backend)
        self.router: AIRouter | None = None
        self.rule_suggester: RuleSuggester | None = None
        self.prose = ProseEngine()
        self._last_thought_time: float = 0
        self._recent_tools: list[str] = []
        self._bored_minutes: float = 0  # Track sustained boredom for nightcap

    def compose(self) -> ComposeResult:
        yield Static("🐾 BUDDIES — Your AI Companions", id="title-bar")
        yield BuddyDisplay(id="buddy-panel")
        yield ChatWindow(id="chat-panel")
        yield SessionMonitor(id="session-panel")
        yield Footer()

    async def on_mount(self):
        await self.store.connect()
        await self.ai_backend.connect()

        # Check if we need to hatch a new buddy
        data = await self.store.get_active_buddy()
        if data:
            self.buddy_state = BuddyState.from_db(data)
            self._finish_setup()
        else:
            # First run — show hatch screen (must use callback, not await)
            self.push_screen(HatchScreen(), callback=self._on_hatch_complete)

    async def _on_hatch_complete(self, result) -> None:
        """Called when the hatch screen is dismissed (first run only)."""
        if result:
            species, shiny, seed, name = result
            self.config.user_seed = seed
            self.config.save()
        else:
            species, shiny = pick_species(self.config.user_seed)
            name = "Buddy"

        soul = f"A {species.rarity.value} {species.name} companion, born to help."
        await self.store.create_buddy(
            species=species.name,
            name=name,
            shiny=shiny,
            soul_description=soul,
        )
        data = await self.store.get_active_buddy()
        self.buddy_state = BuddyState.from_db(data)
        self._finish_setup()

    def _finish_setup(self):
        """Set up the rest of the app after buddy is loaded/hatched."""
        # Initialize AI router and rule suggester
        self.router = AIRouter(self.ai_backend, self.buddy_state)
        self.rule_suggester = RuleSuggester(self.store)
        asyncio.create_task(self.rule_suggester.load_dismissed())

        self._update_displays()

        # Welcome message
        chat = self.query_one("#chat-panel", ChatWindow)
        chat.add_system(f"{self.buddy_state.species.emoji} {self.buddy_state.name} hatched!")
        chat.add_message("buddy", self._get_greeting())

        # Show AI backend status
        asyncio.create_task(self._show_ai_status())

        # Log startup and start session observer
        session = self.query_one("#session-panel", SessionMonitor)
        session.log_event("session", "Buddy started up", 0)

        # Wire up session observer
        self.observer.on_event(self._on_session_event)
        self.observer.on_pattern(self._on_pattern_detected)
        self._observer_task = asyncio.create_task(self.observer.start())
        self._rule_check_task = asyncio.create_task(self._periodic_rule_check())
        self._idle_thought_task = asyncio.create_task(self._idle_thought_loop())
        self._mood_decay_task = asyncio.create_task(self._mood_decay_loop())

    async def _show_ai_status(self):
        ai_available = await self.ai_backend.is_available()
        chat = self.query_one("#chat-panel", ChatWindow)
        if ai_available:
            chat.add_system(f"🧠 Local AI connected: {self.config.ai_backend.model}")
        else:
            chat.add_system("💤 No local AI connected — using personality mode")

    def _update_displays(self):
        """Push current buddy state to all widgets."""
        if not self.buddy_state:
            return
        buddy_display = self.query_one("#buddy-panel", BuddyDisplay)
        buddy_display.update_buddy(self.buddy_state)

    def _get_greeting(self) -> str:
        """Get a mood-appropriate greeting from buddies."""
        if not self.buddy_state:
            return "Hello!"
        greetings = {
            "ecstatic": "I'm SO happy to see you! Let's build something amazing! 🎉",
            "happy": "Hey there! Ready to get some work done? 😊",
            "neutral": "Hi. What are we working on today?",
            "bored": "Oh, you're here. Finally. I was getting restless...",
            "grumpy": "Hmph. About time. Let's just get to work.",
        }
        return greetings.get(self.buddy_state.mood, "Hello!")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle chat input."""
        if event.input.id != "chat-input":
            return

        message = event.value.strip()
        if not message:
            return

        event.input.value = ""
        chat = self.query_one("#chat-panel", ChatWindow)
        chat.add_message("you", message)

        # Route through AI router
        if self.router:
            decision = await self.router.route(message)

            if decision.route == "buddy_only":
                # Buddy handles directly with personality
                response = self._buddy_respond(message)
                chat.add_message("buddy", response)
            elif decision.route == "local":
                # Local AI handled it
                chat.add_message("buddy", decision.response)
                chat.add_system(
                    f"[dim]✅ Handled locally — saved ~{decision.tokens_saved:,} tokens "
                    f"(total saved: ~{self.router.tokens_saved:,})[/]"
                )
                monitor = self.query_one("#session-panel", SessionMonitor)
                monitor.log_event("info", f"Local AI: saved ~{decision.tokens_saved} tokens")
            elif decision.route == "claude":
                # Too complex for local
                chat.add_message("buddy", decision.response)
                chat.add_system(
                    f"[dim]Complexity: {decision.complexity_score:.0%} — {decision.reason}[/]"
                )
        else:
            response = self._buddy_respond(message)
            chat.add_message("buddy", response)

        # Gain XP for interaction (mood-modified)
        if self.buddy_state:
            old_level = self.buddy_state.level
            mood_mod = get_mood_modifier(self.buddy_state.mood)
            xp_gain = int(5 * mood_mod["xp_multiplier"])
            leveled = self.buddy_state.gain_xp(xp_gain)
            self.buddy_state.adjust_mood(2)
            await self.store.update_buddy_by_id(
                self.buddy_state.buddy_id,
                xp=self.buddy_state.xp,
                level=self.buddy_state.level,
                mood=self.buddy_state.mood,
                mood_value=self.buddy_state.mood_value,
            )
            if leveled:
                chat.add_system(f"🎉 {self.buddy_state.name} reached level {self.buddy_state.level}!")
                # Celebration animation
                try:
                    sprite = self.query_one("#buddy-sprite", SpriteDisplay)
                    sprite.celebrate(6)
                except Exception:
                    pass
                lvl_thought = self.prose.thought("level_up", self.buddy_state, {"level": self.buddy_state.level})
                if lvl_thought:
                    chat.add_message("buddy", f"💭 {lvl_thought}")
                # Check for evolution
                evolution = check_evolution(old_level, self.buddy_state.level)
                if evolution:
                    chat.add_system(
                        f"✨ {self.buddy_state.name} evolved to "
                        f"{evolution['symbol']} {evolution['name']}!"
                    )
                    evo_thought = self.prose.thought(
                        "evolution", self.buddy_state,
                        {"stage": evolution["name"]},
                    )
                    if evo_thought:
                        chat.add_message("buddy", f"💭 {evo_thought}")
            self._update_displays()
            # Check for newly unlocked hats
            asyncio.create_task(self._check_and_unlock_hats())

    def _buddy_respond(self, message: str) -> str:
        """Generate a response from buddy (pre-AI fallback)."""
        if not self.buddy_state:
            return "..."

        msg_lower = message.lower()

        if any(w in msg_lower for w in ["hello", "hi", "hey", "sup"]):
            return self._get_greeting()
        elif any(w in msg_lower for w in ["stats", "status", "how are you"]):
            s = self.buddy_state
            return (
                f"I'm feeling {s.mood}! "
                f"Level {s.level}, {s.stat_total()} total stat points. "
                f"My strongest stat is {max(s.stats, key=s.stats.get)}."
            )
        elif any(w in msg_lower for w in ["session", "tokens", "usage", "cost", "saved"]):
            stats = self.observer.stats
            saved = self.router.tokens_saved if self.router else 0
            return (
                f"Session: {stats.event_count} events, "
                f"~{stats.tokens_estimated:,} tokens used by Claude, "
                f"~{saved:,} tokens saved by me. "
                f"Running for {stats.duration_minutes:.1f} min. "
                f"Most used tool: {stats.most_used_tool}."
            )
        elif any(w in msg_lower for w in ["help", "what can you do"]):
            return (
                "I can chat, answer simple questions locally (saving Claude tokens), "
                "watch your Claude sessions, suggest config improvements, "
                "and track my own stats. Try asking me a coding question!"
            )
        elif any(w in msg_lower for w in ["name", "who are you", "what are you"]):
            s = self.buddy_state
            shiny = " (shiny!)" if s.shiny else ""
            return (
                f"I'm {s.name}, a {s.species.rarity.value} {s.species.name}{shiny}. "
                f"{s.species.description}"
            )
        else:
            # Personality-flavored generic responses based on highest stat
            top_stat = max(self.buddy_state.stats, key=self.buddy_state.stats.get)
            responses = {
                "debugging": "Hmm, interesting. Let me think about that from a debugging perspective...",
                "patience": "I hear you. Take your time, we'll figure this out together.",
                "chaos": "CHAOS REIGNS! ...I mean, that's an interesting thought. 🔥",
                "wisdom": "A wise question. The answer often lies in the question itself.",
                "snark": "Oh, is THAT what we're doing now? Sure, I guess. 😏",
            }
            return responses.get(top_stat, "Interesting! Tell me more.")

    async def _notify_hat_found(self, hat_name: str):
        """Persist and notify about a hat found via ecstatic mood bonus."""
        if self.buddy_state:
            await self.store.update_buddy_by_id(
                self.buddy_state.buddy_id,
                hats_owned=json.dumps(self.buddy_state.hats_owned),
            )
            try:
                chat = self.query_one("#chat-panel", ChatWindow)
                chat.add_system(f"🎩 {self.buddy_state.name} found a {hat_name} hat! (ecstatic bonus)")
            except Exception:
                pass

    async def _check_and_unlock_hats(self):
        """Check which hats are newly unlocked and notify user."""
        if not self.buddy_state:
            return
        newly_unlocked = check_hat_unlock(self.buddy_state)
        if not newly_unlocked:
            return
        # Persist unlocked hats to DB
        self.buddy_state.hats_owned.extend(newly_unlocked)
        await self.store.update_buddy_by_id(
            self.buddy_state.buddy_id,
            hats_owned=json.dumps(self.buddy_state.hats_owned),
        )
        chat = self.query_one("#chat-panel", ChatWindow)
        for hat in newly_unlocked:
            chat.add_system(f"🎩 {self.buddy_state.name} unlocked the {hat} hat!")

    def _on_session_event(self, event: SessionEvent):
        """Handle a new session event from the observer."""
        # Determine event category for the monitor
        tool_categories = {
            "Edit": "edit", "Write": "edit",
            "Read": "read",
            "Bash": "bash",
            "Grep": "search", "Glob": "search",
            "Agent": "tool_use",
            "WebSearch": "search", "WebFetch": "search",
        }
        category = tool_categories.get(event.tool_name, "info")
        if event.event_type in ("SessionStart", "SessionEnd"):
            category = "session"

        # Update session monitor
        try:
            monitor = self.query_one("#session-panel", SessionMonitor)
            monitor.log_event(category, event.summary, event.tokens_estimated)
        except Exception:
            pass

        # Animate buddy — speed up during active sessions
        try:
            sprite = self.query_one("#buddy-sprite", SpriteDisplay)
            sprite.set_activity("excited")
        except Exception:
            pass

        # Buddy reacts to events — gains XP from watching sessions
        if self.buddy_state and event.event_type == "PreToolUse":
            mood_mod = get_mood_modifier(self.buddy_state.mood)
            xp_gain = max(1, int(1 * mood_mod["xp_multiplier"]))
            self.buddy_state.gain_xp(xp_gain)
            # Specific stat boosts based on what Claude is doing
            if event.tool_name in ("Edit", "Write"):
                self.buddy_state.stats["debugging"] = min(99, self.buddy_state.stats["debugging"] + 1)
            elif event.tool_name == "Agent":
                self.buddy_state.stats["wisdom"] = min(99, self.buddy_state.stats["wisdom"] + 1)
            elif event.tool_name == "Bash":
                self.buddy_state.stats["chaos"] = min(99, self.buddy_state.stats["chaos"] + 1)
            # Mood bonus stat (bored = patience, grumpy = snark)
            bonus_stat = mood_mod.get("bonus_stat")
            if bonus_stat:
                self.buddy_state.stats[bonus_stat] = min(99, self.buddy_state.stats[bonus_stat] + 1)
            # Ecstatic hat discovery chance
            if mood_mod["hat_discovery_chance"] > 0:
                import random
                if random.random() < mood_mod["hat_discovery_chance"]:
                    all_hats = ["crown", "wizard", "propeller", "tophat", "halo", "horns", "flower", "headphones", "nightcap"]
                    unowned = [h for h in all_hats if h not in self.buddy_state.hats_owned]
                    if unowned:
                        found = random.choice(unowned)
                        self.buddy_state.hats_owned.append(found)
                        asyncio.create_task(self._notify_hat_found(found))
            # Headphones hat: unlocked at 100 session events
            if (self.observer.stats.event_count >= 100
                    and "headphones" not in self.buddy_state.hats_owned):
                self.buddy_state.hats_owned.append("headphones")
                asyncio.create_task(self._notify_hat_found("headphones"))
            # Check for hat unlocks after stat boosts
            asyncio.create_task(self._check_and_unlock_hats())

        # --- Prose engine: buddy thoughts ---
        if self.buddy_state:
            self._recent_tools.append(event.tool_name)
            if len(self._recent_tools) > 10:
                self._recent_tools = self._recent_tools[-10:]

            trigger = self._detect_trigger(event)
            now = time.time()
            if trigger and now - self._last_thought_time > 30:
                ctx = {
                    "count": self.observer.stats.event_count,
                    "minutes": self.observer.stats.duration_minutes,
                    "tool": event.tool_name,
                }
                thought = self.prose.thought(trigger, self.buddy_state, ctx)
                if thought:
                    try:
                        chat = self.query_one("#chat-panel", ChatWindow)
                        chat.add_message("buddy", f"💭 {thought}")
                        self._last_thought_time = now
                    except Exception:
                        pass

    def _on_pattern_detected(self, pattern_type: str, description: str):
        """Handle a detected pattern from the session observer."""
        try:
            chat = self.query_one("#chat-panel", ChatWindow)
            chat.add_message("buddy", f"💡 I noticed something: {description}")

            monitor = self.query_one("#session-panel", SessionMonitor)
            monitor.log_event("info", f"Pattern: {pattern_type}")

            self.notify(f"Pattern: {pattern_type}")
        except Exception:
            pass

    def _detect_trigger(self, event: SessionEvent) -> str | None:
        """Detect what kind of thought trigger this event should produce."""
        if event.event_type == "SessionStart":
            return "session_start"

        if event.event_type != "PreToolUse":
            return None

        recent = self._recent_tools[-5:]

        # Edit storm: 3+ edits in last 5 tools
        if recent.count("Edit") + recent.count("Write") >= 3:
            return "edit_storm"

        # Big read: 3+ reads in last 5
        if recent.count("Read") >= 3:
            return "big_read"

        # Agent spawn
        if event.tool_name == "Agent":
            return "agent_spawn"

        # Bash run (test detection via summary)
        if event.tool_name == "Bash":
            summary_lower = event.summary.lower()
            if any(w in summary_lower for w in ["test", "pytest", "jest", "cargo test"]):
                return "test_run"
            return "bash_run"

        # Long session (only trigger once per 10 minutes)
        if self.observer.stats.duration_minutes > 30:
            return "long_session"

        return None

    async def _idle_thought_loop(self):
        """Periodically emit idle thoughts and slow animation when nothing is happening."""
        while True:
            await asyncio.sleep(120)
            if not self.buddy_state:
                continue
            now = time.time()
            if now - self._last_thought_time > 120:
                # Slow down animation — buddy is getting bored
                try:
                    sprite = self.query_one("#buddy-sprite", SpriteDisplay)
                    sprite.set_activity("sleepy")
                except Exception:
                    pass
                ctx = {
                    "count": self.observer.stats.event_count,
                    "minutes": self.observer.stats.duration_minutes,
                }
                thought = self.prose.thought("idle", self.buddy_state, ctx)
                if thought:
                    try:
                        chat = self.query_one("#chat-panel", ChatWindow)
                        chat.add_message("buddy", f"💭 {thought}")
                        self._last_thought_time = now
                    except Exception:
                        pass

    async def _mood_decay_loop(self):
        """Mood drifts toward neutral (50) every 90 seconds. Sustained boredom unlocks nightcap."""
        while True:
            await asyncio.sleep(90)
            if not self.buddy_state:
                continue

            old_mood = self.buddy_state.mood
            # Drift toward neutral: -2 if above 50, +2 if below 50
            if self.buddy_state.mood_value > 50:
                self.buddy_state.adjust_mood(-2)
            elif self.buddy_state.mood_value < 50:
                self.buddy_state.adjust_mood(1)

            # Track boredom for nightcap hat
            if self.buddy_state.mood in ("bored", "grumpy"):
                self._bored_minutes += 1.5  # 90 seconds = 1.5 minutes
            else:
                self._bored_minutes = max(0, self._bored_minutes - 0.5)

            # Nightcap hat: 10+ minutes of boredom
            if (self._bored_minutes >= 10
                    and "nightcap" not in self.buddy_state.hats_owned):
                self.buddy_state.hats_owned.append("nightcap")
                asyncio.create_task(self._notify_hat_found("nightcap"))

            # Persist mood changes
            await self.store.update_buddy_by_id(
                self.buddy_state.buddy_id,
                mood=self.buddy_state.mood,
                mood_value=self.buddy_state.mood_value,
            )

            # Update display if mood changed
            if self.buddy_state.mood != old_mood:
                self._update_displays()

    async def _periodic_rule_check(self):
        """Periodically analyze session patterns and suggest rules."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            if self.rule_suggester and self.observer.stats.event_count > 5:
                try:
                    suggestions = await self.rule_suggester.analyze(self.observer.stats)
                    chat = self.query_one("#chat-panel", ChatWindow)
                    for s in suggestions[:2]:  # Max 2 suggestions at a time
                        chat.add_message(
                            "buddy",
                            f"💡 **Suggestion: {s.title}**\n{s.description}"
                        )
                        if s.config_snippet:
                            chat.add_system(f"Config snippet:\n{s.config_snippet}")
                        monitor = self.query_one("#session-panel", SessionMonitor)
                        monitor.log_event("info", f"Rule suggested: {s.title}")
                except Exception:
                    pass

    def action_help(self):
        chat = self.query_one("#chat-panel", ChatWindow)
        chat.add_system("─── Help ───")
        chat.add_system("Type messages to chat with your buddy")
        chat.add_system("Simple questions → handled locally (saves Claude tokens)")
        chat.add_system("Complex questions → buddy tells you to ask Claude")
        chat.add_system("Commands: 'stats' 'help' 'name' 'session' 'tokens'")
        chat.add_system("Keys: [q] quit  [?] help  [r] hatch new  [p] party  [F5] refresh")
        chat.add_system("────────────")

    def action_hatch_new(self):
        """Open the hatch screen to create a new buddy (keep existing buddies)."""
        self.push_screen(HatchScreen(), callback=self._on_hatch_new_complete)

    async def _on_hatch_new_complete(self, result) -> None:
        """Create a new buddy (add to collection, don't delete existing)."""
        if not result:
            return  # User cancelled

        species, shiny, seed, name = result
        self.config.user_seed = seed
        self.config.save()

        soul = f"A {species.rarity.value} {species.name} companion, born to help."
        await self.store.create_buddy(
            species=species.name,
            name=name,
            shiny=shiny,
            soul_description=soul,
        )
        data = await self.store.get_active_buddy()
        self.buddy_state = BuddyState.from_db(data)

        if self.router:
            self.router.buddy_state = self.buddy_state

        self._update_displays()
        chat = self.query_one("#chat-panel", ChatWindow)
        chat.add_system(f"🥚 New buddy hatched! {species.emoji} {name}!")
        chat.add_message("buddy", self._get_greeting())

    def action_party(self):
        """Open the party screen to switch or manage buddies."""
        self.push_screen(PartyScreen(self.store), callback=self._on_party_dismissed)

    async def _on_party_dismissed(self, result) -> None:
        """Handle party screen dismissal."""
        if result is None:
            return

        # If user requested a new hatch, open the hatch screen
        if result == "hatch_new":
            self.action_hatch_new()
            return

        # Otherwise, switch to the selected buddy
        data = await self.store.get_buddy_by_id(result)
        if data:
            await self.store.set_active_buddy(result)
            self.buddy_state = BuddyState.from_db(data)
            if self.router:
                self.router.buddy_state = self.buddy_state
            self._update_displays()
            chat = self.query_one("#chat-panel", ChatWindow)
            chat.add_system(f"Switched to {self.buddy_state.name}!")

    def action_refresh(self):
        self._update_displays()

    async def on_unmount(self):
        self.observer.stop()
        for task_name in ('_observer_task', '_rule_check_task', '_idle_thought_task', '_mood_decay_task'):
            task = getattr(self, task_name, None)
            if task:
                task.cancel()
        await self.ai_backend.close()
        if self.buddy_state:
            await self.store.update_buddy_by_id(
                self.buddy_state.buddy_id,
                xp=self.buddy_state.xp,
                level=self.buddy_state.level,
                mood=self.buddy_state.mood,
                mood_value=self.buddy_state.mood_value,
                stat_debugging=self.buddy_state.stats["debugging"],
                stat_patience=self.buddy_state.stats["patience"],
                stat_chaos=self.buddy_state.stats["chaos"],
                stat_wisdom=self.buddy_state.stats["wisdom"],
                stat_snark=self.buddy_state.stats["snark"],
            )
        await self.store.close()


def main():
    app = BuddyApp()
    app.run()


if __name__ == "__main__":
    main()
