"""add_date_fin_essai_to_worker_final

Revision ID: f24a8c8fe81a
Revises: ef65da7ed4a8
Create Date: 2025-12-24 22:32:54.955381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f24a8c8fe81a"
down_revision: Union[str, Sequence[str], None] = "ef65da7ed4a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" in inspector.get_table_names() and not _has_column(inspector, "workers", "date_fin_essai"):
        op.add_column("workers", sa.Column("date_fin_essai", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" in inspector.get_table_names() and _has_column(inspector, "workers", "date_fin_essai"):
        op.drop_column("workers", "date_fin_essai")
