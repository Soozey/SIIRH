"""add_document_reporting_indexes

Revision ID: 8c4b9d21e7aa
Revises: 6a1f7c2d9b34
Create Date: 2026-03-19 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c4b9d21e7aa"
down_revision: Union[str, Sequence[str], None] = "6a1f7c2d9b34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "custom_contracts") and not _has_index(
        inspector, "custom_contracts", "ix_custom_contracts_worker_template_default"
    ):
        op.create_index(
            "ix_custom_contracts_worker_template_default",
            "custom_contracts",
            ["worker_id", "template_type", "is_default"],
            unique=False,
        )

    if _has_table(inspector, "custom_contracts") and not _has_index(
        inspector, "custom_contracts", "ix_custom_contracts_employer_template"
    ):
        op.create_index(
            "ix_custom_contracts_employer_template",
            "custom_contracts",
            ["employer_id", "template_type"],
            unique=False,
        )

    if _has_table(inspector, "document_templates") and not _has_index(
        inspector, "document_templates", "ix_document_templates_employer_type_active"
    ):
        op.create_index(
            "ix_document_templates_employer_type_active",
            "document_templates",
            ["employer_id", "template_type", "is_active"],
            unique=False,
        )

    if _has_table(inspector, "audit_logs") and not _has_index(
        inspector, "audit_logs", "ix_audit_logs_entity_lookup"
    ):
        op.create_index(
            "ix_audit_logs_entity_lookup",
            "audit_logs",
            ["entity_type", "entity_id", "created_at"],
            unique=False,
        )

    if _has_table(inspector, "request_workflows") and not _has_index(
        inspector, "request_workflows", "ix_request_workflows_status_lookup"
    ):
        op.create_index(
            "ix_request_workflows_status_lookup",
            "request_workflows",
            ["request_type", "overall_status", "updated_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "request_workflows") and _has_index(
        inspector, "request_workflows", "ix_request_workflows_status_lookup"
    ):
        op.drop_index("ix_request_workflows_status_lookup", table_name="request_workflows")

    if _has_table(inspector, "audit_logs") and _has_index(
        inspector, "audit_logs", "ix_audit_logs_entity_lookup"
    ):
        op.drop_index("ix_audit_logs_entity_lookup", table_name="audit_logs")

    if _has_table(inspector, "document_templates") and _has_index(
        inspector, "document_templates", "ix_document_templates_employer_type_active"
    ):
        op.drop_index("ix_document_templates_employer_type_active", table_name="document_templates")

    if _has_table(inspector, "custom_contracts") and _has_index(
        inspector, "custom_contracts", "ix_custom_contracts_employer_template"
    ):
        op.drop_index("ix_custom_contracts_employer_template", table_name="custom_contracts")

    if _has_table(inspector, "custom_contracts") and _has_index(
        inspector, "custom_contracts", "ix_custom_contracts_worker_template_default"
    ):
        op.drop_index("ix_custom_contracts_worker_template_default", table_name="custom_contracts")
