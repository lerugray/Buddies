"""AchievementsScreen — view unlocked and locked achievements."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, ScrollableContainer
from textual.widgets import Static, Footer
from textual.screen import Screen

from buddies.core.achievements import ACHIEVEMENTS, Achievement


class AchievementsScreen(Screen):
    """Display all achievements grouped by category."""

    CSS = """
    AchievementsScreen {
        align: center middle;
        background: $background;
    }

    #achv-scroll {
        width: 96%;
        max-width: 120;
        height: 1fr;
        border: double $primary;
        padding: 1 1;
        margin: 0 1;
    }

    #achv-container {
        width: 1fr;
        height: auto;
    }

    #achv-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #achv-progress {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #achv-list {
        height: auto;
        width: 1fr;
    }

    .achv-category {
        margin: 1 0 0 0;
        text-style: bold;
        color: $accent;
    }

    .achv-row {
        padding: 0 1;
    }

    #achv-help {
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    def __init__(self, unlocked_ids: set[str]):
        super().__init__()
        self.unlocked_ids = unlocked_ids

    def compose(self) -> ComposeResult:
        with Center():
            with ScrollableContainer(id="achv-scroll"):
                with Vertical(id="achv-container"):
                    yield Static("🏆 ACHIEVEMENTS 🏆", id="achv-title")
                    yield Static("", id="achv-progress")
                    yield Vertical(id="achv-list")
                    yield Static("[dim]esc=close[/]", id="achv-help")
        yield Footer()

    async def on_mount(self):
        total = len(ACHIEVEMENTS)
        unlocked = len(self.unlocked_ids)
        # Don't count secret achievements in the denominator unless unlocked
        visible_total = sum(
            1 for a in ACHIEVEMENTS
            if a.category != "secret" or a.id in self.unlocked_ids
        )
        visible_unlocked = sum(
            1 for a in ACHIEVEMENTS
            if a.id in self.unlocked_ids and (a.category != "secret" or a.id in self.unlocked_ids)
        )

        progress = self.query_one("#achv-progress", Static)
        progress.update(
            f"[bold]{unlocked}[/]/{total} unlocked "
            f"[dim]({visible_unlocked}/{visible_total} visible)[/]"
        )

        achv_list = self.query_one("#achv-list", Vertical)

        # Group by category
        categories = {
            "collection": "📦 Collection",
            "mastery": "⚔️ Mastery",
            "social": "💬 Social",
            "exploration": "🔍 Exploration",
            "secret": "❓ Secret",
        }

        rows = []
        for cat_id, cat_name in categories.items():
            cat_achievements = [a for a in ACHIEVEMENTS if a.category == cat_id]
            if not cat_achievements:
                continue

            # For secret category, only show unlocked ones plus a "???" count
            if cat_id == "secret":
                unlocked_secrets = [a for a in cat_achievements if a.id in self.unlocked_ids]
                locked_count = len(cat_achievements) - len(unlocked_secrets)
                rows.append(Static(f"\n{cat_name}", classes="achv-category"))
                for a in unlocked_secrets:
                    rows.append(Static(
                        f"  {a.icon} [bold green]{a.name}[/] — {a.description}",
                        classes="achv-row",
                    ))
                if locked_count > 0:
                    rows.append(Static(
                        f"  [dim]❓ {locked_count} secret achievement{'s' if locked_count != 1 else ''} remaining...[/]",
                        classes="achv-row",
                    ))
            else:
                rows.append(Static(f"\n{cat_name}", classes="achv-category"))
                for a in cat_achievements:
                    if a.id in self.unlocked_ids:
                        rows.append(Static(
                            f"  {a.icon} [bold green]{a.name}[/] — {a.description}",
                            classes="achv-row",
                        ))
                    else:
                        rows.append(Static(
                            f"  [dim]🔒 {a.name} — {a.description}[/]",
                            classes="achv-row",
                        ))

        await achv_list.mount(*rows)

    def action_close(self):
        self.dismiss(None)
