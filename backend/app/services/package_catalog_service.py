"""CRUD for PackageDefinition with discount distribution and lifecycle checks."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.package import (
    PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus,
    PackageSale, PackageSaleStatus,
)
from app.schemas.package import PackageDefinitionCreate, PackageDefinitionUpdate
from app.services.package_pricing_engine import (
    distribute_discount, DiscountedItem, DiscountMode,
)


def _validate_discount(payload_items, discount):
    """Dry-run the discount distribution so invalid discounts fail at save time.

    Items are persisted at GROSS prices and the discount is stored alongside;
    actual distribution happens at sale time (and in final_price_paise).
    """
    if not discount:
        return
    item_drafts = [
        DiscountedItem(
            unit_price_paise=i.unit_price_paise,
            quantity=i.quantity,
            locked=i.locked,
        )
        for i in payload_items
    ]
    distribute_discount(item_drafts, DiscountMode(discount.mode), discount.value)


def _build_items(payload_items):
    """Build ORM items at their gross (entered) prices."""
    return [
        PackageDefinitionItem(
            service_id=src.service_id,
            quantity=src.quantity,
            unit_price_paise=src.unit_price_paise,
            locked=src.locked,
            display_order=src.display_order,
            max_redemptions=src.max_redemptions,
        )
        for src in payload_items
    ]


def create_definition(
    db: Session, payload: PackageDefinitionCreate, user_id: str
) -> PackageDefinition:
    """Create a new PackageDefinition in DRAFT status.

    Persists gross item prices plus the discount; validation dry-runs the
    distribution so an impossible discount is rejected up front.
    """
    _validate_discount(payload.items, payload.discount)
    pkg = PackageDefinition(
        name=payload.name,
        description=payload.description,
        entitlement_type=payload.entitlement_type,
        total_sessions=payload.total_sessions,
        shareability=payload.shareability,
        validity_days=payload.validity_days,
        auto_apply=payload.auto_apply,
        cancellation_fee_pct=payload.cancellation_fee_pct,
        discount_mode=payload.discount.mode if payload.discount else None,
        discount_value=payload.discount.value if payload.discount else None,
        blocks=payload.blocks,
        stored_price_paise=payload.final_price_paise,
        created_by_user_id=user_id,
        status=PackageDefinitionStatus.DRAFT,
    )
    pkg.items = _build_items(payload.items)
    db.add(pkg)
    db.flush()
    return pkg


def update_definition(
    db: Session, def_id: str, payload: PackageDefinitionUpdate
) -> PackageDefinition:
    """Wholesale-replace a PackageDefinition's items in a single flush.

    Clears existing items via cascade then re-inserts with optional discount.
    """
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    pkg.name = payload.name
    pkg.description = payload.description
    pkg.entitlement_type = payload.entitlement_type
    pkg.total_sessions = payload.total_sessions
    pkg.shareability = payload.shareability
    pkg.validity_days = payload.validity_days
    pkg.auto_apply = payload.auto_apply
    pkg.cancellation_fee_pct = payload.cancellation_fee_pct
    pkg.discount_mode = payload.discount.mode if payload.discount else None
    pkg.discount_value = payload.discount.value if payload.discount else None
    pkg.blocks = payload.blocks
    pkg.stored_price_paise = payload.final_price_paise
    pkg.items.clear()
    db.flush()  # DELETE orphans before re-inserting

    _validate_discount(payload.items, payload.discount)
    pkg.items = _build_items(payload.items)
    db.flush()
    return pkg


def publish(db: Session, def_id: str) -> PackageDefinition:
    """Transition a DRAFT PackageDefinition to PUBLISHED."""
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    if pkg.status != PackageDefinitionStatus.DRAFT:
        raise ValueError("Only draft packages can be published")
    pkg.status = PackageDefinitionStatus.PUBLISHED
    db.flush()
    return pkg


def archive(db: Session, def_id: str) -> PackageDefinition:
    """Archive a PackageDefinition (stops it appearing in new sales).

    Can be called on DRAFT or PUBLISHED. Raises if already ARCHIVED.
    """
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    if pkg.status == PackageDefinitionStatus.ARCHIVED:
        raise ValueError("Package is already archived")
    pkg.status = PackageDefinitionStatus.ARCHIVED
    db.flush()
    return pkg


def soft_delete(db: Session, def_id: str) -> None:
    """Soft-delete a PackageDefinition.

    Raises ValueError if any active PackageSales reference this definition.
    """
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    if pkg.deleted_at is not None:
        raise ValueError(f"PackageDefinition {def_id} is already deleted")
    active_count = (
        db.query(PackageSale)
        .filter(
            PackageSale.package_definition_id == def_id,
            PackageSale.status == PackageSaleStatus.ACTIVE,
        )
        .count()
    )
    if active_count > 0:
        raise ValueError(f"Cannot delete: {active_count} active sales exist")
    pkg.deleted_at = datetime.now(timezone.utc)
    db.flush()
