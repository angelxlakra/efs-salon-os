"""
Unit tests for Customer API functionality.

This tests the customer management operations:
- List customers with pagination and search
- Create customer with phone uniqueness
- Get customer by ID
- Update customer
- Soft delete customer
- Search customer by phone

To run:
    uv run pytest tests/unit/test_customers.py -v -s
"""

import pytest
from sqlalchemy.orm import Session

from app.models.customer import Customer


class TestCustomerModel:
    """Tests for Customer model operations."""

    def test_create_customer(self, db_session: Session):
        """
        TEST CASE 1: Create a customer

        SCENARIO: Receptionist registers a new customer
        EXPECTED:
            - Customer created with all fields
            - ULID generated for ID
            - Default values set correctly
        """
        customer = Customer(
            first_name="John",
            last_name="Doe",
            phone="+919876543210",
            email="john.doe@example.com",
            gender="male",
            notes="Regular customer"
        )

        db_session.add(customer)
        db_session.flush()

        assert customer.id is not None, "Customer should have an ID"
        assert len(customer.id) == 26, "ID should be a 26-char ULID"
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.phone == "+919876543210"
        assert customer.total_visits == 0
        assert customer.total_spent == 0
        assert customer.created_at is not None
        assert customer.updated_at is not None

        print(f"✅ Created customer: {customer.full_name} (ID: {customer.id})")

    def test_customer_full_name(self, db_session: Session):
        """
        TEST CASE 2: Customer full name property

        SCENARIO: Display customer's full name
        EXPECTED:
            - full_name returns first + last name
            - Only first name if no last name
        """
        customer_with_last = Customer(
            first_name="Jane",
            last_name="Smith",
            phone="+919876543211"
        )

        customer_without_last = Customer(
            first_name="Alex",
            phone="+919876543212"
        )

        db_session.add_all([customer_with_last, customer_without_last])
        db_session.flush()

        assert customer_with_last.full_name == "Jane Smith"
        assert customer_without_last.full_name == "Alex"

        print("✅ Full name property works correctly")

    def test_customer_phone_unique(self, db_session: Session, test_customer):
        """
        TEST CASE 3: Customer phone should be unique

        SCENARIO: Attempt to create customer with duplicate phone
        EXPECTED: Database constraint violation
        """
        duplicate = Customer(
            first_name="Duplicate",
            phone=test_customer.phone  # Same phone
        )

        db_session.add(duplicate)

        with pytest.raises(Exception):
            db_session.flush()

        db_session.rollback()
        print("✅ Duplicate phone correctly rejected")

    def test_customer_soft_delete(self, db_session: Session, test_customer):
        """
        TEST CASE 4: Soft delete a customer

        SCENARIO: Delete a customer
        EXPECTED:
            - Customer marked as deleted (deleted_at set)
            - is_deleted property returns True
            - Customer can be restored
        """
        assert test_customer.deleted_at is None, "Customer should not be deleted initially"
        assert test_customer.is_deleted is False

        # Soft delete
        test_customer.soft_delete()
        db_session.flush()

        assert test_customer.deleted_at is not None, "deleted_at should be set"
        assert test_customer.is_deleted is True

        print(f"✅ Customer soft deleted at: {test_customer.deleted_at}")

        # Restore
        test_customer.restore()
        db_session.flush()

        assert test_customer.deleted_at is None, "deleted_at should be None after restore"
        assert test_customer.is_deleted is False

        print("✅ Customer restored successfully")

    def test_customer_spent_rupees(self, db_session: Session):
        """
        TEST CASE 5: Verify total_spent_rupees calculation

        SCENARIO: Store money in paise, display in rupees
        EXPECTED: Correct conversion without floating point errors
        """
        test_amounts = [
            (150050, 1500.50),  # Rs 1500.50
            (100, 1.00),       # Rs 1.00
            (999999, 9999.99), # Rs 9999.99
            (1, 0.01),         # Rs 0.01 (1 paisa)
        ]

        for paise, expected_rupees in test_amounts:
            customer = Customer(
                first_name=f"Customer {paise}",
                phone=f"+91987654{paise:04d}"[-14:],
                total_spent=paise
            )
            db_session.add(customer)
            db_session.flush()

            assert customer.total_spent == paise
            assert customer.total_spent_rupees == expected_rupees

            print(f"✅ {paise} paise = ₹{customer.total_spent_rupees}")


