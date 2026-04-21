"""add_customer_sync_fields

Revision ID: d7e8f9a0b1c2
Revises: c5d6e7f8g9h0
Create Date: 2026-02-22 00:00:00.000000

Adds three columns to support central sync (Sprint 3):
  - customers.last_synced_to_central  — tracks when each customer was last pushed
  - salon_settings.central_last_pull_at — tracks when delta pull last ran (as_of anchor)
  - salon_settings.central_sync_enabled — per-store toggle (mirrors env flag in DB)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c5d6e7f8g9h0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Track per-customer last sync time so we can find dirty records efficiently
    op.add_column(
        'customers',
        sa.Column('last_synced_to_central', sa.DateTime(timezone=True), nullable=True)
    )

    # Anchor for delta pulls — updated to response as_of after each successful pull
    op.add_column(
        'salon_settings',
        sa.Column('central_last_pull_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Per-store sync toggle stored in DB (mirrors CENTRAL_SYNC_ENABLED env var)
    op.add_column(
        'salon_settings',
        sa.Column(
            'central_sync_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        )
    )


def downgrade() -> None:
    op.drop_column('salon_settings', 'central_sync_enabled')
    op.drop_column('salon_settings', 'central_last_pull_at')
    op.drop_column('customers', 'last_synced_to_central')
