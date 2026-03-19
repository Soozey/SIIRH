"""add_contribution_fields_to_employer

Revision ID: 623602fbeca1
Revises: 000000000000
Create Date: 2025-11-20 10:00:01.247758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "623602fbeca1"
down_revision: Union[str, Sequence[str], None] = "000000000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "employers"):
        return

    columns = [
        ("taux_sal_cnaps", sa.Column("taux_sal_cnaps", sa.Float(), server_default="1.0", nullable=True)),
        ("plafond_cnaps_base", sa.Column("plafond_cnaps_base", sa.Float(), server_default="0.0", nullable=True)),
        ("taux_pat_fmfp", sa.Column("taux_pat_fmfp", sa.Float(), server_default="1.0", nullable=True)),
        ("taux_sal_smie", sa.Column("taux_sal_smie", sa.Float(), server_default="0.0", nullable=True)),
        ("smie_forfait_sal", sa.Column("smie_forfait_sal", sa.Float(), server_default="0.0", nullable=True)),
        ("smie_forfait_pat", sa.Column("smie_forfait_pat", sa.Float(), server_default="0.0", nullable=True)),
    ]

    for column_name, column in columns:
        if not _has_column(inspector, "employers", column_name):
            op.add_column("employers", column)
            inspector = sa.inspect(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "employers"):
        return

    for column_name in [
        "smie_forfait_pat",
        "smie_forfait_sal",
        "taux_sal_smie",
        "taux_pat_fmfp",
        "plafond_cnaps_base",
        "taux_sal_cnaps",
    ]:
        if _has_column(inspector, "employers", column_name):
            op.drop_column("employers", column_name)
            inspector = sa.inspect(bind)
