"""add_termination_legal_fields

Revision ID: fa15b202604
Revises: f6a7b8c9d012
Create Date: 2026-04-15 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fa15b202604"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "termination_workflows"
    if not _has_table(inspector, table_name):
        return

    additions = [
        ("notification_sent_at", sa.DateTime(), True),
        ("notification_received_at", sa.DateTime(), True),
        ("pre_hearing_notice_sent_at", sa.DateTime(), True),
        ("pre_hearing_scheduled_at", sa.DateTime(), True),
        ("preavis_start_date", sa.Date(), True),
        ("economic_consultation_started_at", sa.Date(), True),
        ("economic_inspection_referral_at", sa.Date(), True),
        ("technical_layoff_declared_at", sa.Date(), True),
        ("technical_layoff_end_at", sa.Date(), True),
        ("handover_required", sa.Boolean(), False),
        ("legal_risk_level", sa.String(length=50), False),
        ("legal_metadata_json", sa.Text(), False),
        ("readonly_stc_json", sa.Text(), False),
    ]

    for column_name, column_type, nullable in additions:
        inspector = sa.inspect(bind)
        if _has_column(inspector, table_name, column_name):
            continue
        server_default = None
        if column_name == "handover_required":
            server_default = sa.false()
        elif column_name == "legal_risk_level":
            server_default = sa.text("'normal'")
        elif column_name in {"legal_metadata_json", "readonly_stc_json"}:
            server_default = sa.text("'{}'")
        op.add_column(
            table_name,
            sa.Column(column_name, column_type, nullable=nullable, server_default=server_default),
        )

    index_specs = [
        ("ix_termination_workflows_notification_sent_at", ["notification_sent_at"]),
        ("ix_termination_workflows_notification_received_at", ["notification_received_at"]),
        ("ix_termination_workflows_pre_hearing_notice_sent_at", ["pre_hearing_notice_sent_at"]),
        ("ix_termination_workflows_pre_hearing_scheduled_at", ["pre_hearing_scheduled_at"]),
        ("ix_termination_workflows_preavis_start_date", ["preavis_start_date"]),
        ("ix_termination_workflows_economic_consultation_started_at", ["economic_consultation_started_at"]),
        ("ix_termination_workflows_economic_inspection_referral_at", ["economic_inspection_referral_at"]),
        ("ix_termination_workflows_technical_layoff_declared_at", ["technical_layoff_declared_at"]),
        ("ix_termination_workflows_technical_layoff_end_at", ["technical_layoff_end_at"]),
        ("ix_termination_workflows_handover_required", ["handover_required"]),
        ("ix_termination_workflows_legal_risk_level", ["legal_risk_level"]),
    ]
    inspector = sa.inspect(bind)
    for index_name, columns in index_specs:
        if not _has_index(inspector, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "termination_workflows"
    if not _has_table(inspector, table_name):
        return

    index_names = [
        "ix_termination_workflows_legal_risk_level",
        "ix_termination_workflows_handover_required",
        "ix_termination_workflows_technical_layoff_end_at",
        "ix_termination_workflows_technical_layoff_declared_at",
        "ix_termination_workflows_economic_inspection_referral_at",
        "ix_termination_workflows_economic_consultation_started_at",
        "ix_termination_workflows_preavis_start_date",
        "ix_termination_workflows_pre_hearing_scheduled_at",
        "ix_termination_workflows_pre_hearing_notice_sent_at",
        "ix_termination_workflows_notification_received_at",
        "ix_termination_workflows_notification_sent_at",
    ]
    for index_name in index_names:
        inspector = sa.inspect(bind)
        if _has_index(inspector, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    for column_name in [
        "readonly_stc_json",
        "legal_metadata_json",
        "legal_risk_level",
        "handover_required",
        "technical_layoff_end_at",
        "technical_layoff_declared_at",
        "economic_inspection_referral_at",
        "economic_consultation_started_at",
        "preavis_start_date",
        "pre_hearing_scheduled_at",
        "pre_hearing_notice_sent_at",
        "notification_received_at",
        "notification_sent_at",
    ]:
        inspector = sa.inspect(bind)
        if _has_column(inspector, table_name, column_name):
            op.drop_column(table_name, column_name)
