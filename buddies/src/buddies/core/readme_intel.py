"""README Intelligence — scan, grade, and suggest improvements for README.md.

Same pattern as config_intel.py but for project presentation.
Checks for missing elements, structural issues, and awesome-readme
best practices. Can scaffold a README from project metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReadmeSection:
    """A section found in the README."""
    title: str
    level: int
    line_start: int
    line_count: int


@dataclass
class ReadmeReport:
    """Results of scanning a README.md file."""
    exists: bool = False
    path: Path | None = None
    line_count: int = 0
    grade: str = "?"  # A/B/C/D/F

    # Content checks
    has_title: bool = False
    has_description: bool = False
    has_badges: bool = False
    has_install: bool = False
    has_usage: bool = False
    has_license: bool = False
    has_screenshot: bool = False
    has_gif: bool = False
    has_contributing: bool = False
    has_toc: bool = False
    has_collapsible: bool = False

    sections: list[ReadmeSection] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# Patterns to detect common README elements
BADGE_PATTERN = re.compile(r"\[!\[.*?\]\(.*?shields\.io.*?\)\]|\[!\[.*?\]\(.*?badge.*?\)\]|!\[.*?\]\(https://img\.shields\.io")
INSTALL_KEYWORDS = ["install", "setup", "getting started", "quick start", "pip install", "npm install", "cargo install"]
USAGE_KEYWORDS = ["usage", "how to use", "how to play", "examples", "quick start", "getting started"]
LICENSE_KEYWORDS = ["license", "licence", "mit", "apache", "gpl"]
SCREENSHOT_PATTERN = re.compile(r"!\[.*?\]\(.*?\.(png|jpg|jpeg|gif|webp|svg).*?\)", re.IGNORECASE)
GIF_PATTERN = re.compile(r"!\[.*?\]\(.*?\.gif.*?\)", re.IGNORECASE)
CONTRIBUTING_KEYWORDS = ["contributing", "contribute", "pr welcome", "pull request"]
TOC_PATTERN = re.compile(r"^\s*-\s*\[.*?\]\(#.*?\)", re.MULTILINE)
COLLAPSIBLE_PATTERN = re.compile(r"<details>", re.IGNORECASE)


def scan_readme(project_path: Path) -> ReadmeReport:
    """Scan a project's README.md and generate a health report."""
    report = ReadmeReport()

    # Find README (case-insensitive)
    readme_path = None
    for name in ["README.md", "readme.md", "Readme.md", "README.MD", "README"]:
        candidate = project_path / name
        if candidate.exists():
            readme_path = candidate
            break

    if not readme_path:
        report.suggestions.append("No README found — every project needs one!")
        report.grade = "F"
        return report

    report.exists = True
    report.path = readme_path

    try:
        content = readme_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        report.grade = "F"
        report.suggestions.append("Could not read README file")
        return report

    lines = content.split("\n")
    report.line_count = len(lines)
    content_lower = content.lower()

    # Check for title (first # heading)
    for line in lines[:10]:
        if line.startswith("# "):
            report.has_title = True
            break

    # Check for description (non-heading text in first 10 lines)
    for line in lines[:15]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("[!") and not stripped.startswith("<!--"):
            if len(stripped) > 20:
                report.has_description = True
                break

    # Badges
    report.has_badges = bool(BADGE_PATTERN.search(content))

    # Install instructions
    report.has_install = any(kw in content_lower for kw in INSTALL_KEYWORDS)

    # Usage
    report.has_usage = any(kw in content_lower for kw in USAGE_KEYWORDS)

    # License
    report.has_license = any(kw in content_lower for kw in LICENSE_KEYWORDS)

    # Screenshots / GIFs
    report.has_screenshot = bool(SCREENSHOT_PATTERN.search(content))
    report.has_gif = bool(GIF_PATTERN.search(content))

    # Contributing
    report.has_contributing = any(kw in content_lower for kw in CONTRIBUTING_KEYWORDS)

    # Table of contents
    toc_matches = TOC_PATTERN.findall(content)
    report.has_toc = len(toc_matches) >= 3  # At least 3 linked items

    # Collapsible sections
    report.has_collapsible = bool(COLLAPSIBLE_PATTERN.search(content))

    # Parse sections
    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # Count lines until next heading or end
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if re.match(r"^#{1,6}\s+", lines[j]):
                    end = j
                    break
            report.sections.append(ReadmeSection(
                title=title, level=level,
                line_start=i, line_count=end - i,
            ))

    # Generate suggestions
    if not report.has_title:
        report.suggestions.append("Add a title — start with '# Project Name'")
    if not report.has_description:
        report.suggestions.append("Add a one-line description right after the title")
    if not report.has_badges:
        report.suggestions.append("Add badges (language, license, version) — try shields.io")
    if not report.has_install:
        report.suggestions.append("Add install instructions — users need to know how to get started")
    if not report.has_usage:
        report.suggestions.append("Add usage examples — show how to actually use the project")
    if not report.has_license:
        report.suggestions.append("Mention the license — it tells people if they can use your code")
    if not report.has_screenshot and not report.has_gif:
        report.suggestions.append("Add a screenshot or GIF — visuals make a huge difference")
    elif not report.has_gif:
        report.suggestions.append("Consider a GIF demo — more engaging than static screenshots (try ScreenToGif or vhs)")
    if not report.has_contributing and report.line_count > 50:
        report.suggestions.append("Add a contributing section — invite others to help")
    if report.line_count > 200 and not report.has_collapsible:
        report.suggestions.append("Use collapsible <details> sections — keeps the README scannable")
    if report.line_count > 300 and not report.has_toc:
        report.suggestions.append("Add a table of contents — helps navigation in long READMEs")

    # Grade
    score = 0
    if report.has_title:
        score += 1
    if report.has_description:
        score += 1
    if report.has_badges:
        score += 1
    if report.has_install:
        score += 2  # Weighted — essential
    if report.has_usage:
        score += 2  # Weighted — essential
    if report.has_license:
        score += 1
    if report.has_screenshot or report.has_gif:
        score += 1
    if report.has_gif:
        score += 1  # Bonus for GIF
    if report.has_collapsible:
        score += 0.5
    if report.has_contributing:
        score += 0.5

    # Max score: 11
    if score >= 9:
        report.grade = "A"
    elif score >= 7:
        report.grade = "B"
    elif score >= 5:
        report.grade = "C"
    elif score >= 3:
        report.grade = "D"
    else:
        report.grade = "F"

    return report


