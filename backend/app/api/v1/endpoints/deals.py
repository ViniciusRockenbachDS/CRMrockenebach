import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, ManagerUser, Pagination, RequestContext
from app.models import Deal
from app.schemas.common import Page
from app.schemas.deal import (
    DealCreate,
    DealFilters,
    DealMove,
    DealRead,
    DealStageHistoryRead,
    DealUpdate,
    KanbanBoard,
)
from app.services import deal_service

router = APIRouter(prefix="/deals", tags=["Negociações"])


@router.get("", response_model=Page[DealRead], summary="Lista negociações com filtros")
async def list_deals(
    db: DbSession, _: CurrentUser, page: Pagination, filters: Annotated[DealFilters, Query()]
) -> Page[DealRead]:
    return await deal_service.list_deals(db, filters, page)


@router.get("/board", response_model=KanbanBoard, summary="Funil em formato Kanban")
async def get_board(
    db: DbSession,
    _: CurrentUser,
    owner_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=100),
    closed_days: int = Query(default=30, ge=1, le=365, description="Dias exibidos nas colunas fechadas"),
) -> KanbanBoard:
    return await deal_service.get_board(db, owner_id, search, closed_days)


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(data: DealCreate, db: DbSession, user: CurrentUser, context: RequestContext) -> Deal:
    return await deal_service.create_deal(db, data, user, context)


@router.get("/{deal_id}", response_model=DealRead)
async def get_deal(deal_id: uuid.UUID, db: DbSession, _: CurrentUser) -> Deal:
    return await deal_service.get_deal(db, deal_id)


@router.patch("/{deal_id}", response_model=DealRead)
async def update_deal(
    deal_id: uuid.UUID, data: DealUpdate, db: DbSession, user: CurrentUser, context: RequestContext
) -> Deal:
    return await deal_service.update_deal(db, deal_id, data, user, context)


@router.post("/{deal_id}/move", response_model=DealRead, summary="Muda etapa e/ou posição no Kanban")
async def move_deal(
    deal_id: uuid.UUID, data: DealMove, db: DbSession, user: CurrentUser, context: RequestContext
) -> Deal:
    return await deal_service.move_deal(db, deal_id, data, user, context)


@router.get("/{deal_id}/history", response_model=list[DealStageHistoryRead], summary="Histórico de etapas")
async def get_history(deal_id: uuid.UUID, db: DbSession, _: CurrentUser) -> list[DealStageHistoryRead]:
    return await deal_service.get_history(db, deal_id)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclusão lógica (gestor/admin)")
async def delete_deal(deal_id: uuid.UUID, db: DbSession, user: ManagerUser, context: RequestContext) -> Response:
    await deal_service.delete_deal(db, deal_id, user, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
