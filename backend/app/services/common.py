"""Utilitários compartilhados pelos serviços."""

from collections.abc import Iterable, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import Page, PaginationParams

SchemaT = TypeVar("SchemaT", bound=BaseModel)


async def paginate(
    db: AsyncSession,
    stmt: Select[Any],
    page: PaginationParams,
    schema: type[SchemaT],
) -> Page[SchemaT]:
    """Executa COUNT(*) sobre a consulta filtrada e devolve a página solicitada."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.scalar(count_stmt)) or 0
    rows: Sequence[Any] = (await db.scalars(stmt.limit(page.limit).offset(page.offset))).all()
    return Page[schema](  # type: ignore[valid-type]
        items=[schema.model_validate(row) for row in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


def apply_updates(
    obj: Any, data: dict[str, Any], *, non_nullable: Iterable[str] = ()
) -> dict[str, dict[str, Any]]:
    """Aplica um PATCH parcial no objeto e devolve o diff {campo: {old, new}}.

    Campos em `non_nullable` enviados como null são ignorados (não podem ficar vazios no banco).
    """
    blocked = set(non_nullable)
    changes: dict[str, dict[str, Any]] = {}
    for field, new_value in data.items():
        if new_value is None and field in blocked:
            continue
        old_value = getattr(obj, field)
        if old_value != new_value:
            setattr(obj, field, new_value)
            changes[field] = {"old": old_value, "new": new_value}
    return changes
