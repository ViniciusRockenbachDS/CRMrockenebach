"""Regras de negócio de clientes (leads/contatos) e do histórico de interações."""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import (
    AuditAction,
    Client,
    Deal,
    DealStage,
    Interaction,
    Payment,
    PaymentStatus,
    User,
)
from app.schemas.client import (
    ClientCreate,
    ClientDetail,
    ClientFilters,
    ClientListItem,
    ClientRead,
    ClientStats,
    ClientUpdate,
)
from app.schemas.common import Page, PaginationParams
from app.schemas.interaction import InteractionCreate, InteractionFilters, InteractionRead, InteractionUpdate
from app.schemas.summaries import DealSummary
from app.services import audit_service
from app.services.common import apply_updates, paginate
from app.utils.dates import end_of_day_exclusive, now_utc, start_of_day, today_local
from app.utils.validators import only_digits

_NON_NULLABLE = ("name", "lead_source", "status", "tags", "custom_fields")
_OPEN_STAGES = DealStage.open_stages()
_RECEIVABLE = (PaymentStatus.PENDENTE, PaymentStatus.ATRASADO)


# --------------------------------------------------------------------------- consultas
def _active_clients() -> Select[tuple[Client]]:
    return select(Client).where(Client.deleted_at.is_(None))


def _apply_filters(stmt: Select[tuple[Client]], f: ClientFilters) -> Select[tuple[Client]]:
    if f.search:
        term = f"%{f.search}%"
        conditions = [Client.name.ilike(term), Client.company.ilike(term), Client.email.ilike(term)]
        digits = only_digits(f.search)
        if len(digits) >= 4:
            conditions += [
                Client.phone.contains(digits),
                Client.whatsapp.contains(digits),
                Client.document.contains(digits),
            ]
        stmt = stmt.where(or_(*conditions))
    if f.status:
        stmt = stmt.where(Client.status.in_(f.status))
    if f.lead_source:
        stmt = stmt.where(Client.lead_source.in_(f.lead_source))
    if f.owner_id:
        stmt = stmt.where(Client.owner_id == f.owner_id)
    if f.tag:
        stmt = stmt.where(Client.tags.contains([f.tag.strip().lower()]))
    if f.created_from:
        stmt = stmt.where(Client.created_at >= start_of_day(f.created_from))
    if f.created_to:
        stmt = stmt.where(Client.created_at < end_of_day_exclusive(f.created_to))
    if f.no_contact_days:
        limit_date = now_utc() - timedelta(days=f.no_contact_days)
        stmt = stmt.where(
            or_(Client.last_interaction_at.is_(None), Client.last_interaction_at < limit_date)
        )
    return stmt


_ORDER_COLUMNS = {
    "name": Client.name,
    "created_at": Client.created_at,
    "last_interaction_at": Client.last_interaction_at,
    "status": Client.status,
}


async def list_clients(db: AsyncSession, filters: ClientFilters, page: PaginationParams) -> Page[ClientListItem]:
    stmt = _apply_filters(_active_clients(), filters).options(selectinload(Client.owner))
    column = _ORDER_COLUMNS[filters.order_by]
    order = column.asc() if filters.order_dir == "asc" else column.desc()
    stmt = stmt.order_by(order.nulls_last(), Client.id)
    return await paginate(db, stmt, page, ClientListItem)


async def get_client(db: AsyncSession, client_id: uuid.UUID) -> Client:
    client = await db.scalar(
        _active_clients()
        .where(Client.id == client_id)
        .options(selectinload(Client.owner))
        .execution_options(populate_existing=True)
    )
    if client is None:
        raise NotFoundError("Cliente não encontrado.")
    return client


