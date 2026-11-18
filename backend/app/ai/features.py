"""Extração de features/contexto do banco para a camada de IA.

Mantém a lógica de "quais dados a IA enxerga" num só lugar — o mesmo dicionário serve
ao provedor heurístico, aos LLMs e, no futuro, a um modelo de ML treinado.
"""

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Client,
    Deal,
    DealStage,
    DealStageHistory,
    Interaction,
    Payment,
    PaymentStatus,
)
from app.services import dashboard_service
from app.utils.dates import days_between, now_utc, today_local

_RECEIVABLE = (PaymentStatus.PENDENTE, PaymentStatus.ATRASADO)
STALLED_THRESHOLD_DAYS = 30


async def _client_interaction_stats(db: AsyncSession, client_id: uuid.UUID) -> dict[str, Any]:
    since = now_utc() - timedelta(days=30)
    row = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(Interaction.occurred_at >= since),
                func.max(Interaction.occurred_at),
                func.avg(Interaction.sentiment),
            ).where(Interaction.client_id == client_id)
        )
    ).one()
    last = row[2]
    return {
        "interactions_total": row[0],
        "interactions_last_30d": row[1],
        "days_since_last_interaction": int(days_between(last, now_utc())) if last else None,
        "avg_sentiment": round(float(row[3]), 2) if row[3] is not None else None,
    }


async def build_deal_features(db: AsyncSession, deal: Deal) -> dict[str, Any]:
    """Features de uma negociação. `deal.client` precisa estar carregado."""
    now = now_utc()
    today = today_local()

    history = (
        await db.execute(
            select(DealStageHistory.from_stage, DealStageHistory.to_stage).where(DealStageHistory.deal_id == deal.id)
        )
    ).all()
    regressions = sum(
        1
        for from_stage, to_stage in history
        if from_stage is not None and to_stage != DealStage.FECHADO_PERDIDO and to_stage.order < from_stage.order
    )

    previous_wins = await db.scalar(
        select(func.count()).where(
            Deal.client_id == deal.client_id,
            Deal.id != deal.id,
            Deal.stage == DealStage.FECHADO_GANHO,
            Deal.deleted_at.is_(None),
        )
    )

    owner_win_rate: float | None = None
    owner_closed = 0
    if deal.owner_id:
        won, lost = (
            await db.execute(
                select(
                    func.count().filter(Deal.stage == DealStage.FECHADO_GANHO),
                    func.count().filter(Deal.stage == DealStage.FECHADO_PERDIDO),
                ).where(
                    Deal.owner_id == deal.owner_id,
                    Deal.deleted_at.is_(None),
                    Deal.closed_at >= now - timedelta(days=365),
                )
            )
        ).one()
        owner_closed = won + lost
        owner_win_rate = round(won / owner_closed, 3) if owner_closed else None

    return {
        "deal_id": str(deal.id),
        "title": deal.title,
        "stage": deal.stage.value,
        "stage_label": deal.stage.label,
        "stage_default_probability": deal.stage.default_probability,
        "probability": deal.probability,
        "estimated_value": float(deal.estimated_value),
        "days_in_stage": int(days_between(deal.stage_changed_at, now)),
        "days_since_created": int(days_between(deal.created_at, now)),
        "days_to_expected_close": (deal.expected_close_date - today).days if deal.expected_close_date else None,
        "history_events": len(history),
        "stage_regressions": regressions,
        "client_status": deal.client.status.value,
        "lead_source": deal.client.lead_source.value,
        "client_previous_won_deals": previous_wins or 0,
        "owner_win_rate": owner_win_rate,
        "owner_closed_deals": owner_closed,
        **await _client_interaction_stats(db, deal.client_id),
    }


