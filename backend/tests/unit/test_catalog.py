"""
Unit tests for Catalog (Services) functionality.

This tests the service catalog operations:
- Category CRUD operations
- Service CRUD operations
- Service addon operations
- Soft delete behavior

To run:
    uv run pytest tests/unit/test_catalog.py -v -s
"""

import pytest
from sqlalchemy.orm import Session

from app.models.service import ServiceCategory, Service, ServiceAddon


class TestServiceCategory:
    """Tests for ServiceCategory model operations."""

    def test_create_category(self, db_session: Session):
        """
        TEST CASE 1: Create a service category

        SCENARIO: Owner creates a new category for services
        EXPECTED:
            - Category created with all fields
            - is_active defaults to True
            - display_order set correctly
        """
        category = ServiceCategory(
            name="Hair Coloring",
            description="All hair color services",
            display_order=2,
            is_active=True
        )

        db_session.add(category)
        db_session.flush()

        assert category.id is not None, "Category should have an ID"
        assert len(category.id) == 26, "ID should be a 26-char ULID"
        assert category.name == "Hair Coloring"
        assert category.description == "All hair color services"
        assert category.display_order == 2
        assert category.is_active is True
        assert category.created_at is not None
        assert category.updated_at is not None

        print(f"✅ Created category: {category.name} (ID: {category.id})")

    def test_category_unique_name(self, db_session: Session, test_service_category):
        """
        TEST CASE 2: Category names should be unique

        SCENARIO: Attempt to create category with duplicate name
        EXPECTED: Database constraint violation
        """
        duplicate = ServiceCategory(
            name=test_service_category.name,  # Same name
            description="Duplicate category",
            display_order=99
        )

        db_session.add(duplicate)

        with pytest.raises(Exception):
            db_session.flush()

        db_session.rollback()
        print("✅ Duplicate category name correctly rejected")

    def test_category_ordering(self, db_session: Session):
        """
        TEST CASE 3: Categories should be orderable by display_order

        SCENARIO: Multiple categories with different display orders
        EXPECTED: Sorted correctly when queried
        """
        categories = [
            ServiceCategory(name="Makeup", display_order=3),
            ServiceCategory(name="Haircut", display_order=1),
            ServiceCategory(name="Spa", display_order=2),
        ]

        for cat in categories:
            db_session.add(cat)
        db_session.flush()

        # Query with ordering
        ordered = db_session.query(ServiceCategory).filter(
            ServiceCategory.name.in_(["Makeup", "Haircut", "Spa"])
        ).order_by(ServiceCategory.display_order).all()

        assert ordered[0].name == "Haircut", "Haircut should be first (order 1)"
        assert ordered[1].name == "Spa", "Spa should be second (order 2)"
        assert ordered[2].name == "Makeup", "Makeup should be third (order 3)"

        print("✅ Categories ordered correctly by display_order")


