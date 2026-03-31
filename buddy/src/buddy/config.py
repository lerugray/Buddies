"""Configuration and settings for Buddy."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def get_data_dir() -> Path:
    """Get the Buddy data directory, creating it if needed."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = base / "buddy"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@dataclass
class AIBackendConfig:
    """Configuration for the AI backend."""

    provider: str = "none"  # "ollama", "litellm", "openai-compatible", "none"
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:27b"
    api_key: str = ""
    max_tokens: int = 1024
    temperature: float = 0.7


@dataclass
class BuddyConfig:
    """Main configuration."""

    user_seed: str = ""  # Used for deterministic species selection
    ai_backend: AIBackendConfig = field(default_factory=AIBackendConfig)
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
        """Load config from file, or create default."""
        config_path = get_data_dir() / "config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            ai_data = data.pop("ai_backend", {})
            ai_config = AIBackendConfig(**ai_data)
            return cls(ai_backend=ai_config, **data)
        config = cls()
        config.save()
        return config

    def save(self):
        """Save config to file."""
        config_path = get_data_dir() / "config.json"
        data = {
            "user_seed": self.user_seed,
            "ai_backend": {
                "provider": self.ai_backend.provider,
                "base_url": self.ai_backend.base_url,
                "model": self.ai_backend.model,
                "api_key": self.ai_backend.api_key,
                "max_tokens": self.ai_backend.max_tokens,
                "temperature": self.ai_backend.temperature,
            },
            "theme": self.theme,
            "animation_fps": self.animation_fps,
            "db_path": self.db_path,
        }
        config_path.write_text(json.dumps(data, indent=2))
