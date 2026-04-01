"""Conversation persistence — auto-save, load, rename, delete chat history.

Conversations are stored as JSON files in the data directory under conversations/.
Each message is appended as it happens, so nothing is lost on crash.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from buddies.config import get_data_dir


def _conversations_dir() -> Path:
    """Get the conversations directory, creating if needed."""
    d = get_data_dir() / "conversations"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Message:
    """A single chat message."""

    sender: str  # "you", "buddy", "system", or buddy name
    text: str
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {"sender": self.sender, "text": self.text, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> Message:
        return cls(sender=d["sender"], text=d["text"], timestamp=d.get("timestamp", 0))


@dataclass
class ConversationMeta:
    """Metadata about a saved conversation (for listing)."""

    filename: str
    name: str
    created: float
    message_count: int
    buddy_name: str = ""
    preview: str = ""


class ConversationLog:
    """Manages the active conversation — auto-saves every message."""

    def __init__(self):
        self._messages: list[Message] = []
        self._filename: str = ""
        self._name: str = ""
        self._buddy_name: str = ""
        self._created: float = 0.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def start_new(self, buddy_name: str = "") -> None:
        """Start a new conversation with a timestamped name."""
        now = datetime.now()
        self._created = time.time()
        self._name = now.strftime("%Y-%m-%d %H:%M")
        self._filename = now.strftime("%Y%m%d_%H%M%S") + ".json"
        self._buddy_name = buddy_name
        self._messages = []
        self._save_meta()

    def add_message(self, sender: str, text: str) -> None:
        """Add a message and auto-save to disk."""
        msg = Message(sender=sender, text=text)
        self._messages.append(msg)
        self._append_to_disk(msg)

    def rename(self, new_name: str) -> None:
        """Rename the current conversation."""
        self._name = new_name.strip()
        self._save_full()

    def load(self, filename: str) -> list[Message]:
        """Load a conversation from disk. Returns the messages."""
        path = _conversations_dir() / filename
        if not path.exists():
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        self._filename = filename
        self._name = data.get("name", filename)
        self._created = data.get("created", 0)
        self._buddy_name = data.get("buddy_name", "")
        self._messages = [Message.from_dict(m) for m in data.get("messages", [])]
        return list(self._messages)

    def get_messages(self) -> list[Message]:
        """Get all messages in the current conversation."""
        return list(self._messages)

    def _save_meta(self) -> None:
        """Save conversation metadata (creates the file)."""
        self._save_full()

    def _save_full(self) -> None:
        """Write the full conversation to disk."""
        if not self._filename:
            return
        path = _conversations_dir() / self._filename
        data = {
            "name": self._name,
            "created": self._created,
            "buddy_name": self._buddy_name,
            "messages": [m.to_dict() for m in self._messages],
        }
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _append_to_disk(self, msg: Message) -> None:
        """Efficiently save by rewriting the full file (messages are small)."""
        self._save_full()


def list_conversations() -> list[ConversationMeta]:
    """List all saved conversations, newest first."""
    convos: list[ConversationMeta] = []
    conv_dir = _conversations_dir()

    for path in sorted(conv_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            messages = data.get("messages", [])

            # Find a preview (first non-system user message)
            preview = ""
            for m in messages:
                if m.get("sender") == "you":
                    preview = m.get("text", "")[:50]
                    break
            if not preview and messages:
                preview = messages[0].get("text", "")[:50]

            convos.append(ConversationMeta(
                filename=path.name,
                name=data.get("name", path.stem),
                created=data.get("created", 0),
                message_count=len(messages),
                buddy_name=data.get("buddy_name", ""),
                preview=preview,
            ))
        except (json.JSONDecodeError, OSError):
            continue

    return convos


def delete_conversation(filename: str) -> bool:
    """Delete a conversation file. Returns True if deleted."""
    path = _conversations_dir() / filename
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def rename_conversation(filename: str, new_name: str) -> bool:
    """Rename a conversation (updates the name field, not the filename)."""
    path = _conversations_dir() / filename
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = new_name.strip()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except (json.JSONDecodeError, OSError):
        return False
