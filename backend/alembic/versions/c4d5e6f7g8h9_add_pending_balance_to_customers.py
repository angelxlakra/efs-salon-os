"""add_pending_balance_to_customers

Revision ID: c4d5e6f7g8h9
Revises: 7d84edca4b93
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, None] = '7d84edca4b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pending_balance column to customers table
    op.add_column('customers', sa.Column('pending_balance', sa.Integer(), nullable=False, server_default='0'))

    # Remove server default after adding column (keep default in Python model only)
    op.alter_column('customers', 'pending_balance', server_default=None)


def downgrade() -> None:
    # Remove pending_balance column
    op.drop_column('customers', 'pending_balance')
