import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import Money, pg_enum
from app.models.enums import DealStage

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.deal_stage_history import DealStageHistory
    from app.models.interaction import Interaction
    from app.models.payment import Payment
    from app.models.user import User

_CLOSED_STAGES_SQL = "('fechado_ganho', 'fechado_perdido')"


class Deal(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Negociação (oportunidade) no funil de vendas."""

    __tablename__ = "deals"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_value: Mapped[Decimal] = mapped_column(
        Money, nullable=False, default=Decimal("0"), server_default=text("0")
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="BRL", server_default="BRL"
    )
    probability: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=10, server_default=text("10")
    )
    stage: Mapped[DealStage] = mapped_column(
        pg_enum(DealStage, "deal_stage"),
        nullable=False,
        default=DealStage.PROSPECCAO,
        server_default=DealStage.PROSPECCAO.value,
    )
    # Ordem do card dentro da coluna do Kanban.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lost_reason: Mapped[str | None] = mapped_column(Text)
    # Momento em que entrou na etapa atual (feature "tempo parado na etapa").
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Saída do modelo de Lead Scoring (camada de IA) -----------------------------
    ai_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ai_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Relacionamentos ------------------------------------------------------------
    client: Mapped["Client"] = relationship(back_populates="deals")
    owner: Mapped["User | None"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="deal", order_by="Payment.due_date"
    )
    stage_history: Mapped[list["DealStageHistory"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DealStageHistory.changed_at",
    )
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="deal")

    __table_args__ = (
        CheckConstraint("estimated_value >= 0", name="estimated_value_non_negative"),
        CheckConstraint("probability BETWEEN 0 AND 100", name="probability_range"),
        CheckConstraint("ai_score IS NULL OR ai_score BETWEEN 0 AND 100", name="ai_score_range"),
        # closed_at preenchido se, e somente se, a negociação estiver fechada.
        CheckConstraint(
            f"(stage IN {_CLOSED_STAGES_SQL}) = (closed_at IS NOT NULL)",
            name="closed_at_consistency",
        ),
        # Montagem do Kanban: WHERE deleted_at IS NULL ORDER BY stage, position
        Index(
            "ix_deals_board",
            "stage",
            "position",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_deals_owner_stage", "owner_id", "stage"),
        Index("ix_deals_expected_close_date", "expected_close_date"),
        # Métricas de conversão por período: WHERE stage IN (...) AND closed_at BETWEEN ...
        Index("ix_deals_closed_at", "closed_at", postgresql_where=text("closed_at IS NOT NULL")),
    )

    @property
    def weighted_value(self) -> Decimal:
        """Valor ponderado pela probabilidade (previsão de receita do pipeline)."""
        return (self.estimated_value * Decimal(self.probability) / Decimal(100)).quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return f"<Deal {self.title!r} ({self.stage})>"
