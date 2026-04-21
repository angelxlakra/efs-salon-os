"""Unit tests for CentralSyncService.

Tests cover:
- push_pending_customers: batch selection, sync-flag updates, merge logging
- pull_customer_delta: epoch fallback, as_of persistence, skipping null phones
- apply_incoming_customers: insert new, update if newer, skip if older/equal
- send_heartbeat: success path, swallowed network error

All HTTP calls are mocked with httpx.Client so no real network is required.

To run:
    uv run pytest tests/unit/test_central_sync_service.py -v -s
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.settings import SalonSettings
from app.utils import generate_ulid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc)
PAST = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
FUTURE = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)


def _make_customer(
    db: Session,
    phone: str = "9876543210",
    first_name: str = "Priya",
    last_synced: datetime | None = None,
    updated_at_override: datetime | None = None,
) -> Customer:
    c = Customer(
        id=generate_ulid(),
        first_name=first_name,
        last_name=None,
        phone=phone,
        total_visits=0,
        total_spent=0,
    )
    db.add(c)
    db.flush()
    # Force updated_at to a specific value if needed
    if updated_at_override:
        db.execute(
            __import__("sqlalchemy").text(
                "UPDATE customers SET updated_at = :ts WHERE id = :id"
            ),
            {"ts": updated_at_override, "id": c.id},
        )
        db.flush()
        db.refresh(c)
    if last_synced is not None:
        c.last_synced_to_central = last_synced
        db.flush()
    return c


def _make_settings(db: Session, last_pull_at: datetime | None = None) -> SalonSettings:
    s = SalonSettings(
        id=generate_ulid(),
        salon_name="Test Salon",
        salon_address="123 Test St",
        daily_revenue_target_paise=2000000,
        daily_services_target=25,
    )
    if last_pull_at is not None:
        s.central_last_pull_at = last_pull_at
    db.add(s)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings(monkeypatch):
    """Patch app.config.settings with central sync fields enabled."""
    from app import config

    monkeypatch.setattr(config.settings, "central_sync_enabled", True)
    monkeypatch.setattr(config.settings, "central_api_url", "https://central.example.com")
    monkeypatch.setattr(config.settings, "central_api_key", "test-api-key")
    monkeypatch.setattr(config.settings, "central_sync_push_interval_minutes", 1)
    monkeypatch.setattr(config.settings, "central_sync_pull_interval_minutes", 10)
    return config.settings


# ---------------------------------------------------------------------------
# push_pending_customers
# ---------------------------------------------------------------------------

class TestPushPendingCustomers:
    """Tests for CentralSyncService.push_pending_customers."""

    def test_push_sends_pending_customers(self, db_session: Session, mock_settings):
        """Customers with last_synced_to_central IS NULL are included in the push batch."""
        from app.services.central_sync_service import CentralSyncService

        c = _make_customer(db_session, phone="9000000001", last_synced=None)

        push_response = {
            "results": [{"local_id": c.id, "canonical_id": c.id, "outcome": "created"}],
            "synced": 1,
            "skipped": 0,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = push_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.push_pending_customers()

        assert result["synced"] == 1
        assert result["skipped"] == 0

        # Verify last_synced_to_central was set
        db_session.refresh(c)
        assert c.last_synced_to_central is not None

    def test_push_skips_null_phone_customers(self, db_session: Session, mock_settings):
        """Customers with phone IS NULL must never appear in the push payload."""
        from app.services.central_sync_service import CentralSyncService

        # Customer with no phone — must be excluded
        no_phone = Customer(
            id=generate_ulid(),
            first_name="WalkIn",
            phone=None,
            total_visits=0,
            total_spent=0,
        )
        db_session.add(no_phone)
        db_session.flush()

        push_response = {"results": [], "synced": 0, "skipped": 0}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = push_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.push_pending_customers()

        # No call should include the no-phone customer
        if mock_client_instance.post.called:
            call_body = mock_client_instance.post.call_args
            # Extract the JSON payload if any
            json_body = call_body.kwargs.get("json", {}) or (
                call_body.args[1] if len(call_body.args) > 1 else {}
            )
            customer_ids = [cu["local_id"] for cu in json_body.get("customers", [])]
            assert no_phone.id not in customer_ids

    def test_push_skips_empty_phone_customers(self, db_session: Session, mock_settings):
        """Customers with phone='' (empty string) must be excluded from push."""
        from app.services.central_sync_service import CentralSyncService

        empty_phone = Customer(
            id=generate_ulid(),
            first_name="EmptyPhone",
            phone="",
            total_visits=0,
            total_spent=0,
        )
        db_session.add(empty_phone)
        db_session.flush()

        push_response = {"results": [], "synced": 0, "skipped": 0}
        mock_response = MagicMock()
        mock_response.json.return_value = push_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.push_pending_customers()

        if mock_client_instance.post.called:
            call_body = mock_client_instance.post.call_args
            json_body = call_body.kwargs.get("json", {}) or {}
            customer_ids = [cu["local_id"] for cu in json_body.get("customers", [])]
            assert empty_phone.id not in customer_ids

    def test_push_returns_zero_when_no_pending(self, db_session: Session, mock_settings):
        """When all customers are already synced, push returns synced=0 without HTTP call."""
        from app.services.central_sync_service import CentralSyncService

        # A customer already synced (last_synced == updated_at)
        c = _make_customer(db_session, phone="9000000002", last_synced=None)
        db_session.refresh(c)  # ensure updated_at is populated from DB before assigning
        c.last_synced_to_central = c.updated_at
        db_session.flush()

        push_response = {"results": [], "synced": 0, "skipped": 0}
        mock_response = MagicMock()
        mock_response.json.return_value = push_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.push_pending_customers()

        assert result["synced"] == 0

    def test_push_logs_warning_on_merge(self, db_session: Session, mock_settings, caplog):
        """When canonical_id != local_id (merge outcome), a warning is logged and no remap happens."""
        import logging
        from app.services.central_sync_service import CentralSyncService

        c = _make_customer(db_session, phone="9000000003", last_synced=None)
        canonical_id = generate_ulid()

        push_response = {
            "results": [{"local_id": c.id, "canonical_id": canonical_id, "outcome": "merged"}],
            "synced": 1,
            "skipped": 0,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = push_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            with caplog.at_level(logging.WARNING, logger="app.services.central_sync_service"):
                service = CentralSyncService(db_session)
                result = service.push_pending_customers()

        # ID must NOT be remapped — local ID stays the same
        db_session.refresh(c)
        assert c.id != canonical_id, "Local ULID must not be remapped in Phase 1"

        # Warning must have been logged
        assert any("merge" in record.message.lower() or canonical_id in record.message
                   for record in caplog.records)

    def test_push_raises_on_http_error(self, db_session: Session, mock_settings):
        """Network/HTTP errors propagate so the job knows the push failed."""
        from app.services.central_sync_service import CentralSyncService
        import httpx

        _make_customer(db_session, phone="9000000004", last_synced=None)

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.side_effect = httpx.ConnectError("connection refused")
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            with pytest.raises(httpx.ConnectError):
                service.push_pending_customers()

    def test_push_does_not_call_api_when_no_candidates(self, db_session: Session, mock_settings):
        """If no pending customers exist, the POST endpoint is never called."""
        from app.services.central_sync_service import CentralSyncService

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.push_pending_customers()

        mock_client_instance.post.assert_not_called()
        assert result == {"synced": 0, "skipped": 0}


# ---------------------------------------------------------------------------
# pull_customer_delta
# ---------------------------------------------------------------------------

class TestPullCustomerDelta:
    """Tests for CentralSyncService.pull_customer_delta."""

    def test_pull_uses_epoch_when_no_last_pull_at(self, db_session: Session, mock_settings):
        """When salon_settings.central_last_pull_at is None, since=epoch is sent."""
        from app.services.central_sync_service import CentralSyncService

        _make_settings(db_session, last_pull_at=None)

        as_of_str = "2026-02-22T10:00:00+00:00"
        pull_response = {"customers": [], "count": 0, "as_of": as_of_str}
        mock_response = MagicMock()
        mock_response.json.return_value = pull_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.pull_customer_delta()

        # Check that since param contains epoch string
        call_kwargs = mock_client_instance.get.call_args.kwargs
        params = call_kwargs.get("params", {})
        assert "since" in params
        assert "1970" in params["since"]

    def test_pull_saves_as_of_not_since(self, db_session: Session, mock_settings):
        """After pull, central_last_pull_at is set to as_of (not the since value)."""
        from app.services.central_sync_service import CentralSyncService

        settings_row = _make_settings(db_session, last_pull_at=PAST)

        as_of_str = "2026-02-22T10:05:00+00:00"
        pull_response = {"customers": [], "count": 0, "as_of": as_of_str}
        mock_response = MagicMock()
        mock_response.json.return_value = pull_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            service.pull_customer_delta()

        db_session.refresh(settings_row)
        assert settings_row.central_last_pull_at is not None
        # as_of is 10:05, not the prior 10:00 since value
        assert settings_row.central_last_pull_at.hour == 10
        assert settings_row.central_last_pull_at.minute == 5

    def test_pull_returns_count_and_as_of(self, db_session: Session, mock_settings):
        """Return dict contains pulled count and as_of timestamp string."""
        from app.services.central_sync_service import CentralSyncService

        _make_settings(db_session, last_pull_at=PAST)

        incoming_customer = {
            "id": generate_ulid(),
            "phone": "9111111111",
            "first_name": "Remote",
            "last_name": None,
            "email": None,
            "gender": None,
            "date_of_birth": None,
            "notes": None,
            "updated_at": "2026-02-22T09:00:00+00:00",
        }
        as_of_str = "2026-02-22T10:05:00+00:00"
        pull_response = {"customers": [incoming_customer], "count": 1, "as_of": as_of_str}
        mock_response = MagicMock()
        mock_response.json.return_value = pull_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            result = service.pull_customer_delta()

        assert result["pulled"] == 1
        assert result["as_of"] == as_of_str


# ---------------------------------------------------------------------------
# apply_incoming_customers
# ---------------------------------------------------------------------------

class TestApplyIncomingCustomers:
    """Tests for CentralSyncService.apply_incoming_customers."""

    def test_insert_new_customer_by_phone(self, db_session: Session, mock_settings):
        """A customer from central with no local match is inserted."""
        from app.services.central_sync_service import CentralSyncService

        canonical_id = generate_ulid()
        incoming = [
            {
                "id": canonical_id,
                "phone": "9222222222",
                "first_name": "NewFromCentral",
                "last_name": "User",
                "email": None,
                "gender": None,
                "date_of_birth": None,
                "notes": None,
                "updated_at": "2026-02-22T09:00:00+00:00",
            }
        ]

        service = CentralSyncService(db_session)
        result = service.apply_incoming_customers(incoming)

        created = db_session.query(Customer).filter(Customer.phone == "9222222222").first()
        assert created is not None
        assert created.first_name == "NewFromCentral"
        assert created.last_synced_to_central is not None
        assert result["created"] == 1
        assert result["updated"] == 0

    def test_update_existing_customer_if_central_is_newer(self, db_session: Session, mock_settings):
        """If central updated_at > local updated_at, fields are overwritten."""
        from app.services.central_sync_service import CentralSyncService

        local = _make_customer(db_session, phone="9333333333", first_name="OldName")
        # Set updated_at to a known past time
        db_session.execute(
            __import__("sqlalchemy").text(
                "UPDATE customers SET updated_at = :ts WHERE id = :id"
            ),
            {"ts": PAST, "id": local.id},
        )
        db_session.flush()
        db_session.refresh(local)

        canonical_id = generate_ulid()
        incoming = [
            {
                "id": canonical_id,
                "phone": "9333333333",
                "first_name": "NewName",
                "last_name": "Updated",
                "email": "new@example.com",
                "gender": "female",
                "date_of_birth": None,
                "notes": "updated notes",
                "updated_at": FUTURE.isoformat(),
            }
        ]

        service = CentralSyncService(db_session)
        result = service.apply_incoming_customers(incoming)

        db_session.refresh(local)
        assert local.first_name == "NewName"
        assert local.last_name == "Updated"
        assert local.email == "new@example.com"
        assert local.gender == "female"
        assert local.notes == "updated notes"
        assert local.last_synced_to_central is not None
        assert result["updated"] == 1
        assert result["created"] == 0

    def test_skip_existing_customer_if_central_is_older(self, db_session: Session, mock_settings):
        """If central updated_at <= local updated_at, local record is NOT overwritten."""
        from app.services.central_sync_service import CentralSyncService

        local = _make_customer(db_session, phone="9444444444", first_name="LocalName")
        # Set local updated_at to FUTURE (newer than incoming)
        db_session.execute(
            __import__("sqlalchemy").text(
                "UPDATE customers SET updated_at = :ts WHERE id = :id"
            ),
            {"ts": FUTURE, "id": local.id},
        )
        db_session.flush()
        db_session.refresh(local)

        canonical_id = generate_ulid()
        incoming = [
            {
                "id": canonical_id,
                "phone": "9444444444",
                "first_name": "CentralName",  # should NOT overwrite
                "last_name": None,
                "email": None,
                "gender": None,
                "date_of_birth": None,
                "notes": None,
                "updated_at": PAST.isoformat(),  # older than local
            }
        ]

        service = CentralSyncService(db_session)
        result = service.apply_incoming_customers(incoming)

        db_session.refresh(local)
        assert local.first_name == "LocalName", "Local name must not be overwritten by older central record"
        assert result["updated"] == 0
        assert result["created"] == 0

    def test_skip_incoming_with_null_phone(self, db_session: Session, mock_settings):
        """Incoming customers with null or empty phone are skipped entirely."""
        from app.services.central_sync_service import CentralSyncService

        incoming = [
            {
                "id": generate_ulid(),
                "phone": None,
                "first_name": "NullPhone",
                "last_name": None,
                "email": None,
                "gender": None,
                "date_of_birth": None,
                "notes": None,
                "updated_at": NOW.isoformat(),
            },
            {
                "id": generate_ulid(),
                "phone": "",
                "first_name": "EmptyPhone",
                "last_name": None,
                "email": None,
                "gender": None,
                "date_of_birth": None,
                "notes": None,
                "updated_at": NOW.isoformat(),
            },
        ]

        service = CentralSyncService(db_session)
        result = service.apply_incoming_customers(incoming)

        assert result["created"] == 0
        assert result["updated"] == 0

    def test_apply_is_idempotent(self, db_session: Session, mock_settings):
        """Calling apply_incoming_customers twice with the same data is safe (idempotent)."""
        from app.services.central_sync_service import CentralSyncService

        canonical_id = generate_ulid()
        incoming = [
            {
                "id": canonical_id,
                "phone": "9555555555",
                "first_name": "IdempotentTest",
                "last_name": None,
                "email": None,
                "gender": None,
                "date_of_birth": None,
                "notes": None,
                "updated_at": NOW.isoformat(),
            }
        ]

        service = CentralSyncService(db_session)
        service.apply_incoming_customers(incoming)
        # Second call should not raise or create duplicates
        service.apply_incoming_customers(incoming)

        count = (
            db_session.query(Customer)
            .filter(Customer.phone == "9555555555", Customer.deleted_at.is_(None))
            .count()
        )
        assert count == 1, "Should only have one customer record after two identical applies"


# ---------------------------------------------------------------------------
# send_heartbeat
# ---------------------------------------------------------------------------

class TestSendHeartbeat:
    """Tests for CentralSyncService.send_heartbeat."""

    def test_heartbeat_posts_to_endpoint(self, db_session: Session, mock_settings):
        """Heartbeat sends POST /v1/stores/heartbeat."""
        from app.services.central_sync_service import CentralSyncService

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"received_at": "2026-02-22T10:00:00+00:00"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            service.send_heartbeat()  # should not raise

        mock_client_instance.post.assert_called_once()
        call_path = mock_client_instance.post.call_args.args[0]
        assert "heartbeat" in call_path

    def test_heartbeat_swallows_network_error(self, db_session: Session, mock_settings, caplog):
        """Heartbeat failure must NOT raise — it logs the error and returns silently."""
        import logging
        from app.services.central_sync_service import CentralSyncService
        import httpx

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post.side_effect = httpx.ConnectError("unreachable")
            MockClient.return_value = mock_client_instance

            service = CentralSyncService(db_session)
            with caplog.at_level(logging.ERROR, logger="app.services.central_sync_service"):
                service.send_heartbeat()  # must NOT raise

        assert any("heartbeat" in r.message.lower() or "unreachable" in r.message.lower()
                   for r in caplog.records)


# ---------------------------------------------------------------------------
# Configuration guard (sync disabled)
# ---------------------------------------------------------------------------

class TestSyncDisabledGuard:
    """When central_sync_enabled=False, jobs must return early without side effects."""

    def test_push_job_skips_when_disabled(self, db_session: Session, monkeypatch):
        """customer_sync_push_job does nothing when CENTRAL_SYNC_ENABLED=False."""
        from app import config
        monkeypatch.setattr(config.settings, "central_sync_enabled", False)

        from app.jobs.scheduled import customer_sync_push_job

        with patch("app.services.central_sync_service.CentralSyncService") as MockService:
            customer_sync_push_job()
            MockService.assert_not_called()

    def test_pull_job_skips_when_disabled(self, db_session: Session, monkeypatch):
        """customer_sync_pull_job does nothing when CENTRAL_SYNC_ENABLED=False."""
        from app import config
        monkeypatch.setattr(config.settings, "central_sync_enabled", False)

        from app.jobs.scheduled import customer_sync_pull_job

        with patch("app.services.central_sync_service.CentralSyncService") as MockService:
            customer_sync_pull_job()
            MockService.assert_not_called()

    def test_heartbeat_job_skips_when_disabled(self, db_session: Session, monkeypatch):
        """central_heartbeat_job does nothing when CENTRAL_SYNC_ENABLED=False."""
        from app import config
        monkeypatch.setattr(config.settings, "central_sync_enabled", False)

        from app.jobs.scheduled import central_heartbeat_job

        with patch("app.services.central_sync_service.CentralSyncService") as MockService:
            central_heartbeat_job()
            MockService.assert_not_called()
