import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.db.types import Money, pg_enum
from app.models.enums import DealStage

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.user import User

# O tipo "deal_stage" já é criado pela tabela deals; aqui só é reutilizado.
_deal_stage_type = pg_enum(DealStage, "deal_stage", create_type=False)


class DealStageHistory(UUIDPrimaryKeyMixin, Base):
    """Registro imutável de cada mudança de etapa de uma negociação.

    Permite calcular tempo médio por etapa, taxa de conversão entre etapas e
    serve como dataset rotulado para o modelo de previsão de fechamento.
    """

    __tablename__ = "deal_stage_history"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), nullable=False
    )
    from_stage: Mapped[DealStage | None] = mapped_column(_deal_stage_type)  # NULL = criação
    to_stage: Mapped[DealStage] = mapped_column(_deal_stage_type, nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Fotografia da negociação no momento da mudança (features para IA).
    estimated_value_snapshot: Mapped[Decimal] = mapped_column(Money, nullable=False)
    probability_snapshot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seconds_in_previous_stage: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)

    deal: Mapped["Deal"] = relationship(back_populates="stage_history")
    changed_by: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_deal_stage_history_deal_changed", "deal_id", "changed_at"),
        Index("ix_deal_stage_history_to_stage_changed", "to_stage", "changed_at"),
    )
