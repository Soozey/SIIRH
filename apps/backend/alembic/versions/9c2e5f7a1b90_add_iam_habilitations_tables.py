"""add_iam_habilitations_tables

Revision ID: 9c2e5f7a1b90
Revises: f6a7b8c9d012
Create Date: 2026-04-04 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c2e5f7a1b90"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "iam_roles"):
        op.create_table(
            "iam_roles",
            sa.Column("code", sa.String(length=80), primary_key=True, nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("scope", sa.String(length=80), nullable=False, server_default="company"),
            sa.Column("base_role_code", sa.String(length=80), nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_roles"):
        if not _has_index(inspector, "iam_roles", "ix_iam_roles_is_system"):
            op.create_index("ix_iam_roles_is_system", "iam_roles", ["is_system"], unique=False)
        if not _has_index(inspector, "iam_roles", "ix_iam_roles_is_active"):
            op.create_index("ix_iam_roles_is_active", "iam_roles", ["is_active"], unique=False)

    if not _has_table(inspector, "iam_permissions"):
        op.create_table(
            "iam_permissions",
            sa.Column("code", sa.String(length=120), primary_key=True, nullable=False),
            sa.Column("module", sa.String(length=80), nullable=False),
            sa.Column("action", sa.String(length=30), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("sensitivity", sa.String(length=80), nullable=False, server_default="base"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "action IN ('read', 'create', 'write', 'validate', 'approve', 'close', 'export', 'print', 'document', 'delete', 'admin')",
                name="chk_iam_permission_action",
            ),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_permissions"):
        if not _has_index(inspector, "iam_permissions", "ix_iam_permissions_module"):
            op.create_index("ix_iam_permissions_module", "iam_permissions", ["module"], unique=False)
        if not _has_index(inspector, "iam_permissions", "ix_iam_permissions_action"):
            op.create_index("ix_iam_permissions_action", "iam_permissions", ["action"], unique=False)

    if not _has_table(inspector, "iam_role_permissions"):
        op.create_table(
            "iam_role_permissions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("role_code", sa.String(length=80), sa.ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_code", sa.String(length=120), sa.ForeignKey("iam_permissions.code", ondelete="CASCADE"), nullable=False),
            sa.Column("is_granted", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("role_code", "permission_code", name="uq_iam_role_permission"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_role_permissions"):
        if not _has_index(inspector, "iam_role_permissions", "ix_iam_role_permissions_role_code"):
            op.create_index("ix_iam_role_permissions_role_code", "iam_role_permissions", ["role_code"], unique=False)
        if not _has_index(inspector, "iam_role_permissions", "ix_iam_role_permissions_permission_code"):
            op.create_index("ix_iam_role_permissions_permission_code", "iam_role_permissions", ["permission_code"], unique=False)
        if not _has_index(inspector, "iam_role_permissions", "ix_iam_role_permissions_role_grant"):
            op.create_index("ix_iam_role_permissions_role_grant", "iam_role_permissions", ["role_code", "is_granted"], unique=False)

    if not _has_table(inspector, "iam_role_activations"):
        op.create_table(
            "iam_role_activations",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("scope_key", sa.String(length=100), nullable=False, server_default="installation"),
            sa.Column("role_code", sa.String(length=80), sa.ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("scope_key", "role_code", name="uq_iam_role_activation_scope"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_role_activations"):
        if not _has_index(inspector, "iam_role_activations", "ix_iam_role_activations_scope_key"):
            op.create_index("ix_iam_role_activations_scope_key", "iam_role_activations", ["scope_key"], unique=False)
        if not _has_index(inspector, "iam_role_activations", "ix_iam_role_activations_role_code"):
            op.create_index("ix_iam_role_activations_role_code", "iam_role_activations", ["role_code"], unique=False)
        if not _has_index(inspector, "iam_role_activations", "ix_iam_role_activations_is_enabled"):
            op.create_index("ix_iam_role_activations_is_enabled", "iam_role_activations", ["is_enabled"], unique=False)
        if not _has_index(inspector, "iam_role_activations", "ix_iam_role_activations_updated_by_user_id"):
            op.create_index("ix_iam_role_activations_updated_by_user_id", "iam_role_activations", ["updated_by_user_id"], unique=False)

    if not _has_table(inspector, "iam_user_roles"):
        op.create_table(
            "iam_user_roles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_code", sa.String(length=80), sa.ForeignKey("iam_roles.code", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("valid_from", sa.DateTime(), nullable=True),
            sa.Column("valid_until", sa.DateTime(), nullable=True),
            sa.Column("delegated_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "role_code", "employer_id", "worker_id", name="uq_iam_user_role_scope"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_user_roles"):
        for index_name, columns in [
            ("ix_iam_user_roles_user_id", ["user_id"]),
            ("ix_iam_user_roles_role_code", ["role_code"]),
            ("ix_iam_user_roles_employer_id", ["employer_id"]),
            ("ix_iam_user_roles_worker_id", ["worker_id"]),
            ("ix_iam_user_roles_is_active", ["is_active"]),
            ("ix_iam_user_roles_valid_until", ["valid_until"]),
            ("ix_iam_user_roles_delegated_by_user_id", ["delegated_by_user_id"]),
            ("ix_iam_user_roles_user_active", ["user_id", "is_active", "valid_until"]),
        ]:
            if not _has_index(inspector, "iam_user_roles", index_name):
                op.create_index(index_name, "iam_user_roles", columns, unique=False)

    if not _has_table(inspector, "iam_user_permission_overrides"):
        op.create_table(
            "iam_user_permission_overrides",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_code", sa.String(length=120), sa.ForeignKey("iam_permissions.code", ondelete="CASCADE"), nullable=False),
            sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "permission_code", name="uq_iam_user_permission_override"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_user_permission_overrides"):
        for index_name, columns in [
            ("ix_iam_user_permission_overrides_user_id", ["user_id"]),
            ("ix_iam_user_permission_overrides_permission_code", ["permission_code"]),
            ("ix_iam_user_permission_overrides_expires_at", ["expires_at"]),
            ("ix_iam_user_permission_overrides_updated_by_user_id", ["updated_by_user_id"]),
        ]:
            if not _has_index(inspector, "iam_user_permission_overrides", index_name):
                op.create_index(index_name, "iam_user_permission_overrides", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "iam_user_permission_overrides"):
        op.drop_table("iam_user_permission_overrides")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_user_roles"):
        op.drop_table("iam_user_roles")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_role_activations"):
        op.drop_table("iam_role_activations")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_role_permissions"):
        op.drop_table("iam_role_permissions")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_permissions"):
        op.drop_table("iam_permissions")
    inspector = sa.inspect(bind)
    if _has_table(inspector, "iam_roles"):
        op.drop_table("iam_roles")
