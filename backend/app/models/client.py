import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import pg_enum
from app.models.enums import ClientStatus, LeadSource

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.interaction import Interaction
    from app.models.user import User


class Client(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Lead / contato / cliente. O ciclo de vida é controlado por `status`."""

    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150))
    job_title: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))       # formato E.164: +5547999998888
    whatsapp: Mapped[str | None] = mapped_column(String(20))
    document: Mapped[str | None] = mapped_column(String(14))    # CPF (11) ou CNPJ (14), só dígitos

    lead_source: Mapped[LeadSource] = mapped_column(
        pg_enum(LeadSource, "lead_source"),
        nullable=False,
        default=LeadSource.OUTRO,
        server_default=LeadSource.OUTRO.value,
    )
    status: Mapped[ClientStatus] = mapped_column(
        pg_enum(ClientStatus, "client_status"),
        nullable=False,
        default=ClientStatus.LEAD,
        server_default=ClientStatus.LEAD.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, default=list, server_default=text("'{}'")
    )
    # Campos livres por empresa (segmento, porte, cidade...) — também servem de features para IA.
    custom_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Desnormalizado (atualizado pelo serviço de interações): ordenação por "último contato"
    # e feature "dias sem contato" para o lead scoring.
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Relacionamentos ---------------------------------------------------------
    owner: Mapped["User | None"] = relationship()
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Interaction.occurred_at.desc()",
    )
    deals: Mapped[list["Deal"]] = relationship(back_populates="client")

    __table_args__ = (
        Index("ix_clients_status_owner", "status", "owner_id"),
        Index("ix_clients_lead_source", "lead_source"),
        Index("ix_clients_last_interaction_at", "last_interaction_at"),
        # Listagens padrão ignoram registros excluídos logicamente.
        Index("ix_clients_active_created", "created_at", postgresql_where=text("deleted_at IS NULL")),
        # Busca "contém" por nome/empresa (ILIKE '%termo%') usando pg_trgm.
        Index(
            "ix_clients_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_clients_company_trgm",
            "company",
            postgresql_using="gin",
            postgresql_ops={"company": "gin_trgm_ops"},
        ),
        Index("ix_clients_tags", "tags", postgresql_using="gin"),
        # CPF/CNPJ único entre clientes ativos.
        Index(
            "uq_clients_document_active",
            "document",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND document IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Client {self.name!r} ({self.status})>"
