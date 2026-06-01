"""Pricing engine — pure-function math. 100% coverage required."""

import pytest
from decimal import Decimal
from hypothesis import given, strategies as st
from app.services.package_pricing_engine import (
    distribute_discount, DiscountMode, DiscountedItem, DomainError,
)


def _make(price, qty=1, locked=False):
    return DiscountedItem(unit_price_paise=price, quantity=qty, locked=locked)


def test_pct_discount_no_locked():
    """20% off ₹6000 (3 services at 2000 each) -> ₹4800 total, each line 1600."""
    items = [_make(200000), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("20"))
    assert [i.unit_price_paise for i in out] == [160000, 160000, 160000]


def test_flat_discount_proportional():
    """₹1200 off mix of MRPs -> proportional split."""
    items = [_make(100000), _make(200000), _make(300000)]  # total 6_00_000
    out = distribute_discount(items, DiscountMode.FLAT, Decimal("120000"))  # ₹1200 off
    # expected: 100/600 * 120000 = 20000; 200/600 * 120000 = 40000; 300/600 * 120000 = 60000
    assert [i.unit_price_paise for i in out] == [80000, 160000, 240000]
    assert sum(i.unit_price_paise for i in out) == 480000  # exactly 6_00_000 - 1_20_000


def test_final_amount_mode():
    """Set total final price to ₹4500 from MRP sum ₹6000."""
    items = [_make(200000), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("450000"))
    assert sum(i.unit_price_paise for i in out) == 450000


def test_locked_lines_preserved():
    """Locked line keeps its price; only unlocked lines absorb discount."""
    items = [_make(200000, locked=True), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("450000"))
    # locked line stays at 200000; remaining 250000 spread across two unlocked
    assert out[0].unit_price_paise == 200000
    assert out[1].unit_price_paise + out[2].unit_price_paise == 250000


def test_all_locked_with_discount_raises():
    items = [_make(200000, locked=True), _make(200000, locked=True)]
    with pytest.raises(DomainError, match="no unlocked lines"):
        distribute_discount(items, DiscountMode.PCT, Decimal("10"))


def test_zero_discount_no_op():
    items = [_make(100000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("0"))
    assert [i.unit_price_paise for i in out] == [100000, 200000]


def test_100_pct_discount_zeros_unlocked():
    items = [_make(100000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("100"))
    assert [i.unit_price_paise for i in out] == [0, 0]


def test_rounding_spillover_to_last_unlocked():
    """₹100 split across 3 lines of equal MRP — last gets the residual paise."""
    items = [_make(10000), _make(10000), _make(10000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("9700"))
    total = sum(i.unit_price_paise for i in out)
    assert total == 9700  # exact
    # The last unlocked line absorbs the rounding residual
    assert out[2].unit_price_paise >= out[0].unit_price_paise


def test_quantity_aware():
    """Quantity multiplies the line MRP for distribution weighting."""
    items = [_make(100000, qty=2), _make(100000, qty=1)]  # MRP weight 200k vs 100k
    out = distribute_discount(items, DiscountMode.FLAT, Decimal("30000"))
    # 200/300 * 30000 = 20000 off first line; 100/300 * 30000 = 10000 off second
    # unit prices: 100000 - (20000 / 2) = 90000; 100000 - 10000 = 90000
    assert out[0].unit_price_paise == 90000
    assert out[1].unit_price_paise == 90000


def test_final_exceeds_mrp_sum_raises():
    items = [_make(100000)]
    with pytest.raises(DomainError, match="exceeds MRP"):
        distribute_discount(items, DiscountMode.FINAL, Decimal("200000"))


# Property test


@given(
    n=st.integers(min_value=1, max_value=10),
    base=st.integers(min_value=100, max_value=1_000_000),
    pct=st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2),
)
def test_property_pct_distribution_exact_sum(n, base, pct):
    """For qty=1 items, sum of distributed unit_prices equals expected final total exactly."""
    items = [_make(base, qty=1) for _ in range(n)]
    mrp_sum = n * base
    expected_final = int(mrp_sum * (Decimal("100") - pct) / Decimal("100"))
    out = distribute_discount(items, DiscountMode.PCT, pct)
    assert sum(i.unit_price_paise * i.quantity for i in out) == expected_final


def test_flat_exceeds_unlocked_raises():
    """Flat discount larger than the unlocked weight is rejected."""
    items = [_make(100000, locked=True), _make(50000)]  # unlocked = 50000
    with pytest.raises(DomainError):
        distribute_discount(items, DiscountMode.FLAT, Decimal("80000"))


def test_final_below_locked_minimum_raises():
    """Final target lower than locked-line sum is impossible."""
    items = [_make(200000, locked=True), _make(100000)]  # locked = 200000
    with pytest.raises(DomainError):
        distribute_discount(items, DiscountMode.FINAL, Decimal("150000"))


def test_negative_final_after_pct_on_negative_input():
    """Defensive: negative unlocked_final triggers DomainError."""
    # 150% off makes unlocked_final negative, triggering the guard.
    items = [_make(100000)]
    with pytest.raises(DomainError):
        distribute_discount(items, DiscountMode.PCT, Decimal("150"))  # 150% off
