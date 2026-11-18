"""Provedores reais (OpenAI e Anthropic) via HTTP, com retry e backoff exponencial.

Ative com AI_PROVIDER=openai|anthropic, AI_API_KEY e AI_MODEL no .env.
"""

import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.prompts import AITask
from app.ai.providers.base import AIProvider, AIResult, parse_json_response
from app.core.exceptions import AIProviderError


class _RetryableError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(_RetryableError),
    reraise=True,
)
async def _post(client: httpx.AsyncClient, url: str, headers: dict[str, str], payload: dict[str, Any]) -> httpx.Response:
    try:
        response = await client.post(url, headers=headers, json=payload)
    except httpx.TransportError as exc:
        raise _RetryableError(str(exc)) from exc
    if response.status_code == 429 or response.status_code >= 500:
        raise _RetryableError(f"HTTP {response.status_code}")
    if response.status_code >= 400:
        raise AIProviderError(
            f"O provedor de IA recusou a requisição (HTTP {response.status_code}).",
            code="ai_request_rejected",
            extra={"response": response.text[:300]},
        )
    return response


class _HTTPProvider(AIProvider):
    url: str

    def __init__(self, api_key: str, model: str, timeout: int) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise NotImplementedError

    def _extract(self, body: dict[str, Any]) -> tuple[str, int | None, int | None]:
        raise NotImplementedError

    async def generate_json(
        self, *, task: AITask, system_prompt: str, user_prompt: str, context: dict[str, Any]
    ) -> AIResult:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await _post(client, self.url, self._headers(), self._payload(system_prompt, user_prompt))
        except _RetryableError as exc:
            raise AIProviderError(f"Provedor de IA indisponível após 3 tentativas ({exc}).") from exc
        text, tokens_in, tokens_out = self._extract(response.json())
        return AIResult(
            data=parse_json_response(text),
            provider=self.name,
            model=self.model,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


class OpenAIProvider(_HTTPProvider):
    name = "openai"
    url = "https://api.openai.com/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

    def _extract(self, body: dict[str, Any]) -> tuple[str, int | None, int | None]:
        usage = body.get("usage") or {}
        return (
            body["choices"][0]["message"]["content"],
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )


class AnthropicProvider(_HTTPProvider):
    name = "anthropic"
    url = "https://api.anthropic.com/v1/messages"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    def _payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

    def _extract(self, body: dict[str, Any]) -> tuple[str, int | None, int | None]:
        usage = body.get("usage") or {}
        text = "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")
        return text, usage.get("input_tokens"), usage.get("output_tokens")
