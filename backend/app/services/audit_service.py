"""Trilha de auditoria: registra quem mudou o quê, quando e de onde."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [to_jsonable(v) for v in value]
    return value


def snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    return {field: {"old": None, "new": getattr(obj, field)} for field in fields}


async def log(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    user_id: uuid.UUID | None,
    changes: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Adiciona o registro à sessão atual — é gravado no mesmo commit da operação."""
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            changes=to_jsonable(changes or {}),
            context=to_jsonable(context or {}),
        )
    )
