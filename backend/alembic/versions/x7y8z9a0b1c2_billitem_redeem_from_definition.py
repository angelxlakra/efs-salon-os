"""Add BillItem.redeem_from_definition_id for buy-and-use-immediately.

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa

revision = "x7y8z9a0b1c2"
down_revision = "w6x7y8z9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bill_items",
        sa.Column("redeem_from_definition_id", sa.String(26),
                  sa.ForeignKey("package_definitions.id", ondelete="RESTRICT"),
                  nullable=True),
    )
    op.create_index(
        "ix_bill_items_redeem_from_definition_id", "bill_items",
        ["redeem_from_definition_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bill_items_redeem_from_definition_id", "bill_items")
    op.drop_column("bill_items", "redeem_from_definition_id")
