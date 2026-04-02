"""Tests for code map generation and staleness detection."""

import tempfile
import time
from pathlib import Path

import pytest

from buddies.core.code_map import (
    scan_project, generate_project_map, write_project_map, is_map_stale,
    FileInfo,
)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

class TestScanProject:
    def test_scan_finds_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "lib.py").write_text("def foo(): pass\n")
        files = scan_project(tmp_path)
        assert len(files) >= 2
        names = [f.rel_path for f in files]
        assert "main.py" in names
        assert "lib.py" in names

    def test_scan_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.py").write_text("x = 1\n")
        (tmp_path / "visible.py").write_text("y = 2\n")
        files = scan_project(tmp_path)
        names = [f.rel_path for f in files]
        assert "visible.py" in names
        assert ".hidden/secret.py" not in names

    def test_scan_extracts_python_classes(self, tmp_path):
        (tmp_path / "model.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        files = scan_project(tmp_path)
        model = next(f for f in files if f.rel_path == "model.py")
        assert "Foo" in model.classes
        assert "Bar" in model.classes

    def test_scan_extracts_python_functions(self, tmp_path):
        (tmp_path / "utils.py").write_text("def helper():\n    pass\ndef another():\n    pass\n")
        files = scan_project(tmp_path)
        utils = next(f for f in files if f.rel_path == "utils.py")
        assert "helper" in utils.functions
        assert "another" in utils.functions

    def test_scan_counts_lines(self, tmp_path):
        (tmp_path / "short.py").write_text("a\nb\nc\n")
        files = scan_project(tmp_path)
        short = next(f for f in files if f.rel_path == "short.py")
        assert short.line_count >= 3  # trailing newline may add an extra


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------

class TestGenerateMap:
    def test_generates_markdown(self, tmp_path):
        (tmp_path / "app.py").write_text("class App: pass\n")
        content = generate_project_map(tmp_path)
        assert "# Project Map" in content
        assert "app.py" in content

    def test_empty_project(self, tmp_path):
        content = generate_project_map(tmp_path)
        assert "No source files found" in content


# ---------------------------------------------------------------------------
# Write and staleness
# ---------------------------------------------------------------------------

class TestWriteAndStaleness:
    def test_write_creates_file(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        rules = tmp_path / ".claude" / "rules"
        rules.mkdir(parents=True)
        path = write_project_map(tmp_path)
        assert path.exists()
        assert "project-map.md" in path.name

    def test_stale_when_no_map(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        assert is_map_stale(tmp_path) is True

    def test_not_stale_after_write(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        write_project_map(tmp_path)
        # Give filesystem time to settle
        assert is_map_stale(tmp_path) is False

    def test_stale_after_file_modified(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        write_project_map(tmp_path)
        # Modify a file after the map was written
        time.sleep(0.1)
        (tmp_path / "main.py").write_text("x = 2\n")
        assert is_map_stale(tmp_path) is True

    def test_stale_after_new_file(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        write_project_map(tmp_path)
        time.sleep(0.1)
        (tmp_path / "new_module.py").write_text("y = 2\n")
        assert is_map_stale(tmp_path) is True
