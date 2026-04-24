"""harden_inspection_and_messages

Revision ID: f6a7b8c9d012
Revises: e3b7a9c4d511
Create Date: 2026-03-21 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d012"
down_revision: Union[str, Sequence[str], None] = "e3b7a9c4d511"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "inspector_case_assignments"):
        op.create_table(
            "inspector_case_assignments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("inspector_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
            sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("scope", sa.String(length=50), nullable=False, server_default="lead"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("case_id", "inspector_user_id", name="uq_inspector_case_assignment"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspector_case_assignments") and not _has_index(inspector, "inspector_case_assignments", "ix_inspector_case_assignments_scope"):
        op.create_index("ix_inspector_case_assignments_scope", "inspector_case_assignments", ["inspector_user_id", "status", "assigned_at"], unique=False)

    if _has_table(inspector, "inspector_cases") and _has_table(inspector, "inspector_case_assignments"):
        cases = sa.table(
            "inspector_cases",
            sa.column("id", sa.Integer()),
            sa.column("assigned_inspector_user_id", sa.Integer()),
        )
        assignments = sa.table(
            "inspector_case_assignments",
            sa.column("case_id", sa.Integer()),
            sa.column("inspector_user_id", sa.Integer()),
            sa.column("assigned_by_user_id", sa.Integer()),
            sa.column("scope", sa.String()),
            sa.column("status", sa.String()),
        )
        rows = bind.execute(sa.select(cases.c.id, cases.c.assigned_inspector_user_id).where(cases.c.assigned_inspector_user_id.is_not(None))).fetchall()
        for row in rows:
            existing = bind.execute(
                sa.select(assignments.c.case_id).where(
                    assignments.c.case_id == row.id,
                    assignments.c.inspector_user_id == row.assigned_inspector_user_id,
                )
            ).first()
            if not existing:
                bind.execute(
                    sa.insert(assignments).values(
                        case_id=row.id,
                        inspector_user_id=row.assigned_inspector_user_id,
                        assigned_by_user_id=None,
                        scope="lead",
                        status="active",
                    )
                )

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "inspection_documents"):
        op.create_table(
            "inspection_documents",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("document_type", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(length=50), nullable=False, server_default="case_parties"),
            sa.Column("confidentiality", sa.String(length=50), nullable=False, server_default="restricted"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspection_documents") and not _has_index(inspector, "inspection_documents", "ix_inspection_documents_queue"):
        op.create_index("ix_inspection_documents_queue", "inspection_documents", ["case_id", "status", "updated_at"], unique=False)

    if not _has_table(inspector, "inspection_document_versions"):
        op.create_table(
            "inspection_document_versions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("inspection_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("original_name", sa.String(length=255), nullable=False),
            sa.Column("storage_path", sa.String(length=500), nullable=False),
            sa.Column("static_url", sa.String(length=500), nullable=True),
            sa.Column("content_type", sa.String(length=255), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("checksum", sa.String(length=128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("document_id", "version_number", name="uq_inspection_document_version"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspection_document_versions") and not _has_index(inspector, "inspection_document_versions", "ix_inspection_document_versions_case"):
        op.create_index("ix_inspection_document_versions_case", "inspection_document_versions", ["case_id", "created_at"], unique=False)

    if not _has_table(inspector, "inspection_document_access_logs"):
        op.create_table(
            "inspection_document_access_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("inspection_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_id", sa.Integer(), sa.ForeignKey("inspection_document_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("inspector_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("action", sa.String(length=50), nullable=False, server_default="view"),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "inspection_document_access_logs") and not _has_index(inspector, "inspection_document_access_logs", "ix_inspection_document_access_logs_document"):
        op.create_index("ix_inspection_document_access_logs_document", "inspection_document_access_logs", ["document_id", "created_at"], unique=False)

    if not _has_table(inspector, "internal_message_channels"):
        op.create_table(
            "internal_message_channels",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("channel_code", sa.String(length=100), nullable=False, unique=True),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("channel_type", sa.String(length=50), nullable=False, server_default="group"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(length=50), nullable=False, server_default="internal"),
            sa.Column("ack_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_message_channels") and not _has_index(inspector, "internal_message_channels", "ix_internal_message_channels_queue"):
        op.create_index("ix_internal_message_channels_queue", "internal_message_channels", ["employer_id", "status", "updated_at"], unique=False)

    if not _has_table(inspector, "internal_message_channel_members"):
        op.create_table(
            "internal_message_channel_members",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("channel_id", sa.Integer(), sa.ForeignKey("internal_message_channels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
            sa.Column("member_role", sa.String(length=50), nullable=False, server_default="member"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_read_at", sa.DateTime(), nullable=True),
            sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("channel_id", "user_id", name="uq_internal_message_channel_member"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_message_channel_members") and not _has_index(inspector, "internal_message_channel_members", "ix_internal_message_channel_members_user"):
        op.create_index("ix_internal_message_channel_members_user", "internal_message_channel_members", ["user_id", "is_active", "joined_at"], unique=False)

    if not _has_table(inspector, "internal_messages"):
        op.create_table(
            "internal_messages",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("channel_id", sa.Integer(), sa.ForeignKey("internal_message_channels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("message_type", sa.String(length=50), nullable=False, server_default="message"),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="sent"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_messages") and not _has_index(inspector, "internal_messages", "ix_internal_messages_channel_created"):
        op.create_index("ix_internal_messages_channel_created", "internal_messages", ["channel_id", "created_at"], unique=False)

    if not _has_table(inspector, "internal_message_receipts"):
        op.create_table(
            "internal_message_receipts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("message_id", sa.Integer(), sa.ForeignKey("internal_messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="read"),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("message_id", "user_id", name="uq_internal_message_receipt"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_message_receipts") and not _has_index(inspector, "internal_message_receipts", "ix_internal_message_receipts_user"):
        op.create_index("ix_internal_message_receipts_user", "internal_message_receipts", ["user_id", "status", "updated_at"], unique=False)

    if not _has_table(inspector, "internal_notices"):
        op.create_table(
            "internal_notices",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("employer_id", sa.Integer(), sa.ForeignKey("employers.id"), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("notice_type", sa.String(length=50), nullable=False, server_default="service_note"),
            sa.Column("audience_role", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="published"),
            sa.Column("ack_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_notices") and not _has_index(inspector, "internal_notices", "ix_internal_notices_queue"):
        op.create_index("ix_internal_notices_queue", "internal_notices", ["employer_id", "status", "published_at"], unique=False)

    if not _has_table(inspector, "internal_notice_acknowledgements"):
        op.create_table(
            "internal_notice_acknowledgements",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("notice_id", sa.Integer(), sa.ForeignKey("internal_notices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="acknowledged"),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("notice_id", "user_id", name="uq_internal_notice_acknowledgement"),
        )
    inspector = sa.inspect(bind)
    if _has_table(inspector, "internal_notice_acknowledgements") and not _has_index(inspector, "internal_notice_acknowledgements", "ix_internal_notice_acknowledgements_user"):
        op.create_index("ix_internal_notice_acknowledgements_user", "internal_notice_acknowledgements", ["user_id", "acknowledged_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "internal_notice_acknowledgements") and _has_index(inspector, "internal_notice_acknowledgements", "ix_internal_notice_acknowledgements_user"):
        op.drop_index("ix_internal_notice_acknowledgements_user", table_name="internal_notice_acknowledgements")
    if _has_table(inspector, "internal_notice_acknowledgements"):
        op.drop_table("internal_notice_acknowledgements")
    if _has_table(inspector, "internal_notices") and _has_index(inspector, "internal_notices", "ix_internal_notices_queue"):
        op.drop_index("ix_internal_notices_queue", table_name="internal_notices")
    if _has_table(inspector, "internal_notices"):
        op.drop_table("internal_notices")
    if _has_table(inspector, "internal_message_receipts") and _has_index(inspector, "internal_message_receipts", "ix_internal_message_receipts_user"):
        op.drop_index("ix_internal_message_receipts_user", table_name="internal_message_receipts")
    if _has_table(inspector, "internal_message_receipts"):
        op.drop_table("internal_message_receipts")
    if _has_table(inspector, "internal_messages") and _has_index(inspector, "internal_messages", "ix_internal_messages_channel_created"):
        op.drop_index("ix_internal_messages_channel_created", table_name="internal_messages")
    if _has_table(inspector, "internal_messages"):
        op.drop_table("internal_messages")
    if _has_table(inspector, "internal_message_channel_members") and _has_index(inspector, "internal_message_channel_members", "ix_internal_message_channel_members_user"):
        op.drop_index("ix_internal_message_channel_members_user", table_name="internal_message_channel_members")
    if _has_table(inspector, "internal_message_channel_members"):
        op.drop_table("internal_message_channel_members")
    if _has_table(inspector, "internal_message_channels") and _has_index(inspector, "internal_message_channels", "ix_internal_message_channels_queue"):
        op.drop_index("ix_internal_message_channels_queue", table_name="internal_message_channels")
    if _has_table(inspector, "internal_message_channels"):
        op.drop_table("internal_message_channels")
    if _has_table(inspector, "inspection_document_access_logs") and _has_index(inspector, "inspection_document_access_logs", "ix_inspection_document_access_logs_document"):
        op.drop_index("ix_inspection_document_access_logs_document", table_name="inspection_document_access_logs")
    if _has_table(inspector, "inspection_document_access_logs"):
        op.drop_table("inspection_document_access_logs")
    if _has_table(inspector, "inspection_document_versions") and _has_index(inspector, "inspection_document_versions", "ix_inspection_document_versions_case"):
        op.drop_index("ix_inspection_document_versions_case", table_name="inspection_document_versions")
    if _has_table(inspector, "inspection_document_versions"):
        op.drop_table("inspection_document_versions")
    if _has_table(inspector, "inspection_documents") and _has_index(inspector, "inspection_documents", "ix_inspection_documents_queue"):
        op.drop_index("ix_inspection_documents_queue", table_name="inspection_documents")
    if _has_table(inspector, "inspection_documents"):
        op.drop_table("inspection_documents")
    if _has_table(inspector, "inspector_case_assignments") and _has_index(inspector, "inspector_case_assignments", "ix_inspector_case_assignments_scope"):
        op.drop_index("ix_inspector_case_assignments_scope", table_name="inspector_case_assignments")
    if _has_table(inspector, "inspector_case_assignments"):
        op.drop_table("inspector_case_assignments")
