"""Contrato comum a todos os provedores de IA."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.ai.prompts import AITask
from app.core.exceptions import AIProviderError


@dataclass
class AIResult:
    data: dict[str, Any]
    provider: str
    model: str
    tokens_input: int | None = None
    tokens_output: int | None = None
    latency_ms: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate_json(
        self, *, task: AITask, system_prompt: str, user_prompt: str, context: dict[str, Any]
    ) -> AIResult:
        """Executa a tarefa e devolve um dicionário no formato pedido pelo prompt."""


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_response(text: str) -> dict[str, Any]:
    """Extrai o objeto JSON da resposta do LLM (tolera blocos ```json e texto ao redor)."""
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise AIProviderError("A IA não retornou JSON.", code="ai_invalid_response")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIProviderError("A IA retornou JSON inválido.", code="ai_invalid_response") from exc
    if not isinstance(data, dict):
        raise AIProviderError("A IA retornou um formato inesperado.", code="ai_invalid_response")
    return data
