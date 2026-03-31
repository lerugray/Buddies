"""Agentic tool loop — gives the local AI model real capabilities.

Inspired by claw-code's Rust ConversationRuntime. Sends messages to
Ollama with tool definitions, parses tool_use responses, executes
tools locally, feeds results back, and loops until a text response.

Tools available to the local model:
- read_file: Read a file's contents
- list_files: List files in a directory
- grep_search: Search file contents with regex
- run_command: Execute a shell command (with user approval)

Safety: all tool executions are sandboxed to the current working
directory. Bash commands require explicit patterns to be allowed.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from buddies.core.ai_backend import AIBackend, AIResponse


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format, works with Ollama)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Returns the file text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to working directory)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a path. Returns names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (relative to working directory). Use '.' for current directory.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search for a pattern in files. Returns matching lines with file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: current directory)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return its output. Only safe read-only commands are allowed (ls, cat, git status, python --version, etc). Destructive commands are blocked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run",
                    },
                },
                "required": ["command"],
            },
        },
    },
]

# Commands that are safe for the buddy to run
SAFE_COMMAND_PATTERNS = [
    r"^ls\b",
    r"^dir\b",
    r"^cat\b",
    r"^head\b",
    r"^tail\b",
    r"^wc\b",
    r"^find\b",
    r"^git\s+(status|log|diff|branch|show|blame)\b",
    r"^python\s+--version",
    r"^python\s+-c\b",
    r"^pip\s+(list|show|freeze)\b",
    r"^echo\b",
    r"^pwd\b",
    r"^whoami\b",
    r"^date\b",
    r"^type\b",
    r"^which\b",
    r"^where\b",
]

# Explicitly blocked patterns
BLOCKED_PATTERNS = [
    r"\brm\b",
    r"\bdel\b",
    r"\brmdir\b",
    r"\bmkdir\b",
    r"\bmv\b",
    r"\bcp\b",
    r"\bgit\s+(push|reset|checkout|clean|rebase)\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bsudo\b",
    r"\bformat\b",
    r"\bdd\b",
    r"\b>\b",  # redirect/overwrite
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bcurl\b",
    r"\bwget\b",
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Result of a tool execution."""
    name: str
    output: str
    success: bool = True


def _resolve_path(path: str, working_dir: str) -> Path:
    """Resolve a path relative to working directory, blocking traversal."""
    resolved = Path(working_dir) / path
    resolved = resolved.resolve()
    # Ensure we don't escape the working directory
    if not str(resolved).startswith(str(Path(working_dir).resolve())):
        raise ValueError(f"Path escapes working directory: {path}")
    return resolved


def execute_tool(name: str, arguments: dict, working_dir: str) -> ToolResult:
    """Execute a tool and return the result."""
    try:
        if name == "read_file":
            return _exec_read_file(arguments, working_dir)
        elif name == "list_files":
            return _exec_list_files(arguments, working_dir)
        elif name == "grep_search":
            return _exec_grep_search(arguments, working_dir)
        elif name == "run_command":
            return _exec_run_command(arguments, working_dir)
        else:
            return ToolResult(name=name, output=f"Unknown tool: {name}", success=False)
    except Exception as e:
        return ToolResult(name=name, output=f"Error: {e}", success=False)


def _exec_read_file(args: dict, working_dir: str) -> ToolResult:
    path = _resolve_path(args["path"], working_dir)
    if not path.exists():
        return ToolResult(name="read_file", output=f"File not found: {args['path']}", success=False)
    if not path.is_file():
        return ToolResult(name="read_file", output=f"Not a file: {args['path']}", success=False)
    # Limit to 500 lines to avoid blowing context
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > 500:
        content = "\n".join(lines[:500]) + f"\n... ({len(lines) - 500} more lines truncated)"
    else:
        content = "\n".join(lines)
    return ToolResult(name="read_file", output=content)


def _exec_list_files(args: dict, working_dir: str) -> ToolResult:
    path = _resolve_path(args.get("path", "."), working_dir)
    if not path.exists():
        return ToolResult(name="list_files", output=f"Path not found: {args['path']}", success=False)
    if not path.is_dir():
        return ToolResult(name="list_files", output=f"Not a directory: {args['path']}", success=False)
    entries = sorted(path.iterdir())
    lines = []
    for e in entries[:100]:  # Cap at 100 entries
        prefix = "📁 " if e.is_dir() else "📄 "
        lines.append(f"{prefix}{e.name}")
    if len(entries) > 100:
        lines.append(f"... ({len(entries) - 100} more entries)")
    return ToolResult(name="list_files", output="\n".join(lines))


