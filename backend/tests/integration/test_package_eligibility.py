"""Eligibility check: returns active+matching+FIFO+non-expired+non-exhausted packages."""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.package_pricing_engine import find_eligible_packages
from app.models.package import PackageSaleStatus, EntitlementType, Shareability


@pytest.fixture
def sample_setup(db_session, customer_factory, service_factory):
    customer = customer_factory()
    service = service_factory()
    return customer, service


def test_returns_active_matching_package(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    sale = package_sale_factory(
        customer=customer,
        services=[service],
        sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.ACTIVE,
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert len(eligible) == 1
    assert eligible[0].id == sale.id


def test_excludes_expired(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=PackageSaleStatus.ACTIVE,
    )
    assert find_eligible_packages(customer.id, service.id, db_session) == []


def test_excludes_exhausted(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    package_sale_factory(
        customer=customer, services=[service], sessions_remaining=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.EXHAUSTED,
    )
    assert find_eligible_packages(customer.id, service.id, db_session) == []


def test_includes_unlimited_with_null_sessions(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    sale = package_sale_factory(
        customer=customer, services=[service],
        entitlement_type=EntitlementType.UNLIMITED,
        sessions_remaining=None, total_sessions_snapshot=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.ACTIVE,
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert eligible[0].id == sale.id


def test_fifo_by_expires_at(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    later = package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    sooner = package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=10),
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert [e.id for e in eligible] == [sooner.id, later.id]


def test_owner_only_excluded_for_other_customer(
    db_session, sample_setup, package_sale_factory, customer_factory,
):
    buyer, service = sample_setup
    other = customer_factory()
    package_sale_factory(
        customer=buyer, services=[service], sessions_remaining=5,
        shareability=Shareability.OWNER_ONLY,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    assert find_eligible_packages(other.id, service.id, db_session) == []


def test_shared_visible_to_other_customer(
    db_session, sample_setup, package_sale_factory, customer_factory,
):
    buyer, service = sample_setup
    other = customer_factory()
    sale = package_sale_factory(
        customer=buyer, services=[service], sessions_remaining=5,
        shareability=Shareability.SHARED,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    eligible = find_eligible_packages(other.id, service.id, db_session)
    assert eligible[0].id == sale.id
