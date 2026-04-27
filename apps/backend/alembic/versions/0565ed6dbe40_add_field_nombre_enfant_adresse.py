"""add_field_nombre_enfant_adresse

Revision ID: 0565ed6dbe40
Revises: 623602fbeca1
Create Date: 2025-11-20 10:38:01.497897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0565ed6dbe40'
down_revision: Union[str, Sequence[str], None] = '623602fbeca1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
