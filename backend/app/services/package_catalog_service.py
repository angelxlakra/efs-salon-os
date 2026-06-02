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


def _apply_discount(payload_items, discount):
    """Apply optional discount distribution to item price list."""
    item_drafts = [
        DiscountedItem(
            unit_price_paise=i.unit_price_paise,
            quantity=i.quantity,
            locked=i.locked,
        )
        for i in payload_items
    ]
    if discount:
        item_drafts = distribute_discount(
            item_drafts, DiscountMode(discount.mode), discount.value,
        )
    return item_drafts


def _build_items(payload_items, item_drafts):
    """Zip payload items with discounted drafts into ORM objects."""
    return [
        PackageDefinitionItem(
            service_id=src.service_id,
            quantity=draft.quantity,
            unit_price_paise=draft.unit_price_paise,
            locked=draft.locked,
            display_order=src.display_order,
        )
        for src, draft in zip(payload_items, item_drafts)
    ]


def create_definition(
    db: Session, payload: PackageDefinitionCreate, user_id: str
) -> PackageDefinition:
    """Create a new PackageDefinition in DRAFT status.

    Applies optional discount distribution to item prices before persisting.
    """
    item_drafts = _apply_discount(payload.items, payload.discount)
    pkg = PackageDefinition(
        name=payload.name,
        description=payload.description,
        entitlement_type=payload.entitlement_type,
        total_sessions=payload.total_sessions,
        shareability=payload.shareability,
        validity_days=payload.validity_days,
        auto_apply=payload.auto_apply,
        cancellation_fee_pct=payload.cancellation_fee_pct,
        created_by_user_id=user_id,
        status=PackageDefinitionStatus.DRAFT,
    )
    pkg.items = _build_items(payload.items, item_drafts)
    db.add(pkg)
    db.flush()
    return pkg


def update_definition(
    db: Session, def_id: str, payload: PackageDefinitionUpdate, user_id: str
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
    pkg.items.clear()
    db.flush()  # DELETE orphans before re-inserting

    item_drafts = _apply_discount(payload.items, payload.discount)
    pkg.items = _build_items(payload.items, item_drafts)
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
    """Archive a PackageDefinition (stops it appearing in new sales)."""
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
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
