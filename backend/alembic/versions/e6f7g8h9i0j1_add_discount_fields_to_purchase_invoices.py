"""add_discount_fields_to_purchase_invoices

Revision ID: e6f7g8h9i0j1
Revises: a1b2c3d4e5f6
Create Date: 2026-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7g8h9i0j1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add discount_amount to purchase_items table
    op.add_column('purchase_items', sa.Column('discount_amount', sa.Integer(), nullable=False, server_default='0'))

    # Add discount fields to purchase_invoices table
    op.add_column('purchase_invoices', sa.Column('subtotal', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('purchase_invoices', sa.Column('invoice_discount_amount', sa.Integer(), nullable=False, server_default='0'))

    # Populate subtotal with current total_amount for existing records
    op.execute('UPDATE purchase_invoices SET subtotal = total_amount WHERE subtotal = 0')

    # Remove server defaults after adding columns
    op.alter_column('purchase_items', 'discount_amount', server_default=None)
    op.alter_column('purchase_invoices', 'subtotal', server_default=None)
    op.alter_column('purchase_invoices', 'invoice_discount_amount', server_default=None)


def downgrade() -> None:
    # Remove discount fields from purchase_invoices
    op.drop_column('purchase_invoices', 'invoice_discount_amount')
    op.drop_column('purchase_invoices', 'subtotal')

    # Remove discount_amount from purchase_items
    op.drop_column('purchase_items', 'discount_amount')
