"""ToolBrowserScreen — browse installed MCP servers and skills.

Scans Claude Code configuration for MCP servers and skill definitions,
displays them in a searchable list. Zero AI cost — pure file reading.
"""

from __future__ import annotations

import asyncio
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, ScrollableContainer
from textual.widgets import Static, Input, Footer
from textual.screen import Screen

from buddies.core.tool_scanner import scan_all_tools, ToolInfo


class ToolBrowserScreen(Screen):
    """Browse installed MCP servers and Claude Code skills."""

    CSS = """
    ToolBrowserScreen {
        align: center middle;
        background: $background;
    }

    #tools-scroll {
        width: 90%;
        max-width: 90;
        height: 1fr;
        border: double $primary;
        padding: 1 2;
        margin: 1 2;
    }

    #tools-container {
        width: 1fr;
        height: auto;
    }

    #tools-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #tools-search {
        margin: 0 0 1 0;
    }

    #tools-list {
        height: auto;
        border: solid $primary;
        padding: 1;
        width: 1fr;
        overflow: auto;
    }

    .tool-row {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    #tools-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }

    #tools-count {
        text-align: center;
        color: $text-muted;
        margin: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("slash", "search", "Search", show=True),
        Binding("up", "navigate_up", "Up", show=False),
        Binding("down", "navigate_down", "Down", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.all_tools: list[ToolInfo] = []
        self.filtered_tools: list[ToolInfo] = []
        self.selected_idx = 0

    def compose(self) -> ComposeResult:
        with Center():
            with ScrollableContainer(id="tools-scroll"):
                with Vertical(id="tools-container"):
                    yield Static("🔍 TOOL BROWSER 🔍", id="tools-title")
                    yield Input(
                        placeholder="Type to filter...",
                        id="tools-search",
                    )
                    yield Static("", id="tools-count")
                    yield Vertical(id="tools-list")
                    yield Static(
                        "[dim]esc=close  /=search  ↑↓=navigate[/]",
                        id="tools-help",
                    )
        yield Footer()

    async def on_mount(self):
        """Scan for tools and display them."""
        self.all_tools = scan_all_tools()
        self.filtered_tools = list(self.all_tools)
        await self._render_tools()

    async def _render_tools(self):
        """Render the current filtered tool list."""
        tools_list = self.query_one("#tools-list", Vertical)
        await tools_list.query("Static").remove()

        count = self.query_one("#tools-count", Static)
        total_mcp = sum(1 for t in self.all_tools if t.tool_type == "mcp")
        total_skill = sum(1 for t in self.all_tools if t.tool_type == "skill")
        showing = len(self.filtered_tools)
        count.update(
            f"[dim]{showing} shown — {total_mcp} MCP servers, {total_skill} skills total[/]"
        )

        if not self.filtered_tools:
            await tools_list.mount(
                Static("[dim]No tools found. Install MCP servers or create skills.[/]")
            )
            return

        rows = []
        for idx, tool in enumerate(self.filtered_tools):
            is_selected = "[reverse]" if idx == self.selected_idx else ""
            end_tag = "[/]" if idx == self.selected_idx else ""

            source_color = "cyan" if tool.source == "project" else "dim"
            source_badge = f"[{source_color}]{tool.source}[/]"

            # Truncate description
            desc = tool.description[:55]

            text = (
                f"{is_selected}"
                f"{tool.icon} [bold]{tool.name:<20}[/] "
                f"{source_badge:<10} "
                f"[dim]{desc}[/]"
                f"{end_tag}"
            )
            rows.append(Static(text, classes="tool-row"))

        await tools_list.mount(*rows)

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter tools as user types."""
        if event.input.id != "tools-search":
            return

        query = event.value.strip().lower()
        if not query:
            self.filtered_tools = list(self.all_tools)
        else:
            self.filtered_tools = [
                t for t in self.all_tools
                if query in t.name.lower() or query in t.description.lower()
            ]

        self.selected_idx = 0
        await self._render_tools()

    def action_close(self):
        self.dismiss(None)

    def action_search(self):
        self.query_one("#tools-search", Input).focus()

    def action_navigate_up(self):
        asyncio.create_task(self._do_navigate(-1))

    def action_navigate_down(self):
        asyncio.create_task(self._do_navigate(1))

    async def _do_navigate(self, delta: int):
        if self.filtered_tools:
            self.selected_idx = (self.selected_idx + delta) % len(self.filtered_tools)
            await self._render_tools()
