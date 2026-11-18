from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.common import InputModel, QueryModel, TimestampedRead
from app.schemas.summaries import ClientSummary, DealSummary
from app.schemas.types import Money, NonNegativeMoney, PositiveMoney


def _not_future(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("A data de pagamento não pode estar no futuro.")
    return value


class PaymentCreate(InputModel):
    deal_id: UUID
    description: str | None = Field(default=None, max_length=255)
    amount: PositiveMoney
    method: PaymentMethod
    due_date: date
    status: Literal[PaymentStatus.PENDENTE, PaymentStatus.PAGO] = Field(
        default=PaymentStatus.PENDENTE,
        description="Na criação só faz sentido pendente ou já pago; 'atrasado' é calculado.",
    )
    payment_date: date | None = None
    installment_number: int = Field(default=1, ge=1, le=360)
    installment_total: int = Field(default=1, ge=1, le=360)
    external_reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    _check_payment_date = field_validator("payment_date")(_not_future)

    @model_validator(mode="after")
    def _validate(self) -> "PaymentCreate":
        if self.installment_number > self.installment_total:
            raise ValueError("installment_number não pode ser maior que installment_total.")
        if self.status == PaymentStatus.PAGO and self.payment_date is None:
            raise ValueError("Informe payment_date para registrar um pagamento como pago.")
        if self.status == PaymentStatus.PENDENTE and self.payment_date is not None:
            raise ValueError("Pagamento pendente não deve ter payment_date.")
        return self


class PaymentInstallmentsCreate(InputModel):
    """Gera N parcelas mensais de uma vez (o resto da divisão vai para a 1ª parcela)."""

    deal_id: UUID
    total_amount: PositiveMoney
    installments: int = Field(ge=1, le=120)
    first_due_date: date
    method: PaymentMethod
    description: str | None = Field(default=None, max_length=255)

    def split_amounts(self) -> list[Decimal]:
        base = (self.total_amount / self.installments).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        remainder = self.total_amount - base * self.installments
        return [base + remainder if i == 0 else base for i in range(self.installments)]


class PaymentUpdate(InputModel):
    """Só pagamentos não liquidados podem ser editados (regra no serviço)."""

    description: str | None = Field(default=None, max_length=255)
    amount: PositiveMoney | None = None
    method: PaymentMethod | None = None
    due_date: date | None = None
    external_reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class PaymentMarkPaid(InputModel):
    payment_date: date = Field(default_factory=date.today)
    method: PaymentMethod | None = Field(default=None, description="Sobrescreve o método previsto")
    notes: str | None = Field(default=None, max_length=2000)

    _check_payment_date = field_validator("payment_date")(_not_future)


class PaymentCancel(InputModel):
    reason: str = Field(min_length=3, max_length=1000)


class PaymentRead(TimestampedRead):
    deal_id: UUID
    deal: DealSummary
    client: ClientSummary | None = None
    invoice_number: str
    description: str | None = None
    amount: Money
    method: PaymentMethod
    status: PaymentStatus
    due_date: date
    payment_date: date | None = None
    installment_number: int
    installment_total: int
    external_reference: str | None = None
    notes: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_overdue(self) -> int:
        if self.status.is_receivable and self.due_date < date.today():
            return (date.today() - self.due_date).days
        return 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return self.status.label


class PaymentFilters(QueryModel):
    status: list[PaymentStatus] | None = None
    method: list[PaymentMethod] | None = None
    deal_id: UUID | None = None
    client_id: UUID | None = None
    due_from: date | None = None
    due_to: date | None = None
    paid_from: date | None = None
    paid_to: date | None = None
    overdue_only: bool = False
    order_by: Literal["due_date", "amount", "payment_date", "created_at"] = "due_date"
    order_dir: Literal["asc", "desc"] = "asc"


class ReceivablesSummary(BaseModel):
    """Totais exibidos no topo da tela de pagamentos."""

    total_pending: NonNegativeMoney
    total_overdue: NonNegativeMoney
    total_paid_period: NonNegativeMoney
    count_overdue: int
    generated_at: datetime
