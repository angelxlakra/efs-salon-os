"""Integration tests for package eligibility check and undo-redemption API endpoints.

Tests cover:
- POST /eligibility/check — all roles can check, returns matching sales
- POST /eligibility/check — returns empty list when no eligible packages
- POST /redemptions/{audit_id}/undo — all roles with redeem permission can undo (DRAFT bill only)
- POST /redemptions/{audit_id}/undo — missing audit returns 400
- POST /redemptions/{audit_id}/undo — posted bill returns 400 (undo not allowed)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.auth.jwt import JWTHandler
from app.models.user import User, Role, RoleEnum

# ---------------------------------------------------------------------------
# Role/user/client fixtures (same pattern as other integration test files)
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
    u = User(role_id=test_role.id, username="elig_owner", email="elig_owner@test.com",
             password_hash="fake", full_name="Elig Owner", is_active=True)
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def receptionist_user(db_session, receptionist_role):
    u = User(role_id=receptionist_role.id, username="elig_rcpt", email="elig_rcpt@test.com",
             password_hash="fake", full_name="Elig Rcpt", is_active=True)
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def staff_user(db_session, staff_role):
    u = User(role_id=staff_role.id, username="elig_staff", email="elig_staff@test.com",
             password_hash="fake", full_name="Elig Staff", is_active=True)
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
# Tests: eligibility check
# ---------------------------------------------------------------------------

def test_owner_can_check_eligibility_returns_match(
    client_as_owner, db_session, package_sale_factory, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    r = client_as_owner.post(
        "/api/packages/eligibility/check",
        json={"customer_id": cust.id, "service_id": svc.id},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["package_sale"]["id"] == sale.id
    assert data[0]["snapshot_price_paise"] == svc.base_price


def test_eligibility_returns_empty_when_no_match(
    client_as_owner, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()  # No sale created for this customer/service

    r = client_as_owner.post(
        "/api/packages/eligibility/check",
        json={"customer_id": cust.id, "service_id": svc.id},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_receptionist_can_check_eligibility(
    client_as_receptionist, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    r = client_as_receptionist.post(
        "/api/packages/eligibility/check",
        json={"customer_id": cust.id, "service_id": svc.id},
    )
    assert r.status_code == 200


def test_staff_can_check_eligibility(
    client_as_staff, customer_factory, service_factory
):
    cust = customer_factory()
    svc = service_factory()
    r = client_as_staff.post(
        "/api/packages/eligibility/check",
        json={"customer_id": cust.id, "service_id": svc.id},
    )
    assert r.status_code == 200


def test_eligibility_invalid_id_length_returns_422(client_as_owner):
    r = client_as_owner.post(
        "/api/packages/eligibility/check",
        json={"customer_id": "short", "service_id": "short"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Tests: undo redemption
# ---------------------------------------------------------------------------

def test_owner_can_undo_redemption(
    client_as_owner, db_session, owner_user,
    package_sale_factory, customer_factory, service_factory, bill_item_factory,
):
    """Create a redemption via apply_redemption then undo it via the API."""
    from app.services.package_redemption_service import apply_redemption

    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    # Create a DRAFT bill item for this service
    bi = bill_item_factory(service_id=svc.id)

    # Apply redemption directly at service level
    audit = apply_redemption(
        db=db_session,
        package_sale_id=sale.id,
        bill_item_id=bi.id,
        redeemed_for_customer_id=cust.id,
        user_id=owner_user.id,
    )
    db_session.flush()

    # Undo via API
    r = client_as_owner.post(f"/api/packages/redemptions/{audit.id}/undo")
    assert r.status_code == 204


def test_receptionist_can_undo_redemption(
    client_as_receptionist, db_session, owner_user,
    package_sale_factory, customer_factory, service_factory, bill_item_factory,
):
    from app.services.package_redemption_service import apply_redemption

    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    bi = bill_item_factory(service_id=svc.id)

    audit = apply_redemption(
        db=db_session,
        package_sale_id=sale.id,
        bill_item_id=bi.id,
        redeemed_for_customer_id=cust.id,
        user_id=owner_user.id,
    )
    db_session.flush()

    r = client_as_receptionist.post(f"/api/packages/redemptions/{audit.id}/undo")
    assert r.status_code == 204


def test_staff_can_undo_redemption(
    client_as_staff, db_session, owner_user,
    package_sale_factory, customer_factory, service_factory, bill_item_factory,
):
    from app.services.package_redemption_service import apply_redemption

    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    bi = bill_item_factory(service_id=svc.id)
    audit = apply_redemption(
        db=db_session,
        package_sale_id=sale.id,
        bill_item_id=bi.id,
        redeemed_for_customer_id=cust.id,
        user_id=owner_user.id,
    )
    db_session.flush()

    r = client_as_staff.post(f"/api/packages/redemptions/{audit.id}/undo")
    assert r.status_code == 204


def test_undo_missing_audit_returns_400(client_as_owner):
    r = client_as_owner.post("/api/packages/redemptions/01AAAAAAAAAAAAAAAAAAAAAAA0/undo")
    assert r.status_code == 400


def test_undo_on_posted_bill_returns_400(
    client_as_owner, db_session, owner_user,
    package_sale_factory, customer_factory, service_factory, bill_item_factory,
):
    """Undo is only allowed on DRAFT bills — POSTED bills must return 400."""
    from app.services.package_redemption_service import apply_redemption
    from app.models.billing import Bill, BillStatus

    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])
    bi = bill_item_factory(service_id=svc.id)

    audit = apply_redemption(
        db=db_session,
        package_sale_id=sale.id,
        bill_item_id=bi.id,
        redeemed_for_customer_id=cust.id,
        user_id=owner_user.id,
    )
    db_session.flush()

    # Promote the bill to POSTED so undo is disallowed
    bill = db_session.get(Bill, bi.bill_id)
    bill.status = BillStatus.POSTED
    db_session.flush()

    r = client_as_owner.post(f"/api/packages/redemptions/{audit.id}/undo")
    assert r.status_code == 400
