"""Importa todos os models para registrá-los no metadata (necessário para o Alembic)."""

from app.models.ai_insight import AIInsight
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.deal import Deal
from app.models.deal_stage_history import DealStageHistory
from app.models.enums import (
    AIInsightType,
    AuditAction,
    ClientStatus,
    DealStage,
    InteractionDirection,
    InteractionType,
    LeadSource,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.models.interaction import Interaction
from app.models.payment import Payment
from app.models.user import User

__all__ = [
    "AIInsight",
    "AIInsightType",
    "AuditAction",
    "AuditLog",
    "Client",
    "ClientStatus",
    "Deal",
    "DealStage",
    "DealStageHistory",
    "Interaction",
    "InteractionDirection",
    "InteractionType",
    "LeadSource",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "User",
    "UserRole",
]
