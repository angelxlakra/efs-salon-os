"""Add GST registration mode fields to salon_settings.

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-06-11

GST mode (Phase 0 of the GST split-billing scheme):
  - gst_registered          explicit owner toggle; GSTIN alone never flips billing
  - gst_effective_from      date boundary; bills before it keep legacy inclusive-18% math
  - invoice_prefix_service  SRV invoice series for service bills
  - invoice_prefix_product  PRD invoice series for product bills
  - default_service_sac_code / default_product_hsn_code  Rule 46 line-item codes
"""

from alembic import op
import sqlalchemy as sa

revision = "n7o8p9q0r1s2"
down_revision = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "salon_settings",
        sa.Column("gst_registered", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "salon_settings",
        sa.Column("gst_effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "salon_settings",
        sa.Column("invoice_prefix_service", sa.String(10), nullable=False, server_default="SRV"),
    )
    op.add_column(
        "salon_settings",
        sa.Column("invoice_prefix_product", sa.String(10), nullable=False, server_default="PRD"),
    )
    op.add_column(
        "salon_settings",
        sa.Column("default_service_sac_code", sa.String(8), nullable=False, server_default="999721"),
    )
    op.add_column(
        "salon_settings",
        sa.Column("default_product_hsn_code", sa.String(8), nullable=False, server_default="3305"),
    )


def downgrade() -> None:
    op.drop_column("salon_settings", "default_product_hsn_code")
    op.drop_column("salon_settings", "default_service_sac_code")
    op.drop_column("salon_settings", "invoice_prefix_product")
    op.drop_column("salon_settings", "invoice_prefix_service")
    op.drop_column("salon_settings", "gst_effective_from")
    op.drop_column("salon_settings", "gst_registered")
