"""Invoice number generator for bills.

  This module provides atomic generation of sequential invoice numbers
  using PostgreSQL advisory locks to prevent race conditions.

  Invoice Number Format: SAL-YY-NNNN
  - SAL: Prefix for salon
  - YY: Fiscal year (starts April 1st)
  - NNNN: Sequential number (resets each fiscal year)

  Examples:
      SAL-25-0001  (First invoice of FY 2025-26)
      SAL-25-0042  (42nd invoice of FY 2025-26)
      SAL-26-0001  (First invoice of FY 2026-27, after April 1st)

  The generator uses PostgreSQL advisory locks to ensure no gaps or
  duplicates even under concurrent load.
"""

from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

class InvoiceNumberGenerator:
    """Generate sequential invoice numbers atomically.

      Uses PostgreSQL advisory locks to ensure thread-safe, gap-free
      invoice number generation across multiple processes.

      Attributes:
          ADVISORY_LOCK_ID: PostgreSQL advisory lock identifier (12345)
          INVOICE_PREFIX: Invoice number prefix ("SAL")
    """

    ADVISORY_LOCK_ID = 987123
    INVOICE_PREFIX = "SAL"

    @classmethod
    def generate(cls, db: Session) -> str:
        """Generate next invoice number atomically.

            Acquires a PostgreSQL transaction-scoped advisory lock, queries the
            current max invoice number for the fiscal year, and increments it.
            The lock is automatically released when the transaction commits or rolls back.

            Args:
                db: SQLAlchemy database session.

            Returns:
                str: Next invoice number in format SAL-YY-NNNN

            Example:
                >>> generator = InvoiceNumberGenerator()
                >>> generator.generate(db)
                'SAL-25-0042'

            Raises:
                SQLAlchemyError: If database query fails.

            Note:
                - Fiscal year starts April 1st
                - Numbers reset to 0001 each fiscal year
                - Uses pg_advisory_xact_lock (transaction-scoped)
                - Lock is held until transaction commits, preventing race conditions
                - Multiple calls in the same transaction will see the same lock
        """

        now = datetime.now()
        if now.month >= 4:
            fiscal_year = now.strftime("%y")
        else:
            fiscal_year = (now.year - 1) % 100
            fiscal_year = f"{fiscal_year:02d}"

        # Use transaction-scoped advisory lock (automatically released on commit/rollback)
        # This ensures the lock is held until the transaction completes, preventing
        # race conditions where multiple threads generate the same invoice number
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": cls.ADVISORY_LOCK_ID})

        pattern = f"{cls.INVOICE_PREFIX}-{fiscal_year}-%"

        result = db.execute(
            text("""
                    SELECT COALESCE(MAX(
                        CAST(SPLIT_PART(invoice_number, '-', 3) AS INTEGER)
                    ), 0) as max_num
                    FROM bills
                    WHERE invoice_number LIKE :pattern
                """), {"pattern": pattern}
        ).first()

        max_num = result.max_num if result else 0

        next_num = max_num + 1
        invoice_number = f"{cls.INVOICE_PREFIX}-{fiscal_year}-{next_num:04d}"

        return invoice_number

        # Note: No finally block needed! pg_advisory_xact_lock is automatically
        # released when the transaction commits or rolls back

