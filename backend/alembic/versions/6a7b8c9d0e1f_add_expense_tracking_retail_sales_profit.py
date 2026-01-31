"""Add expense tracking, retail sales, and accurate profit calculation

Revision ID: 6a7b8c9d0e1f
Revises: 5f8f6222177c
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6a7b8c9d0e1f'
down_revision: Union[str, None] = '5f8f6222177c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== 1. Create expenses table ==========
    op.create_table(
        'expenses',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('category', sa.Enum(
            'RENT', 'SALARIES', 'UTILITIES', 'SUPPLIES', 'MARKETING',
            'MAINTENANCE', 'INSURANCE', 'TAXES_FEES', 'PROFESSIONAL_SERVICES', 'OTHER',
            name='expensecategory'
        ), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('vendor_name', sa.String(), nullable=True),
        sa.Column('invoice_number', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=False),
        sa.Column('recurrence_type', sa.Enum(
            'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY',
            name='recurrencetype'
        ), nullable=True),
        sa.Column('parent_expense_id', sa.String(length=26), nullable=True),
        sa.Column('staff_id', sa.String(length=26), nullable=True),
        sa.Column('status', sa.Enum(
            'PENDING', 'APPROVED', 'REJECTED',
            name='expensestatus'
        ), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=False),
        sa.Column('recorded_by', sa.String(length=26), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_by', sa.String(length=26), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', sa.String(length=26), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parent_expense_id'], ['expenses.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_category'), 'expenses', ['category'], unique=False)
    op.create_index(op.f('ix_expenses_expense_date'), 'expenses', ['expense_date'], unique=False)
    op.create_index(op.f('ix_expenses_is_recurring'), 'expenses', ['is_recurring'], unique=False)
    op.create_index(op.f('ix_expenses_staff_id'), 'expenses', ['staff_id'], unique=False)
    op.create_index(op.f('ix_expenses_status'), 'expenses', ['status'], unique=False)

    # ========== 2. Add retail fields to SKUs ==========
    op.add_column('skus', sa.Column('is_sellable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('skus', sa.Column('retail_price', sa.Integer(), nullable=True))
    op.add_column('skus', sa.Column('retail_markup_percent', sa.Numeric(precision=5, scale=2), nullable=True))
    op.create_index(op.f('ix_skus_is_sellable'), 'skus', ['is_sellable'], unique=False)

    # ========== 3. Modify BillItem to support products ==========
    # Make service_id nullable
    op.alter_column('bill_items', 'service_id', nullable=True, existing_type=sa.String(length=26))

    # Add product fields
    op.add_column('bill_items', sa.Column('sku_id', sa.String(length=26), nullable=True))
    op.add_column('bill_items', sa.Column('cogs_amount', sa.Integer(), nullable=True))

    # Add foreign key and index
    op.create_foreign_key('fk_bill_items_sku_id', 'bill_items', 'skus', ['sku_id'], ['id'])
    op.create_index(op.f('ix_bill_items_sku_id'), 'bill_items', ['sku_id'], unique=False)

    # Add check constraint (service XOR product)
    op.create_check_constraint(
        'bill_item_service_or_sku_check',
        'bill_items',
        '(service_id IS NOT NULL AND sku_id IS NULL) OR (service_id IS NULL AND sku_id IS NOT NULL)'
    )

    # ========== 4. Add tips to bills ==========
    op.add_column('bills', sa.Column('tip_amount', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('bills', sa.Column('tip_staff_id', sa.String(length=26), nullable=True))
    op.create_foreign_key('fk_bills_tip_staff_id', 'bills', 'staff', ['tip_staff_id'], ['id'])

    # ========== 5. Add actual profit fields to day_summary ==========
    op.add_column('day_summary', sa.Column('actual_service_cogs', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('actual_product_cogs', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('total_cogs', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('total_expenses', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('gross_profit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('net_profit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_summary', sa.Column('total_tips', sa.Integer(), nullable=False, server_default='0'))

    # ========== 6. Create service_material_usage table ==========
    op.create_table(
        'service_material_usage',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('service_id', sa.String(length=26), nullable=False),
        sa.Column('sku_id', sa.String(length=26), nullable=False),
        sa.Column('quantity_per_service', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_material_usage_service_id'), 'service_material_usage', ['service_id'], unique=False)
    op.create_index(op.f('ix_service_material_usage_sku_id'), 'service_material_usage', ['sku_id'], unique=False)


def downgrade() -> None:
    # ========== Reverse order of upgrade ==========

    # 6. Drop service_material_usage table
    op.drop_index(op.f('ix_service_material_usage_sku_id'), table_name='service_material_usage')
    op.drop_index(op.f('ix_service_material_usage_service_id'), table_name='service_material_usage')
    op.drop_table('service_material_usage')

    # 5. Remove actual profit fields from day_summary
    op.drop_column('day_summary', 'total_tips')
    op.drop_column('day_summary', 'net_profit')
    op.drop_column('day_summary', 'gross_profit')
    op.drop_column('day_summary', 'total_expenses')
    op.drop_column('day_summary', 'total_cogs')
    op.drop_column('day_summary', 'actual_product_cogs')
    op.drop_column('day_summary', 'actual_service_cogs')

    # 4. Remove tips from bills
    op.drop_constraint('fk_bills_tip_staff_id', 'bills', type_='foreignkey')
    op.drop_column('bills', 'tip_staff_id')
    op.drop_column('bills', 'tip_amount')

    # 3. Revert BillItem changes
    op.drop_constraint('bill_item_service_or_sku_check', 'bill_items', type_='check')
    op.drop_index(op.f('ix_bill_items_sku_id'), table_name='bill_items')
    op.drop_constraint('fk_bill_items_sku_id', 'bill_items', type_='foreignkey')
    op.drop_column('bill_items', 'cogs_amount')
    op.drop_column('bill_items', 'sku_id')
    op.alter_column('bill_items', 'service_id', nullable=False, existing_type=sa.String(length=26))

    # 2. Remove retail fields from SKUs
    op.drop_index(op.f('ix_skus_is_sellable'), table_name='skus')
    op.drop_column('skus', 'retail_markup_percent')
    op.drop_column('skus', 'retail_price')
    op.drop_column('skus', 'is_sellable')

    # 1. Drop expenses table
    op.drop_index(op.f('ix_expenses_status'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_staff_id'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_is_recurring'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_expense_date'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_category'), table_name='expenses')
    op.drop_table('expenses')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS expensestatus')
    op.execute('DROP TYPE IF EXISTS recurrencetype')
    op.execute('DROP TYPE IF EXISTS expensecategory')
