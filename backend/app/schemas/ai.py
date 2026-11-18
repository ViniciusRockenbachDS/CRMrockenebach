"""Contratos da camada de IA (endpoints /api/v1/ai/...).

Os schemas são independentes do provedor: o stub, a OpenAI ou a Anthropic
devem devolver exatamente estas estruturas.
"""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AIInsightType
from app.schemas.common import InputModel, ORMModel

Confidence = Literal["baixa", "media", "alta"]
Severity = Literal["info", "atencao", "critico"]


class AIMeta(BaseModel):
    """Metadados comuns a toda resposta de IA (rastreabilidade)."""

    insight_id: UUID | None = None
    provider: str
    model: str
    prompt_version: str
    cached: bool = False
    generated_at: datetime


class AIStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    features: list[AIInsightType]


# --- Resumo automático do cliente --------------------------------------------------
class ClientSummaryRequest(InputModel):
    max_interactions: int = Field(default=50, ge=1, le=200)
    include_deals: bool = True
    include_payments: bool = True
    force_refresh: bool = Field(default=False, description="Ignora o cache e gera novamente")


class ClientSummaryResponse(BaseModel):
    client_id: UUID
    summary: str
    key_points: list[str] = Field(default_factory=list)
    sentiment: Literal["positivo", "neutro", "negativo", "indefinido"] = "indefinido"
    risks: list[str] = Field(default_factory=list)
    next_best_actions: list[str] = Field(default_factory=list)
    interactions_analyzed: int
    meta: AIMeta


# --- Lead scoring (previsão de fechamento) ------------------------------------------
class LeadScoreFactor(BaseModel):
    feature: str = Field(examples=["dias_sem_contato"])
    description: str
    value: Any = None
    impact: float = Field(ge=-1, le=1, description="Negativo reduz, positivo aumenta a chance")


class LeadScoreRequest(InputModel):
    force_refresh: bool = False
    apply_to_deal: bool = Field(
        default=True, description="Grava o score em deals.ai_score / ai_scored_at"
    )


class LeadScoreResponse(BaseModel):
    deal_id: UUID
    score: float = Field(ge=0, le=100, description="Probabilidade prevista de ganho (%)")
    current_probability: int = Field(ge=0, le=100, description="Probabilidade manual do vendedor")
    confidence: Confidence
    factors: list[LeadScoreFactor] = Field(default_factory=list)
    recommendation: str | None = None
    meta: AIMeta


class BatchLeadScoreRequest(InputModel):
    deal_ids: list[UUID] | None = Field(
        default=None, max_length=200, description="Se omitido, pontua todos os deals abertos"
    )
    force_refresh: bool = False


class BatchLeadScoreResponse(BaseModel):
    scored: int
    skipped: int
    results: list[LeadScoreResponse]


# --- Insights comerciais (funil e inadimplência) ------------------------------------
class InsightsRequest(InputModel):
    date_from: date | None = None
    date_to: date | None = None
    focus: list[Literal["funil", "inadimplencia", "receita", "origem_leads"]] = Field(
        default_factory=lambda: ["funil", "inadimplencia"]
    )
    owner_id: UUID | None = None
    force_refresh: bool = False

    @model_validator(mode="after")
    def _check(self) -> "InsightsRequest":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from deve ser anterior ou igual a date_to.")
        if not self.focus:
            raise ValueError("Informe ao menos um foco de análise.")
        return self


class Insight(BaseModel):
    category: Literal["funil", "inadimplencia", "receita", "origem_leads"]
    title: str
    description: str
    severity: Severity = "info"
    metric: str | None = Field(default=None, examples=["conversion_rate"])
    value: float | None = None
    recommendation: str | None = None
    related_entity_ids: list[UUID] = Field(default_factory=list)


class InsightsResponse(BaseModel):
    period_start: date
    period_end: date
    headline: str
    insights: list[Insight]
    meta: AIMeta


# --- Histórico de insights gerados --------------------------------------------------
class AIInsightRead(ORMModel):
    id: UUID
    insight_type: AIInsightType
    entity_type: str | None = None
    entity_id: UUID | None = None
    provider: str
    model: str
    prompt_version: str
    content: str | None = None
    score: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    tokens_input: int | None = None
    tokens_output: int | None = None
    latency_ms: int | None = None
    created_at: datetime
    expires_at: datetime | None = None
