"""add_lieu_naissance_to_worker

Revision ID: ef65da7ed4a8
Revises: 09676a08809a
Create Date: 2025-12-24 22:24:46.125363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef65da7ed4a8"
down_revision: Union[str, Sequence[str], None] = "09676a08809a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" in inspector.get_table_names() and not _has_column(inspector, "workers", "lieu_naissance"):
        op.add_column("workers", sa.Column("lieu_naissance", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" in inspector.get_table_names() and _has_column(inspector, "workers", "lieu_naissance"):
        op.drop_column("workers", "lieu_naissance")
