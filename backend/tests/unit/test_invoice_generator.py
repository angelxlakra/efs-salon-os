"""
  Unit tests for InvoiceNumberGenerator
"""

import freezegun
import pytest
from datetime import datetime
from freezegun import freeze_time  # We'll install this!
from app.services.invoice_generator import InvoiceNumberGenerator
from ulid import ULID

def create_minimal_bill(db_session, invoice_number: str, user):
    """
        Helper function to create a minimal bill for testing.

        Args:
          db_session: Database session
          invoice_number: Invoice number to assign (e.g., "SAL-25-0001")
          user: User object OR user ID string (flexible!)

        Returns:
          Bill: The created bill object
    """

    from app.models.billing import Bill, BillStatus

    # Handle both User object and user ID string
    if isinstance(user, str):
        user_id = user  # It's already a string ID
    else:
        user_id = user.id  # Extract ID from User object

    bill = Bill(
          invoice_number=invoice_number,
          subtotal=100000,  # ₹1,000 in paise
          discount_amount=0,
          tax_amount=18000,  # 18% GST
          cgst_amount=9000,
          sgst_amount=9000,
          total_amount=118000,
          rounded_total=118000,
          rounding_adjustment=0,
          status=BillStatus.POSTED,
          created_by=user_id
      )

    db_session.add(bill)
    db_session.flush()

    return bill


def test_generate_first_invoice(db_session):
    """
      Test generating the very first invoice.

      SCENARIO: No invoices exist in database
      EXPECTED: Should generate SAL-25-0001 (or current year)
    """

    invoice_number = InvoiceNumberGenerator.generate(db_session)

    assert invoice_number.startswith("SAL-"), "Should start with SAL"
    assert invoice_number.endswith("-0001"), "First invoice should be 0001"
    assert len(invoice_number) == 11, "Invoice should be SAL-YY-NNNN format"

    print(f"✅ Generated first invoice: {invoice_number}")


def test_generate_sequential_invoices(db_session, test_user):
    """
        Test that invoice numbers increment sequentially.

        SCENARIO: Generate 3 invoices in a row
        EXPECTED: Should get SAL-25-0001, SAL-25-0002, SAL-25-0003
    """

    invoice1 = InvoiceNumberGenerator.generate(db_session)
    create_minimal_bill(db_session, invoice1, test_user)

    invoice2 = InvoiceNumberGenerator.generate(db_session)
    create_minimal_bill(db_session, invoice2, test_user)

    invoice3 = InvoiceNumberGenerator.generate(db_session)
    create_minimal_bill(db_session, invoice3, test_user)

    assert invoice1 == "SAL-25-0001"
    assert invoice2 == "SAL-25-0002"
    assert invoice3 == "SAL-25-0003"

    assert invoice1.startswith("SAL-")
    assert invoice2.startswith("SAL-")
    assert invoice3.startswith("SAL-")

    print(f"✅ Sequential invoices: {invoice1}, {invoice2}, {invoice3}")

@freeze_time("2025-03-31")  # type: ignore
def test_fiscal_year_reset(db_session, test_user):
    """
        Test that invoice numbers reset on fiscal year change.

        SCENARIO: Generate invoice on March 31, 2025, then April 1 2025(new fiscal year)
        EXPECTED: March 31 -> SAL-24-0001; April 1 -> SAL-25-0001 (resets!)

    """

    invoice1 = InvoiceNumberGenerator.generate(db_session)
    create_minimal_bill(db_session, invoice1, test_user)

    assert invoice1 == "SAL-24-0001", f"Invoice on March 31 should be FY 24, got {invoice1}"

    with freeze_time("2025-04-01"):
        invoice2 = InvoiceNumberGenerator.generate(db_session)
        create_minimal_bill(db_session, invoice2, test_user)

    assert invoice2 == "SAL-25-0001", f"Invoice on April 1 should be FY 25, got {invoice2}"

    assert invoice1.endswith("-0001")
    assert invoice2.endswith("-0001")

    print(f"✅ Fiscal year rollover: {invoice1} → {invoice2}")

def test_handles_gap_in_sequence(db_session, test_user):
    """
        Test that the generator continues from MAX even with gaps.

        SCENARIO: Create invoices 0001, 0002, 0005 (simulating deletions at 0003 and 0004)
        EXPECTED: Next invoice should be 0006 (not 0003!)
    """

    invoices = []
    for i in range(5):
        invoice = InvoiceNumberGenerator.generate(db_session)
        bill = create_minimal_bill(db_session, invoice, test_user)
        invoices.append((invoice, bill))
    

    # Delete invoice 3 & 4
    db_session.delete(invoices[2][1])
    db_session.delete(invoices[3][1])
    db_session.flush()

    new_invoice = InvoiceNumberGenerator.generate(db_session)
    create_minimal_bill(db_session, new_invoice, test_user)

    assert new_invoice.endswith("-0006"), f"Should have correct gap/Expected->SAL-25-0006\nGOT->{new_invoice}"
    assert new_invoice.split("-")[1] == "25"


