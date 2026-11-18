"""Regras de negócio de faturas, recebimentos e inadimplência."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import AuditAction, Deal, DealStage, Payment, PaymentStatus, User
from app.schemas.common import Page, PaginationParams
from app.schemas.payment import (
    PaymentCancel,
    PaymentCreate,
    PaymentFilters,
    PaymentInstallmentsCreate,
    PaymentMarkPaid,
    PaymentRead,
    PaymentUpdate,
    ReceivablesSummary,
)
from app.services import audit_service
from app.services.common import apply_updates, paginate
from app.utils.dates import add_months, now_utc, today_local

_RECEIVABLE = (PaymentStatus.PENDENTE, PaymentStatus.ATRASADO)
_LOAD_OPTIONS = (selectinload(Payment.deal).selectinload(Deal.client),)


async def refresh_overdue_statuses(db: AsyncSession) -> int:
    """Marca como ATRASADO todo pagamento pendente com vencimento anterior a hoje.

    Chamado antes de listagens e do dashboard (barato graças ao índice status+due_date).
    Em produção, também pode rodar num agendador (cron) uma vez por dia.
    """
    result = await db.execute(
        update(Payment)
        .where(Payment.status == PaymentStatus.PENDENTE, Payment.due_date < today_local())
        .values(status=PaymentStatus.ATRASADO)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount:  # type: ignore[attr-defined]
        await db.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]


def _status_for_due_date(due_date: date) -> PaymentStatus:
    return PaymentStatus.ATRASADO if due_date < today_local() else PaymentStatus.PENDENTE


async def get_payment(db: AsyncSession, payment_id: uuid.UUID) -> Payment:
    payment = await db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .options(*_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if payment is None:
        raise NotFoundError("Pagamento não encontrado.")
    return payment


def _apply_filters(stmt: Select[tuple[Payment]], f: PaymentFilters) -> Select[tuple[Payment]]:
    if f.status:
        stmt = stmt.where(Payment.status.in_(f.status))
    if f.method:
        stmt = stmt.where(Payment.method.in_(f.method))
    if f.deal_id:
        stmt = stmt.where(Payment.deal_id == f.deal_id)
    if f.client_id:
        stmt = stmt.where(Deal.client_id == f.client_id)
    if f.due_from:
        stmt = stmt.where(Payment.due_date >= f.due_from)
    if f.due_to:
        stmt = stmt.where(Payment.due_date <= f.due_to)
    if f.paid_from:
        stmt = stmt.where(Payment.payment_date >= f.paid_from)
    if f.paid_to:
        stmt = stmt.where(Payment.payment_date <= f.paid_to)
    if f.overdue_only:
        stmt = stmt.where(Payment.status.in_(_RECEIVABLE), Payment.due_date < today_local())
    return stmt


_ORDER_COLUMNS = {
    "due_date": Payment.due_date,
    "amount": Payment.amount,
    "payment_date": Payment.payment_date,
    "created_at": Payment.created_at,
}


async def list_payments(db: AsyncSession, filters: PaymentFilters, page: PaginationParams) -> Page[PaymentRead]:
    await refresh_overdue_statuses(db)
    stmt = select(Payment).join(Deal, Deal.id == Payment.deal_id).options(*_LOAD_OPTIONS)
    stmt = _apply_filters(stmt, filters)
    column = _ORDER_COLUMNS[filters.order_by]
    order = column.asc() if filters.order_dir == "asc" else column.desc()
    stmt = stmt.order_by(order.nulls_last(), Payment.seq)
    return await paginate(db, stmt, page, PaymentRead)


async def get_summary(db: AsyncSession, paid_from: date | None = None, paid_to: date | None = None) -> ReceivablesSummary:
    await refresh_overdue_statuses(db)
    today = today_local()
    paid_from = paid_from or today.replace(day=1)
    paid_to = paid_to or today
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.PENDENTE), 0),
                func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.ATRASADO), 0),
                func.coalesce(
                    func.sum(Payment.amount).filter(
                        Payment.status == PaymentStatus.PAGO,
                        Payment.payment_date.between(paid_from, paid_to),
                    ),
                    0,
                ),
                func.count().filter(Payment.status == PaymentStatus.ATRASADO),
            )
        )
    ).one()
    return ReceivablesSummary(
        total_pending=Decimal(row[0]),
        total_overdue=Decimal(row[1]),
        total_paid_period=Decimal(row[2]),
        count_overdue=row[3],
        generated_at=now_utc(),
    )


async def _get_won_deal(db: AsyncSession, deal_id: uuid.UUID) -> Deal:
    deal = await db.get(Deal, deal_id)
    if deal is None or deal.deleted_at is not None:
        raise BusinessRuleError("Negociação não encontrada.", code="deal_not_found")
    if deal.stage != DealStage.FECHADO_GANHO:
        raise BusinessRuleError(
            "Pagamentos só podem ser lançados em negociações em 'Fechado Ganho'.", code="deal_not_won"
        )
    return deal


async def create_payment(db: AsyncSession, data: PaymentCreate, actor: User, context: dict[str, Any]) -> Payment:
    await _get_won_deal(db, data.deal_id)
    payload = data.model_dump()
    if data.status == PaymentStatus.PENDENTE:
        payload["status"] = _status_for_due_date(data.due_date)
    payment = Payment(**payload)
    db.add(payment)
    await db.flush()
    await audit_service.log(
        db, entity_type="payment", entity_id=payment.id, action=AuditAction.CREATE, user_id=actor.id,
        changes=audit_service.snapshot(payment, ["deal_id", "amount", "method", "status", "due_date"]),
        context=context,
    )
    await db.commit()
    return await get_payment(db, payment.id)


async def create_installments(
    db: AsyncSession, data: PaymentInstallmentsCreate, actor: User, context: dict[str, Any]
) -> list[Payment]:
    await _get_won_deal(db, data.deal_id)
    created: list[Payment] = []
    for index, amount in enumerate(data.split_amounts()):
        due = add_months(data.first_due_date, index)
        payment = Payment(
            deal_id=data.deal_id,
            description=data.description or f"Parcela {index + 1}/{data.installments}",
            amount=amount,
            method=data.method,
            due_date=due,
            status=_status_for_due_date(due),
            installment_number=index + 1,
            installment_total=data.installments,
        )
        db.add(payment)
        created.append(payment)
    await db.flush()
    for payment in created:
        await audit_service.log(
            db, entity_type="payment", entity_id=payment.id, action=AuditAction.CREATE, user_id=actor.id,
            changes=audit_service.snapshot(payment, ["deal_id", "amount", "due_date", "installment_number"]),
            context=context,
        )
    await db.commit()
    return [await get_payment(db, p.id) for p in created]


def _ensure_open(payment: Payment) -> None:
    if payment.status not in _RECEIVABLE:
        raise BusinessRuleError(
            f"Pagamento com status '{payment.status.label}' não pode ser alterado.", code="payment_closed"
        )


async def update_payment(
    db: AsyncSession, payment_id: uuid.UUID, data: PaymentUpdate, actor: User, context: dict[str, Any]
) -> Payment:
    payment = await get_payment(db, payment_id)
    _ensure_open(payment)
    changes = apply_updates(payment, data.model_dump(exclude_unset=True), non_nullable=("amount", "method", "due_date"))
    if "due_date" in changes:
        payment.status = _status_for_due_date(payment.due_date)
    if changes:
        await audit_service.log(
            db, entity_type="payment", entity_id=payment.id, action=AuditAction.UPDATE, user_id=actor.id,
            changes=changes, context=context,
        )
        await db.commit()
    return await get_payment(db, payment_id)


async def mark_paid(
    db: AsyncSession, payment_id: uuid.UUID, data: PaymentMarkPaid, actor: User, context: dict[str, Any]
) -> Payment:
    payment = await get_payment(db, payment_id)
    _ensure_open(payment)
    old_status = payment.status
    payment.status = PaymentStatus.PAGO
    payment.payment_date = data.payment_date
    if data.method:
        payment.method = data.method
    if data.notes:
        payment.notes = f"{payment.notes}\n{data.notes}".strip() if payment.notes else data.notes
    await audit_service.log(
        db, entity_type="payment", entity_id=payment.id, action=AuditAction.STATUS_CHANGE, user_id=actor.id,
        changes={"status": {"old": old_status, "new": PaymentStatus.PAGO},
                 "payment_date": {"old": None, "new": data.payment_date}},
        context=context,
    )
    await db.commit()
    return await get_payment(db, payment_id)


async def cancel_payment(
    db: AsyncSession, payment_id: uuid.UUID, data: PaymentCancel, actor: User, context: dict[str, Any]
) -> Payment:
    payment = await get_payment(db, payment_id)
    _ensure_open(payment)
    old_status = payment.status
    payment.status = PaymentStatus.CANCELADO
    note = f"Cancelado: {data.reason}"
    payment.notes = f"{payment.notes}\n{note}" if payment.notes else note
    await audit_service.log(
        db, entity_type="payment", entity_id=payment.id, action=AuditAction.STATUS_CHANGE, user_id=actor.id,
        changes={"status": {"old": old_status, "new": PaymentStatus.CANCELADO}, "reason": {"old": None, "new": data.reason}},
        context=context,
    )
    await db.commit()
    return await get_payment(db, payment_id)
