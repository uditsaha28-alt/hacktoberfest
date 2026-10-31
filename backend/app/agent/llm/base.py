"""Provider-neutral LLM types.

History is a list of neutral messages (the agent loop builds it, each provider converts it):
  {"role": "user", "content": str}
  {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "args", "provider_id"}],
   "gemini_parts": list | None}
  {"role": "tool", "results": [{"id", "name", "provider_id", "result": dict}]}
"""
from dataclasses import dataclass, field
from typing import Any


class LLMError(Exception):
    """A provider call failed. Messages are safe to show to users (no keys, no raw bodies)."""


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    id: str = ""  # assigned by the agent loop
    provider_id: str | None = None  # id given by the provider, if any


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    gemini_parts: list[dict] | None = None  # raw parts, replayed verbatim to Gemini


class LLMClient:
    name = "llm"

    async def generate(self, system: str, history: list[dict], tools: list[dict]) -> LLMResponse:
        raise NotImplementedError


def clean_schema(schema: Any) -> Any:
    """Drop empty `required` lists, which some providers reject."""
    if isinstance(schema, dict):
        return {
            key: clean_schema(value)
            for key, value in schema.items()
            if not (key == "required" and not value)
        }
    if isinstance(schema, list):
        return [clean_schema(item) for item in schema]
    return schema