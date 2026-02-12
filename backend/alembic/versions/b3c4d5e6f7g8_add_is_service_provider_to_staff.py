"""Add is_service_provider to staff

Revision ID: b3c4d5e6f7g8
Revises: 41d2148c77a2
Create Date: 2026-02-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = '41d2148c77a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_service_provider column with default True
    op.add_column('staff', sa.Column('is_service_provider', sa.Boolean(), nullable=False, server_default=sa.text('true')))

    # Data migration: set receptionist staff profiles to False
    # Staff linked to users with RECEPTIONIST role should default to non-provider
    op.execute("""
        UPDATE staff
        SET is_service_provider = false
        FROM users
        JOIN roles ON users.role_id = roles.id
        WHERE staff.user_id = users.id
          AND roles.name = 'RECEPTIONIST'::roleenum
    """)


def downgrade() -> None:
    op.drop_column('staff', 'is_service_provider')
