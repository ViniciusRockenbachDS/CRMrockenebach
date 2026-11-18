"""Schemas genéricos: base ORM, paginação, ordenação e respostas padrão."""

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base para schemas de leitura que recebem objetos SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class InputModel(BaseModel):
    """Base para payloads de entrada: rejeita campos desconhecidos e remove espaços extras."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueryModel(BaseModel):
    """Base para filtros recebidos via query string (Annotated[Model, Query()]).

    Usa extra="ignore" porque limit/offset chegam na mesma query string por outra dependência.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class TimestampedRead(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SortParams(BaseModel):
    order_dir: Literal["asc", "desc"] = "desc"


class Page(BaseModel, Generic[T]):
    """Resposta paginada padrão: { items, total, limit, offset, has_more }."""

    items: list[T]
    total: int = Field(ge=0)
    limit: int
    offset: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


class EnumOption(BaseModel):
    """Par valor/rótulo para popular selects no front-end."""

    value: str
    label: str


class MessageResponse(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorResponse(BaseModel):
    """Formato único de erro devolvido pela API (usado pelo handler global na Etapa 2)."""

    code: str = Field(examples=["deal_not_won"])
    message: str = Field(examples=["Pagamentos só podem ser lançados em negociações ganhas."])
    details: list[ErrorDetail] | None = None
    extra: dict[str, Any] | None = None
