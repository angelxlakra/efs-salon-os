"""Add salon settings table

Revision ID: 01d5c8e3f4a1
Revises: 5f8f6222177c
Create Date: 2026-01-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '01d5c8e3f4a1'
down_revision: Union[str, None] = '5f8f6222177c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create salon_settings table
    op.create_table('salon_settings',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Business Information
        sa.Column('salon_name', sa.String(length=255), nullable=False, server_default='SalonOS'),
        sa.Column('salon_tagline', sa.String(length=255), nullable=True),
        sa.Column('salon_address', sa.Text(), nullable=False),
        sa.Column('salon_city', sa.String(length=100), nullable=True),
        sa.Column('salon_state', sa.String(length=100), nullable=True),
        sa.Column('salon_pincode', sa.String(length=20), nullable=True),

        # Contact Information
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_website', sa.String(length=255), nullable=True),

        # Tax Information
        sa.Column('gstin', sa.String(length=15), nullable=True),
        sa.Column('pan', sa.String(length=10), nullable=True),

        # Receipt Customization
        sa.Column('receipt_header_text', sa.Text(), nullable=True),
        sa.Column('receipt_footer_text', sa.Text(), nullable=True),
        sa.Column('receipt_show_gstin', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('receipt_show_logo', sa.Boolean(), server_default='false', nullable=True),

        # Branding
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('primary_color', sa.String(length=7), server_default='#000000', nullable=True),

        # Invoice Settings
        sa.Column('invoice_prefix', sa.String(length=10), nullable=False, server_default='SAL'),
        sa.Column('invoice_terms', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('salon_settings')
