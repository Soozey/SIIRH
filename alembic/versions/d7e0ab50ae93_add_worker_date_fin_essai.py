"""add_worker_date_fin_essai

Revision ID: d7e0ab50ae93
Revises: dddd4444eeee
Create Date: 2025-12-20 21:55:26.155907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e0ab50ae93"
down_revision: Union[str, Sequence[str], None] = "dddd4444eeee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "employer_primes"):
        if _has_index(inspector, "employer_primes", op.f("ix_employer_primes_id")):
            op.drop_index(op.f("ix_employer_primes_id"), table_name="employer_primes")
        op.drop_table("employer_primes")
        inspector = sa.inspect(bind)

    if _has_table(inspector, "avances") and _has_column(inspector, "avances", "periode"):
        op.alter_column("avances", "periode", existing_type=sa.VARCHAR(), nullable=False)

    if _has_table(inspector, "workers") and not _has_column(inspector, "workers", "date_fin_essai"):
        op.add_column("workers", sa.Column("date_fin_essai", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "workers") and _has_column(inspector, "workers", "date_fin_essai"):
        op.drop_column("workers", "date_fin_essai")
        inspector = sa.inspect(bind)

    if _has_table(inspector, "avances") and _has_column(inspector, "avances", "periode"):
        op.alter_column("avances", "periode", existing_type=sa.VARCHAR(), nullable=True)
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "employer_primes"):
        op.create_table(
            "employer_primes",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("employer_id", sa.INTEGER(), autoincrement=False, nullable=False),
            sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
            sa.Column("formula_nombre", sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.Column("formula_base", sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.Column("formula_taux", sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=True),
            sa.ForeignKeyConstraint(["employer_id"], ["employers.id"], name=op.f("employer_primes_employer_id_fkey")),
            sa.PrimaryKeyConstraint("id", name=op.f("employer_primes_pkey")),
        )
        op.create_index(op.f("ix_employer_primes_id"), "employer_primes", ["id"], unique=False)
