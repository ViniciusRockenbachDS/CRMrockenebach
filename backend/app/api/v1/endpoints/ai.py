import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models import AIInsightType
from app.schemas.ai import (
    AIInsightRead,
    AIStatus,
    BatchLeadScoreRequest,
    BatchLeadScoreResponse,
    ClientSummaryRequest,
    ClientSummaryResponse,
    InsightsRequest,
    InsightsResponse,
    LeadScoreRequest,
    LeadScoreResponse,
)
from app.schemas.common import Page
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["Inteligência Artificial"])


@router.get("/status", response_model=AIStatus, summary="Provedor e recursos de IA ativos")
async def ai_status(_: CurrentUser) -> AIStatus:
    return AIService.status()


@router.post(
    "/clients/{client_id}/summary",
    response_model=ClientSummaryResponse,
    summary="Resumo automático do histórico do cliente",
)
async def summarize_client(
    client_id: uuid.UUID, db: DbSession, user: CurrentUser, data: ClientSummaryRequest | None = None
) -> ClientSummaryResponse:
    return await AIService(db).summarize_client(client_id, data or ClientSummaryRequest(), user)


@router.post(
    "/deals/{deal_id}/score",
    response_model=LeadScoreResponse,
    summary="Lead scoring: probabilidade prevista de fechamento",
)
async def score_deal(
    deal_id: uuid.UUID, db: DbSession, user: CurrentUser, data: LeadScoreRequest | None = None
) -> LeadScoreResponse:
    return await AIService(db).score_deal(deal_id, data or LeadScoreRequest(), user)


@router.post("/deals/score-batch", response_model=BatchLeadScoreResponse, summary="Pontua várias negociações")
async def score_batch(
    db: DbSession, user: CurrentUser, data: BatchLeadScoreRequest | None = None
) -> BatchLeadScoreResponse:
    return await AIService(db).score_batch(data or BatchLeadScoreRequest(), user)


@router.post("/insights", response_model=InsightsResponse, summary="Insights sobre funil, receita e inadimplência")
async def insights(db: DbSession, user: CurrentUser, data: InsightsRequest | None = None) -> InsightsResponse:
    return await AIService(db).generate_insights(data or InsightsRequest(), user)


@router.get("/history", response_model=Page[AIInsightRead], summary="Histórico de saídas da IA")
async def history(
    db: DbSession,
    _: CurrentUser,
    page: Pagination,
    insight_type: AIInsightType | None = None,
    entity_id: uuid.UUID | None = None,
) -> Page[AIInsightRead]:
    return await AIService(db).history(page, insight_type, entity_id)
