"""The smallest possible interface to a chat language model.

The framework needs exactly one thing from an LLM: "here are a few chat
messages, give me back text". Anything that can do that — a hosted API, a local
Ollama server, or a fake in a unit test — is an :class:`LLMProvider`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


class LLMError(Exception):
    """The provider could not produce an answer (network, timeout, bad response)."""


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@runtime_checkable
class LLMProvider(Protocol):
    """Anything that turns chat messages into a reply.

    Implementations must raise :class:`LLMError` (or any exception) on failure;
    callers treat every exception as "no answer" and fall back to templates.
    """

    @property
    def name(self) -> str:
        """A short label for transcripts, e.g. ``"openai-compatible/llama3.1"``."""
        ...

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str: ...
