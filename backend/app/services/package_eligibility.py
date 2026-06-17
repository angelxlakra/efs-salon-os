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

    from app.models.package import PackageSaleBlock

    # Block counters (choice@visit / pool) that still have budget.
    good_blocks = (
        db.query(PackageSaleBlock.id).filter(PackageSaleBlock.remaining > 0)
    )

    # Sales whose matching line is "independent" of the global session pool —
    # a pool-exempt (unlimited) line OR a block-counted line. These bypass the
    # EXHAUSTED status and empty-pool gates, staying redeemable to expiry.
    independent_sales = (
        db.query(PackageSaleItem.package_sale_id)
          .filter(PackageSaleItem.service_id == service_id)
          .filter(or_(
              PackageSaleItem.pool_exempt.is_(True),
              PackageSaleItem.sale_block_id.isnot(None),
          ))
    )

    # Sales with a matching line that has budget right now.
    budget_ok_sales = (
        db.query(PackageSaleItem.package_sale_id)
          .filter(PackageSaleItem.service_id == service_id)
          .filter(or_(
              # Block-counted line whose block still has budget.
              and_(
                  PackageSaleItem.sale_block_id.isnot(None),
                  PackageSaleItem.sale_block_id.in_(good_blocks),
              ),
              # Pool-exempt (unlimited) line — always.
              PackageSaleItem.pool_exempt.is_(True),
              # Global-pool / per-line-capped line.
              and_(
                  PackageSaleItem.sale_block_id.is_(None),
                  PackageSaleItem.pool_exempt.is_(False),
                  or_(
                      PackageSaleItem.max_redemptions.is_(None),
                      PackageSaleItem.remaining > 0,
                  ),
              ),
          ))
    )

    return (
        db.query(PackageSale)
          .filter(and_(
              or_(
                  PackageSale.status == PackageSaleStatus.ACTIVE,
                  and_(
                      PackageSale.status == PackageSaleStatus.EXHAUSTED,
                      PackageSale.id.in_(independent_sales),
                  ),
              ),
              PackageSale.expires_at > now,
              PackageSale.id.in_(budget_ok_sales),
              or_(
                  PackageSale.entitlement_type_snapshot == EntitlementType.UNLIMITED,
                  PackageSale.sessions_remaining > 0,
                  PackageSale.id.in_(independent_sales),
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
