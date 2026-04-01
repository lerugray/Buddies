"""Multi-machine awareness — detects when a project is used across computers.

On startup, saves the current machine's hostname to a local marker file.
Checks git history and project state for signs of multi-machine usage.
When detected, explains that CLAUDE.md is local/gitignored and offers
to set up the HANDOFF.md sharing pattern.

Aimed at non-programmers who don't realize CLAUDE.md doesn't travel
with the repo when they push/pull between machines.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

from buddies.config import get_data_dir


@dataclass
class MachineInfo:
    """Information about the current machine."""
    hostname: str
    is_new_machine: bool = False  # First time this hostname seen for this project
    other_machines: list[str] = None  # Other hostnames seen for this project
    has_claude_md: bool = False
    claude_md_gitignored: bool = False
    has_handoff_md: bool = False

    def __post_init__(self):
        if self.other_machines is None:
            self.other_machines = []

    @property
    def is_multi_machine(self) -> bool:
        return len(self.other_machines) > 0

    @property
    def needs_setup(self) -> bool:
        """True if multi-machine detected but CLAUDE.md sharing isn't set up properly."""
        if not self.is_multi_machine:
            return False
        # Needs setup if CLAUDE.md exists but isn't gitignored,
        # or if there's no HANDOFF.md for shared state
        if self.has_claude_md and not self.claude_md_gitignored:
            return True
        if not self.has_handoff_md and not self.has_claude_md:
            return True
        return False


def _get_hostname() -> str:
    """Get a human-readable machine identifier."""
    return platform.node() or os.environ.get("COMPUTERNAME", "unknown")


def _get_project_id(project_path: Path) -> str:
    """Get a unique-ish ID for this project directory."""
    # Use the resolved path as a stable identifier
    return str(project_path.resolve()).replace("\\", "/").replace("/", "_").replace(":", "")


def _get_machines_file(project_path: Path) -> Path:
    """Get the path to the machine tracking file for this project."""
    data_dir = get_data_dir()
    machines_dir = data_dir / "machines"
    machines_dir.mkdir(parents=True, exist_ok=True)
    project_id = _get_project_id(project_path)
    # Truncate long paths
    if len(project_id) > 80:
        project_id = project_id[-80:]
    return machines_dir / f"{project_id}.txt"


def _check_gitignore(project_path: Path, filename: str) -> bool:
    """Check if a file is listed in .gitignore."""
    gitignore = project_path / ".gitignore"
    if not gitignore.exists():
        return False
    try:
        content = gitignore.read_text(encoding="utf-8", errors="replace")
        return filename in content.split("\n")
    except OSError:
        return False


def _check_git_authors(project_path: Path) -> list[str]:
    """Check git log for different machine hints in commit messages/authors."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H %ae", "-50"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_path),
        )
        if result.returncode != 0:
            return []

        # Look for different author emails or machine-specific patterns
        emails = set()
        for line in result.stdout.strip().split("\n"):
            if " " in line:
                _, email = line.split(" ", 1)
                emails.add(email.strip())

        return list(emails)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def detect_machine(project_path: Path | None = None) -> MachineInfo:
    """Detect current machine and check for multi-machine usage.

    Returns MachineInfo with details about the current setup.
    """
    if project_path is None:
        project_path = Path.cwd()

    hostname = _get_hostname()
    machines_file = _get_machines_file(project_path)

    # Load known machines for this project
    known_machines: list[str] = []
    if machines_file.exists():
        try:
            content = machines_file.read_text(encoding="utf-8").strip()
            known_machines = [m for m in content.split("\n") if m.strip()]
        except OSError:
            pass

    # Is this a new machine for this project?
    is_new = hostname not in known_machines

    # Save current hostname if new
    if is_new:
        known_machines.append(hostname)
        try:
            machines_file.write_text(
                "\n".join(known_machines), encoding="utf-8"
            )
        except OSError:
            pass

    # Other machines (excluding current)
    other_machines = [m for m in known_machines if m != hostname]

    # Check project state
    has_claude_md = (project_path / "CLAUDE.md").exists()
    claude_md_gitignored = _check_gitignore(project_path, "CLAUDE.md")
    has_handoff_md = (project_path / "HANDOFF.md").exists()

    return MachineInfo(
        hostname=hostname,
        is_new_machine=is_new,
        other_machines=other_machines,
        has_claude_md=has_claude_md,
        claude_md_gitignored=claude_md_gitignored,
        has_handoff_md=has_handoff_md,
    )


def get_multi_machine_advice(info: MachineInfo) -> str | None:
    """Generate advice message for multi-machine setups. Returns None if no advice needed."""
    if not info.is_multi_machine:
        return None

    if not info.is_new_machine:
        # Not new — only warn if setup is wrong
        if info.has_claude_md and not info.claude_md_gitignored:
            return (
                f"Heads up — you're working across machines "
                f"({', '.join(info.other_machines)} + this one) "
                f"but CLAUDE.md isn't in .gitignore. "
                f"CLAUDE.md should be local to each machine (it has machine-specific notes). "
                f"Add 'CLAUDE.md' to .gitignore and use HANDOFF.md for shared context."
            )
        return None

    # New machine detected!
    machines_str = ", ".join(info.other_machines)
    lines = [
        f"I notice you've also worked on this project from: {machines_str}. "
        f"Welcome to this machine ({info.hostname})!"
    ]

    if not info.has_claude_md:
        lines.append(
            "This project doesn't have a CLAUDE.md yet. "
            "CLAUDE.md is local to each machine (gitignored) — it's where you put "
            "machine-specific notes like GPU info, local model settings, and routing to shared docs. "
            "Press [bold][g][/] to scaffold one."
        )
    elif not info.claude_md_gitignored:
        lines.append(
            "Your CLAUDE.md isn't gitignored — that means it's shared between machines. "
            "This can cause issues if your machines have different hardware or AI setups. "
            "Consider adding 'CLAUDE.md' to .gitignore and using HANDOFF.md for shared context."
        )
    else:
        # Good setup — just remind them to create a local CLAUDE.md
        lines.append(
            "CLAUDE.md is gitignored (good!), so you'll need a local copy on this machine. "
            "Press [bold][g][/] to check your config and scaffold one if needed."
        )

    if not info.has_handoff_md:
        lines.append(
            "Consider creating a HANDOFF.md for context that should travel between machines "
            "(project status, decisions, session notes). This file gets committed to git."
        )

    return " ".join(lines)
