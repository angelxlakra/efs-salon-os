"""Tests for GST-mode per-line tax functions (Phase 1 of GST split billing).

GST mode rules (owner-confirmed, see docs/superpowers/plans/2026-06-11-gst-split-billing.md):
  - Services: 5% EXCLUSIVE — tax added on top of the (discounted) base price.
  - Products: 18% INCLUSIVE — tax extracted from the (discounted) MRP price.
  - CGST and SGST are always equal halves.
  - All tax amounts FLOOR (round down) to the paise.
  - Final payable floors to the whole rupee.

Invariants:
  - exclusive: gross == taxable + cgst + sgst
  - inclusive: taxable + cgst + sgst == amount (gross == amount)
  - cgst == sgst always
"""

import pytest

from app.services.tax_calculator import TaxCalculator


class TestCalculateLineTaxExclusive:
    """Services: 5% added on top (2.5% CGST + 2.5% SGST)."""

    def test_round_amount(self):
        # ₹500 service → ₹12.50 + ₹12.50 tax, customer pays ₹525
        r = TaxCalculator.calculate_line_tax(50000, 5, "exclusive")
        assert r == {
            "taxable_value": 50000,
            "cgst": 1250,
            "sgst": 1250,
            "total_tax": 2500,
            "gross": 52500,
        }

    def test_floors_to_paise(self):
        # 49999 * 2.5% = 1249.975 paise → floors to 1249, never rounds up
        r = TaxCalculator.calculate_line_tax(49999, 5, "exclusive")
        assert r["cgst"] == 1249
        assert r["sgst"] == 1249
        assert r["gross"] == 49999 + 2498

    def test_gross_invariant(self):
        for amount in (1, 99, 33333, 1234567):
            r = TaxCalculator.calculate_line_tax(amount, 5, "exclusive")
            assert r["gross"] == r["taxable_value"] + r["cgst"] + r["sgst"]
            assert r["cgst"] == r["sgst"]

    def test_zero_amount(self):
        r = TaxCalculator.calculate_line_tax(0, 5, "exclusive")
        assert r["total_tax"] == 0
        assert r["gross"] == 0


class TestCalculateLineTaxInclusive:
    """Products: 18% extracted from MRP (9% CGST + 9% SGST)."""

    def test_round_amount(self):
        # ₹1,180 MRP → ₹1,000 taxable + ₹90 + ₹90; customer pays the MRP
        r = TaxCalculator.calculate_line_tax(118000, 18, "inclusive")
        assert r == {
            "taxable_value": 100000,
            "cgst": 9000,
            "sgst": 9000,
            "total_tax": 18000,
            "gross": 118000,
        }

    def test_sum_invariant_holds_exactly(self):
        # taxable + cgst + sgst must reconstruct the inclusive price exactly,
        # with each tax half floored
        for amount in (1, 9999, 12345, 118000, 9999999):
            r = TaxCalculator.calculate_line_tax(amount, 18, "inclusive")
            assert r["taxable_value"] + r["cgst"] + r["sgst"] == amount
            assert r["cgst"] == r["sgst"]
            assert r["gross"] == amount

    def test_floors_to_paise(self):
        # 9999 * 18/236 = 762.63... → each half floors to 762
        r = TaxCalculator.calculate_line_tax(9999, 18, "inclusive")
        assert r["cgst"] == 762
        assert r["sgst"] == 762
        assert r["taxable_value"] == 9999 - 1524


class TestCalculateLineTaxNone:
    """Zero-tax lines: package redemptions, legacy, exempt."""

    def test_no_tax(self):
        r = TaxCalculator.calculate_line_tax(50000, 0, "none")
        assert r == {
            "taxable_value": 50000,
            "cgst": 0,
            "sgst": 0,
            "total_tax": 0,
            "gross": 50000,
        }


class TestCalculateLineTaxValidation:
    def test_negative_amount_rejected(self):
        with pytest.raises(ValueError):
            TaxCalculator.calculate_line_tax(-1, 5, "exclusive")

    def test_unknown_mode_rejected(self):
        with pytest.raises(ValueError):
            TaxCalculator.calculate_line_tax(100, 5, "added")

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError):
            TaxCalculator.calculate_line_tax(100, -5, "exclusive")


class TestRoundDownToRupee:
    def test_floors(self):
        # ₹1470.99 → ₹1470, salon absorbs 99 paise
        assert TaxCalculator.round_down_to_rupee(147099) == (147000, -99)

    def test_exact_rupee_unchanged(self):
        assert TaxCalculator.round_down_to_rupee(147000) == (147000, 0)

    def test_never_rounds_up(self):
        # contrast with legacy round_to_rupee which rounds 50p up
        assert TaxCalculator.round_down_to_rupee(147050) == (147000, -50)

    def test_zero(self):
        assert TaxCalculator.round_down_to_rupee(0) == (0, 0)

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            TaxCalculator.round_down_to_rupee(-100)


class TestLegacyBehaviorUntouched:
    """Old bills must stay reproducible: legacy methods keep ROUND_HALF_UP."""

    def test_legacy_extraction_unchanged(self):
        r = TaxCalculator.calculate_tax_breakdown(118000)
        assert r["taxable_value"] == 100000
        assert r["cgst"] == 9000
        assert r["sgst"] == 9000

    def test_legacy_rounding_still_half_up(self):
        assert TaxCalculator.round_to_rupee(147050) == (147100, 50)
