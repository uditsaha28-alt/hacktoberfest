import json
import logging

import httpx

from app.agent.llm.base import LLMClient, LLMError, LLMResponse, ToolCall, clean_schema

logger = logging.getLogger(__name__)

URL = "https://api.groq.com/openai/v1/chat/completions"


def to_messages(system: str, history: list[dict]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in history:
        role = msg["role"]
        if role == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            calls = msg.get("tool_calls") or []
            entry: dict = {"role": "assistant", "content": msg.get("content") or None}
            if calls:
                entry["tool_calls"] = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": json.dumps(c["args"])},
                    }
                    for c in calls
                ]
            elif entry["content"] is None:
                entry["content"] = "(no output)"
            messages.append(entry)
        elif role == "tool":
            for item in msg["results"]:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": item["id"],
                        "content": json.dumps(item["result"]),
                    }
                )
    return messages


def parse_response(data: dict) -> LLMResponse:
    choices = data.get("choices") or []
    if not choices:
        raise LLMError("Groq returned no answer.")
    message = choices[0].get("message") or {}
    calls = []
    for raw in message.get("tool_calls") or []:
        function = raw.get("function") or {}
        try:
            args = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append(
            ToolCall(
                name=function.get("name", ""),
                args=args if isinstance(args, dict) else {},
                provider_id=raw.get("id"),
            )
        )
    return LLMResponse(text=message.get("content") or "", tool_calls=calls)


class GroqClient(LLMClient):
    name = "groq"

    def __init__(self, api_key: str, model: str, timeout: int = 60) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def generate(self, system: str, history: list[dict], tools: list[dict]) -> LLMResponse:
        body: dict = {
            "model": self.model,
            "messages": to_messages(system, history),
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": clean_schema(t["parameters"]),
                    },
                }
                for t in tools
            ]
            body["tool_choice"] = "auto"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(URL, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise LLMError("Could not reach Groq.") from exc

        if res.status_code == 200:
            return parse_response(res.json())

        logger.warning("Groq HTTP %s: %s", res.status_code, res.text[:500])
        if res.status_code in (401, 403):
            raise LLMError("Groq rejected the API key.")
        if res.status_code in (413, 429):
            raise LLMError("Groq rate limit or request size limit reached.")
        raise LLMError(f"Groq request failed (HTTP {res.status_code}).")