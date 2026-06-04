"""Apply / undo redemptions with concurrency control."""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.package import (
    PackageSale, PackageRedemptionAudit, PackageSaleStatus, EntitlementType,
)
from app.models.billing import BillItem, BillItemType, Bill, BillStatus, Payment, PaymentMethod


def apply_redemption(
    db: Session,
    package_sale_id: str,
    bill_item_id: str,
    redeemed_for_customer_id: str,
    user_id: str,
) -> PackageRedemptionAudit:
    """Apply a redemption to a BillItem against a PackageSale.

    Uses SELECT FOR UPDATE on PackageSale to prevent concurrent over-redemption.
    Decrements sessions, creates audit row, flips BillItem to PACKAGE_REDEMPTION,
    creates an internal Payment row (amount = bill_item.base_price * quantity).

    Raises ValueError for all domain errors.
    """
    now = datetime.now(timezone.utc)

    # Lock the PackageSale row for this transaction
    sale = db.execute(
        select(PackageSale).where(PackageSale.id == package_sale_id).with_for_update()
    ).scalar_one_or_none()
    if not sale:
        raise ValueError(f"PackageSale {package_sale_id} not found")

    # 1. Status must be ACTIVE (EXHAUSTED, EXPIRED, REFUNDED are all disallowed here)
    if sale.status != PackageSaleStatus.ACTIVE:
        raise ValueError(f"Package not active (status={sale.status.value})")

    # 2. Expiry check
    if sale.expires_at <= now:
        raise ValueError("Package expired")

    # 3. Sessions check (COUNTED packages only)
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        if not sale.sessions_remaining or sale.sessions_remaining <= 0:
            raise ValueError("no sessions remaining")

    bill_item = db.get(BillItem, bill_item_id)
    if not bill_item:
        raise ValueError(f"BillItem {bill_item_id} not found")

    # Match by service_id to find the PackageSaleItem
    sale_item = next(
        (i for i in sale.items if i.service_id == bill_item.service_id),
        None,
    )
    if not sale_item:
        raise ValueError("Service not covered by this package")

    # Update BillItem — set price to the snapshotted package price
    bill_item.item_type = BillItemType.PACKAGE_REDEMPTION
    bill_item.package_sale_id = sale.id
    bill_item.package_sale_item_id = sale_item.id
    bill_item.base_price = sale_item.snapshot_unit_price_paise
    bill_item.line_total = bill_item.base_price * bill_item.quantity

    # Decrement sessions (COUNTED only)
    session_number = None
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        session_number = (
            (sale.total_sessions_snapshot or 0) - (sale.sessions_remaining or 0) + 1
        )
        sale.sessions_remaining -= 1
        if sale.sessions_remaining == 0:
            sale.status = PackageSaleStatus.EXHAUSTED

    # Audit row
    audit = PackageRedemptionAudit(
        package_sale_id=sale.id,
        bill_item_id=bill_item.id,
        package_sale_item_id=sale_item.id,
        redeemed_for_customer_id=redeemed_for_customer_id,
        performed_by_user_id=user_id,
        redeemed_at=now,
        session_number=session_number,
    )
    db.add(audit)

    # Internal Payment row — confirmed_at and confirmed_by are non-nullable
    payment = Payment(
        bill_id=bill_item.bill_id,
        amount=bill_item.base_price * bill_item.quantity,
        payment_method=PaymentMethod.PACKAGE_REDEMPTION,
        confirmed_at=now,
        confirmed_by=user_id,
    )
    db.add(payment)

    db.flush()
    return audit


def undo_redemption(db: Session, audit_id: str, user_id: str) -> None:
    """Inverse of apply_redemption. Only allowed on DRAFT bills.

    Restores sessions_remaining, reverts BillItem to SERVICE type,
    deletes the internal Payment row, and deletes the audit row.

    Raises ValueError for all domain errors.
    """
    audit = db.get(PackageRedemptionAudit, audit_id)
    if not audit:
        raise ValueError(f"Audit row {audit_id} not found")

    bill_item = db.get(BillItem, audit.bill_item_id)
    if not bill_item:
        raise ValueError(f"BillItem {audit.bill_item_id} not found")

    bill = db.get(Bill, bill_item.bill_id)
    if not bill:
        raise ValueError(f"Bill {bill_item.bill_id} not found")
    if bill.status != BillStatus.DRAFT:
        raise ValueError("Undo only allowed on draft bills")

    # Lock the sale row before modifying
    sale = db.execute(
        select(PackageSale)
        .where(PackageSale.id == audit.package_sale_id)
        .with_for_update()
    ).scalar_one()

    # Capture the package price BEFORE restoring bill_item.base_price
    # (apply_redemption set base_price = snapshot_unit_price_paise)
    package_price_at_redemption = bill_item.base_price
    expected_payment_amount = package_price_at_redemption * bill_item.quantity

    # Restore BillItem to original service price
    from app.models.service import Service  # local import avoids circular dependency
    svc = db.get(Service, bill_item.service_id)
    original_price = svc.base_price if svc else bill_item.base_price
    bill_item.item_type = BillItemType.SERVICE
    bill_item.package_sale_id = None
    bill_item.package_sale_item_id = None
    bill_item.base_price = original_price
    bill_item.line_total = original_price * bill_item.quantity

    # Restore session counter
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        sale.sessions_remaining = (sale.sessions_remaining or 0) + 1
        if sale.status == PackageSaleStatus.EXHAUSTED:
            sale.status = PackageSaleStatus.ACTIVE

    # Find and delete the matching PACKAGE_REDEMPTION Payment row.
    # Match on bill_id + payment_method + amount (package price, captured before restore).
    internal_pay = db.execute(
        select(Payment).where(
            Payment.bill_id == bill.id,
            Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION,
            Payment.amount == expected_payment_amount,
        )
    ).scalar_one_or_none()
    if internal_pay:
        db.delete(internal_pay)

    db.delete(audit)
    db.flush()
