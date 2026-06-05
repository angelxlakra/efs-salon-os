"""Integration tests for package_expiry_service.py."""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.package_expiry_service import extend_expiry, run_expiry_transitions
from app.models.package import PackageSale, PackageSaleStatus, PackageExpiryExtension
from app.services.package_pricing_engine import DomainError


def test_extend_expiry_forward_succeeds(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """extend_expiry moves expires_at forward and creates an audit extension row."""
    svc = service_factory()
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(customer=customer, services=[svc])
    original_expires = sale.expires_at
    new_expires = original_expires + timedelta(days=30)

    result = extend_expiry(db_session, sale.id, new_expires, "Customer request", user.id)

    assert result.expires_at == new_expires
    # Audit row created
    ext = db_session.query(PackageExpiryExtension).filter(
        PackageExpiryExtension.package_sale_id == sale.id
    ).one()
    assert ext.previous_expires_at == original_expires
    assert ext.new_expires_at == new_expires
    assert ext.reason == "Customer request"


def test_extend_expired_sale_restores_to_active(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """Extending an EXPIRED sale flips it back to ACTIVE."""
    svc = service_factory()
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=PackageSaleStatus.EXPIRED,
    )
    new_expires = datetime.now(timezone.utc) + timedelta(days=60)

    result = extend_expiry(db_session, sale.id, new_expires, "Comp extension", user.id)

    assert result.status == PackageSaleStatus.ACTIVE


def test_extend_backward_raises_domain_error(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """extend_expiry raises DomainError if new date is not forward in time."""
    svc = service_factory()
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(customer=customer, services=[svc])
    bad_date = sale.expires_at - timedelta(days=1)  # earlier than current expiry

    with pytest.raises(DomainError, match="forward"):
        extend_expiry(db_session, sale.id, bad_date, "Bad request", user.id)


def test_run_expiry_transitions_marks_expired(
    db_session, service_factory, customer_factory,
    package_sale_factory,
):
    """run_expiry_transitions marks ACTIVE sales with past expires_at as EXPIRED."""
    svc = service_factory()
    customer = customer_factory()
    expired_sale = package_sale_factory(
        customer=customer, services=[svc],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=PackageSaleStatus.ACTIVE,
    )
    active_sale = package_sale_factory(
        customer=customer, services=[svc],
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.ACTIVE,
    )

    result = run_expiry_transitions(db_session)

    assert result["transitioned"] == 1
    db_session.refresh(expired_sale)
    db_session.refresh(active_sale)
    assert expired_sale.status == PackageSaleStatus.EXPIRED
    assert active_sale.status == PackageSaleStatus.ACTIVE
