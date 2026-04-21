"""add_write_off_fields_to_bills

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-03-01 10:00:00.000000

Adds four columns to the bills table to support Option B write-offs:
- write_off_amount: paise forgiven (separate from discount_amount)
- write_off_at: when the write-off was recorded
- write_off_reason: free-text reason
- write_off_approved_by: FK to users.id (owner who approved)

These columns intentionally do NOT alter discount_amount or rounded_total
so that the original bill totals remain accurate for GST reporting.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Amount forgiven in paise — separate tracking from discount_amount
    op.add_column(
        'bills',
        sa.Column('write_off_amount', sa.Integer(), nullable=False, server_default='0')
    )
    # Remove server_default after backfill — Python model default handles new rows
    op.alter_column('bills', 'write_off_amount', server_default=None)

    # Timestamp of the write-off action (nullable: NULL means never written off)
    op.add_column(
        'bills',
        sa.Column('write_off_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Free-text reason supplied by the owner at write-off time
    op.add_column(
        'bills',
        sa.Column('write_off_reason', sa.Text(), nullable=True)
    )

    # FK to users.id — owner who approved the write-off
    op.add_column(
        'bills',
        sa.Column('write_off_approved_by', sa.String(26), nullable=True)
    )
    op.create_foreign_key(
        'fk_bills_write_off_approved_by',
        'bills', 'users',
        ['write_off_approved_by'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_bills_write_off_approved_by', 'bills', type_='foreignkey')
    op.drop_column('bills', 'write_off_approved_by')
    op.drop_column('bills', 'write_off_reason')
    op.drop_column('bills', 'write_off_at')
    op.drop_column('bills', 'write_off_amount')
