"""add_logo_path_column_fix

Revision ID: 2f20da188f02
Revises: 0a5ab69c3bf1
Create Date: 2025-12-11 09:35:07.647785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2f20da188f02"
down_revision: Union[str, Sequence[str], None] = "0a5ab69c3bf1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "employers" in inspector.get_table_names() and not _has_column(inspector, "employers", "logo_path"):
        op.add_column("employers", sa.Column("logo_path", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "employers" in inspector.get_table_names() and _has_column(inspector, "employers", "logo_path"):
        op.drop_column("employers", "logo_path")
