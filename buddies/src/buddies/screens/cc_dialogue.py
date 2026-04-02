"""CCDialogueScreen — cross-system conversation with the CC companion.

Your Buddies party talks with the imported Claude Code /buddy companion.
CC buddy messages are styled distinctly (cyan border/color).
Three modes: open chat, guided topic, ask CC.
"""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static, Input, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.cc_dialogue import CCDialogueEngine, CCDialogueMessage
from buddies.db.store import BuddyStore
from buddies.widgets.styling import (
    RARITY_COLORS,
    REGISTER_COLORS,
    DISCUSSION_BORDER,
)


def format_cc_dialogue_message(msg: CCDialogueMessage) -> str:
    """Format a CC dialogue message with appropriate styling.

    CC buddy messages get cyan border and a (CC) tag.
    Party buddy messages get register-colored borders like normal discussions.
    """
    if msg.is_cc_buddy:
        border = f"[cyan]{DISCUSSION_BORDER}[/]"
        name_color = "cyan"
        tag = " [bold cyan](CC)[/bold cyan]"
        header = f"{border} [bold {name_color}]{msg.species_emoji} {msg.buddy_name}{tag}[/]"
    else:
        name_color = RARITY_COLORS.get(msg.rarity, "white")
        border_color = REGISTER_COLORS.get(msg.register, "white")
        border = f"[{border_color}]{DISCUSSION_BORDER}[/]"
        header = (
            f"{border} [bold {name_color}]{msg.species_emoji} {msg.buddy_name}[/] "
            f"[dim]({msg.register})[/]"
        )

    lines = msg.message.split("\n")
    body = "\n".join(f"{border} {line}" for line in lines)
    return f"{header}\n{body}"


