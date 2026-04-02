"""Tests for AI backend, router, and agent modules."""

from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from buddies.config import AIBackendConfig
from buddies.core.ai_backend import AIBackend, AIResponse, OfflineBackend, create_backend
from buddies.core.ai_router import (
    AIRouter,
    BUDDY_PATTERNS,
    COMPLEX_PATTERNS,
    SIMPLE_PATTERNS,
    RoutingDecision,
)
from buddies.core.agent import (
    ALLOWED_COMMANDS,
    SHELL_METACHARACTERS,
    ToolResult,
    execute_tool,
    _resolve_path,
)
from buddies.core.buddy_brain import BuddyState, Species, Rarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_buddy(name="Tester", dominant="patience", **overrides):
    stats = {"debugging": 10, "chaos": 10, "snark": 10, "wisdom": 10, "patience": 10}
    stats[dominant] = max(stats.get(dominant, 10), 30)
    sp = Species(
        name="test_species", emoji="🐱", rarity=Rarity.COMMON,
        base_stats=stats, description="Test buddy",
    )
    defaults = dict(
        name=name, species=sp, level=5, xp=0, mood="happy",
        stats=stats, shiny=False, buddy_id=1, mood_value=50,
        soul_description="test", hat=None, hats_owned=[],
    )
    defaults.update(overrides)
    return BuddyState(**defaults)


def make_config(**overrides):
    defaults = dict(provider="none", base_url="http://localhost:11434", model="test-model")
    defaults.update(overrides)
    return AIBackendConfig(**defaults)


# ===========================================================================
# AI Backend Tests
# ===========================================================================

class TestAIResponse:
    """AIResponse dataclass creation and defaults."""

    def test_create_with_required_fields(self):
        resp = AIResponse(content="hello", tokens_used=42, model="test")
        assert resp.content == "hello"
        assert resp.tokens_used == 42
        assert resp.model == "test"

    def test_default_fields(self):
        resp = AIResponse(content="", tokens_used=0, model="m")
        assert resp.handled_locally is True
        assert resp.error == ""

    def test_custom_defaults(self):
        resp = AIResponse(content="x", tokens_used=1, model="m",
                          handled_locally=False, error="oops")
        assert resp.handled_locally is False
        assert resp.error == "oops"


class TestOfflineBackend:
    """OfflineBackend always reports unavailable."""

    def test_is_available_returns_false(self):
        cfg = make_config(provider="none")
        backend = OfflineBackend(cfg)
        assert run(backend.is_available()) is False

    def test_generate_returns_offline_message(self):
        cfg = make_config(provider="none")
        backend = OfflineBackend(cfg)
        resp = run(backend.chat([{"role": "user", "content": "hi"}]))
        assert resp.model == "none"
        assert resp.handled_locally is False
        assert "No AI backend configured" in resp.error

    def test_chat_with_system_prompt(self):
        cfg = make_config(provider="none")
        backend = OfflineBackend(cfg)
        resp = run(backend.chat([], system_prompt="be helpful"))
        assert resp.error != ""
        assert resp.tokens_used == 0


class TestAIBackend:
    """AIBackend constructor and config storage."""

    def test_stores_config(self):
        cfg = make_config(provider="ollama")
        backend = AIBackend(cfg)
        assert backend.config is cfg
        assert backend.config.provider == "ollama"

    def test_initial_state(self):
        cfg = make_config()
        backend = AIBackend(cfg)
        assert backend._client is None
        assert backend._available is None

    def test_chat_returns_error_when_unavailable(self):
        """Provider=none -> is_available returns False -> chat returns error."""
        cfg = make_config(provider="none")
        backend = AIBackend(cfg)
        resp = run(backend.chat([{"role": "user", "content": "hi"}]))
        assert resp.error == "No AI backend available"
        assert resp.handled_locally is False


class TestCreateBackend:
    """Factory function create_backend."""

    def test_none_returns_offline(self):
        cfg = make_config(provider="none")
        backend = create_backend(cfg)
        assert isinstance(backend, OfflineBackend)

    def test_ollama_returns_ai_backend(self):
        cfg = make_config(provider="ollama")
        backend = create_backend(cfg)
        assert isinstance(backend, AIBackend)
        assert not isinstance(backend, OfflineBackend)

    def test_openai_compatible_returns_ai_backend(self):
        cfg = make_config(provider="openai-compatible")
        backend = create_backend(cfg)
        assert isinstance(backend, AIBackend)


# ===========================================================================
# AI Router Tests
# ===========================================================================

