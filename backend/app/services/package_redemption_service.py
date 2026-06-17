"""Apply / undo redemptions with concurrency control."""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.package import (
    PackageSale, PackageSaleItem, PackageRedemptionAudit, PackageSaleStatus, EntitlementType,
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

    bill_item = db.get(BillItem, bill_item_id)
    if not bill_item:
        raise ValueError(f"BillItem {bill_item_id} not found")

    # Match by service_id to find the PackageSaleItem (resolved BEFORE the
    # status/sessions gates so a pool-exempt unlimited line can relax them).
    sale_item = next(
        (i for i in sale.items if i.service_id == bill_item.service_id),
        None,
    )
    if not sale_item:
        raise ValueError("Service not covered by this package")

    # A line is governed by EXACTLY one budget: an independent block counter,
    # the pool-exempt (unlimited) free perk, or the global session pool.
    block = None
    if sale_item.sale_block_id is not None:
        block = next(
            (b for b in sale.block_counters if b.id == sale_item.sale_block_id), None
        )
    independent = sale_item.pool_exempt or block is not None

    # 1. Status gate. EXHAUSTED blocks redemption EXCEPT for independent lines
    #    (block-counted or pool-exempt), which stay redeemable until expiry.
    if sale.status == PackageSaleStatus.EXHAUSTED and independent:
        pass
    elif sale.status != PackageSaleStatus.ACTIVE:
        raise ValueError(f"Package not active (status={sale.status.value})")

    # 2. Expiry check (applies to everything)
    if sale.expires_at <= now:
        raise ValueError("Package expired")

    # A redeemed line covers `quantity` units, each consuming one budget unit.
    qty = bill_item.quantity or 1

    # 3. Budget check — enough budget to cover the WHOLE line.
    if block is not None:
        if block.remaining < qty:
            raise ValueError(f"'{block.name}' budget exhausted for this package")
    elif not sale_item.pool_exempt:
        # Global session pool (COUNTED only).
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
            if not sale.sessions_remaining or sale.sessions_remaining < qty:
                raise ValueError("no sessions remaining")
        # Per-line cap enforcement.
        # TODO: all ValueError in this codebase maps to HTTP 400 at the router
        # layer. When router-layer exception handling is unified to 422 for
        # domain rule violations, this surfaces with the correct status code.
        if sale_item.remaining is not None and sale_item.remaining < qty:
            raise ValueError("Per-line redemption cap exhausted for this service")

    # Update BillItem — set price to the snapshotted package price
    bill_item.item_type = BillItemType.PACKAGE_REDEMPTION
    bill_item.package_sale_id = sale.id
    bill_item.package_sale_item_id = sale_item.id
    bill_item.base_price = sale_item.snapshot_unit_price_paise
    bill_item.line_total = bill_item.base_price * qty

    # Decrement the governing budget by the line quantity.
    session_number = None
    if block is not None:
        block.remaining -= qty  # safe: guarded by the sale-row lock
    elif not sale_item.pool_exempt:
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
            session_number = (
                (sale.total_sessions_snapshot or 0) - (sale.sessions_remaining or 0) + 1
            )
            sale.sessions_remaining -= qty
            if sale.sessions_remaining == 0:
                sale.status = PackageSaleStatus.EXHAUSTED
        if sale_item.remaining is not None:
            sale_item.remaining -= qty

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

    # Restore whichever budget the redemption drew from. A block-counted or
    # pool-exempt line never touched the global session pool.
    sale_item = db.get(PackageSaleItem, audit.package_sale_item_id)
    block = None
    if sale_item is not None and sale_item.sale_block_id is not None:
        from app.models.package import PackageSaleBlock
        block = db.get(PackageSaleBlock, sale_item.sale_block_id)
    pool_exempt = bool(sale_item and sale_item.pool_exempt)
    qty = bill_item.quantity or 1  # apply_redemption drew `quantity` budget units

    if block is not None:
        block.remaining += qty
    elif not pool_exempt:
        # Restore global session counter (COUNTED only).
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
            sale.sessions_remaining = (sale.sessions_remaining or 0) + qty
            if sale.status == PackageSaleStatus.EXHAUSTED:
                sale.status = PackageSaleStatus.ACTIVE
        # Restore per-line counter.
        if sale_item is not None and sale_item.remaining is not None:
            sale_item.remaining += qty

    # NOTE: Payment is matched by (bill_id, payment_method, amount). This triple is not
    # unique if two redemptions of equal value occur on the same bill. A future migration
    # should add payment_id to PackageRedemptionAudit to make the lookup exact.
    internal_pay = db.execute(
        select(Payment).where(
            Payment.bill_id == bill.id,
            Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION,
            Payment.amount == expected_payment_amount,
        )
    ).scalar_one_or_none()
    if internal_pay is None:
        raise ValueError(
            "Internal PACKAGE_REDEMPTION payment row not found — data integrity problem. "
            "Undo aborted to avoid partial state."
        )
    db.delete(internal_pay)

    db.delete(audit)
    db.flush()
