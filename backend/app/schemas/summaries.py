"""Representações resumidas usadas dentro de outros schemas (evita imports circulares)."""

from datetime import date
from uuid import UUID

from app.models.enums import ClientStatus, DealStage, UserRole
from app.schemas.common import ORMModel
from app.schemas.types import Money


class UserSummary(ORMModel):
    id: UUID
    name: str
    email: str
    role: UserRole


class ClientSummary(ORMModel):
    id: UUID
    name: str
    company: str | None = None
    email: str | None = None
    status: ClientStatus


class DealSummary(ORMModel):
    id: UUID
    title: str
    stage: DealStage
    estimated_value: Money
    probability: int
    expected_close_date: date | None = None
    client_id: UUID
