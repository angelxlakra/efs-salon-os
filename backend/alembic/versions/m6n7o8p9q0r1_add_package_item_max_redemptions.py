"""Add max_redemptions to package items and remaining to package_sale_items.

Revision ID: m6n7o8p9q0r1
Revises: edc2fc235e3b
Create Date: 2026-06-09

Adds per-line redemption caps to package definitions:
  - package_definition_items.max_redemptions  (nullable, the cap)
  - package_sale_items.max_redemptions        (snapshot of the cap at sale)
  - package_sale_items.remaining              (runtime counter; null = uncapped)

null on max_redemptions means "no per-line cap; this line draws from the
global sessions_remaining pool only."
"""

from alembic import op
import sqlalchemy as sa

revision = "m6n7o8p9q0r1"
down_revision = "edc2fc235e3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_definition_items",
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_package_def_item_max_redemptions_positive",
        "package_definition_items",
        "max_redemptions IS NULL OR max_redemptions >= 1",
    )

    op.add_column(
        "package_sale_items",
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
    )
    op.add_column(
        "package_sale_items",
        sa.Column("remaining", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_package_sale_item_max_redemptions_positive",
        "package_sale_items",
        "max_redemptions IS NULL OR max_redemptions >= 1",
    )
    op.create_check_constraint(
        "ck_package_sale_item_remaining_non_negative",
        "package_sale_items",
        "remaining IS NULL OR remaining >= 0",
    )
    op.create_check_constraint(
        "ck_package_sale_item_remaining_matches_cap",
        "package_sale_items",
        "(max_redemptions IS NULL AND remaining IS NULL) "
        "OR (max_redemptions IS NOT NULL AND remaining IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_package_sale_item_remaining_matches_cap",
        "package_sale_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_package_sale_item_remaining_non_negative",
        "package_sale_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_package_sale_item_max_redemptions_positive",
        "package_sale_items",
        type_="check",
    )
    op.drop_column("package_sale_items", "remaining")
    op.drop_column("package_sale_items", "max_redemptions")
    op.drop_constraint(
        "ck_package_def_item_max_redemptions_positive",
        "package_definition_items",
        type_="check",
    )
    op.drop_column("package_definition_items", "max_redemptions")
