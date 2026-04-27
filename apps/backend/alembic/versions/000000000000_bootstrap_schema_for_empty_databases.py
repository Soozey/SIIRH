"""bootstrap_schema_for_empty_databases

Revision ID: 000000000000
Revises:
Create Date: 2026-03-19 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

from app.config.config import Base
import app.models  # noqa: F401


revision: str = "000000000000"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    pass