class TestService:
    """Tests for Service model operations."""

    def test_create_service(self, db_session: Session, test_service_category):
        """
        TEST CASE 1: Create a service

        SCENARIO: Owner creates a new service in a category
        EXPECTED:
            - Service created with all fields
            - Price stored in paise
            - Linked to category
        """
        service = Service(
            category_id=test_service_category.id,
            name="Women's Haircut",
            description="Stylish women's haircut",
            base_price=60000,  # Rs 600
            duration_minutes=45,
            display_order=2,
            is_active=True
        )

        db_session.add(service)
        db_session.flush()

        assert service.id is not None
        assert len(service.id) == 26
        assert service.name == "Women's Haircut"
        assert service.base_price == 60000
        assert service.base_price_rupees == 600.0
        assert service.duration_minutes == 45
        assert service.category_id == test_service_category.id
        assert service.is_active is True
        assert service.deleted_at is None

        print(f"✅ Created service: {service.name} @ ₹{service.base_price_rupees}")

    def test_service_soft_delete(self, db_session: Session, test_service):
        """
        TEST CASE 2: Soft delete a service

        SCENARIO: Owner deletes a service
        EXPECTED:
            - Service marked as deleted (deleted_at set)
            - is_deleted property returns True
            - Service can be restored
        """
        assert test_service.deleted_at is None, "Service should not be deleted initially"
        assert test_service.is_deleted is False

        # Soft delete
        test_service.soft_delete()
        db_session.flush()

        assert test_service.deleted_at is not None, "deleted_at should be set"
        assert test_service.is_deleted is True

        print(f"✅ Service soft deleted at: {test_service.deleted_at}")

        # Restore
        test_service.restore()
        db_session.flush()

        assert test_service.deleted_at is None, "deleted_at should be None after restore"
        assert test_service.is_deleted is False

        print("✅ Service restored successfully")

    def test_service_category_relationship(self, db_session: Session, test_service, test_service_category):
        """
        TEST CASE 3: Service-Category relationship

        SCENARIO: Service belongs to a category
        EXPECTED:
            - Service.category returns the category
            - Category.services includes the service
        """
        # Refresh to ensure relationships are loaded
        db_session.refresh(test_service)
        db_session.refresh(test_service_category)

        assert test_service.category is not None
        assert test_service.category.id == test_service_category.id
        assert test_service.category.name == test_service_category.name

        assert test_service in test_service_category.services

        print(f"✅ Service '{test_service.name}' belongs to category '{test_service.category.name}'")

    def test_query_active_services(self, db_session: Session, test_service_category):
        """
        TEST CASE 4: Query only active, non-deleted services

        SCENARIO: Filter out inactive and deleted services
        EXPECTED: Only active, non-deleted services returned
        """
        # Create multiple services
        active_service = Service(
            category_id=test_service_category.id,
            name="Active Service",
            base_price=30000,
            duration_minutes=30,
            is_active=True
        )

        inactive_service = Service(
            category_id=test_service_category.id,
            name="Inactive Service",
            base_price=30000,
            duration_minutes=30,
            is_active=False
        )

        deleted_service = Service(
            category_id=test_service_category.id,
            name="Deleted Service",
            base_price=30000,
            duration_minutes=30,
            is_active=True
        )

        db_session.add_all([active_service, inactive_service, deleted_service])
        db_session.flush()

        # Soft delete one
        deleted_service.soft_delete()
        db_session.flush()

        # Query active services
        active_services = db_session.query(Service).filter(
            Service.category_id == test_service_category.id,
            Service.is_active == True,
            Service.deleted_at.is_(None)
        ).all()

        service_names = [s.name for s in active_services]

        assert "Active Service" in service_names
        assert "Inactive Service" not in service_names
        assert "Deleted Service" not in service_names

        print(f"✅ Found {len(active_services)} active services")


class TestServiceAddon:
    """Tests for ServiceAddon model operations."""

    def test_create_addon(self, db_session: Session, test_service):
        """
        TEST CASE 1: Create a service addon

        SCENARIO: Owner adds an addon to a service
        EXPECTED:
            - Addon created and linked to service
            - Price stored in paise
        """
        addon = ServiceAddon(
            service_id=test_service.id,
            name="Head Massage",
            price=15000  # Rs 150
        )

        db_session.add(addon)
        db_session.flush()

        assert addon.id is not None
        assert addon.name == "Head Massage"
        assert addon.price == 15000
        assert addon.price_rupees == 150.0
        assert addon.service_id == test_service.id

        print(f"✅ Created addon: {addon.name} @ ₹{addon.price_rupees}")

    def test_service_addons_relationship(self, db_session: Session, test_service):
        """
        TEST CASE 2: Service has multiple addons

        SCENARIO: Service with multiple addon options
        EXPECTED:
            - service.addons returns all addons
            - Addons are correctly linked
        """
        addons = [
            ServiceAddon(service_id=test_service.id, name="Beard Trim", price=10000),
            ServiceAddon(service_id=test_service.id, name="Hair Wash", price=5000),
            ServiceAddon(service_id=test_service.id, name="Styling", price=20000),
        ]

        for addon in addons:
            db_session.add(addon)
        db_session.flush()

        # Refresh to load relationships
        db_session.refresh(test_service)

        assert len(test_service.addons) == 3
        addon_names = [a.name for a in test_service.addons]
        assert "Beard Trim" in addon_names
        assert "Hair Wash" in addon_names
        assert "Styling" in addon_names

        print(f"✅ Service has {len(test_service.addons)} addons")

    def test_delete_addon(self, db_session: Session, test_service):
        """
        TEST CASE 3: Delete an addon (hard delete)

        SCENARIO: Owner removes an addon
        EXPECTED:
            - Addon is permanently deleted
            - Service.addons no longer contains it
        """
        addon = ServiceAddon(
            service_id=test_service.id,
            name="Temporary Addon",
            price=5000
        )

        db_session.add(addon)
        db_session.flush()
        addon_id = addon.id

        # Hard delete
        db_session.delete(addon)
        db_session.flush()

        # Verify deletion
        deleted = db_session.query(ServiceAddon).filter(
            ServiceAddon.id == addon_id
        ).first()

        assert deleted is None, "Addon should be permanently deleted"

        print("✅ Addon deleted successfully")


