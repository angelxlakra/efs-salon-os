"""Add invoice and ticket number generator functions

Revision ID: 597eeb0d2ec7
Revises: 94d0a1476464
Create Date: 2025-10-17 15:31:38.048715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '597eeb0d2ec7'
down_revision: Union[str, None] = '94d0a1476464'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence for invoice numbers starting with 2025
    op.execute("CREATE SEQUENCE invoice_sequence_2025 START 1;")

    # Create invoice number generator function
    op.execute("""
        CREATE OR REPLACE FUNCTION generate_invoice_number()
        RETURNS TEXT AS $$
        DECLARE
            current_year TEXT;
            next_num INTEGER;
            invoice_num TEXT;
        BEGIN
            current_year := TO_CHAR(CURRENT_DATE, 'YY');

            -- Get next number from sequence for current year
            next_num := nextval('invoice_sequence_' || '20' || current_year);

            invoice_num := 'SAL-' || current_year || '-' || LPAD(next_num::TEXT, 4, '0');

            RETURN invoice_num;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create ticket number generator function
    op.execute("""
        CREATE OR REPLACE FUNCTION generate_ticket_number()
        RETURNS TEXT AS $$
        DECLARE
            date_part TEXT;
            count INTEGER;
            ticket_num TEXT;
        BEGIN
            date_part := TO_CHAR(CURRENT_DATE, 'YYMMDD');

            -- Count existing tickets for today
            SELECT COUNT(*) + 1 INTO count
            FROM (
                SELECT ticket_number FROM appointments
                WHERE ticket_number LIKE 'TKT-' || date_part || '%'
                UNION ALL
                SELECT ticket_number FROM walkins
                WHERE ticket_number LIKE 'TKT-' || date_part || '%'
            ) AS tickets;

            ticket_num := 'TKT-' || date_part || '-' || LPAD(count::TEXT, 3, '0');

            RETURN ticket_num;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS generate_ticket_number();")
    op.execute("DROP FUNCTION IF EXISTS generate_invoice_number();")

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS invoice_sequence_2025;")
