"""merge_discount_and_pending_payment_heads

Revision ID: f7g8h9i0j1k2
Revises: d5e6f7g8h9i0, e6f7g8h9i0j1
Create Date: 2026-02-07 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = ('d5e6f7g8h9i0', 'e6f7g8h9i0j1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass
