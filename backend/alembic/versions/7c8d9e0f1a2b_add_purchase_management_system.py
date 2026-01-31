"""Add purchase management system

Revision ID: 7c8d9e0f1a2b
Revises: 09164dc44353
Create Date: 2026-01-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7c8d9e0f1a2b'
down_revision: Union[str, None] = '09164dc44353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== 1. Add business fields to suppliers ==========
    op.add_column('suppliers', sa.Column('gstin', sa.String(length=15), nullable=True))
    op.add_column('suppliers', sa.Column('payment_terms', sa.String(length=255), nullable=True))

    # ========== 2. Add barcode field to SKUs ==========
    op.add_column('skus', sa.Column('barcode', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_skus_barcode'), 'skus', ['barcode'], unique=False)

    # ========== 3. Create purchase_invoices table ==========
    op.create_table(
        'purchase_invoices',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('supplier_id', sa.String(length=26), nullable=False),
        sa.Column('invoice_number', sa.String(length=100), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('paid_amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('balance_due', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum(
            'DRAFT', 'RECEIVED', 'PARTIALLY_PAID', 'PAID',
            name='purchasestatus'
        ), nullable=False, server_default='DRAFT'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_by', sa.String(length=26), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('invoice_file_url', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.String(length=26), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_invoices_supplier_id'), 'purchase_invoices', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_purchase_invoices_invoice_date'), 'purchase_invoices', ['invoice_date'], unique=False)
    op.create_index(op.f('ix_purchase_invoices_status'), 'purchase_invoices', ['status'], unique=False)

    # ========== 4. Create purchase_items table ==========
    op.create_table(
        'purchase_items',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('purchase_invoice_id', sa.String(length=26), nullable=False),
        sa.Column('sku_id', sa.String(length=26), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('uom', sa.String(length=20), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit_cost', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['purchase_invoice_id'], ['purchase_invoices.id'], ),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_items_purchase_invoice_id'), 'purchase_items', ['purchase_invoice_id'], unique=False)
    op.create_index(op.f('ix_purchase_items_sku_id'), 'purchase_items', ['sku_id'], unique=False)

    # ========== 5. Create supplier_payments table ==========
    op.create_table(
        'supplier_payments',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('supplier_id', sa.String(length=26), nullable=False),
        sa.Column('purchase_invoice_id', sa.String(length=26), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(length=26), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['purchase_invoice_id'], ['purchase_invoices.id'], ),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplier_payments_supplier_id'), 'supplier_payments', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_supplier_payments_purchase_invoice_id'), 'supplier_payments', ['purchase_invoice_id'], unique=False)
    op.create_index(op.f('ix_supplier_payments_payment_date'), 'supplier_payments', ['payment_date'], unique=False)

    # ========== 6. Update stock_ledger to support purchase references ==========
    # Rename change_request_id to a more generic reference for backward compatibility
    op.alter_column('stock_ledger', 'transaction_type',
                   existing_type=sa.String(),
                   type_=sa.String(),
                   nullable=False)
    # The existing columns already support our needs:
    # - reference_type can be 'purchase'
    # - reference_id can point to purchase_invoice.id
    # No schema changes needed


def downgrade() -> None:
    # ========== Reverse order of upgrade ==========

    # 5. Drop supplier_payments table
    op.drop_index(op.f('ix_supplier_payments_payment_date'), table_name='supplier_payments')
    op.drop_index(op.f('ix_supplier_payments_purchase_invoice_id'), table_name='supplier_payments')
    op.drop_index(op.f('ix_supplier_payments_supplier_id'), table_name='supplier_payments')
    op.drop_table('supplier_payments')

    # 4. Drop purchase_items table
    op.drop_index(op.f('ix_purchase_items_sku_id'), table_name='purchase_items')
    op.drop_index(op.f('ix_purchase_items_purchase_invoice_id'), table_name='purchase_items')
    op.drop_table('purchase_items')

    # 3. Drop purchase_invoices table
    op.drop_index(op.f('ix_purchase_invoices_status'), table_name='purchase_invoices')
    op.drop_index(op.f('ix_purchase_invoices_invoice_date'), table_name='purchase_invoices')
    op.drop_index(op.f('ix_purchase_invoices_supplier_id'), table_name='purchase_invoices')
    op.drop_table('purchase_invoices')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS purchasestatus')

    # 2. Remove barcode from SKUs
    op.drop_index(op.f('ix_skus_barcode'), table_name='skus')
    op.drop_column('skus', 'barcode')

    # 1. Remove business fields from suppliers
    op.drop_column('suppliers', 'payment_terms')
    op.drop_column('suppliers', 'gstin')
