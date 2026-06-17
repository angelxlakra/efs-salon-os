"""v2 package sell+redeem: pool_exempt sale items + bill-item locked choices.

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-06-13

- package_sale_items.pool_exempt: an unlimited-block line, redeemable without
  limit and without drawing the global session pool (survives EXHAUSTED).
- bill_items.package_locked_choices: purchase-time choice service_ids carried
  from cart to the PackageSale snapshot at settlement.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "t3u4v5w6x7y8"
down_revision = "s2t3u4v5w6x7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_sale_items",
        sa.Column("pool_exempt", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "bill_items",
        sa.Column("package_locked_choices", JSONB(), nullable=True),
    )
    # v2 sale items are synthesized from blocks, not definition items.
    op.alter_column(
        "package_sale_items", "package_definition_item_id", nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "package_sale_items", "package_definition_item_id", nullable=False
    )
    op.drop_column("bill_items", "package_locked_choices")
    op.drop_column("package_sale_items", "pool_exempt")
