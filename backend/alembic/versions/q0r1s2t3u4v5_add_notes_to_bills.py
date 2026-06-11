"""Add notes column to bills.

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-06-11

void_bill and complete_bill have always written the void reason / pending-
balance note to bill.notes, but the column was never created — so voiding a
bill WITH a reason raised AttributeError. This adds the missing column.
"""

from alembic import op
import sqlalchemy as sa

revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bills", "notes")
