"""add_brand_name_and_volume_to_skus

Revision ID: f4c4095917d2
Revises: 31b428a12b36
Create Date: 2026-01-31 10:39:18.758912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4c4095917d2'
down_revision: Union[str, None] = '31b428a12b36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add brand_name and volume columns to skus table
    op.add_column('skus', sa.Column('brand_name', sa.String(255), nullable=True))
    op.add_column('skus', sa.Column('volume', sa.String(50), nullable=True))


def downgrade() -> None:
    # Remove brand_name and volume columns from skus table
    op.drop_column('skus', 'volume')
    op.drop_column('skus', 'brand_name')
