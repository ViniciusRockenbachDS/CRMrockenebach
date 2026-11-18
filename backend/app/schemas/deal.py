from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, computed_field, model_validator

from app.models.enums import DealStage
from app.schemas.common import InputModel, ORMModel, QueryModel, TimestampedRead
from app.schemas.summaries import ClientSummary, UserSummary
from app.schemas.types import Money, NonNegativeMoney, Probability


class DealCreate(InputModel):
    client_id: UUID
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    estimated_value: NonNegativeMoney = Decimal("0")
    probability: Probability | None = Field(
        default=None, description="Se omitida, usa a probabilidade padrão da etapa"
    )
    stage: DealStage = DealStage.PROSPECCAO
    expected_close_date: date | None = None
    owner_id: UUID | None = None
    lost_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validate(self) -> "DealCreate":
        if self.probability is None:
            self.probability = self.stage.default_probability
        _check_closed_stage_rules(self.stage, self.probability, self.lost_reason)
        return self


class DealUpdate(InputModel):
    """Edição de dados da negociação. A ETAPA muda por `DealMove` (gera histórico)."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    estimated_value: NonNegativeMoney | None = None
    probability: Probability | None = None
    expected_close_date: date | None = None
    owner_id: UUID | None = None
    client_id: UUID | None = None


class DealMove(InputModel):
    """Movimentação no Kanban: troca de etapa e/ou reordenação dentro da coluna."""

    stage: DealStage
    position: int | None = Field(default=None, ge=0, description="Índice na coluna de destino")
    probability: Probability | None = Field(
        default=None, description="Se omitida, assume a padrão da nova etapa"
    )
    lost_reason: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validate(self) -> "DealMove":
        _check_closed_stage_rules(self.stage, self.probability, self.lost_reason)
        return self


def _check_closed_stage_rules(
    stage: DealStage, probability: int | None, lost_reason: str | None
) -> None:
    if stage == DealStage.FECHADO_PERDIDO and not (lost_reason and lost_reason.strip()):
        raise ValueError("Informe o motivo da perda (lost_reason) ao marcar como Fechado Perdido.")
    if stage == DealStage.FECHADO_GANHO and probability is not None and probability != 100:
        raise ValueError("Negociações em Fechado Ganho devem ter probabilidade 100%.")
    if stage == DealStage.FECHADO_PERDIDO and probability is not None and probability != 0:
        raise ValueError("Negociações em Fechado Perdido devem ter probabilidade 0%.")


class DealRead(TimestampedRead):
    client_id: UUID
    client: ClientSummary
    owner: UserSummary | None = None
    title: str
    description: str | None = None
    estimated_value: Money
    currency: str
    probability: int
    stage: DealStage
    position: int
    expected_close_date: date | None = None
    closed_at: datetime | None = None
    lost_reason: str | None = None
    stage_changed_at: datetime
    ai_score: float | None = None
    ai_scored_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def weighted_value(self) -> float:
        return float(
            (self.estimated_value * Decimal(self.probability) / Decimal(100)).quantize(Decimal("0.01"))
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stage_label(self) -> str:
        return self.stage.label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        """Negociação aberta com data prevista de fechamento já vencida."""
        return (
            not self.stage.is_closed
            and self.expected_close_date is not None
            and self.expected_close_date < date.today()
        )


class DealStageHistoryRead(ORMModel):
    id: UUID
    deal_id: UUID
    from_stage: DealStage | None = None
    to_stage: DealStage
    changed_by: UserSummary | None = None
    changed_at: datetime
    estimated_value_snapshot: Money
    probability_snapshot: int
    seconds_in_previous_stage: int | None = None
    note: str | None = None


class DealFilters(QueryModel):
    search: str | None = Field(default=None, max_length=100)
    stage: list[DealStage] | None = None
    client_id: UUID | None = None
    owner_id: UUID | None = None
    min_value: NonNegativeMoney | None = None
    max_value: NonNegativeMoney | None = None
    expected_close_from: date | None = None
    expected_close_to: date | None = None
    only_open: bool = False
    order_by: Literal["created_at", "estimated_value", "expected_close_date", "probability", "ai_score"] = (
        "created_at"
    )
    order_dir: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def _check_ranges(self) -> "DealFilters":
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value não pode ser maior que max_value.")
        if (
            self.expected_close_from
            and self.expected_close_to
            and self.expected_close_from > self.expected_close_to
        ):
            raise ValueError("expected_close_from deve ser anterior a expected_close_to.")
        return self


class KanbanColumn(ORMModel):
    stage: DealStage
    label: str
    count: int
    total_value: Money
    weighted_value: Money
    deals: list[DealRead]


class KanbanBoard(ORMModel):
    columns: list[KanbanColumn]
    total_open_value: Money
    total_weighted_value: Money