async def _client_stats(db: AsyncSession, client_id: uuid.UUID) -> ClientStats:
    deal_row = (
        await db.execute(
            select(
                func.count().filter(Deal.stage.in_(_OPEN_STAGES)),
                func.count().filter(Deal.stage == DealStage.FECHADO_GANHO),
                func.count().filter(Deal.stage == DealStage.FECHADO_PERDIDO),
                func.coalesce(func.sum(Deal.estimated_value).filter(Deal.stage.in_(_OPEN_STAGES)), 0),
                func.coalesce(func.sum(Deal.estimated_value).filter(Deal.stage == DealStage.FECHADO_GANHO), 0),
            ).where(Deal.client_id == client_id, Deal.deleted_at.is_(None))
        )
    ).one()
    today = today_local()
    pay_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.PAGO), 0),
                func.coalesce(func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE)), 0),
                func.coalesce(
                    func.sum(Payment.amount).filter(
                        and_(Payment.status.in_(_RECEIVABLE), Payment.due_date < today)
                    ),
                    0,
                ),
            )
            .join(Deal, Deal.id == Payment.deal_id)
            .where(Deal.client_id == client_id)
        )
    ).one()
    return ClientStats(
        open_deals=deal_row[0],
        won_deals=deal_row[1],
        lost_deals=deal_row[2],
        pipeline_value=Decimal(deal_row[3]),
        total_won_value=Decimal(deal_row[4]),
        total_paid=Decimal(pay_row[0]),
        outstanding_amount=Decimal(pay_row[1]),
        overdue_amount=Decimal(pay_row[2]),
    )


async def get_client_detail(db: AsyncSession, client_id: uuid.UUID) -> ClientDetail:
    client = await get_client(db, client_id)
    interactions = (
        await db.scalars(
            select(Interaction)
            .where(Interaction.client_id == client_id)
            .options(selectinload(Interaction.user))
            .order_by(Interaction.occurred_at.desc())
            .limit(10)
        )
    ).all()
    deals = (
        await db.scalars(
            select(Deal)
            .where(Deal.client_id == client_id, Deal.deleted_at.is_(None))
            .order_by(Deal.created_at.desc())
        )
    ).all()
    base = ClientRead.model_validate(client).model_dump()
    return ClientDetail(
        **base,
        stats=await _client_stats(db, client_id),
        recent_interactions=[InteractionRead.model_validate(i) for i in interactions],
        deals=[DealSummary.model_validate(d) for d in deals],
    )


async def _ensure_user_exists(db: AsyncSession, user_id: uuid.UUID | None) -> None:
    if user_id is not None and await db.get(User, user_id) is None:
        raise BusinessRuleError("Responsável (owner_id) não encontrado.", code="owner_not_found")


# --------------------------------------------------------------------------- escrita
async def create_client(
    db: AsyncSession, data: ClientCreate, actor: User, context: dict[str, Any]
) -> Client:
    await _ensure_user_exists(db, data.owner_id)
    payload = data.model_dump(exclude={"owner_id"})
    client = Client(**payload, owner_id=data.owner_id or actor.id)
    db.add(client)
    await db.flush()
    await audit_service.log(
        db, entity_type="client", entity_id=client.id, action=AuditAction.CREATE, user_id=actor.id,
        changes=audit_service.snapshot(client, ["name", "company", "email", "status", "lead_source"]),
        context=context,
    )
    await db.commit()
    return await get_client(db, client.id)


async def update_client(
    db: AsyncSession, client_id: uuid.UUID, data: ClientUpdate, actor: User, context: dict[str, Any]
) -> Client:
    client = await get_client(db, client_id)
    payload = data.model_dump(exclude_unset=True)
    if "owner_id" in payload:
        await _ensure_user_exists(db, payload["owner_id"])
    changes = apply_updates(client, payload, non_nullable=_NON_NULLABLE)
    if changes:
        action = AuditAction.STATUS_CHANGE if set(changes) == {"status"} else AuditAction.UPDATE
        await audit_service.log(
            db, entity_type="client", entity_id=client.id, action=action, user_id=actor.id,
            changes=changes, context=context,
        )
        await db.commit()
    return await get_client(db, client_id)


async def delete_client(db: AsyncSession, client_id: uuid.UUID, actor: User, context: dict[str, Any]) -> None:
    """Exclusão lógica — o histórico continua disponível para relatórios e IA."""
    client = await get_client(db, client_id)
    open_deals = await db.scalar(
        select(func.count()).where(
            Deal.client_id == client_id, Deal.deleted_at.is_(None), Deal.stage.in_(_OPEN_STAGES)
        )
    )
    if open_deals:
        raise BusinessRuleError(
            f"O cliente possui {open_deals} negociação(ões) em aberto. Feche-as antes de excluir.",
            code="client_has_open_deals",
        )
    client.deleted_at = now_utc()
    await audit_service.log(
        db, entity_type="client", entity_id=client.id, action=AuditAction.DELETE,
        user_id=actor.id, context=context,
    )
    await db.commit()


