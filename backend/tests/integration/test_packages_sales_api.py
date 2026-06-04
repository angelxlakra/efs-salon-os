"""Integration tests for package sales API endpoints.

Tests cover:
- list sales (all roles can read)
- get sale by ID (404 on missing)
- list active for customer
- extend expiry (owner only)
- refund (owner only)
- RBAC: receptionist/staff cannot extend or refund
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.auth.jwt import JWTHandler
from app.models.user import User, Role, RoleEnum
from app.models.package import PackageSaleStatus, EntitlementType


# ---------------------------------------------------------------------------
# Fixtures (same pattern as test_packages_catalog_api.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def receptionist_role(db_session):
    role = Role(name=RoleEnum.RECEPTIONIST, description="Receptionist", permissions={})
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def staff_role(db_session):
    role = Role(name=RoleEnum.STAFF, description="Staff", permissions={})
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def owner_user(db_session, test_role):
    u = User(role_id=test_role.id, username="sales_owner", email="sales_owner@test.com",
             password_hash="fake", full_name="Sales Owner", is_active=True)
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def receptionist_user(db_session, receptionist_role):
    u = User(role_id=receptionist_role.id, username="sales_rcpt", email="sales_rcpt@test.com",
             password_hash="fake", full_name="Sales Rcpt", is_active=True)
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def staff_user(db_session, staff_role):
    u = User(role_id=staff_role.id, username="sales_staff", email="sales_staff@test.com",
             password_hash="fake", full_name="Sales Staff", is_active=True)
    db_session.add(u)
    db_session.flush()
    return u


def _make_client(db_session, user, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    token = JWTHandler.create_access_token(user)
    client = TestClient(app, raise_server_exceptions=True)
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_as_owner(db_session, owner_user, monkeypatch):
    yield from _make_client(db_session, owner_user, monkeypatch)


@pytest.fixture
def client_as_receptionist(db_session, receptionist_user, monkeypatch):
    yield from _make_client(db_session, receptionist_user, monkeypatch)


@pytest.fixture
def client_as_staff(db_session, staff_user, monkeypatch):
    yield from _make_client(db_session, staff_user, monkeypatch)


# ---------------------------------------------------------------------------
# Tests: list sales
# ---------------------------------------------------------------------------

def test_owner_can_list_sales(client_as_owner):
    r = client_as_owner.get("/api/packages/sales")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_receptionist_can_list_sales(client_as_receptionist):
    r = client_as_receptionist.get("/api/packages/sales")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_staff_can_list_sales(client_as_staff):
    r = client_as_staff.get("/api/packages/sales")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_sales_filter_by_status(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    active_sale = package_sale_factory(customer=cust, services=[svc], status=PackageSaleStatus.ACTIVE)
    expired_sale = package_sale_factory(
        customer=cust, services=[svc],
        status=PackageSaleStatus.EXPIRED,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    r = client_as_owner.get("/api/packages/sales?status=active")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert active_sale.id in ids
    assert expired_sale.id not in ids

    r2 = client_as_owner.get("/api/packages/sales?status=expired")
    assert r2.status_code == 200
    ids2 = [s["id"] for s in r2.json()]
    assert expired_sale.id in ids2
    assert active_sale.id not in ids2


def test_list_sales_filter_by_customer(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust_a = customer_factory()
    cust_b = customer_factory()
    svc = service_factory()
    sale_a = package_sale_factory(customer=cust_a, services=[svc])
    sale_b = package_sale_factory(customer=cust_b, services=[svc])

    r = client_as_owner.get(f"/api/packages/sales?customer_id={cust_a.id}")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sale_a.id in ids
    assert sale_b.id not in ids


# ---------------------------------------------------------------------------
# Tests: get sale by ID
# ---------------------------------------------------------------------------

def test_get_sale_by_id(client_as_owner, package_sale_factory, customer_factory, service_factory):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    r = client_as_owner.get(f"/api/packages/sales/{sale.id}")
    assert r.status_code == 200
    assert r.json()["id"] == sale.id


def test_get_sale_missing_returns_404(client_as_owner):
    r = client_as_owner.get("/api/packages/sales/01AAAAAAAAAAAAAAAAAAAAAAA0")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: list active for customer
# ---------------------------------------------------------------------------

def test_list_active_for_customer(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    active_sale = package_sale_factory(customer=cust, services=[svc], status=PackageSaleStatus.ACTIVE)
    expired_sale = package_sale_factory(
        customer=cust, services=[svc],
        status=PackageSaleStatus.EXPIRED,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    r = client_as_owner.get(f"/api/packages/sales/active-for-customer/{cust.id}")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert active_sale.id in ids
    assert expired_sale.id not in ids


# ---------------------------------------------------------------------------
# Tests: extend expiry
# ---------------------------------------------------------------------------

def test_owner_can_extend_expiry(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    new_expires = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()

    r = client_as_owner.post(
        f"/api/packages/sales/{sale.id}/extend",
        json={"new_expires_at": new_expires, "reason": "Customer request"}
    )
    assert r.status_code == 200
    assert r.json()["id"] == sale.id


def test_receptionist_cannot_extend(
    client_as_receptionist, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    new_expires = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()

    r = client_as_receptionist.post(
        f"/api/packages/sales/{sale.id}/extend",
        json={"new_expires_at": new_expires, "reason": "Test"}
    )
    assert r.status_code == 403


def test_staff_cannot_extend(
    client_as_staff, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    new_expires = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()

    r = client_as_staff.post(
        f"/api/packages/sales/{sale.id}/extend",
        json={"new_expires_at": new_expires, "reason": "Test"}
    )
    assert r.status_code == 403


def test_extend_missing_sale_returns_400_or_404(client_as_owner):
    new_expires = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
    r = client_as_owner.post(
        "/api/packages/sales/01AAAAAAAAAAAAAAAAAAAAAAA0/extend",
        json={"new_expires_at": new_expires, "reason": "Test"}
    )
    # Service raises ValueError for missing sale -> 400 (endpoint has no 404 pre-check for this)
    assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# Tests: refund
# ---------------------------------------------------------------------------

def test_owner_can_refund_sale(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc], sessions_remaining=5)

    r = client_as_owner.post(
        f"/api/packages/sales/{sale.id}/refund",
        json={"payment_method": "cash", "reason": "Customer unhappy"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("credit_note_bill_id") is not None
    assert len(data["credit_note_bill_id"]) == 26  # ULID
    assert data["status"] == "refunded"


def test_receptionist_cannot_refund(
    client_as_receptionist, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    r = client_as_receptionist.post(
        f"/api/packages/sales/{sale.id}/refund",
        json={"payment_method": "cash", "reason": "Test"}
    )
    assert r.status_code == 403


def test_staff_cannot_refund(
    client_as_staff, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    r = client_as_staff.post(
        f"/api/packages/sales/{sale.id}/refund",
        json={"payment_method": "cash", "reason": "Test"}
    )
    assert r.status_code == 403


def test_refund_invalid_method_returns_422(
    client_as_owner, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    r = client_as_owner.post(
        f"/api/packages/sales/{sale.id}/refund",
        json={"payment_method": "bitcoin", "reason": "Test"}
    )
    assert r.status_code == 422
