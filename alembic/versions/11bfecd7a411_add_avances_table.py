"""add_avances_table

Revision ID: 11bfecd7a411
Revises: 2f20da188f02
Create Date: 2025-12-11 11:39:15.737576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "11bfecd7a411"
down_revision: Union[str, Sequence[str], None] = "2f20da188f02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "avances"):
        op.create_table(
            "avances",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.Integer(), nullable=False),
            sa.Column("periode", sa.String(), nullable=False),
            sa.Column("montant", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if _has_table(inspector, "avances") and not _has_index(inspector, "avances", op.f("ix_avances_id")):
        op.create_index(op.f("ix_avances_id"), "avances", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_table(inspector, "avances") and _has_index(inspector, "avances", op.f("ix_avances_id")):
        op.drop_index(op.f("ix_avances_id"), table_name="avances")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "avances"):
        op.drop_table("avances")
