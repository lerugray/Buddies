"""Chat widget — interact with buddy / local AI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, RichLog


class ChatWindow(Vertical):
    """Chat interface for talking to buddy."""

    DEFAULT_CSS = """
    ChatWindow {
        width: 1fr;
        height: 1fr;
        border: solid $secondary;
    }

    ChatWindow #chat-header {
        height: 1;
        background: $secondary;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 0 1;
    }

    ChatWindow #chat-log {
        height: 1fr;
        padding: 0 1;
    }

    ChatWindow #chat-input {
        dock: bottom;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("💬 Chat", id="chat-header")
        yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Talk to your buddy...", id="chat-input")

    def add_message(self, sender: str, message: str):
        log = self.query_one("#chat-log", RichLog)
        if sender == "you":
            log.write(f"[bold cyan]You:[/] {message}")
        elif sender == "buddy":
            log.write(f"[bold green]Buddy:[/] {message}")
        elif sender == "system":
            log.write(f"[dim italic]{message}[/]")
        else:
            log.write(f"[bold yellow]{sender}:[/] {message}")

    def add_system(self, message: str):
        self.add_message("system", message)
