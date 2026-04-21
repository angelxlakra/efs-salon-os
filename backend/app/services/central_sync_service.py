"""Central sync service for pushing/pulling customer data to/from central API.

All network calls use a synchronous httpx.Client (not async) because this
service is consumed by the BlockingScheduler worker (plain def jobs, not coroutines).

Design constraints:
- sync_enabled guard must be checked by the *caller* (job function), not here.
- push_pending_customers: safe to call repeatedly (idempotent by last_synced_to_central).
  "skipped" outcome (rejected by central, e.g. invalid phone) does NOT stamp
  last_synced_to_central, so the customer will be re-queued on the next run.
- apply_incoming_customers: insert-or-update based on phone lookup + updated_at comparison.
  Fields from central that are None/empty are NOT written over non-None local values.
- send_heartbeat: failure is non-critical; errors are logged and swallowed.
  Does not require a database session.
"""

import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.billing import Bill, BillStatus, Payment, PaymentMethod
from app.models.customer import Customer
from app.models.settings import SalonSettings
from app.utils import generate_ulid

logger = logging.getLogger(__name__)

PUSH_BATCH_SIZE = 100

# Epoch used as the lower-bound when no prior pull has been recorded
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Phone validation: accept E.164 (+countrycode...) or 10-15 digit numbers
_PHONE_RE = re.compile(r'^\+?[1-9]\d{1,14}$')


def _normalize_phone(phone: str | None) -> str | None:
    """Strip whitespace/dashes and validate phone format.

    Returns the normalised phone string, or None if invalid/empty.
    """
    if not phone:
        return None
    normalized = re.sub(r'[\s\-()+]', '', phone.strip())
    # Re-add leading + if original had it (E.164)
    if phone.strip().startswith('+'):
        normalized = '+' + normalized
    if not _PHONE_RE.match(normalized):
        return None
    return normalized


def _parse_date(value) -> date | None:
    """Parse an ISO date string or return None. Used for date_of_birth."""
    if not value:
        return None
    try:
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        return None


