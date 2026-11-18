from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import DealStage, PaymentStatus
from app.schemas.client import ClientCreate
from app.schemas.deal import DealCreate, DealMove, DealRead
from app.schemas.payment import PaymentCreate, PaymentInstallmentsCreate


def test_client_normalization() -> None:
    client = ClientCreate(
        name="  Maria Silva ",
        email="Maria@Empresa.com",
        phone="(47) 99999-8888",
        whatsapp_same_as_phone=True,
        tags=["VIP", " vip "],
    )
    assert client.name == "Maria Silva"
    assert client.email == "maria@empresa.com"
    assert client.whatsapp == "+5547999998888"
    assert client.tags == ["vip"]


def test_client_requires_contact() -> None:
    with pytest.raises(ValidationError, match="meio de contato"):
        ClientCreate(name="Sem contato")


def test_deal_default_probability_and_lost_reason() -> None:
    deal = DealCreate(client_id=uuid4(), title="Implantação", stage=DealStage.PROPOSTA)
    assert deal.probability == 50
    with pytest.raises(ValidationError, match="motivo da perda"):
        DealMove(stage=DealStage.FECHADO_PERDIDO)


def test_deal_read_computed_fields() -> None:
    now = datetime.now(UTC)
    deal = DealRead(
        id=uuid4(), created_at=now, updated_at=now, client_id=uuid4(),
        client={"id": uuid4(), "name": "Ana", "status": "cliente"},
        title="T", estimated_value=Decimal("1000.00"), currency="BRL", probability=75,
        stage=DealStage.NEGOCIACAO, position=0, stage_changed_at=now,
        expected_close_date=date.today() - timedelta(days=1),
    )
    data = deal.model_dump(mode="json")
    assert data["weighted_value"] == 750.0
    assert data["is_overdue"] is True


def test_payment_rules() -> None:
    with pytest.raises(ValidationError):
        PaymentCreate(deal_id=uuid4(), amount=Decimal("10"), method="pix", due_date=date.today(), status=PaymentStatus.PAGO)
    parts = PaymentInstallmentsCreate(
        deal_id=uuid4(), total_amount=Decimal("1000.00"), installments=3, first_due_date=date.today(), method="boleto"
    ).split_amounts()
    assert sum(parts) == Decimal("1000.00")
    assert parts[0] == Decimal("333.34")
