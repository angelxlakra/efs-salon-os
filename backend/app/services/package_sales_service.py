"""Create PackageSale rows from PackageDefinition at bill finalization."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.package import (
    EntitlementType,
    PackageDefinition,
    PackageSale,
    PackageSaleItem,
    PackageSaleStatus,
)


def create_sale(
    db: Session,
    package_definition_id: str,
    bill_id: str,
    customer_id: str,
    selling_staff_id: str | None,
) -> PackageSale:
    """Atomically snapshot a PackageDefinition into a PackageSale + PackageSaleItems.

    Called from billing_service.finalize_bill() for each package_sale_line BillItem.
    Uses db.flush() only — transaction ownership belongs to the caller.

    Raises:
        ValueError: if the PackageDefinition does not exist.
    """
    pkg = db.get(PackageDefinition, package_definition_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {package_definition_id} not found")

    sold_at = datetime.now(timezone.utc)
    expires_at = sold_at + timedelta(days=pkg.validity_days)

    sale = PackageSale(
        bill_id=bill_id,
        package_definition_id=pkg.id,
        customer_id=customer_id,
        selling_staff_id=selling_staff_id,
        sold_at=sold_at,
        expires_at=expires_at,
        entitlement_type_snapshot=pkg.entitlement_type,
        shareability_snapshot=pkg.shareability,
        cancellation_fee_pct_snapshot=pkg.cancellation_fee_pct,
        total_sessions_snapshot=pkg.total_sessions,
        sessions_remaining=(
            pkg.total_sessions if pkg.entitlement_type == EntitlementType.COUNTED else None
        ),
        status=PackageSaleStatus.ACTIVE,
    )
    db.add(sale)
    db.flush()  # get sale.id before inserting items

    for def_item in pkg.items:
        item = PackageSaleItem(
            package_sale_id=sale.id,
            package_definition_item_id=def_item.id,
            service_id=def_item.service_id,
            quantity=def_item.quantity,
            snapshot_unit_price_paise=def_item.unit_price_paise,
            snapshot_gst_rate_pct=Decimal("0"),  # prices are tax-inclusive; no separate GST rate
            locked=def_item.locked,
            display_order=def_item.display_order,
            max_redemptions=def_item.max_redemptions,
            remaining=def_item.max_redemptions,  # initial counter == cap; null if uncapped
        )
        db.add(item)

    db.flush()
    return sale
