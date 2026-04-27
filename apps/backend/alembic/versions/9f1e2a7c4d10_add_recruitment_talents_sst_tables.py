"""add_recruitment_talents_sst_tables

Revision ID: 9f1e2a7c4d10
Revises: 8c4b9d21e7aa
Create Date: 2026-03-19 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f1e2a7c4d10"
down_revision: Union[str, Sequence[str], None] = "8c4b9d21e7aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "recruitment_job_postings"):
        op.create_table(
            "recruitment_job_postings",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("department", sa.String(length=255), nullable=True),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("contract_type", sa.String(length=50), nullable=False, server_default="CDI"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("salary_range", sa.String(length=255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("skills_required", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_job_postings") and not _has_index(
        inspector, "recruitment_job_postings", "ix_recruitment_job_postings_employer_status"
    ):
        op.create_index(
            "ix_recruitment_job_postings_employer_status",
            "recruitment_job_postings",
            ["employer_id", "status"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_candidates"):
        op.create_table(
            "recruitment_candidates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("first_name", sa.String(length=120), nullable=False),
            sa.Column("last_name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=100), nullable=True),
            sa.Column("education_level", sa.String(length=120), nullable=True),
            sa.Column("experience_years", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("cv_file_path", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_candidates") and not _has_index(
        inspector, "recruitment_candidates", "ix_recruitment_candidates_employer_status"
    ):
        op.create_index(
            "ix_recruitment_candidates_employer_status",
            "recruitment_candidates",
            ["employer_id", "status"],
            unique=False,
        )

    if _has_table(inspector, "recruitment_candidates") and not _has_index(
        inspector, "recruitment_candidates", "ix_recruitment_candidates_email"
    ):
        op.create_index(
            "ix_recruitment_candidates_email",
            "recruitment_candidates",
            ["email"],
            unique=False,
        )

    if not _has_table(inspector, "recruitment_applications"):
        op.create_table(
            "recruitment_applications",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "job_posting_id",
                sa.Integer(),
                sa.ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "candidate_id",
                sa.Integer(),
                sa.ForeignKey("recruitment_candidates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("stage", sa.String(length=50), nullable=False, server_default="applied"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("job_posting_id", "candidate_id", name="uq_recruitment_job_candidate"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_applications") and not _has_index(
        inspector, "recruitment_applications", "ix_recruitment_applications_job_stage"
    ):
        op.create_index(
            "ix_recruitment_applications_job_stage",
            "recruitment_applications",
            ["job_posting_id", "stage"],
            unique=False,
        )

    if _has_table(inspector, "recruitment_applications") and not _has_index(
        inspector, "recruitment_applications", "ix_recruitment_applications_candidate_stage"
    ):
        op.create_index(
            "ix_recruitment_applications_candidate_stage",
            "recruitment_applications",
            ["candidate_id", "stage"],
            unique=False,
        )

    if not _has_table(inspector, "talent_skills"):
        op.create_table(
            "talent_skills",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("scale_max", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("employer_id", "code", name="uq_talent_skill_code"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "talent_skills") and not _has_index(
        inspector, "talent_skills", "ix_talent_skills_employer_active"
    ):
        op.create_index(
            "ix_talent_skills_employer_active",
            "talent_skills",
            ["employer_id", "is_active"],
            unique=False,
        )

    if not _has_table(inspector, "talent_employee_skills"):
        op.create_table(
            "talent_employee_skills",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("skill_id", sa.Integer(), sa.ForeignKey("talent_skills.id", ondelete="CASCADE"), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("source", sa.String(length=100), nullable=False, server_default="manager"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("worker_id", "skill_id", name="uq_talent_worker_skill"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "talent_employee_skills") and not _has_index(
        inspector, "talent_employee_skills", "ix_talent_employee_skills_worker_lookup"
    ):
        op.create_index(
            "ix_talent_employee_skills_worker_lookup",
            "talent_employee_skills",
            ["worker_id", "updated_at"],
            unique=False,
        )

    if not _has_table(inspector, "talent_trainings"):
        op.create_table(
            "talent_trainings",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("provider", sa.String(length=255), nullable=True),
            sa.Column("duration_hours", sa.Float(), nullable=False, server_default="0"),
            sa.Column("mode", sa.String(length=100), nullable=True),
            sa.Column("price", sa.Float(), nullable=False, server_default="0"),
            sa.Column("objectives", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "talent_trainings") and not _has_index(
        inspector, "talent_trainings", "ix_talent_trainings_employer_status"
    ):
        op.create_index(
            "ix_talent_trainings_employer_status",
            "talent_trainings",
            ["employer_id", "status"],
            unique=False,
        )

    if not _has_table(inspector, "talent_training_sessions"):
        op.create_table(
            "talent_training_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "training_id",
                sa.Integer(),
                sa.ForeignKey("talent_trainings.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("site", sa.String(length=255), nullable=True),
            sa.Column("trainer", sa.String(length=255), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="planned"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "talent_training_sessions") and not _has_index(
        inspector, "talent_training_sessions", "ix_talent_training_sessions_training_start"
    ):
        op.create_index(
            "ix_talent_training_sessions_training_start",
            "talent_training_sessions",
            ["training_id", "start_date"],
            unique=False,
        )

    if not _has_table(inspector, "sst_incidents"):
        op.create_table(
            "sst_incidents",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("incident_type", sa.String(length=100), nullable=False),
            sa.Column("severity", sa.String(length=50), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("action_taken", sa.Text(), nullable=True),
            sa.Column("witnesses", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "sst_incidents") and not _has_index(
        inspector, "sst_incidents", "ix_sst_incidents_employer_status_occurred"
    ):
        op.create_index(
            "ix_sst_incidents_employer_status_occurred",
            "sst_incidents",
            ["employer_id", "status", "occurred_at"],
            unique=False,
        )

    if _has_table(inspector, "sst_incidents") and not _has_index(
        inspector, "sst_incidents", "ix_sst_incidents_worker_occurred"
    ):
        op.create_index(
            "ix_sst_incidents_worker_occurred",
            "sst_incidents",
            ["worker_id", "occurred_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "sst_incidents") and _has_index(
        inspector, "sst_incidents", "ix_sst_incidents_worker_occurred"
    ):
        op.drop_index("ix_sst_incidents_worker_occurred", table_name="sst_incidents")

    if _has_table(inspector, "sst_incidents") and _has_index(
        inspector, "sst_incidents", "ix_sst_incidents_employer_status_occurred"
    ):
        op.drop_index("ix_sst_incidents_employer_status_occurred", table_name="sst_incidents")

    if _has_table(inspector, "sst_incidents"):
        op.drop_table("sst_incidents")

    if _has_table(inspector, "talent_training_sessions") and _has_index(
        inspector, "talent_training_sessions", "ix_talent_training_sessions_training_start"
    ):
        op.drop_index("ix_talent_training_sessions_training_start", table_name="talent_training_sessions")

    if _has_table(inspector, "talent_training_sessions"):
        op.drop_table("talent_training_sessions")

    if _has_table(inspector, "talent_trainings") and _has_index(
        inspector, "talent_trainings", "ix_talent_trainings_employer_status"
    ):
        op.drop_index("ix_talent_trainings_employer_status", table_name="talent_trainings")

    if _has_table(inspector, "talent_trainings"):
        op.drop_table("talent_trainings")

    if _has_table(inspector, "talent_employee_skills") and _has_index(
        inspector, "talent_employee_skills", "ix_talent_employee_skills_worker_lookup"
    ):
        op.drop_index("ix_talent_employee_skills_worker_lookup", table_name="talent_employee_skills")

    if _has_table(inspector, "talent_employee_skills"):
        op.drop_table("talent_employee_skills")

    if _has_table(inspector, "talent_skills") and _has_index(
        inspector, "talent_skills", "ix_talent_skills_employer_active"
    ):
        op.drop_index("ix_talent_skills_employer_active", table_name="talent_skills")

    if _has_table(inspector, "talent_skills"):
        op.drop_table("talent_skills")

    if _has_table(inspector, "recruitment_applications") and _has_index(
        inspector, "recruitment_applications", "ix_recruitment_applications_candidate_stage"
    ):
        op.drop_index("ix_recruitment_applications_candidate_stage", table_name="recruitment_applications")

    if _has_table(inspector, "recruitment_applications") and _has_index(
        inspector, "recruitment_applications", "ix_recruitment_applications_job_stage"
    ):
        op.drop_index("ix_recruitment_applications_job_stage", table_name="recruitment_applications")

    if _has_table(inspector, "recruitment_applications"):
        op.drop_table("recruitment_applications")

    if _has_table(inspector, "recruitment_candidates") and _has_index(
        inspector, "recruitment_candidates", "ix_recruitment_candidates_email"
    ):
        op.drop_index("ix_recruitment_candidates_email", table_name="recruitment_candidates")

    if _has_table(inspector, "recruitment_candidates") and _has_index(
        inspector, "recruitment_candidates", "ix_recruitment_candidates_employer_status"
    ):
        op.drop_index("ix_recruitment_candidates_employer_status", table_name="recruitment_candidates")

    if _has_table(inspector, "recruitment_candidates"):
        op.drop_table("recruitment_candidates")

    if _has_table(inspector, "recruitment_job_postings") and _has_index(
        inspector, "recruitment_job_postings", "ix_recruitment_job_postings_employer_status"
    ):
        op.drop_index("ix_recruitment_job_postings_employer_status", table_name="recruitment_job_postings")

    if _has_table(inspector, "recruitment_job_postings"):
        op.drop_table("recruitment_job_postings")
