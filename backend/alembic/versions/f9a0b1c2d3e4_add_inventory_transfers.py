"""Add inventory transfers table and TRANSFER_IN/OUT expense categories.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-03-03 12:00:00.000000

Changes:
- Adds TRANSFER_OUT and TRANSFER_IN values to the expensecategory enum (uppercase to match SQLAlchemy enum name storage)
- Creates the inventory_transfers table for local transfer tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== 1. Extend expense category enum ==========
    # ALTER TYPE ... ADD VALUE must run outside a transaction block.
    # We use AUTOCOMMIT mode on the raw connection — safer than manual
    # COMMIT/BEGIN which can confuse Alembic's transaction tracking.
    # PostgreSQL 12+ allows ALTER TYPE ADD VALUE inside a transaction.
    # Note: these lowercase values are superseded by the uppercase ones added in g0a1b2c3d4e5.
    op.execute(sa.text("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'transfer_out'"))
    op.execute(sa.text("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'transfer_in'"))

    # ========== 2. Create inventory_transfers table ==========
    op.create_table(
        'inventory_transfers',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('central_transfer_id', sa.String(26), nullable=True, unique=True),
        sa.Column('direction', sa.String(3), nullable=False),  # 'OUT' or 'IN'
        sa.Column('other_store_name', sa.String(255), nullable=False),
        sa.Column('sku_id', sa.String(26), sa.ForeignKey('skus.id'), nullable=True),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('product_sku', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_cost_paise', sa.Integer, nullable=False),
        sa.Column('total_cost_paise', sa.Integer, nullable=False),
        sa.Column('expense_id', sa.String(26), sa.ForeignKey('expenses.id'), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_inventory_transfers_status', 'inventory_transfers', ['status'])
    op.create_index('ix_inventory_transfers_direction', 'inventory_transfers', ['direction'])
    op.create_index('ix_inventory_transfers_initiated_at', 'inventory_transfers',
                    ['initiated_at'], postgresql_ops={'initiated_at': 'DESC'})


def downgrade() -> None:
    op.drop_index('ix_inventory_transfers_initiated_at', table_name='inventory_transfers')
    op.drop_index('ix_inventory_transfers_direction', table_name='inventory_transfers')
    op.drop_index('ix_inventory_transfers_status', table_name='inventory_transfers')
    op.drop_table('inventory_transfers')
    # Note: PostgreSQL does not support DROP VALUE on an enum.
    # The TRANSFER_OUT and TRANSFER_IN values will remain in the enum type.
    # To fully revert, drop and recreate the enum type with the original values.
