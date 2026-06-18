"""Independent per-block redemption counters for v2 packages.

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-06-14

choice@visit and pool blocks get their own budget (shared across the block's
options, separate from the global session pool). The counter lives in
package_sale_blocks; each governed PackageSaleItem points at it via
sale_block_id.
"""

from alembic import op
import sqlalchemy as sa

revision = "w6x7y8z9a0b1"
down_revision = "v5w6x7y8z9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "package_sale_blocks",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "package_sale_id", sa.String(26),
            sa.ForeignKey("package_sales.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("remaining", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("remaining >= 0",
                           name="ck_package_sale_block_remaining_non_negative"),
    )
    op.add_column(
        "package_sale_items",
        sa.Column("sale_block_id", sa.String(26),
                  sa.ForeignKey("package_sale_blocks.id", ondelete="CASCADE"),
                  nullable=True),
    )
    op.create_index(
        "ix_package_sale_items_sale_block_id", "package_sale_items", ["sale_block_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_package_sale_items_sale_block_id", "package_sale_items")
    op.drop_column("package_sale_items", "sale_block_id")
    op.drop_table("package_sale_blocks")
