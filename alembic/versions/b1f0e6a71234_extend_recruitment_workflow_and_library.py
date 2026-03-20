"""extend_recruitment_workflow_and_library

Revision ID: b1f0e6a71234
Revises: 9f1e2a7c4d10
Create Date: 2026-03-19 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1f0e6a71234"
down_revision: Union[str, Sequence[str], None] = "9f1e2a7c4d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "recruitment_library_items"):
        op.create_table(
            "recruitment_library_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=True),
            sa.Column("category", sa.String(length=100), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("normalized_key", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("employer_id", "category", "normalized_key", name="uq_recruitment_library_scope_key"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_library_items") and not _has_index(
        inspector, "recruitment_library_items", "ix_recruitment_library_items_scope_lookup"
    ):
        op.create_index(
            "ix_recruitment_library_items_scope_lookup",
            "recruitment_library_items",
            ["category", "employer_id", "normalized_key"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_job_profiles"):
        op.create_table(
            "recruitment_job_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("job_posting_id", sa.Integer(), sa.ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("manager_title", sa.String(length=255), nullable=True),
            sa.Column("mission_summary", sa.Text(), nullable=True),
            sa.Column("main_activities_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("technical_skills_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("behavioral_skills_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("education_level", sa.String(length=255), nullable=True),
            sa.Column("experience_required", sa.String(length=255), nullable=True),
            sa.Column("languages_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("tools_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("certifications_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("salary_min", sa.Float(), nullable=True),
            sa.Column("salary_max", sa.Float(), nullable=True),
            sa.Column("working_hours", sa.String(length=255), nullable=True),
            sa.Column("benefits_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("desired_start_date", sa.Date(), nullable=True),
            sa.Column("application_deadline", sa.Date(), nullable=True),
            sa.Column("publication_channels_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("classification", sa.String(length=255), nullable=True),
            sa.Column("workflow_status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("validation_comment", sa.Text(), nullable=True),
            sa.Column("validated_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            sa.Column("assistant_source_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("interview_criteria_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("announcement_title", sa.String(length=255), nullable=True),
            sa.Column("announcement_body", sa.Text(), nullable=True),
            sa.Column("announcement_status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("announcement_slug", sa.String(length=255), nullable=True),
            sa.Column("announcement_share_pack_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("job_posting_id"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_job_profiles") and not _has_index(
        inspector, "recruitment_job_profiles", "ix_recruitment_job_profiles_status"
    ):
        op.create_index(
            "ix_recruitment_job_profiles_status",
            "recruitment_job_profiles",
            ["job_posting_id", "workflow_status", "announcement_status"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_candidate_assets"):
        op.create_table(
            "recruitment_candidate_assets",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("recruitment_candidates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("resume_original_name", sa.String(length=255), nullable=True),
            sa.Column("resume_storage_path", sa.String(length=500), nullable=True),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("raw_extract_text", sa.Text(), nullable=True),
            sa.Column("parsed_profile_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("parsing_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("candidate_id"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_candidate_assets") and not _has_index(
        inspector, "recruitment_candidate_assets", "ix_recruitment_candidate_assets_status"
    ):
        op.create_index(
            "ix_recruitment_candidate_assets_status",
            "recruitment_candidate_assets",
            ["candidate_id", "parsing_status"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_interviews"):
        op.create_table(
            "recruitment_interviews",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("application_id", sa.Integer(), sa.ForeignKey("recruitment_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("round_label", sa.String(length=100), nullable=False, server_default="Tour 1"),
            sa.Column("interview_type", sa.String(length=100), nullable=False, server_default="entretien"),
            sa.Column("scheduled_at", sa.DateTime(), nullable=True),
            sa.Column("interviewer_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("interviewer_name", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="scheduled"),
            sa.Column("score_total", sa.Float(), nullable=True),
            sa.Column("scorecard_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("recommendation", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_interviews") and not _has_index(
        inspector, "recruitment_interviews", "ix_recruitment_interviews_schedule"
    ):
        op.create_index(
            "ix_recruitment_interviews_schedule",
            "recruitment_interviews",
            ["application_id", "scheduled_at", "status"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_decisions"):
        op.create_table(
            "recruitment_decisions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("application_id", sa.Integer(), sa.ForeignKey("recruitment_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("shortlist_rank", sa.Integer(), nullable=True),
            sa.Column("decision_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("decision_comment", sa.Text(), nullable=True),
            sa.Column("decided_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("converted_worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("contract_draft_id", sa.Integer(), sa.ForeignKey("custom_contracts.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("application_id"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_decisions") and not _has_index(
        inspector, "recruitment_decisions", "ix_recruitment_decisions_lookup"
    ):
        op.create_index(
            "ix_recruitment_decisions_lookup",
            "recruitment_decisions",
            ["application_id", "decision_status", "shortlist_rank"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_activities"):
        op.create_table(
            "recruitment_activities",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("job_posting_id", sa.Integer(), sa.ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("recruitment_candidates.id", ondelete="CASCADE"), nullable=True),
            sa.Column("application_id", sa.Integer(), sa.ForeignKey("recruitment_applications.id", ondelete="CASCADE"), nullable=True),
            sa.Column("interview_id", sa.Integer(), sa.ForeignKey("recruitment_interviews.id", ondelete="CASCADE"), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("visibility", sa.String(length=50), nullable=False, server_default="internal"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_activities") and not _has_index(
        inspector, "recruitment_activities", "ix_recruitment_activities_timeline"
    ):
        op.create_index(
            "ix_recruitment_activities_timeline",
            "recruitment_activities",
            ["employer_id", "application_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "recruitment_activities") and _has_index(
        inspector, "recruitment_activities", "ix_recruitment_activities_timeline"
    ):
        op.drop_index("ix_recruitment_activities_timeline", table_name="recruitment_activities")
    if _has_table(inspector, "recruitment_activities"):
        op.drop_table("recruitment_activities")

    if _has_table(inspector, "recruitment_decisions") and _has_index(
        inspector, "recruitment_decisions", "ix_recruitment_decisions_lookup"
    ):
        op.drop_index("ix_recruitment_decisions_lookup", table_name="recruitment_decisions")
    if _has_table(inspector, "recruitment_decisions"):
        op.drop_table("recruitment_decisions")

    if _has_table(inspector, "recruitment_interviews") and _has_index(
        inspector, "recruitment_interviews", "ix_recruitment_interviews_schedule"
    ):
        op.drop_index("ix_recruitment_interviews_schedule", table_name="recruitment_interviews")
    if _has_table(inspector, "recruitment_interviews"):
        op.drop_table("recruitment_interviews")

    if _has_table(inspector, "recruitment_candidate_assets") and _has_index(
        inspector, "recruitment_candidate_assets", "ix_recruitment_candidate_assets_status"
    ):
        op.drop_index("ix_recruitment_candidate_assets_status", table_name="recruitment_candidate_assets")
    if _has_table(inspector, "recruitment_candidate_assets"):
        op.drop_table("recruitment_candidate_assets")

    if _has_table(inspector, "recruitment_job_profiles") and _has_index(
        inspector, "recruitment_job_profiles", "ix_recruitment_job_profiles_status"
    ):
        op.drop_index("ix_recruitment_job_profiles_status", table_name="recruitment_job_profiles")
    if _has_table(inspector, "recruitment_job_profiles"):
        op.drop_table("recruitment_job_profiles")

    if _has_table(inspector, "recruitment_library_items") and _has_index(
        inspector, "recruitment_library_items", "ix_recruitment_library_items_scope_lookup"
    ):
        op.drop_index("ix_recruitment_library_items_scope_lookup", table_name="recruitment_library_items")
    if _has_table(inspector, "recruitment_library_items"):
        op.drop_table("recruitment_library_items")
