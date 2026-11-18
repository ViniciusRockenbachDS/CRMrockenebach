import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import pg_enum
from app.models.enums import InteractionDirection, InteractionType

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.deal import Deal
    from app.models.user import User


class Interaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Histórico de interações com o cliente (ligações, e-mails, reuniões, notas...).

    É a principal fonte de texto para a IA (resumo do cliente, sentimento, próximos passos).
    """

    __tablename__ = "interactions"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    type: Mapped[InteractionType] = mapped_column(
        pg_enum(InteractionType, "interaction_type"), nullable=False
    )
    direction: Mapped[InteractionDirection] = mapped_column(
        pg_enum(InteractionDirection, "interaction_direction"),
        nullable=False,
        default=InteractionDirection.SAIDA,
        server_default=InteractionDirection.SAIDA.value,
    )
    subject: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    # Preenchido pela IA: -1.00 (muito negativo) a 1.00 (muito positivo).
    sentiment: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    # Dados extras de integrações futuras (id da mensagem no WhatsApp, gravação, etc.).
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    client: Mapped["Client"] = relationship(back_populates="interactions")
    deal: Mapped["Deal | None"] = relationship(back_populates="interactions")
    user: Mapped["User | None"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes >= 0", name="duration_non_negative"
        ),
        CheckConstraint(
            "sentiment IS NULL OR sentiment BETWEEN -1 AND 1", name="sentiment_range"
        ),
        # Timeline do cliente: WHERE client_id = ? ORDER BY occurred_at DESC
        Index("ix_interactions_client_occurred", "client_id", "occurred_at"),
        Index("ix_interactions_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<Interaction {self.type} client={self.client_id}>"
