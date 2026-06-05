"""make appointment service_id nullable

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'k4l5m6n7o8p9'
down_revision = 'j3k4l5m6n7o8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('appointments', 'service_id', nullable=True)


def downgrade() -> None:
    # Re-applying NOT NULL requires all rows to already have a value.
    # Set NULLs to a sentinel before adding the constraint back.
    op.execute("UPDATE appointments SET service_id = (SELECT id FROM services LIMIT 1) WHERE service_id IS NULL")
    op.alter_column('appointments', 'service_id', nullable=False)
