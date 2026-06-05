"""Pricing engine — pure-function math for packages.

Single shared module owning all package math. Called by sales, redemption,
refund, reports. No package-math logic anywhere else in the codebase.

DB-touching eligibility queries live in package_eligibility.py to keep
this module free of SQLAlchemy dependencies.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import List, Optional, Protocol


def _paise(d: Decimal) -> int:
    """Convert a Decimal paise value to int, rounding down to nearest whole paise."""
    return int(d.to_integral_value(rounding=ROUND_FLOOR))


class DomainError(ValueError):
    """Raised for pricing engine domain violations."""


class DiscountMode(str, enum.Enum):
    PCT = "pct"
    FLAT = "flat"
    FINAL = "final"


@dataclass
class DiscountedItem:
    unit_price_paise: int
    quantity: int = 1
    locked: bool = False


def distribute_discount(
    items: List[DiscountedItem],
    mode: DiscountMode,
    value: Decimal,
) -> List[DiscountedItem]:
    """Apply a package-level discount across UNLOCKED lines proportional to MRP weight.

    Locked lines preserve their price exactly. Rounding spillover goes to the
    LAST unlocked line so the package total matches exactly.

    Note:
        For lines with quantity > 1, the returned unit_price_paise may be off by
        up to (quantity - 1) paise from perfect division due to integer floor
        division. Callers that need the exact line total should recompute it as
        unit_price_paise * quantity; the overall package-level total is exact only
        for qty=1 lines.

    Raises:
        DomainError: if all lines are locked and a discount is requested,
                     or if FINAL value exceeds total MRP.
    """
    if not items:
        return []

    for item in items:
        if item.quantity <= 0:
            raise DomainError(f"Item quantity must be >= 1, got {item.quantity}")
        if item.unit_price_paise < 0:
            raise DomainError(f"unit_price_paise must be >= 0, got {item.unit_price_paise}")

    if value == 0:
        return [replace(i) for i in items]

    # Compute MRP weights
    locked_weight = sum(i.unit_price_paise * i.quantity for i in items if i.locked)
    unlocked_weight = sum(i.unit_price_paise * i.quantity for i in items if not i.locked)
    total_mrp = locked_weight + unlocked_weight

    if unlocked_weight == 0:
        raise DomainError("Cannot distribute discount: no unlocked lines")

    # Compute total final paise across unlocked lines
    if mode == DiscountMode.PCT:
        unlocked_final = int(
            (Decimal(unlocked_weight) * (Decimal("100") - value) / Decimal("100"))
            .to_integral_value(rounding=ROUND_FLOOR)
        )
    elif mode == DiscountMode.FLAT:
        if _paise(value) > unlocked_weight:
            raise DomainError("Flat discount exceeds unlocked MRP")
        unlocked_final = unlocked_weight - _paise(value)
    elif mode == DiscountMode.FINAL:
        if _paise(value) > total_mrp:
            raise DomainError("Final amount exceeds MRP")
        if _paise(value) < locked_weight:
            raise DomainError("Final amount below locked-line minimum")
        unlocked_final = _paise(value) - locked_weight
    else:
        raise DomainError(f"Unknown discount mode: {mode}")

    if unlocked_final < 0:
        raise DomainError("Negative final amount after discount")

    # Distribute proportionally to MRP weight across unlocked lines
    result = []
    unlocked_indices = [idx for idx, i in enumerate(items) if not i.locked]
    last_unlocked_idx = unlocked_indices[-1]

    running_total = 0
    for idx, item in enumerate(items):
        if item.locked:
            result.append(replace(item))
            continue

        item_weight = item.unit_price_paise * item.quantity
        if idx == last_unlocked_idx:
            # Spillover: last unlocked absorbs rounding residual
            line_final = unlocked_final - running_total
        else:
            line_final = int(
                (Decimal(item_weight) * Decimal(unlocked_final) / Decimal(unlocked_weight))
                .to_integral_value(rounding=ROUND_FLOOR)
            )
            running_total += line_final

        # Convert line_final (the line's total) back to unit price
        new_unit_price = line_final // item.quantity
        result.append(replace(item, unit_price_paise=new_unit_price))

    return result


class _ServiceProto(Protocol):
    gst_rate_pct: Decimal


class _DefinitionItemProto(Protocol):
    id: str
    service_id: str
    quantity: int
    unit_price_paise: int
    locked: bool
    display_order: int
    service: _ServiceProto


class _DefinitionProto(Protocol):
    items: List[_DefinitionItemProto]


@dataclass(frozen=True)
class PackageSaleItemDraft:
    package_definition_item_id: str
    service_id: str
    quantity: int
    snapshot_unit_price_paise: int
    snapshot_gst_rate_pct: Decimal
    locked: bool
    display_order: int


def snapshot_at_sale(definition: _DefinitionProto) -> List[PackageSaleItemDraft]:
    """Produce per-line snapshot drafts for a new PackageSale.

    Copies id (→ package_definition_item_id), service_id, quantity, unit_price_paise,
    service.gst_rate_pct, locked, and display_order from each PackageDefinitionItem
    at the moment of sale.
    """
    return [
        PackageSaleItemDraft(
            package_definition_item_id=item.id,
            service_id=item.service_id,
            quantity=item.quantity,
            snapshot_unit_price_paise=item.unit_price_paise,
            snapshot_gst_rate_pct=item.service.gst_rate_pct,
            locked=item.locked,
            display_order=item.display_order,
        )
        for item in definition.items
    ]


@dataclass
class RefundComputation:
    kind: str  # "counted" | "unlimited"
    base_paise: int
    fee_paise: int
    refund_paise: int
    consumed_value_paise: int
    pct_remaining: Optional[Decimal] = None
    sessions_consumed: Optional[int] = None
    sessions_total: Optional[int] = None


def compute_refund(sale) -> RefundComputation:
    """Compute refund breakdown for a PackageSale.

    Branches by entitlement_type_snapshot. Returns paise integers + UI breakdown.
    Compares against string values ("counted", "unlimited") to avoid importing
    the SQLAlchemy-backed EntitlementType enum.
    """
    if sale.entitlement_type_snapshot == "counted":
        return _compute_counted_refund(sale)
    elif sale.entitlement_type_snapshot == "unlimited":
        return _compute_unlimited_refund(sale)
    else:
        raise DomainError(f"Unknown entitlement_type: {sale.entitlement_type_snapshot}")


def _compute_counted_refund(sale) -> RefundComputation:
    total = sale.total_sessions_snapshot
    if not total:
        raise DomainError("total_sessions_snapshot must be a positive int on a counted sale")
    remaining = sale.sessions_remaining or 0
    if remaining > total:
        raise DomainError(
            f"sessions_remaining ({remaining}) exceeds total_sessions_snapshot ({total})"
        )
    consumed = total - remaining

    # Per-session value: sum of all item MRPs (each item price is already per-session)
    session_value_paise = sum(
        i.snapshot_unit_price_paise * i.quantity for i in sale.items
    )

    base_paise = session_value_paise * remaining
    consumed_value_paise = session_value_paise * consumed

    fee_paise = int(
        (Decimal(base_paise) * sale.cancellation_fee_pct_snapshot / Decimal("100"))
        .to_integral_value(rounding=ROUND_FLOOR)
    )
    refund_paise = base_paise - fee_paise

    pct_remaining = (
        Decimal(remaining) / Decimal(max(total, 1)) * Decimal("100")
    ).to_integral_value(rounding=ROUND_FLOOR)

    return RefundComputation(
        kind="counted",
        base_paise=base_paise,
        fee_paise=fee_paise,
        refund_paise=refund_paise,
        consumed_value_paise=consumed_value_paise,
        pct_remaining=pct_remaining,
        sessions_consumed=consumed,
        sessions_total=total,
    )


def _compute_unlimited_refund(sale) -> RefundComputation:
    """Time-pro-rata refund for unlimited-entitlement packages.

    pct_remaining is a Decimal fraction in [0, 1] (not a percentage),
    unlike the counted branch which stores an integer percentage.
    """
    now = datetime.now(timezone.utc)
    total_validity_days = max((sale.expires_at - sale.sold_at).days, 1)
    days_remaining = max((sale.expires_at - now).days, 0)
    pct_remaining = Decimal(days_remaining) / Decimal(total_validity_days)

    if sale.bill is None:
        raise DomainError("PackageSale has no associated bill — cannot compute unlimited refund")
    paid_paise = sale.bill.total_paise
    base_paise = int(
        (Decimal(paid_paise) * pct_remaining).to_integral_value(rounding=ROUND_FLOOR)
    )
    consumed_value_paise = paid_paise - base_paise

    fee_paise = int(
        (Decimal(base_paise) * sale.cancellation_fee_pct_snapshot / Decimal("100"))
        .to_integral_value(rounding=ROUND_FLOOR)
    )
    refund_paise = base_paise - fee_paise

    return RefundComputation(
        kind="unlimited",
        base_paise=base_paise,
        fee_paise=fee_paise,
        refund_paise=refund_paise,
        consumed_value_paise=consumed_value_paise,
        pct_remaining=pct_remaining,
    )


def can_extend_expiry(sale, new_expires_at: datetime) -> None:
    """Validate an expiry extension request. Raises DomainError on violation.

    Rules:
    - new_expires_at must be strictly after sale.expires_at (always forward)
    - new_expires_at must be strictly after now() (cannot set a past expiry)
    """
    if new_expires_at <= sale.expires_at:
        raise DomainError("Extension must be forward in time")
    if new_expires_at <= datetime.now(timezone.utc):
        raise DomainError("Extension cannot be in the past")


