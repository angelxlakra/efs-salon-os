"""Add date_of_birth to users table.

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-03-08 00:00:00.000000

Adds optional date_of_birth (DATE, nullable) to the users table.
Only month and day are meaningful; year is stored as 1900 (placeholder).
Used for the dashboard birthday tile feature.
"""
from alembic import op
import sqlalchemy as sa

revision = 'j3k4l5m6n7o8'
down_revision = 'i2j3k4l5m6n7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'date_of_birth')
