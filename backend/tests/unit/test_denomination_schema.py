"""Pure unit tests for DenominationBreakdown and request validators.

These tests only import Pydantic schemas — no app.main, no Redis, no DB.
They can run locally without Docker.
"""
import pytest
from app.schemas.cash_drawer import DenominationBreakdown, DrawerOpenRequest, DrawerCloseRequest


class TestDenominationBreakdown:

    def test_total_paise_all_denominations(self):
        """Verify total_paise calculation with all 7 denominations."""
        d = DenominationBreakdown(note_5=1, note_10=1, note_20=1, note_50=1, note_100=1, note_200=1, note_500=1)
        # (5 + 10 + 20 + 50 + 100 + 200 + 500) * 100 = 88500 paise
        assert d.total_paise == 88500

    def test_total_paise_small_denominations_only(self):
        """Verify ₹10 and ₹20 notes calculate correctly."""
        d = DenominationBreakdown(note_10=5, note_20=3)
        # (5*10 + 3*20) = 110 rupees = 11000 paise
        assert d.total_paise == 11000

    def test_total_paise_zero(self):
        """All zeros should equal zero."""
        d = DenominationBreakdown()
        assert d.total_paise == 0

    def test_to_dict_includes_all_keys(self):
        """Verify to_dict() outputs all 7 denomination keys."""
        d = DenominationBreakdown(note_5=1, note_10=2, note_20=3, note_50=4, note_100=5, note_200=6, note_500=7)
        assert d.to_dict() == {"5": 1, "10": 2, "20": 3, "50": 4, "100": 5, "200": 6, "500": 7}

    def test_from_dict_with_all_keys(self):
        """Verify from_dict() with all 7 keys."""
        data = {"5": 1, "10": 2, "20": 3, "50": 4, "100": 5, "200": 6, "500": 7}
        d = DenominationBreakdown.from_dict(data)
        assert d.note_5 == 1
        assert d.note_10 == 2
        assert d.note_20 == 3
        assert d.note_500 == 7

    def test_from_dict_backward_compatible(self):
        """Old JSONB data without ₹5/₹10/₹20 keys should default to 0."""
        old_data = {"50": 10, "100": 5, "200": 2, "500": 1}
        d = DenominationBreakdown.from_dict(old_data)
        assert d.note_5 == 0
        assert d.note_10 == 0
        assert d.note_20 == 0
        assert d.note_50 == 10
        assert d.total_paise == (10 * 50 + 5 * 100 + 2 * 200 + 1 * 500) * 100

    def test_from_dict_none_returns_none(self):
        """from_dict(None) should return None."""
        assert DenominationBreakdown.from_dict(None) is None

    def test_from_dict_empty_returns_none(self):
        """from_dict({}) is falsy, should return None."""
        assert DenominationBreakdown.from_dict({}) is None

    def test_roundtrip_to_dict_from_dict(self):
        """Verify to_dict -> from_dict roundtrip preserves values."""
        original = DenominationBreakdown(note_5=9, note_10=8, note_20=7, note_50=6, note_100=5, note_200=4, note_500=3)
        restored = DenominationBreakdown.from_dict(original.to_dict())
        assert restored.total_paise == original.total_paise
        assert restored.to_dict() == original.to_dict()

    def test_negative_count_rejected(self):
        """Negative note counts should be rejected by ge=0."""
        with pytest.raises(Exception):
            DenominationBreakdown(note_10=-1)

    def test_excessive_count_rejected(self):
        """Counts above le=10000 should be rejected."""
        with pytest.raises(Exception):
            DenominationBreakdown(note_500=10001)

    def test_upper_bound_accepted(self):
        """Exactly 10000 should be accepted."""
        d = DenominationBreakdown(note_500=10000)
        assert d.note_500 == 10000


class TestDrawerRequestValidation:

    def test_open_request_requires_at_least_one_field(self):
        """Opening with neither float nor denominations should fail at model level."""
        with pytest.raises(Exception):
            DrawerOpenRequest()

    def test_open_request_with_denominations(self):
        """Opening with denomination breakdown should compute correct paise."""
        req = DrawerOpenRequest(opening_denominations=DenominationBreakdown(note_10=5, note_500=2))
        # (5*10 + 2*500) = 1050 rupees = 105000 paise
        assert req.get_opening_float_paise() == 105000

    def test_open_request_with_float(self):
        """Opening with raw paise float should pass through."""
        req = DrawerOpenRequest(opening_float=5000)
        assert req.get_opening_float_paise() == 5000

    def test_close_request_requires_at_least_one_field(self):
        """Closing with neither counted nor denominations should fail at model level."""
        with pytest.raises(Exception):
            DrawerCloseRequest()

    def test_close_request_with_denominations(self):
        """Closing with denomination breakdown should compute correct paise."""
        req = DrawerCloseRequest(closing_denominations=DenominationBreakdown(note_20=10, note_100=5))
        # (10*20 + 5*100) = 700 rupees = 70000 paise
        assert req.get_closing_counted_paise() == 70000

    def test_close_request_notes_max_length(self):
        """Notes exceeding max_length=1000 should be rejected."""
        with pytest.raises(Exception):
            DrawerCloseRequest(closing_counted=5000, notes="x" * 1001)

    def test_close_request_reason_max_length(self):
        """Cash taken out reason exceeding max_length=500 should be rejected."""
        with pytest.raises(Exception):
            DrawerCloseRequest(closing_counted=5000, cash_taken_out=1000, cash_taken_out_reason="x" * 501)
