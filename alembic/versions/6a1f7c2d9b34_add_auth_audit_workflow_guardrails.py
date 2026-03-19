"""add_auth_audit_workflow_guardrails

Revision ID: 6a1f7c2d9b34
Revises: 3f5376309957, 11bfecd7a411
Create Date: 2026-03-19 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a1f7c2d9b34"
down_revision: Union[str, Sequence[str], None] = ("3f5376309957", "11bfecd7a411")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_constraint(inspector, table_name: str, constraint_name: str) -> bool:
    return any(constraint["name"] == constraint_name for constraint in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "app_users"):
        op.create_table(
            "app_users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role_code", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("employer_id", sa.Integer(), nullable=True),
            sa.Column("worker_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_app_users_id", "app_users", ["id"], unique=False)
        op.create_index("ix_app_users_username", "app_users", ["username"], unique=True)
        op.create_index("ix_app_users_role_code", "app_users", ["role_code"], unique=False)
        op.create_index("ix_app_users_employer_id", "app_users", ["employer_id"], unique=False)
        op.create_index("ix_app_users_worker_id", "app_users", ["worker_id"], unique=False)

    if not _has_table(inspector, "auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"], unique=False)
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
        op.create_index("ix_auth_sessions_token", "auth_sessions", ["token"], unique=True)
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)

    if not _has_table(inspector, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_role", sa.String(length=50), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("entity_type", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.String(length=100), nullable=False),
            sa.Column("route", sa.String(length=255), nullable=True),
            sa.Column("employer_id", sa.Integer(), nullable=True),
            sa.Column("worker_id", sa.Integer(), nullable=True),
            sa.Column("before_json", sa.Text(), nullable=True),
            sa.Column("after_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["actor_user_id"], ["app_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
        op.create_index("ix_audit_logs_actor_role", "audit_logs", ["actor_role"], unique=False)
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
        op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
        op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
        op.create_index("ix_audit_logs_employer_id", "audit_logs", ["employer_id"], unique=False)
        op.create_index("ix_audit_logs_worker_id", "audit_logs", ["worker_id"], unique=False)
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    if not _has_table(inspector, "request_workflows"):
        op.create_table(
            "request_workflows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_type", sa.String(length=30), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("overall_status", sa.String(length=30), nullable=False, server_default="pending_manager"),
            sa.Column("manager_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("rh_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("manager_comment", sa.Text(), nullable=True),
            sa.Column("rh_comment", sa.Text(), nullable=True),
            sa.Column("manager_actor_user_id", sa.Integer(), nullable=True),
            sa.Column("rh_actor_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("request_type IN ('leave', 'permission')", name="chk_request_workflow_type"),
            sa.ForeignKeyConstraint(["manager_actor_user_id"], ["app_users.id"]),
            sa.ForeignKeyConstraint(["rh_actor_user_id"], ["app_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_request_workflows_id", "request_workflows", ["id"], unique=False)
        op.create_index("ix_request_workflows_request_type", "request_workflows", ["request_type"], unique=False)
        op.create_index("ix_request_workflows_request_id", "request_workflows", ["request_id"], unique=False)
        op.create_index("ix_request_workflows_overall_status", "request_workflows", ["overall_status"], unique=False)
        op.create_unique_constraint(
            "uq_request_workflow_request",
            "request_workflows",
            ["request_type", "request_id"],
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "workers") and not _has_index(inspector, "workers", "ix_workers_employer_id"):
        op.create_index("ix_workers_employer_id", "workers", ["employer_id"], unique=False)
    if _has_table(inspector, "workers") and not _has_index(inspector, "workers", "ix_workers_name_lookup"):
        op.create_index("ix_workers_name_lookup", "workers", ["nom", "prenom"], unique=False)
    if _has_table(inspector, "payroll_runs") and not _has_index(inspector, "payroll_runs", "ix_payroll_runs_employer_period"):
        op.create_index("ix_payroll_runs_employer_period", "payroll_runs", ["employer_id", "period"], unique=False)
    if _has_table(inspector, "leaves") and not _has_index(inspector, "leaves", "ix_leaves_worker_period"):
        op.create_index("ix_leaves_worker_period", "leaves", ["worker_id", "period"], unique=False)
    if _has_table(inspector, "permissions") and not _has_index(inspector, "permissions", "ix_permissions_worker_period"):
        op.create_index("ix_permissions_worker_period", "permissions", ["worker_id", "period"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "permissions") and _has_index(inspector, "permissions", "ix_permissions_worker_period"):
        op.drop_index("ix_permissions_worker_period", table_name="permissions")
    if _has_table(inspector, "leaves") and _has_index(inspector, "leaves", "ix_leaves_worker_period"):
        op.drop_index("ix_leaves_worker_period", table_name="leaves")
    if _has_table(inspector, "payroll_runs") and _has_index(inspector, "payroll_runs", "ix_payroll_runs_employer_period"):
        op.drop_index("ix_payroll_runs_employer_period", table_name="payroll_runs")
    if _has_table(inspector, "workers") and _has_index(inspector, "workers", "ix_workers_name_lookup"):
        op.drop_index("ix_workers_name_lookup", table_name="workers")
    if _has_table(inspector, "workers") and _has_index(inspector, "workers", "ix_workers_employer_id"):
        op.drop_index("ix_workers_employer_id", table_name="workers")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "request_workflows"):
        if _has_constraint(inspector, "request_workflows", "uq_request_workflow_request"):
            op.drop_constraint("uq_request_workflow_request", "request_workflows", type_="unique")
        for index_name in [
            "ix_request_workflows_overall_status",
            "ix_request_workflows_request_id",
            "ix_request_workflows_request_type",
            "ix_request_workflows_id",
        ]:
            if _has_index(inspector, "request_workflows", index_name):
                op.drop_index(index_name, table_name="request_workflows")
        op.drop_table("request_workflows")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "audit_logs"):
        for index_name in [
            "ix_audit_logs_created_at",
            "ix_audit_logs_worker_id",
            "ix_audit_logs_employer_id",
            "ix_audit_logs_entity_id",
            "ix_audit_logs_entity_type",
            "ix_audit_logs_action",
            "ix_audit_logs_actor_role",
            "ix_audit_logs_actor_user_id",
            "ix_audit_logs_id",
        ]:
            if _has_index(inspector, "audit_logs", index_name):
                op.drop_index(index_name, table_name="audit_logs")
        op.drop_table("audit_logs")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "auth_sessions"):
        for index_name in [
            "ix_auth_sessions_expires_at",
            "ix_auth_sessions_token",
            "ix_auth_sessions_user_id",
            "ix_auth_sessions_id",
        ]:
            if _has_index(inspector, "auth_sessions", index_name):
                op.drop_index(index_name, table_name="auth_sessions")
        op.drop_table("auth_sessions")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "app_users"):
        for index_name in [
            "ix_app_users_worker_id",
            "ix_app_users_employer_id",
            "ix_app_users_role_code",
            "ix_app_users_username",
            "ix_app_users_id",
        ]:
            if _has_index(inspector, "app_users", index_name):
                op.drop_index(index_name, table_name="app_users")
        op.drop_table("app_users")
