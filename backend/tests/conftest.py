"""
  Shared test fixtures for SalonOS tests.
"""

import pytest

from sqlalchemy import create_engine, event, text
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
    import os
    host = os.getenv("TEST_DB_HOST", "localhost")
    return f"postgresql+psycopg://salon_user:change_me_123@{host}:5432/salon_test_db"

@pytest.fixture(scope="session")
def postgres_admin_engine():
    """
    Admin connection to PostgreSQL (connects to 'postgres' database).
    """
    import os
    host = os.getenv("TEST_DB_HOST", "localhost")
    admin_url = f"postgresql+psycopg://salon_user:change_me_123@{host}:5432/postgres"

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
        appointment, inventory, accounting, audit,
        settings, expense, purchase, reconciliation, attendance, package
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
    """Provide an isolated database session for a single test.

    Services under test call ``session.commit()`` themselves, so a plain
    ``session.rollback()`` at teardown cannot undo their durable rows — they
    leak into the next test (e.g. a duplicate seeded ``OWNER`` role). We instead
    use SQLAlchemy's "join an external transaction" recipe: bind the session to a
    single connection wrapped in an outer transaction, and run the test inside a
    SAVEPOINT that auto-restarts every time the test code commits. The outer
    transaction is never committed, so teardown rolls back *everything* the test
    did — service commits included — giving true per-test isolation.
    """
    connection = test_engine.connect()
    outer = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        # When the test code commits/rolls back the SAVEPOINT, open a fresh one
        # so the session stays usable while the outer transaction stays open.
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", _restart_savepoint)
        session.close()
        outer.rollback()
        connection.close()

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


@pytest.fixture
def customer_factory(db_session):
    """Factory that creates Customer objects."""
    from app.models.customer import Customer
    counter = [0]
    def make(**kwargs):
        counter[0] += 1
        c = Customer(
            first_name=kwargs.get("first_name", "Factory"),
            last_name=kwargs.get("last_name", f"Customer{counter[0]}"),
            phone=kwargs.get("phone", f"98765{counter[0]:05d}"),
            total_visits=0,
            total_spent=0,
        )
        db_session.add(c)
        db_session.flush()
        return c
    return make


@pytest.fixture
def service_factory(db_session):
    """Factory that creates Service objects (with auto-created ServiceCategory).

    Note: Service model has no gst_rate_pct column — prices are tax-inclusive paise.
    """
    from app.models.service import Service, ServiceCategory
    counter = [0]
    def make(**kwargs):
        counter[0] += 1
        cat = ServiceCategory(
            name=f"Factory Category {counter[0]}",
            display_order=counter[0],
            is_active=True,
        )
        db_session.add(cat)
        db_session.flush()
        svc = Service(
            category_id=cat.id,
            name=kwargs.get("name", f"Factory Service {counter[0]}"),
            base_price=kwargs.get("base_price", 50000),
            duration_minutes=kwargs.get("duration_minutes", 30),
            is_active=True,
            display_order=counter[0],
        )
        db_session.add(svc)
        db_session.flush()
        return svc
    return make


@pytest.fixture
def user_factory(db_session, test_role):
    """Factory that creates User objects."""
    from app.models.user import User
    counter = [0]
    def make(**kwargs):
        counter[0] += 1
        u = User(
            role_id=test_role.id,
            username=kwargs.get("username", f"factory_user_{counter[0]}"),
            email=kwargs.get("email", f"factory{counter[0]}@example.com"),
            password_hash="fake_hash",
            full_name=kwargs.get("full_name", f"Factory User {counter[0]}"),
            is_active=True,
        )
        db_session.add(u)
        db_session.flush()
        return u
    return make


@pytest.fixture
def bill_factory(db_session, test_user):
    """Factory that creates minimal Bill objects for use as FKs in other factories."""
    from app.models.billing import Bill, BillStatus, BillType
    counter = [0]
    def make(customer_id=None, **kwargs):
        counter[0] += 1
        b = Bill(
            customer_id=customer_id,
            subtotal=kwargs.get("subtotal", 100000),
            discount_amount=0,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=kwargs.get("subtotal", 100000),
            rounded_total=kwargs.get("subtotal", 100000),
            rounding_adjustment=0,
            status=BillStatus.DRAFT,
            bill_type=BillType.NORMAL,
            created_by=test_user.id,
        )
        db_session.add(b)
        db_session.flush()
        return b
    return make


