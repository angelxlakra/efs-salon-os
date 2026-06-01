"""Pricing engine — pure-function math for packages.

Single shared module owning all package math. Called by sales, redemption,
refund, reports. No package-math logic anywhere else in the codebase.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import List


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