class TestComplexityScoring:
    """Router scores queries on a 0.0-1.0 complexity scale."""

    def _score(self, query: str) -> float:
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        return router.score_complexity(query)

    # Buddy-handled (score == 0.0)
    def test_greeting_scores_zero(self):
        assert self._score("hello") == 0.0

    def test_status_scores_zero(self):
        assert self._score("how are you") == 0.0

    def test_help_scores_zero(self):
        assert self._score("help") == 0.0

    def test_level_scores_zero(self):
        assert self._score("what level am I at") == 0.0

    def test_name_scores_zero(self):
        assert self._score("what is your name") == 0.0

    # Simple patterns -> low scores (< 0.5)
    def test_simple_definition_scores_low(self):
        score = self._score("what is a decorator")
        assert score < 0.5

    def test_syntax_question_scores_low(self):
        score = self._score("syntax for list comprehension")
        assert score < 0.5

    def test_short_query_pulls_score_down(self):
        # Short + simple pattern = low
        score = self._score("convert int to str")
        assert score < 0.5

    # Complex patterns -> high scores (>= 0.7)
    def test_refactor_scores_high(self):
        score = self._score("refactor the entire authentication system across multiple files")
        assert score >= 0.7

    def test_architecture_scores_high(self):
        score = self._score("architect a new microservice system for our application")
        assert score >= 0.7

    def test_multi_file_scores_high(self):
        score = self._score("review code across files and implement a new feature module")
        assert score >= 0.7

    def test_debug_complex_issue_scores_high(self):
        score = self._score("debug and troubleshoot this crash error in the build system /src/main.py")
        assert score >= 0.7

    # Medium complexity
    def test_medium_coding_question(self):
        score = self._score("explain how async await works in Python")
        assert 0.0 < score < 0.7

    # Heuristics
    def test_code_blocks_increase_score(self):
        plain = self._score("fix this function")
        with_code = self._score("fix this function ```\ndef foo():\n  pass\n```")
        assert with_code > plain

    def test_long_query_increases_score(self):
        short = self._score("explain decorators")
        long_q = " ".join(["explain decorators and"] * 20)
        assert self._score(long_q) > short

    def test_score_clamped_to_0_1(self):
        # Even extreme queries stay in [0.0, 1.0]
        extreme = "refactor rewrite redesign restructure migrate optimize " * 5
        score = self._score(extreme)
        assert 0.0 <= score <= 1.0


class TestRoutingDecision:
    """RoutingDecision dataclass."""

    def test_stores_fields(self):
        rd = RoutingDecision(
            route="local", complexity_score=0.3,
            reason="test", response="hi", tokens_saved=100,
        )
        assert rd.route == "local"
        assert rd.complexity_score == 0.3
        assert rd.reason == "test"
        assert rd.response == "hi"
        assert rd.tokens_saved == 100

    def test_default_fields(self):
        rd = RoutingDecision(route="claude", complexity_score=0.8, reason="complex")
        assert rd.response == ""
        assert rd.tokens_saved == 0


class TestRouterRouting:
    """Router routes queries to correct destinations."""

    def test_buddy_only_for_greetings(self):
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        result = run(router.route("hello"))
        assert result.route == "buddy_only"
        assert result.complexity_score == 0.0

    def test_claude_for_complex_query(self):
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        result = run(router.route(
            "refactor the entire authentication system and review code across files"
        ))
        assert result.route == "claude"
        assert result.complexity_score >= 0.7

    def test_buddy_fallback_when_backend_unavailable(self):
        """Medium-complexity query with offline backend falls back to buddy."""
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        result = run(router.route("what is a Python decorator"))
        assert result.route == "buddy_only"
        assert "not available" in result.reason.lower() or "offline" in result.reason.lower() or "buddy" in result.reason.lower()

    def test_expensive_tier_uses_buddy_fallback(self):
        """Expensive cost tier should not send chat traffic."""
        cfg = make_config(provider="ollama", cost_tier="expensive")
        backend = AIBackend(cfg)
        # Mock is_available to return True so we reach the cost-tier check
        backend.is_available = AsyncMock(return_value=True)
        backend._client = MagicMock()
        router = AIRouter(backend)
        # Use a medium-complexity query (not buddy-handled, not claude-level)
        result = run(router.route("what is the syntax for list comprehension"))
        assert result.route == "buddy_only"
        assert "expensive" in result.reason.lower()

    def test_tokens_saved_tracking(self):
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        assert router.tokens_saved == 0

    def test_clear_conversation(self):
        cfg = make_config()
        backend = OfflineBackend(cfg)
        router = AIRouter(backend)
        router._conversation.append({"role": "user", "content": "test"})
        router.clear_conversation()
        assert len(router._conversation) == 0


# ===========================================================================
# Agent Tests
# ===========================================================================

class TestToolResult:
    """ToolResult dataclass."""

    def test_create(self):
        tr = ToolResult(name="read_file", output="contents here")
        assert tr.name == "read_file"
        assert tr.output == "contents here"
        assert tr.success is True

    def test_failure(self):
        tr = ToolResult(name="run_command", output="error", success=False)
        assert tr.success is False


class TestExecuteToolReadFile:
    """execute_tool with read_file."""

    def test_read_existing_file(self, tmp_path):
        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello World", encoding="utf-8")
        result = execute_tool("read_file", {"path": "hello.txt"}, str(tmp_path))
        assert result.success is True
        assert "Hello World" in result.output

    def test_read_nonexistent_file(self, tmp_path):
        result = execute_tool("read_file", {"path": "nope.txt"}, str(tmp_path))
        assert result.success is False
        assert "not found" in result.output.lower()

    def test_read_file_truncates_long_content(self, tmp_path):
        test_file = tmp_path / "big.txt"
        test_file.write_text("\n".join(f"line {i}" for i in range(600)), encoding="utf-8")
        result = execute_tool("read_file", {"path": "big.txt"}, str(tmp_path))
        assert result.success is True
        assert "truncated" in result.output.lower()


