"""Pricing engine — pure-function math. 100% coverage required."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from hypothesis import given, strategies as st
from unittest.mock import MagicMock
from app.services.package_pricing_engine import (
    distribute_discount, DiscountMode, DiscountedItem, DomainError,
    snapshot_at_sale, PackageSaleItemDraft,
    compute_refund, RefundComputation,
    can_extend_expiry,
)
from app.models.package import EntitlementType


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
    with pytest.raises(DomainError, match="all lines are locked"):
        distribute_discount(items, DiscountMode.PCT, Decimal("10"))


def test_zero_price_unlocked_with_discount_raises():
    items = [_make(0), _make(0)]  # unlocked but price=0 — distinct from all-locked
    with pytest.raises(DomainError, match="zero price"):
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
    expected_final = int(
        (Decimal(mrp_sum) * (Decimal("100") - pct) / Decimal("100"))
        .to_integral_value(rounding=ROUND_FLOOR)
    )
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


def test_zero_quantity_raises():
    """quantity=0 would cause ZeroDivisionError — guard catches it early."""
    items = [_make(100000, qty=0)]
    with pytest.raises(DomainError, match="quantity must be >= 1"):
        distribute_discount(items, DiscountMode.PCT, Decimal("10"))


def test_negative_price_raises():
    """Negative unit price corrupts proportional distribution — guard rejects it."""
    items = [_make(-100000)]
    with pytest.raises(DomainError, match="unit_price_paise must be >= 0"):
        distribute_discount(items, DiscountMode.PCT, Decimal("10"))


def test_snapshot_copies_items_exactly():
    # Mock a PackageDefinition with 2 items
    def_item_1 = MagicMock(
        id="01HXYZDEFITEM1000000000001",
        service_id="01HSVCSERVICE100000000001A",
        quantity=1,
        unit_price_paise=200000,
        locked=False,
        display_order=0,
    )
    def_item_1.service = MagicMock(gst_rate_pct=Decimal("18.00"))
    def_item_2 = MagicMock(
        id="01HXYZDEFITEM2000000000001",
        service_id="01HSVCSERVICE200000000001A",
        quantity=2,
        unit_price_paise=100000,
        locked=True,
        display_order=1,
    )
    def_item_2.service = MagicMock(gst_rate_pct=Decimal("12.00"))

    definition = MagicMock(items=[def_item_1, def_item_2])

    drafts = snapshot_at_sale(definition)
    assert len(drafts) == 2
    assert drafts[0].package_definition_item_id == "01HXYZDEFITEM1000000000001"
    assert drafts[0].snapshot_unit_price_paise == 200000
    assert drafts[0].snapshot_gst_rate_pct == Decimal("18.00")
    assert drafts[0].service_id == "01HSVCSERVICE100000000001A"
    assert drafts[0].quantity == 1
    assert drafts[0].display_order == 0
    assert drafts[0].locked is False
    assert drafts[1].snapshot_unit_price_paise == 100000
    assert drafts[1].locked is True
    assert drafts[1].snapshot_gst_rate_pct == Decimal("12.00")


def test_snapshot_empty_definition():
    """snapshot_at_sale with no items returns empty list."""
    definition = MagicMock(items=[])
    drafts = snapshot_at_sale(definition)
    assert drafts == []


def test_refund_counted_pro_rata():
    """5 sessions of 10 used, ₹1000 each, 20% cancellation fee."""
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=5,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
    )
    result = compute_refund(sale)
    assert result.kind == "counted"
    # 5 unredeemed x 10000 paise/session = 500000 paise base; 20% fee = 100000; refund = 400000
    assert result.base_paise == 500000
    assert result.fee_paise == 100000
    assert result.refund_paise == 400000
    assert result.sessions_consumed == 5
    assert result.sessions_total == 10
    assert result.consumed_value_paise == 500000
    assert result.pct_remaining == Decimal("50")


def test_refund_counted_all_redeemed_zero_refund():
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=0,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
    )
    result = compute_refund(sale)
    assert result.base_paise == 0
    assert result.refund_paise == 0


def test_refund_counted_zero_fee():
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=5,
        cancellation_fee_pct_snapshot=Decimal("0.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
    )
    result = compute_refund(sale)
    assert result.refund_paise == result.base_paise == 500000


def test_refund_counted_remaining_exceeds_total_raises():
    """Data corruption guard: sessions_remaining > total_sessions_snapshot."""
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=5,
        sessions_remaining=8,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
    )
    with pytest.raises(DomainError, match="exceeds total_sessions_snapshot"):
        compute_refund(sale)


def test_refund_counted_none_total_sessions_raises():
    """total_sessions_snapshot=None on a counted sale must raise DomainError."""
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=None,
        sessions_remaining=3,
        cancellation_fee_pct_snapshot=Decimal("0.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
    )
    with pytest.raises(DomainError, match="total_sessions_snapshot must be a positive int"):
        compute_refund(sale)


def test_refund_counted_multi_item():
    """Package with two service lines: the per-session value sums across all items."""
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=6,
        sessions_remaining=3,
        cancellation_fee_pct_snapshot=Decimal("0.00"),
        items=[
            MagicMock(snapshot_unit_price_paise=50000, quantity=1),  # haircut
            MagicMock(snapshot_unit_price_paise=30000, quantity=1),  # massage
        ],
    )
    result = compute_refund(sale)
    # session_value_paise = 50000 + 30000 = 80000; 3 remaining → base = 240000
    assert result.base_paise == 240000
    assert result.refund_paise == 240000
    assert result.consumed_value_paise == 240000


def test_refund_unlimited_pro_rata_time():
    """Bought for ₹1500, 30-day validity, 8 days elapsed → 22/30 remaining.

    expires_at is set to now + 22 days + 1 hour so that timedelta.days is
    reliably 22 even accounting for microseconds of execution time between
    the test's 'now' and the implementation's datetime.now() call.
    """
    now = datetime.now(timezone.utc)
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.UNLIMITED,
        total_sessions_snapshot=None,
        sessions_remaining=None,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        sold_at=now - timedelta(days=8),
        expires_at=now + timedelta(days=22, hours=1),
        items=[],
    )
    sale.bill.total_paise = 150000
    result = compute_refund(sale)
    assert result.kind == "unlimited"
    # 22/30 * 150000 = 110000 base; 20% fee = 22000; refund = 88000
    assert result.base_paise == 110000
    assert result.fee_paise == 22000
    assert result.refund_paise == 88000
    assert result.consumed_value_paise == 40000       # 150000 - 110000
    assert result.pct_remaining == Decimal(22) / Decimal(30)
    assert result.sessions_consumed is None
    assert result.sessions_total is None


def test_refund_unlimited_expired_zero():
    """Expired package → zero remaining days → zero base → zero refund."""
    now = datetime.now(timezone.utc)
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.UNLIMITED,
        total_sessions_snapshot=None,
        sessions_remaining=None,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        sold_at=now - timedelta(days=60),
        expires_at=now - timedelta(days=30),
        items=[],
    )
    sale.bill.total_paise = 150000
    result = compute_refund(sale)
    assert result.base_paise == 0
    assert result.refund_paise == 0
    assert result.consumed_value_paise == 150000      # full amount consumed
    assert result.fee_paise == 0                      # 0 base × fee_pct = 0
    assert result.sessions_consumed is None
    assert result.sessions_total is None


def test_extend_must_be_forward_in_time():
    """new_expires_at must be strictly after sale.expires_at."""
    sale = MagicMock(expires_at=datetime.now(timezone.utc) + timedelta(days=10))
    new_expires = sale.expires_at - timedelta(days=1)
    with pytest.raises(DomainError, match="forward"):
        can_extend_expiry(sale, new_expires)


def test_extend_must_be_future_relative_to_now():
    """new_expires_at must be > now() even if it is > sale.expires_at (e.g. extending an already-expired package)."""
    sale = MagicMock(expires_at=datetime.now(timezone.utc) - timedelta(days=5))
    new_expires = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(DomainError, match="past"):
        can_extend_expiry(sale, new_expires)


def test_extend_valid():
    """A future date beyond current expiry raises nothing."""
    sale = MagicMock(expires_at=datetime.now(timezone.utc) + timedelta(days=10))
    can_extend_expiry(sale, sale.expires_at + timedelta(days=30))  # must not raise
