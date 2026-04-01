"""ConfigHealthScreen — CLAUDE.md health dashboard and config scaffolding."""

from __future__ import annotations

import asyncio
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Footer
from textual.screen import Screen

from buddies.core.config_intel import ConfigIntelligence, ConfigReport
from buddies.core.readme_intel import scan_readme, ReadmeReport


# Grade display colors
GRADE_COLORS = {
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "#ff8800",
    "F": "red",
    "?": "dim",
}

GRADE_EMOJI = {
    "A": "🟢",
    "B": "🔵",
    "C": "🟡",
    "D": "🟠",
    "F": "🔴",
    "?": "⚪",
}


class ConfigHealthScreen(Screen):
    """Dashboard showing Claude Code config health and improvement suggestions."""

    CSS = """
    ConfigHealthScreen {
        background: $background;
    }

    #health-scroll {
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #health-container {
        width: 1fr;
        height: auto;
    }

    #health-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #health-grade {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #health-claude-md {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #health-rules-dir {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #health-readme {
        border: solid $primary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #health-suggestions {
        border: solid $accent;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #health-scaffold-status {
        text-align: center;
        margin: 1 0;
    }

    #health-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("s", "scaffold", "Scaffold", show=True),
        Binding("r", "rescan", "Rescan", show=True),
    ]

    def __init__(self, project_path: Path | None = None):
        super().__init__()
        self.project_path = project_path
        self.report: ConfigReport | None = None
        self._intel: ConfigIntelligence | None = None

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="health-scroll"):
            with Vertical(id="health-container"):
                    yield Static("🩺 CONFIG HEALTH 🩺", id="health-title")
                    yield Static("", id="health-grade")
                    yield Static("", id="health-claude-md")
                    yield Static("", id="health-rules-dir")
                    yield Static("", id="health-readme")
                    yield Static("", id="health-suggestions")
                    yield Static("", id="health-scaffold-status")
                    yield Static(
                        "[dim]s=scaffold config  r=rescan  esc=close[/]",
                        id="health-help",
                    )
        yield Footer()

    async def on_mount(self):
        await self._run_scan()

    async def _run_scan(self):
        self._intel = ConfigIntelligence(self.project_path)
        self.report = self._intel.scan()
        project_path = self._intel.project_path if self._intel else Path.cwd()
        self.readme_report = scan_readme(project_path)
        self._render_report()

    def _render_report(self):
        if not self.report:
            return

        r = self.report

        # Overall grade
        grade_color = GRADE_COLORS.get(r.overall_grade, "white")
        grade_emoji = GRADE_EMOJI.get(r.overall_grade, "")
        grade_widget = self.query_one("#health-grade", Static)
        grade_widget.update(
            f"{grade_emoji} [bold {grade_color}]Overall Grade: {r.overall_grade}[/] {grade_emoji}\n"
            f"[dim]{r.summary}[/]"
        )

        # CLAUDE.md section
        md = r.claude_md
        md_color = GRADE_COLORS.get(md.grade, "white")
        md_emoji = GRADE_EMOJI.get(md.grade, "")
        if md.exists:
            sections_text = ""
            if md.sections:
                section_list = ", ".join(s.title for s in md.sections[:8])
                if len(md.sections) > 8:
                    section_list += f" (+{len(md.sections) - 8} more)"
                sections_text = f"\n[dim]Sections:[/] {section_list}"

            bloated_text = ""
            if md.bloated_sections:
                bloated_names = ", ".join(
                    f"{s.title} ({s.line_count}L)" for s in md.bloated_sections[:3]
                )
                bloated_text = f"\n[bold red]Bloated:[/] {bloated_names}"

            routing_text = "[green]yes[/]" if md.has_routing else "[red]no[/]"

            md_text = (
                f"{md_emoji} [bold {md_color}]CLAUDE.md — Grade {md.grade}[/]\n"
                f"Lines: {md.line_count}"
                f"{'  [bold red](BLOATED)[/]' if md.is_bloated else '  [green](ok)[/]'}\n"
                f"Routing to rules files: {routing_text}"
                f"{sections_text}"
                f"{bloated_text}"
            )
        else:
            md_text = f"{md_emoji} [bold red]CLAUDE.md — Not Found[/]\nNo CLAUDE.md in project root."

        self.query_one("#health-claude-md", Static).update(md_text)

        # Rules dir section
        rd = r.rules_dir
        if rd.rules_dir_exists:
            if rd.rule_files:
                files_text = "\n".join(f"  [green]•[/] {f}" for f in rd.rule_files)
            else:
                files_text = "  [dim](empty)[/]"
            rd_text = (
                f"[bold]📁 .claude/rules/[/]\n"
                f"{files_text}\n"
                f"Settings.json: {'[green]yes[/]' if rd.settings_exists else '[dim]no[/]'}"
            )
        elif rd.claude_dir_exists:
            rd_text = (
                "[bold]📁 .claude/[/] exists\n"
                "[yellow]No rules/ subdirectory[/] — press [bold]s[/] to scaffold"
            )
        else:
            rd_text = (
                "[bold red]📁 .claude/ — Not Found[/]\n"
                "No Claude Code config directory. Press [bold]s[/] to scaffold."
            )

        self.query_one("#health-rules-dir", Static).update(rd_text)

        # README section
        if hasattr(self, "readme_report") and self.readme_report:
            rm = self.readme_report
            rm_color = GRADE_COLORS.get(rm.grade, "white")
            rm_emoji = GRADE_EMOJI.get(rm.grade, "")

            if rm.exists:
                checks = []
                for label, val in [
                    ("Title", rm.has_title),
                    ("Description", rm.has_description),
                    ("Badges", rm.has_badges),
                    ("Install", rm.has_install),
                    ("Usage", rm.has_usage),
                    ("License", rm.has_license),
                    ("Screenshot/GIF", rm.has_screenshot or rm.has_gif),
                    ("Collapsible", rm.has_collapsible),
                ]:
                    icon = "[green]✓[/]" if val else "[red]✗[/]"
                    checks.append(f"  {icon} {label}")

                checks_text = "\n".join(checks)
                rm_text = (
                    f"{rm_emoji} [bold {rm_color}]README.md — Grade {rm.grade}[/]\n"
                    f"Lines: {rm.line_count} | Sections: {len(rm.sections)}\n"
                    f"{checks_text}"
                )
            else:
                rm_text = f"{rm_emoji} [bold red]README.md — Not Found[/]\nNo README in project root."

            self.query_one("#health-readme", Static).update(rm_text)

        # Suggestions
        readme_suggestions = self.readme_report.suggestions if hasattr(self, "readme_report") and self.readme_report else []
        all_suggestions = md.suggestions + rd.suggestions + readme_suggestions
        if all_suggestions:
            suggestion_lines = "\n".join(
                f"  [yellow]→[/] {s}" for s in all_suggestions
            )
            suggestions_text = f"[bold]💡 Suggestions ({len(all_suggestions)})[/]\n{suggestion_lines}"
        else:
            suggestions_text = "[bold green]✅ No suggestions — config looks healthy![/]"

        self.query_one("#health-suggestions", Static).update(suggestions_text)

    def action_close(self):
        self.dismiss(None)

    def action_scaffold(self):
        asyncio.create_task(self._do_scaffold())

    async def _do_scaffold(self):
        if not self._intel:
            return

        scaffold = self._intel.generate_scaffold()
        status_widget = self.query_one("#health-scaffold-status", Static)

        if not scaffold:
            status_widget.update("[green]All recommended files already exist![/]")
            return

        # Create the files
        created = []
        for rel_path, content in scaffold.items():
            full_path = self._intel.project_path / rel_path.replace("/", os.sep)
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                created.append(rel_path)
            except OSError as e:
                status_widget.update(f"[red]Error creating {rel_path}: {e}[/]")
                return

        files_text = ", ".join(created)
        status_widget.update(
            f"[bold green]✅ Created {len(created)} files:[/] {files_text}"
        )

        # Rescan to update the display
        await self._run_scan()

    def action_rescan(self):
        asyncio.create_task(self._run_scan())


# Need os for path separator in scaffold
import os
