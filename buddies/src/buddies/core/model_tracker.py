"""Model Tracker — detect current CC model and classify work phases.

Watches session events to determine which Claude model is active and
what phase of work the user is in, then suggests model switches when
there's a mismatch (e.g., using Opus for git commits).
"""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from buddies.config import get_data_dir


# ---------------------------------------------------------------------------
# Model tiers and display
# ---------------------------------------------------------------------------

MODEL_TIERS = {
    "opus": {"tier": "opus", "color": "magenta", "cost": "expensive"},
    "sonnet": {"tier": "sonnet", "color": "cyan", "cost": "moderate"},
    "haiku": {"tier": "haiku", "color": "green", "cost": "cheap"},
}


def classify_model(model_name: str) -> dict:
    """Classify a model string into a tier with display info."""
    lower = model_name.lower()
    for key, info in MODEL_TIERS.items():
        if key in lower:
            return {**info, "name": model_name}
    return {"tier": "unknown", "color": "dim", "cost": "unknown", "name": model_name}


# ---------------------------------------------------------------------------
# Work phases
# ---------------------------------------------------------------------------

PHASES = {
    "planning": {
        "description": "Planning & design — conversations, research, architecture",
        "recommended_model": "opus",
        "icon": "📐",
    },
    "implementing": {
        "description": "Implementing — writing code, editing files",
        "recommended_model": "sonnet",
        "icon": "🔨",
    },
    "exploring": {
        "description": "Exploring — reading files, searching codebase",
        "recommended_model": "sonnet",
        "icon": "🔍",
    },
    "maintenance": {
        "description": "Maintenance — commits, tests, small fixes",
        "recommended_model": "haiku",
        "icon": "🔧",
    },
}


# ---------------------------------------------------------------------------
# Model Tracker
# ---------------------------------------------------------------------------

@dataclass
class PhaseChange:
    """Emitted when the detected work phase changes."""
    old_phase: str
    new_phase: str
    recommended_model: str
    current_model_tier: str
    is_mismatch: bool
    suggestion: str  # Human-readable suggestion


