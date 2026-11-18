import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, ManagerUser, Pagination, RequestContext
from app.models import Payment
from app.schemas.common import Page
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
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Pagamentos"])


@router.get("", response_model=Page[PaymentRead], summary="Lista faturas com filtros")
async def list_payments(
    db: DbSession, _: CurrentUser, page: Pagination, filters: Annotated[PaymentFilters, Query()]
) -> Page[PaymentRead]:
    return await payment_service.list_payments(db, filters, page)


@router.get("/summary", response_model=ReceivablesSummary, summary="Totais de contas a receber")
async def get_summary(
    db: DbSession, _: CurrentUser, paid_from: date | None = None, paid_to: date | None = None
) -> ReceivablesSummary:
    return await payment_service.get_summary(db, paid_from, paid_to)


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(data: PaymentCreate, db: DbSession, user: CurrentUser, context: RequestContext) -> Payment:
    return await payment_service.create_payment(db, data, user, context)


@router.post(
    "/installments",
    response_model=list[PaymentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Gera parcelas mensais",
)
async def create_installments(
    data: PaymentInstallmentsCreate, db: DbSession, user: CurrentUser, context: RequestContext
) -> list[Payment]:
    return await payment_service.create_installments(db, data, user, context)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: uuid.UUID, db: DbSession, _: CurrentUser) -> Payment:
    return await payment_service.get_payment(db, payment_id)


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: uuid.UUID, data: PaymentUpdate, db: DbSession, user: CurrentUser, context: RequestContext
) -> Payment:
    return await payment_service.update_payment(db, payment_id, data, user, context)


@router.post("/{payment_id}/pay", response_model=PaymentRead, summary="Registra o recebimento")
async def mark_paid(
    payment_id: uuid.UUID, data: PaymentMarkPaid, db: DbSession, user: CurrentUser, context: RequestContext
) -> Payment:
    return await payment_service.mark_paid(db, payment_id, data, user, context)


@router.post("/{payment_id}/cancel", response_model=PaymentRead, summary="Cancela a fatura (gestor/admin)")
async def cancel_payment(
    payment_id: uuid.UUID, data: PaymentCancel, db: DbSession, user: ManagerUser, context: RequestContext
) -> Payment:
    return await payment_service.cancel_payment(db, payment_id, data, user, context)


@router.post("/refresh-overdue", summary="Atualiza status de faturas vencidas para 'atrasado'")
async def refresh_overdue(db: DbSession, _: CurrentUser) -> dict[str, int]:
    return {"updated": await payment_service.refresh_overdue_statuses(db)}