class TestCustomerQueries:
    """Tests for customer query patterns."""

    def test_query_active_customers(self, db_session: Session):
        """
        TEST CASE 1: Query only active (non-deleted) customers

        SCENARIO: List customers, excluding deleted ones
        EXPECTED: Only active customers returned
        """
        # Create multiple customers
        active_customer = Customer(
            first_name="Active",
            phone="+919876540001"
        )

        deleted_customer = Customer(
            first_name="Deleted",
            phone="+919876540002"
        )

        db_session.add_all([active_customer, deleted_customer])
        db_session.flush()

        # Soft delete one
        deleted_customer.soft_delete()
        db_session.flush()

        # Query active customers
        active_customers = db_session.query(Customer).filter(
            Customer.deleted_at.is_(None)
        ).all()

        customer_names = [c.first_name for c in active_customers]

        assert "Active" in customer_names
        assert "Deleted" not in customer_names

        print(f"✅ Found {len(active_customers)} active customers")

    def test_search_customer_by_phone(self, db_session: Session):
        """
        TEST CASE 2: Search customer by phone number

        SCENARIO: Look up customer by phone
        EXPECTED: Customer found with exact phone match
        """
        customer = Customer(
            first_name="Searchable",
            phone="+919876599999"
        )

        db_session.add(customer)
        db_session.flush()

        # Search by phone
        found = db_session.query(Customer).filter(
            Customer.phone == "+919876599999",
            Customer.deleted_at.is_(None)
        ).first()

        assert found is not None
        assert found.first_name == "Searchable"

        print(f"✅ Found customer by phone: {found.full_name}")

    def test_search_customer_by_name(self, db_session: Session):
        """
        TEST CASE 3: Search customers by name (partial match)

        SCENARIO: Search for customers whose name contains a query
        EXPECTED: Matching customers returned
        """
        customers = [
            Customer(first_name="Rajesh", last_name="Kumar", phone="+919876540010"),
            Customer(first_name="Raj", phone="+919876540011"),
            Customer(first_name="Rajan", last_name="Sharma", phone="+919876540012"),
            Customer(first_name="Sunil", phone="+919876540013"),
        ]

        for c in customers:
            db_session.add(c)
        db_session.flush()

        # Search for names containing "raj" (case-insensitive)
        results = db_session.query(Customer).filter(
            Customer.first_name.ilike("%raj%"),
            Customer.deleted_at.is_(None)
        ).all()

        assert len(results) == 3  # Rajesh, Raj, Rajan
        result_names = [r.first_name for r in results]
        assert "Sunil" not in result_names

        print(f"✅ Found {len(results)} customers matching 'raj'")

    def test_customers_ordered_by_created(self, db_session: Session):
        """
        TEST CASE 4: Customers ordered by created_at

        SCENARIO: List customers in order of registration
        EXPECTED: Most recent first (DESC order)
        """
        from datetime import datetime, timedelta, timezone

        # Create customers with explicit timestamps to ensure ordering
        now = datetime.now(timezone.utc)

        c1 = Customer(first_name="First", phone="+919876540020")
        c1.created_at = now - timedelta(hours=2)
        db_session.add(c1)

        c2 = Customer(first_name="Second", phone="+919876540021")
        c2.created_at = now - timedelta(hours=1)
        db_session.add(c2)

        c3 = Customer(first_name="Third", phone="+919876540022")
        c3.created_at = now
        db_session.add(c3)

        db_session.flush()

        # Query with DESC order
        ordered = db_session.query(Customer).filter(
            Customer.first_name.in_(["First", "Second", "Third"])
        ).order_by(Customer.created_at.desc()).all()

        # Most recent should be first
        assert ordered[0].first_name == "Third"
        assert ordered[1].first_name == "Second"
        assert ordered[2].first_name == "First"

        print("✅ Customers ordered by created_at DESC correctly")


class TestCustomerAnalytics:
    """Tests for customer analytics fields."""

    def test_update_visit_count(self, db_session: Session, test_customer):
        """
        TEST CASE 1: Update customer visit count

        SCENARIO: Customer completes a visit
        EXPECTED: total_visits incremented
        """
        initial_visits = test_customer.total_visits

        test_customer.total_visits += 1
        db_session.flush()

        assert test_customer.total_visits == initial_visits + 1

        print(f"✅ Visit count updated: {test_customer.total_visits}")

    def test_update_total_spent(self, db_session: Session, test_customer):
        """
        TEST CASE 2: Update customer spending

        SCENARIO: Customer pays a bill
        EXPECTED: total_spent updated correctly
        """
        initial_spent = test_customer.total_spent

        # Add Rs 500 (50000 paise)
        test_customer.total_spent += 50000
        db_session.flush()

        assert test_customer.total_spent == initial_spent + 50000
        assert test_customer.total_spent_rupees == (initial_spent + 50000) / 100.0

        print(f"✅ Total spent updated: ₹{test_customer.total_spent_rupees}")

    def test_update_last_visit(self, db_session: Session, test_customer):
        """
        TEST CASE 3: Update last visit timestamp

        SCENARIO: Customer completes a visit
        EXPECTED: last_visit_at updated to current time
        """
        from datetime import datetime, timezone

        assert test_customer.last_visit_at is None

        now = datetime.now(timezone.utc)
        test_customer.last_visit_at = now
        db_session.flush()

        assert test_customer.last_visit_at is not None
        assert test_customer.last_visit_at == now

        print(f"✅ Last visit updated: {test_customer.last_visit_at}")
