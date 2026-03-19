"""Add payroll_hs_hm table

Revision ID: f6522e96157e
Revises: 0565ed6dbe40
Create Date: 2025-12-08 22:23:33.600974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6522e96157e"
down_revision: Union[str, Sequence[str], None] = "0565ed6dbe40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "payroll_hs_hm"):
        op.create_table(
            "payroll_hs_hm",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("payroll_run_id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.Integer(), nullable=False),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("hs_calculation_id", sa.Integer(), nullable=True),
            sa.Column("import_file_name", sa.String(length=255), nullable=True),
            sa.Column("hsni_130_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hsi_130_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hsni_150_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hsi_150_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hmnh_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hmno_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hmd_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hmjf_heures", sa.Numeric(precision=10, scale=2), server_default="0"),
            sa.Column("hsni_130_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hsi_130_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hsni_150_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hsi_150_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hmnh_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hmno_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hmd_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("hmjf_montant", sa.Numeric(precision=15, scale=2), server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["hs_calculation_id"], ["hs_calculations_HS.id_HS"]),
            sa.ForeignKeyConstraint(["payroll_run_id"], ["payroll_runs.id"]),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("payroll_run_id", "worker_id", name="uq_payroll_worker_hs_hm"),
        )
        inspector = sa.inspect(bind)

    if _has_table(inspector, "payroll_hs_hm") and not _has_index(inspector, "payroll_hs_hm", op.f("ix_payroll_hs_hm_id")):
        op.create_index(op.f("ix_payroll_hs_hm_id"), "payroll_hs_hm", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_table(inspector, "payroll_hs_hm") and _has_index(inspector, "payroll_hs_hm", op.f("ix_payroll_hs_hm_id")):
        op.drop_index(op.f("ix_payroll_hs_hm_id"), table_name="payroll_hs_hm")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "payroll_hs_hm"):
        op.drop_table("payroll_hs_hm")
