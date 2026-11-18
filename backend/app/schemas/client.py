from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import ClientStatus, LeadSource
from app.schemas.common import InputModel, ORMModel, QueryModel, TimestampedRead
from app.schemas.interaction import InteractionRead
from app.schemas.summaries import DealSummary, UserSummary
from app.schemas.types import (
    Money,
    OptionalDocumentBR,
    OptionalEmail,
    OptionalPhoneBR,
    Tags,
)


class _ClientFields(InputModel):
    name: str = Field(min_length=2, max_length=150)
    company: str | None = Field(default=None, max_length=150)
    job_title: str | None = Field(default=None, max_length=100)
    email: OptionalEmail = None
    phone: OptionalPhoneBR = None
    whatsapp: OptionalPhoneBR = None
    document: OptionalDocumentBR = None
    lead_source: LeadSource = LeadSource.OUTRO
    status: ClientStatus = ClientStatus.LEAD
    notes: str | None = Field(default=None, max_length=5000)
    tags: Tags = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class ClientCreate(_ClientFields):
    owner_id: UUID | None = Field(
        default=None, description="Responsável; se omitido, o usuário logado assume"
    )
    whatsapp_same_as_phone: bool = Field(
        default=False, description="Copia o telefone para o WhatsApp", exclude=True
    )

    @model_validator(mode="after")
    def _contact_required(self) -> "ClientCreate":
        if self.whatsapp_same_as_phone and self.phone and not self.whatsapp:
            self.whatsapp = self.phone
        if not any((self.email, self.phone, self.whatsapp)):
            raise ValueError("Informe ao menos um meio de contato: e-mail, telefone ou WhatsApp.")
        return self


class ClientUpdate(InputModel):
    """PATCH parcial: só os campos enviados são alterados (model_dump(exclude_unset=True))."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    company: str | None = Field(default=None, max_length=150)
    job_title: str | None = Field(default=None, max_length=100)
    email: OptionalEmail = None
    phone: OptionalPhoneBR = None
    whatsapp: OptionalPhoneBR = None
    document: OptionalDocumentBR = None
    lead_source: LeadSource | None = None
    status: ClientStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)
    tags: Tags | None = None
    custom_fields: dict[str, Any] | None = None
    owner_id: UUID | None = None


class ClientListItem(ORMModel):
    """Linha da tabela de clientes (payload enxuto)."""

    id: UUID
    name: str
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    status: ClientStatus
    lead_source: LeadSource
    tags: list[str] = Field(default_factory=list)
    owner: UserSummary | None = None
    last_interaction_at: datetime | None = None
    created_at: datetime


class ClientRead(TimestampedRead):
    name: str
    company: str | None = None
    job_title: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    document: str | None = None
    lead_source: LeadSource
    status: ClientStatus
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    owner: UserSummary | None = None
    last_interaction_at: datetime | None = None


class ClientStats(ORMModel):
    open_deals: int = 0
    won_deals: int = 0
    lost_deals: int = 0
    pipeline_value: Money = Field(default=Decimal("0"), description="Soma das negociações abertas")
    total_won_value: Money = Decimal("0")
    total_paid: Money = Decimal("0")
    outstanding_amount: Money = Field(default=Decimal("0"), description="Pendente + atrasado")
    overdue_amount: Money = Decimal("0")


class ClientDetail(ClientRead):
    """GET /clients/{id}: cadastro + estatísticas + últimas interações + negociações."""

    stats: ClientStats = Field(default_factory=ClientStats)
    recent_interactions: list[InteractionRead] = Field(default_factory=list)
    deals: list[DealSummary] = Field(default_factory=list)


class ClientFilters(QueryModel):
    search: str | None = Field(
        default=None, max_length=100, description="Busca em nome, empresa, e-mail e telefone"
    )
    status: list[ClientStatus] | None = None
    lead_source: list[LeadSource] | None = None
    owner_id: UUID | None = None
    tag: str | None = None
    created_from: date | None = None
    created_to: date | None = None
    no_contact_days: int | None = Field(
        default=None, ge=1, description="Clientes sem interação há N dias ou mais"
    )
    order_by: Literal["name", "created_at", "last_interaction_at", "status"] = "created_at"
    order_dir: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def _check_dates(self) -> "ClientFilters":
        if self.created_from and self.created_to and self.created_from > self.created_to:
            raise ValueError("created_from deve ser anterior ou igual a created_to.")
        return self
