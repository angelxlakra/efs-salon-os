"""Package models — definitions, sales, redemptions, expiry extensions."""

import enum
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


class PackageDefinitionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EntitlementType(str, enum.Enum):
    COUNTED = "counted"
    UNLIMITED = "unlimited"


class Shareability(str, enum.Enum):
    OWNER_ONLY = "owner_only"
    SHARED = "shared"


class PackageDefinition(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    """Catalog row. Edits don't affect already-sold packages (snapshots protect them)."""
    __tablename__ = "package_definitions"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(PackageDefinitionStatus, name="packagedefinitionstatus"),
        nullable=False, default=PackageDefinitionStatus.DRAFT,
    )
    entitlement_type = Column(
        Enum(EntitlementType, name="entitlementtype"), nullable=False,
    )
    total_sessions = Column(Integer, nullable=True)
    shareability = Column(
        Enum(Shareability, name="shareability"),
        nullable=False, default=Shareability.OWNER_ONLY,
    )
    validity_days = Column(Integer, nullable=False)
    auto_apply = Column(Boolean, nullable=False, default=True)
    cancellation_fee_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("20.00"))
    created_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)

    items = relationship(
        "PackageDefinitionItem",
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="PackageDefinitionItem.display_order",
    )

    __table_args__ = (
        CheckConstraint(
            "(entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
            "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
            name="ck_package_def_entitlement_sessions",
        ),
        CheckConstraint("cancellation_fee_pct >= 0 AND cancellation_fee_pct <= 100",
                        name="ck_package_def_fee_range"),
        CheckConstraint("validity_days > 0", name="ck_package_def_validity_positive"),
    )


class PackageDefinitionItem(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_definition_items"

    package_definition_id = Column(
        String(26),
        ForeignKey("package_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id = Column(String(26), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_paise = Column(Integer, nullable=False)
    locked = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)

    definition = relationship("PackageDefinition", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_def_item_qty_positive"),
        CheckConstraint("unit_price_paise >= 0", name="ck_package_def_item_price_non_negative"),
    )
