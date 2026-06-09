"""Package eligibility queries — DB-touching logic for finding redeemable packages.

Intentionally separate from package_pricing_engine.py so that the pricing
engine remains a pure-function module with no SQLAlchemy dependencies.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.package import (
    EntitlementType,
    PackageSale,
    PackageSaleItem,
    PackageSaleStatus,
    Shareability,
)


def find_eligible_packages(
    customer_id: str,
    service_id: str,
    db: Session,
) -> List[PackageSale]:
    """Return active PackageSales where this customer can redeem this service.

    Filters:
      - status = 'active'
      - expires_at > now()
      - service_id is in the sale's snapshot items
      - sessions_remaining > 0 OR entitlement_type='unlimited'
      - shareability rule: owner_only requires customer_id == sale.customer_id;
        shared allows any customer

    Ordered: expires_at ASC (FIFO by soonest expiry).
    """
    now = datetime.now(timezone.utc)

    return (
        db.query(PackageSale)
          .filter(and_(
              PackageSale.status == PackageSaleStatus.ACTIVE,
              PackageSale.expires_at > now,
              PackageSale.id.in_(
                  db.query(PackageSaleItem.package_sale_id)
                    .filter(PackageSaleItem.service_id == service_id)
                    .filter(
                        or_(
                            PackageSaleItem.max_redemptions.is_(None),
                            PackageSaleItem.remaining > 0,
                        )
                    )
              ),
              or_(
                  PackageSale.entitlement_type_snapshot == EntitlementType.UNLIMITED,
                  PackageSale.sessions_remaining > 0,
              ),
              or_(
                  and_(
                      PackageSale.shareability_snapshot == Shareability.OWNER_ONLY,
                      PackageSale.customer_id == customer_id,
                  ),
                  PackageSale.shareability_snapshot == Shareability.SHARED,
              ),
          ))
          .order_by(PackageSale.expires_at.asc())
          .all()
    )
