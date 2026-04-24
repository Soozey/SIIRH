"""widen_app_user_role_code_for_enterprise

Revision ID: af3d91b1c742
Revises: 9c2e5f7a1b90
Create Date: 2026-04-04 23:59:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "af3d91b1c742"
down_revision: Union[str, Sequence[str], None] = "9c2e5f7a1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column(
        "app_users",
        "role_code",
        existing_type=sa.String(length=50),
        type_=sa.String(length=80),
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column(
        "app_users",
        "role_code",
        existing_type=sa.String(length=80),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
