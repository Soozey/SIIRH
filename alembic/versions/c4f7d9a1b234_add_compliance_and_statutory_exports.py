"""add_compliance_and_statutory_exports

Revision ID: c4f7d9a1b234
Revises: b1f0e6a71234
Create Date: 2026-03-20 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f7d9a1b234"
down_revision: Union[str, Sequence[str], None] = "b1f0e6a71234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "contract_versions"):
        op.create_table(
            "contract_versions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("custom_contracts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("source_module", sa.String(length=50), nullable=False, server_default="contracts"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("salary_amount", sa.Float(), nullable=True),
            sa.Column("classification_index", sa.String(length=100), nullable=True),
            sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("contract_id", "version_number", name="uq_contract_versions_contract_version"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "contract_versions") and not _has_index(inspector, "contract_versions", "ix_contract_versions_lookup"):
        op.create_index(
            "ix_contract_versions_lookup",
            "contract_versions",
            ["contract_id", "worker_id", "version_number", "status"],
            unique=False,
        )

    if not _has_table(inspector, "compliance_reviews"):
        op.create_table(
            "compliance_reviews",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("custom_contracts.id"), nullable=True),
            sa.Column("contract_version_id", sa.Integer(), sa.ForeignKey("contract_versions.id"), nullable=True),
            sa.Column("review_type", sa.String(length=50), nullable=False, server_default="contract_control"),
            sa.Column("review_stage", sa.String(length=50), nullable=False, server_default="pre_signature"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("source_module", sa.String(length=50), nullable=False, server_default="contracts"),
            sa.Column("checklist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("observations_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("requested_documents_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("submitted_to_inspector_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "compliance_reviews") and not _has_index(inspector, "compliance_reviews", "ix_compliance_reviews_queue"):
        op.create_index(
            "ix_compliance_reviews_queue",
            "compliance_reviews",
            ["employer_id", "status", "review_stage", "updated_at"],
            unique=False,
        )

    if not _has_table(inspector, "inspector_observations"):
        op.create_table(
            "inspector_observations",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("compliance_reviews.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("visibility", sa.String(length=50), nullable=False, server_default="restricted"),
            sa.Column("observation_type", sa.String(length=50), nullable=False, server_default="general"),
            sa.Column("status_marker", sa.String(length=50), nullable=False, server_default="observation"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("structured_payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspector_observations") and not _has_index(inspector, "inspector_observations", "ix_inspector_observations_review"):
        op.create_index(
            "ix_inspector_observations_review",
            "inspector_observations",
            ["review_id", "created_at", "status_marker"],
            unique=False,
        )

    if not _has_table(inspector, "compliance_visits"):
        op.create_table(
            "compliance_visits",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("compliance_reviews.id"), nullable=True),
            sa.Column("visit_type", sa.String(length=50), nullable=False, server_default="inspection"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="scheduled"),
            sa.Column("inspector_name", sa.String(length=255), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(), nullable=True),
            sa.Column("occurred_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "compliance_visits") and not _has_index(inspector, "compliance_visits", "ix_compliance_visits_schedule"):
        op.create_index(
            "ix_compliance_visits_schedule",
            "compliance_visits",
            ["employer_id", "scheduled_at", "status"],
            unique=False,
        )

    if not _has_table(inspector, "employer_register_entries"):
        op.create_table(
            "employer_register_entries",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("custom_contracts.id"), nullable=True),
            sa.Column("contract_version_id", sa.Integer(), sa.ForeignKey("contract_versions.id"), nullable=True),
            sa.Column("entry_type", sa.String(length=50), nullable=False, server_default="employer_register"),
            sa.Column("registry_label", sa.String(length=255), nullable=False, server_default="Registre employeur"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("employer_id", "entry_type", "worker_id", "contract_id", name="uq_employer_register_entry_scope"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "employer_register_entries") and not _has_index(inspector, "employer_register_entries", "ix_employer_register_entries_lookup"):
        op.create_index(
            "ix_employer_register_entries_lookup",
            "employer_register_entries",
            ["employer_id", "entry_type", "status", "effective_date"],
            unique=False,
        )

    if not _has_table(inspector, "export_templates"):
        op.create_table(
            "export_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("type_document", sa.String(length=100), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=False, server_default="1.0"),
            sa.Column("format", sa.String(length=20), nullable=False, server_default="xlsx"),
            sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("options_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_export_templates_code"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "export_templates") and not _has_index(inspector, "export_templates", "ix_export_templates_type_active"):
        op.create_index(
            "ix_export_templates_type_active",
            "export_templates",
            ["type_document", "is_active", "format"],
            unique=False,
        )

    if not _has_table(inspector, "reporting_snapshots"):
        op.create_table(
            "reporting_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("snapshot_type", sa.String(length=100), nullable=False),
            sa.Column("start_period", sa.String(length=7), nullable=False),
            sa.Column("end_period", sa.String(length=7), nullable=False),
            sa.Column("source_hash", sa.String(length=128), nullable=True),
            sa.Column("data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "reporting_snapshots") and not _has_index(inspector, "reporting_snapshots", "ix_reporting_snapshots_lookup"):
        op.create_index(
            "ix_reporting_snapshots_lookup",
            "reporting_snapshots",
            ["employer_id", "snapshot_type", "start_period", "end_period"],
            unique=False,
        )

    if not _has_table(inspector, "export_jobs"):
        op.create_table(
            "export_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("export_templates.id"), nullable=True),
            sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("reporting_snapshots.id"), nullable=True),
            sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("document_type", sa.String(length=100), nullable=False),
            sa.Column("start_period", sa.String(length=7), nullable=False),
            sa.Column("end_period", sa.String(length=7), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("file_path", sa.String(length=500), nullable=True),
            sa.Column("checksum", sa.String(length=128), nullable=True),
            sa.Column("logs_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("errors_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "export_jobs") and not _has_index(inspector, "export_jobs", "ix_export_jobs_lookup"):
        op.create_index(
            "ix_export_jobs_lookup",
            "export_jobs",
            ["employer_id", "document_type", "status", "created_at"],
            unique=False,
        )

    if not _has_table(inspector, "statutory_declarations"):
        op.create_table(
            "statutory_declarations",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("export_job_id", sa.Integer(), sa.ForeignKey("export_jobs.id"), nullable=True),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("period_label", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="generated"),
            sa.Column("reference_number", sa.String(length=255), nullable=True),
            sa.Column("receipt_path", sa.String(length=500), nullable=True),
            sa.Column("totals_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "statutory_declarations") and not _has_index(inspector, "statutory_declarations", "ix_statutory_declarations_lookup"):
        op.create_index(
            "ix_statutory_declarations_lookup",
            "statutory_declarations",
            ["employer_id", "channel", "status", "updated_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "statutory_declarations") and _has_index(inspector, "statutory_declarations", "ix_statutory_declarations_lookup"):
        op.drop_index("ix_statutory_declarations_lookup", table_name="statutory_declarations")
    if _has_table(inspector, "statutory_declarations"):
        op.drop_table("statutory_declarations")

    if _has_table(inspector, "export_jobs") and _has_index(inspector, "export_jobs", "ix_export_jobs_lookup"):
        op.drop_index("ix_export_jobs_lookup", table_name="export_jobs")
    if _has_table(inspector, "export_jobs"):
        op.drop_table("export_jobs")

    if _has_table(inspector, "reporting_snapshots") and _has_index(inspector, "reporting_snapshots", "ix_reporting_snapshots_lookup"):
        op.drop_index("ix_reporting_snapshots_lookup", table_name="reporting_snapshots")
    if _has_table(inspector, "reporting_snapshots"):
        op.drop_table("reporting_snapshots")

    if _has_table(inspector, "export_templates") and _has_index(inspector, "export_templates", "ix_export_templates_type_active"):
        op.drop_index("ix_export_templates_type_active", table_name="export_templates")
    if _has_table(inspector, "export_templates"):
        op.drop_table("export_templates")

    if _has_table(inspector, "employer_register_entries") and _has_index(inspector, "employer_register_entries", "ix_employer_register_entries_lookup"):
        op.drop_index("ix_employer_register_entries_lookup", table_name="employer_register_entries")
    if _has_table(inspector, "employer_register_entries"):
        op.drop_table("employer_register_entries")

    if _has_table(inspector, "compliance_visits") and _has_index(inspector, "compliance_visits", "ix_compliance_visits_schedule"):
        op.drop_index("ix_compliance_visits_schedule", table_name="compliance_visits")
    if _has_table(inspector, "compliance_visits"):
        op.drop_table("compliance_visits")

    if _has_table(inspector, "inspector_observations") and _has_index(inspector, "inspector_observations", "ix_inspector_observations_review"):
        op.drop_index("ix_inspector_observations_review", table_name="inspector_observations")
    if _has_table(inspector, "inspector_observations"):
        op.drop_table("inspector_observations")

    if _has_table(inspector, "compliance_reviews") and _has_index(inspector, "compliance_reviews", "ix_compliance_reviews_queue"):
        op.drop_index("ix_compliance_reviews_queue", table_name="compliance_reviews")
    if _has_table(inspector, "compliance_reviews"):
        op.drop_table("compliance_reviews")

    if _has_table(inspector, "contract_versions") and _has_index(inspector, "contract_versions", "ix_contract_versions_lookup"):
        op.drop_index("ix_contract_versions_lookup", table_name="contract_versions")
    if _has_table(inspector, "contract_versions"):
        op.drop_table("contract_versions")
