"""Base declarativa do SQLAlchemy com convenção de nomes para constraints e índices.

A convenção garante nomes estáveis e previsíveis nas migrations do Alembic
(sem ela, o Postgres gera nomes aleatórios e o downgrade fica frágil).
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    """Classe base de todos os models.

    AsyncAttrs habilita `await obj.awaitable_attrs.relacionamento` quando for
    preciso carregar um relacionamento sob demanda em contexto assíncrono.
    Como regra, os repositórios usam selectinload/joinedload explicitamente.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Busca valores gerados no servidor (server_default, Identity, Computed) via RETURNING
    # logo após INSERT/UPDATE — evita lazy loads implícitos, que não funcionam em async.
    __mapper_args__ = {"eager_defaults": True}
