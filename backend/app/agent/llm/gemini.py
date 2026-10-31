import asyncio
import logging

import httpx

from app.agent.llm.base import LLMClient, LLMError, LLMResponse, ToolCall, clean_schema
from app.config import settings

logger = logging.getLogger(__name__)

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE = {429, 500, 502, 503, 504}


def to_contents(history: list[dict]) -> list[dict]:
    contents: list[dict] = []
    for msg in history:
        role = msg["role"]
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif role == "assistant":
            parts = msg.get("gemini_parts")
            if not parts:
                parts = []
                if msg.get("content"):
                    parts.append({"text": msg["content"]})
                for call in msg.get("tool_calls", []):
                    parts.append({"functionCall": {"name": call["name"], "args": call["args"]}})
            if not parts:
                parts = [{"text": "(no output)"}]
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            parts = []
            for item in msg["results"]:
                response = {"name": item["name"], "response": item["result"]}
                if item.get("provider_id"):
                    response["id"] = item["provider_id"]
                parts.append({"functionResponse": response})
            contents.append({"role": "user", "parts": parts})
    return contents


def parse_response(data: dict) -> LLMResponse:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "empty response")
        raise LLMError(f"Gemini returned no answer ({reason}).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
    calls = [
        ToolCall(
            name=p["functionCall"].get("name", ""),
            args=dict(p["functionCall"].get("args") or {}),
            provider_id=p["functionCall"].get("id"),
        )
        for p in parts
        if p.get("functionCall")
    ]
    return LLMResponse(text=text, tool_calls=calls, gemini_parts=parts or None)


class GeminiClient(LLMClient):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: int = 60) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def generate(self, system: str, history: list[dict], tools: list[dict]) -> LLMResponse:
        body: dict = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": to_contents(history),
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
        }
        level = settings.gemini_thinking_level.strip()
        if level:
            body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": level}
        if tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": t["name"],
                            "description": t["description"],
                            "parameters": clean_schema(t["parameters"]),
                        }
                        for t in tools
                    ]
                }
            ]
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        url = URL.format(model=self.model)

        res = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, headers=headers, json=body)
            except httpx.TimeoutException as exc:
                logger.warning("Gemini timeout: %r", exc)
                if attempt == 0:
                    continue
                raise LLMError("Gemini timed out.") from exc
            except httpx.HTTPError as exc:
                logger.warning("Gemini network error: %r", exc)
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                raise LLMError(f"Could not reach Gemini ({type(exc).__name__}).") from exc

            if res.status_code == 400 and "thinkingConfig" in body["generationConfig"]:
                logger.warning("Gemini rejected thinkingConfig, retrying without it: %s", res.text[:300])
                del body["generationConfig"]["thinkingConfig"]
                continue
            if res.status_code in RETRYABLE and attempt == 0:
                await asyncio.sleep(2)
                continue
            break

        if res.status_code == 200:
            return parse_response(res.json())

        logger.warning("Gemini HTTP %s: %s", res.status_code, res.text[:500])
        if res.status_code in (401, 403):
            raise LLMError("Gemini rejected the API key.")
        if res.status_code == 404:
            raise LLMError("Gemini model not found. Check GEMINI_MODEL in backend/.env.")
        if res.status_code == 429:
            raise LLMError("Gemini rate limit reached.")
        raise LLMError(f"Gemini request failed (HTTP {res.status_code}).")