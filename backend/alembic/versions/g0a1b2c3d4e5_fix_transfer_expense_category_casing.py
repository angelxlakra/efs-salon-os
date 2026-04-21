"""Fix TRANSFER_OUT/TRANSFER_IN enum casing to match SQLAlchemy name-based storage.

Revision ID: g0a1b2c3d4e5
Revises: f9a0b1c2d3e4
Create Date: 2026-03-03 18:30:00.000000

Problem:
- Migration f9a0b1c2d3e4 added 'transfer_out' and 'transfer_in' (lowercase) to the
  expensecategory PostgreSQL enum.
- SQLAlchemy stores Python enum NAMES (e.g. 'TRANSFER_OUT'), not values ('transfer_out').
- All other enum labels in the DB are uppercase (RENT, SALARIES, etc.).
- This mismatch causes DataError: invalid input value for enum expensecategory: "TRANSFER_OUT"

Fix:
- Add 'TRANSFER_OUT' and 'TRANSFER_IN' (uppercase) to the enum.
- PostgreSQL does not allow dropping enum values, so the lowercase variants remain
  as dead labels (they are never written by the application).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g0a1b2c3d4e5'
down_revision: Union[str, None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL 12+ allows ALTER TYPE ADD VALUE inside a transaction.
    # No AUTOCOMMIT needed — just execute directly.
    op.execute(sa.text("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'TRANSFER_OUT'"))
    op.execute(sa.text("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'TRANSFER_IN'"))


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE on an enum type.
    # No action needed — the uppercase labels remain as no-ops.
    pass
