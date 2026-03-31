"""Setup script to register Buddy's hooks with Claude Code.

Run this once to add Buddy's event hooks to your Claude Code settings.
It adds hook entries that forward events to Buddy's event log.

Usage:
    python -m buddies.setup_hooks
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get_claude_settings_path() -> Path:
    """Find the Claude Code settings.json."""
    home = Path.home()
    return home / ".claude" / "settings.json"


def get_hook_command() -> str:
    """Get the command to invoke the buddy hook receiver."""
    python = sys.executable.replace("\\", "/")
    return f"{python} -m buddies.core.hooks"


def setup_hooks():
    """Add buddy hooks to Claude Code settings."""
    settings_path = get_claude_settings_path()

    if not settings_path.exists():
        print(f"Claude Code settings not found at {settings_path}")
        print("Make sure Claude Code is installed and has been run at least once.")
        return False

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    hook_cmd = get_hook_command()

    # Events we want to observe
    events_to_hook = [
        "PreToolUse",
        "PostToolUse",
        "SessionStart",
        "SessionEnd",
        "UserPromptSubmit",
        "Notification",
    ]

    buddy_hook_marker = "buddies.core.hooks"
    changes_made = False

    for event_name in events_to_hook:
        event_hooks = hooks.get(event_name, [])

        # Check if buddy hook already exists
        already_exists = any(
            buddy_hook_marker in h.get("command", "")
            for h in event_hooks
            if isinstance(h, dict)
        )

        if not already_exists:
            new_hook = {
                "type": "command",
                "command": f"{hook_cmd} {event_name}",
                "timeout": 2000,
            }
            event_hooks.append(new_hook)
            hooks[event_name] = event_hooks
            changes_made = True
            print(f"  Added hook: {event_name}")

    if changes_made:
        settings["hooks"] = hooks
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print(f"\nHooks written to {settings_path}")
        print("Buddy will now receive Claude Code events!")
    else:
        print("Buddy hooks already configured — nothing to do.")

    return True


def remove_hooks():
    """Remove buddy hooks from Claude Code settings."""
    settings_path = get_claude_settings_path()
    if not settings_path.exists():
        return

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    buddy_hook_marker = "buddies.core.hooks"

    for event_name in list(hooks.keys()):
        hooks[event_name] = [
            h for h in hooks[event_name]
            if not (isinstance(h, dict) and buddy_hook_marker in h.get("command", ""))
        ]
        if not hooks[event_name]:
            del hooks[event_name]

    settings["hooks"] = hooks
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("Buddy hooks removed from Claude Code settings.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_hooks()
    else:
        setup_hooks()
