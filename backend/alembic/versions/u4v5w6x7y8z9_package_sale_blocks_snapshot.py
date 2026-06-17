"""Add blocks_snapshot to package_sales for block-labelled entitlement display.

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-06-13

Stores the v2 block stack as sold on each PackageSale, so the customer
entitlements view can render block labels (Pick N, Unlimited, Credit, …)
alongside the per-line consumption tracked on package_sale_items.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "u4v5w6x7y8z9"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_sales",
        sa.Column("blocks_snapshot", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("package_sales", "blocks_snapshot")
