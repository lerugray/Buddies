"""WikiScreen — Obsidian vault status and generation controls."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Footer
from textual.screen import Screen

from buddies.core.obsidian_vault import ObsidianVault, VaultStats


class WikiScreen(Screen):
    """Dashboard for the Obsidian wiki vault."""

    CSS = """
    WikiScreen {
        background: $background;
    }

    #wiki-scroll {
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #wiki-container {
        width: 1fr;
        height: auto;
    }

    #wiki-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #wiki-status {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #wiki-sections {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #wiki-sessions {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #wiki-action-log {
        text-align: center;
        margin: 1 0;
    }

    #wiki-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("g", "generate", "Generate All", show=True),
        Binding("s", "gen_species", "Species", show=True),
        Binding("a", "gen_arch", "Architecture", show=True),
        Binding("d", "gen_decisions", "Decisions", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, project_path: Path | None = None):
        super().__init__()
        self.project_path = project_path
        self._vault: ObsidianVault | None = None
        self._stats: VaultStats | None = None

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="wiki-scroll"):
            with Vertical(id="wiki-container"):
                yield Static("📖 OBSIDIAN WIKI 📖", id="wiki-title")
                yield Static("", id="wiki-status")
                yield Static("", id="wiki-sections")
                yield Static("", id="wiki-sessions")
                yield Static("", id="wiki-action-log")
                yield Static(
                    "[dim]g=generate all  s=species  a=arch  d=decisions  r=refresh  esc=close[/]",
                    id="wiki-help",
                )
        yield Footer()

    async def on_mount(self):
        await self._scan()

    async def _scan(self):
        """Scan existing vault and update display."""
        self._vault = ObsidianVault(self.project_path)
        self._stats = self._vault.get_stats()
        self._render_stats()

    def _render_stats(self):
        """Update all Static widgets from self._stats."""
        if not self._stats:
            return

        s = self._stats

        # Vault status
        if s.exists:
            updated = datetime.fromtimestamp(s.last_updated).strftime("%Y-%m-%d %H:%M") if s.last_updated else "never"
            status_text = (
                f"[bold green]Vault exists[/] at `{VAULT_DIR_NAME}/`\n"
                f"Last updated: {updated}\n"
                f"Path: [dim]{s.vault_path}[/]"
            )
        else:
            status_text = (
                f"[bold yellow]No vault found[/]\n"
                f"Press [bold]g[/] to generate the wiki at `{VAULT_DIR_NAME}/`\n"
                f"[dim]The vault is auto-gitignored and won't clutter your repo.[/]"
            )
        self.query_one("#wiki-status", Static).update(status_text)

        # Section counts
        if s.exists:
            sections_text = (
                f"[bold]📚 Vault Contents[/]\n"
                f"  [green]●[/] Species pages: {s.species_count}\n"
                f"  [green]●[/] Module pages: {s.module_count}\n"
                f"  [green]●[/] Decision pages: {s.decision_count}"
            )
        else:
            sections_text = "[dim]Generate the vault to see contents.[/]"
        self.query_one("#wiki-sections", Static).update(sections_text)

        # Session journals
        if s.exists:
            if s.session_count > 0:
                sessions_text = (
                    f"[bold]📓 Session Journals[/]\n"
                    f"  {s.session_count} journal{'s' if s.session_count != 1 else ''} recorded\n"
                    f"  [dim]New journals are added automatically when you close Buddies.[/]"
                )
            else:
                sessions_text = (
                    f"[bold]📓 Session Journals[/]\n"
                    f"  No journals yet — they're created when Buddies exits.\n"
                    f"  [dim]Each session saves stats, tools used, and conversation highlights.[/]"
                )
        else:
            sessions_text = ""
        self.query_one("#wiki-sessions", Static).update(sessions_text)

    def action_close(self):
        self.dismiss(None)

    def action_generate(self):
        asyncio.create_task(self._do_generate_full())

    async def _do_generate_full(self):
        """Generate the complete vault."""
        if not self._vault:
            return

        action_log = self.query_one("#wiki-action-log", Static)
        action_log.update("[bold cyan]Generating vault...[/]")

        self._stats = self._vault.generate_full()

        action_log.update(
            f"[bold green]Wiki generated![/] "
            f"{self._stats.species_count} species, "
            f"{self._stats.module_count} modules, "
            f"{self._stats.decision_count} decisions"
        )
        self._render_stats()

    def action_gen_species(self):
        asyncio.create_task(self._do_gen_species())

    async def _do_gen_species(self):
        if not self._vault:
            return
        action_log = self.query_one("#wiki-action-log", Static)
        action_log.update("[bold cyan]Generating species pages...[/]")
        count = self._vault.generate_species_pages()
        self._vault.generate_home()
        self._stats = self._vault.get_stats()
        action_log.update(f"[bold green]Generated {count} species pages![/]")
        self._render_stats()

    def action_gen_arch(self):
        asyncio.create_task(self._do_gen_arch())

    async def _do_gen_arch(self):
        if not self._vault:
            return
        action_log = self.query_one("#wiki-action-log", Static)
        action_log.update("[bold cyan]Scanning project structure...[/]")
        count = self._vault.generate_architecture_pages()
        self._vault.generate_home()
        self._stats = self._vault.get_stats()
        action_log.update(f"[bold green]Generated {count} module pages![/]")
        self._render_stats()

    def action_gen_decisions(self):
        asyncio.create_task(self._do_gen_decisions())

    async def _do_gen_decisions(self):
        if not self._vault:
            return
        action_log = self.query_one("#wiki-action-log", Static)
        action_log.update("[bold cyan]Parsing decisions...[/]")
        count = self._vault.generate_decisions_pages()
        self._vault.generate_home()
        self._stats = self._vault.get_stats()
        action_log.update(f"[bold green]Generated {count} decision pages![/]")
        self._render_stats()

    def action_refresh(self):
        asyncio.create_task(self._scan())


# Used in status display
from buddies.core.obsidian_vault import VAULT_DIR_NAME
