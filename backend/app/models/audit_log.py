import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import AuditAction


class AuditLog(Base):
    """Trilha de auditoria genérica (append-only) de todas as entidades.

    `changes` guarda o diff: {"campo": {"old": valor_antigo, "new": valor_novo}}.
    Além de compliance, é um histórico rico de eventos para modelos de IA
    (ex.: quantas vezes o valor da proposta foi renegociado).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "client", "deal", "payment"...
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[AuditAction] = mapped_column(pg_enum(AuditAction, "audit_action"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    # Contexto da requisição: ip, user_agent, request_id.
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
