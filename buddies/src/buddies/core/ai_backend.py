"""Flexible AI backend — connects to Ollama, OpenAI-compatible APIs, or runs offline.

Supports:
- Ollama (local or remote, e.g. on your home machine)
- Any OpenAI-compatible API (LM Studio, vLLM, Together, etc.)
- Graceful offline fallback when no backend is available
"""

from __future__ import annotations

import logging
import httpx
from dataclasses import dataclass

from buddies.config import AIBackendConfig

_log = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Response from the AI backend."""
    content: str
    tokens_used: int
    model: str
    handled_locally: bool = True
    error: str = ""


class AIBackend:
    """Unified interface to local/remote AI models."""

    def __init__(self, config: AIBackendConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None

    async def connect(self):
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def is_available(self) -> bool:
        """Check if the AI backend is reachable."""
        if self.config.provider == "none":
            return False
        if self._available is not None:
            return self._available

        try:
            if self.config.provider == "ollama":
                resp = await self._client.get(f"{self.config.base_url}/api/tags")
                self._available = resp.status_code == 200
            else:
                # OpenAI-compatible — try /v1/models
                headers = {}
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"
                resp = await self._client.get(
                    f"{self.config.base_url}/v1/models",
                    headers=headers,
                )
                self._available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False

        return self._available

    async def chat(self, messages: list[dict], system_prompt: str = "") -> AIResponse:
        """Send a chat completion request.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system prompt prepended to messages
        """
        if not await self.is_available():
            return AIResponse(
                content="",
                tokens_used=0,
                model="none",
                handled_locally=False,
                error="No AI backend available",
            )

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            if self.config.provider == "ollama":
                return await self._chat_ollama(full_messages)
            else:
                return await self._chat_openai_compatible(full_messages)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            self._available = False
            _log.warning("AI backend connection failed: %s", e)
            return AIResponse(
                content="",
                tokens_used=0,
                model=self.config.model,
                handled_locally=False,
                error="AI backend connection failed",
            )
        except Exception as e:
            _log.warning("AI backend error: %s", e)
            return AIResponse(
                content="",
                tokens_used=0,
                model=self.config.model,
                handled_locally=False,
                error="AI backend error",
            )

    async def _chat_ollama(self, messages: list[dict]) -> AIResponse:
        """Chat via Ollama's /api/chat endpoint."""
        resp = await self._client.post(
            f"{self.config.base_url}/api/chat",
            json={
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("message", {}).get("content", "")
        tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

        return AIResponse(
            content=content.strip(),
            tokens_used=tokens,
            model=self.config.model,
            handled_locally=True,
        )

    async def _chat_openai_compatible(self, messages: list[dict]) -> AIResponse:
        """Chat via OpenAI-compatible /v1/chat/completions."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        resp = await self._client.post(
            f"{self.config.base_url}/v1/chat/completions",
            headers=headers,
            json={
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)

        return AIResponse(
            content=content.strip(),
            tokens_used=tokens,
            model=self.config.model,
            handled_locally=True,
        )


class OfflineBackend(AIBackend):
    """Stub backend that always reports offline. Used when provider is 'none'."""

    async def is_available(self) -> bool:
        return False

    async def chat(self, messages, system_prompt="") -> AIResponse:
        return AIResponse(
            content="",
            tokens_used=0,
            model="none",
            handled_locally=False,
            error="No AI backend configured. Run buddy config to set one up.",
        )


def create_backend(config: AIBackendConfig) -> AIBackend:
    """Factory — create the right backend based on config."""
    if config.provider == "none":
        return OfflineBackend(config)
    return AIBackend(config)
