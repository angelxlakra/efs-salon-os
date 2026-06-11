"""Tests for GST registration mode fields on SalonSettings (Phase 0).

GST mode activates the dual-rate billing scheme:
  - gst_registered: explicit owner toggle (GSTIN presence alone is not enough)
  - gst_effective_from: clean date boundary; bills before it stay legacy
  - invoice_prefix_service / invoice_prefix_product: SRV/PRD series
  - default_service_sac_code / default_product_hsn_code: Rule 46 line codes
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.settings import SalonSettings
from app.schemas.settings import SalonSettingsBase, SalonSettingsUpdate


class TestSalonSettingsModelGstFields:
    def _make(self, **kw):
        return SalonSettings(salon_name="Test Salon", salon_address="Addr", **kw)

    def test_gst_fields_default_off(self, db_session):
        s = self._make()
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.gst_registered is False
        assert s.gst_effective_from is None
        assert s.invoice_prefix_service == "SRV"
        assert s.invoice_prefix_product == "PRD"
        assert s.default_service_sac_code == "999721"
        assert s.default_product_hsn_code == "3305"

    def test_gst_fields_round_trip(self, db_session):
        s = self._make(
            gst_registered=True,
            gst_effective_from=date(2026, 6, 12),
            gstin="29ABCDE1234F1Z5",
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.gst_registered is True
        assert s.gst_effective_from == date(2026, 6, 12)

    def test_to_dict_includes_gst_mode_keys(self, db_session):
        s = self._make(gst_registered=True, gst_effective_from=date(2026, 6, 12))
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        d = s.to_dict()
        assert d["gst_registered"] is True
        assert d["gst_effective_from"] == "2026-06-12"
        assert d["invoice_prefix_service"] == "SRV"
        assert d["invoice_prefix_product"] == "PRD"
        assert d["default_service_sac_code"] == "999721"
        assert d["default_product_hsn_code"] == "3305"

    def test_to_dict_gst_effective_from_none(self, db_session):
        s = self._make()
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.to_dict()["gst_effective_from"] is None


class TestSettingsSchemasGstFields:
    BASE = {"salon_name": "Test", "salon_address": "Addr"}

    def test_base_defaults(self):
        schema = SalonSettingsBase(**self.BASE)
        assert schema.gst_registered is False
        assert schema.gst_effective_from is None
        assert schema.invoice_prefix_service == "SRV"
        assert schema.invoice_prefix_product == "PRD"

    def test_registered_requires_gstin(self):
        with pytest.raises(ValidationError, match="GSTIN"):
            SalonSettingsBase(**self.BASE, gst_registered=True)

    def test_registered_with_gstin_ok(self):
        schema = SalonSettingsBase(
            **self.BASE, gst_registered=True, gstin="29ABCDE1234F1Z5"
        )
        assert schema.gst_registered is True

    def test_update_schema_accepts_gst_fields(self):
        upd = SalonSettingsUpdate(
            gst_registered=True,
            gst_effective_from=date(2026, 6, 12),
            invoice_prefix_service="SV",
            invoice_prefix_product="PR",
        )
        assert upd.gst_registered is True
        assert upd.gst_effective_from == date(2026, 6, 12)

    def test_service_update_rejects_gst_on_without_gstin(self, db_session):
        from app.services.settings_service import SettingsService

        SettingsService.get_or_create_settings(db_session)
        with pytest.raises(ValueError, match="GSTIN"):
            SettingsService.update_settings(db_session, {"gst_registered": True})

    def test_service_update_allows_gst_on_with_gstin(self, db_session):
        from app.services.settings_service import SettingsService

        SettingsService.get_or_create_settings(db_session)
        s = SettingsService.update_settings(
            db_session,
            {"gst_registered": True, "gstin": "29ABCDE1234F1Z5"},
        )
        assert s.gst_registered is True

    def test_prefixes_must_differ(self):
        with pytest.raises(ValidationError, match="differ"):
            SalonSettingsBase(
                **self.BASE,
                invoice_prefix_service="SRV",
                invoice_prefix_product="SRV",
            )
