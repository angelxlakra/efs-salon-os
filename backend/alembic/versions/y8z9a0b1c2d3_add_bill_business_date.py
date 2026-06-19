"""Add bills.business_date for work-day revenue attribution.

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-06-18

Revenue is attributed to the IST day the WORK was done, not the day a (possibly
late) checkout posted the bill. Set at bill creation from the earliest linked
walk-in's day. Backfills existing bills the same way: earliest linked walk-in's
day, else the bill's own creation day. (Tax filing still keys on posted_at.)
"""

from alembic import op
import sqlalchemy as sa

revision = "y8z9a0b1c2d3"
down_revision = "x7y8z9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("business_date", sa.Date(), nullable=True))
    op.create_index("ix_bills_business_date", "bills", ["business_date"])

    # Backfill 1: bills with linked walk-ins → earliest walk-in's IST work day.
    op.execute(
        """
        UPDATE bills b
        SET business_date = sub.work_date
        FROM (
            SELECT bill_id,
                   MIN(DATE(timezone('Asia/Kolkata',
                                     COALESCE(checked_in_at, created_at)))) AS work_date
            FROM walkins
            WHERE bill_id IS NOT NULL
            GROUP BY bill_id
        ) sub
        WHERE b.id = sub.bill_id
        """
    )
    # Backfill 2: every remaining bill → its own creation day (IST).
    op.execute(
        """
        UPDATE bills
        SET business_date = DATE(timezone('Asia/Kolkata', created_at))
        WHERE business_date IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_bills_business_date", "bills")
    op.drop_column("bills", "business_date")