class TestPathTraversal:
    """Path traversal attacks are blocked."""

    def test_dotdot_blocked(self, tmp_path):
        result = execute_tool("read_file", {"path": "../../etc/passwd"}, str(tmp_path))
        assert result.success is False
        assert "escape" in result.output.lower() or "error" in result.output.lower()

    def test_absolute_path_outside_workdir(self, tmp_path):
        # Absolute path that's outside working dir
        result = execute_tool("read_file", {"path": "/etc/passwd"}, str(tmp_path))
        assert result.success is False

    def test_resolve_path_raises_on_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="escapes"):
            _resolve_path("../../etc/passwd", str(tmp_path))


class TestExecuteToolListFiles:
    """execute_tool with list_files."""

    def test_list_directory(self, tmp_path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        result = execute_tool("list_files", {"path": "."}, str(tmp_path))
        assert result.success is True
        assert "a.py" in result.output
        assert "b.txt" in result.output

    def test_list_nonexistent_dir(self, tmp_path):
        result = execute_tool("list_files", {"path": "nope"}, str(tmp_path))
        assert result.success is False


class TestExecuteToolGrepSearch:
    """execute_tool with grep_search."""

    def test_grep_finds_pattern(self, tmp_path):
        (tmp_path / "code.py").write_text("def hello():\n    pass\n", encoding="utf-8")
        result = execute_tool("grep_search", {"pattern": "def hello", "path": "."}, str(tmp_path))
        assert result.success is True
        assert "hello" in result.output

    def test_grep_no_matches(self, tmp_path):
        (tmp_path / "code.py").write_text("x = 1\n", encoding="utf-8")
        result = execute_tool("grep_search", {"pattern": "zzz_not_here"}, str(tmp_path))
        assert "No matches" in result.output

    def test_grep_invalid_regex(self, tmp_path):
        result = execute_tool("grep_search", {"pattern": "[invalid"}, str(tmp_path))
        assert result.success is False
        assert "regex" in result.output.lower()


class TestExecuteToolRunCommand:
    """execute_tool with run_command — safety checks."""

    def test_blocks_rm(self, tmp_path):
        result = execute_tool("run_command", {"command": "rm -rf /"}, str(tmp_path))
        assert result.success is False
        assert "not in the allowed list" in result.output.lower() or "not allowed" in result.output.lower()

    def test_blocks_shell_metacharacters(self, tmp_path):
        result = execute_tool("run_command", {"command": "echo hi; rm -rf /"}, str(tmp_path))
        assert result.success is False
        assert "metacharacter" in result.output.lower()

    def test_blocks_pipe(self, tmp_path):
        result = execute_tool("run_command", {"command": "cat foo | grep bar"}, str(tmp_path))
        assert result.success is False

    def test_blocks_backtick(self, tmp_path):
        result = execute_tool("run_command", {"command": "echo `whoami`"}, str(tmp_path))
        assert result.success is False

    def test_blocks_git_push(self, tmp_path):
        """git push is not in the allowed subcommands."""
        result = execute_tool("run_command", {"command": "git push"}, str(tmp_path))
        assert result.success is False
        assert "not allowed" in result.output.lower()

    def test_allows_git_status(self, tmp_path):
        """git status is in the allowed subcommands."""
        # This may fail if git isn't installed, but the command itself should be allowed
        result = execute_tool("run_command", {"command": "git status"}, str(tmp_path))
        # Even if git returns non-zero (not a repo), the command was permitted
        assert "not in the allowed list" not in result.output.lower()
        assert "not allowed" not in result.output.lower() or "git status" not in result.output.lower()


class TestExecuteToolUnknown:
    """Unknown tool names return an error."""

    def test_unknown_tool(self, tmp_path):
        result = execute_tool("delete_everything", {}, str(tmp_path))
        assert result.success is False
        assert "Unknown tool" in result.output


class TestAllowedCommands:
    """Verify the ALLOWED_COMMANDS allowlist structure."""

    def test_dangerous_commands_not_allowed(self):
        for dangerous in ["rm", "rmdir", "del", "mv", "cp", "chmod", "chown", "sudo", "curl", "wget"]:
            assert dangerous not in ALLOWED_COMMANDS, f"{dangerous} should not be allowed"

    def test_git_subcommands_restricted(self):
        allowed_git = ALLOWED_COMMANDS["git"]
        assert allowed_git is not None  # git has subcommand restrictions
        assert "status" in allowed_git
        assert "push" not in allowed_git
        assert "reset" not in allowed_git
        assert "checkout" not in allowed_git

    def test_shell_metacharacters_comprehensive(self):
        for char in ";|&`$(){}!><":
            assert char in SHELL_METACHARACTERS