class ModelTracker:
    """Tracks the current Claude model and detects work phase transitions."""

    def __init__(self):
        self._current_model: str = ""
        self._current_phase: str = ""
        self._phase_window: list[str] = []  # Recent tool names for phase detection
        self._window_size: int = 15
        self._last_phase_check: float = 0
        self._suggestions_made: set[str] = set()
        self._state_file = get_data_dir() / "current-model.txt"

        # Try to load persisted model
        self._load_persisted_model()

    @property
    def current_model(self) -> str:
        return self._current_model or "unknown"

    @property
    def current_model_info(self) -> dict:
        return classify_model(self._current_model)

    @property
    def current_phase(self) -> str:
        return self._current_phase or "unknown"

    @property
    def phase_info(self) -> dict:
        return PHASES.get(self._current_phase, {
            "description": "Unknown phase",
            "recommended_model": "sonnet",
            "icon": "❓",
        })

    def observe_event(self, event_type: str, tool_name: str,
                      summary: str, raw_data: dict) -> PhaseChange | None:
        """Process a session event. Returns PhaseChange if phase transition detected.

        Call this for every event from the session observer.
        """
        # Model detection from SessionStart
        if event_type == "SessionStart":
            model = raw_data.get("model", "")
            if model:
                self._set_model(model)

        # Model detection from /model commands in user prompts
        if event_type == "UserPromptSubmit":
            self._check_model_command(summary, raw_data)

        # Track tools for phase detection
        if tool_name:
            self._phase_window.append(tool_name)
            if len(self._phase_window) > self._window_size:
                self._phase_window = self._phase_window[-self._window_size:]

        # Check for phase change (throttled to every 10 events)
        if len(self._phase_window) >= 5 and len(self._phase_window) % 5 == 0:
            return self._detect_phase_change()

        return None

    def check_phase(self) -> PhaseChange | None:
        """Manually trigger a phase check. Called periodically by the app."""
        if len(self._phase_window) >= 5:
            return self._detect_phase_change()
        return None

    def _set_model(self, model: str):
        """Update the current model and persist it."""
        self._current_model = model
        self._suggestions_made.clear()  # Reset suggestions on model change
        try:
            self._state_file.write_text(model, encoding="utf-8")
        except OSError:
            pass

    def _load_persisted_model(self):
        """Load the last known model from disk."""
        try:
            if self._state_file.exists():
                self._current_model = self._state_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    def _check_model_command(self, summary: str, raw_data: dict):
        """Check if a user prompt contains a /model switch command."""
        # The user prompt text might be in the summary or raw data
        text = summary or ""
        prompt = raw_data.get("tool_input", {}).get("prompt", "")
        if prompt:
            text = prompt

        # Match /model <model-name> patterns
        match = re.search(r"/model\s+([\w.-]+)", text, re.IGNORECASE)
        if match:
            new_model = match.group(1)
            # Expand short names
            model_aliases = {
                "opus": "claude-opus-4-6",
                "sonnet": "claude-sonnet-4-6",
                "haiku": "claude-haiku-4-5",
            }
            resolved = model_aliases.get(new_model.lower(), new_model)
            self._set_model(resolved)

    def _detect_phase_change(self) -> PhaseChange | None:
        """Analyze recent tools to classify the current work phase."""
        if not self._phase_window:
            return None

        counts = Counter(self._phase_window)
        total = len(self._phase_window)

        # Calculate ratios
        edit_ratio = (counts.get("Edit", 0) + counts.get("Write", 0)) / total
        read_ratio = (counts.get("Read", 0) + counts.get("Grep", 0) + counts.get("Glob", 0)) / total
        bash_ratio = counts.get("Bash", 0) / total
        agent_ratio = counts.get("Agent", 0) / total

        # Phase classification
        new_phase = "exploring"  # default

        if edit_ratio >= 0.35:
            new_phase = "implementing"
        elif bash_ratio >= 0.30:
            new_phase = "maintenance"
        elif agent_ratio >= 0.20 or (read_ratio < 0.3 and edit_ratio < 0.1):
            new_phase = "planning"
        elif read_ratio >= 0.40:
            new_phase = "exploring"

        # Check if phase actually changed
        if new_phase == self._current_phase:
            return None

        old_phase = self._current_phase
        self._current_phase = new_phase

        # Check for model mismatch
        recommended = PHASES[new_phase]["recommended_model"]
        current_tier = classify_model(self._current_model)["tier"]
        is_mismatch = self._is_mismatch(current_tier, recommended, new_phase)

        suggestion = ""
        if is_mismatch:
            suggestion = self._build_suggestion(new_phase, current_tier, recommended)

        # Don't repeat the same suggestion
        suggestion_key = f"{new_phase}:{current_tier}"
        if suggestion_key in self._suggestions_made:
            suggestion = ""
            is_mismatch = False
        elif suggestion:
            self._suggestions_made.add(suggestion_key)

        return PhaseChange(
            old_phase=old_phase,
            new_phase=new_phase,
            recommended_model=recommended,
            current_model_tier=current_tier,
            is_mismatch=is_mismatch,
            suggestion=suggestion,
        )

    def _is_mismatch(self, current_tier: str, recommended: str, phase: str) -> bool:
        """Determine if there's a meaningful model-phase mismatch."""
        if current_tier == "unknown":
            return False
        if current_tier == recommended:
            return False

        tier_rank = {"haiku": 1, "sonnet": 2, "opus": 3}
        current_rank = tier_rank.get(current_tier, 0)
        recommended_rank = tier_rank.get(recommended, 0)

        # Only flag significant mismatches
        # Using expensive model for cheap work (overspending)
        if phase == "maintenance" and current_rank >= 3:
            return True
        # Using cheap model for important work (underperforming)
        if phase == "planning" and current_rank <= 1:
            return True
        # Two tiers away in either direction
        if abs(current_rank - recommended_rank) >= 2:
            return True

        return False

    def _build_suggestion(self, phase: str, current_tier: str, recommended: str) -> str:
        """Build a human-readable model switch suggestion."""
        phase_info = PHASES[phase]
        icon = phase_info["icon"]

        tier_rank = {"haiku": 1, "sonnet": 2, "opus": 3}
        overspending = tier_rank.get(current_tier, 0) > tier_rank.get(recommended, 0)

        if overspending:
            return (
                f"{icon} Phase shift: **{phase}** — "
                f"You're using {current_tier.title()} but {recommended.title()} "
                f"would handle this and save tokens. Try `/model {recommended}`"
            )
        else:
            return (
                f"{icon} Phase shift: **{phase}** — "
                f"You're using {current_tier.title()} but {recommended.title()} "
                f"would give better results here. Try `/model {recommended}`"
            )
