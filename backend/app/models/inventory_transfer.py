"""Local inventory transfer tracking model.

Each record represents one inter-store transfer as seen by this store:
- direction=OUT: this store sent stock to another store
- direction=IN:  this store received stock from another store

The central_transfer_id links to the central API's inventory_transfers table.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class InventoryTransfer(Base, ULIDMixin, TimestampMixin):
    """Local record of a single inter-store inventory transfer."""

    __tablename__ = "inventory_transfers"

    # Central API reference (populated after successful POST /v1/transfers)
    central_transfer_id = Column(String(26), unique=True, nullable=True)

    # Direction from this store's perspective
    direction = Column(String(3), nullable=False)  # 'OUT' or 'IN'

    # The other store involved
    other_store_name = Column(String(255), nullable=False)

    # Product info (denormalised so the record is self-contained)
    sku_id = Column(String(26), ForeignKey("skus.id"), nullable=True)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True)

    # Quantities and costs — all in paise (INTEGER)
    quantity = Column(Integer, nullable=False)
    unit_cost_paise = Column(Integer, nullable=False)
    total_cost_paise = Column(Integer, nullable=False)

    # Linked expense entry (TRANSFER_OUT or TRANSFER_IN)
    expense_id = Column(String(26), ForeignKey("expenses.id"), nullable=True)

    # Status mirrors the central API: PENDING → APPLIED | CANCELLED
    status = Column(String(30), nullable=False, default="PENDING")

    # Timestamps
    initiated_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<InventoryTransfer {self.direction} {self.product_name} "
            f"×{self.quantity} [{self.status}]>"
        )
