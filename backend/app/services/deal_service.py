"""Regras de negócio do funil de vendas (negociações e Kanban)."""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import (
    AuditAction,
    Client,
    ClientStatus,
    Deal,
    DealStage,
    DealStageHistory,
    Payment,
    PaymentStatus,
    User,
)
from app.schemas.common import Page, PaginationParams
from app.schemas.deal import (
    DealCreate,
    DealFilters,
    DealMove,
    DealRead,
    DealStageHistoryRead,
    DealUpdate,
    KanbanBoard,
    KanbanColumn,
)
from app.services import audit_service
from app.services.common import apply_updates, paginate
from app.utils.dates import now_utc

_LOAD_OPTIONS = (selectinload(Deal.client), selectinload(Deal.owner))


def _active_deals() -> Select[tuple[Deal]]:
    return select(Deal).where(Deal.deleted_at.is_(None))


# --------------------------------------------------------------------------- leitura
async def get_deal(db: AsyncSession, deal_id: uuid.UUID) -> Deal:
    deal = await db.scalar(
        _active_deals()
        .where(Deal.id == deal_id)
        .options(*_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if deal is None:
        raise NotFoundError("Negociação não encontrada.")
    return deal


def _apply_filters(stmt: Select[tuple[Deal]], f: DealFilters) -> Select[tuple[Deal]]:
    if f.search:
        term = f"%{f.search}%"
        stmt = stmt.join(Client, Client.id == Deal.client_id).where(
            or_(Deal.title.ilike(term), Client.name.ilike(term), Client.company.ilike(term))
        )
    if f.stage:
        stmt = stmt.where(Deal.stage.in_(f.stage))
    if f.only_open:
        stmt = stmt.where(Deal.stage.in_(DealStage.open_stages()))
    if f.client_id:
        stmt = stmt.where(Deal.client_id == f.client_id)
    if f.owner_id:
        stmt = stmt.where(Deal.owner_id == f.owner_id)
    if f.min_value is not None:
        stmt = stmt.where(Deal.estimated_value >= f.min_value)
    if f.max_value is not None:
        stmt = stmt.where(Deal.estimated_value <= f.max_value)
    if f.expected_close_from:
        stmt = stmt.where(Deal.expected_close_date >= f.expected_close_from)
    if f.expected_close_to:
        stmt = stmt.where(Deal.expected_close_date <= f.expected_close_to)
    return stmt


_ORDER_COLUMNS = {
    "created_at": Deal.created_at,
    "estimated_value": Deal.estimated_value,
    "expected_close_date": Deal.expected_close_date,
    "probability": Deal.probability,
    "ai_score": Deal.ai_score,
}


async def list_deals(db: AsyncSession, filters: DealFilters, page: PaginationParams) -> Page[DealRead]:
    stmt = _apply_filters(_active_deals(), filters).options(*_LOAD_OPTIONS)
    column = _ORDER_COLUMNS[filters.order_by]
    order = column.asc() if filters.order_dir == "asc" else column.desc()
    stmt = stmt.order_by(order.nulls_last(), Deal.id)
    return await paginate(db, stmt, page, DealRead)


async def get_board(
    db: AsyncSession,
    owner_id: uuid.UUID | None = None,
    search: str | None = None,
    closed_days: int = 30,
) -> KanbanBoard:
    """Monta o Kanban. Colunas fechadas mostram só os últimos `closed_days` dias."""
    filters = DealFilters(owner_id=owner_id, search=search)
    stmt = _apply_filters(_active_deals(), filters).options(*_LOAD_OPTIONS)
    since = now_utc() - timedelta(days=closed_days)
    stmt = stmt.where(or_(Deal.stage.in_(DealStage.open_stages()), Deal.closed_at >= since))
    stmt = stmt.order_by(Deal.position, Deal.created_at)
    deals = (await db.scalars(stmt)).all()

    by_stage: dict[DealStage, list[DealRead]] = {stage: [] for stage in DealStage}
    for deal in deals:
        by_stage[deal.stage].append(DealRead.model_validate(deal))

    columns: list[KanbanColumn] = []
    total_open = Decimal("0")
    total_weighted = Decimal("0")
    for stage, items in by_stage.items():
        total = sum((d.estimated_value for d in items), Decimal("0"))
        weighted = sum((Decimal(str(d.weighted_value)) for d in items), Decimal("0"))
        if not stage.is_closed:
            total_open += total
            total_weighted += weighted
        columns.append(
            KanbanColumn(
                stage=stage, label=stage.label, count=len(items),
                total_value=total, weighted_value=weighted, deals=items,
            )
        )
    return KanbanBoard(columns=columns, total_open_value=total_open, total_weighted_value=total_weighted)


async def get_history(db: AsyncSession, deal_id: uuid.UUID) -> list[DealStageHistoryRead]:
    await get_deal(db, deal_id)
    rows = (
        await db.scalars(
            select(DealStageHistory)
            .where(DealStageHistory.deal_id == deal_id)
            .options(selectinload(DealStageHistory.changed_by))
            .order_by(DealStageHistory.changed_at)
        )
    ).all()
    return [DealStageHistoryRead.model_validate(r) for r in rows]


# --------------------------------------------------------------------------- escrita
async def _get_active_client(db: AsyncSession, client_id: uuid.UUID) -> Client:
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise BusinessRuleError("Cliente não encontrado.", code="client_not_found")
    return client


async def _next_position(db: AsyncSession, stage: DealStage) -> int:
    current = await db.scalar(
        select(func.max(Deal.position)).where(Deal.stage == stage, Deal.deleted_at.is_(None))
    )
    return (current if current is not None else -1) + 1


def _mark_client_as_customer(client: Client) -> None:
    if client.status in (ClientStatus.LEAD, ClientStatus.PROSPECT, ClientStatus.INATIVO):
        client.status = ClientStatus.CLIENTE


async def create_deal(db: AsyncSession, data: DealCreate, actor: User, context: dict[str, Any]) -> Deal:
    client = await _get_active_client(db, data.client_id)
    if data.owner_id and await db.get(User, data.owner_id) is None:
        raise BusinessRuleError("Responsável não encontrado.", code="owner_not_found")

    now = now_utc()
    deal = Deal(
        client_id=client.id,
        owner_id=data.owner_id or actor.id,
        title=data.title,
        description=data.description,
        estimated_value=data.estimated_value,
        probability=data.probability if data.probability is not None else data.stage.default_probability,
        stage=data.stage,
        expected_close_date=data.expected_close_date,
        lost_reason=data.lost_reason if data.stage == DealStage.FECHADO_PERDIDO else None,
        closed_at=now if data.stage.is_closed else None,
        stage_changed_at=now,
        position=await _next_position(db, data.stage),
    )
    db.add(deal)
    await db.flush()
    db.add(
        DealStageHistory(
            deal_id=deal.id, from_stage=None, to_stage=deal.stage, changed_by_id=actor.id, changed_at=now,
            estimated_value_snapshot=deal.estimated_value, probability_snapshot=deal.probability,
            note="Negociação criada",
        )
    )
    if deal.stage == DealStage.FECHADO_GANHO:
        _mark_client_as_customer(client)
    elif client.status == ClientStatus.LEAD:
        client.status = ClientStatus.PROSPECT  # abriu negociação → deixa de ser lead frio
    await audit_service.log(
        db, entity_type="deal", entity_id=deal.id, action=AuditAction.CREATE, user_id=actor.id,
        changes=audit_service.snapshot(deal, ["title", "client_id", "estimated_value", "stage", "probability"]),
        context=context,
    )
    await db.commit()
    return await get_deal(db, deal.id)


async def update_deal(
    db: AsyncSession, deal_id: uuid.UUID, data: DealUpdate, actor: User, context: dict[str, Any]
) -> Deal:
    deal = await get_deal(db, deal_id)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("client_id") and payload["client_id"] != deal.client_id:
        await _get_active_client(db, payload["client_id"])
    if payload.get("owner_id") and await db.get(User, payload["owner_id"]) is None:
        raise BusinessRuleError("Responsável não encontrado.", code="owner_not_found")
    if deal.stage.is_closed and "probability" in payload:
        raise BusinessRuleError("Não é possível alterar a probabilidade de uma negociação fechada.")
    changes = apply_updates(
        deal, payload, non_nullable=("title", "estimated_value", "probability", "client_id")
    )
    if changes:
        await audit_service.log(
            db, entity_type="deal", entity_id=deal.id, action=AuditAction.UPDATE, user_id=actor.id,
            changes=changes, context=context,
        )
        await db.commit()
    return await get_deal(db, deal_id)


async def _reorder_column(db: AsyncSession, deal: Deal, position: int | None) -> None:
    """Reposiciona o card na coluna de destino e normaliza as posições (0..n)."""
    siblings = list(
        (
            await db.scalars(
                _active_deals()
                .where(Deal.stage == deal.stage, Deal.id != deal.id)
                .order_by(Deal.position, Deal.created_at)
            )
        ).all()
    )
    index = len(siblings) if position is None else min(position, len(siblings))
    siblings.insert(index, deal)
    for i, item in enumerate(siblings):
        if item.position != i:
            item.position = i


async def move_deal(
    db: AsyncSession, deal_id: uuid.UUID, data: DealMove, actor: User, context: dict[str, Any]
) -> Deal:
    deal = await get_deal(db, deal_id)
    old_stage = deal.stage
    new_stage = data.stage
    now = now_utc()

    if new_stage != old_stage:
        if old_stage == DealStage.FECHADO_GANHO:
            active_payments = await db.scalar(
                select(func.count()).where(
                    Payment.deal_id == deal.id, Payment.status != PaymentStatus.CANCELADO
                )
            )
            if active_payments:
                raise BusinessRuleError(
                    "Esta negociação já possui faturas. Cancele-as antes de reabrir.",
                    code="deal_has_payments",
                )
        seconds_in_stage = int((now - deal.stage_changed_at).total_seconds())
        old_probability = deal.probability

        deal.stage = new_stage
        deal.stage_changed_at = now
        deal.probability = data.probability if data.probability is not None else new_stage.default_probability
        deal.closed_at = now if new_stage.is_closed else None
        deal.lost_reason = data.lost_reason if new_stage == DealStage.FECHADO_PERDIDO else None

        db.add(
            DealStageHistory(
                deal_id=deal.id, from_stage=old_stage, to_stage=new_stage, changed_by_id=actor.id,
                changed_at=now, estimated_value_snapshot=deal.estimated_value,
                probability_snapshot=deal.probability, seconds_in_previous_stage=seconds_in_stage,
                note=data.note,
            )
        )
        if new_stage == DealStage.FECHADO_GANHO:
            _mark_client_as_customer(deal.client)
        await audit_service.log(
            db, entity_type="deal", entity_id=deal.id, action=AuditAction.STAGE_CHANGE, user_id=actor.id,
            changes={
                "stage": {"old": old_stage, "new": new_stage},
                "probability": {"old": old_probability, "new": deal.probability},
                **({"lost_reason": {"old": None, "new": deal.lost_reason}} if deal.lost_reason else {}),
            },
            context=context,
        )
    elif data.probability is not None and not new_stage.is_closed:
        deal.probability = data.probability

    await _reorder_column(db, deal, data.position)
    await db.commit()
    return await get_deal(db, deal_id)


async def delete_deal(db: AsyncSession, deal_id: uuid.UUID, actor: User, context: dict[str, Any]) -> None:
    deal = await get_deal(db, deal_id)
    has_payments = await db.scalar(
        select(func.count()).where(Payment.deal_id == deal.id, Payment.status != PaymentStatus.CANCELADO)
    )
    if has_payments:
        raise BusinessRuleError(
            "Negociações com faturas ativas não podem ser excluídas.", code="deal_has_payments"
        )
    deal.deleted_at = now_utc()
    await audit_service.log(
        db, entity_type="deal", entity_id=deal.id, action=AuditAction.DELETE, user_id=actor.id, context=context
    )
    await db.commit()
