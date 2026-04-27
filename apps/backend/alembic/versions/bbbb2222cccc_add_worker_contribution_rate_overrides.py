"""add_worker_contribution_rate_overrides

Revision ID: bbbb2222cccc
Revises: 3e8a9d1b2c4f
Create Date: 2025-12-16 10:51:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "bbbb2222cccc"
down_revision = "3e8a9d1b2c4f"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" not in inspector.get_table_names():
        return

    for column_name in ["taux_sal_cnaps_override", "taux_sal_smie_override"]:
        if not _has_column(inspector, "workers", column_name):
            op.add_column("workers", sa.Column(column_name, sa.Float(), nullable=True))
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workers" not in inspector.get_table_names():
        return

    for column_name in ["taux_sal_smie_override", "taux_sal_cnaps_override"]:
        if _has_column(inspector, "workers", column_name):
            op.drop_column("workers", column_name)
            inspector = sa.inspect(bind)
