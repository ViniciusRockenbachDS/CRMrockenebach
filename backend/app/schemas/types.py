"""Tipos anotados reutilizáveis nos schemas (validação + serialização)."""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, EmailStr, Field, PlainSerializer, StringConstraints

from app.utils.validators import normalize_document, normalize_phone_br


def _empty_to_none(value: object) -> object:
    """Strings vazias vindas de formulários viram None (campo opcional não preenchido)."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for tag in tags:
        cleaned = " ".join(tag.strip().lower().split())
        if cleaned:
            seen.setdefault(cleaned, None)
    return list(seen)


# Dinheiro: Decimal exato na entrada/banco; número (float) no JSON para facilitar o front-end.
_money_serializer = PlainSerializer(lambda v: float(v), return_type=float, when_used="json")

Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2), _money_serializer]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2), _money_serializer]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2), _money_serializer]

Probability = Annotated[int, Field(ge=0, le=100, description="Probabilidade de fechamento (0–100%)")]

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

LowerEmail = Annotated[EmailStr, AfterValidator(lambda v: v.lower())]
OptionalEmail = Annotated[LowerEmail | None, BeforeValidator(_empty_to_none)]

PhoneBR = Annotated[
    str,
    AfterValidator(normalize_phone_br),
    Field(examples=["(47) 99999-8888"], description="Normalizado para +5547999998888"),
]
OptionalPhoneBR = Annotated[PhoneBR | None, BeforeValidator(_empty_to_none)]

DocumentBR = Annotated[
    str,
    AfterValidator(normalize_document),
    Field(description="CPF ou CNPJ (com ou sem máscara); armazenado só com dígitos"),
]
OptionalDocumentBR = Annotated[DocumentBR | None, BeforeValidator(_empty_to_none)]

Tags = Annotated[
    list[Annotated[str, StringConstraints(max_length=50)]],
    Field(max_length=20),
    AfterValidator(_normalize_tags),
]