def test_invoice_format_is_valid(db_session, test_user):
    """
        Test that generated invoice numbers always match the expected format.

        SCENARIO: Generate multiple invoices and verify format
        EXPECTED: All should match SAL-YY-NNNN format
    """

    invoices = []

    for _ in range(5):
        invoice = InvoiceNumberGenerator.generate(db_session)
        create_minimal_bill(db_session, invoice, test_user)
        invoices.append(invoice)

    
    import re
    from app.config import settings

    pattern = r"^SAL-\d{2}-\d{4}$"
    current_fiscal_year = datetime.now().strftime("%y")

    for invoice in invoices:
        assert re.match(pattern, invoice), \
            f"Invoice {invoice} doesn't match format SAL-YY-NNNN"
        
        parts = invoice.split("-")


        assert len(parts) == 3, f"Should have 3 parts (SAL, YY, NNNN), got {len(parts)}"
        assert parts[0] == settings.invoice_prefix, f"Prefix should be '{settings.invoice_prefix}', got {parts[0]}"
        assert parts[1] == current_fiscal_year, \
            f"Fiscal year should be current FY({current_fiscal_year}), got {parts[1]}"
        assert len(parts[1]) == 2, f"Fiscal year should be 2 digits, got {len(parts[1])}"
        assert parts[2].isdigit(), "Number parts should be digits"
        assert len(parts[2]) == 4, f"Number part should be length 4, got {len(parts[2])}"


def test_concurrent_invoice_generation_no_duplicates(test_engine):
    """
        Test that concurrent invoice generation doesn't create duplicates.

        SCENARIO: Simulate multiple requests generating invoices at the same time
        EXPECTED: No duplicate invoice numbers (advisory lock prevents race conditions)

        NOTE: This test manages its own sessions and cleanup since it needs
        to commit data that threads can see.
    """

    import threading
    from sqlalchemy.orm import sessionmaker
    from app.models.user import User, Role, RoleEnum
    from app.models.billing import Bill

    # Step 1: Create and commit test user that all threads can reference
    SessionLocal = sessionmaker(bind=test_engine)
    setup_session = SessionLocal()

    try:
        # Create test role and user
        role = Role(
            name=RoleEnum.OWNER,
            description="Test owner role for concurrent test",
            permissions={"*": ["*"]}
        )
        setup_session.add(role)
        setup_session.flush()

        user = User(
            role_id=role.id,
            username="concurrent_test_user",
            email="concurrent@test.com",
            password_hash="fake_hash_for_testing",
            full_name="Concurrent Test User",
            is_active=True
        )
        setup_session.add(user)
        setup_session.commit()  # COMMIT so threads can see this user

        user_id = user.id  # Extract ID for threads

    except Exception as e:
        setup_session.rollback()
        setup_session.close()
        raise AssertionError(f"Failed to create test user: {e}")
    finally:
        setup_session.close()

    # Step 2: Run concurrent invoice generation
    generated_invoices = []
    errors = []
    lock = threading.Lock()

    def generate_invoice_in_thread():
        """
            Function that runs in a separate thread.
            Each thread creates its own database session and generates an invoice.

            NOTE: This is the SIMPLE version - just generate and create.
            If there's a race condition bug, this test will FAIL with duplicates!
        """
        thread_session = SessionLocal()

        try:
            # Generate invoice (advisory lock inside generator)
            invoice = InvoiceNumberGenerator.generate(thread_session)

            # Create the bill
            create_minimal_bill(thread_session, invoice, user_id)

            # Commit the transaction
            thread_session.commit()

            with lock:
                generated_invoices.append(invoice)

        except Exception as e:
            thread_session.rollback()
            with lock:
                errors.append(str(e))
        finally:
            thread_session.close()

    # Launch threads
    threads = []
    num_threads = 10

    for _ in range(num_threads):
        thread = threading.Thread(target=generate_invoice_in_thread)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Step 3: Cleanup - delete all test data
    cleanup_session = SessionLocal()
    try:
        cleanup_session.query(Bill).filter(Bill.created_by == user_id).delete()
        cleanup_session.query(User).filter(User.id == user_id).delete()
        cleanup_session.query(Role).filter(Role.name == RoleEnum.OWNER).delete()
        cleanup_session.commit()
    except Exception:
        cleanup_session.rollback()
    finally:
        cleanup_session.close()

    # Step 4: Assertions
    if errors:
        raise AssertionError(f"Threads failed with errors: {errors[:3]}")

    assert len(generated_invoices) == num_threads, \
        f"Should generate {num_threads} invoices, got {len(generated_invoices)}"

    unique_invoices = set(generated_invoices)
    assert len(unique_invoices) == num_threads, \
        f"Should have {num_threads} unique invoices, found duplicates: {generated_invoices}"

    invoice_numbers = sorted([int(inv.split("-")[2]) for inv in generated_invoices])
    expected_numbers = list(range(1, num_threads + 1))

    assert invoice_numbers == expected_numbers, \
        f"Invoices should be sequential 1-{num_threads}, got {invoice_numbers}"

    print(f"✅ Generated {num_threads} concurrent invoices without duplicates:")
    for inv in sorted(generated_invoices):
        print(f"   {inv}")

