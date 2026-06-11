"""Per-line tax columns, bill groups, payment groups + legacy zero-tax backfill.

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-06-11

Phase 2a of the GST split-billing scheme:
  bills:      bill_class (service|product|mixed_legacy), bill_group_id
  bill_items: tax_rate, tax_mode (exclusive|inclusive|none), taxable_value,
              cgst_amount, sgst_amount
  payments:   payment_group_id

Backfill (owner decision): the salon was NOT GST-registered before 2026-06-11,
so no GST was actually collected. All existing bills get their tax fields
zeroed (subtotal/total/rounded_total untouched) and are classed mixed_legacy,
which excludes them from GST reports. This is intentionally NOT restored on
downgrade — the pre-migration tax figures were an accounting fiction.
"""

from alembic import op
import sqlalchemy as sa

revision = "o8p9q0r1s2t3"
down_revision = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None

billclass = sa.Enum("service", "product", "mixed_legacy", name="billclass")
taxmode = sa.Enum("exclusive", "inclusive", "none", name="taxmode")


def upgrade() -> None:
    bind = op.get_bind()
    billclass.create(bind, checkfirst=True)
    taxmode.create(bind, checkfirst=True)

    # bills
    op.add_column(
        "bills",
        sa.Column("bill_class", billclass, nullable=False, server_default="mixed_legacy"),
    )
    op.create_index("ix_bills_bill_class", "bills", ["bill_class"])
    op.add_column("bills", sa.Column("bill_group_id", sa.String(26), nullable=True))
    op.create_index("ix_bills_bill_group_id", "bills", ["bill_group_id"])

    # bill_items
    op.add_column("bill_items", sa.Column("tax_rate", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_items", sa.Column("tax_mode", taxmode, nullable=False, server_default="none"))
    op.add_column("bill_items", sa.Column("taxable_value", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_items", sa.Column("cgst_amount", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_items", sa.Column("sgst_amount", sa.Integer(), nullable=False, server_default="0"))

    # payments
    op.add_column("payments", sa.Column("payment_group_id", sa.String(26), nullable=True))
    op.create_index("ix_payments_payment_group_id", "payments", ["payment_group_id"])

    # Legacy backfill: zero out tax on all pre-registration bills.
    # Totals are untouched — customers paid exactly what they paid.
    op.execute("UPDATE bills SET tax_amount = 0, cgst_amount = 0, sgst_amount = 0")


def downgrade() -> None:
    op.drop_index("ix_payments_payment_group_id", table_name="payments")
    op.drop_column("payments", "payment_group_id")

    op.drop_column("bill_items", "sgst_amount")
    op.drop_column("bill_items", "cgst_amount")
    op.drop_column("bill_items", "taxable_value")
    op.drop_column("bill_items", "tax_mode")
    op.drop_column("bill_items", "tax_rate")

    op.drop_index("ix_bills_bill_group_id", table_name="bills")
    op.drop_column("bills", "bill_group_id")
    op.drop_index("ix_bills_bill_class", table_name="bills")
    op.drop_column("bills", "bill_class")

    bind = op.get_bind()
    taxmode.drop(bind, checkfirst=True)
    billclass.drop(bind, checkfirst=True)
