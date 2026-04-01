"""Configuration and settings for Buddy."""

from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Get the Buddy data directory, creating it if needed."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = base / "buddy"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _restrict_permissions(path: Path) -> None:
    """Set file to owner-only read/write (Unix). No-op on Windows."""
    if os.name != "nt" and path.exists():
        try:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass


@dataclass
class AIBackendConfig:
    """Configuration for the AI backend."""

    provider: str = "none"  # "ollama", "litellm", "openai-compatible", "none"
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:27b"
    api_key: str = ""
    max_tokens: int = 1024
    temperature: float = 0.7
    cost_tier: str = "free"  # "free" (local), "cheap" (haiku), "expensive" (opus/sonnet)


@dataclass
class BBSConfig:
    """Configuration for the BBS social network."""

    enabled: bool = True
    default_repo: str = "lerugray/buddies-bbs"
    github_token: str = ""  # PAT for write access (read-only without)
    privacy_level: str = "public"  # "public", "friends_only", "private"
    show_github_username: bool = False
    min_post_level: int = 3  # Buddy must be level 3+ to post
    max_posts_per_day: int = 3
    max_replies_per_day: int = 10
    auto_browse: bool = True
    auto_post: bool = True


@dataclass
class BuddyConfig:
    """Main configuration."""

    user_seed: str = ""  # Used for deterministic species selection
    ai_backend: AIBackendConfig = field(default_factory=AIBackendConfig)
    bbs: BBSConfig = field(default_factory=BBSConfig)
    theme: str = "default"
    animation_fps: int = 4
    db_path: str = ""

    def __post_init__(self):
        if not self.db_path:
            self.db_path = str(get_data_dir() / "buddy.db")
        if not self.user_seed:
            self.user_seed = os.environ.get("USER", os.environ.get("USERNAME", "buddy"))

    @classmethod
    def load(cls) -> BuddyConfig:
        """Load config from file, or create default.

        Secrets (API keys, tokens) are loaded with this priority:
          1. Environment variables (BUDDY_AI_API_KEY, BUDDY_GITHUB_TOKEN)
          2. config.json fallback (plaintext — not recommended)
        """
        config_path = get_data_dir() / "config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            ai_data = data.pop("ai_backend", {})
            ai_config = AIBackendConfig(**ai_data)
            bbs_data = data.pop("bbs", {})
            bbs_config = BBSConfig(**bbs_data) if bbs_data else BBSConfig()
            config = cls(ai_backend=ai_config, bbs=bbs_config, **data)
        else:
            config = cls()
            config.save()

        # Environment variables override config file for secrets
        env_api_key = os.environ.get("BUDDY_AI_API_KEY", "")
        env_gh_token = os.environ.get("BUDDY_GITHUB_TOKEN", "")
        if env_api_key:
            config.ai_backend.api_key = env_api_key
        if env_gh_token:
            config.bbs.github_token = env_gh_token

        # Warn if secrets are in the config file (prefer env vars)
        if config_path.exists():
            raw = json.loads(config_path.read_text())
            if raw.get("ai_backend", {}).get("api_key") or raw.get("bbs", {}).get("github_token"):
                log.warning(
                    "Secrets found in config.json — consider using environment "
                    "variables BUDDY_AI_API_KEY / BUDDY_GITHUB_TOKEN instead"
                )

        return config

    def save(self):
        """Save config to file. Secrets are omitted if set via env vars."""
        config_path = get_data_dir() / "config.json"

        # Don't write secrets to disk if they came from environment
        save_api_key = self.ai_backend.api_key if not os.environ.get("BUDDY_AI_API_KEY") else ""
        save_gh_token = self.bbs.github_token if not os.environ.get("BUDDY_GITHUB_TOKEN") else ""

        data = {
            "user_seed": self.user_seed,
            "ai_backend": {
                "provider": self.ai_backend.provider,
                "base_url": self.ai_backend.base_url,
                "model": self.ai_backend.model,
                "api_key": save_api_key,
                "max_tokens": self.ai_backend.max_tokens,
                "temperature": self.ai_backend.temperature,
                "cost_tier": self.ai_backend.cost_tier,
            },
            "bbs": {
                "enabled": self.bbs.enabled,
                "default_repo": self.bbs.default_repo,
                "github_token": save_gh_token,
                "privacy_level": self.bbs.privacy_level,
                "show_github_username": self.bbs.show_github_username,
                "min_post_level": self.bbs.min_post_level,
                "max_posts_per_day": self.bbs.max_posts_per_day,
                "max_replies_per_day": self.bbs.max_replies_per_day,
                "auto_browse": self.bbs.auto_browse,
                "auto_post": self.bbs.auto_post,
            },
            "theme": self.theme,
            "animation_fps": self.animation_fps,
            "db_path": self.db_path,
        }
        config_path.write_text(json.dumps(data, indent=2))
        _restrict_permissions(config_path)
