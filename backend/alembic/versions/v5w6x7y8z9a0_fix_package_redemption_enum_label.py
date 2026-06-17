"""Add the 'PACKAGE_REDEMPTION' label to the paymentmethod enum.

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-06-14

`Column(Enum(PaymentMethod))` (no values_callable) persists the enum NAME, so
the internal package-redemption payment is written as 'PACKAGE_REDEMPTION'
(uppercase). The packages migration only added the lowercase value
'package_redemption' (the enum's .value), which SQLAlchemy never writes — so
redeeming a service in a real bill failed with an invalid-enum DataError. Add
the uppercase label the ORM actually uses. (Test DBs built from metadata via
create_all already have it, which is why this slipped past the suite.)
"""

from alembic import op
import sqlalchemy as sa

revision = "v5w6x7y8z9a0"
down_revision = "u4v5w6x7y8z9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'PACKAGE_REDEMPTION'")
        )


def downgrade() -> None:
    # PostgreSQL cannot drop a value from an enum type; leave it in place.
    pass
