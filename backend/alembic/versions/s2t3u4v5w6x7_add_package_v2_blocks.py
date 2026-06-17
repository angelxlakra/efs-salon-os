"""Add Package Builder v2 block stack + stored price to package_definitions.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-06-13

The v2 builder models a package as a stack of entitlement blocks (fixed items,
choice group, unlimited, session pool, credit) rather than a flat items list.
`blocks` stores that stack as JSON; `stored_price_paise` holds the builder's
computed sell price. Both NULL for existing v1 packages, whose price stays
derived from `items` + discount.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_definitions",
        sa.Column("blocks", JSONB(), nullable=True),
    )
    op.add_column(
        "package_definitions",
        sa.Column("stored_price_paise", sa.Integer(), nullable=True),
    )
    # Relax the entitlement/sessions check so v2 block packages (no sessions
    # envelope) are valid. v1 rows still satisfy the original two branches.
    op.drop_constraint(
        "ck_package_def_entitlement_sessions", "package_definitions", type_="check"
    )
    op.create_check_constraint(
        "ck_package_def_entitlement_sessions",
        "package_definitions",
        "(blocks IS NOT NULL) "
        "OR (entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
        "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_package_def_entitlement_sessions", "package_definitions", type_="check"
    )
    op.create_check_constraint(
        "ck_package_def_entitlement_sessions",
        "package_definitions",
        "(entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
        "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
    )
    op.drop_column("package_definitions", "stored_price_paise")
    op.drop_column("package_definitions", "blocks")
