"""add_avantages_to_worker

Revision ID: 3e8a9d1b2c4f
Revises: 11bfecd7a411
Create Date: 2025-12-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3e8a9d1b2c4f"
down_revision: Union[str, Sequence[str], None] = "11bfecd7a411"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "workers"):
        return

    columns = [
        ("avantage_vehicule", sa.Column("avantage_vehicule", sa.Float(), nullable=True, server_default="0.0")),
        ("avantage_logement", sa.Column("avantage_logement", sa.Float(), nullable=True, server_default="0.0")),
        ("avantage_telephone", sa.Column("avantage_telephone", sa.Float(), nullable=True, server_default="0.0")),
        ("avantage_autres", sa.Column("avantage_autres", sa.Float(), nullable=True, server_default="0.0")),
    ]

    for column_name, column in columns:
        if not _has_column(inspector, "workers", column_name):
            op.add_column("workers", column)
            inspector = sa.inspect(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "workers"):
        return

    for column_name in [
        "avantage_autres",
        "avantage_telephone",
        "avantage_logement",
        "avantage_vehicule",
    ]:
        if _has_column(inspector, "workers", column_name):
            op.drop_column("workers", column_name)
            inspector = sa.inspect(bind)
