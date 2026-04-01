"""DiscussionScreen — party focus group conversations.

Buddies in your party discuss topics, react to each other, and comment on files.
Three modes: open chat, guided topic, and file focus.
"""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center
from textual.widgets import Static, Input, Footer, RichLog
from textual.screen import Screen

from buddies.core.ai_backend import AIBackend
from buddies.core.buddy_brain import BuddyState, SPECIES_CATALOG
from buddies.core.discussion import DiscussionEngine, DiscussionMessage
from buddies.core.prose import ProseEngine
from buddies.db.store import BuddyStore
from buddies.widgets.styling import format_discussion_message


class DiscussionScreen(Screen):
    """Party focus group — buddies discuss and react to each other."""

    CSS = """
    DiscussionScreen {
        background: $background;
    }

    #discussion-title {
        text-align: center;
        text-style: bold;
        color: $text;
        height: 1;
        margin: 1 0 0 0;
    }

    #discussion-mode {
        text-align: center;
        height: 1;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    #discussion-log {
        height: 1fr;
        border: solid $primary;
        margin: 0 1;
        padding: 1;
    }

    #discussion-input {
        dock: bottom;
        margin: 1 1;
    }

    #discussion-help {
        text-align: center;
        height: 1;
        color: $text-muted;
        margin: 0 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("n", "new_round", "New Round", show=True),
        Binding("g", "guided", "Topic", show=True),
        Binding("f", "file_focus", "File", show=True),
    ]

    def __init__(
        self,
        store: BuddyStore,
        prose: ProseEngine,
        ai_backend: AIBackend | None = None,
    ):
        super().__init__()
        self.store = store
        self.prose = prose
        self.engine = DiscussionEngine(prose, ai_backend=ai_backend)
        self.participants: list[BuddyState] = []
        self._mode = "open"
        self._input_target = ""  # "topic" or "file"
        self._discussing = False

    def compose(self) -> ComposeResult:
        yield Static("💬 PARTY DISCUSSION 💬", id="discussion-title")
        yield Static("[dim]open chat[/]", id="discussion-mode")
        yield RichLog(id="discussion-log", wrap=True, highlight=True, markup=True)
        yield Input(
            placeholder="Enter topic or file path...",
            id="discussion-input",
        )
        yield Static(
            "[dim]esc=close  n=new round  g=guided topic  f=file focus[/]",
            id="discussion-help",
        )
        yield Footer()

    async def on_mount(self):
        """Load all buddies as participants and start first discussion."""
        # Hide input initially (only shown for guided/file modes)
        self.query_one("#discussion-input", Input).display = False

        # Load all buddies
        all_buddies = await self.store.get_all_buddies()
        for buddy_data in all_buddies:
            state = BuddyState.from_db(buddy_data)
            self.participants.append(state)

        log = self.query_one("#discussion-log", RichLog)

        if not self.participants:
            log.write("[dim]No buddies to discuss! Hatch some friends first.[/]")
            return

        if len(self.participants) == 1:
            log.write(
                "[dim]Only one buddy — it's a monologue! "
                "Hatch more friends for real discussions.[/]"
            )

        # Start with an open chat round
        await self._run_discussion("open")

    def action_close(self):
        if self._input_target:
            self._cancel_input()
            return
        self.dismiss(None)

    def action_new_round(self):
        if self._discussing or self._input_target:
            return
        asyncio.create_task(self._run_discussion("open"))

    def action_guided(self):
        if self._discussing or self._input_target:
            return
        self._input_target = "topic"
        inp = self.query_one("#discussion-input", Input)
        inp.placeholder = "Enter a topic to discuss..."
        inp.value = ""
        inp.display = True
        inp.focus()
        self._update_mode("guided — type a topic")

    def action_file_focus(self):
        if self._discussing or self._input_target:
            return
        self._input_target = "file"
        inp = self.query_one("#discussion-input", Input)
        inp.placeholder = "Enter file path..."
        inp.value = ""
        inp.display = True
        inp.focus()
        self._update_mode("file focus — enter a path")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "discussion-input":
            return

        value = event.value.strip()
        if not value:
            self._cancel_input()
            return

        target = self._input_target
        self._cancel_input()

        if target == "topic":
            await self._run_discussion("topic", value)
        elif target == "file":
            await self._run_discussion("file", value)

    def _cancel_input(self):
        self._input_target = ""
        inp = self.query_one("#discussion-input", Input)
        inp.display = False
        inp.value = ""
        self._update_mode("open chat")

    def _update_mode(self, label: str):
        mode_widget = self.query_one("#discussion-mode", Static)
        mode_widget.update(f"[dim]{label}[/]")

    async def _run_discussion(
        self, mode: str, value: str = ""
    ):
        """Run a discussion round with staggered message display."""
        if self._discussing or not self.participants:
            return

        self._discussing = True
        log = self.query_one("#discussion-log", RichLog)

        # Separator between rounds
        log.write("")
        log.write("[dim]─── new round ───[/]")

        # Update mode display
        if mode == "open":
            self._update_mode("open chat")
            messages = self.engine.open_chat(self.participants)
        elif mode == "topic":
            self._update_mode(f"topic: {value[:40]}")
            log.write(f"[bold]Topic: {value}[/]")
            messages = self.engine.guided_topic(self.participants, value)
        elif mode == "file":
            self._update_mode(f"file: {value[:40]}")
            log.write(f"[bold]File: {value}[/]")
            if self.engine.ai_backend:
                log.write("[dim]Analyzing with AI...[/]")
            messages = await self.engine.file_focus(self.participants, value)
        else:
            self._discussing = False
            return

        log.write("")

        # Display messages with staggered timing
        for msg in messages:
            formatted = format_discussion_message(
                name=msg.buddy_name,
                message=msg.message,
                rarity=msg.rarity,
                register=msg.register,
                emoji=msg.species_emoji,
            )
            log.write(formatted)
            log.write("")  # spacing between messages
            await asyncio.sleep(1.2)

        self._discussing = False
