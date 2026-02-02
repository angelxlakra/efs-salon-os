"""make_customer_phone_nullable_and_non_unique

Revision ID: f27fc6b8b70f
Revises: f4c4095917d2
Create Date: 2026-02-02 18:53:59.934151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f27fc6b8b70f'
down_revision: Union[str, None] = 'f4c4095917d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop unique index on phone
    op.drop_index('ix_customers_phone', table_name='customers')

    # Step 2: Make phone column nullable
    op.alter_column('customers', 'phone',
                    existing_type=sa.String(),
                    nullable=True)

    # Step 3: Update existing dummy phone numbers to NULL
    op.execute("UPDATE customers SET phone = NULL WHERE phone = '0000000000'")

    # Step 4: Re-create index without unique constraint
    op.create_index('ix_customers_phone', 'customers', ['phone'], unique=False)


def downgrade() -> None:
    # Drop the non-unique index
    op.drop_index('ix_customers_phone', table_name='customers')

    # Make phone not nullable again (will fail if there are NULL values)
    op.alter_column('customers', 'phone',
                    existing_type=sa.String(),
                    nullable=False)

    # Re-create unique index
    op.create_index('ix_customers_phone', 'customers', ['phone'], unique=True)
