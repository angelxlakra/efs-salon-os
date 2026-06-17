"""Add persisted discount columns to package_definitions.

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-06-12

Items now keep their GROSS (entered) prices and the package-level discount
is stored on the definition itself, applied at sale time:
  - package_definitions.discount_mode   (nullable: 'pct' | 'flat' | 'final')
  - package_definitions.discount_value  (nullable: paise for flat/final, % for pct)

Existing rows stay NULL — their item prices were already discounted at save
time under the old behavior, so they remain correct as-is (no backfill).
"""

from alembic import op
import sqlalchemy as sa

revision = "r1s2t3u4v5w6"
down_revision = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_definitions",
        sa.Column("discount_mode", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "package_definitions",
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_package_def_discount_pair",
        "package_definitions",
        "(discount_mode IS NULL AND discount_value IS NULL) "
        "OR (discount_mode IN ('pct', 'flat', 'final') AND discount_value IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_package_def_discount_pair", "package_definitions", type_="check"
    )
    op.drop_column("package_definitions", "discount_value")
    op.drop_column("package_definitions", "discount_mode")
