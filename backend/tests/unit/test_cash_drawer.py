import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY as PGArray
from sqlalchemy import ARRAY
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb(element, compiler, **kw):
    return "JSON"

@compiles(ARRAY, 'sqlite')
@compiles(PGArray, 'sqlite')
def compile_array(element, compiler, **kw):
    return "JSON"

from app.main import app
from app.api.deps import check_receptionist_permission, get_current_active_user
from app.database import get_db, Base
# Import models to ensure they are registered with Base
from app.models.accounting import CashDrawer
from app.models.billing import Payment, Bill
from app.models.user import User

# Setup in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_mock_user():
    user = MagicMock()
    user.id = "user_123"
    user.is_active = True
    user.is_owner = True
    user.is_receptionist = False
    return user

# Override dependencies at module level
app.dependency_overrides[check_receptionist_permission] = get_mock_user
app.dependency_overrides[get_current_active_user] = get_mock_user

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close here, we do it in the fixture cleanup

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with test database - function scoped to match db_session."""
    with TestClient(app) as c:
        yield c


def test_open_drawer(client, db_session):
    response = client.post("/api/cash/open", json={"opening_float": 1000})
    assert response.status_code == 200
    data = response.json()
    assert data["opening_float"] == 1000
    assert data["opened_by"] == "user_123"

def test_cannot_open_twice(client, db_session):
    client.post("/api/cash/open", json={"opening_float": 1000})
    response = client.post("/api/cash/open", json={"opening_float": 2000})
    assert response.status_code == 400
    assert "already opened" in response.json()["detail"]

def test_close_drawer(client, db_session):
    client.post("/api/cash/open", json={"opening_float": 5000})

    response = client.post("/api/cash/close", json={"closing_counted": 5000, "notes": "All good"})
    assert response.status_code == 200
    data = response.json()
    assert data["closing_counted"] == 5000
    assert data["closed_by"] == "user_123"

def test_reopen_drawer(client, db_session):
    client.post("/api/cash/open", json={"opening_float": 5000})
    client.post("/api/cash/close", json={"closing_counted": 5000})

    response = client.post("/api/cash/reopen", json={"reason": "Forgot something"})
    assert response.status_code == 200
    data = response.json()
    assert data["closed_at"] is None
    assert data["reopen_reason"] == "Forgot something"

def test_get_current_summary_no_drawer(client, db_session):
    """Test getting current summary when no drawer has been opened."""
    response = client.get("/api/cash/current")
    assert response.status_code == 200
    data = response.json()
    assert data["is_open"] is False
    assert data["opening_float"] == 0

def test_get_current_summary_with_drawer(client, db_session):
    """Test getting current summary when drawer is open."""
    client.post("/api/cash/open", json={"opening_float": 5000})
    response = client.get("/api/cash/current")
    assert response.status_code == 200
    data = response.json()
    assert data["is_open"] is True
    assert data["opening_float"] == 5000

def test_get_drawer_history(client, db_session):
    # Open and close a drawer to have history
    client.post("/api/cash/open", json={"opening_float": 5000})
    client.post("/api/cash/close", json={"closing_counted": 5000})

    response = client.get("/api/cash/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_close_without_open(client, db_session):
    """Test closing drawer when none is open."""
    response = client.post("/api/cash/close", json={"closing_counted": 5000})
    assert response.status_code == 404
    assert "No drawer found" in response.json()["detail"]

def test_reopen_without_close(client, db_session):
    """Test reopening drawer that isn't closed."""
    client.post("/api/cash/open", json={"opening_float": 5000})
    response = client.post("/api/cash/reopen", json={"reason": "Testing reopen"})
    assert response.status_code == 400
    assert "currently open" in response.json()["detail"]
