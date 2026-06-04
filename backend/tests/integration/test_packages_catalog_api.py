"""Integration tests for package catalog API endpoints.

Tests cover:
- RBAC gating per role (Owner / Receptionist / Staff)
- Happy path CRUD for definitions
- Status transitions (publish, archive)
- 404 on missing definitions
- 400 on invalid state transitions
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.auth.jwt import JWTHandler
from app.models.user import User, Role, RoleEnum


# ---------------------------------------------------------------------------
# Fixtures: roles + users per role
# ---------------------------------------------------------------------------

@pytest.fixture
def receptionist_role(db_session):
    role = Role(
        name=RoleEnum.RECEPTIONIST,
        description="Receptionist test role",
        permissions={},
    )
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def staff_role(db_session):
    role = Role(
        name=RoleEnum.STAFF,
        description="Staff test role",
        permissions={},
    )
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def owner_user(db_session, test_role):
    """Owner user — test_role fixture already creates the OWNER role."""
    u = User(
        role_id=test_role.id,
        username="api_owner_pkg",
        email="api_owner_pkg@example.com",
        password_hash="fake_hash",
        full_name="API Owner",
        is_active=True,
    )
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def receptionist_user(db_session, receptionist_role):
    u = User(
        role_id=receptionist_role.id,
        username="api_rcpt_pkg",
        email="api_rcpt_pkg@example.com",
        password_hash="fake_hash",
        full_name="API Receptionist",
        is_active=True,
    )
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def staff_user(db_session, staff_role):
    u = User(
        role_id=staff_role.id,
        username="api_staff_pkg",
        email="api_staff_pkg@example.com",
        password_hash="fake_hash",
        full_name="API Staff",
        is_active=True,
    )
    db_session.add(u)
    db_session.flush()
    return u


# ---------------------------------------------------------------------------
# TestClient fixture factory
# ---------------------------------------------------------------------------

def _make_client(db_session, user, monkeypatch):
    """Create a TestClient with a specific user's auth token.

    Patches db.commit -> db.flush so the test transaction can be rolled back
    by the db_session fixture even after endpoint code calls db.commit().
    """
    # Turn commit into flush so the outer transaction stays open for rollback
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
# Payload helpers
# ---------------------------------------------------------------------------

def make_payload(service_id: str, name: str = "Test Bundle") -> dict:
    """Minimal valid PackageDefinitionCreate payload."""
    return {
        "name": name,
        "entitlement_type": "counted",
        "total_sessions": 5,
        "shareability": "owner_only",
        "validity_days": 90,
        "auto_apply": True,
        "cancellation_fee_pct": "20.00",
        "items": [
            {
                "service_id": service_id,
                "quantity": 1,
                "unit_price_paise": 50000,
                "locked": False,
                "display_order": 0,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests: list
# ---------------------------------------------------------------------------

def test_all_roles_can_list(client_as_owner, client_as_receptionist, client_as_staff):
    for client in [client_as_owner, client_as_receptionist, client_as_staff]:
        r = client.get("/api/packages/definitions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_list_requires_auth():
    """Unauthenticated request gets 403 (HTTPBearer raises 403 when no credentials)."""
    client = TestClient(app)
    r = client.get("/api/packages/definitions")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------

def test_owner_can_create(client_as_owner, service_factory):
    svc = service_factory()
    payload = make_payload(svc.id)
    r = client_as_owner.post("/api/packages/definitions", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Bundle"
    assert data["status"] == "draft"
    assert len(data["id"]) == 26
    assert len(data["items"]) == 1
    assert data["items"][0]["unit_price_paise"] == 50000


def test_receptionist_cannot_create(client_as_receptionist, service_factory):
    svc = service_factory()
    r = client_as_receptionist.post("/api/packages/definitions", json=make_payload(svc.id))
    assert r.status_code == 403


def test_staff_cannot_create(client_as_staff, service_factory):
    svc = service_factory()
    r = client_as_staff.post("/api/packages/definitions", json=make_payload(svc.id))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests: get
# ---------------------------------------------------------------------------

def test_owner_can_get_definition(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_owner.get(f"/api/packages/definitions/{def_id}")
    assert r.status_code == 200
    assert r.json()["id"] == def_id


def test_get_nonexistent_returns_404(client_as_owner):
    r = client_as_owner.get("/api/packages/definitions/01AAAAAAAAAAAAAAAAAAAAAAA0")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------

def test_owner_can_update_definition(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    updated_payload = make_payload(svc.id, name="Updated Bundle")
    r = client_as_owner.put(f"/api/packages/definitions/{def_id}", json=updated_payload)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Bundle"


def test_receptionist_cannot_update(client_as_owner, client_as_receptionist, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_receptionist.put(f"/api/packages/definitions/{def_id}", json=make_payload(svc.id))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests: publish
# ---------------------------------------------------------------------------

def test_owner_can_publish(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_owner.post(f"/api/packages/definitions/{def_id}/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published"


def test_publish_already_published_returns_400(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]
    client_as_owner.post(f"/api/packages/definitions/{def_id}/publish")  # first publish

    r = client_as_owner.post(f"/api/packages/definitions/{def_id}/publish")
    assert r.status_code == 400


def test_receptionist_cannot_publish(client_as_owner, client_as_receptionist, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_receptionist.post(f"/api/packages/definitions/{def_id}/publish")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests: archive
# ---------------------------------------------------------------------------

def test_owner_can_archive(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_owner.post(f"/api/packages/definitions/{def_id}/archive")
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


def test_archive_already_archived_returns_400(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]
    client_as_owner.post(f"/api/packages/definitions/{def_id}/archive")  # first archive

    r = client_as_owner.post(f"/api/packages/definitions/{def_id}/archive")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests: delete
# ---------------------------------------------------------------------------

def test_owner_can_delete_definition(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_owner.delete(f"/api/packages/definitions/{def_id}")
    assert r.status_code == 204

    # Verify it's gone
    r2 = client_as_owner.get(f"/api/packages/definitions/{def_id}")
    assert r2.status_code == 404


def test_receptionist_cannot_delete(client_as_owner, client_as_receptionist, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_receptionist.delete(f"/api/packages/definitions/{def_id}")
    assert r.status_code == 403


def test_staff_cannot_delete(client_as_owner, client_as_staff, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id)).json()
    def_id = created["id"]

    r = client_as_staff.delete(f"/api/packages/definitions/{def_id}")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests: status filter on list
# ---------------------------------------------------------------------------

def test_list_filter_by_status(client_as_owner, service_factory):
    svc = service_factory()
    created = client_as_owner.post("/api/packages/definitions", json=make_payload(svc.id, name="Draft Pkg")).json()
    def_id = created["id"]
    client_as_owner.post(f"/api/packages/definitions/{def_id}/publish")

    r = client_as_owner.get("/api/packages/definitions?status=published")
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert "Draft Pkg" in names

    r2 = client_as_owner.get("/api/packages/definitions?status=draft")
    assert r2.status_code == 200
    names2 = [d["name"] for d in r2.json()]
    assert "Draft Pkg" not in names2