async def build_client_context(
    db: AsyncSession,
    client: Client,
    *,
    max_interactions: int,
    include_deals: bool,
    include_payments: bool,
) -> dict[str, Any]:
    now = now_utc()
    interactions = (
        await db.scalars(
            select(Interaction)
            .where(Interaction.client_id == client.id)
            .order_by(Interaction.occurred_at.desc())
            .limit(max_interactions)
        )
    ).all()
    stats = await _client_interaction_stats(db, client.id)

    context: dict[str, Any] = {
        "today": today_local().isoformat(),
        "client": {
            "name": client.name,
            "company": client.company,
            "job_title": client.job_title,
            "status": client.status.value,
            "status_label": client.status.label,
            "lead_source": client.lead_source.value,
            "lead_source_label": client.lead_source.label,
            "created_at": client.created_at.date().isoformat(),
            "tags": client.tags,
            "notes": (client.notes or "")[:1000],
        },
        "interactions": [
            {
                "type": i.type.value,
                "type_label": i.type.label,
                "direction": i.direction.value,
                "occurred_at": i.occurred_at.isoformat(),
                "subject": i.subject,
                "content": i.content[:1000],
                "sentiment": float(i.sentiment) if i.sentiment is not None else None,
            }
            for i in interactions
        ],
        "interactions_total": stats["interactions_total"],
        "days_since_last_interaction": stats["days_since_last_interaction"],
    }

    if include_deals:
        deals = (
            await db.scalars(
                select(Deal).where(Deal.client_id == client.id, Deal.deleted_at.is_(None)).order_by(Deal.created_at.desc())
            )
        ).all()
        context["deals"] = [
            {
                "title": d.title,
                "stage": d.stage.value,
                "stage_label": d.stage.label,
                "estimated_value": float(d.estimated_value),
                "probability": d.probability,
                "expected_close_date": d.expected_close_date.isoformat() if d.expected_close_date else None,
                "days_in_stage": int(days_between(d.stage_changed_at, now)),
                "lost_reason": d.lost_reason,
            }
            for d in deals
        ]

    if include_payments:
        today = today_local()
        row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(Payment.amount).filter(Payment.status == PaymentStatus.PAGO), 0),
                    func.coalesce(func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE)), 0),
                    func.coalesce(
                        func.sum(Payment.amount).filter(Payment.status.in_(_RECEIVABLE), Payment.due_date < today), 0
                    ),
                    func.count().filter(Payment.status.in_(_RECEIVABLE), Payment.due_date < today),
                )
                .join(Deal, Deal.id == Payment.deal_id)
                .where(Deal.client_id == client.id)
            )
        ).one()
        context["payments"] = {
            "paid": float(row[0]),
            "outstanding": float(row[1]),
            "overdue": float(row[2]),
            "overdue_count": row[3],
        }
    return context


async def build_insights_context(
    db: AsyncSession, start: date, end: date, owner_id: uuid.UUID | None, focus: list[str]
) -> dict[str, Any]:
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    today = today_local()
    owner_filter = [Deal.owner_id == owner_id] if owner_id else []

    kpis = await dashboard_service.compute_kpis(db, start, end, owner_id)
    previous = await dashboard_service.compute_kpis(db, prev_start, prev_end, owner_id)
    funnel = await dashboard_service.compute_funnel(db, start, end, owner_id)
    sources = await dashboard_service.compute_lead_sources(db, owner_id)
    overdue = await dashboard_service.compute_top_overdue(db, owner_id)

    open_deals = select(Deal.id).where(
        Deal.deleted_at.is_(None), Deal.stage.in_(DealStage.open_stages()), *owner_filter
    )
    stalled_ids = (
        await db.scalars(
            open_deals.where(Deal.stage_changed_at < now_utc() - timedelta(days=STALLED_THRESHOLD_DAYS)).limit(20)
        )
    ).all()
    late_ids = (await db.scalars(open_deals.where(Deal.expected_close_date < today).limit(20))).all()

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "focus": focus,
        "kpis": kpis.model_dump(mode="json"),
        "previous_kpis": previous.model_dump(mode="json"),
        "funnel": [f.model_dump(mode="json") for f in funnel],
        "lead_sources": [s.model_dump(mode="json") for s in sources],
        "top_overdue": [o.model_dump(mode="json") for o in overdue],
        "stalled_deals": {
            "count": len(stalled_ids),
            "ids": [str(i) for i in stalled_ids],
            "threshold_days": STALLED_THRESHOLD_DAYS,
        },
        "overdue_close_deals": {"count": len(late_ids), "ids": [str(i) for i in late_ids]},
    }
