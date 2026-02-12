"""create_pending_payment_collections_table

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-02-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7g8h9i0'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import existing enum from PostgreSQL
    from sqlalchemy.dialects import postgresql
    payment_method_enum = postgresql.ENUM('cash', 'card', 'upi', 'other', name='paymentmethod', create_type=False)

    # Create pending_payment_collections table
    op.create_table(
        'pending_payment_collections',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('payment_method', payment_method_enum, nullable=False),
        sa.Column('reference_number', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('bill_id', sa.String(), nullable=True),
        sa.Column('collected_by', sa.String(), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_balance', sa.Integer(), nullable=False),
        sa.Column('new_balance', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_pending_payment_collections_customer_id', 'pending_payment_collections', ['customer_id'])
    op.create_index('ix_pending_payment_collections_bill_id', 'pending_payment_collections', ['bill_id'])
    op.create_index('ix_pending_payment_collections_collected_at', 'pending_payment_collections', ['collected_at'])

    # Create foreign keys
    op.create_foreign_key(
        'fk_pending_payment_collections_customer_id',
        'pending_payment_collections', 'customers',
        ['customer_id'], ['id']
    )
    op.create_foreign_key(
        'fk_pending_payment_collections_bill_id',
        'pending_payment_collections', 'bills',
        ['bill_id'], ['id']
    )
    op.create_foreign_key(
        'fk_pending_payment_collections_collected_by',
        'pending_payment_collections', 'users',
        ['collected_by'], ['id']
    )


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint('fk_pending_payment_collections_collected_by', 'pending_payment_collections', type_='foreignkey')
    op.drop_constraint('fk_pending_payment_collections_bill_id', 'pending_payment_collections', type_='foreignkey')
    op.drop_constraint('fk_pending_payment_collections_customer_id', 'pending_payment_collections', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_pending_payment_collections_collected_at', 'pending_payment_collections')
    op.drop_index('ix_pending_payment_collections_bill_id', 'pending_payment_collections')
    op.drop_index('ix_pending_payment_collections_customer_id', 'pending_payment_collections')

    # Drop table
    op.drop_table('pending_payment_collections')
