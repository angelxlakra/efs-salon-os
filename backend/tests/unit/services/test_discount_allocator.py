"""Tests for proportional discount allocation (Phase 3 of GST split billing).

A bill-level discount must be distributed across lines BEFORE per-line tax,
because services (5% exclusive) and products (18% inclusive) tax differently.

Invariants:
  - sum(allocated) == discount, exactly (remainder goes to the largest line)
  - no line receives more discount than its line total
  - allocation is proportional to line-total share (floored)
  - deterministic: same input → same output
"""

import pytest

from app.services.discount_allocator import allocate_discount


class TestAllocateDiscount:
    def test_even_split(self):
        # Two equal lines share the discount equally
        assert allocate_discount([50000, 50000], 10000) == [5000, 5000]

    def test_proportional(self):
        # 3:1 line ratio → 3:1 discount split
        assert allocate_discount([75000, 25000], 10000) == [7500, 2500]

    def test_remainder_goes_to_largest_line(self):
        # 10001 over two equal halves: floor gives 5000 each, 1p remainder
        # lands on the largest (first-listed on tie) line
        result = allocate_discount([50000, 50000], 10001)
        assert result == [5001, 5000]
        assert sum(result) == 10001

    def test_sum_invariant_fuzz(self):
        cases = [
            ([33333, 66667, 12345], 9999),
            ([1, 1, 1], 2),
            ([99999], 12345),
            ([10, 20, 30, 40], 7),
        ]
        for lines, discount in cases:
            result = allocate_discount(lines, discount)
            assert sum(result) == discount
            assert all(a >= 0 for a in result)
            assert all(a <= l for a, l in zip(result, lines))

    def test_zero_discount(self):
        assert allocate_discount([50000, 30000], 0) == [0, 0]

    def test_full_discount(self):
        # 100% discount allocates each line exactly its own total
        assert allocate_discount([50000, 30000], 80000) == [50000, 30000]

    def test_single_line(self):
        assert allocate_discount([50000], 7777) == [7777]

    def test_deterministic(self):
        lines, discount = [33333, 66667, 12345], 9999
        assert allocate_discount(lines, discount) == allocate_discount(lines, discount)

    def test_discount_exceeding_total_rejected(self):
        with pytest.raises(ValueError):
            allocate_discount([50000], 50001)

    def test_negative_discount_rejected(self):
        with pytest.raises(ValueError):
            allocate_discount([50000], -1)

    def test_negative_line_rejected(self):
        with pytest.raises(ValueError):
            allocate_discount([50000, -1], 100)

    def test_empty_lines_with_zero_discount(self):
        assert allocate_discount([], 0) == []

    def test_empty_lines_with_discount_rejected(self):
        with pytest.raises(ValueError):
            allocate_discount([], 1)

    def test_zero_value_lines_get_nothing(self):
        # package redemption lines have 0 line_total; they absorb no discount
        result = allocate_discount([0, 50000], 5000)
        assert result == [0, 5000]
