import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.db.types import pg_enum
from app.models.enums import AIInsightType


class AIInsight(UUIDPrimaryKeyMixin, Base):
    """Toda saída gerada pela camada de IA fica registrada aqui.

    - Cache: evita chamar o provedor de novo para a mesma entrada (`input_hash`).
    - Rastreabilidade: provedor, modelo, versão do prompt, tokens e latência.
    - Avaliação: permite comparar previsões (lead score) com o resultado real do deal.
    """

    __tablename__ = "ai_insights"

    insight_type: Mapped[AIInsightType] = mapped_column(
        pg_enum(AIInsightType, "ai_insight_type"), nullable=False
    )
    # Alvo do insight; ambos nulos para insights globais (ex.: funil inteiro).
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)       # stub, openai, anthropic
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)    # SHA-256 da entrada

    content: Mapped[str | None] = mapped_column(Text)                     # texto principal gerado
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))           # ex.: lead score 0–100
    payload: Mapped[dict[str, Any]] = mapped_column(                       # resposta estruturada completa
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # "Último insight do tipo X para a entidade Y"
        Index("ix_ai_insights_lookup", "insight_type", "entity_type", "entity_id", "created_at"),
        Index("ix_ai_insights_input_hash", "insight_type", "input_hash"),
    )
