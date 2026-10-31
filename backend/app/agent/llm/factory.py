import logging

from app.agent.llm.base import LLMClient, LLMError, LLMResponse
from app.agent.llm.gemini import GeminiClient
from app.agent.llm.groq import GroqClient
from app.config import settings

logger = logging.getLogger(__name__)


class FallbackLLM(LLMClient):
    def __init__(self, clients: list[LLMClient]) -> None:
        self.clients = clients
        self.index = 0

    @property
    def name(self) -> str:
        return self.clients[min(self.index, len(self.clients) - 1)].name

    async def generate(self, system: str, history: list[dict], tools: list[dict]) -> LLMResponse:
        last: LLMError | None = None
        while self.index < len(self.clients):
            client = self.clients[self.index]
            try:
                return await client.generate(system, history, tools)
            except LLMError as exc:
                last = exc
                logger.warning("LLM provider %s failed: %s", client.name, exc)
                self.index += 1
        raise last or LLMError("No AI provider is available.")


def build_llm() -> FallbackLLM:
    clients: list[LLMClient] = []
    if settings.gemini_api_key and settings.gemini_model:
        clients.append(
            GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds)
        )
    if settings.groq_api_key and settings.groq_model:
        clients.append(
            GroqClient(settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds)
        )
    if not clients:
        raise LLMError(
            "No AI provider is configured. Set GEMINI_API_KEY and GEMINI_MODEL in backend/.env."
        )
    return FallbackLLM(clients)