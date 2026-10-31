import logging

from app.agent.llm.base import LLMClient, LLMError, LLMResponse
from app.agent.llm.gemini import GeminiClient
from app.agent.llm.groq import GroqClient
from app.config import settings

logger = logging.getLogger(__name__)


class FallbackLLM(LLMClient):
    def __init__(self, clients: list[LLMClient], standalone: list[LLMClient] | None = None) -> None:
        self.clients = clients
        self.standalone = standalone or clients
        self.index = 0

    @property
    def name(self) -> str:
        return self.clients[min(self.index, len(self.clients) - 1)].name

    async def generate(self, system: str, history: list[dict], tools: list[dict]) -> LLMResponse:
        """Conversation calls: once a provider fails we stay on the next one for the rest of the run."""
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

    async def generate_standalone(
        self, system: str, history: list[dict], tools: list[dict]
    ) -> LLMResponse:
        """Self-contained one-shot calls: walk the full chain (extra Gemini models, then Groq)."""
        last: LLMError | None = None
        for client in self.standalone:
            try:
                return await client.generate(system, history, tools)
            except LLMError as exc:
                last = exc
                logger.warning(
                    "LLM provider %s (%s) failed (standalone): %s",
                    client.name, getattr(client, "model", "?"), exc,
                )
        raise last or LLMError("No AI provider is available.")


def build_llm() -> FallbackLLM:
    clients: list[LLMClient] = []
    standalone: list[LLMClient] = []

    if settings.gemini_api_key and settings.gemini_model:
        main = GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds)
        clients.append(main)
        standalone.append(main)
        for model in (m.strip() for m in settings.gemini_fallback_models.split(",")):
            if model and model != settings.gemini_model:
                standalone.append(
                    GeminiClient(settings.gemini_api_key, model, settings.llm_timeout_seconds)
                )

    if settings.groq_api_key and settings.groq_model:
        groq = GroqClient(settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds)
        clients.append(groq)
        standalone.append(groq)

    if not clients:
        raise LLMError(
            "No AI provider is configured. Set GEMINI_API_KEY and GEMINI_MODEL in backend/.env."
        )
    return FallbackLLM(clients, standalone)