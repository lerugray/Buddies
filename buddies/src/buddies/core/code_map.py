"""Code Structure Map — generates a concise project-map.md for AI consumption.

Scans the project directory and produces a compact map of:
- File tree with one-line descriptions
- Key classes and functions per file
- Import relationships

Written for AI to skim, not humans to read. Lives in .claude/rules/
so Claude Code auto-loads it into context, reducing exploration tokens.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field


# File extensions we care about
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".lua", ".sh", ".bash", ".zsh",
}

CONFIG_EXTENSIONS = {
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".conf",
    ".env", ".lock",
}

DOC_EXTENSIONS = {
    ".md", ".rst", ".txt",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".eggs", "*.egg-info", "venv", ".venv", "env", ".env",
    ".claude", ".idea", ".vscode", "target", "out", "bin",
}

# Max files before we start being more aggressive about filtering
MAX_FILES = 200

# Max lines to read per file for analysis
MAX_LINES_PER_FILE = 300


@dataclass
class FileInfo:
    """Extracted info about a single source file."""
    rel_path: str
    extension: str
    line_count: int = 0
    description: str = ""
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def _should_skip_dir(name: str) -> bool:
    """Check if a directory should be skipped."""
    return name in SKIP_DIRS or name.startswith(".")


def _get_file_category(ext: str) -> str:
    """Categorize a file by extension."""
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in CONFIG_EXTENSIONS:
        return "config"
    if ext in DOC_EXTENSIONS:
        return "doc"
    return "other"


def _extract_python_info(content: str, lines: list[str]) -> tuple[list[str], list[str], list[str], str]:
    """Extract classes, functions, imports, and docstring from Python file."""
    classes = []
    functions = []
    imports = []
    description = ""

    # Module docstring (first string literal)
    doc_match = re.match(r'^(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')', content, re.DOTALL)
    if doc_match:
        doc = (doc_match.group(1) or doc_match.group(2) or "").strip()
        # Take first line of docstring
        description = doc.split("\n")[0].strip()

    for line in lines[:MAX_LINES_PER_FILE]:
        stripped = line.strip()

        # Classes (top-level only — no indentation)
        if line.startswith("class ") and ":" in line:
            match = re.match(r"class\s+(\w+)", stripped)
            if match:
                classes.append(match.group(1))

        # Functions (top-level and methods — but we only take top-level for the map)
        if line.startswith("def ") and ":" in line:
            match = re.match(r"def\s+(\w+)", stripped)
            if match:
                name = match.group(1)
                if not name.startswith("_"):
                    functions.append(name)

        # Async functions
        if line.startswith("async def ") and ":" in line:
            match = re.match(r"async\s+def\s+(\w+)", stripped)
            if match:
                name = match.group(1)
                if not name.startswith("_"):
                    functions.append(name)

        # Imports (from X import Y)
        if stripped.startswith("from ") and " import " in stripped:
            match = re.match(r"from\s+([\w.]+)\s+import", stripped)
            if match:
                module = match.group(1)
                # Only track internal imports (relative or project imports)
                if module.startswith(".") or module.startswith("buddies"):
                    imports.append(module)

    return classes, functions, imports, description


def _extract_js_ts_info(content: str, lines: list[str]) -> tuple[list[str], list[str], list[str], str]:
    """Extract classes, functions, imports from JS/TS files."""
    classes = []
    functions = []
    imports = []
    description = ""

    for line in lines[:MAX_LINES_PER_FILE]:
        stripped = line.strip()

        if re.match(r"(export\s+)?(class|interface)\s+\w+", stripped):
            match = re.search(r"(class|interface)\s+(\w+)", stripped)
            if match:
                classes.append(match.group(2))

        if re.match(r"(export\s+)?(async\s+)?function\s+\w+", stripped):
            match = re.search(r"function\s+(\w+)", stripped)
            if match:
                functions.append(match.group(1))

        if re.match(r"(export\s+)?const\s+\w+\s*=\s*(async\s+)?\(", stripped):
            match = re.search(r"const\s+(\w+)", stripped)
            if match:
                functions.append(match.group(1))

        if stripped.startswith("import "):
            match = re.search(r"from\s+['\"](.+?)['\"]", stripped)
            if match and match.group(1).startswith("."):
                imports.append(match.group(1))

    return classes, functions, imports, description


def _extract_general_info(content: str, lines: list[str], ext: str) -> tuple[list[str], list[str], list[str], str]:
    """Extract basic structure from other languages."""
    classes = []
    functions = []

    for line in lines[:MAX_LINES_PER_FILE]:
        stripped = line.strip()

        # Generic class detection
        match = re.match(r"(?:pub\s+)?(?:class|struct|enum|trait|interface)\s+(\w+)", stripped)
        if match:
            classes.append(match.group(1))

        # Generic function detection
        match = re.match(r"(?:pub\s+)?(?:fn|func|def|function|sub)\s+(\w+)", stripped)
        if match:
            name = match.group(1)
            if not name.startswith("_"):
                functions.append(name)

    return classes, functions, [], ""


def scan_project(project_path: Path) -> list[FileInfo]:
    """Scan a project directory and extract file information."""
    files: list[FileInfo] = []

    for root, dirs, filenames in os.walk(project_path):
        # Filter out skip directories in-place
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]

        rel_root = Path(root).relative_to(project_path)

        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            category = _get_file_category(ext)

            if category == "other":
                continue

            rel_path = str(rel_root / filename).replace("\\", "/")
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]

            file_path = Path(root) / filename
            info = FileInfo(rel_path=rel_path, extension=ext)

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                info.line_count = len(lines)

                if category == "code":
                    if ext == ".py":
                        info.classes, info.functions, info.imports, info.description = (
                            _extract_python_info(content, lines)
                        )
                    elif ext in (".js", ".ts", ".tsx", ".jsx"):
                        info.classes, info.functions, info.imports, info.description = (
                            _extract_js_ts_info(content, lines)
                        )
                    else:
                        info.classes, info.functions, info.imports, info.description = (
                            _extract_general_info(content, lines, ext)
                        )
                elif category == "config":
                    info.description = f"{ext.lstrip('.')} config"
                elif category == "doc":
                    # First non-empty, non-heading line as description
                    for line in lines[:10]:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            info.description = stripped[:80]
                            break

            except (OSError, UnicodeDecodeError):
                pass

            files.append(info)

            if len(files) >= MAX_FILES:
                return files

    return files


def generate_project_map(project_path: Path) -> str:
    """Generate a concise project map as markdown text."""
    files = scan_project(project_path)

    if not files:
        return "# Project Map\n\nNo source files found.\n"

    lines = [
        "# Project Map",
        "",
        f"Auto-generated code structure for AI navigation. {len(files)} files indexed.",
        "",
    ]

    # Group by directory
    dirs: dict[str, list[FileInfo]] = {}
    for f in files:
        dir_name = str(Path(f.rel_path).parent)
        if dir_name == ".":
            dir_name = "(root)"
        dirs.setdefault(dir_name, []).append(f)

    # File tree with descriptions
    lines.append("## File Tree")
    lines.append("")

    for dir_name in sorted(dirs.keys()):
        dir_files = dirs[dir_name]
        lines.append(f"### {dir_name}/")
        for f in dir_files:
            desc = f" — {f.description}" if f.description else ""
            loc = f" ({f.line_count}L)" if f.line_count > 0 else ""
            lines.append(f"- `{Path(f.rel_path).name}`{loc}{desc}")
        lines.append("")

    # Key symbols (classes + public functions) for code files only
    code_files = [f for f in files if _get_file_category(f.extension) == "code"]
    has_symbols = [f for f in code_files if f.classes or f.functions]

    if has_symbols:
        lines.append("## Key Symbols")
        lines.append("")

        for f in has_symbols:
            parts = []
            if f.classes:
                parts.append("classes: " + ", ".join(f.classes[:8]))
            if f.functions:
                # Limit to 10 most important functions
                funcs = f.functions[:10]
                parts.append("fns: " + ", ".join(funcs))

            if parts:
                lines.append(f"- **{f.rel_path}**: {' | '.join(parts)}")

        lines.append("")

    # Internal import graph (only for files with internal imports)
    imports_files = [f for f in code_files if f.imports]
    if imports_files:
        lines.append("## Internal Dependencies")
        lines.append("")
        for f in imports_files:
            deps = ", ".join(sorted(set(f.imports)))
            lines.append(f"- `{f.rel_path}` ← {deps}")
        lines.append("")

    return "\n".join(lines)


def write_project_map(project_path: Path) -> Path:
    """Generate and write project-map.md to .claude/rules/."""
    map_content = generate_project_map(project_path)

    rules_dir = project_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    map_path = rules_dir / "project-map.md"
    map_path.write_text(map_content, encoding="utf-8")

    return map_path
