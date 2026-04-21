"""Add round_off_amount to purchase_invoices.

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-03-07 01:00:00.000000

Adds round_off_amount (INTEGER, nullable=false, default=0) to purchase_invoices.
Value is in paise and can be negative (round down) or positive (round up).
The invoice total_amount = subtotal - invoice_discount + round_off_amount.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'purchase_invoices',
        sa.Column('round_off_amount', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    op.drop_column('purchase_invoices', 'round_off_amount')
