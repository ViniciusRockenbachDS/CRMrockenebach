"""Provedor offline: usa as heurísticas determinísticas de app.ai.heuristics."""

import time
from typing import Any

from app.ai import heuristics
from app.ai.prompts import AITask
from app.ai.providers.base import AIProvider, AIResult


class StubProvider(AIProvider):
    name = "stub"
    model = "heuristic-v1"

    async def generate_json(
        self, *, task: AITask, system_prompt: str, user_prompt: str, context: dict[str, Any]
    ) -> AIResult:
        started = time.perf_counter()
        if task == "client_summary":
            data = heuristics.client_summary(context)
        elif task == "lead_score":
            data = context.get("heuristic_baseline") or heuristics.lead_score(context["features"])
        else:
            data = heuristics.commercial_insights(context)
        return AIResult(
            data=data,
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
