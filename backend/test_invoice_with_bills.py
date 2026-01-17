"""Test invoice generator by actually creating bills.

This test creates real Bill records with invoice numbers to verify
the generator works correctly when integrated with the database.
"""

from datetime import datetime
from app.database import SessionLocal
from app.models.billing import Bill, BillStatus
from app.services.invoice_generator import InvoiceNumberGenerator
from ulid import ULID


def test_invoice_generation_with_bills():
    """Test invoice generation by creating actual bills."""
    print("\n" + "="*60)
    print("INVOICE GENERATOR TEST - WITH BILL CREATION")
    print("="*60)

    db = SessionLocal()

    try:
        print("\nCreating 5 bills with sequential invoice numbers...\n")

        created_bills = []
        invoice_numbers = []

        for i in range(5):
            # Generate invoice number
            invoice_number = InvoiceNumberGenerator.generate(db)
            invoice_numbers.append(invoice_number)

            # Create a bill with this invoice number
            bill = Bill(
                id=str(ULID()),
                invoice_number=invoice_number,
                customer_name=f"Test Customer {i+1}",
                customer_phone="9876543210",
                subtotal=100000,  # Rs 1000 in paise
                discount_amount=0,
                tax_amount=15254,
                cgst_amount=7627,
                sgst_amount=7627,
                total_amount=115254,
                rounded_total=115300,
                rounding_adjustment=46,
                status=BillStatus.POSTED,
                posted_at=datetime.utcnow(),
                created_by="01TEST00000000000000000000"  # Dummy user ID (26 chars)
            )

            db.add(bill)
            db.commit()  # Commit after each bill
            db.refresh(bill)

            created_bills.append(bill)
            print(f"  Bill {i+1}: {invoice_number} (ID: {bill.id})")

        # Verify sequential
        print("\n" + "-"*60)
        print("Verifying sequential numbering...")
        print("-"*60)

        numbers = [int(inv.split('-')[2]) for inv in invoice_numbers]

        for i in range(1, len(numbers)):
            diff = numbers[i] - numbers[i-1]
            print(f"  {invoice_numbers[i-1]} → {invoice_numbers[i]} (diff: {diff})")
            assert diff == 1, f"❌ Not sequential: {numbers[i-1]} -> {numbers[i]}"

        print("\n✅ All invoice numbers are sequential!")
        print(f"   Range: {invoice_numbers[0]} to {invoice_numbers[-1]}")

        # Verify all bills are in database
        print("\n" + "-"*60)
        print("Verifying bills are saved in database...")
        print("-"*60)

        for bill in created_bills:
            db_bill = db.query(Bill).filter(Bill.id == bill.id).first()
            assert db_bill is not None, f"❌ Bill {bill.id} not found in database"
            assert db_bill.invoice_number == bill.invoice_number, \
                f"❌ Invoice number mismatch for bill {bill.id}"
            print(f"  ✓ Bill {db_bill.invoice_number}: Found in database")

        print("\n✅ All bills saved correctly!")

        # Test that next invoice increments from last one
        print("\n" + "-"*60)
        print("Testing next invoice continues sequence...")
        print("-"*60)

        next_invoice = InvoiceNumberGenerator.generate(db)
        next_num = int(next_invoice.split('-')[2])
        last_num = numbers[-1]

        print(f"  Last generated: {invoice_numbers[-1]} (number: {last_num})")
        print(f"  Next generated: {next_invoice} (number: {next_num})")

        assert next_num == last_num + 1, \
            f"❌ Next invoice should be {last_num + 1}, got {next_num}"

        print(f"\n✅ Next invoice continues sequence correctly!")

        # Clean up - delete test bills
        print("\n" + "-"*60)
        print("Cleaning up test data...")
        print("-"*60)

        for bill in created_bills:
            db.delete(bill)

        # Delete the last test invoice we created
        last_bill = db.query(Bill).filter(Bill.invoice_number == next_invoice).first()
        if last_bill:
            db.delete(last_bill)

        db.commit()
        print("✅ Test data cleaned up")

        # Final summary
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✅ Invoice generator works correctly")
        print("✅ Sequential numbering verified")
        print("✅ Database integration working")
        print("✅ No gaps in sequence\n")

    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"\nError: {e}\n")

        # Cleanup on failure
        print("Attempting cleanup...")
        try:
            for bill in created_bills:
                db.delete(bill)
            db.commit()
            print("✅ Cleanup completed")
        except:
            print("⚠️  Cleanup failed - may need manual cleanup")

        raise

    except Exception as e:
        print("\n" + "="*60)
        print("❌ UNEXPECTED ERROR!")
        print("="*60)
        print(f"\nError: {e}\n")

        # Cleanup on error
        print("Attempting cleanup...")
        try:
            db.rollback()
            print("✅ Rolled back transaction")
        except:
            print("⚠️  Rollback failed")

        raise

    finally:
        db.close()


if __name__ == "__main__":
    test_invoice_generation_with_bills()
