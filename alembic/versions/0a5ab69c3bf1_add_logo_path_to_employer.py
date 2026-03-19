"""add_logo_path_to_employer

Revision ID: 0a5ab69c3bf1
Revises: aaaa1111bbbb
Create Date: 2025-12-10 20:55:29.853758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a5ab69c3bf1"
down_revision: Union[str, Sequence[str], None] = "aaaa1111bbbb"
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
