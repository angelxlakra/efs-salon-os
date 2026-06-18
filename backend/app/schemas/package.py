"""Pydantic schemas for packages API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.package import (
    PackageDefinitionStatus, EntitlementType, Shareability, PackageSaleStatus,
)


# ---------- Definition CRUD ----------

class PackageDefinitionItemCreate(BaseModel):
    service_id: str = Field(..., min_length=26, max_length=26)
    quantity: int = Field(default=1, ge=1)
    unit_price_paise: int = Field(..., ge=0)
    locked: bool = False
    display_order: int = 0
    max_redemptions: Optional[int] = Field(default=None, ge=1)


class DiscountInput(BaseModel):
    mode: Literal["pct", "flat", "final"]
    value: Decimal = Field(..., ge=0)


class PackageDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    # v1 fields are optional so the v2 block builder (which sends `blocks` +
    # `final_price_paise` instead of items/entitlement_type) can reuse this
    # endpoint. v1 callers still send these and are validated as before.
    entitlement_type: EntitlementType = EntitlementType.COUNTED
    total_sessions: Optional[int] = Field(None, ge=1)
    shareability: Shareability = Shareability.OWNER_ONLY
    validity_days: int = Field(..., ge=1)
    auto_apply: bool = True
    cancellation_fee_pct: Decimal = Field(default=Decimal("20.00"), ge=0, le=100)
    items: List[PackageDefinitionItemCreate] = Field(default_factory=list)
    discount: Optional[DiscountInput] = None
    # Package Builder v2 — entitlement-block stack + builder-computed price.
    blocks: Optional[List[dict]] = None
    final_price_paise: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_entitlement_sessions(self) -> "PackageDefinitionCreate":
        if self.blocks is not None:
            return self  # v2 packages don't use the counted/sessions envelope
        if not self.items:
            raise ValueError("items must not be empty")
        if self.entitlement_type == EntitlementType.COUNTED and self.total_sessions is None:
            raise ValueError("total_sessions required when entitlement_type=counted")
        if self.entitlement_type == EntitlementType.UNLIMITED and self.total_sessions is not None:
            raise ValueError("total_sessions must be null when entitlement_type=unlimited")
        return self


class PackageDefinitionUpdate(PackageDefinitionCreate):
    pass


class PackageDefinitionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    service_name: Optional[str] = None
    quantity: int
    unit_price_paise: int
    locked: bool
    display_order: int
    max_redemptions: Optional[int] = None


class PackageDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    status: PackageDefinitionStatus
    entitlement_type: EntitlementType
    total_sessions: Optional[int]
    shareability: Shareability
    validity_days: int
    auto_apply: bool
    cancellation_fee_pct: Decimal
    items: List[PackageDefinitionItemResponse]
    # Items carry GROSS prices; discount + final_price_paise expose the
    # selling price so callers never re-implement distribution math.
    discount: Optional[DiscountInput] = None
    final_price_paise: int
    # v2 entitlement-block stack; null for v1 (items-based) packages.
    blocks: Optional[List[dict]] = None
    created_at: datetime
    updated_at: datetime


class PackageSaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    service_name: Optional[str] = None
    quantity: int
    snapshot_unit_price_paise: int
    snapshot_gst_rate_pct: Decimal
    locked: bool
    max_redemptions: Optional[int] = None
    remaining: Optional[int] = None
    pool_exempt: bool = False


class PackageSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bill_id: str
    package_definition_id: str
    package_definition_name: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None
    selling_staff_id: Optional[str]
    sold_at: datetime
    expires_at: datetime
    entitlement_type_snapshot: EntitlementType
    shareability_snapshot: Shareability
    cancellation_fee_pct_snapshot: Decimal
    total_sessions_snapshot: Optional[int]
    sessions_remaining: Optional[int]
    status: PackageSaleStatus
    refunded_at: Optional[datetime]
    refund_bill_id: Optional[str]
    # v2 block stack as sold (null for v1); per-line consumption is on `items`.
    blocks_snapshot: Optional[List[dict]] = None
    created_at: datetime
    updated_at: datetime
    items: List[PackageSaleItemResponse]


class PackageSaleSummary(BaseModel):
    """Lightweight projection for eligibility rail."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    package_definition_name: Optional[str] = None
    entitlement_type_snapshot: EntitlementType
    sessions_remaining: Optional[int]
    total_sessions_snapshot: Optional[int]
    expires_at: datetime
    shareability_snapshot: Shareability
    customer_id: str
    customer_name: Optional[str] = None


# ---------- Eligibility ----------

class RedemptionEligibilityRequest(BaseModel):
    customer_id: str = Field(..., min_length=26, max_length=26)
    service_id: str = Field(..., min_length=26, max_length=26)


class EligiblePackageResponse(BaseModel):
    package_sale: PackageSaleSummary
    snapshot_price_paise: int
    # How many more times this service can be redeemed from this package (the
    # governing budget). The POS cart caps optimistic redemptions by this.
    remaining_uses: int = 0
    # Two-level budget for accurate cart allocation: this service's own cap, plus
    # a budget shared across services keyed by shared_budget_key (the package's
    # global pool, or a choice/pool block counter). null key = no shared budget.
    line_remaining: int = 0
    shared_budget_key: Optional[str] = None
    shared_remaining: int = 0


# ---------- Refund + extend ----------

class RefundRequest(BaseModel):
    payment_method: Literal["cash", "upi", "card", "pending_balance"]
    reason: str = Field(..., min_length=1)


class RefundBreakdown(BaseModel):
    kind: Literal["counted", "unlimited"]
    base_paise: int
    fee_paise: int
    refund_paise: int
    consumed_value_paise: int
    pct_remaining: Optional[Decimal] = None
    sessions_consumed: Optional[int] = None
    sessions_total: Optional[int] = None


class ExtendExpiryRequest(BaseModel):
    new_expires_at: datetime
    reason: str = Field(..., min_length=1)


class RefundResponse(BaseModel):
    credit_note_bill_id: str
    status: Literal["refunded"]
