"""Status bar widget — alerts, notifications, and quick info."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """Bottom status bar with alerts and buddy status."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buddy_name = "Buddy"
        self._mood = "neutral"
        self._level = 1
        self._alert = ""

    def set_buddy_info(self, name: str, mood: str, level: int):
        self._buddy_name = name
        self._mood = mood
        self._level = level
        self._refresh_display()

    def set_alert(self, message: str):
        self._alert = message
        self._refresh_display()

    def clear_alert(self):
        self._alert = ""
        self._refresh_display()

    def _refresh_display(self):
        parts = [
            f"[bold]{self._buddy_name}[/] Lv.{self._level}",
            f"Mood: {self._mood}",
        ]
        if self._alert:
            parts.append(f"[bold yellow]⚠ {self._alert}[/]")
        parts.append("[dim]Press [bold]q[/] to quit | [bold]?[/] for help[/]")
        self.update("  │  ".join(parts))
