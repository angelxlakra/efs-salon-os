"""merge migration heads

Revision ID: 09164dc44353
Revises: 1a137ed244c2, 6a7b8c9d0e1f
Create Date: 2026-01-29 08:54:14.802292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09164dc44353'
down_revision: Union[str, None] = ('1a137ed244c2', '6a7b8c9d0e1f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