def scaffold_readme(project_path: Path) -> str:
    """Generate a basic README scaffold from project metadata."""
    project_name = project_path.name

    # Try to detect language/framework
    has_python = (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists()
    has_node = (project_path / "package.json").exists()
    has_rust = (project_path / "Cargo.toml").exists()
    has_go = (project_path / "go.mod").exists()

    if has_python:
        install_cmd = "pip install -e ."
        lang_badge = "[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)"
    elif has_node:
        install_cmd = "npm install"
        lang_badge = "[![Node.js](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)"
    elif has_rust:
        install_cmd = "cargo build --release"
        lang_badge = "[![Rust](https://img.shields.io/badge/rust-stable-orange.svg)](https://www.rust-lang.org/)"
    elif has_go:
        install_cmd = "go build"
        lang_badge = "[![Go](https://img.shields.io/badge/go-1.21+-cyan.svg)](https://go.dev/)"
    else:
        install_cmd = "# Add install instructions here"
        lang_badge = ""

    badge_line = f"{lang_badge} " if lang_badge else ""
    badge_line += "[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)"

    return f"""# {project_name}

{badge_line}

<!-- One-line description of what this project does -->
A brief description of {project_name}.

<!-- TODO: Add a screenshot or GIF demo -->

## Quick Start

```bash
{install_cmd}
```

## Usage

<!-- Show how to use the project -->

## Features

<!-- Bullet list of key features -->

## License

MIT
"""