@pytest.fixture
def bill_item_factory(db_session, bill_factory, customer_factory, test_user):
    """Factory that creates BillItem objects, creating a Bill + Customer automatically."""
    from app.models.billing import BillItem, BillItemType
    counter = [0]
    def make(service_id, base_price=100000, quantity=1, bill=None, **kwargs):
        counter[0] += 1
        if bill is None:
            customer = customer_factory()
            bill = bill_factory(customer_id=customer.id)
        item = BillItem(
            bill_id=bill.id,
            service_id=service_id,
            item_name=kwargs.get("item_name", f"Test Service {counter[0]}"),
            base_price=base_price,
            quantity=quantity,
            line_total=base_price * quantity,
            item_type=BillItemType.SERVICE,
        )
        db_session.add(item)
        db_session.flush()
        return item
    return make


@pytest.fixture
def package_definition_factory(db_session, test_user):
    """Factory that creates PackageDefinition + PackageDefinitionItem objects."""
    from decimal import Decimal
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem,
        PackageDefinitionStatus, EntitlementType, Shareability,
    )
    counter = [0]
    def make(services, entitlement_type=EntitlementType.COUNTED, total_sessions=10,
             shareability=Shareability.OWNER_ONLY, validity_days=90, **kwargs):
        counter[0] += 1
        defn = PackageDefinition(
            name=f"Factory Package {counter[0]}",
            status=PackageDefinitionStatus.PUBLISHED,
            entitlement_type=entitlement_type,
            total_sessions=total_sessions if entitlement_type == EntitlementType.COUNTED else None,
            shareability=shareability,
            validity_days=validity_days,
            auto_apply=True,
            cancellation_fee_pct=Decimal("20.00"),
            created_by_user_id=test_user.id,
        )
        db_session.add(defn)
        db_session.flush()

        for i, svc in enumerate(services):
            item = PackageDefinitionItem(
                package_definition_id=defn.id,
                service_id=svc.id,
                quantity=1,
                unit_price_paise=svc.base_price,
                locked=False,
                display_order=i,
            )
            db_session.add(item)
        db_session.flush()
        db_session.refresh(defn)
        return defn
    return make


@pytest.fixture
def definition_factory(package_definition_factory):
    """Alias for package_definition_factory (shorter name for catalog service tests)."""
    return package_definition_factory


@pytest.fixture
def package_sale_factory(db_session, test_user, package_definition_factory):
    """Factory that creates a PackageSale with PackageSaleItems.

    Creates a Bill (required FK) automatically. bill_id has unique=True so each
    call creates its own Bill.
    """
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import (
        PackageSale, PackageSaleItem, PackageSaleStatus, EntitlementType, Shareability,
    )
    counter = [0]

    def make(
        customer,
        services,
        sessions_remaining=5,
        expires_at=None,
        status=PackageSaleStatus.ACTIVE,
        entitlement_type=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        shareability=Shareability.OWNER_ONLY,
        **kwargs,
    ):
        counter[0] += 1
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=90)

        # Create minimal Bill — bill_id is non-nullable and unique on PackageSale
        bill = Bill(
            customer_id=customer.id,
            subtotal=500000,
            discount_amount=0,
            tax_amount=90000,
            cgst_amount=45000,
            sgst_amount=45000,
            total_amount=590000,
            rounded_total=590000,
            rounding_adjustment=0,
            status=BillStatus.POSTED,
            bill_type=BillType.NORMAL,
            created_by=test_user.id,
        )
        db_session.add(bill)
        db_session.flush()

        # Create PackageDefinition
        defn = package_definition_factory(
            services=services,
            entitlement_type=entitlement_type,
            total_sessions=total_sessions_snapshot if entitlement_type == EntitlementType.COUNTED else None,
            shareability=shareability,
        )

        # For UNLIMITED: sessions_remaining and total_sessions_snapshot must be None
        actual_sessions = sessions_remaining
        actual_total_snapshot = total_sessions_snapshot
        if entitlement_type == EntitlementType.UNLIMITED:
            actual_sessions = None
            actual_total_snapshot = None

        sale = PackageSale(
            bill_id=bill.id,
            package_definition_id=defn.id,
            customer_id=customer.id,
            sold_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            entitlement_type_snapshot=entitlement_type,
            shareability_snapshot=shareability,
            cancellation_fee_pct_snapshot=Decimal("20.00"),
            total_sessions_snapshot=actual_total_snapshot,
            sessions_remaining=actual_sessions,
            status=status,
        )
        db_session.add(sale)
        db_session.flush()

        # Create PackageSaleItems from definition items
        for i, (svc, def_item) in enumerate(zip(services, defn.items)):
            sale_item = PackageSaleItem(
                package_sale_id=sale.id,
                package_definition_item_id=def_item.id,
                service_id=svc.id,
                quantity=1,
                snapshot_unit_price_paise=svc.base_price,
                snapshot_gst_rate_pct=Decimal("18.00"),
                locked=False,
                display_order=i,
            )
            db_session.add(sale_item)
        db_session.flush()

        return sale

    return make