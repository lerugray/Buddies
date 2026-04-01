"""Chat widget — interact with buddy / local AI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, RichLog, Static

from buddies.widgets.styling import format_buddy_message, format_system_message


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

    # Set by app.py when buddy is loaded/switched
    buddy_name: str = "Buddy"
    buddy_emoji: str = ""
    buddy_rarity: str = "common"

    # Conversation log — set by app.py for auto-saving
    convo_log = None  # Optional[ConversationLog]

    def compose(self) -> ComposeResult:
        yield Static("💬 Chat", id="chat-header")
        yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Talk to your buddy...", id="chat-input")

    def set_buddy_info(self, name: str, emoji: str, rarity: str):
        """Update buddy info for styled messages."""
        self.buddy_name = name
        self.buddy_emoji = emoji
        self.buddy_rarity = rarity

    def add_message(self, sender: str, message: str):
        log = self.query_one("#chat-log", RichLog)
        if sender == "you":
            log.write(f"[bold cyan]You:[/] {message}")
        elif sender == "buddy":
            log.write(format_buddy_message(
                self.buddy_name, message,
                rarity=self.buddy_rarity,
                emoji=self.buddy_emoji,
            ))
        elif sender == "system":
            log.write(format_system_message(message))
        else:
            log.write(f"[bold yellow]{sender}:[/] {message}")

        # Auto-save to conversation log
        if self.convo_log is not None:
            self.convo_log.add_message(sender, message)

    def add_system(self, message: str):
        self.add_message("system", message)

    def clear_log(self):
        """Clear the chat log display (for loading a different conversation)."""
        log = self.query_one("#chat-log", RichLog)
        log.clear()

    def replay_messages(self, messages: list) -> None:
        """Replay a list of Message objects into the chat log without re-saving."""
        saved_log = self.convo_log
        self.convo_log = None  # Temporarily disable auto-save during replay
        for msg in messages:
            self.add_message(msg.sender, msg.text)
        self.convo_log = saved_log  # Re-enable
