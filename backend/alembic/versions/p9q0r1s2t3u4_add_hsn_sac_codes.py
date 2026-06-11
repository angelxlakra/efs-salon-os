"""Add SAC code to services and HSN code to SKUs (GST invoice compliance).

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-06-11

Rule 46 CGST Rules requires the HSN/SAC code on each tax-invoice line.
NULL values fall back to the salon-level defaults added in n7o8p9q0r1s2
(default_service_sac_code=999721, default_product_hsn_code=3305).
"""

from alembic import op
import sqlalchemy as sa

revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("services", sa.Column("sac_code", sa.String(8), nullable=True))
    op.add_column("skus", sa.Column("hsn_code", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("skus", "hsn_code")
    op.drop_column("services", "sac_code")
