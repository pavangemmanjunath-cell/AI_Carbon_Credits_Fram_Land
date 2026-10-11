"""A minimal client for OpenAI-compatible ``/chat/completions`` endpoints.

Works with anything that speaks that wire format: Ollama
(``http://localhost:11434/v1``), vLLM, LM Studio, llama.cpp server, and hosted
OpenAI-style gateways.

Design rules (see docs/agents/README.md, "Switching on an LLM"):

* **Off unless configured.** :meth:`OpenAICompatibleProvider.from_settings` returns
  ``None`` unless the reasoner is ``llm`` *and* a base URL and model are set.
* **Bounded.** Every request has a timeout; a slow model cannot stall a run.
* **Quiet.** Prompts and replies are never logged. Errors carry the exception
  type and HTTP status only.
* **Lazy dependency.** ``httpx`` is imported when the client is created, so the
  rest of the framework works without it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from carboncreditbuy_agents.llm.base import ChatMessage, LLMError


class OpenAICompatibleProvider:
    """``POST {base_url}/chat/completions`` with a JSON body, non-streaming."""

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 20.0,
        transport: Any = None,
    ) -> None:
        if not base_url or not model:
            raise ValueError("base_url and model are required")
        import httpx  # lazy: only needed when an LLM is switched on

        self._httpx = httpx
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = float(timeout_seconds)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # ``transport`` lets tests plug in httpx.MockTransport (no network).
        self._client = httpx.Client(
            timeout=self.timeout_seconds, headers=headers, transport=transport
        )

    @property
    def name(self) -> str:
        return f"openai-compatible/{self.model}"

    @classmethod
    def from_settings(
        cls,
        *,
        reasoner: str,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 20.0,
    ) -> OpenAICompatibleProvider | None:
        """Build a provider only when ``reasoner == "llm"`` and the endpoint is configured."""
        if reasoner.strip().lower() != "llm" or not base_url or not model:
            return None
        return cls(base_url, model, api_key=api_key, timeout_seconds=timeout_seconds)

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        try:
            response = self._client.post(f"{self.base_url}/chat/completions", json=payload)
        except self._httpx.TimeoutException as exc:
            raise LLMError(f"timeout after {self.timeout_seconds:g} s") from exc
        except self._httpx.HTTPError as exc:
            raise LLMError(f"transport error: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise LLMError(f"HTTP {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("malformed response (no choices[0].message.content)") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("empty response")
        return content.strip()

    def close(self) -> None:
        self._client.close()
