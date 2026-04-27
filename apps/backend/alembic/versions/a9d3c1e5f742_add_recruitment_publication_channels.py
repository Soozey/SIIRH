"""add_recruitment_publication_channels

Revision ID: a9d3c1e5f742
Revises: fa15b202604
Create Date: 2026-04-20 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9d3c1e5f742"
down_revision: Union[str, Sequence[str], None] = "fa15b202604"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique(inspector, table_name: str, constraint_name: str) -> bool:
    return any(item["name"] == constraint_name for item in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "recruitment_job_postings"):
        additions = [
            ("publish_channels_json", sa.Text(), sa.text("'[]'")),
            ("publish_status", sa.String(length=50), sa.text("'draft'")),
            ("publish_logs_json", sa.Text(), sa.text("'[]'")),
        ]
        for column_name, column_type, default in additions:
            inspector = sa.inspect(bind)
            if _has_column(inspector, "recruitment_job_postings", column_name):
                continue
            op.add_column(
                "recruitment_job_postings",
                sa.Column(column_name, column_type, nullable=False, server_default=default),
            )
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "recruitment_job_postings", "ix_recruitment_job_postings_publish_status"):
            op.create_index(
                "ix_recruitment_job_postings_publish_status",
                "recruitment_job_postings",
                ["publish_status"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "recruitment_publication_channels"):
        op.create_table(
            "recruitment_publication_channels",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("employers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_type", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("config_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("default_publish", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_publication_channels"):
        if not _has_unique(inspector, "recruitment_publication_channels", "uq_recruitment_publication_channel_company_type"):
            op.create_unique_constraint(
                "uq_recruitment_publication_channel_company_type",
                "recruitment_publication_channels",
                ["company_id", "channel_type"],
            )
        for index_name, columns in [
            ("ix_recruitment_publication_channels_company_id", ["company_id"]),
            ("ix_recruitment_publication_channels_channel_type", ["channel_type"]),
            ("ix_recruitment_publication_channels_is_active", ["is_active"]),
            ("ix_recruitment_publication_channels_default_publish", ["default_publish"]),
        ]:
            inspector = sa.inspect(bind)
            if not _has_index(inspector, "recruitment_publication_channels", index_name):
                op.create_index(index_name, "recruitment_publication_channels", columns, unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "recruitment_publication_logs"):
        op.create_table(
            "recruitment_publication_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("recruitment_job_postings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("details_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_publication_logs"):
        for index_name, columns in [
            ("ix_recruitment_publication_logs_job_id", ["job_id"]),
            ("ix_recruitment_publication_logs_channel", ["channel"]),
            ("ix_recruitment_publication_logs_status", ["status"]),
            ("ix_recruitment_publication_logs_triggered_by_user_id", ["triggered_by_user_id"]),
            ("ix_recruitment_publication_logs_timestamp", ["timestamp"]),
        ]:
            inspector = sa.inspect(bind)
            if not _has_index(inspector, "recruitment_publication_logs", index_name):
                op.create_index(index_name, "recruitment_publication_logs", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "recruitment_publication_logs"):
        for index_name in [
            "ix_recruitment_publication_logs_timestamp",
            "ix_recruitment_publication_logs_triggered_by_user_id",
            "ix_recruitment_publication_logs_status",
            "ix_recruitment_publication_logs_channel",
            "ix_recruitment_publication_logs_job_id",
        ]:
            inspector = sa.inspect(bind)
            if _has_index(inspector, "recruitment_publication_logs", index_name):
                op.drop_index(index_name, table_name="recruitment_publication_logs")
        op.drop_table("recruitment_publication_logs")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_publication_channels"):
        for index_name in [
            "ix_recruitment_publication_channels_default_publish",
            "ix_recruitment_publication_channels_is_active",
            "ix_recruitment_publication_channels_channel_type",
            "ix_recruitment_publication_channels_company_id",
        ]:
            inspector = sa.inspect(bind)
            if _has_index(inspector, "recruitment_publication_channels", index_name):
                op.drop_index(index_name, table_name="recruitment_publication_channels")
        inspector = sa.inspect(bind)
        if _has_unique(inspector, "recruitment_publication_channels", "uq_recruitment_publication_channel_company_type"):
            op.drop_constraint(
                "uq_recruitment_publication_channel_company_type",
                "recruitment_publication_channels",
                type_="unique",
            )
        op.drop_table("recruitment_publication_channels")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "recruitment_job_postings"):
        if _has_index(inspector, "recruitment_job_postings", "ix_recruitment_job_postings_publish_status"):
            op.drop_index("ix_recruitment_job_postings_publish_status", table_name="recruitment_job_postings")
        for column_name in ["publish_logs_json", "publish_status", "publish_channels_json"]:
            inspector = sa.inspect(bind)
            if _has_column(inspector, "recruitment_job_postings", column_name):
                op.drop_column("recruitment_job_postings", column_name)
