"""add_employee_portal_people_ops_tables

Revision ID: e3b7a9c4d511
Revises: c4f7d9a1b234
Create Date: 2026-03-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b7a9c4d511"
down_revision: Union[str, Sequence[str], None] = "c4f7d9a1b234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "employee_portal_requests"):
        op.create_table(
            "employee_portal_requests",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("request_type", sa.String(length=50), nullable=False),
            sa.Column("destination", sa.String(length=50), nullable=False, server_default="rh"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="submitted"),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
            sa.Column("confidentiality", sa.String(length=50), nullable=False, server_default="standard"),
            sa.Column("case_number", sa.String(length=100), nullable=True, unique=True),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("history_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "employee_portal_requests") and not _has_index(inspector, "employee_portal_requests", "ix_employee_portal_requests_queue"):
        op.create_index("ix_employee_portal_requests_queue", "employee_portal_requests", ["employer_id", "destination", "status", "priority"], unique=False)

    if not _has_table(inspector, "inspector_cases"):
        op.create_table(
            "inspector_cases",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("case_number", sa.String(length=100), nullable=False, unique=True),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("custom_contracts.id"), nullable=True),
            sa.Column("portal_request_id", sa.Integer(), sa.ForeignKey("employee_portal_requests.id"), nullable=True),
            sa.Column("filed_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("assigned_inspector_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("case_type", sa.String(length=50), nullable=False, server_default="general_claim"),
            sa.Column("source_party", sa.String(length=50), nullable=False, server_default="employee"),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="received"),
            sa.Column("confidentiality", sa.String(length=50), nullable=False, server_default="standard"),
            sa.Column("amicable_attempt_status", sa.String(length=50), nullable=False, server_default="not_started"),
            sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="filing"),
            sa.Column("receipt_reference", sa.String(length=100), nullable=True),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("last_response_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspector_cases") and not _has_index(inspector, "inspector_cases", "ix_inspector_cases_queue"):
        op.create_index("ix_inspector_cases_queue", "inspector_cases", ["employer_id", "status", "current_stage", "updated_at"], unique=False)

    if not _has_table(inspector, "inspector_messages"):
        op.create_table(
            "inspector_messages",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("sender_role", sa.String(length=50), nullable=False, server_default="employee"),
            sa.Column("direction", sa.String(length=50), nullable=False, server_default="employee_to_inspector"),
            sa.Column("message_type", sa.String(length=50), nullable=False, server_default="message"),
            sa.Column("visibility", sa.String(length=50), nullable=False, server_default="case_parties"),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="sent"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspector_messages") and not _has_index(inspector, "inspector_messages", "ix_inspector_messages_case_created"):
        op.create_index("ix_inspector_messages_case_created", "inspector_messages", ["case_id", "created_at"], unique=False)

    if not _has_table(inspector, "workforce_job_profiles"):
        op.create_table(
            "workforce_job_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("department", sa.String(length=255), nullable=True),
            sa.Column("category_prof", sa.String(length=255), nullable=True),
            sa.Column("classification_index", sa.String(length=100), nullable=True),
            sa.Column("criticality", sa.String(length=50), nullable=False, server_default="medium"),
            sa.Column("target_headcount", sa.Integer(), nullable=True),
            sa.Column("required_skills_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("mobility_paths_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("succession_candidates_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("employer_id", "title", "department", name="uq_workforce_job_profiles_title_department"),
        )

    if not _has_table(inspector, "performance_cycles"):
        op.create_table(
            "performance_cycles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("cycle_type", sa.String(length=50), nullable=False, server_default="annual"),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("objectives_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "performance_reviews"):
        op.create_table(
            "performance_reviews",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("performance_cycles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
            sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("manager_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("self_assessment", sa.Text(), nullable=True),
            sa.Column("manager_comment", sa.Text(), nullable=True),
            sa.Column("hr_comment", sa.Text(), nullable=True),
            sa.Column("objectives_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("competencies_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("development_actions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("promotion_recommendation", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("cycle_id", "worker_id", name="uq_performance_review_cycle_worker"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "performance_reviews") and not _has_index(inspector, "performance_reviews", "ix_performance_reviews_queue"):
        op.create_index("ix_performance_reviews_queue", "performance_reviews", ["employer_id", "status", "updated_at"], unique=False)

    if not _has_table(inspector, "workforce_planning"):
        op.create_table(
            "workforce_planning",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("job_profile_id", sa.Integer(), sa.ForeignKey("workforce_job_profiles.id"), nullable=True),
            sa.Column("planning_year", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("current_headcount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("target_headcount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("recruitment_need", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mobility_need", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("criticality", sa.String(length=50), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("assumptions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "training_needs"):
        op.create_table(
            "training_needs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("performance_reviews.id"), nullable=True),
            sa.Column("job_profile_id", sa.Integer(), sa.ForeignKey("workforce_job_profiles.id"), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="gpec"),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("target_skill", sa.String(length=255), nullable=True),
            sa.Column("gap_level", sa.Integer(), nullable=True),
            sa.Column("recommended_training_id", sa.Integer(), sa.ForeignKey("talent_trainings.id"), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="identified"),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "training_plans"):
        op.create_table(
            "training_plans",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("plan_year", sa.Integer(), nullable=False),
            sa.Column("budget_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("objectives_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("fmfp_tracking_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("employer_id", "name", "plan_year", name="uq_training_plan_name_year"),
        )

    if not _has_table(inspector, "training_plan_items"):
        op.create_table(
            "training_plan_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("training_plan_id", sa.Integer(), sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("need_id", sa.Integer(), sa.ForeignKey("training_needs.id"), nullable=True),
            sa.Column("training_id", sa.Integer(), sa.ForeignKey("talent_trainings.id"), nullable=True),
            sa.Column("training_session_id", sa.Integer(), sa.ForeignKey("talent_training_sessions.id"), nullable=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="planned"),
            sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0"),
            sa.Column("funding_source", sa.String(length=100), nullable=True),
            sa.Column("fmfp_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("scheduled_start", sa.Date(), nullable=True),
            sa.Column("scheduled_end", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "training_evaluations"):
        op.create_table(
            "training_evaluations",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("training_session_id", sa.Integer(), sa.ForeignKey("talent_training_sessions.id"), nullable=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
            sa.Column("evaluation_type", sa.String(length=50), nullable=False, server_default="hot"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("impact_level", sa.String(length=50), nullable=True),
            sa.Column("comments", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "disciplinary_cases"):
        op.create_table(
            "disciplinary_cases",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
            sa.Column("inspection_case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("case_type", sa.String(length=50), nullable=False, server_default="warning"),
            sa.Column("severity", sa.String(length=50), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("happened_at", sa.DateTime(), nullable=True),
            sa.Column("hearing_at", sa.DateTime(), nullable=True),
            sa.Column("defense_notes", sa.Text(), nullable=True),
            sa.Column("sanction_type", sa.String(length=100), nullable=True),
            sa.Column("monetary_sanction_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("documents_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "termination_workflows"):
        op.create_table(
            "termination_workflows",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("custom_contracts.id"), nullable=True),
            sa.Column("inspection_case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("validated_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("termination_type", sa.String(length=50), nullable=False, server_default="resignation"),
            sa.Column("motif", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("sensitive_case", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("inspection_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("checklist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("documents_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "duer_entries"):
        op.create_table(
            "duer_entries",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("site_name", sa.String(length=255), nullable=False),
            sa.Column("risk_family", sa.String(length=255), nullable=False),
            sa.Column("hazard", sa.String(length=255), nullable=False),
            sa.Column("exposure_population", sa.String(length=255), nullable=True),
            sa.Column("probability", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("severity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("existing_controls", sa.Text(), nullable=True),
            sa.Column("residual_risk", sa.Integer(), nullable=True),
            sa.Column("owner_name", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
            sa.Column("last_reviewed_at", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "prevention_actions"):
        op.create_table(
            "prevention_actions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("duer_entry_id", sa.Integer(), sa.ForeignKey("duer_entries.id"), nullable=True),
            sa.Column("action_title", sa.String(length=255), nullable=False),
            sa.Column("action_type", sa.String(length=50), nullable=False, server_default="pap"),
            sa.Column("owner_name", sa.String(length=255), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="planned"),
            sa.Column("measure_details", sa.Text(), nullable=True),
            sa.Column("inspection_follow_up", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "prevention_actions"):
        op.drop_table("prevention_actions")
    if _has_table(inspector, "duer_entries"):
        op.drop_table("duer_entries")
    if _has_table(inspector, "termination_workflows"):
        op.drop_table("termination_workflows")
    if _has_table(inspector, "disciplinary_cases"):
        op.drop_table("disciplinary_cases")
    if _has_table(inspector, "training_evaluations"):
        op.drop_table("training_evaluations")
    if _has_table(inspector, "training_plan_items"):
        op.drop_table("training_plan_items")
    if _has_table(inspector, "training_plans"):
        op.drop_table("training_plans")
    if _has_table(inspector, "training_needs"):
        op.drop_table("training_needs")
    if _has_table(inspector, "workforce_planning"):
        op.drop_table("workforce_planning")
    if _has_table(inspector, "performance_reviews") and _has_index(inspector, "performance_reviews", "ix_performance_reviews_queue"):
        op.drop_index("ix_performance_reviews_queue", table_name="performance_reviews")
    if _has_table(inspector, "performance_reviews"):
        op.drop_table("performance_reviews")
    if _has_table(inspector, "performance_cycles"):
        op.drop_table("performance_cycles")
    if _has_table(inspector, "workforce_job_profiles"):
        op.drop_table("workforce_job_profiles")
    if _has_table(inspector, "inspector_messages") and _has_index(inspector, "inspector_messages", "ix_inspector_messages_case_created"):
        op.drop_index("ix_inspector_messages_case_created", table_name="inspector_messages")
    if _has_table(inspector, "inspector_messages"):
        op.drop_table("inspector_messages")
    if _has_table(inspector, "inspector_cases") and _has_index(inspector, "inspector_cases", "ix_inspector_cases_queue"):
        op.drop_index("ix_inspector_cases_queue", table_name="inspector_cases")
    if _has_table(inspector, "inspector_cases"):
        op.drop_table("inspector_cases")
    if _has_table(inspector, "employee_portal_requests") and _has_index(inspector, "employee_portal_requests", "ix_employee_portal_requests_queue"):
        op.drop_index("ix_employee_portal_requests_queue", table_name="employee_portal_requests")
    if _has_table(inspector, "employee_portal_requests"):
        op.drop_table("employee_portal_requests")
