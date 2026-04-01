"""MemoryScreen — browse the three-tier memory system."""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Footer
from textual.screen import Screen

from buddies.core.memory import MemoryManager


class MemoryScreen(Screen):
    """Dashboard for the buddy's three-tier memory."""

    CSS = """
    MemoryScreen {
        background: $background;
    }

    #mem-scroll {
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #mem-container {
        width: 1fr;
        height: auto;
    }

    #mem-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #mem-stats {
        text-align: center;
        margin-bottom: 1;
    }

    #mem-episodic {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #mem-semantic {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #mem-procedural {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #mem-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, memory: MemoryManager):
        super().__init__()
        self._memory = memory

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="mem-scroll"):
            with Vertical(id="mem-container"):
                yield Static("🧠 BUDDY MEMORY 🧠", id="mem-title")
                yield Static("", id="mem-stats")
                yield Static("", id="mem-episodic")
                yield Static("", id="mem-semantic")
                yield Static("", id="mem-procedural")
                yield Static(
                    "[dim]r=refresh  esc=close[/]",
                    id="mem-help",
                )
        yield Footer()

    async def on_mount(self):
        await self._render()

    async def _render(self):
        """Populate all sections from memory."""
        stats = await self._memory.get_stats()

        # Stats summary
        self.query_one("#mem-stats", Static).update(
            f"[bold]Episodic:[/] {stats['episodic']}  "
            f"[bold]Semantic:[/] {stats['semantic']}  "
            f"[bold]Procedural:[/] {stats['procedural']}"
            + (f"  [yellow]⚠ {stats['contradictions']} contradiction{'s' if stats['contradictions'] != 1 else ''}[/]"
               if stats["contradictions"] else "")
        )

        # Episodic memories (recent)
        episodes = await self._memory.query_episodic(limit=15)
        if episodes:
            lines = ["[bold]📅 Episodic — What Happened[/]", ""]
            for ep in episodes:
                imp = ep["importance"]
                star = "★" if imp >= 7 else "☆" if imp >= 5 else "·"
                time_str = ep["created_at"][:16] if ep["created_at"] else "?"
                summary = ep["summary"][:80]
                lines.append(f"  [{star}{imp}] [dim]{time_str}[/] {summary}")
        else:
            lines = [
                "[bold]📅 Episodic — What Happened[/]",
                "",
                "  [dim]No episodic memories yet. They're recorded from session events.[/]",
            ]
        self.query_one("#mem-episodic", Static).update("\n".join(lines))

        # Semantic memories (facts)
        facts = await self._memory.query_semantic(limit=15)
        contradictions = await self._memory.get_contradictions()
        sem_lines = ["[bold]📚 Semantic — What We Know[/]", ""]
        if facts:
            for fact in facts:
                conf = f"{fact['confidence']:.0%}"
                topic = fact["topic"]
                key = fact["key"]
                value = fact["value"][:60]
                sem_lines.append(f"  [{conf}] [cyan]{topic}[/]/{key} → {value}")
        else:
            sem_lines.append("  [dim]No semantic memories yet. Chat naturally — buddy picks up facts.[/]")

        if contradictions:
            sem_lines.extend(["", "  [bold yellow]Contradictions:[/]"])
            for c in contradictions[:5]:
                sem_lines.append(
                    f"  [yellow]⚠[/] {c['topic']}/{c['key']}: "
                    f"was [red]'{c['value']}'[/] → now [green]'{c['new_value']}'[/]"
                )

        self.query_one("#mem-semantic", Static).update("\n".join(sem_lines))

        # Procedural memories (patterns)
        procedures = await self._memory.query_procedural(limit=15)
        if procedures:
            proc_lines = ["[bold]⚙ Procedural — What Works[/]", ""]
            for proc in procedures:
                score = proc["success_count"] - proc["fail_count"]
                icon = "✓" if score > 0 else "~" if score == 0 else "✗"
                color = "green" if score > 0 else "yellow" if score == 0 else "red"
                trigger = proc["trigger_pattern"][:40]
                action = proc["action"][:40]
                proc_lines.append(
                    f"  [{color}]{icon}×{proc['success_count']}[/] "
                    f"When {trigger} → {action}"
                )
        else:
            proc_lines = [
                "[bold]⚙ Procedural — What Works[/]",
                "",
                "  [dim]No procedural memories yet. They're learned from successful patterns.[/]",
            ]
        self.query_one("#mem-procedural", Static).update("\n".join(proc_lines))

    def action_close(self):
        self.dismiss(None)

    def action_refresh(self):
        asyncio.create_task(self._render())
