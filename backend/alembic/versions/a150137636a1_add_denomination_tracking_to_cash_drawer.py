"""add_denomination_tracking_to_cash_drawer

Revision ID: a150137636a1
Revises: b2c3d4e5f6g7
Create Date: 2026-02-06 19:39:47.684525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a150137636a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add denomination tracking columns to cash_drawer table
    op.add_column('cash_drawer', sa.Column('opening_denominations', postgresql.JSONB, nullable=True))
    op.add_column('cash_drawer', sa.Column('closing_denominations', postgresql.JSONB, nullable=True))
    op.add_column('cash_drawer', sa.Column('cash_taken_out', sa.Integer, nullable=True, server_default='0'))
    op.add_column('cash_drawer', sa.Column('cash_taken_out_reason', sa.Text, nullable=True))


def downgrade() -> None:
    # Remove denomination tracking columns
    op.drop_column('cash_drawer', 'cash_taken_out_reason')
    op.drop_column('cash_drawer', 'cash_taken_out')
    op.drop_column('cash_drawer', 'closing_denominations')
    op.drop_column('cash_drawer', 'opening_denominations')
