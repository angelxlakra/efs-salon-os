"""Add GST and discount fields to purchase_items.

Revision ID: h1i2j3k4l5m6
Revises: g0a1b2c3d4e5
Create Date: 2026-03-07 00:00:00.000000

Adds:
  - rate_incl_tax:    MRP per unit in paise (for reference / auto-calc)
  - tax_rate_percent: GST rate % per item (default 18)
  - discount_percent: Trade discount % applied on base rate (reference)
  - cgst_amount:      Line-level CGST in paise
  - sgst_amount:      Line-level SGST in paise
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'g0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_items', sa.Column('rate_incl_tax', sa.Integer(), nullable=True))
    op.add_column('purchase_items', sa.Column('tax_rate_percent', sa.SmallInteger(), nullable=False, server_default='18'))
    op.add_column('purchase_items', sa.Column('discount_percent', sa.Numeric(5, 2), nullable=True))
    op.add_column('purchase_items', sa.Column('cgst_amount', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('purchase_items', sa.Column('sgst_amount', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('purchase_items', 'sgst_amount')
    op.drop_column('purchase_items', 'cgst_amount')
    op.drop_column('purchase_items', 'discount_percent')
    op.drop_column('purchase_items', 'tax_rate_percent')
    op.drop_column('purchase_items', 'rate_incl_tax')