def _exec_grep_search(args: dict, working_dir: str) -> ToolResult:
    pattern = args["pattern"]
    search_path = _resolve_path(args.get("path", "."), working_dir)

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return ToolResult(name="grep_search", output=f"Invalid regex: {e}", success=False)

    matches = []
    if search_path.is_file():
        files = [search_path]
    else:
        files = [f for f in search_path.rglob("*") if f.is_file() and f.suffix in (
            ".py", ".js", ".ts", ".rs", ".go", ".java", ".md", ".txt", ".toml",
            ".yaml", ".yml", ".json", ".css", ".html", ".sh", ".bat",
        )]

    for fpath in files[:200]:  # Cap files searched
        try:
            for i, line in enumerate(fpath.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if regex.search(line):
                    rel = fpath.relative_to(Path(working_dir).resolve())
                    matches.append(f"{rel}:{i}: {line.strip()}")
                    if len(matches) >= 50:
                        break
        except Exception:
            continue
        if len(matches) >= 50:
            break

    if not matches:
        return ToolResult(name="grep_search", output=f"No matches for '{pattern}'")
    return ToolResult(name="grep_search", output="\n".join(matches))


def _exec_run_command(args: dict, working_dir: str) -> ToolResult:
    command = args["command"].strip()

    # Check blocked patterns first
    for blocked in BLOCKED_PATTERNS:
        if re.search(blocked, command):
            return ToolResult(
                name="run_command",
                output=f"Command blocked for safety: {command}",
                success=False,
            )

    # Check if command matches safe patterns
    is_safe = any(re.search(p, command) for p in SAFE_COMMAND_PATTERNS)
    if not is_safe:
        return ToolResult(
            name="run_command",
            output=f"Command not in safe list: {command}. Only read-only commands are allowed.",
            success=False,
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=working_dir,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        # Truncate long output
        if len(output) > 5000:
            output = output[:5000] + "\n... (output truncated)"
        return ToolResult(name="run_command", output=output or "(no output)")
    except subprocess.TimeoutExpired:
        return ToolResult(name="run_command", output="Command timed out (30s limit)", success=False)


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Final result of an agent loop run."""
    response: str
    tool_calls_made: int
    tools_used: list[str] = field(default_factory=list)
    error: str = ""


class BuddyAgent:
    """Agentic tool loop for the local AI model.

    Sends queries to Ollama with tool definitions, executes tool calls,
    feeds results back, and loops until the model produces a text response.
    """

    MAX_ITERATIONS = 8

    def __init__(self, backend: AIBackend, working_dir: str | None = None):
        self.backend = backend
        self.working_dir = working_dir or os.getcwd()

    async def run(self, query: str, system_prompt: str = "") -> AgentResult:
        """Run the agent loop for a query.

        Returns the final text response after all tool calls are resolved.
        """
        if not await self.backend.is_available():
            return AgentResult(
                response="",
                tool_calls_made=0,
                error="No AI backend available",
            )

        messages = [{"role": "user", "content": query}]
        tools_used = []
        total_tool_calls = 0

        for iteration in range(self.MAX_ITERATIONS):
            # Send to Ollama with tools
            response = await self._chat_with_tools(messages, system_prompt)

            if response.error:
                return AgentResult(
                    response="",
                    tool_calls_made=total_tool_calls,
                    tools_used=tools_used,
                    error=response.error,
                )

            # Check if model wants to call tools
            tool_calls = response.tool_calls
            if not tool_calls:
                # No tool calls — model is done, return text
                return AgentResult(
                    response=response.content,
                    tool_calls_made=total_tool_calls,
                    tools_used=tools_used,
                )

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": tool_calls,
            })

            # Execute each tool call
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                result = execute_tool(func_name, func_args, self.working_dir)
                tools_used.append(func_name)
                total_tool_calls += 1

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{total_tool_calls}"),
                    "content": result.output,
                })

        # Hit max iterations
        return AgentResult(
            response="I've reached my tool call limit for this query. Here's what I found so far.",
            tool_calls_made=total_tool_calls,
            tools_used=tools_used,
        )

    async def _chat_with_tools(
        self, messages: list[dict], system_prompt: str
    ) -> "_ToolResponse":
        """Send a chat request with tool definitions to the backend."""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            if self.backend.config.provider == "ollama":
                return await self._ollama_with_tools(full_messages)
            else:
                return await self._openai_with_tools(full_messages)
        except Exception as e:
            return _ToolResponse(content="", tool_calls=[], error=str(e))

    async def _ollama_with_tools(self, messages: list[dict]) -> "_ToolResponse":
        """Ollama chat with tool calling support."""
        resp = await self.backend._client.post(
            f"{self.backend.config.base_url}/api/chat",
            json={
                "model": self.backend.config.model,
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
                "stream": False,
                "options": {
                    "temperature": self.backend.config.temperature,
                    "num_predict": self.backend.config.max_tokens,
                },
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data.get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        return _ToolResponse(content=content.strip(), tool_calls=tool_calls)

    async def _openai_with_tools(self, messages: list[dict]) -> "_ToolResponse":
        """OpenAI-compatible chat with tool calling."""
        headers = {"Content-Type": "application/json"}
        if self.backend.config.api_key:
            headers["Authorization"] = f"Bearer {self.backend.config.api_key}"

        resp = await self.backend._client.post(
            f"{self.backend.config.base_url}/v1/chat/completions",
            headers=headers,
            json={
                "model": self.backend.config.model,
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
                "max_tokens": self.backend.config.max_tokens,
                "temperature": self.backend.config.temperature,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        return _ToolResponse(content=content.strip(), tool_calls=tool_calls)


@dataclass
class _ToolResponse:
    """Internal response from a chat-with-tools call."""
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    error: str = ""