class TestCatalogIntegration:
    """Integration tests for full catalog functionality."""

    def test_full_catalog_structure(self, db_session: Session):
        """
        TEST CASE: Full catalog with categories, services, and addons

        SCENARIO: Build a realistic catalog structure
        EXPECTED:
            - Multiple categories with services
            - Services with addons
            - Proper ordering
        """
        # Create categories
        haircut_cat = ServiceCategory(name="Haircut", display_order=1)
        color_cat = ServiceCategory(name="Hair Color", display_order=2)
        spa_cat = ServiceCategory(name="Spa", display_order=3)

        db_session.add_all([haircut_cat, color_cat, spa_cat])
        db_session.flush()

        # Create services
        services = [
            Service(category_id=haircut_cat.id, name="Men's Cut", base_price=40000, duration_minutes=30, display_order=1),
            Service(category_id=haircut_cat.id, name="Women's Cut", base_price=60000, duration_minutes=45, display_order=2),
            Service(category_id=color_cat.id, name="Root Touch-up", base_price=150000, duration_minutes=90, display_order=1),
            Service(category_id=color_cat.id, name="Full Color", base_price=250000, duration_minutes=120, display_order=2),
            Service(category_id=spa_cat.id, name="Deep Conditioning", base_price=80000, duration_minutes=60, display_order=1),
        ]

        for s in services:
            db_session.add(s)
        db_session.flush()

        # Add addons to haircut services
        mens_cut = services[0]
        addons = [
            ServiceAddon(service_id=mens_cut.id, name="Beard Trim", price=10000),
            ServiceAddon(service_id=mens_cut.id, name="Head Massage", price=15000),
        ]

        for a in addons:
            db_session.add(a)
        db_session.flush()

        # Verify full structure
        categories = db_session.query(ServiceCategory).filter(
            ServiceCategory.name.in_(["Haircut", "Hair Color", "Spa"])
        ).order_by(ServiceCategory.display_order).all()

        assert len(categories) == 3

        # Verify Haircut category
        haircut = categories[0]
        assert haircut.name == "Haircut"
        assert len([s for s in haircut.services if s.is_active]) == 2

        # Verify Men's Cut has addons
        mens_cut_from_db = db_session.query(Service).filter(
            Service.name == "Men's Cut"
        ).first()
        assert len(mens_cut_from_db.addons) == 2

        print("✅ Full catalog structure created:")
        for cat in categories:
            print(f"   📁 {cat.name}")
            for svc in sorted(cat.services, key=lambda s: s.display_order):
                addon_count = len(svc.addons)
                addon_str = f" ({addon_count} addons)" if addon_count > 0 else ""
                print(f"      └─ {svc.name} @ ₹{svc.base_price_rupees}{addon_str}")

    def test_service_pricing_precision(self, db_session: Session, test_service_category):
        """
        TEST CASE: Verify price storage and retrieval precision

        SCENARIO: Store and retrieve prices in paise
        EXPECTED:
            - No floating point errors
            - Correct conversion to rupees
        """
        test_prices = [
            (34950, 349.50),   # Rs 349.50
            (100, 1.00),      # Rs 1.00
            (999999, 9999.99), # Rs 9999.99
            (1, 0.01),        # Rs 0.01 (1 paisa)
        ]

        for paise, expected_rupees in test_prices:
            service = Service(
                category_id=test_service_category.id,
                name=f"Price Test {paise}",
                base_price=paise,
                duration_minutes=30
            )
            db_session.add(service)
            db_session.flush()

            assert service.base_price == paise
            assert service.base_price_rupees == expected_rupees

            print(f"✅ {paise} paise = ₹{service.base_price_rupees}")
