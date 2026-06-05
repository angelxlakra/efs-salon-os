"""add_package_definition_id_to_bill_items

Revision ID: edc2fc235e3b
Revises: l5m6n7o8p9q0
Create Date: 2026-06-05 10:55:43.862350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'edc2fc235e3b'
down_revision: Union[str, None] = 'l5m6n7o8p9q0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add package_definition_id FK column to bill_items.
    # Set when item_type=PACKAGE_SALE_LINE; used at finalization to create the PackageSale row.
    op.add_column('bill_items', sa.Column('package_definition_id', sa.String(length=26), nullable=True))
    op.create_index(op.f('ix_bill_items_package_definition_id'), 'bill_items', ['package_definition_id'], unique=False)
    op.create_foreign_key(
        None, 'bill_items', 'package_definitions',
        ['package_definition_id'], ['id'], ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint(None, 'bill_items', type_='foreignkey')
    op.drop_index(op.f('ix_bill_items_package_definition_id'), table_name='bill_items')
    op.drop_column('bill_items', 'package_definition_id')
