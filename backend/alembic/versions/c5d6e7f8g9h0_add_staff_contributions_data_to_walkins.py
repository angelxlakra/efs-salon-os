"""Add staff_contributions_data to walkins

Revision ID: c5d6e7f8g9h0
Revises: b3c4d5e6f7g8
Create Date: 2026-02-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8g9h0'
down_revision: Union[str, None] = 'b3c4d5e6f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('walkins', sa.Column('staff_contributions_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('walkins', 'staff_contributions_data')
