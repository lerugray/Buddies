"""Query complexity router — decides whether to handle locally or flag for Claude.

The router scores incoming queries on complexity and routes them:
- Simple queries → local AI (saves Claude tokens)
- Complex queries → tells the user to ask Claude instead
- Medium queries → tries local, falls back to Claude suggestion if response seems weak
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections import deque

from buddies.core.ai_backend import AIBackend, AIResponse
from buddies.core.agent import BuddyAgent
from buddies.core.buddy_brain import BuddyState


@dataclass
class RoutingDecision:
    """Result of the routing decision."""
    route: str  # "local", "claude", "buddy_only"
    complexity_score: float  # 0.0 (trivial) to 1.0 (very complex)
    reason: str
    response: str = ""
    tokens_saved: int = 0


# Keywords/patterns that suggest simple queries
SIMPLE_PATTERNS = [
    r"\b(what is|what's|define|meaning of)\b",
    r"\b(syntax|how to write|format for)\b",
    r"\b(convert|translate)\b.{0,30}\b(to|into)\b",
    r"\b(list|enumerate|name)\b.{0,20}\b(types|kinds|examples)\b",
    r"\b(difference between)\b",
    r"\b(when to use|should i use)\b",
    r"\b(explain|describe)\b.{0,30}\b(briefly|simply|quickly)\b",
    r"\b(what does .{0,30} mean)\b",
    r"\b(how many|how much|how long)\b",
    r"\b(yes or no|true or false)\b",
]

# Keywords that suggest complex queries requiring Claude
COMPLEX_PATTERNS = [
    r"\b(refactor|rewrite|redesign|restructure)\b",
    r"\b(implement|build|create|develop)\b.{0,30}\b(feature|system|module|component)\b",
    r"\b(debug|fix|diagnose|troubleshoot)\b.{0,30}\b(error|bug|issue|problem|crash)\b",
    r"\b(architect|design|plan)\b.{0,30}\b(system|application|service)\b",
    r"\b(review|audit|analyze)\b.{0,30}\b(code|codebase|project)\b",
    r"\b(migrate|upgrade|port)\b",
    r"\b(optimize|performance|speed up)\b",
    r"\b(write tests|test coverage|testing strategy)\b",
    r"\b(multiple files|across files|entire project)\b",
    r"\b(security|vulnerability|authentication)\b",
]

# Queries that buddy handles directly without AI
BUDDY_PATTERNS = [
    r"^(hi|hello|hey|sup|yo)\b",
    r"\b(stats|status|how are you|mood)\b",
    r"\b(help|what can you do)\b",
    r"\b(name|who are you|what are you)\b",
    r"\b(session|tokens|usage|cost)\b",
    r"\b(level|xp|experience)\b",
]


class AIRouter:
    """Routes queries between local AI, Claude suggestions, and buddy responses."""

    def __init__(self, backend: AIBackend, buddy_state: BuddyState | None = None):
        self.backend = backend
        self.buddy_state = buddy_state
        self.agent = BuddyAgent(backend)
        self._conversation: deque[dict] = deque(maxlen=20)
        self._tokens_saved_total = 0

    @property
    def tokens_saved(self) -> int:
        return self._tokens_saved_total

    def score_complexity(self, query: str) -> float:
        """Score query complexity from 0.0 (trivial) to 1.0 (very complex)."""
        score = 0.5  # Start at medium

        query_lower = query.lower()

        # Check for buddy-handled patterns (lowest complexity)
        for pattern in BUDDY_PATTERNS:
            if re.search(pattern, query_lower):
                return 0.0

        # Simple patterns pull score down
        for pattern in SIMPLE_PATTERNS:
            if re.search(pattern, query_lower):
                score -= 0.15

        # Complex patterns push score up
        for pattern in COMPLEX_PATTERNS:
            if re.search(pattern, query_lower):
                score += 0.2

        # Length heuristics
        word_count = len(query.split())
        if word_count < 8:
            score -= 0.1
        elif word_count > 60:
            score += 0.2
        elif word_count > 30:
            score += 0.1

        # Code blocks suggest complexity
        if "```" in query or query.count("\n") > 5:
            score += 0.2

        # File paths suggest codebase work
        if re.search(r"[/\\]\w+\.\w+", query):
            score += 0.15

        return max(0.0, min(1.0, score))

    async def route(self, query: str) -> RoutingDecision:
        """Route a query and return the decision + response."""
        complexity = self.score_complexity(query)

        # Buddy handles its own stuff
        if complexity == 0.0:
            return RoutingDecision(
                route="buddy_only",
                complexity_score=0.0,
                reason="Buddy can handle this directly",
            )

        # High complexity → suggest Claude
        if complexity >= 0.7:
            estimated_tokens = len(query.split()) * 15  # rough estimate
            return RoutingDecision(
                route="claude",
                complexity_score=complexity,
                reason="This looks complex enough for Claude",
                response=(
                    f"This seems like a job for Claude — it involves "
                    f"{'code changes' if complexity > 0.8 else 'deeper analysis'} "
                    f"that I'd handle better with more reasoning power. "
                    f"Ask Claude directly and I'll watch the session!"
                ),
            )

        # Medium/low complexity → try local AI
        # Guard: never send chat traffic through expensive models
        backend_tier = getattr(self.backend.config, "cost_tier", "free")
        if backend_tier == "expensive":
            return RoutingDecision(
                route="buddy_only",
                complexity_score=complexity,
                reason="Backend is expensive-tier — using buddy fallback to save tokens",
            )

        if not await self.backend.is_available():
            return RoutingDecision(
                route="buddy_only",
                complexity_score=complexity,
                reason="Local AI not available, using buddy fallback",
            )

        # Check if query needs agentic tools (mentions files, code investigation)
        needs_tools = self._needs_tools(query)

        if needs_tools and complexity >= 0.3:
            # Use agentic loop with tool calling
            system_prompt = self._build_system_prompt()
            result = await self.agent.run(query, system_prompt)

            if result.error:
                # Fall back to simple chat
                pass
            elif result.response:
                estimated_claude_tokens = len(query.split()) * 15 + len(result.response.split()) * 5
                self._tokens_saved_total += estimated_claude_tokens
                tools_str = ", ".join(set(result.tools_used)) if result.tools_used else "none"
                return RoutingDecision(
                    route="local",
                    complexity_score=complexity,
                    reason=f"Agent mode ({result.tool_calls_made} tool calls: {tools_str})",
                    response=result.response,
                    tokens_saved=estimated_claude_tokens,
                )

        # Simple chat (no tools needed)
        system_prompt = self._build_system_prompt()

        # Add to conversation history
        self._conversation.append({"role": "user", "content": query})
        messages = list(self._conversation)

        ai_response = await self.backend.chat(messages, system_prompt)

        if ai_response.error:
            return RoutingDecision(
                route="buddy_only",
                complexity_score=complexity,
                reason=f"Local AI error: {ai_response.error}",
            )

        # Track conversation
        self._conversation.append({"role": "assistant", "content": ai_response.content})

        # Estimate tokens saved (what Claude would have used)
        estimated_claude_tokens = len(query.split()) * 15 + len(ai_response.content.split()) * 5
        self._tokens_saved_total += estimated_claude_tokens

        return RoutingDecision(
            route="local",
            complexity_score=complexity,
            reason=f"Handled locally ({ai_response.model})",
            response=ai_response.content,
            tokens_saved=estimated_claude_tokens,
        )

    def _needs_tools(self, query: str) -> bool:
        """Check if a query would benefit from tool use (file access, code search)."""
        tool_indicators = [
            r"(read|show|open|look at|check|view)\s.*(file|code|source|module)",
            r"(find|search|grep|where)\s.*(function|class|import|variable|definition)",
            r"(what|which)\s.*(files|modules|functions)",
            r"(list|show)\s.*(directory|folder|files)",
            r"[/\\]\w+\.\w+",  # file paths
            r"\.(py|js|ts|rs|go|java|toml|json|yaml|md)\b",  # file extensions
            r"(project|repo|codebase)\s.*(structure|layout|organization)",
            r"(run|execute|check)\s.*(command|script|test|version)",
        ]
        query_lower = query.lower()
        return any(re.search(p, query_lower) for p in tool_indicators)

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes buddy's personality."""
        personality = ""
        if self.buddy_state:
            top_stat = max(self.buddy_state.stats, key=self.buddy_state.stats.get)
            personality_traits = {
                "debugging": "You're analytical and detail-oriented. You like finding root causes.",
                "patience": "You're calm and methodical. You explain things step by step.",
                "chaos": "You're energetic and creative. You like unconventional solutions.",
                "wisdom": "You're thoughtful and philosophical. You see the bigger picture.",
                "snark": "You're witty and sarcastic, but always helpful underneath the sass.",
            }
            personality = personality_traits.get(top_stat, "")

        return (
            f"You are Buddy, a helpful AI companion running locally. "
            f"You assist with coding questions, explanations, and simple tasks. "
            f"Keep responses concise and practical. "
            f"If a question is too complex for you, say so honestly — "
            f"the user can ask Claude for harder tasks. "
            f"{personality}"
        )

    def clear_conversation(self):
        self._conversation.clear()
