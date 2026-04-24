"""add_working_days_to_recruitment_profiles

Revision ID: 0f2c9d4a6b11
Revises: fa15b202604
Create Date: 2026-04-20 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f2c9d4a6b11"
down_revision: Union[str, Sequence[str], None] = "b7c9d4e2a113"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "recruitment_job_profiles", "working_days_json"):
        return

    with op.batch_alter_table("recruitment_job_profiles") as batch_op:
        batch_op.add_column(sa.Column("working_days_json", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "recruitment_job_profiles", "working_days_json"):
        return

    with op.batch_alter_table("recruitment_job_profiles") as batch_op:
        batch_op.drop_column("working_days_json")
