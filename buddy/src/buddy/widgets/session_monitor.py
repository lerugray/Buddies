"""Session monitor widget — shows Claude Code activity feed."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, RichLog


class SessionMonitor(Vertical):
    """Displays Claude Code session activity in real-time."""

    DEFAULT_CSS = """
    SessionMonitor {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }

    SessionMonitor #session-header {
        height: 1;
        background: $accent;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 0 1;
    }

    SessionMonitor #session-stats {
        height: 3;
        padding: 0 1;
    }

    SessionMonitor #session-log {
        height: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_tokens = 0
        self.session_events = 0

    def compose(self) -> ComposeResult:
        yield Static("📡 Session Monitor", id="session-header")
        yield Static(self._stats_text(), id="session-stats")
        yield RichLog(id="session-log", wrap=True, highlight=True, markup=True)

    def _stats_text(self) -> str:
        return (
            f"Events: [bold]{self.session_events}[/]  "
            f"Tokens: [bold]~{self.total_tokens:,}[/]"
        )

    def log_event(self, event_type: str, summary: str, tokens: int = 0):
        self.session_events += 1
        self.total_tokens += tokens

        type_colors = {
            "tool_use": "cyan",
            "edit": "yellow",
            "read": "green",
            "bash": "red",
            "search": "magenta",
            "session": "blue",
            "info": "dim",
        }
        color = type_colors.get(event_type, "white")

        log = self.query_one("#session-log", RichLog)
        log.write(f"[{color}][{event_type.upper()}][/] {summary}")

        stats = self.query_one("#session-stats", Static)
        stats.update(self._stats_text())

    def clear_session(self):
        self.total_tokens = 0
        self.session_events = 0
        log = self.query_one("#session-log", RichLog)
        log.clear()
        stats = self.query_one("#session-stats", Static)
        stats.update(self._stats_text())
