"""Optional language-model support: provider interface, OpenAI-compatible client, redaction.

Nothing in here is used unless an LLM is switched on. The redaction helpers are
also used by the always-on guardrails and tool summaries.
"""

from carboncreditbuy_agents.llm.base import ChatMessage, LLMError, LLMProvider
from carboncreditbuy_agents.llm.openai_compatible import OpenAICompatibleProvider
from carboncreditbuy_agents.llm.redaction import (
    MASK,
    SENSITIVE_KEYS,
    find_coordinates,
    looks_like_position,
    redact,
    redact_text,
    sensitive_number_strings,
)

__all__ = [
    "MASK",
    "SENSITIVE_KEYS",
    "ChatMessage",
    "LLMError",
    "LLMProvider",
    "OpenAICompatibleProvider",
    "find_coordinates",
    "looks_like_position",
    "redact",
    "redact_text",
    "sensitive_number_strings",
]
