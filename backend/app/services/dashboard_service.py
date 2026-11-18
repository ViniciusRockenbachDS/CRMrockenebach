"""Métricas do Dashboard (também reutilizadas como contexto pela camada de IA)."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Date, and_, cast, distinct, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Client, Deal, DealStage, DealStageHistory, LeadSource, Payment, PaymentStatus
from app.schemas.dashboard import (
    DashboardFilters,
    DashboardResponse,
    FunnelStageMetric,
    KPIComparison,
    KPISummary,
    LeadSourceMetric,
    OverduePaymentItem,
    RevenuePoint,
    TopClient,
)
from app.schemas.summaries import ClientSummary
from app.services.payment_service import refresh_overdue_statuses
from app.utils.dates import add_months, end_of_day_exclusive, month_start, now_utc, start_of_day, today_local

_OPEN = DealStage.open_stages()
_RECEIVABLE = (PaymentStatus.PENDENTE, PaymentStatus.ATRASADO)
_ZERO = Decimal("0")


def _dec(value: object) -> Decimal:
    return Decimal(str(value)) if value is not None else _ZERO


def _pct_change(current: float | Decimal, previous: float | Decimal) -> float | None:
    if not previous:
        return None
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def resolve_period(filters: DashboardFilters) -> tuple[date, date]:
    today = today_local()
    return filters.date_from or month_start(today), filters.date_to or today


async def compute_kpis(db: AsyncSession, start: date, end: date, owner_id: uuid.UUID | None) -> KPISummary:
    today = today_local()
    start_dt, end_dt = start_of_day(start), end_of_day_exclusive(end)
    deal_owner = [Deal.owner_id == owner_id] if owner_id else []

    revenue = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Deal, Deal.id == Payment.deal_id)
        .where(Payment.status == PaymentStatus.PAGO, Payment.payment_date.between(start, end), *deal_owner)
    )

    closed = (
        await db.execute(
            select(
                func.count().filter(Deal.stage == DealStage.FECHADO_GANHO),
                func.count().filter(Deal.stage == DealStage.FECHADO_PERDIDO),
                func.avg(Deal.estimated_value).filter(Deal.stage == DealStage.FECHADO_GANHO),
            ).where(
                Deal.deleted_at.is_(None), Deal.closed_at >= start_dt, Deal.closed_at < end_dt, *deal_owner
            )
        )
    ).one()
    won, lost, avg_ticket = closed[0], closed[1], closed[2]

    pipeline = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Deal.estimated_value), 0),
                func.coalesce(func.sum(Deal.estimated_value * Deal.probability / 100), 0),
            ).where(Deal.deleted_at.is_(None), Deal.stage.in_(_OPEN), *deal_owner)
        )
    ).one()

    receivables = (
        await db.execute(
            select(
                func.coalesce(func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE)), 0),
                func.coalesce(
                    func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE), Payment.due_date < today), 0
                ),
                func.count().filter(Payment.status.in_(_RECEIVABLE), Payment.due_date < today),
                # Base da inadimplência: tudo que já venceu (pago ou não), exceto cancelados.
                func.coalesce(
                    func.sum(Payment.amount).filter(
                        Payment.status != PaymentStatus.CANCELADO, Payment.due_date < today
                    ),
                    0,
                ),
            )
            .join(Deal, Deal.id == Payment.deal_id)
            .where(*deal_owner)
        )
    ).one()
    overdue_amount, matured_total = _dec(receivables[1]), _dec(receivables[3])

    new_clients = await db.scalar(
        select(func.count()).where(
            Client.deleted_at.is_(None),
            Client.created_at >= start_dt,
            Client.created_at < end_dt,
            *([Client.owner_id == owner_id] if owner_id else []),
        )
    )

    return KPISummary(
        total_revenue=_dec(revenue).quantize(Decimal("0.01")),
        average_ticket=_dec(avg_ticket).quantize(Decimal("0.01")),
        conversion_rate=round(won / (won + lost), 4) if (won + lost) else 0.0,
        won_deals_count=won,
        lost_deals_count=lost,
        open_deals_count=pipeline[0],
        open_pipeline_value=_dec(pipeline[1]).quantize(Decimal("0.01")),
        weighted_pipeline_value=_dec(pipeline[2]).quantize(Decimal("0.01")),
        receivables=_dec(receivables[0]).quantize(Decimal("0.01")),
        overdue_amount=overdue_amount.quantize(Decimal("0.01")),
        overdue_count=receivables[2],
        delinquency_rate=round(float(overdue_amount / matured_total), 4) if matured_total else 0.0,
        new_clients_count=new_clients or 0,
    )


async def compute_funnel(
    db: AsyncSession, start: date, end: date, owner_id: uuid.UUID | None
) -> list[FunnelStageMetric]:
    start_dt, end_dt = start_of_day(start), end_of_day_exclusive(end)
    deal_owner = [Deal.owner_id == owner_id] if owner_id else []

    # Contagem e valores: etapas abertas = estado atual; fechadas = fechadas no período.
    rows = (
        await db.execute(
            select(
                Deal.stage,
                func.count(),
                func.coalesce(func.sum(Deal.estimated_value), 0),
                func.coalesce(func.sum(Deal.estimated_value * Deal.probability / 100), 0),
            )
            .where(
                Deal.deleted_at.is_(None),
                *deal_owner,
                (Deal.stage.in_(_OPEN)) | (and_(Deal.closed_at >= start_dt, Deal.closed_at < end_dt)),
            )
            .group_by(Deal.stage)
        )
    ).all()
    stats = {row[0]: row for row in rows}

    # Tempo médio (dias) que os deals passaram em cada etapa antes de sair dela.
    avg_rows = (
        await db.execute(
            select(DealStageHistory.from_stage, func.avg(DealStageHistory.seconds_in_previous_stage))
            .join(Deal, Deal.id == DealStageHistory.deal_id)
            .where(DealStageHistory.from_stage.is_not(None), *deal_owner)
            .group_by(DealStageHistory.from_stage)
        )
    ).all()
    avg_days = {row[0]: round(float(row[1]) / 86400, 1) for row in avg_rows if row[1] is not None}

    # Conversão entre etapas: % dos deals que chegaram à etapa k-1 e também chegaram à etapa k.
    reach_rows = (
        await db.execute(
            select(DealStageHistory.deal_id, DealStageHistory.to_stage)
            .join(Deal, Deal.id == DealStageHistory.deal_id)
            .where(Deal.deleted_at.is_(None), *deal_owner)
        )
    ).all()
    max_order: dict[uuid.UUID, int] = defaultdict(lambda: -1)
    for deal_id, stage in reach_rows:
        if stage != DealStage.FECHADO_PERDIDO:
            max_order[deal_id] = max(max_order[deal_id], stage.order)
    progression = [s for s in DealStage if s != DealStage.FECHADO_PERDIDO]
    reached = {s: sum(1 for o in max_order.values() if o >= s.order) for s in progression}

    result: list[FunnelStageMetric] = []
    for stage in DealStage:
        row = stats.get(stage)
        conversion = None
        if stage in progression and stage.order > 0:
            previous = progression[progression.index(stage) - 1]
            if reached[previous]:
                conversion = round(reached[stage] / reached[previous], 4)
        result.append(
            FunnelStageMetric(
                stage=stage,
                label=stage.label,
                count=row[1] if row else 0,
                total_value=_dec(row[2] if row else 0).quantize(Decimal("0.01")),
                weighted_value=_dec(row[3] if row else 0).quantize(Decimal("0.01")),
                avg_days_in_stage=avg_days.get(stage),
                conversion_from_previous=conversion,
            )
        )
    return result


async def compute_revenue_series(
    db: AsyncSession, end: date, owner_id: uuid.UUID | None, months: int = 6
) -> list[RevenuePoint]:
    today = today_local()
    first_month = add_months(month_start(end), -(months - 1))
    last_exclusive = add_months(month_start(end), 1)
    deal_owner = [Deal.owner_id == owner_id] if owner_id else []

    # literal_column: o mesmo SQL literal no SELECT e no GROUP BY (parâmetros distintos quebrariam o agrupamento).
    _month = literal_column("'month'")
    received_month = cast(func.date_trunc(_month, Payment.payment_date), Date)
    received = dict(
        (
            await db.execute(
                select(received_month, func.sum(Payment.amount))
                .join(Deal, Deal.id == Payment.deal_id)
                .where(
                    Payment.status == PaymentStatus.PAGO,
                    Payment.payment_date >= first_month,
                    Payment.payment_date < last_exclusive,
                    *deal_owner,
                )
                .group_by(received_month)
            )
        ).all()
    )
    due_month = cast(func.date_trunc(_month, Payment.due_date), Date)
    due_rows = (
        await db.execute(
            select(
                due_month,
                func.sum(Payment.amount),
                func.coalesce(
                    func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE), Payment.due_date < today), 0
                ),
            )
            .join(Deal, Deal.id == Payment.deal_id)
            .where(
                Payment.status != PaymentStatus.CANCELADO,
                Payment.due_date >= first_month,
                Payment.due_date < last_exclusive,
                *deal_owner,
            )
            .group_by(due_month)
        )
    ).all()
    expected = {row[0]: row[1] for row in due_rows}
    overdue = {row[0]: row[2] for row in due_rows}

    return [
        RevenuePoint(
            period=month,
            received=_dec(received.get(month)).quantize(Decimal("0.01")),
            expected=_dec(expected.get(month)).quantize(Decimal("0.01")),
            overdue=_dec(overdue.get(month)).quantize(Decimal("0.01")),
        )
        for month in (add_months(first_month, i) for i in range(months))
    ]


async def compute_lead_sources(db: AsyncSession, owner_id: uuid.UUID | None) -> list[LeadSourceMetric]:
    won = Deal.stage == DealStage.FECHADO_GANHO
    rows = (
        await db.execute(
            select(
                Client.lead_source,
                func.count(distinct(Client.id)),
                func.count(distinct(Client.id)).filter(won),
                func.count(distinct(Deal.id)).filter(won),
                func.coalesce(func.sum(Deal.estimated_value).filter(won), 0),
            )
            .outerjoin(Deal, and_(Deal.client_id == Client.id, Deal.deleted_at.is_(None)))
            .where(Client.deleted_at.is_(None), *([Client.owner_id == owner_id] if owner_id else []))
            .group_by(Client.lead_source)
        )
    ).all()
    metrics = [
        LeadSourceMetric(
            lead_source=row[0],
            label=LeadSource(row[0]).label,
            clients_count=row[1],
            won_deals_count=row[3],
            won_value=_dec(row[4]).quantize(Decimal("0.01")),
            conversion_rate=round(row[2] / row[1], 4) if row[1] else 0.0,
        )
        for row in rows
    ]
    return sorted(metrics, key=lambda m: m.won_value, reverse=True)


async def compute_top_clients(db: AsyncSession, owner_id: uuid.UUID | None, limit: int = 5) -> list[TopClient]:
    total = func.sum(Payment.amount).label("total_paid")
    rows = (
        await db.execute(
            select(Client, total, func.count(distinct(Deal.id)))
            .join(Deal, Deal.client_id == Client.id)
            .join(Payment, Payment.deal_id == Deal.id)
            .where(
                Payment.status == PaymentStatus.PAGO,
                Client.deleted_at.is_(None),
                *([Deal.owner_id == owner_id] if owner_id else []),
            )
            .group_by(Client.id)
            .order_by(total.desc())
            .limit(limit)
        )
    ).all()
    return [
        TopClient(client=ClientSummary.model_validate(row[0]), total_paid=_dec(row[1]), deals_won=row[2])
        for row in rows
    ]


async def compute_top_overdue(db: AsyncSession, owner_id: uuid.UUID | None, limit: int = 5) -> list[OverduePaymentItem]:
    today = today_local()
    payments = (
        await db.scalars(
            select(Payment)
            .join(Deal, Deal.id == Payment.deal_id)
            .where(Payment.status.in_(_RECEIVABLE), Payment.due_date < today,
                   *([Deal.owner_id == owner_id] if owner_id else []))
            .options(selectinload(Payment.deal).selectinload(Deal.client))
            .order_by(Payment.due_date)
            .limit(limit)
        )
    ).all()
    return [
        OverduePaymentItem(
            payment_id=p.id,
            invoice_number=p.invoice_number,
            client=ClientSummary.model_validate(p.deal.client),
            amount=p.amount,
            due_date=p.due_date,
            days_overdue=(today - p.due_date).days,
        )
        for p in payments
    ]


async def get_dashboard(db: AsyncSession, filters: DashboardFilters) -> DashboardResponse:
    await refresh_overdue_statuses(db)
    start, end = resolve_period(filters)
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)

    summary = await compute_kpis(db, start, end, filters.owner_id)
    previous = await compute_kpis(db, prev_start, prev_end, filters.owner_id)

    return DashboardResponse(
        period_start=start,
        period_end=end,
        summary=summary,
        comparison=KPIComparison(
            total_revenue_pct=_pct_change(summary.total_revenue, previous.total_revenue),
            conversion_rate_pct=_pct_change(summary.conversion_rate, previous.conversion_rate),
            average_ticket_pct=_pct_change(summary.average_ticket, previous.average_ticket),
            new_clients_pct=_pct_change(summary.new_clients_count, previous.new_clients_count),
        ),
        funnel=await compute_funnel(db, start, end, filters.owner_id),
        revenue_series=await compute_revenue_series(db, end, filters.owner_id),
        lead_sources=await compute_lead_sources(db, filters.owner_id),
        top_clients=await compute_top_clients(db, filters.owner_id),
        top_overdue=await compute_top_overdue(db, filters.owner_id),
        generated_at=now_utc(),
    )