class CCDialogueScreen(Screen):
    """Cross-system dialogue between party buddies and the CC companion."""

    CSS = """
    CCDialogueScreen {
        background: $background;
    }

    #cc-title {
        text-align: center;
        text-style: bold;
        color: cyan;
        height: 1;
        margin: 1 0 0 0;
    }

    #cc-mode {
        text-align: center;
        height: 1;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    #cc-log {
        height: 1fr;
        border: solid cyan;
        margin: 0 1;
        padding: 1;
    }

    #cc-input {
        dock: bottom;
        margin: 1 1;
    }

    #cc-help {
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
        Binding("a", "ask_cc", "Ask CC", show=True),
    ]

    def __init__(self, store: BuddyStore):
        super().__init__()
        self.store = store
        self.engine = CCDialogueEngine()
        self.cc_buddy: BuddyState | None = None
        self.party: list[BuddyState] = []
        self._input_target = ""  # "topic" or "ask"
        self._discussing = False
        self._rounds_completed = 0

    def compose(self) -> ComposeResult:
        yield Static("🔗 CC COMPANION DIALOGUE 🔗", id="cc-title")
        yield Static("[dim]loading...[/]", id="cc-mode")
        yield RichLog(id="cc-log", wrap=True, highlight=True, markup=True)
        yield Input(
            placeholder="Enter topic or question...",
            id="cc-input",
        )
        yield Static(
            "[dim]n=new round  g=topic  a=ask CC  esc=close[/]",
            id="cc-help",
        )
        yield Footer()

    async def on_mount(self):
        """Load CC buddy and party, then start first dialogue."""
        self.query_one("#cc-input", Input).display = False
        log = self.query_one("#cc-log", RichLog)

        # Load CC buddy
        cc_data = await self.store.get_cc_buddy()
        if not cc_data:
            log.write("[yellow]No CC companion imported yet![/yellow]")
            log.write("")
            log.write("[dim]To import your Claude Code /buddy companion:[/dim]")
            log.write("[dim]  1. Use the MCP tool: import_cc_buddy[/dim]")
            log.write("[dim]  2. Or set cc_buddy in your Buddies config.json[/dim]")
            log.write("[dim]  3. Or let Buddies auto-detect from CC config files[/dim]")
            log.write("")
            log.write("[dim]Press Esc to go back.[/dim]")
            self._update_mode("no CC buddy")
            return

        self.cc_buddy = BuddyState.from_db(cc_data)

        # Load party (excluding CC buddy)
        all_buddies = await self.store.get_all_buddies()
        for b in all_buddies:
            if b.get("source") != "cc_companion":
                try:
                    self.party.append(BuddyState.from_db(b))
                except Exception:
                    pass

        if not self.party:
            log.write("[dim]You have a CC buddy but no party buddies to talk to it![/dim]")
            log.write("[dim]Hatch some buddies first, then come back.[/dim]")
            self._update_mode("no party")
            return

        log.write(
            f"[bold cyan]Connected to {self.cc_buddy.species.emoji} "
            f"{self.cc_buddy.name} (CC)[/bold cyan]"
        )
        log.write(
            f"[dim]Party: {', '.join(f'{b.species.emoji} {b.name}' for b in self.party[:5])}"
            f"{'...' if len(self.party) > 5 else ''}[/dim]"
        )

        # Start first round
        await self._run_dialogue("open")

    def action_close(self):
        if self._input_target:
            self._cancel_input()
            return
        self.dismiss(self._rounds_completed)

    def action_new_round(self):
        if self._discussing or self._input_target or not self.cc_buddy:
            return
        asyncio.create_task(self._run_dialogue("open"))

    def action_guided(self):
        if self._discussing or self._input_target or not self.cc_buddy:
            return
        self._input_target = "topic"
        inp = self.query_one("#cc-input", Input)
        inp.placeholder = "Enter a topic for CC dialogue..."
        inp.value = ""
        inp.display = True
        inp.focus()
        self._update_mode("topic — type a topic")

    def action_ask_cc(self):
        if self._discussing or self._input_target or not self.cc_buddy:
            return
        self._input_target = "ask"
        inp = self.query_one("#cc-input", Input)
        inp.placeholder = "Ask the CC buddy something..."
        inp.value = ""
        inp.display = True
        inp.focus()
        self._update_mode("ask — type a question")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cc-input":
            return

        value = event.value.strip()
        if not value:
            self._cancel_input()
            return

        target = self._input_target
        self._cancel_input()

        if target == "topic":
            await self._run_dialogue("topic", value)
        elif target == "ask":
            await self._run_dialogue("ask", value)

    def _cancel_input(self):
        self._input_target = ""
        inp = self.query_one("#cc-input", Input)
        inp.display = False
        inp.value = ""
        self._update_mode("open dialogue")

    def _update_mode(self, label: str):
        mode_widget = self.query_one("#cc-mode", Static)
        mode_widget.update(f"[dim]{label}[/]")

    async def _run_dialogue(self, mode: str, value: str = ""):
        """Run a dialogue round with staggered messages."""
        if self._discussing or not self.cc_buddy or not self.party:
            return

        self._discussing = True
        log = self.query_one("#cc-log", RichLog)

        log.write("")
        log.write("[dim]─── new round ───[/]")

        if mode == "open":
            self._update_mode("open dialogue")
            messages = self.engine.open_chat(self.cc_buddy, self.party)
        elif mode == "topic":
            self._update_mode(f"topic: {value[:40]}")
            log.write(f"[bold]Topic: {value}[/]")
            messages = self.engine.guided_topic(self.cc_buddy, self.party, value)
        elif mode == "ask":
            self._update_mode(f"ask: {value[:40]}")
            log.write(f"[bold]Question: {value}[/]")
            messages = self.engine.ask_cc(self.cc_buddy, self.party, value)
        else:
            self._discussing = False
            return

        log.write("")

        for msg in messages:
            formatted = format_cc_dialogue_message(msg)
            log.write(formatted)
            log.write("")
            await asyncio.sleep(1.2)

        self._rounds_completed += 1
        self._discussing = False
