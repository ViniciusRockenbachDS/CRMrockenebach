from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from app.models.enums import InteractionDirection, InteractionType
from app.schemas.common import InputModel, QueryModel, TimestampedRead
from app.schemas.summaries import UserSummary

# Tolerância para diferença de relógio entre cliente e servidor.
_FUTURE_TOLERANCE = timedelta(minutes=5)


def _not_in_future(value: datetime | None) -> datetime | None:
    if value is not None and value > datetime.now(UTC) + _FUTURE_TOLERANCE:
        raise ValueError("A data da interação não pode estar no futuro.")
    return value


class InteractionCreate(InputModel):
    """O client_id vem da rota: POST /clients/{client_id}/interactions."""

    type: InteractionType
    direction: InteractionDirection = InteractionDirection.SAIDA
    subject: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    occurred_at: AwareDatetime | None = Field(
        default=None, description="Se omitido, usa o horário atual do servidor"
    )
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    deal_id: UUID | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)

    _check_occurred_at = field_validator("occurred_at")(_not_in_future)


class InteractionUpdate(InputModel):
    type: InteractionType | None = None
    direction: InteractionDirection | None = None
    subject: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)
    occurred_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    deal_id: UUID | None = None

    _check_occurred_at = field_validator("occurred_at")(_not_in_future)


class InteractionRead(TimestampedRead):
    client_id: UUID
    deal_id: UUID | None = None
    user: UserSummary | None = None
    type: InteractionType
    direction: InteractionDirection
    subject: str | None = None
    content: str
    occurred_at: datetime
    duration_minutes: int | None = None
    sentiment: float | None = Field(default=None, description="-1 a 1, preenchido pela IA")
    extra_data: dict[str, Any] = Field(default_factory=dict)


class InteractionFilters(QueryModel):
    type: list[InteractionType] | None = None
    deal_id: UUID | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
