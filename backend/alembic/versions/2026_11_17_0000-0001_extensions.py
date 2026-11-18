"""Extensões do PostgreSQL necessárias antes do schema

- pg_trgm: busca textual rápida por nome de cliente (índice GIN trigram)

Revision ID: 0001_extensions
Revises:
Create Date: 2026-11-17 00:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_extensions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
