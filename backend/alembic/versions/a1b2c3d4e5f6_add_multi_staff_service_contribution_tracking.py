"""Add multi-staff service contribution tracking

Revision ID: a1b2c3d4e5f6
Revises: e0c1c3273fbb
Create Date: 2026-02-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e0c1c3273fbb'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types (check if exists first to handle production data restores)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contributiontype AS ENUM ('percentage', 'fixed', 'equal');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contributionsplittype AS ENUM ('percentage', 'fixed', 'equal', 'time_based', 'hybrid');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create service_staff_templates table
    op.create_table(
        'service_staff_templates',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('service_id', sa.String(length=26), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('role_description', sa.Text(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('contribution_type', postgresql.ENUM('percentage', 'fixed', 'equal', name='contributiontype', create_type=False), nullable=False, server_default='percentage'),
        sa.Column('default_contribution_percent', sa.Integer(), nullable=True),
        sa.Column('default_contribution_fixed', sa.Integer(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_service_staff_templates_service_id', 'service_staff_templates', ['service_id'])

    # Create bill_item_staff_contributions table
    op.create_table(
        'bill_item_staff_contributions',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('bill_item_id', sa.String(length=26), nullable=False),
        sa.Column('staff_id', sa.String(length=26), nullable=False),
        sa.Column('role_in_service', sa.String(length=100), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('contribution_split_type', postgresql.ENUM('percentage', 'fixed', 'equal', 'time_based', 'hybrid', name='contributionsplittype', create_type=False), nullable=False, server_default='percentage'),
        sa.Column('contribution_percent', sa.Integer(), nullable=True),
        sa.Column('contribution_fixed', sa.Integer(), nullable=True),
        sa.Column('contribution_amount', sa.Integer(), nullable=False),
        sa.Column('time_spent_minutes', sa.Integer(), nullable=True),
        sa.Column('base_percent_component', sa.Integer(), nullable=True),
        sa.Column('time_component', sa.Integer(), nullable=True),
        sa.Column('skill_component', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bill_item_id'], ['bill_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bill_item_staff_contributions_bill_item_id', 'bill_item_staff_contributions', ['bill_item_id'])
    op.create_index('ix_bill_item_staff_contributions_staff_id', 'bill_item_staff_contributions', ['staff_id'])


def downgrade():
    # Drop tables
    op.drop_index('ix_bill_item_staff_contributions_staff_id', table_name='bill_item_staff_contributions')
    op.drop_index('ix_bill_item_staff_contributions_bill_item_id', table_name='bill_item_staff_contributions')
    op.drop_table('bill_item_staff_contributions')

    op.drop_index('ix_service_staff_templates_service_id', table_name='service_staff_templates')
    op.drop_table('service_staff_templates')

    # Drop enum types (check if exists first)
    op.execute('DROP TYPE IF EXISTS contributionsplittype')
    op.execute('DROP TYPE IF EXISTS contributiontype')
