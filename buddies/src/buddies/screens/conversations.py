"""ConversationsScreen — browse, load, rename, and delete saved conversations."""

from __future__ import annotations

import asyncio
from datetime import datetime
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Input, Footer
from textual.screen import Screen

from buddies.core.conversation import (
    list_conversations,
    delete_conversation,
    rename_conversation,
    ConversationMeta,
)


class ConversationsScreen(Screen):
    """Browse and manage saved conversations."""

    CSS = """
    ConversationsScreen {
        background: $background;
    }

    #convos-scroll {
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #convos-container {
        width: 1fr;
        height: auto;
    }

    #convos-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #convos-list {
        height: auto;
        border: solid $primary;
        padding: 1;
        width: 1fr;
        overflow: auto;
    }

    .convo-row {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    #rename-input {
        margin: 1 0;
    }

    #convos-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }

    #convos-count {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("enter", "load_convo", "Load", show=True),
        Binding("n", "rename_convo", "Rename", show=True),
        Binding("delete", "delete_convo", "Delete", show=True),
        Binding("up", "navigate_up", "Up", show=False),
        Binding("down", "navigate_down", "Down", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.conversations: list[ConversationMeta] = []
        self.selected_idx = 0
        self._renaming = False

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="convos-scroll"):
            with Vertical(id="convos-container"):
                    yield Static("💾 CONVERSATIONS 💾", id="convos-title")
                    yield Static("", id="convos-count")
                    yield Vertical(id="convos-list")
                    yield Static(
                        "[dim]↑↓ navigate  enter=load  n=rename  del=delete  esc=close[/]",
                        id="convos-help",
                    )
        yield Footer()

    async def on_mount(self):
        self.conversations = list_conversations()
        await self._render_list()

    async def _render_list(self):
        convos_list = self.query_one("#convos-list", Vertical)
        await convos_list.query("Static").remove()
        await convos_list.query("Input").remove()

        count = self.query_one("#convos-count", Static)
        count.update(f"[dim]{len(self.conversations)} saved conversations[/]")

        if not self.conversations:
            await convos_list.mount(
                Static("[dim]No saved conversations yet.[/]")
            )
            return

        rows = []
        for idx, convo in enumerate(self.conversations):
            is_selected = "[reverse]" if idx == self.selected_idx else ""
            end_tag = "[/]" if idx == self.selected_idx else ""

            # Format timestamp
            try:
                dt = datetime.fromtimestamp(convo.created)
                date_str = dt.strftime("%m/%d %H:%M")
            except (ValueError, OSError):
                date_str = "??/??"

            # Truncate name and preview
            name = convo.name[:35]
            preview = convo.preview[:50] if convo.preview else ""
            buddy = convo.buddy_name[:15] if convo.buddy_name else ""

            text = (
                f"{is_selected}"
                f"[bold]{name:<35}[/] "
                f"[dim]{date_str}[/] "
                f"[cyan]{buddy:<15}[/] "
                f"[dim]{convo.message_count:>3} msgs[/] "
                f"[dim italic]{preview}[/]"
                f"{end_tag}"
            )
            rows.append(Static(text, classes="convo-row"))

        await convos_list.mount(*rows)

    def action_close(self):
        if self._renaming:
            self._cancel_rename()
            return
        self.dismiss(None)

    def action_load_convo(self):
        """Load the selected conversation."""
        if self._renaming:
            return
        if 0 <= self.selected_idx < len(self.conversations):
            convo = self.conversations[self.selected_idx]
            self.dismiss(("load", convo.filename))

    def action_delete_convo(self):
        """Delete the selected conversation."""
        if self._renaming:
            return
        asyncio.create_task(self._do_delete())

    async def _do_delete(self):
        if not (0 <= self.selected_idx < len(self.conversations)):
            return
        convo = self.conversations[self.selected_idx]
        delete_conversation(convo.filename)
        self.conversations = list_conversations()
        if self.selected_idx >= len(self.conversations):
            self.selected_idx = max(0, len(self.conversations) - 1)
        await self._render_list()

    def action_rename_convo(self):
        """Rename the selected conversation."""
        if self._renaming:
            return
        if not (0 <= self.selected_idx < len(self.conversations)):
            return
        self._renaming = True
        convo = self.conversations[self.selected_idx]
        convos_list = self.query_one("#convos-list", Vertical)
        rename_input = Input(
            placeholder="New name...",
            id="rename-input",
            value=convo.name,
        )
        asyncio.create_task(self._mount_rename(convos_list, rename_input))

    async def _mount_rename(self, container: Vertical, rename_input: Input):
        await container.mount(rename_input)
        rename_input.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "rename-input":
            return

        new_name = event.value.strip()
        if new_name and 0 <= self.selected_idx < len(self.conversations):
            convo = self.conversations[self.selected_idx]
            rename_conversation(convo.filename, new_name)
            self.conversations = list_conversations()

        self._renaming = False
        await event.input.remove()
        await self._render_list()

    def _cancel_rename(self):
        self._renaming = False
        try:
            rename_input = self.query_one("#rename-input", Input)
            asyncio.create_task(rename_input.remove())
        except Exception:
            pass

    def action_navigate_up(self):
        if self._renaming:
            return
        asyncio.create_task(self._do_navigate(-1))

    def action_navigate_down(self):
        if self._renaming:
            return
        asyncio.create_task(self._do_navigate(1))

    async def _do_navigate(self, delta: int):
        if self.conversations:
            self.selected_idx = (self.selected_idx + delta) % len(self.conversations)
            await self._render_list()
