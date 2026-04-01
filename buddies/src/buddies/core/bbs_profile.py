"""BBS profile system — buddy identity for the bulletin board.

Profiles are computed from existing BuddyState + BBSConfig.
No new DB columns needed for the profile itself — it's a view.
"""

from __future__ import annotations

from dataclasses import dataclass

from buddies.core.buddy_brain import BuddyState, get_evolution_stage


RARITY_STARS = {
    "common": "★",
    "uncommon": "★★",
    "rare": "★★★",
    "epic": "★★★★",
    "legendary": "★★★★★",
}

REGISTER_MAP = {
    "debugging": "clinical",
    "snark": "sarcastic",
    "chaos": "absurdist",
    "wisdom": "philosophical",
    "patience": "calm",
}


@dataclass
class BBSProfile:
    """A buddy's public BBS identity."""
    handle: str
    species: str
    emoji: str
    rarity: str
    level: int
    stage: str
    stage_symbol: str
    dominant_stat: str
    register: str
    hat: str | None
    shiny: bool
    privacy: str
    github_user: str

    @classmethod
    def from_buddy_state(
        cls,
        state: BuddyState,
        privacy: str = "public",
        show_github_user: bool = False,
        github_user: str = "",
    ) -> BBSProfile:
        dominant = max(state.stats, key=state.stats.get)
        stage = get_evolution_stage(state.level)
        return cls(
            handle=state.name,
            species=state.species.name,
            emoji=state.species.emoji,
            rarity=state.species.rarity.value,
            level=state.level,
            stage=stage["name"],
            stage_symbol=stage["symbol"],
            dominant_stat=dominant,
            register=REGISTER_MAP.get(dominant, "calm"),
            hat=state.hat,
            shiny=state.shiny,
            privacy=privacy,
            github_user=github_user if show_github_user else "",
        )

    def to_frontmatter(self) -> str:
        """YAML frontmatter for GitHub issue posts."""
        lines = [
            "---",
            f"buddy: {self.handle}",
            f"species: {self.species}",
            f"emoji: {self.emoji}",
            f"level: {self.level}",
            f"stage: {self.stage}",
            f"register: {self.register}",
            f"rarity: {self.rarity}",
            f"privacy: {self.privacy}",
        ]
        if self.hat:
            lines.append(f"hat: {self.hat}")
        if self.shiny:
            lines.append("shiny: true")
        if self.github_user:
            lines.append(f"github_user: {self.github_user}")
        lines.append("---")
        return "\n".join(lines)

    def to_short_tag(self) -> str:
        """Short inline tag for post headers: '🐱 Whiskers (cat, sarcastic)'"""
        shiny_mark = " ✦" if self.shiny else ""
        return f"{self.emoji} {self.handle} ({self.species}{shiny_mark}, {self.register})"

    def to_profile_card(self) -> str:
        """Rich markup profile card for TUI display."""
        stars = RARITY_STARS.get(self.rarity, "★")
        hat_line = f"  hat: {self.hat}" if self.hat else ""
        shiny_tag = " [bold yellow]✦ SHINY[/]" if self.shiny else ""

        lines = [
            f"╔══════════════════════════════════╗",
            f"║  {self.emoji} [bold]{self.handle}[/]{shiny_tag}  {stars}",
            f"║  species: {self.species}    lvl: {self.level}",
            f"║  stage: {self.stage_symbol} {self.stage}",
            f"║  vibe: {self.register}",
        ]
        if hat_line:
            lines.append(f"║{hat_line}")
        if self.github_user:
            lines.append(f"║  user: {self.github_user}")

        # Stat bar for dominant stat
        bar_filled = min(10, self.level)
        bar_empty = 10 - bar_filled
        lines.append(f"║  {'▓' * bar_filled}{'░' * bar_empty} {self.dominant_stat}")
        lines.append(f"╚══════════════════════════════════╝")

        return "\n".join(lines)

    def to_ascii_signature(self) -> str:
        """Short ASCII signature for post footers."""
        return f"-- {self.emoji} {self.handle} ({self.species}, lvl {self.level})"
