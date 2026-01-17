"""add_password_history_to_users

Revision ID: 890347448c6e
Revises: 597eeb0d2ec7
Create Date: 2025-10-17 16:11:36.536406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '890347448c6e'
down_revision: Union[str, None] = '597eeb0d2ec7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_history column to users table
    op.add_column('users', sa.Column('password_history', sa.ARRAY(sa.String()), nullable=True))


def downgrade() -> None:
    # Remove password_history column from users table
    op.drop_column('users', 'password_history')
