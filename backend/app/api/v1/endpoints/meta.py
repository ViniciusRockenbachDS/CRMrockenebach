from fastapi import APIRouter

from app.models import (
    ClientStatus,
    DealStage,
    InteractionDirection,
    InteractionType,
    LeadSource,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.schemas.common import EnumOption

router = APIRouter(prefix="/meta", tags=["Metadados"])

_ENUMS = {
    "client_status": ClientStatus,
    "lead_source": LeadSource,
    "deal_stage": DealStage,
    "interaction_type": InteractionType,
    "interaction_direction": InteractionDirection,
    "payment_status": PaymentStatus,
    "payment_method": PaymentMethod,
    "user_role": UserRole,
}


@router.get("/enums", response_model=dict[str, list[EnumOption]], summary="Opções (valor/rótulo) para selects")
async def get_enums() -> dict[str, list[EnumOption]]:
    return {name: [EnumOption(value=m.value, label=m.label) for m in enum] for name, enum in _ENUMS.items()}
