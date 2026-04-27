"""add_worker_soft_delete

Revision ID: b7c9d4e2a113
Revises: a9d3c1e5f742
Create Date: 2026-04-20 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c9d4e2a113"
down_revision: Union[str, Sequence[str], None] = "a9d3c1e5f742"
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
    table_name = "workers"
    if not _has_table(inspector, table_name):
        return

    additions = [
        ("is_active", sa.Boolean(), sa.true()),
        ("deleted_at", sa.DateTime(), None),
        ("deleted_by_user_id", sa.Integer(), None),
    ]
    for column_name, column_type, default in additions:
        inspector = sa.inspect(bind)
        if _has_column(inspector, table_name, column_name):
            continue
        op.add_column(
            table_name,
            sa.Column(column_name, column_type, nullable=True if column_name != "is_active" else False, server_default=default),
        )

    inspector = sa.inspect(bind)
    if _has_column(inspector, table_name, "deleted_by_user_id"):
        fk_names = [fk["name"] for fk in inspector.get_foreign_keys(table_name) if "deleted_by_user_id" in fk.get("constrained_columns", [])]
        if not fk_names:
            op.create_foreign_key(
                "fk_workers_deleted_by_user_id",
                "workers",
                "app_users",
                ["deleted_by_user_id"],
                ["id"],
            )

    for index_name, columns in [
        ("ix_workers_is_active", ["is_active"]),
        ("ix_workers_deleted_at", ["deleted_at"]),
        ("ix_workers_deleted_by_user_id", ["deleted_by_user_id"]),
    ]:
        inspector = sa.inspect(bind)
        if not _has_index(inspector, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "workers"
    if not _has_table(inspector, table_name):
        return

    for index_name in ["ix_workers_deleted_by_user_id", "ix_workers_deleted_at", "ix_workers_is_active"]:
        inspector = sa.inspect(bind)
        if _has_index(inspector, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("name") == "fk_workers_deleted_by_user_id":
            op.drop_constraint("fk_workers_deleted_by_user_id", table_name, type_="foreignkey")
            break

    for column_name in ["deleted_by_user_id", "deleted_at", "is_active"]:
        inspector = sa.inspect(bind)
        if _has_column(inspector, table_name, column_name):
            op.drop_column(table_name, column_name)
