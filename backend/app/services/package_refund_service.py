"""Issue refund credit notes for PackageSales."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.package import PackageSale, PackageSaleStatus
from app.models.billing import (
    Bill, BillType, BillStatus, BillItem, BillItemType,
    Payment, PaymentMethod,
)
from app.services.package_pricing_engine import compute_refund

# Map incoming payment_method strings (from API) to PaymentMethod enum.
# "pending_balance" has no dedicated enum value, so it maps to OTHER.
_METHOD_MAP = {
    "cash": PaymentMethod.CASH,
    "upi": PaymentMethod.UPI,
    "card": PaymentMethod.CARD,
    "pending_balance": PaymentMethod.OTHER,
}


def issue_refund(
    db: Session,
    package_sale_id: str,
    payment_method: str,
    reason: str,
    user_id: str,
) -> Bill:
    """Issue a credit-note Bill for a PackageSale refund.

    Computes the refund breakdown via compute_refund(), creates a credit note
    Bill with two line items (refund value + cancellation fee), creates a
    Payment row, and marks the PackageSale as REFUNDED.

    Uses db.flush() only — transaction belongs to the caller.

    Raises:
        ValueError: if the sale does not exist or is already refunded.
    """
    sale = db.get(PackageSale, package_sale_id)
    if not sale:
        raise ValueError(f"PackageSale {package_sale_id} not found")
    if sale.status == PackageSaleStatus.REFUNDED:
        raise ValueError("Package already refunded")

    # Load original bill and attach to sale so compute_refund can access
    # sale.bill.total_paise for UNLIMITED (time-pro-rata) packages.
    original_bill = db.get(Bill, sale.bill_id)
    sale.bill = original_bill

    breakdown = compute_refund(sale)
    if breakdown.refund_paise == 0:
        raise ValueError("No refundable value remaining on this package sale")
    now = datetime.now(timezone.utc)

    # Credit note total is negative: money owed back to the customer.
    # net_total = -(refund_paise) because the fee is already deducted inside
    # breakdown.refund_paise (refund = base - fee).
    net_total = -breakdown.refund_paise

    credit_note = Bill(
        customer_id=sale.customer_id,
        bill_type=BillType.CREDIT_NOTE,
        original_bill_id=sale.bill_id,
        subtotal=net_total,
        discount_amount=0,
        # Prices are tax-inclusive; no additional GST on the refund credit note.
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=net_total,
        rounded_total=net_total,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        created_by=user_id,
        refund_reason=reason,
    )
    db.add(credit_note)
    db.flush()  # materialise credit_note.id before referencing it in FKs

    # Line item 1: unredeemed value being refunded (credit — negative amount).
    refund_li = BillItem(
        bill_id=credit_note.id,
        # No service_id or sku_id on credit lines; constraint requires package type.
        item_type=BillItemType.PACKAGE_SALE_LINE,
        item_name="Package refund — unredeemed value",
        base_price=-breakdown.base_paise,
        quantity=1,
        line_total=-breakdown.base_paise,
        package_sale_id=sale.id,
    )
    db.add(refund_li)

    # Line item 2: cancellation fee retained by the salon (positive — deducted from refund).
    fee_pct = sale.cancellation_fee_pct_snapshot
    fee_li = BillItem(
        bill_id=credit_note.id,
        item_type=BillItemType.PACKAGE_SALE_LINE,
        item_name=f"Cancellation fee ({fee_pct}%)",
        base_price=breakdown.fee_paise,
        quantity=1,
        line_total=breakdown.fee_paise,
        package_sale_id=sale.id,
    )
    db.add(fee_li)

    # Payment row: positive amount = cash being paid out to the customer.
    pay_method = _METHOD_MAP.get(payment_method, PaymentMethod.OTHER)
    payment = Payment(
        bill_id=credit_note.id,
        amount=breakdown.refund_paise,
        payment_method=pay_method,
        confirmed_at=now,
        confirmed_by=user_id,
    )
    db.add(payment)

    # Mark the sale as refunded and link back to the credit note.
    sale.status = PackageSaleStatus.REFUNDED
    sale.refunded_at = now
    sale.refund_bill_id = credit_note.id

    db.flush()
    return credit_note
