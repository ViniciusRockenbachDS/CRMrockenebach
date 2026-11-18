"""Orquestra a camada de IA: monta o contexto, usa cache, chama o provedor,
valida a resposta e registra tudo em ai_insights."""

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import features, heuristics
from app.ai.prompts import PROMPT_VERSIONS, AITask, build_prompts
from app.ai.providers import AIProvider, AIResult, get_provider
from app.core.config import settings
from app.core.exceptions import AIProviderError, BusinessRuleError
from app.models import AIInsight, AIInsightType, Deal, DealStage, User
from app.schemas.ai import (
    AIInsightRead,
    AIMeta,
    AIStatus,
    BatchLeadScoreRequest,
    BatchLeadScoreResponse,
    ClientSummaryRequest,
    ClientSummaryResponse,
    Confidence,
    Insight,
    InsightsRequest,
    InsightsResponse,
    LeadScoreFactor,
    LeadScoreRequest,
    LeadScoreResponse,
)
from app.schemas.common import Page, PaginationParams
from app.services import client_service, deal_service
from app.services.common import paginate
from app.utils.dates import month_start, now_utc, today_local


# Formatos esperados do provedor (validação tolerante da resposta do LLM).
class _SummaryOut(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    sentiment: str = "indefinido"
    risks: list[str] = Field(default_factory=list)
    next_best_actions: list[str] = Field(default_factory=list)


class _ScoreOut(BaseModel):
    score: float = Field(ge=0, le=100)
    confidence: Confidence = "media"
    factors: list[LeadScoreFactor] = Field(default_factory=list)
    recommendation: str | None = None


class _InsightsOut(BaseModel):
    headline: str
    insights: list[Insight] = Field(default_factory=list)


class AIService:
    def __init__(self, db: AsyncSession, provider: AIProvider | None = None) -> None:
        self.db = db
        self.provider = provider or get_provider()

    # ----------------------------------------------------------------------- infraestrutura
    @staticmethod
    def status() -> AIStatus:
        provider = get_provider()
        return AIStatus(
            enabled=settings.AI_ENABLED,
            provider=provider.name,
            model=provider.model,
            features=[AIInsightType.CLIENT_SUMMARY, AIInsightType.LEAD_SCORE, AIInsightType.FUNNEL_INSIGHT],
        )

    @staticmethod
    def _ensure_enabled() -> None:
        if not settings.AI_ENABLED:
            raise AIProviderError("A IA está desativada (AI_ENABLED=false).", code="ai_disabled")

    def _hash(self, task: AITask, context: dict[str, Any]) -> str:
        raw = json.dumps(
            {"task": task, "version": PROMPT_VERSIONS[task], "model": self.provider.model, "context": context},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _cached(
        self, insight_type: AIInsightType, entity_id: uuid.UUID | None, input_hash: str
    ) -> AIInsight | None:
        stmt = select(AIInsight).where(
            AIInsight.insight_type == insight_type,
            AIInsight.input_hash == input_hash,
            AIInsight.provider == self.provider.name,
            (AIInsight.expires_at.is_(None)) | (AIInsight.expires_at > now_utc()),
        )
        stmt = stmt.where(AIInsight.entity_id == entity_id) if entity_id else stmt.where(AIInsight.entity_id.is_(None))
        return await self.db.scalar(stmt.order_by(AIInsight.created_at.desc()).limit(1))

    async def _run(self, task: AITask, context: dict[str, Any]) -> AIResult:
        system_prompt, user_prompt = build_prompts(task, context)
        try:
            return await self.provider.generate_json(
                task=task, system_prompt=system_prompt, user_prompt=user_prompt, context=context
            )
        except AIProviderError:
            raise
        except Exception as exc:  # erro inesperado do provedor não derruba a API
            raise AIProviderError(f"Falha ao consultar a IA: {exc.__class__.__name__}.") from exc

    async def _save(
        self,
        *,
        insight_type: AIInsightType,
        task: AITask,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        input_hash: str,
        result: AIResult,
        content: str | None,
        score: float | None,
        payload: dict[str, Any],
        user: User,
    ) -> AIInsight:
        ttl = settings.AI_CACHE_TTL_HOURS
        insight = AIInsight(
            insight_type=insight_type,
            entity_type=entity_type,
            entity_id=entity_id,
            provider=result.provider,
            model=result.model,
            prompt_version=PROMPT_VERSIONS[task],
            input_hash=input_hash,
            content=content,
            score=Decimal(str(round(score, 2))) if score is not None else None,
            payload=json.loads(json.dumps(payload, default=str)),
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            latency_ms=result.latency_ms,
            requested_by_id=user.id,
            created_at=now_utc(),
            expires_at=now_utc() + timedelta(hours=ttl) if ttl else None,
        )
        self.db.add(insight)
        await self.db.flush()
        return insight

    @staticmethod
    def _meta(insight: AIInsight, cached: bool) -> AIMeta:
        return AIMeta(
            insight_id=insight.id,
            provider=insight.provider,
            model=insight.model,
            prompt_version=insight.prompt_version,
            cached=cached,
            generated_at=insight.created_at,
        )

    # ----------------------------------------------------------------------- resumo do cliente
    async def summarize_client(
        self, client_id: uuid.UUID, req: ClientSummaryRequest, user: User
    ) -> ClientSummaryResponse:
        self._ensure_enabled()
        client = await client_service.get_client(self.db, client_id)
        context = await features.build_client_context(
            self.db, client,
            max_interactions=req.max_interactions,
            include_deals=req.include_deals,
            include_payments=req.include_payments,
        )
        input_hash = self._hash("client_summary", context)

        cached = None if req.force_refresh else await self._cached(AIInsightType.CLIENT_SUMMARY, client_id, input_hash)
        if cached:
            return ClientSummaryResponse(client_id=client_id, **cached.payload, meta=self._meta(cached, True))

        result = await self._run("client_summary", context)
        try:
            out = _SummaryOut.model_validate(result.data)
        except ValidationError as exc:
            raise AIProviderError("A IA respondeu em um formato inesperado.", code="ai_invalid_response") from exc
        if out.sentiment not in ("positivo", "neutro", "negativo", "indefinido"):
            out.sentiment = "indefinido"

        payload = {**out.model_dump(), "interactions_analyzed": len(context["interactions"])}
        insight = await self._save(
            insight_type=AIInsightType.CLIENT_SUMMARY, task="client_summary", entity_type="client",
            entity_id=client_id, input_hash=input_hash, result=result, content=out.summary, score=None,
            payload=payload, user=user,
        )
        await self.db.commit()
        return ClientSummaryResponse(client_id=client_id, **payload, meta=self._meta(insight, False))

    # ----------------------------------------------------------------------- lead scoring
    async def score_deal(self, deal_id: uuid.UUID, req: LeadScoreRequest, user: User) -> LeadScoreResponse:
        self._ensure_enabled()
        deal = await deal_service.get_deal(self.db, deal_id)
        if deal.stage.is_closed:
            raise BusinessRuleError("O lead scoring só se aplica a negociações abertas.", code="deal_closed")

        feats = await features.build_deal_features(self.db, deal)
        context = {"features": feats, "heuristic_baseline": heuristics.lead_score(feats)}
        input_hash = self._hash("lead_score", context)

        cached = None if req.force_refresh else await self._cached(AIInsightType.LEAD_SCORE, deal_id, input_hash)
        if cached:
            out = _ScoreOut.model_validate(cached.payload)
            insight, is_cached = cached, True
        else:
            result = await self._run("lead_score", context)
            try:
                out = _ScoreOut.model_validate(result.data)
            except ValidationError as exc:
                raise AIProviderError("A IA respondeu em um formato inesperado.", code="ai_invalid_response") from exc
            insight = await self._save(
                insight_type=AIInsightType.LEAD_SCORE, task="lead_score", entity_type="deal", entity_id=deal_id,
                input_hash=input_hash, result=result, content=out.recommendation, score=out.score,
                payload=out.model_dump(mode="json"), user=user,
            )
            is_cached = False

        if req.apply_to_deal:
            deal.ai_score = Decimal(str(round(out.score, 2)))
            deal.ai_scored_at = now_utc()
        await self.db.commit()
        return LeadScoreResponse(
            deal_id=deal_id,
            score=out.score,
            current_probability=deal.probability,
            confidence=out.confidence,
            factors=out.factors,
            recommendation=out.recommendation,
            meta=self._meta(insight, is_cached),
        )

    async def score_batch(self, req: BatchLeadScoreRequest, user: User) -> BatchLeadScoreResponse:
        self._ensure_enabled()
        ids = req.deal_ids
        if not ids:
            ids = list(
                (
                    await self.db.scalars(
                        select(Deal.id)
                        .where(Deal.deleted_at.is_(None), Deal.stage.in_(DealStage.open_stages()))
                        .limit(200)
                    )
                ).all()
            )
        results: list[LeadScoreResponse] = []
        skipped = 0
        for deal_id in ids:
            try:
                results.append(await self.score_deal(deal_id, LeadScoreRequest(force_refresh=req.force_refresh), user))
            except (BusinessRuleError, AIProviderError):
                # Ambos ocorrem antes de qualquer escrita na sessão: basta pular o deal.
                skipped += 1
        return BatchLeadScoreResponse(scored=len(results), skipped=skipped, results=results)

    # ----------------------------------------------------------------------- insights
    async def generate_insights(self, req: InsightsRequest, user: User) -> InsightsResponse:
        self._ensure_enabled()
        today = today_local()
        start, end = req.date_from or month_start(today), req.date_to or today
        context = await features.build_insights_context(self.db, start, end, req.owner_id, list(req.focus))
        input_hash = self._hash("insights", context)

        cached = None if req.force_refresh else await self._cached(AIInsightType.FUNNEL_INSIGHT, None, input_hash)
        if cached:
            out = _InsightsOut.model_validate(cached.payload)
            insight, is_cached = cached, True
        else:
            result = await self._run("insights", context)
            try:
                out = _InsightsOut.model_validate(result.data)
            except ValidationError as exc:
                raise AIProviderError("A IA respondeu em um formato inesperado.", code="ai_invalid_response") from exc
            out.insights = [i for i in out.insights if i.category in req.focus]
            insight = await self._save(
                insight_type=AIInsightType.FUNNEL_INSIGHT, task="insights", entity_type=None, entity_id=None,
                input_hash=input_hash, result=result, content=out.headline, score=None,
                payload=out.model_dump(mode="json"), user=user,
            )
            await self.db.commit()
            is_cached = False

        return InsightsResponse(
            period_start=start, period_end=end, headline=out.headline, insights=out.insights,
            meta=self._meta(insight, is_cached),
        )

    # ----------------------------------------------------------------------- histórico
    async def history(
        self,
        page: PaginationParams,
        insight_type: AIInsightType | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Page[AIInsightRead]:
        stmt = select(AIInsight).order_by(AIInsight.created_at.desc())
        if insight_type:
            stmt = stmt.where(AIInsight.insight_type == insight_type)
        if entity_id:
            stmt = stmt.where(AIInsight.entity_id == entity_id)
        return await paginate(self.db, stmt, page, AIInsightRead)
