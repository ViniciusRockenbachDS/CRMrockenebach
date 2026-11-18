import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import Money, pg_enum
from app.models.enums import PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.deal import Deal


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fatura / parcela vinculada a uma negociação GANHA.

    Regra "só negociações em Fechado Ganho" é validada na camada de serviço
    (exige consulta a outra tabela, o que não cabe em CHECK constraint).
    O cliente é obtido via deal → client (modelo normalizado, sem client_id duplicado).
    """

    __tablename__ = "payments"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Sequencial gerado pelo banco; o número da fatura é derivado dele (FAT-000001).
    # Gerar no banco elimina condição de corrida entre requisições simultâneas.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False, unique=True)
    invoice_number: Mapped[str] = mapped_column(
        String(30), Computed("'FAT-' || lpad(seq::text, 6, '0')", persisted=True), unique=True
    )
    description: Mapped[str | None] = mapped_column(String(255))

    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        pg_enum(PaymentMethod, "payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "payment_status"),
        nullable=False,
        default=PaymentStatus.PENDENTE,
        server_default=PaymentStatus.PENDENTE.value,
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date)

    installment_number: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )
    installment_total: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )
    # ID no gateway de pagamento (Asaas, Mercado Pago, Stripe...) para conciliação futura.
    external_reference: Mapped[str | None] = mapped_column(String(100), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    deal: Mapped["Deal"] = relationship(back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "status <> 'pago' OR payment_date IS NOT NULL", name="paid_requires_payment_date"
        ),
        CheckConstraint(
            "installment_number >= 1 AND installment_number <= installment_total",
            name="installment_range",
        ),
        # Contas a receber / inadimplência: WHERE status IN (...) AND due_date < hoje
        Index("ix_payments_status_due_date", "status", "due_date"),
        # Receita realizada por período.
        Index(
            "ix_payments_paid_date",
            "payment_date",
            postgresql_where=text("status = 'pago'"),
        ),
    )

    @property
    def client(self) -> "Client | None":
        """Atalho para serialização. Exige `deal` carregado (selectinload) em contexto async."""
        return self.deal.client if self.deal is not None else None

    def __repr__(self) -> str:
        return f"<Payment {self.invoice_number} {self.amount} ({self.status})>"
