"""merge_denomination_and_supplier_tracking

Revision ID: 7d84edca4b93
Revises: b2c3d4e5f6g7, a150137636a1
Create Date: 2026-02-06 19:42:15.032916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d84edca4b93'
down_revision: Union[str, None] = ('b2c3d4e5f6g7', 'a150137636a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
