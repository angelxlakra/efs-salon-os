"""
  Shared test fixtures for SalonOS tests.
"""

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from _pytest import monkeypatch
from app.database import Base
from sqlalchemy.sql import True_

# =============================================================================
  # DATABASE URL CONFIGURATION
  # =============================================================================

@pytest.fixture(scope="session")
def test_db_url():
    """
        Database URL for testing.
    """
    return "postgresql+psycopg://salon_user:change_me_123@localhost:5432/salon_test_db"

@pytest.fixture(scope="session")
def postgres_admin_engine():
    """
    Admin connection to PostgreSQL (connects to 'postgres' database).
    """

    admin_url = "postgresql+psycopg://salon_user:change_me_123@localhost:5432/postgres"

    engine = create_engine(admin_url, poolclass=NullPool, isolation_level="AUTOCOMMIT")

    yield engine

    engine.dispose()

@pytest.fixture(scope="session")
def test_engine(postgres_admin_engine, test_db_url):
    """
        Create a database session for a test.
    """

    from app.models import (
          user, billing, customer, service,
          appointment, inventory, accounting, audit
      )

    with postgres_admin_engine.connect() as conn:
        conn.execute(
            text("DROP DATABASE IF EXISTS salon_test_db")
        )
        conn.commit()
    print("\n✅ Dropped old salon_test_db (if existed)")



    with postgres_admin_engine.connect() as conn:
        conn.execute(
            text("CREATE DATABASE salon_test_db")
        )
        conn.commit()
    print("✅ Created fresh salon_test_db")

    engine = create_engine(test_db_url, poolclass=NullPool)

    Base.metadata.create_all(engine)
    print("✅ Created all tables in salon_test_db")

    yield engine

    engine.dispose()


    with postgres_admin_engine.connect() as conn:
        conn.execute(
            text("DROP DATABASE IF EXISTS salon_test_db")
        )
        conn.commit()
    print("\n✅ Cleaned up: Dropped salon_test_db")

@pytest.fixture(scope="function")
def db_session(test_engine):
    """
      Provide a database session for a single test.
    """

    SessionLocal = sessionmaker(bind=test_engine)

    session = SessionLocal()

    session.begin()

    yield session

    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def test_role(db_session):
    """
      Create a test role for users.
    """

    from app.models.user import Role, RoleEnum

    role = Role(
        name=RoleEnum.OWNER,
        description="Test owner role",
        permissions={"*": ["*"]}
    )

    db_session.add(role)
    db_session.flush()

    return role

@pytest.fixture(scope="function")
def test_user(db_session, test_role):
    """
        Create a test user.
    """

    from app.models.user import User

    user = User(
        role_id=test_role.id,
        username="test_user",
        email="test@example.com",
        password_hash="fake_hash_for_testing",
        full_name="Test User",
        is_active=True
    )

    db_session.add(user)
    db_session.flush()

    return user


# =============================================================================
# REDIS FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def redis_url():
    """
    Redis URL for testing.

    Uses localhost instead of 'redis' hostname for local testing.
    Database 1 is used for tests (not 0) to avoid interfering with dev data.

    Password support:
    - Set REDIS_TEST_PASSWORD environment variable if your test Redis requires auth
    - Leave unset for passwordless Redis (development only)

    Examples:
        Passwordless: redis://localhost:6379/1
        With auth:    redis://:password@localhost:6379/1
    """
    import os

    password = os.getenv("REDIS_TEST_PASSWORD", "")
    auth = f":{password}@" if password else ""

    return f"redis://{auth}localhost:6379/1"


@pytest.fixture(scope="function")
def redis_client(redis_url, monkeypatch):
    """
    Provide a Redis client for tests with automatic cleanup.

    LEARNING POINTS:
    - monkeypatch: Pytest fixture to modify settings temporarily
    - Uses Redis DB 1 (not 0) to avoid interfering with dev data
    - Automatically flushes test database before and after each test
    - Always closes the connection properly

    Usage in tests:
        def test_something(redis_client):
            redis_client.set("key", "value")
            # Test runs...
            # Cleanup happens automatically!
    """
    import redis
    from app import config

    # Override the Redis URL in settings for this test
    monkeypatch.setattr(config.settings, "redis_url", redis_url)

    # Create Redis client
    client = redis.from_url(redis_url, decode_responses=True)

    # Clean before test (in case previous test failed to cleanup)
    client.flushdb()

    yield client

    # Clean after test (always cleanup!)
    client.flushdb()
    client.close()


@pytest.fixture(scope="function")
def idempotency_service(redis_url, monkeypatch):
    """
    Provide an IdempotencyService configured for testing.
    """

    from app.services.idempotency_service import IdempotencyService
    from app import config

    monkeypatch.setattr(config.settings, "redis_url", redis_url)

    service = IdempotencyService()

    service.redis_client.flushdb()

    yield service

    service.redis_client.flushdb()
    service.redis_client.close()


@pytest.fixture(scope="function")
def test_service_category(db_session):
    """
    Create a test service category.
    """

    from app.models.service import ServiceCategory

    category = ServiceCategory(
        name="Test Haircut Services",
        description="Test category for haircut services",
        display_order=1,
        is_active=True
    )

    db_session.add(category)
    db_session.flush()

    return category


@pytest.fixture(scope="function")
def test_service(db_session, test_service_category):
    """
    Create a test service.
    """

    from app.models.service import Service

    service = Service(
        category_id=test_service_category.id,
        name="Test Men's Haircut",
        description="Standard men's haircut",
        base_price=50000,
        duration_minutes=30,
        is_active=True,
        display_order=1
    )

    db_session.add(service)
    db_session.flush()

    return service

@pytest.fixture(scope="function")
def test_customer(db_session):
    """
    Create a test customer.
    """

    from app.models.customer import Customer

    customer = Customer(
        first_name="Test",
        last_name="Customer",
        phone="9876543210",
        email="test.customer@example.com",
        total_visits=0,
        total_spent=0
    )

    db_session.add(customer)
    db_session.flush()

    return customer