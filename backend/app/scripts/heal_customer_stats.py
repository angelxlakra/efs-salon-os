"""Healing script: fix customer stat inconsistencies caused by billing bugs.

Fixes three known issues:
  1. total_visits undercounted when complete_bill() was called with zero payments
     (the customer visited but paid nothing on the spot; the visit was not counted).
  2. last_visit_at stale / NULL when the same bug affected the visit timestamp.
  3. pending_payment_collections with bill_id=NULL that were created before the
     FIFO linking fix — backfills bill_id so that the bills list no longer shows
     "Pending" for bills whose debt has already been collected.

Also reports (but does NOT auto-fix) any potential duplicate customer records
created by the central sync phone-format mismatch (+91 prefix vs 10-digit).
These must be reviewed and merged manually.

Usage (inside the backend container or with uv):
    python -m app.scripts.heal_customer_stats [--dry-run]

    --dry-run   Print what would change without writing to the database.
    --fix       Apply changes (default mode is --dry-run for safety).

The script is idempotent: running it twice produces no additional changes.
"""

import argparse
import logging
import re
import sys
from datetime import datetime, timezone

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models.billing import Bill, BillStatus, Payment
from app.models.customer import Customer
from app.models.pending_payment import PendingPaymentCollection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_plus91(phone: str | None) -> str | None:
    """Normalise Indian phone to 10-digit form (strips +91 prefix if present)."""
    if not phone:
        return None
    stripped = re.sub(r"^\+91", "", phone.strip())
    if len(stripped) == 10 and stripped.isdigit():
        return stripped
    return phone  # Return as-is if not a standard Indian number


# ---------------------------------------------------------------------------
# Stat recomputation
# ---------------------------------------------------------------------------

def _recompute_visits(db, customer_id: str) -> tuple[int, datetime | None]:
    """Return (correct_total_visits, most_recent_posted_at) for a customer.

    Counts POSTED + REFUNDED bills that are original (not refund credit notes)
    i.e. original_bill_id IS NULL.
    """
    rows = (
        db.query(Bill.posted_at)
        .filter(
            Bill.customer_id == customer_id,
            Bill.status.in_([BillStatus.POSTED, BillStatus.REFUNDED]),
            Bill.original_bill_id.is_(None),
        )
        .all()
    )
    count = len(rows)
    last = max((r.posted_at for r in rows if r.posted_at), default=None)
    return count, last


# ---------------------------------------------------------------------------
# Main heal logic
# ---------------------------------------------------------------------------

def heal_customer_stats(db, dry_run: bool) -> dict:
    """Scan all non-deleted customers and fix total_visits + last_visit_at.

    Returns a summary dict with counts of checked / fixed / skipped customers.
    """
    customers = (
        db.query(Customer)
        .filter(Customer.deleted_at.is_(None))
        .order_by(Customer.created_at)
        .all()
    )

    checked = 0
    fixed = 0
    ok = 0

    for cust in customers:
        checked += 1
        correct_visits, correct_last_visit = _recompute_visits(db, cust.id)

        visits_wrong = cust.total_visits != correct_visits
        # last_visit_at is considered wrong if:
        #   - We have a real posted_at timestamp but the field is NULL
        #   - The stored timestamp differs from the latest bill posted_at
        last_wrong = (
            correct_last_visit is not None
            and (
                cust.last_visit_at is None
                or abs(
                    (cust.last_visit_at.replace(tzinfo=timezone.utc) if cust.last_visit_at.tzinfo is None else cust.last_visit_at)
                    - (correct_last_visit.replace(tzinfo=timezone.utc) if correct_last_visit.tzinfo is None else correct_last_visit)
                ).total_seconds()
                > 1
            )
        )

        if visits_wrong or last_wrong:
            fixed += 1
            logger.info(
                "[%s] %s %s | total_visits: %d → %d | last_visit_at: %s → %s",
                "DRY-RUN" if dry_run else "FIX",
                cust.first_name,
                cust.last_name or "",
                cust.total_visits,
                correct_visits,
                cust.last_visit_at,
                correct_last_visit,
            )
            if not dry_run:
                cust.total_visits = correct_visits
                if correct_last_visit is not None:
                    cust.last_visit_at = correct_last_visit
        else:
            ok += 1

    if not dry_run and fixed > 0:
        db.commit()
        logger.info("Committed %d customer stat fixes.", fixed)

    return {"checked": checked, "fixed": fixed, "ok": ok}


# ---------------------------------------------------------------------------
# Central sync duplicate detection
# ---------------------------------------------------------------------------

