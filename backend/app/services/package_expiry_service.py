"""Expiry extension and batch transition service for PackageSales."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.package import PackageSale, PackageSaleStatus, PackageExpiryExtension
from app.services.package_pricing_engine import can_extend_expiry


def extend_expiry(
    db: Session,
    sale_id: str,
    new_expires_at: datetime,
    reason: str,
    user_id: str,
) -> PackageSale:
    """Extend a PackageSale's expiry date forward.

    Raises ValueError if sale not found.
    Raises DomainError (from can_extend_expiry) if new_expires_at is invalid.
    If sale was EXPIRED and new date is valid, restores to ACTIVE.
    """
    sale = db.get(PackageSale, sale_id)
    if not sale:
        raise ValueError(f"PackageSale {sale_id} not found")

    can_extend_expiry(sale, new_expires_at)  # raises DomainError if invalid

    ext = PackageExpiryExtension(
        package_sale_id=sale.id,
        previous_expires_at=sale.expires_at,
        new_expires_at=new_expires_at,
        performed_by_user_id=user_id,
        extended_at=datetime.now(timezone.utc),
        reason=reason,
    )
    db.add(ext)

    sale.expires_at = new_expires_at
    if sale.status == PackageSaleStatus.EXPIRED:
        sale.status = PackageSaleStatus.ACTIVE

    db.flush()
    return sale


def run_expiry_transitions(db: Session) -> dict:
    """Bulk-mark ACTIVE sales with expires_at < now() as EXPIRED.

    Called by the daily job. Uses db.flush() — caller is responsible for commit.
    Returns a dict with count of transitioned sales.
    """
    now = datetime.now(timezone.utc)
    rows = db.query(PackageSale).filter(
        PackageSale.status == PackageSaleStatus.ACTIVE,
        PackageSale.expires_at < now,
    ).all()
    for sale in rows:
        sale.status = PackageSaleStatus.EXPIRED
    db.flush()
    return {"transitioned": len(rows)}
