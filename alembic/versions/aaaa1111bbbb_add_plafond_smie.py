"""add_plafond_smie_to_employer

Revision ID: aaaa1111bbbb
Revises: f6522e96157e
Create Date: 2025-12-10 13:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aaaa1111bbbb"
down_revision: Union[str, Sequence[str], None] = "f6522e96157e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "employers" in inspector.get_table_names() and not _has_column(inspector, "employers", "plafond_smie"):
        op.add_column("employers", sa.Column("plafond_smie", sa.Float(), nullable=True, server_default="0.0"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "employers" in inspector.get_table_names() and _has_column(inspector, "employers", "plafond_smie"):
        op.drop_column("employers", "plafond_smie")
