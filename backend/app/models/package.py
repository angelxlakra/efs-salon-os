"""Package models — definitions, sales, redemptions, expiry extensions."""

import enum
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Enum, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    # Package-level discount, persisted so edits round-trip the entered values.
    # Items keep their GROSS prices; the discount is applied at sale time.
    # discount_value is paise for flat/final modes, a percentage for pct.
    discount_mode = Column(String(8), nullable=True)
    discount_value = Column(Numeric(12, 2), nullable=True)
    # Package Builder v2: the entitlement-block stack (source of truth for the
    # v2 builder UI) and the builder-computed sell price. NULL for v1 packages,
    # whose price is still derived from `items` + discount.
    blocks = Column(JSONB, nullable=True)
    stored_price_paise = Column(Integer, nullable=True)
    created_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)

    items = relationship(
        "PackageDefinitionItem",
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="PackageDefinitionItem.display_order",
    )

    __table_args__ = (
        CheckConstraint(
            "(blocks IS NOT NULL) "  # v2 block packages don't use the sessions envelope
            "OR (entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
            "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
            name="ck_package_def_entitlement_sessions",
        ),
        CheckConstraint("cancellation_fee_pct >= 0 AND cancellation_fee_pct <= 100",
                        name="ck_package_def_fee_range"),
        CheckConstraint("validity_days > 0", name="ck_package_def_validity_positive"),
        CheckConstraint(
            "(discount_mode IS NULL AND discount_value IS NULL) "
            "OR (discount_mode IN ('pct', 'flat', 'final') AND discount_value IS NOT NULL)",
            name="ck_package_def_discount_pair",
        ),
    )

    @property
    def discount(self) -> dict | None:
        """Discount as {mode, value} for API serialization, or None."""
        if self.discount_mode is None:
            return None
        return {"mode": self.discount_mode, "value": self.discount_value}

    def effective_item_prices(self) -> list[int]:
        """Per-item unit prices with the package discount applied (paise).

        Pure computation — pricing engine owns the distribution math.
        """
        from app.services.package_pricing_engine import (
            distribute_discount, DiscountedItem, DiscountMode,
        )
        drafts = [
            DiscountedItem(
                unit_price_paise=i.unit_price_paise,
                quantity=i.quantity,
                locked=i.locked,
            )
            for i in self.items
        ]
        if self.discount_mode is not None:
            drafts = distribute_discount(
                drafts, DiscountMode(self.discount_mode), self.discount_value,
            )
        return [d.unit_price_paise for d in drafts]

    @property
    def final_price_paise(self) -> int:
        """Effective selling price of the whole package (paise).

        Computed at total level so FINAL/FLAT are exact; per-unit floor
        division (effective_item_prices) can drift by a few paise on
        qty>1 lines and is only used for sale snapshots.
        """
        # v2 block packages carry a builder-computed price; trust it.
        if self.stored_price_paise is not None:
            return self.stored_price_paise
        gross = sum(i.unit_price_paise * i.quantity for i in self.items)
        if self.discount_mode is None:
            return gross
        if self.discount_mode == "pct":
            return int(gross * (Decimal("100") - self.discount_value) / Decimal("100"))
        if self.discount_mode == "flat":
            return gross - int(self.discount_value)
        return int(self.discount_value)  # final


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
    max_redemptions = Column(Integer, nullable=True)  # null = no per-line cap

    definition = relationship("PackageDefinition", back_populates="items")
    service = relationship("Service")

    @property
    def service_name(self) -> str | None:
        """Name of the linked service, for API serialization."""
        return self.service.name if self.service else None

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_def_item_qty_positive"),
        CheckConstraint("unit_price_paise >= 0", name="ck_package_def_item_price_non_negative"),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions >= 1",
            name="ck_package_def_item_max_redemptions_positive",
        ),
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
    # v2: the block stack as sold, for block-labelled entitlement display.
    # NULL for v1 (items) sales. Per-line consumption lives on PackageSaleItem.
    blocks_snapshot = Column(JSONB, nullable=True)

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
    block_counters = relationship(
        "PackageSaleBlock",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="PackageSaleBlock.block_index",
    )
    customer = relationship("Customer", foreign_keys=[customer_id])
    definition = relationship("PackageDefinition", foreign_keys=[package_definition_id])

    @property
    def customer_name(self) -> str | None:
        """Full name of customer, for API serialization."""
        if not self.customer:
            return None
        parts = [self.customer.first_name, self.customer.last_name]
        return " ".join(p for p in parts if p)

    @property
    def package_definition_name(self) -> str | None:
        """Name of the package definition, for API serialization."""
        return self.definition.name if self.definition else None

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
    # Nullable: v2 block packages have no PackageDefinitionItem rows — their
    # sale items are synthesized from the block stack instead.
    package_definition_item_id = Column(
        String(26), ForeignKey("package_definition_items.id", ondelete="RESTRICT"),
        nullable=True,
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
    max_redemptions = Column(Integer, nullable=True)  # null = no per-line cap
    remaining = Column(Integer, nullable=True)        # null iff max_redemptions is null
    # v2 unlimited blocks: this line is redeemable without limit and does NOT
    # draw from the global session pool (survives EXHAUSTED until expiry).
    pool_exempt = Column(Boolean, nullable=False, default=False)
    # v2 choice@visit / pool blocks: this line draws from an INDEPENDENT
    # per-block counter (PackageSaleBlock) instead of the global session pool.
    sale_block_id = Column(
        String(26), ForeignKey("package_sale_blocks.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    sale = relationship("PackageSale", back_populates="items")
    service = relationship("Service")

    @property
    def service_name(self) -> str | None:
        """Name of the linked service, for API serialization."""
        return self.service.name if self.service else None

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_sale_item_qty_positive"),
        CheckConstraint("snapshot_unit_price_paise >= 0", name="ck_package_sale_item_price_non_negative"),
        # Covering index for the find_eligible_packages subquery:
        #   SELECT package_sale_id FROM package_sale_items WHERE service_id = ?
        Index("ix_package_sale_items_service_id_sale_id", "service_id", "package_sale_id"),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions >= 1",
            name="ck_package_sale_item_max_redemptions_positive",
        ),
        CheckConstraint(
            "remaining IS NULL OR remaining >= 0",
            name="ck_package_sale_item_remaining_non_negative",
        ),
        CheckConstraint(
            "(max_redemptions IS NULL AND remaining IS NULL) "
            "OR (max_redemptions IS NOT NULL AND remaining IS NOT NULL)",
            name="ck_package_sale_item_remaining_matches_cap",
        ),
    )


class PackageSaleBlock(Base, ULIDMixin, TimestampMixin):
    """Independent per-block redemption counter for a sold v2 package.

    A choice@visit or pool block gets one of these: `remaining` is a budget
    shared across all its option lines (use any option, N times total), wholly
    separate from the global session pool. Mutated only under the PackageSale
    row lock in apply_redemption/undo_redemption.
    """
    __tablename__ = "package_sale_blocks"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    block_index = Column(Integer, nullable=False)  # index into blocks_snapshot
    kind = Column(String(16), nullable=False)
    name = Column(String(255), nullable=False)
    remaining = Column(Integer, nullable=False)

    sale = relationship("PackageSale", back_populates="block_counters")

    __table_args__ = (
        CheckConstraint("remaining >= 0", name="ck_package_sale_block_remaining_non_negative"),
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
