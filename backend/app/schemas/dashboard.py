"""Schemas do Dashboard analítico.

Definições das métricas (implementadas no dashboard_service na Etapa 2):
- total_revenue ....... soma de payments PAGO com payment_date no período
- average_ticket ...... média de estimated_value dos deals GANHOS fechados no período
- conversion_rate ..... ganhos / (ganhos + perdidos) fechados no período
- receivables ......... soma de payments PENDENTE + ATRASADO (todas as datas)
- overdue_amount ...... soma de payments em aberto com due_date < hoje
- delinquency_rate .... overdue_amount / (valor vencido até hoje: pago + em atraso)
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DealStage, LeadSource
from app.schemas.common import QueryModel
from app.schemas.summaries import ClientSummary
from app.schemas.types import Money


class DashboardFilters(QueryModel):
    date_from: date | None = Field(default=None, description="Padrão: 1º dia do mês atual")
    date_to: date | None = Field(default=None, description="Padrão: hoje")
    owner_id: UUID | None = Field(default=None, description="Filtra por vendedor responsável")

    @model_validator(mode="after")
    def _check(self) -> "DashboardFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from deve ser anterior ou igual a date_to.")
        return self


class KPISummary(BaseModel):
    total_revenue: Money
    average_ticket: Money
    conversion_rate: float = Field(ge=0, le=1, description="0–1 (multiplique por 100 para %)")
    won_deals_count: int
    lost_deals_count: int
    open_deals_count: int
    open_pipeline_value: Money
    weighted_pipeline_value: Money
    receivables: Money
    overdue_amount: Money
    overdue_count: int
    delinquency_rate: float = Field(ge=0, le=1)
    new_clients_count: int


class KPIComparison(BaseModel):
    """Variação percentual em relação ao período anterior de mesma duração."""

    total_revenue_pct: float | None = None
    conversion_rate_pct: float | None = None
    average_ticket_pct: float | None = None
    new_clients_pct: float | None = None


class FunnelStageMetric(BaseModel):
    stage: DealStage
    label: str
    count: int
    total_value: Money
    weighted_value: Money
    avg_days_in_stage: float | None = None
    conversion_from_previous: float | None = Field(
        default=None, description="% de deals que passaram da etapa anterior para esta"
    )


class RevenuePoint(BaseModel):
    period: date = Field(description="Primeiro dia do mês")
    received: Money
    expected: Money = Field(description="Valor com vencimento no mês")
    overdue: Money


class LeadSourceMetric(BaseModel):
    lead_source: LeadSource
    label: str
    clients_count: int
    won_deals_count: int
    won_value: Money
    conversion_rate: float


class TopClient(BaseModel):
    client: ClientSummary
    total_paid: Money
    deals_won: int


class OverduePaymentItem(BaseModel):
    payment_id: UUID
    invoice_number: str
    client: ClientSummary
    amount: Money
    due_date: date
    days_overdue: int


class DashboardResponse(BaseModel):
    period_start: date
    period_end: date
    summary: KPISummary
    comparison: KPIComparison
    funnel: list[FunnelStageMetric]
    revenue_series: list[RevenuePoint]
    lead_sources: list[LeadSourceMetric]
    top_clients: list[TopClient]
    top_overdue: list[OverduePaymentItem]
    generated_at: datetime
