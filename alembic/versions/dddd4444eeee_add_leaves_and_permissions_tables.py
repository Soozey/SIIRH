"""add_leaves_and_permissions_tables

Revision ID: dddd4444eeee
Revises: cccc3333dddd
Create Date: 2025-12-16 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "dddd4444eeee"
down_revision = "cccc3333dddd"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "leaves"):
        op.create_table(
            "leaves",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.Integer(), nullable=False),
            sa.Column("period", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("days_taken", sa.Float(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if _has_table(inspector, "leaves"):
        for index_name, columns in [
            (op.f("ix_leaves_id"), ["id"]),
            (op.f("ix_leaves_worker_id"), ["worker_id"]),
            (op.f("ix_leaves_period"), ["period"]),
        ]:
            if not _has_index(inspector, "leaves", index_name):
                op.create_index(index_name, "leaves", columns, unique=False)
                inspector = sa.inspect(bind)

    if not _has_table(inspector, "permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.Integer(), nullable=False),
            sa.Column("period", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("days_taken", sa.Float(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if _has_table(inspector, "permissions"):
        for index_name, columns in [
            (op.f("ix_permissions_id"), ["id"]),
            (op.f("ix_permissions_worker_id"), ["worker_id"]),
            (op.f("ix_permissions_period"), ["period"]),
        ]:
            if not _has_index(inspector, "permissions", index_name):
                op.create_index(index_name, "permissions", columns, unique=False)
                inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "permissions"):
        for index_name in [op.f("ix_permissions_period"), op.f("ix_permissions_worker_id"), op.f("ix_permissions_id")]:
            if _has_index(inspector, "permissions", index_name):
                op.drop_index(index_name, table_name="permissions")
                inspector = sa.inspect(bind)
        op.drop_table("permissions")
        inspector = sa.inspect(bind)

    if _has_table(inspector, "leaves"):
        for index_name in [op.f("ix_leaves_period"), op.f("ix_leaves_worker_id"), op.f("ix_leaves_id")]:
            if _has_index(inspector, "leaves", index_name):
                op.drop_index(index_name, table_name="leaves")
                inspector = sa.inspect(bind)
        op.drop_table("leaves")
