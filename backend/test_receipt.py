#!/usr/bin/env python3
"""Test receipt generation with current salon settings.

This script generates a test receipt PDF using your actual salon settings.
Run with: python test_receipt.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.billing import Bill
from app.services.receipt_service import ReceiptService

def main():
    db = SessionLocal()

    try:
        # Get the most recent posted bill
        bill = db.query(Bill).filter(
            Bill.status == 'posted'
        ).order_by(Bill.created_at.desc()).first()

        if not bill:
            print("❌ No posted bills found in database.")
            print("💡 Create a bill in POS and complete payment first.")
            return

        print(f"📄 Found bill: {bill.invoice_number or bill.id}")
        print(f"   Customer: {bill.customer_name or 'Walk-in'}")
        print(f"   Total: ₹{bill.rounded_total / 100:.2f}")
        print(f"   Items: {len(bill.items)}")

        # Generate receipt
        print("\n🖨️  Generating receipt PDF...")
        pdf_buffer = ReceiptService.generate_receipt_pdf(bill, db)

        # Save to file
        output_file = Path(__file__).parent / f"test_receipt_{bill.invoice_number or 'draft'}.pdf"
        with open(output_file, 'wb') as f:
            f.write(pdf_buffer.getvalue())

        print(f"✅ Receipt saved to: {output_file}")
        print(f"\n📱 Open the PDF to view:")
        print(f"   open {output_file}")
        print(f"\n🖨️  Print to thermal printer:")
        print(f"   lp -d YOUR_PRINTER_NAME {output_file}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