class CentralSyncService:
    """Handles all communication between this SalonOS store and the central API."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        """Lazily create a shared httpx.Client for the lifetime of this service instance."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=settings.central_api_url,
                headers={"X-Store-API-Key": settings.central_api_key},
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client. Call this in a finally block."""
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push_pending_customers(self) -> dict:
        """Push up to PUSH_BATCH_SIZE customers whose local data is ahead of central.

        A customer is considered pending if:
          - last_synced_to_central IS NULL  (never pushed), OR
          - last_synced_to_central < updated_at  (updated locally since last push)

        Only non-deleted customers with a non-null, non-empty phone are included.

        "skipped" outcome from central means the record was rejected (e.g. invalid
        phone format). These are NOT stamped so they will be re-queued on the next
        run. All other outcomes (created, updated, unchanged, merged) stamp the field.

        On HTTP error or network failure the exception propagates so the
        calling job can log it at job level.

        Returns:
            {"synced": int, "skipped": int}
        """
        pending = (
            self.db.query(Customer)
            .filter(
                Customer.deleted_at.is_(None),
                Customer.phone.isnot(None),
                Customer.phone != '',
                (
                    (Customer.last_synced_to_central == None)  # noqa: E711
                    | (Customer.last_synced_to_central < Customer.updated_at)
                ),
            )
            .limit(PUSH_BATCH_SIZE)
            .all()
        )

        if not pending:
            logger.debug("No pending customers to push.")
            return {"synced": 0, "skipped": 0}

        payload = {
            "customers": [
                {
                    "local_id": c.id,
                    "phone": c.phone,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "gender": c.gender,
                    "date_of_birth": c.date_of_birth.isoformat() if c.date_of_birth else None,
                    "notes": c.notes,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in pending
            ]
        }

        client = self._get_client()
        response = client.post("/v1/customers/push", json=payload)
        response.raise_for_status()
        data = response.json()

        now_utc = datetime.now(timezone.utc)

        # Index pending customers by id for quick lookup
        customer_map = {c.id: c for c in pending}

        for result in data.get("results", []):
            local_id = result.get("local_id")
            canonical_id = result.get("canonical_id")
            outcome = result.get("outcome")

            # "skipped" = central rejected the record. Do not stamp — let it retry.
            if outcome == "skipped":
                continue

            # Phase 1: log merge but do NOT remap ULIDs (deferred to Phase 3)
            if canonical_id and canonical_id != local_id:
                logger.warning(
                    "Central merge detected: local_id=%s was merged into canonical_id=%s. "
                    "ULID remap deferred to Phase 3.",
                    local_id,
                    canonical_id,
                )

            if local_id in customer_map:
                customer_map[local_id].last_synced_to_central = now_utc

        self.db.commit()

        return {
            "synced": data.get("synced", 0),
            "skipped": data.get("skipped", 0),
        }

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    def pull_customer_delta(self) -> dict:
        """Fetch customer records updated since our last pull and apply them locally.

        Uses salon_settings.central_last_pull_at as the lower bound.
        Falls back to epoch (1970-01-01) if never pulled before.

        After a successful pull, stores the response as_of value (not the
        since parameter) to prevent timestamp-gap races.

        Note: If no SalonSettings row exists, the as_of anchor cannot be persisted
        and every pull will re-fetch from epoch. Ensure salon_settings has a row
        before enabling sync.

        Returns:
            {"pulled": int, "as_of": str}
        """
        settings_row = self.db.query(SalonSettings).first()
        since_dt = _EPOCH
        if settings_row and settings_row.central_last_pull_at:
            since_dt = settings_row.central_last_pull_at

        if not settings_row:
            logger.warning(
                "No salon_settings row found. The as_of anchor cannot be persisted. "
                "Every pull will re-fetch from epoch until a settings row is created."
            )

        client = self._get_client()
        response = client.get(
            "/v1/customers/delta",
            params={"since": since_dt.isoformat()},
        )
        response.raise_for_status()
        data = response.json()

        customers = data.get("customers", [])
        as_of_str = data.get("as_of")

        apply_result = self.apply_incoming_customers(customers)

        # Persist as_of (not since) to prevent timestamp-gap races
        if settings_row and as_of_str:
            try:
                as_of_parsed = datetime.fromisoformat(as_of_str)
                settings_row.central_last_pull_at = as_of_parsed
                self.db.commit()
            except (ValueError, TypeError) as exc:
                logger.error("Failed to parse as_of timestamp %r: %s", as_of_str, exc)

        pulled_count = apply_result.get("created", 0) + apply_result.get("updated", 0)
        logger.debug(
            "Delta pull complete: pulled=%d created=%d updated=%d as_of=%s",
            pulled_count,
            apply_result.get("created", 0),
            apply_result.get("updated", 0),
            as_of_str,
        )

        return {"pulled": pulled_count, "as_of": as_of_str}

    # ------------------------------------------------------------------
    # Apply incoming
    # ------------------------------------------------------------------

    def apply_incoming_customers(self, customers: list[dict]) -> dict:
        """Upsert a list of customer dicts received from central.

        Rules:
        - Normalise and validate phone before processing. Skip if invalid.
        - Look up local customer by phone (first non-deleted match).
        - If not found: create new record using canonical id from central.
        - If found: update only when central updated_at is strictly newer than local.
          Fields from central that are None/empty are NOT written over non-None
          local values (avoids silent data erasure from partial central records).
        - A single db.commit() at the end.

        Returns:
            {"created": int, "updated": int}
        """
        created = 0
        updated = 0
        # Computed once for the entire batch (all records share the same sync timestamp)
        now_utc = datetime.now(timezone.utc)

        for record in customers:
            phone = _normalize_phone(record.get("phone"))
            if not phone:
                logger.debug("Skipping incoming customer with missing or invalid phone.")
                continue

            canonical_id = record.get("id")
            central_updated_raw = record.get("updated_at")

            try:
                central_updated_at = (
                    datetime.fromisoformat(central_updated_raw)
                    if central_updated_raw
                    else None
                )
            except (ValueError, TypeError):
                logger.warning(
                    "Unparseable updated_at for incoming customer with id=%s; skipping.",
                    canonical_id,
                )
                continue

            # Build phone variants to handle +91 vs 10-digit mismatch.
            # Central may store phones as E.164 (+919876543210) while the
            # local store uses 10-digit format (9876543210), or vice versa.
            phone_variants = [phone]
            if phone.startswith('+91') and len(phone) == 13:
                phone_variants.append(phone[3:])  # "+919876543210" → "9876543210"
            elif len(phone) == 10 and phone.isdigit():
                phone_variants.append('+91' + phone)  # "9876543210" → "+919876543210"

            local = (
                self.db.query(Customer)
                .filter(
                    or_(*[Customer.phone == v for v in phone_variants]),
                    Customer.deleted_at.is_(None),
                )
                .first()
            )

            if local is None:
                # Insert new customer using the canonical id from central
                new_customer = Customer(
                    id=canonical_id or generate_ulid(),
                    phone=phone,
                    first_name=record.get("first_name") or "",
                    last_name=record.get("last_name"),
                    email=record.get("email"),
                    gender=record.get("gender"),
                    date_of_birth=_parse_date(record.get("date_of_birth")),
                    notes=record.get("notes"),
                    total_visits=0,
                    total_spent=0,
                    last_synced_to_central=now_utc,
                )
                self.db.add(new_customer)
                created += 1

            else:
                # Only update if central data is strictly newer
                local_updated_at = local.updated_at
                if local_updated_at and local_updated_at.tzinfo is None:
                    local_updated_at = local_updated_at.replace(tzinfo=timezone.utc)

                if central_updated_at and local_updated_at and central_updated_at > local_updated_at:
                    # Preserve existing local values when central sends None/empty
                    local.first_name = record.get("first_name") or local.first_name
                    local.last_name = record.get("last_name") or local.last_name
                    local.email = record.get("email") or local.email
                    local.gender = record.get("gender") or local.gender
                    local.date_of_birth = (
                        _parse_date(record.get("date_of_birth")) or local.date_of_birth
                    )
                    local.notes = record.get("notes") or local.notes
                    local.last_synced_to_central = now_utc
                    updated += 1

        self.db.commit()
        return {"created": created, "updated": updated}

    # ------------------------------------------------------------------
    # Metrics push
    # ------------------------------------------------------------------

    def push_metrics_snapshot(self, target_date: date) -> None:
        """Push today's aggregated metrics snapshot to central.

        Queries bills, payments, and customers to build a snapshot and POSTs
        it to /v1/metrics/push. Failures are swallowed so they never impact
        the caller (background task or scheduler job).
        """
        try:
            if not settings.central_sync_enabled:
                return

            # Total bills + revenue for target_date
            bills_count, revenue_paise = self.db.query(
                func.count(Bill.id),
                func.coalesce(func.sum(Bill.rounded_total), 0),
            ).filter(
                Bill.status == BillStatus.POSTED,
                func.date(Bill.posted_at) == target_date,
            ).one()

            # Payment method breakdown — join via posted bill IDs on target_date
            posted_bill_ids = (
                self.db.query(Bill.id)
                .filter(
                    Bill.status == BillStatus.POSTED,
                    func.date(Bill.posted_at) == target_date,
                )
                .subquery()
            )

            payment_rows = (
                self.db.query(
                    Payment.payment_method,
                    func.coalesce(func.sum(Payment.amount), 0),
                )
                .filter(Payment.bill_id.in_(posted_bill_ids))
                .group_by(Payment.payment_method)
                .all()
            )

            payment_totals: dict[str, int] = {}
            for method, total in payment_rows:
                payment_totals[method.value if hasattr(method, "value") else str(method)] = int(total)

            cash_paise = payment_totals.get(PaymentMethod.CASH.value, 0)
            upi_paise = payment_totals.get(PaymentMethod.UPI.value, 0)
            card_paise = payment_totals.get(PaymentMethod.CARD.value, 0)

            # New customers registered today
            new_customers_today = self.db.query(func.count(Customer.id)).filter(
                func.date(Customer.created_at) == target_date,
                Customer.deleted_at.is_(None),
            ).scalar() or 0

            # Total pending balance across all customers with outstanding amounts
            pending_balance_total_paise = self.db.query(
                func.coalesce(func.sum(Customer.pending_balance), 0)
            ).filter(
                Customer.pending_balance > 0,
                Customer.deleted_at.is_(None),
            ).scalar() or 0

            payload = {
                "date": target_date.isoformat(),
                "bills_count": int(bills_count),
                "revenue_paise": int(revenue_paise),
                "cash_paise": int(cash_paise),
                "upi_paise": int(upi_paise),
                "card_paise": int(card_paise),
                "new_customers_today": int(new_customers_today),
                "pending_balance_total_paise": int(pending_balance_total_paise),
                "as_of": datetime.now(timezone.utc).isoformat(),
            }

            client = self._get_client()
            response = client.post("/v1/metrics/push", json=payload)
            response.raise_for_status()
            logger.debug("Metrics snapshot pushed for %s: %s bills", target_date, bills_count)

        except Exception as exc:
            logger.error("push_metrics_snapshot failed (non-critical): %s", exc)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def send_heartbeat(self) -> None:
        """POST /v1/stores/heartbeat to signal this store is online.

        Failures are logged but never raised — heartbeat should not crash the worker.
        Does not use self.db; a database session is not required.
        """
        try:
            client = self._get_client()
            response = client.post("/v1/stores/heartbeat")
            response.raise_for_status()
            data = response.json()
            logger.info("Heartbeat acknowledged by central: received_at=%s", data.get("received_at"))
        except Exception as exc:
            logger.error("Heartbeat to central failed (non-critical): %s", exc)