# --------------------------------------------------------------------------- interações
async def _get_interaction(db: AsyncSession, client_id: uuid.UUID, interaction_id: uuid.UUID) -> Interaction:
    interaction = await db.scalar(
        select(Interaction)
        .where(Interaction.id == interaction_id, Interaction.client_id == client_id)
        .options(selectinload(Interaction.user))
        .execution_options(populate_existing=True)
    )
    if interaction is None:
        raise NotFoundError("Interação não encontrada.")
    return interaction


async def _validate_deal_of_client(db: AsyncSession, client_id: uuid.UUID, deal_id: uuid.UUID | None) -> None:
    if deal_id is None:
        return
    deal = await db.get(Deal, deal_id)
    if deal is None or deal.client_id != client_id or deal.deleted_at is not None:
        raise BusinessRuleError("A negociação informada não pertence a este cliente.", code="deal_mismatch")


async def _refresh_last_interaction(db: AsyncSession, client: Client) -> None:
    client.last_interaction_at = await db.scalar(
        select(func.max(Interaction.occurred_at)).where(Interaction.client_id == client.id)
    )


async def list_interactions(
    db: AsyncSession, client_id: uuid.UUID, filters: InteractionFilters, page: PaginationParams
) -> Page[InteractionRead]:
    await get_client(db, client_id)
    stmt = (
        select(Interaction)
        .where(Interaction.client_id == client_id)
        .options(selectinload(Interaction.user))
        .order_by(Interaction.occurred_at.desc())
    )
    if filters.type:
        stmt = stmt.where(Interaction.type.in_(filters.type))
    if filters.deal_id:
        stmt = stmt.where(Interaction.deal_id == filters.deal_id)
    if filters.occurred_from:
        stmt = stmt.where(Interaction.occurred_at >= filters.occurred_from)
    if filters.occurred_to:
        stmt = stmt.where(Interaction.occurred_at <= filters.occurred_to)
    return await paginate(db, stmt, page, InteractionRead)


async def create_interaction(
    db: AsyncSession, client_id: uuid.UUID, data: InteractionCreate, actor: User, context: dict[str, Any]
) -> Interaction:
    client = await get_client(db, client_id)
    await _validate_deal_of_client(db, client_id, data.deal_id)
    payload = data.model_dump()
    payload["occurred_at"] = payload["occurred_at"] or now_utc()
    interaction = Interaction(**payload, client_id=client_id, user_id=actor.id)
    db.add(interaction)
    await db.flush()
    if client.last_interaction_at is None or interaction.occurred_at > client.last_interaction_at:
        client.last_interaction_at = interaction.occurred_at
    await audit_service.log(
        db, entity_type="interaction", entity_id=interaction.id, action=AuditAction.CREATE,
        user_id=actor.id, changes={"client_id": {"old": None, "new": client_id}}, context=context,
    )
    await db.commit()
    return await _get_interaction(db, client_id, interaction.id)


async def update_interaction(
    db: AsyncSession,
    client_id: uuid.UUID,
    interaction_id: uuid.UUID,
    data: InteractionUpdate,
    actor: User,
    context: dict[str, Any],
) -> Interaction:
    client = await get_client(db, client_id)
    interaction = await _get_interaction(db, client_id, interaction_id)
    payload = data.model_dump(exclude_unset=True)
    if "deal_id" in payload:
        await _validate_deal_of_client(db, client_id, payload["deal_id"])
    changes = apply_updates(
        interaction, payload, non_nullable=("type", "direction", "content", "occurred_at")
    )
    if changes:
        await db.flush()
        await _refresh_last_interaction(db, client)
        await audit_service.log(
            db, entity_type="interaction", entity_id=interaction.id, action=AuditAction.UPDATE,
            user_id=actor.id, changes=changes, context=context,
        )
        await db.commit()
    return await _get_interaction(db, client_id, interaction_id)


async def delete_interaction(
    db: AsyncSession, client_id: uuid.UUID, interaction_id: uuid.UUID, actor: User, context: dict[str, Any]
) -> None:
    client = await get_client(db, client_id)
    interaction = await _get_interaction(db, client_id, interaction_id)
    await db.delete(interaction)
    await db.flush()
    await _refresh_last_interaction(db, client)
    await audit_service.log(
        db, entity_type="interaction", entity_id=interaction_id, action=AuditAction.DELETE,
        user_id=actor.id, changes={"content": {"old": interaction.content[:500], "new": None}}, context=context,
    )
    await db.commit()
