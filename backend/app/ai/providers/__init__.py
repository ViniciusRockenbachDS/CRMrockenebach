from functools import lru_cache

from app.ai.providers.base import AIProvider, AIResult
from app.ai.providers.http_providers import AnthropicProvider, OpenAIProvider
from app.ai.providers.stub import StubProvider
from app.core.config import settings


@lru_cache
def get_provider() -> AIProvider:
    """Escolhe o provedor conforme AI_PROVIDER no .env."""
    if settings.AI_PROVIDER == "stub":
        return StubProvider()
    api_key = settings.AI_API_KEY.get_secret_value() if settings.AI_API_KEY else ""
    if settings.AI_PROVIDER == "openai":
        return OpenAIProvider(api_key, settings.AI_MODEL, settings.AI_TIMEOUT_SECONDS)
    return AnthropicProvider(api_key, settings.AI_MODEL, settings.AI_TIMEOUT_SECONDS)


__all__ = ["AIProvider", "AIResult", "get_provider"]
