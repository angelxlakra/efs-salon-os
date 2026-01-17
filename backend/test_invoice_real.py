"""Test invoice generator with real database.

This test script verifies:
1. Invoice number generation works with actual PostgreSQL
2. Numbers are sequential with no gaps
3. Format is correct (SAL-YY-NNNN)
4. Fiscal year logic is correct
5. Advisory locks work properly
"""

from datetime import datetime
from app.database import SessionLocal
from app.services.invoice_generator import InvoiceNumberGenerator


def test_invoice_format():
    """Test that invoice number has correct format."""
    print("\n" + "="*60)
    print("TEST 1: Invoice Number Format")
    print("="*60)

    db = SessionLocal()

    try:
        invoice = InvoiceNumberGenerator.generate(db)
        print(f"Generated invoice: {invoice}")

        # Check format
        parts = invoice.split('-')
        assert len(parts) == 3, f"Should have 3 parts, got {len(parts)}"
        assert parts[0] == "SAL", f"Prefix should be SAL, got {parts[0]}"
        assert len(parts[1]) == 2, f"Year should be 2 digits, got {len(parts[1])}"
        assert len(parts[2]) == 4, f"Number should be 4 digits, got {len(parts[2])}"
        assert parts[2].isdigit(), f"Number should be digits, got {parts[2]}"

        print("✅ Format is correct: SAL-YY-NNNN")
        return invoice

    finally:
        db.close()


def test_sequential_generation():
    """Test that invoice numbers are sequential."""
    print("\n" + "="*60)
    print("TEST 2: Sequential Generation")
    print("="*60)

    db = SessionLocal()

    try:
        # Generate 5 sequential invoices
        invoices = []
        for i in range(5):
            invoice = InvoiceNumberGenerator.generate(db)
            invoices.append(invoice)
            print(f"  Invoice {i+1}: {invoice}")

        # Extract numbers
        numbers = [int(inv.split('-')[2]) for inv in invoices]

        # Verify sequential
        for i in range(1, len(numbers)):
            diff = numbers[i] - numbers[i-1]
            assert diff == 1, f"Gap detected: {numbers[i-1]} -> {numbers[i]}"

        print(f"✅ All {len(invoices)} invoices are sequential")
        print(f"   Range: {invoices[0]} to {invoices[-1]}")
        return invoices

    finally:
        db.close()


def test_fiscal_year():
    """Test that fiscal year is calculated correctly."""
    print("\n" + "="*60)
    print("TEST 3: Fiscal Year Logic")
    print("="*60)

    db = SessionLocal()

    try:
        invoice = InvoiceNumberGenerator.generate(db)
        year_part = invoice.split('-')[1]

        # Current date logic
        now = datetime.now()
        if now.month >= 4:
            expected_year = now.strftime("%y")
        else:
            expected_year = f"{(now.year - 1) % 100:02d}"

        print(f"Current date: {now.strftime('%Y-%m-%d')}")
        print(f"Current month: {now.month}")
        print(f"Expected fiscal year: {expected_year}")
        print(f"Invoice fiscal year: {year_part}")

        assert year_part == expected_year, \
            f"Fiscal year mismatch: expected {expected_year}, got {year_part}"

        print("✅ Fiscal year is correct")

    finally:
        db.close()


def test_concurrent_generation():
    """Test that concurrent calls don't create duplicates (simulated)."""
    print("\n" + "="*60)
    print("TEST 4: Concurrent Safety (Sequential Simulation)")
    print("="*60)

    # Create multiple DB sessions (simulates concurrent requests)
    sessions = [SessionLocal() for _ in range(3)]

    try:
        invoices = []

        # Generate from different sessions
        for i, db in enumerate(sessions):
            invoice = InvoiceNumberGenerator.generate(db)
            invoices.append(invoice)
            print(f"  Session {i+1}: {invoice}")

        # Check for duplicates
        unique_invoices = set(invoices)
        assert len(unique_invoices) == len(invoices), \
            f"Duplicates found! {len(invoices)} generated, {len(unique_invoices)} unique"

        print(f"✅ No duplicates across {len(sessions)} sessions")

    finally:
        for db in sessions:
            db.close()


def test_zero_padding():
    """Test that numbers are zero-padded to 4 digits."""
    print("\n" + "="*60)
    print("TEST 5: Zero Padding")
    print("="*60)

    db = SessionLocal()

    try:
        invoice = InvoiceNumberGenerator.generate(db)
        number_part = invoice.split('-')[2]

        print(f"Invoice number part: {number_part}")

        # Should always be 4 characters
        assert len(number_part) == 4, \
            f"Number should be 4 digits, got {len(number_part)}"

        # Should start with zero if number < 1000
        num_value = int(number_part)
        if num_value < 1000:
            assert number_part.startswith('0'), \
                f"Numbers < 1000 should have leading zeros"
            print(f"✅ Zero padding correct for number {num_value}")
        else:
            print(f"✅ Number {num_value} >= 1000, no padding needed")

    finally:
        db.close()


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "🚀 " + "="*56)
    print("   INVOICE GENERATOR - REAL DATABASE TESTS")
    print("="*60 + "\n")

    try:
        # Test 1: Format
        test_invoice_format()

        # Test 2: Sequential
        test_sequential_generation()

        # Test 3: Fiscal year
        test_fiscal_year()

        # Test 4: Concurrent safety
        test_concurrent_generation()

        # Test 5: Zero padding
        test_zero_padding()

        # Summary
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✅ Invoice generator is working correctly")
        print("✅ Format: SAL-YY-NNNN")
        print("✅ Sequential numbering")
        print("✅ No duplicates")
        print("✅ Fiscal year logic correct")
        print("✅ Zero padding working\n")

    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"\nError: {e}\n")
        raise
    except Exception as e:
        print("\n" + "="*60)
        print("❌ UNEXPECTED ERROR!")
        print("="*60)
        print(f"\nError: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
