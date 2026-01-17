import sys
from unittest.mock import MagicMock

# Patch Postgres types for SQLite
import sqlalchemy.dialects.postgresql
from sqlalchemy import types

class MockJSONB(types.TypeDecorator):
    impl = types.JSON
    cache_ok = True

class MockARRAY(types.TypeDecorator):
    impl = types.JSON
    cache_ok = True
    def __init__(self, item_type=None, as_tuple=False, dimensions=None, zero_indexes=False):
        super(MockARRAY, self).__init__()

sqlalchemy.dialects.postgresql.JSONB = MockJSONB
sqlalchemy.dialects.postgresql.ARRAY = MockARRAY
from sqlalchemy import ARRAY as SQLArray
# Patch sqlalchemy.ARRAY if it's being used directly (which it isn't in user.py, user.py imports ARRAY from sqlalchemy)
# Wait, user.py does `from sqlalchemy import ... ARRAY`. 
# If I patch `sqlalchemy.ARRAY` it might work.
# But it's a class. 
# Better to patch `app.models.user` or ensure this runs before `app.models.user` is imported.

# To be safe, let's just use the fact that we are mocking BEFORE imports.
# But sqlalchemy.ARRAY is likely standard. Standard ARRAY is not supported by SQLite.
# We might need to replace sqlalchemy.ARRAY with our MockARRAY in `sqlalchemy` module?
# Unsafe.

# Strategy: Mock `app.models.user` ARRAY import? No.
# If user.py says `from sqlalchemy import ARRAY`, it gets the real class.
# I might need to suppress `app.models.user` creation logic for SQLite?
# No, I need the tables.

# Let's hope replacing `sqlalchemy.dialects.postgresql.JSONB` is enough for JSONB.
# For ARRAY, if standard SQLAlchemy ARRAY is used, it throws error on SQLite compile.
# Fix: I will modify `app/models/user.py` to import ARRAY from `sqlalchemy.dialects.postgresql` (if it was specific) or change to JSON.
# But `user.py` uses `from sqlalchemy import ARRAY`.
# I will overwrite `sqlalchemy.ARRAY` ?
sqlalchemy.ARRAY = MockARRAY

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.auth.dependencies import get_current_user, require_owner, require_owner_or_receptionist
from app.models.user import User, Role, RoleEnum
from app.models.inventory import SKU, InventoryCategory, Supplier, ChangeType, ChangeStatus
from app.utils import generate_ulid

# Setup in-memory SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Mock User
mock_owner = User(
    id="owner_id",
    username="owner",
    role=Role(name=RoleEnum.OWNER),
    is_active=True
)

mock_receptionist = User(
    id="receptionist_id",
    username="receptionist",
    role=Role(name=RoleEnum.RECEPTIONIST),
    is_active=True
)

def override_get_current_owner():
    return mock_owner

def override_get_current_receptionist():
    return mock_receptionist

def override_get_current_user():
    return mock_owner

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[require_owner] = override_get_current_owner
app.dependency_overrides[require_owner_or_receptionist] = override_get_current_owner

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_category():
    response = client.post(
        "/api/inventory/categories",
        json={"name": "Hair Products", "description": "Shampoos and conditioners"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Hair Products"
    assert "id" in data

def test_create_sku():
    # Setup Category and Supplier
    db = TestingSessionLocal()
    cat = InventoryCategory(id=generate_ulid(), name="Test Cat")
    sup = Supplier(id=generate_ulid(), name="Test Sup")
    db.add(cat)
    db.add(sup)
    db.commit()
    cat_id = cat.id
    sup_id = sup.id
    db.close()

    response = client.post(
        "/api/inventory/skus",
        json={
            "sku_code": "SKU001",
            "name": "Test Shampoo",
            "uom": "bottle",
            "category_id": cat_id,
            "supplier_id": sup_id,
            "reorder_point": 10
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sku_code"] == "SKU001"
    assert data["current_stock"] == 0

def test_change_request_flow():
    # 1. Create SKU
    db = TestingSessionLocal()
    cat = InventoryCategory(id=generate_ulid(), name="Test Cat")
    sup = Supplier(id=generate_ulid(), name="Test Sup")
    db.add(cat)
    db.add(sup)
    db.commit()
    
    sku = SKU(
        id=generate_ulid(),
        sku_code="SKU002",
        name="Conditioner",
        uom="bottle",
        category_id=cat.id,
        supplier_id=sup.id
    )
    db.add(sku)
    db.commit()
    sku_id = sku.id
    db.close()
    
    # 2. Create Change Request (Receive 10 @ 100)
    response = client.post(
        "/api/inventory/change-requests",
        json={
            "sku_id": sku_id,
            "change_type": "receive",
            "quantity": 10,
            "unit_cost": 10000, # 100 rupees
            "reason_code": "new_stock"
        }
    )
    assert response.status_code == 200
    req_id = response.json()["id"]
    
    # 3. Approve Request
    response = client.post(f"/api/inventory/change-requests/{req_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    
    # 4. Check Stock and Ledger
    response = client.get(f"/api/inventory/skus/{sku_id}")
    assert response.json()["current_stock"] == 10.0
    assert response.json()["avg_cost_per_unit"] == 10000

    response = client.get(f"/api/inventory/ledger/{sku_id}")
    assert len(response.json()) == 1
    assert response.json()[0]["transaction_type"] == "receive"
    assert response.json()[0]["quantity_change"] == 10.0
