"""Tipos de coluna compartilhados."""

import enum

from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import ENUM

# Valores monetários: até 999.999.999.999,99 com 2 casas decimais exatas.
Money = Numeric(14, 2)


def pg_enum(enum_cls: type[enum.Enum], name: str, *, create_type: bool = True) -> ENUM:
    """ENUM nativo do Postgres que persiste o `.value` (ex.: 'fechado_ganho'), não o nome.

    Use `create_type=False` quando o MESMO tipo for reutilizado em uma segunda
    tabela/coluna: assim o Alembic não tenta executar CREATE TYPE duas vezes.
    """
    return ENUM(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
        create_type=create_type,
    )
