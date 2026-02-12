"""add supplier tracking to inventory change requests

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add supplier tracking columns to inventory_change_requests table
    op.add_column('inventory_change_requests', sa.Column('supplier_invoice_number', sa.String(100), nullable=True))
    op.add_column('inventory_change_requests', sa.Column('supplier_discount_percent', sa.Numeric(5, 2), nullable=True))
    op.add_column('inventory_change_requests', sa.Column('supplier_discount_fixed', sa.Integer, nullable=True))


def downgrade():
    # Remove supplier tracking columns from inventory_change_requests table
    op.drop_column('inventory_change_requests', 'supplier_discount_fixed')
    op.drop_column('inventory_change_requests', 'supplier_discount_percent')
    op.drop_column('inventory_change_requests', 'supplier_invoice_number')