def report_central_sync_duplicates(db) -> list[dict]:
    """Find customers that appear to be duplicates from central sync.

    Looks for pairs where one record has phone '+91XXXXXXXXXX' and another
    has '9876543210' — the same person, different format. Reports them so
    staff can review and decide which record to keep.

    Returns a list of duplicate groups (each group is a dict with ids/phones).
    """
    customers = (
        db.query(Customer.id, Customer.first_name, Customer.last_name, Customer.phone,
                 Customer.total_visits, Customer.total_spent, Customer.pending_balance,
                 Customer.created_at)
        .filter(Customer.deleted_at.is_(None), Customer.phone.isnot(None))
        .all()
    )

    # Group by normalised phone
    groups: dict[str, list] = {}
    for c in customers:
        key = _strip_plus91(c.phone)
        if key:
            groups.setdefault(key, []).append(c)

    duplicates = []
    for normalized, group in groups.items():
        if len(group) < 2:
            continue
        # Report the group
        duplicates.append({
            "normalized_phone": normalized,
            "records": [
                {
                    "id": c.id,
                    "name": f"{c.first_name} {c.last_name or ''}".strip(),
                    "phone": c.phone,
                    "total_visits": c.total_visits,
                    "total_spent_rupees": round(c.total_spent / 100, 2),
                    "pending_balance_rupees": round(c.pending_balance / 100, 2),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in sorted(group, key=lambda x: x.created_at or datetime.min)
            ],
        })

    return duplicates


# ---------------------------------------------------------------------------
# Backfill: link existing unlinked collections to bills (FIFO)
# ---------------------------------------------------------------------------

def backfill_collection_bill_links(db, dry_run: bool) -> dict:
    """Link historical PendingPaymentCollection records that have bill_id=NULL
    to the appropriate bills using FIFO (oldest bill first).

    This fixes the bills page still showing "Pending" for bills whose debt
    was collected via the customer-level Collect workflow before the FIFO
    linking fix was deployed.

    Returns:
        {"checked": int, "linked": int}
    """
    unlinked = (
        db.query(PendingPaymentCollection)
        .filter(PendingPaymentCollection.bill_id.is_(None))
        .order_by(PendingPaymentCollection.collected_at.asc())
        .all()
    )

    if not unlinked:
        logger.info("No unlinked pending payment collections found.")
        return {"checked": 0, "linked": 0}

    linked = 0

    for collection in unlinked:
        customer_id = collection.customer_id

        # Find POSTED bills with uncovered pending for this customer (FIFO)
        pending_bills = (
            db.query(Bill)
            .filter(
                Bill.customer_id == customer_id,
                Bill.status == BillStatus.POSTED,
                Bill.original_bill_id.is_(None),
                # Only bills posted before this collection (it couldn't cover future bills)
                Bill.posted_at <= collection.collected_at,
            )
            .order_by(Bill.posted_at.asc())
            .all()
        )

        for bill in pending_bills:
            bill_paid_direct = sum(p.amount for p in bill.payments)
            bill_already_collected = (
                db.query(func.coalesce(func.sum(PendingPaymentCollection.amount), 0))
                .filter(PendingPaymentCollection.bill_id == bill.id)
                .scalar()
            )
            bill_uncovered = max(0, bill.rounded_total - bill_paid_direct - bill_already_collected)

            if bill_uncovered <= 0:
                continue

            # This collection fully or partially covers the oldest uncovered bill
            logger.info(
                "[%s] collection=%s (₹%.2f) → bill=%s (%s, uncovered ₹%.2f) customer=%s",
                "DRY-RUN" if dry_run else "LINK",
                collection.id,
                collection.amount / 100,
                bill.invoice_number,
                bill.id,
                bill_uncovered / 100,
                customer_id,
            )

            if not dry_run:
                collection.bill_id = bill.id

            linked += 1
            break  # Each collection links to at most one bill (the oldest)

    if not dry_run and linked > 0:
        db.commit()
        logger.info("Committed %d collection → bill links.", linked)

    return {"checked": len(unlinked), "linked": linked}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Heal customer stat inconsistencies.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print what would change without writing (default).",
    )
    mode.add_argument(
        "--fix",
        action="store_true",
        default=False,
        help="Apply fixes to the database.",
    )
    args = parser.parse_args()

    dry_run = not args.fix
    if dry_run:
        logger.info("=== DRY-RUN MODE — no changes will be written ===")
        logger.info("Re-run with --fix to apply changes.")
    else:
        logger.info("=== FIX MODE — changes WILL be written to the database ===")

    db = SessionLocal()
    try:
        # ----------------------------------------------------------------
        # 1. Fix total_visits / last_visit_at
        # ----------------------------------------------------------------
        logger.info("--- Checking customer visit stats ---")
        result = heal_customer_stats(db, dry_run=dry_run)
        logger.info(
            "Stats check complete: %d checked, %d need fixing, %d already correct.",
            result["checked"],
            result["fixed"],
            result["ok"],
        )

        # ----------------------------------------------------------------
        # 2. Backfill unlinked pending collections → bills
        # ----------------------------------------------------------------
        logger.info("--- Backfilling unlinked pending payment collection → bill links ---")
        backfill_result = backfill_collection_bill_links(db, dry_run=dry_run)
        logger.info(
            "Backfill complete: %d unlinked collections checked, %d linked to bills.",
            backfill_result["checked"],
            backfill_result["linked"],
        )

        # ----------------------------------------------------------------
        # 3. Report central sync duplicates
        # ----------------------------------------------------------------
        logger.info("--- Checking for central sync duplicate customers ---")
        duplicates = report_central_sync_duplicates(db)
        if not duplicates:
            logger.info("No central sync duplicates found.")
        else:
            logger.warning(
                "Found %d potential duplicate customer group(s). "
                "These must be reviewed and merged manually.",
                len(duplicates),
            )
            for dup in duplicates:
                logger.warning("  Normalised phone: %s", dup["normalized_phone"])
                for rec in dup["records"]:
                    logger.warning(
                        "    id=%-30s phone=%-16s visits=%d spent=₹%.2f pending=₹%.2f created=%s name=%s",
                        rec["id"],
                        rec["phone"],
                        rec["total_visits"],
                        rec["total_spent_rupees"],
                        rec["pending_balance_rupees"],
                        (rec["created_at"] or "")[:19],
                        rec["name"],
                    )
            logger.warning(
                "\nTo merge a duplicate: soft-delete the empty central-sync record "
                "(DELETE /api/customers/<id>) after confirming it has no bills. "
                "The real record with transactions is the one with total_visits > 0."
            )

    except Exception as exc:
        logger.error("Healing script failed: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
