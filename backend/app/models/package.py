"""Package models — definitions, sales, redemptions, expiry extensions."""

import enum
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Enum, ForeignKey,
    Integer, Numeric, String, Text,
)
# Re-exported for Task 4 (sales/expiry/audit models)
from sqlalchemy import DateTime, Index  # noqa: F401
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
        Enum(PackageDefinitionStatus, name="packagedefinitionstatus",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=PackageDefinitionStatus.DRAFT,
    )
    entitlement_type = Column(
        Enum(EntitlementType, name="entitlementtype",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    total_sessions = Column(Integer, nullable=True)
    shareability = Column(
        Enum(Shareability, name="shareability",
             values_callable=lambda obj: [e.value for e in obj]),
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


class PackageSaleStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    EXHAUSTED = "exhausted"


class PackageSale(Base, ULIDMixin, TimestampMixin):
    """Lifecycle row for one sold package. All policy snapshotted at sale time."""
    __tablename__ = "package_sales"

    bill_id = Column(
        String(26), ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False, unique=True,
    )
    package_definition_id = Column(
        String(26), ForeignKey("package_definitions.id", ondelete="RESTRICT"), nullable=False,
    )
    customer_id = Column(
        String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    selling_staff_id = Column(String(26), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)

    sold_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    entitlement_type_snapshot = Column(
        Enum(EntitlementType, name="entitlementtype",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    shareability_snapshot = Column(
        Enum(Shareability, name="shareability",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    cancellation_fee_pct_snapshot = Column(Numeric(5, 2), nullable=False)
    total_sessions_snapshot = Column(Integer, nullable=True)
    sessions_remaining = Column(Integer, nullable=True)

    status = Column(
        Enum(PackageSaleStatus, name="packagesalestatus",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=PackageSaleStatus.ACTIVE, index=True,
    )
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_bill_id = Column(String(26), ForeignKey("bills.id", ondelete="RESTRICT"), nullable=True)

    items = relationship(
        "PackageSaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="PackageSaleItem.display_order",
    )

    __table_args__ = (
        Index("ix_package_sales_customer_status", "customer_id", "status"),
        Index("ix_package_sales_expires_status", "expires_at", "status"),
        Index("ix_package_sales_selling_staff_sold_at", "selling_staff_id", "sold_at"),
        CheckConstraint(
            "sessions_remaining IS NULL OR sessions_remaining >= 0",
            name="ck_package_sale_sessions_remaining_non_negative",
        ),
    )


class PackageSaleItem(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_sale_items"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    package_definition_item_id = Column(
        String(26), ForeignKey("package_definition_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id = Column(
        String(26), ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    quantity = Column(Integer, nullable=False)
    snapshot_unit_price_paise = Column(Integer, nullable=False)
    snapshot_gst_rate_pct = Column(Numeric(5, 2), nullable=False)
    locked = Column(Boolean, nullable=False)
    display_order = Column(Integer, nullable=False)

    sale = relationship("PackageSale", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_sale_item_qty_positive"),
        CheckConstraint("snapshot_unit_price_paise >= 0", name="ck_package_sale_item_price_non_negative"),
    )


class PackageRedemptionAudit(Base, ULIDMixin, TimestampMixin):
    """Append-only log of every redemption. Captures recipient for shared packages."""
    __tablename__ = "package_redemption_audit"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    bill_item_id = Column(
        String(26), ForeignKey("bill_items.id", ondelete="RESTRICT"),
        nullable=False, unique=True,
    )
    package_sale_item_id = Column(
        String(26), ForeignKey("package_sale_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    redeemed_for_customer_id = Column(
        String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    performed_by_user_id = Column(String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=False)
    session_number = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_package_redemption_audit_for_customer_redeemed_at",
              "redeemed_for_customer_id", "redeemed_at"),
    )


class PackageExpiryExtension(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_expiry_extensions"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    previous_expires_at = Column(DateTime(timezone=True), nullable=False)
    new_expires_at = Column(DateTime(timezone=True), nullable=False)
    performed_by_user_id = Column(String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    extended_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("new_expires_at > previous_expires_at",
                        name="ck_package_extend_forward_in_time"),
    )
