"""add packages module

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-06-02

Creates 6 new tables for the bundles & session packages feature:
  - package_definitions
  - package_definition_items
  - package_sales
  - package_sale_items
  - package_redemption_audit
  - package_expiry_extensions

Adds new columns to existing tables:
  - bills.bill_type (billtype enum, server_default='normal')
  - bill_items.item_type (billitemtype enum, server_default='service')
  - bill_items.package_sale_id
  - bill_items.package_sale_item_id

Adds new enum value:
  - paymentmethod: 'package_redemption'

Data backfills:
  - bills with original_bill_id IS NOT NULL -> bill_type = 'credit_note'
  - bill_items with sku_id IS NOT NULL -> item_type = 'product'

Constraint changes:
  - Drops and recreates bill_item_service_or_sku_check (relaxed for package types)
  - Adds ck_bill_credit_note_has_original on bills (AFTER data backfill)

Implementation notes:
  - ALTER TYPE ADD VALUE cannot run inside a transaction in PostgreSQL.
    We use a non-transactional connection context for that step only.
  - All other enum types are created via raw SQL using a DO $$ BEGIN ... EXCEPTION
    WHEN duplicate_object THEN NULL; END $$ block to guarantee idempotency
    (PostgreSQL does not support CREATE TYPE IF NOT EXISTS) without relying on
    SQLAlchemy's create_type flag.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'l5m6n7o8p9q0'
down_revision = 'k4l5m6n7o8p9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Add package_redemption to paymentmethod enum.
    #    ALTER TYPE ... ADD VALUE cannot run inside a transaction block in
    #    PostgreSQL (it is allowed but only as the sole statement in its
    #    own transaction). We use autocommit=True on a raw connection.
    # -------------------------------------------------------------------------
    # ALTER TYPE ADD VALUE cannot reliably run inside a transaction on PG < 12.
    # Alembic's autocommit_block() commits the current transaction, executes the
    # statement in AUTOCOMMIT mode, then opens a new transaction for subsequent ops.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'package_redemption'"))

    # -------------------------------------------------------------------------
    # 2. Create new enum types via raw SQL with IF NOT EXISTS for idempotency.
    #    We do NOT let SQLAlchemy auto-create these — we use create_type=False
    #    everywhere and manage creation ourselves.
    # -------------------------------------------------------------------------
    op.execute(
        "DO $$ BEGIN CREATE TYPE packagedefinitionstatus AS ENUM ('draft', 'published', 'archived'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE entitlementtype AS ENUM ('counted', 'unlimited'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE shareability AS ENUM ('owner_only', 'shared'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE packagesalestatus AS ENUM ('active', 'expired', 'refunded', 'exhausted'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE billtype AS ENUM ('normal', 'credit_note'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE billitemtype AS ENUM ('service', 'product', 'package_sale_line', 'package_redemption'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    # -------------------------------------------------------------------------
    # 3. Create package_definitions table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_definitions',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('draft', 'published', 'archived', name='packagedefinitionstatus', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'entitlement_type',
            postgresql.ENUM('counted', 'unlimited', name='entitlementtype', create_type=False),
            nullable=False,
        ),
        sa.Column('total_sessions', sa.Integer, nullable=True),
        sa.Column(
            'shareability',
            postgresql.ENUM('owner_only', 'shared', name='shareability', create_type=False),
            nullable=False,
        ),
        sa.Column('validity_days', sa.Integer, nullable=False),
        sa.Column('auto_apply', sa.Boolean, nullable=False),
        sa.Column('cancellation_fee_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('created_by_user_id', sa.String(26), sa.ForeignKey('users.id'), nullable=False),
        sa.CheckConstraint(
            "(entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
            "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
            name='ck_package_def_entitlement_sessions',
        ),
        sa.CheckConstraint(
            'cancellation_fee_pct >= 0 AND cancellation_fee_pct <= 100',
            name='ck_package_def_fee_range',
        ),
        sa.CheckConstraint(
            'validity_days > 0',
            name='ck_package_def_validity_positive',
        ),
    )

    # -------------------------------------------------------------------------
    # 4. Create package_definition_items table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_definition_items',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column(
            'package_definition_id',
            sa.String(26),
            sa.ForeignKey('package_definitions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('service_id', sa.String(26), sa.ForeignKey('services.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price_paise', sa.Integer, nullable=False),
        sa.Column('locked', sa.Boolean, nullable=False),
        sa.Column('display_order', sa.Integer, nullable=False),
        sa.CheckConstraint('quantity >= 1', name='ck_package_def_item_qty_positive'),
        sa.CheckConstraint('unit_price_paise >= 0', name='ck_package_def_item_price_non_negative'),
    )
    op.create_index('ix_package_definition_items_package_definition_id', 'package_definition_items', ['package_definition_id'])

    # -------------------------------------------------------------------------
    # 5. Create package_sales table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_sales',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('bill_id', sa.String(26), sa.ForeignKey('bills.id', ondelete='RESTRICT'), nullable=False, unique=True),
        sa.Column(
            'package_definition_id',
            sa.String(26),
            sa.ForeignKey('package_definitions.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('customer_id', sa.String(26), sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('selling_staff_id', sa.String(26), sa.ForeignKey('staff.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sold_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'entitlement_type_snapshot',
            postgresql.ENUM('counted', 'unlimited', name='entitlementtype', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'shareability_snapshot',
            postgresql.ENUM('owner_only', 'shared', name='shareability', create_type=False),
            nullable=False,
        ),
        sa.Column('cancellation_fee_pct_snapshot', sa.Numeric(5, 2), nullable=False),
        sa.Column('total_sessions_snapshot', sa.Integer, nullable=True),
        sa.Column('sessions_remaining', sa.Integer, nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('active', 'expired', 'refunded', 'exhausted', name='packagesalestatus', create_type=False),
            nullable=False,
        ),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_bill_id', sa.String(26), sa.ForeignKey('bills.id', ondelete='RESTRICT'), nullable=True),
        sa.CheckConstraint(
            'sessions_remaining IS NULL OR sessions_remaining >= 0',
            name='ck_package_sale_sessions_remaining_non_negative',
        ),
        sa.CheckConstraint(
            "(total_sessions_snapshot IS NULL)"
            " OR (sessions_remaining IS NULL)"
            " OR (sessions_remaining <= total_sessions_snapshot)",
            name='ck_package_sale_sessions_not_exceed_total',
        ),
        sa.CheckConstraint(
            'cancellation_fee_pct_snapshot >= 0 AND cancellation_fee_pct_snapshot <= 100',
            name='ck_package_sale_fee_snapshot_range',
        ),
    )
    op.create_index('ix_package_sales_customer_id', 'package_sales', ['customer_id'])
    op.create_index('ix_package_sales_expires_at', 'package_sales', ['expires_at'])
    op.create_index('ix_package_sales_status', 'package_sales', ['status'])
    op.create_index('ix_package_sales_customer_status', 'package_sales', ['customer_id', 'status'])
    op.create_index('ix_package_sales_expires_status', 'package_sales', ['expires_at', 'status'])
    op.create_index('ix_package_sales_selling_staff_sold_at', 'package_sales', ['selling_staff_id', 'sold_at'])

    # -------------------------------------------------------------------------
    # 6. Create package_sale_items table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_sale_items',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column(
            'package_sale_id',
            sa.String(26),
            sa.ForeignKey('package_sales.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'package_definition_item_id',
            sa.String(26),
            sa.ForeignKey('package_definition_items.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('service_id', sa.String(26), sa.ForeignKey('services.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('snapshot_unit_price_paise', sa.Integer, nullable=False),
        sa.Column('snapshot_gst_rate_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('locked', sa.Boolean, nullable=False),
        sa.Column('display_order', sa.Integer, nullable=False),
        sa.CheckConstraint('quantity >= 1', name='ck_package_sale_item_qty_positive'),
        sa.CheckConstraint('snapshot_unit_price_paise >= 0', name='ck_package_sale_item_price_non_negative'),
    )
    op.create_index('ix_package_sale_items_package_sale_id', 'package_sale_items', ['package_sale_id'])
    op.create_index('ix_package_sale_items_service_id', 'package_sale_items', ['service_id'])

    # -------------------------------------------------------------------------
    # 7. Create package_redemption_audit table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_redemption_audit',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column(
            'package_sale_id',
            sa.String(26),
            sa.ForeignKey('package_sales.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'bill_item_id',
            sa.String(26),
            sa.ForeignKey('bill_items.id', ondelete='RESTRICT'),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            'package_sale_item_id',
            sa.String(26),
            sa.ForeignKey('package_sale_items.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'redeemed_for_customer_id',
            sa.String(26),
            sa.ForeignKey('customers.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'performed_by_user_id',
            sa.String(26),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_number', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )
    op.create_index('ix_package_redemption_audit_package_sale_id', 'package_redemption_audit', ['package_sale_id'])
    op.create_index('ix_package_redemption_audit_redeemed_for_customer_id', 'package_redemption_audit', ['redeemed_for_customer_id'])
    op.create_index(
        'ix_package_redemption_audit_for_customer_redeemed_at',
        'package_redemption_audit',
        ['redeemed_for_customer_id', 'redeemed_at'],
    )
    op.create_index('ix_package_redemption_audit_package_sale_item_id', 'package_redemption_audit', ['package_sale_item_id'])

    # -------------------------------------------------------------------------
    # 8. Create package_expiry_extensions table
    # -------------------------------------------------------------------------
    op.create_table(
        'package_expiry_extensions',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column(
            'package_sale_id',
            sa.String(26),
            sa.ForeignKey('package_sales.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('previous_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('new_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'performed_by_user_id',
            sa.String(26),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('extended_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.CheckConstraint(
            'new_expires_at > previous_expires_at',
            name='ck_package_extend_forward_in_time',
        ),
    )
    op.create_index('ix_package_expiry_extensions_package_sale_id', 'package_expiry_extensions', ['package_sale_id'])

    # -------------------------------------------------------------------------
    # 9. Add bill_type column to bills
    # -------------------------------------------------------------------------
    op.add_column(
        'bills',
        sa.Column(
            'bill_type',
            postgresql.ENUM('normal', 'credit_note', name='billtype', create_type=False),
            nullable=False,
            server_default='normal',
        ),
    )
    op.create_index('ix_bills_bill_type', 'bills', ['bill_type'])

    # -------------------------------------------------------------------------
    # 10. Add item_type, package_sale_id, package_sale_item_id to bill_items
    # -------------------------------------------------------------------------
    op.add_column(
        'bill_items',
        sa.Column(
            'item_type',
            postgresql.ENUM(
                'service', 'product', 'package_sale_line', 'package_redemption',
                name='billitemtype',
                create_type=False,
            ),
            nullable=False,
            server_default='service',
        ),
    )
    op.add_column(
        'bill_items',
        sa.Column(
            'package_sale_id',
            sa.String(26),
            sa.ForeignKey('package_sales.id', ondelete='RESTRICT'),
            nullable=True,
        ),
    )
    op.add_column(
        'bill_items',
        sa.Column(
            'package_sale_item_id',
            sa.String(26),
            sa.ForeignKey('package_sale_items.id', ondelete='RESTRICT'),
            nullable=True,
        ),
    )
    op.create_index('ix_bill_items_item_type', 'bill_items', ['item_type'])
    op.create_index('ix_bill_items_package_sale_id', 'bill_items', ['package_sale_id'])
    op.create_index('ix_bill_items_package_sale_item_id', 'bill_items', ['package_sale_item_id'])

    # -------------------------------------------------------------------------
    # 11. Data backfills — MUST run before adding constraints that depend on
    #     the backfilled column values.
    # -------------------------------------------------------------------------
    # Bills that already have original_bill_id set are credit notes
    op.execute("""
        UPDATE bills
        SET bill_type = 'credit_note'
        WHERE original_bill_id IS NOT NULL
    """)

    # Bill items linked to a SKU are products (existing service items stay 'service')
    op.execute("""
        UPDATE bill_items
        SET item_type = 'product'
        WHERE sku_id IS NOT NULL
    """)

    # -------------------------------------------------------------------------
    # 12. Drop old bill_item_service_or_sku_check, recreate relaxed version
    # -------------------------------------------------------------------------
    op.drop_constraint('bill_item_service_or_sku_check', 'bill_items', type_='check')
    op.create_check_constraint(
        'bill_item_service_or_sku_check',
        'bill_items',
        "(service_id IS NOT NULL AND sku_id IS NULL)"
        " OR (service_id IS NULL AND sku_id IS NOT NULL)"
        " OR item_type IN ('package_sale_line', 'package_redemption')",
    )

    # -------------------------------------------------------------------------
    # 13. Add credit-note constraint on bills — AFTER backfill (step 11)
    # -------------------------------------------------------------------------
    op.create_check_constraint(
        'ck_bill_credit_note_has_original',
        'bills',
        "(bill_type = 'credit_note' AND original_bill_id IS NOT NULL)"
        " OR (bill_type = 'normal' AND original_bill_id IS NULL)",
    )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # Remove constraints first
    # -------------------------------------------------------------------------
    op.drop_constraint('ck_bill_credit_note_has_original', 'bills', type_='check')
    # Safety: delete any package-typed bill_items before restoring the strict
    # service/sku-only constraint. This downgrade is destructive if package data
    # was written after the upgrade. Only run downgrade on schema-only rollbacks.
    op.execute(
        "DELETE FROM bill_items WHERE item_type IN ('package_sale_line', 'package_redemption')"
    )
    op.drop_constraint('bill_item_service_or_sku_check', 'bill_items', type_='check')
    # Restore the original strict check constraint
    op.create_check_constraint(
        'bill_item_service_or_sku_check',
        'bill_items',
        '(service_id IS NOT NULL AND sku_id IS NULL) OR (service_id IS NULL AND sku_id IS NOT NULL)',
    )

    # -------------------------------------------------------------------------
    # Remove indexes added to existing tables
    # -------------------------------------------------------------------------
    op.drop_index('ix_bill_items_package_sale_item_id', table_name='bill_items')
    op.drop_index('ix_bill_items_package_sale_id', table_name='bill_items')
    op.drop_index('ix_bill_items_item_type', table_name='bill_items')
    op.drop_index('ix_bills_bill_type', table_name='bills')

    # -------------------------------------------------------------------------
    # Remove new columns from bill_items and bills
    # -------------------------------------------------------------------------
    op.drop_column('bill_items', 'package_sale_item_id')
    op.drop_column('bill_items', 'package_sale_id')
    op.drop_column('bill_items', 'item_type')
    op.drop_column('bills', 'bill_type')

    # -------------------------------------------------------------------------
    # Drop new tables in reverse dependency order
    # -------------------------------------------------------------------------
    op.drop_table('package_expiry_extensions')
    op.execute('DROP INDEX IF EXISTS ix_package_redemption_audit_package_sale_item_id')
    op.drop_table('package_redemption_audit')
    op.drop_table('package_sale_items')
    op.execute('ALTER TABLE package_sales DROP CONSTRAINT IF EXISTS ck_package_sale_sessions_not_exceed_total')
    op.execute('ALTER TABLE package_sales DROP CONSTRAINT IF EXISTS ck_package_sale_fee_snapshot_range')
    op.drop_table('package_sales')
    op.drop_table('package_definition_items')
    op.drop_table('package_definitions')

    # -------------------------------------------------------------------------
    # Drop new enum types
    # -------------------------------------------------------------------------
    op.execute('DROP TYPE IF EXISTS billitemtype')
    op.execute('DROP TYPE IF EXISTS billtype')
    op.execute('DROP TYPE IF EXISTS packagesalestatus')
    op.execute('DROP TYPE IF EXISTS shareability')
    op.execute('DROP TYPE IF EXISTS entitlementtype')
    op.execute('DROP TYPE IF EXISTS packagedefinitionstatus')
    # NOTE: paymentmethod enum value 'package_redemption' is NOT removed.
    # PostgreSQL does not support DROP VALUE on enums — this is acceptable.
    # The value remains dormant after downgrade.
