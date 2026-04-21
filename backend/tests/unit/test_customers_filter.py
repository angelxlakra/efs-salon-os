"""
Unit tests for the `exclude_walkins` query param in list_customers.

Filter logic under test (from app/api/customers.py):

    if exclude_walkins:
        query = query.filter(Customer.phone.isnot(None), Customer.phone != '')

Tests operate directly on the SQLAlchemy query layer — no HTTP client needed —
so they run fast and do not require a running FastAPI server.

Test plan:
  1. exclude_walkins=False (default) — walk-ins (phone=NULL) ARE returned
  2. exclude_walkins=True  — walk-ins (phone=NULL) are excluded
  3. exclude_walkins=True  — customers with phone='' are also excluded
  4. exclude_walkins=True  — customers with a valid phone ARE returned
  5. exclude_walkins=True + search — both filters apply simultaneously

To run:
    uv run pytest tests/unit/test_customers_filter.py -v -s
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer(
    db: Session,
    first_name: str,
    phone: str | None,
    last_name: str | None = None,
) -> Customer:
    """
    Persist a single Customer and return the flushed ORM object.

    phone=None  → walk-in with NULL phone (the walk-in scenario)
    phone=''    → walk-in with empty-string phone (treated as walk-in)
    phone=<str> → real customer with a phone number
    """
    customer = Customer(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        total_visits=0,
        total_spent=0,
    )
    db.add(customer)
    db.flush()
    return customer


def _apply_exclude_walkins(query):
    """
    Apply the exact filter from app/api/customers.py list_customers.

    Mirrors:
        query = query.filter(Customer.phone.isnot(None), Customer.phone != '')
    """
    return query.filter(Customer.phone.isnot(None), Customer.phone != "")


def _base_query(db: Session):
    """Return the base active-customer query (deleted_at IS NULL)."""
    return db.query(Customer).filter(Customer.deleted_at.is_(None))


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestExcludeWalkinsDefault:
    """
    Test Case 1: exclude_walkins=False (the default)

    When the flag is not set, the filter block is skipped entirely.
    Walk-in customers (phone IS NULL) MUST appear in the results.
    """

    def test_walkin_with_null_phone_is_returned_when_flag_is_false(
        self, db_session: Session
    ):
        """
        SCENARIO: Two customers exist — one with a phone, one walk-in (NULL phone).
        GIVEN   : exclude_walkins=False (flag not applied)
        EXPECTED: Both customers appear in query results.
        """
        walkin = _make_customer(db_session, "WalkIn Null", phone=None)
        regular = _make_customer(db_session, "Regular", phone="9870000101")

        # No exclude_walkins filter applied
        results = _base_query(db_session).all()
        ids = {c.id for c in results}

        assert walkin.id in ids, (
            "Walk-in customer with NULL phone must be returned when "
            "exclude_walkins is False"
        )
        assert regular.id in ids, "Regular customer must also be returned"


class TestExcludeWalkinsNullPhone:
    """
    Test Case 2: exclude_walkins=True — customers with phone=NULL are excluded.
    """

    def test_walkin_with_null_phone_is_excluded(self, db_session: Session):
        """
        SCENARIO: Walk-in customer has phone=NULL; flag is True.
        EXPECTED: Walk-in does NOT appear; regular customer does.
        """
        walkin = _make_customer(db_session, "NullPhone WalkIn", phone=None)
        regular = _make_customer(db_session, "HasPhone Regular", phone="9870000201")

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert walkin.id not in ids, (
            "Customer with NULL phone must be excluded when exclude_walkins=True"
        )
        assert regular.id in ids, (
            "Customer with a valid phone must remain in results"
        )

    def test_all_walkins_excluded_when_only_walkins_exist(
        self, db_session: Session
    ):
        """
        SCENARIO: Only walk-in customers (NULL phone) exist in the table.
        EXPECTED: Query returns zero results.
        """
        _make_customer(db_session, "WalkIn A", phone=None)
        _make_customer(db_session, "WalkIn B", phone=None)

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()

        # Filter only the IDs we just created to stay isolated from other tests
        assert results == [] or all(
            c.phone is not None and c.phone != "" for c in results
        ), "No customer with NULL/empty phone should survive the filter"


class TestExcludeWalkinsEmptyPhone:
    """
    Test Case 3: exclude_walkins=True — customers with phone='' are also excluded.

    An empty string is treated as a walk-in sentinel, equivalent to NULL.
    """

    def test_walkin_with_empty_string_phone_is_excluded(
        self, db_session: Session
    ):
        """
        SCENARIO: A customer record was created with phone=''.
        EXPECTED: Excluded from results when exclude_walkins=True.
        """
        empty_phone = _make_customer(db_session, "EmptyPhone WalkIn", phone="")
        regular = _make_customer(db_session, "HasPhone Regular2", phone="9870000301")

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert empty_phone.id not in ids, (
            "Customer with empty-string phone must be excluded when exclude_walkins=True"
        )
        assert regular.id in ids, (
            "Customer with a valid phone must remain in results"
        )

    def test_both_null_and_empty_phone_are_excluded_together(
        self, db_session: Session
    ):
        """
        SCENARIO: One customer has NULL phone; another has empty-string phone;
                  one has a valid phone.
        EXPECTED: Only the valid-phone customer survives the filter.
        """
        null_phone = _make_customer(db_session, "Null Phone", phone=None)
        empty_phone = _make_customer(db_session, "Empty Phone", phone="")
        valid_phone = _make_customer(db_session, "Valid Phone", phone="9870000302")

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert null_phone.id not in ids, "NULL-phone customer must be excluded"
        assert empty_phone.id not in ids, "Empty-phone customer must be excluded"
        assert valid_phone.id in ids, "Valid-phone customer must be retained"


class TestExcludeWalkinsValidPhone:
    """
    Test Case 4: exclude_walkins=True — customers with a valid phone ARE returned.
    """

    def test_customer_with_valid_phone_is_retained(self, db_session: Session):
        """
        SCENARIO: Customer has a non-null, non-empty phone number.
        EXPECTED: Customer appears in results when exclude_walkins=True.
        """
        customer = _make_customer(
            db_session, "Priya", phone="9870000401", last_name="Sharma"
        )

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert customer.id in ids, (
            "Customer with a valid phone must be returned when exclude_walkins=True"
        )

    def test_multiple_valid_phone_customers_all_retained(
        self, db_session: Session
    ):
        """
        SCENARIO: Several real customers, no walk-ins.
        EXPECTED: All are returned when exclude_walkins=True.
        """
        c1 = _make_customer(db_session, "Raju", phone="9870000402")
        c2 = _make_customer(db_session, "Sita", phone="9870000403")
        c3 = _make_customer(db_session, "Mohan", phone="9870000404")

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert c1.id in ids, "c1 with valid phone must be retained"
        assert c2.id in ids, "c2 with valid phone must be retained"
        assert c3.id in ids, "c3 with valid phone must be retained"

    def test_soft_deleted_valid_phone_customer_is_not_returned(
        self, db_session: Session
    ):
        """
        EDGE CASE: A customer with a valid phone who has been soft-deleted.
        EXPECTED: Does NOT appear — the base query already filters deleted_at IS NULL.
                  Confirms the two filters compose correctly.
        """
        deleted = _make_customer(db_session, "DeletedReal", phone="9870000405")
        deleted.soft_delete()
        db_session.flush()

        active = _make_customer(db_session, "ActiveReal", phone="9870000406")

        query = _apply_exclude_walkins(_base_query(db_session))
        results = query.all()
        ids = {c.id for c in results}

        assert deleted.id not in ids, (
            "Soft-deleted customer must not appear even with a valid phone"
        )
        assert active.id in ids, "Active customer with valid phone must appear"


class TestExcludeWalkinsWithSearch:
    """
    Test Case 5: exclude_walkins=True combined with a search term.

    Both filters must be applied simultaneously (AND semantics).
    The search mirrors the OR ilike logic from the endpoint:
        Customer.first_name.ilike(...)
        Customer.last_name.ilike(...)
        Customer.phone.ilike(...)
    """

    def _apply_search(self, query, search: str):
        """
        Apply the same search filter as list_customers in the endpoint.
        """
        return query.filter(
            or_(
                Customer.first_name.ilike(f"%{search}%"),
                Customer.last_name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )

    def test_search_does_not_resurface_excluded_walkin(
        self, db_session: Session
    ):
        """
        SCENARIO: A walk-in customer (NULL phone) has a first_name that matches
                  the search term. exclude_walkins=True is also active.
        EXPECTED: The walk-in does NOT appear — exclude_walkins takes priority
                  because both conditions must hold (AND, not OR).
        """
        # Walk-in whose name would match the search
        walkin = _make_customer(db_session, "Deepika", phone=None)
        # Real customer whose name also matches
        real = _make_customer(db_session, "Deepak", phone="9870000501")

        query = self._apply_search(
            _apply_exclude_walkins(_base_query(db_session)),
            search="deep",
        )
        results = query.all()
        ids = {c.id for c in results}

        assert walkin.id not in ids, (
            "Walk-in matching the search must still be excluded by exclude_walkins"
        )
        assert real.id in ids, (
            "Real customer matching both search and phone requirement must appear"
        )

    def test_search_excludes_non_matching_valid_phone_customers(
        self, db_session: Session
    ):
        """
        SCENARIO: exclude_walkins=True AND search='anita'.
                  One customer matches search + has phone; another has phone
                  but doesn't match the search.
        EXPECTED: Only the customer satisfying BOTH conditions is returned.
        """
        matching = _make_customer(
            db_session, "Anita", phone="9870000502", last_name="Rao"
        )
        non_matching = _make_customer(
            db_session, "Suresh", phone="9870000503"
        )
        walkin = _make_customer(db_session, "Anita WalkIn", phone=None)

        query = self._apply_search(
            _apply_exclude_walkins(_base_query(db_session)),
            search="anita",
        )
        results = query.all()
        ids = {c.id for c in results}

        assert matching.id in ids, (
            "Customer matching both search and phone requirement must appear"
        )
        assert non_matching.id not in ids, (
            "Customer with phone but not matching search must be excluded"
        )
        assert walkin.id not in ids, (
            "Walk-in matching search must be excluded by exclude_walkins"
        )

    def test_search_by_phone_substring_with_exclude_walkins(
        self, db_session: Session
    ):
        """
        SCENARIO: search='60016' matches a phone substring; exclude_walkins=True.
                  A walk-in (NULL phone) cannot match the phone ilike branch,
                  and a real customer whose phone contains '60016' should appear.
        EXPECTED: Real customer returned; walk-in excluded.
        """
        real = _make_customer(db_session, "PhoneMatch", phone="9876600160")
        walkin = _make_customer(db_session, "PhoneMatch WalkIn", phone=None)

        query = self._apply_search(
            _apply_exclude_walkins(_base_query(db_session)),
            search="60016",
        )
        results = query.all()
        ids = {c.id for c in results}

        assert real.id in ids, (
            "Real customer whose phone contains the search term must be returned"
        )
        assert walkin.id not in ids, (
            "Walk-in (NULL phone) must be excluded regardless of name match"
        )

    def test_no_results_when_search_matches_nothing(
        self, db_session: Session
    ):
        """
        EDGE CASE: search term matches no customer at all; exclude_walkins=True.
        EXPECTED: Empty result set — filter composition does not cause errors.
        """
        _make_customer(db_session, "Kamala", phone="9870000504")

        query = self._apply_search(
            _apply_exclude_walkins(_base_query(db_session)),
            search="ZZZNOMATCH",
        )
        results = query.all()

        assert results == [], (
            "Combined filter with an unmatched search must return an empty list"
        )
