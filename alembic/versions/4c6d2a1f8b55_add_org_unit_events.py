"""add_org_unit_events

Revision ID: 4c6d2a1f8b55
Revises: 0f2c9d4a6b11
Create Date: 2026-04-20 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c6d2a1f8b55"
down_revision: Union[str, Sequence[str], None] = "0f2c9d4a6b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "org_unit_events"):
        return

    op.create_table(
        "org_unit_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
        sa.Column("org_unit_id", sa.Integer(), sa.ForeignKey("organizational_units.id"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_org_unit_events_employer_id", "org_unit_events", ["employer_id"], unique=False)
    op.create_index("ix_org_unit_events_org_unit_id", "org_unit_events", ["org_unit_id"], unique=False)
    op.create_index("ix_org_unit_events_event_type", "org_unit_events", ["event_type"], unique=False)
    op.create_index("ix_org_unit_events_created_at", "org_unit_events", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "org_unit_events"):
        return

    op.drop_index("ix_org_unit_events_created_at", table_name="org_unit_events")
    op.drop_index("ix_org_unit_events_event_type", table_name="org_unit_events")
    op.drop_index("ix_org_unit_events_org_unit_id", table_name="org_unit_events")
    op.drop_index("ix_org_unit_events_employer_id", table_name="org_unit_events")
    op.drop_table("org_unit_events")
