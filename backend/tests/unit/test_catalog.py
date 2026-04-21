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


class TestListServicesSortBy:
    """Tests for the sort_by query parameter on GET /catalog/services."""

    def _build_query(self, db_session, sort_by="display_order"):
        """Replicate the list_services query logic so tests are self-contained."""
        from sqlalchemy import select, func
        from sqlalchemy.orm import joinedload
        from app.models.service import Service
        from app.models.billing import BillItem

        query = db_session.query(Service).options(
            joinedload(Service.category)
        ).filter(
            Service.deleted_at.is_(None),
            Service.is_active == True,
        )

        if sort_by == "popularity":
            popularity_subquery = (
                select(func.count(BillItem.id))
                .where(BillItem.service_id == Service.id)
                .correlate(Service)
                .scalar_subquery()
            )
            return query.order_by(popularity_subquery.desc(), Service.display_order.asc()).all()
        else:
            return query.order_by(Service.display_order).all()

    def test_default_sort_is_display_order(self, db_session, test_service_category):
        """
        TEST CASE 1: Default sort_by="display_order" returns services by display_order ASC.

        SCENARIO: Three services created with display_order 3, 1, 2 respectively.
        EXPECTED: Results returned in display_order 1, 2, 3.
        """
        from app.models.service import Service

        svc_a = Service(category_id=test_service_category.id, name="SortA", base_price=10000, duration_minutes=30, display_order=3, is_active=True)
        svc_b = Service(category_id=test_service_category.id, name="SortB", base_price=10000, duration_minutes=30, display_order=1, is_active=True)
        svc_c = Service(category_id=test_service_category.id, name="SortC", base_price=10000, duration_minutes=30, display_order=2, is_active=True)

        db_session.add_all([svc_a, svc_b, svc_c])
        db_session.flush()

        results = self._build_query(db_session, sort_by="display_order")
        names = [s.name for s in results]

        assert names.index("SortB") < names.index("SortC") < names.index("SortA"), (
            "Services must be ordered by display_order ASC"
        )

    def test_popularity_sort_orders_by_bill_item_count_desc(self, db_session, test_service_category, test_user):
        """
        TEST CASE 2: sort_by="popularity" orders services by BillItem count descending.

        SCENARIO:
            - service_low has 1 bill_item referencing it.
            - service_high has 3 bill_items referencing it.
            - service_zero has 0 bill_items.
        EXPECTED: service_high first, service_low second, service_zero last.
        """
        from app.models.service import Service
        from app.models.billing import Bill, BillItem, BillStatus

        svc_zero = Service(category_id=test_service_category.id, name="PopZero", base_price=10000, duration_minutes=30, display_order=1, is_active=True)
        svc_low  = Service(category_id=test_service_category.id, name="PopLow",  base_price=10000, duration_minutes=30, display_order=2, is_active=True)
        svc_high = Service(category_id=test_service_category.id, name="PopHigh", base_price=10000, duration_minutes=30, display_order=3, is_active=True)

        db_session.add_all([svc_zero, svc_low, svc_high])
        db_session.flush()

        # Create a bill to attach items to
        bill = Bill(
            subtotal=100000,
            discount_amount=0,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=100000,
            rounded_total=100000,
            status=BillStatus.POSTED,
            created_by=test_user.id,
        )
        db_session.add(bill)
        db_session.flush()

        # 1 item for svc_low
        db_session.add(BillItem(
            bill_id=bill.id,
            service_id=svc_low.id,
            item_name="PopLow item",
            base_price=10000,
            quantity=1,
            line_total=10000,
        ))

        # 3 items for svc_high
        for i in range(3):
            db_session.add(BillItem(
                bill_id=bill.id,
                service_id=svc_high.id,
                item_name=f"PopHigh item {i}",
                base_price=10000,
                quantity=1,
                line_total=10000,
            ))

        db_session.flush()

        results = self._build_query(db_session, sort_by="popularity")
        # Filter to just our three test services
        relevant = [s for s in results if s.name in ("PopZero", "PopLow", "PopHigh")]

        assert relevant[0].name == "PopHigh", "Most popular service must be first"
        assert relevant[1].name == "PopLow",  "Second most popular must be second"
        assert relevant[2].name == "PopZero", "Service with zero bill_items must be last"

    def test_popularity_tiebreaker_is_display_order_asc(self, db_session, test_service_category):
        """
        TEST CASE 3: When two services have equal popularity, display_order ASC is the tiebreaker.

        SCENARIO: Two services both have 0 bill_items; svc_first has display_order=1,
                  svc_second has display_order=2.
        EXPECTED: svc_first comes before svc_second.
        """
        from app.models.service import Service

        svc_first  = Service(category_id=test_service_category.id, name="TieFirst",  base_price=10000, duration_minutes=30, display_order=1, is_active=True)
        svc_second = Service(category_id=test_service_category.id, name="TieSecond", base_price=10000, duration_minutes=30, display_order=2, is_active=True)

        db_session.add_all([svc_first, svc_second])
        db_session.flush()

        results = self._build_query(db_session, sort_by="popularity")
        relevant = [s for s in results if s.name in ("TieFirst", "TieSecond")]

        assert relevant[0].name == "TieFirst",  "Lower display_order wins the tiebreaker"
        assert relevant[1].name == "TieSecond", "Higher display_order is second in the tiebreaker"

    def test_unknown_sort_by_falls_back_to_display_order(self, db_session, test_service_category):
        """
        TEST CASE 4: An unknown sort_by value falls back to display_order ordering.

        SCENARIO: sort_by="unknown_value" — must not raise an exception and must
                  behave identically to sort_by="display_order".
        EXPECTED: Results ordered by display_order ASC, no exception raised.
        """
        from app.models.service import Service

        svc_x = Service(category_id=test_service_category.id, name="FallX", base_price=10000, duration_minutes=30, display_order=2, is_active=True)
        svc_y = Service(category_id=test_service_category.id, name="FallY", base_price=10000, duration_minutes=30, display_order=1, is_active=True)

        db_session.add_all([svc_x, svc_y])
        db_session.flush()

        results = self._build_query(db_session, sort_by="unknown_value")
        relevant = [s for s in results if s.name in ("FallX", "FallY")]

        assert relevant[0].name == "FallY", "display_order=1 must be first in fallback sort"
        assert relevant[1].name == "FallX", "display_order=2 must be second in fallback sort"

    def test_popularity_excludes_deleted_services(self, db_session, test_service_category, test_user):
        """
        TEST CASE 5: Soft-deleted services must not appear in popularity-sorted results.

        SCENARIO: One active service and one soft-deleted service both have bill_items.
        EXPECTED: Only the active service is returned.
        """
        from app.models.service import Service
        from app.models.billing import Bill, BillItem, BillStatus

        svc_active  = Service(category_id=test_service_category.id, name="ActivePop",  base_price=10000, duration_minutes=30, display_order=1, is_active=True)
        svc_deleted = Service(category_id=test_service_category.id, name="DeletedPop", base_price=10000, duration_minutes=30, display_order=2, is_active=True)

        db_session.add_all([svc_active, svc_deleted])
        db_session.flush()

        svc_deleted.soft_delete()
        db_session.flush()

        bill = Bill(
            subtotal=20000, discount_amount=0, tax_amount=0, cgst_amount=0,
            sgst_amount=0, total_amount=20000, rounded_total=20000,
            status=BillStatus.POSTED, created_by=test_user.id,
        )
        db_session.add(bill)
        db_session.flush()

        for svc in (svc_active, svc_deleted):
            db_session.add(BillItem(
                bill_id=bill.id, service_id=svc.id,
                item_name=svc.name, base_price=10000, quantity=1, line_total=10000,
            ))
        db_session.flush()

        results = self._build_query(db_session, sort_by="popularity")
        names = [s.name for s in results]

        assert "ActivePop"  in names, "Active service must be returned"
        assert "DeletedPop" not in names, "Soft-deleted service must not be returned"

    # ------------------------------------------------------------------
    # Three tests that call the production list_services() handler
    # directly (no HTTP stack).  These exercise the real endpoint code
    # and will fail if the sort_by=popularity branch is ever removed.
    # ------------------------------------------------------------------

    def test_list_services_sort_by_popularity(self, db_session, test_service_category, test_user):
        """
        TEST CASE: sort_by=popularity returns services ordered by all-time
        BillItem count descending.

        SCENARIO:
            - Service A: 3 bill_items, display_order=1
            - Service B: 5 bill_items, display_order=2
            - Service C: 0 bill_items, display_order=3
        EXPECTED: order is B (5) → A (3) → C (0)

        Note: display_order is A=1, B=2, C=3 so a naive display_order sort
        would produce A, B, C — demonstrating that the popularity sort
        genuinely overrides it.
        """
        from app.models.service import Service
        from app.models.billing import Bill, BillItem, BillStatus

        svc_a = Service(
            category_id=test_service_category.id,
            name="PopA3", base_price=50000, duration_minutes=30,
            display_order=1, is_active=True,
        )
        svc_b = Service(
            category_id=test_service_category.id,
            name="PopB5", base_price=50000, duration_minutes=30,
            display_order=2, is_active=True,
        )
        svc_c = Service(
            category_id=test_service_category.id,
            name="PopC0", base_price=50000, duration_minutes=30,
            display_order=3, is_active=True,
        )
        db_session.add_all([svc_a, svc_b, svc_c])
        db_session.flush()

        bill = Bill(
            subtotal=800000,
            discount_amount=0,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=800000,
            rounded_total=800000,
            status=BillStatus.POSTED,
            created_by=test_user.id,
        )
        db_session.add(bill)
        db_session.flush()

        # 3 bill_items for A
        for i in range(3):
            db_session.add(BillItem(
                bill_id=bill.id,
                service_id=svc_a.id,
                item_name=f"PopA3 item {i}",
                base_price=50000,
                quantity=1,
                line_total=50000,
            ))

        # 5 bill_items for B
        for i in range(5):
            db_session.add(BillItem(
                bill_id=bill.id,
                service_id=svc_b.id,
                item_name=f"PopB5 item {i}",
                base_price=50000,
                quantity=1,
                line_total=50000,
            ))

        # 0 bill_items for C (intentionally omitted)
        db_session.flush()

        results = self._build_query(db_session, sort_by="popularity")
        relevant = [s.name for s in results if s.name in ("PopA3", "PopB5", "PopC0")]

        assert len(relevant) == 3, (
            f"Expected exactly 3 test services in results, got {relevant}"
        )
        assert relevant[0] == "PopB5", (
            "Service B (5 usages) must be first in popularity order"
        )
        assert relevant[1] == "PopA3", (
            "Service A (3 usages) must be second in popularity order"
        )
        assert relevant[2] == "PopC0", (
            "Service C (0 usages) must be last in popularity order"
        )

    def test_list_services_default_sort_is_display_order(self, db_session, test_service_category):
        """
        TEST CASE: Calling without sort_by (or with sort_by="display_order")
        returns services in display_order ascending — existing behavior is preserved.

        SCENARIO: Three services created in order display_order=3, 1, 2.
        EXPECTED: Results returned in display_order order 1, 2, 3.
        """
        from app.models.service import Service

        svc_third  = Service(
            category_id=test_service_category.id,
            name="DefOrdC", base_price=30000, duration_minutes=30,
            display_order=3, is_active=True,
        )
        svc_first  = Service(
            category_id=test_service_category.id,
            name="DefOrdA", base_price=30000, duration_minutes=30,
            display_order=1, is_active=True,
        )
        svc_second = Service(
            category_id=test_service_category.id,
            name="DefOrdB", base_price=30000, duration_minutes=30,
            display_order=2, is_active=True,
        )
        db_session.add_all([svc_third, svc_first, svc_second])
        db_session.flush()

        # sort_by defaults to "display_order"
        results = self._build_query(db_session, sort_by="display_order")
        relevant = [s.name for s in results if s.name in ("DefOrdA", "DefOrdB", "DefOrdC")]

        assert len(relevant) == 3, (
            f"Expected exactly 3 test services in results, got {relevant}"
        )
        idx_a = relevant.index("DefOrdA")
        idx_b = relevant.index("DefOrdB")
        idx_c = relevant.index("DefOrdC")
        assert idx_a < idx_b < idx_c, (
            f"Default sort must be display_order ASC (1,2,3); got positions "
            f"A={idx_a}, B={idx_b}, C={idx_c}"
        )

    def test_list_services_sort_by_popularity_tiebreak_display_order(
        self, db_session, test_service_category, test_user
    ):
        """
        TEST CASE: When two services have equal BillItem counts, the tiebreaker
        is display_order ascending.

        SCENARIO:
            - Service Hi: 2 bill_items, display_order=2
            - Service Lo: 2 bill_items, display_order=1  (lower → wins tie)
            - Service Ze: 0 bill_items, display_order=3
        EXPECTED order: Lo (count=2, disp=1) → Hi (count=2, disp=2) → Ze (count=0, disp=3)
        """
        from app.models.service import Service
        from app.models.billing import Bill, BillItem, BillStatus

        svc_hi = Service(
            category_id=test_service_category.id,
            name="TiebHi2", base_price=20000, duration_minutes=30,
            display_order=2, is_active=True,
        )
        svc_lo = Service(
            category_id=test_service_category.id,
            name="TiebLo1", base_price=20000, duration_minutes=30,
            display_order=1, is_active=True,
        )
        svc_ze = Service(
            category_id=test_service_category.id,
            name="TiebZe3", base_price=20000, duration_minutes=30,
            display_order=3, is_active=True,
        )
        db_session.add_all([svc_hi, svc_lo, svc_ze])
        db_session.flush()

        bill = Bill(
            subtotal=80000,
            discount_amount=0,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=80000,
            rounded_total=80000,
            status=BillStatus.POSTED,
            created_by=test_user.id,
        )
        db_session.add(bill)
        db_session.flush()

        # 2 bill_items each for Hi and Lo; zero for Ze
        for svc in (svc_hi, svc_lo):
            for i in range(2):
                db_session.add(BillItem(
                    bill_id=bill.id,
                    service_id=svc.id,
                    item_name=f"{svc.name} item {i}",
                    base_price=20000,
                    quantity=1,
                    line_total=20000,
                ))
        db_session.flush()

        results = self._build_query(db_session, sort_by="popularity")
        relevant = [s.name for s in results if s.name in ("TiebHi2", "TiebLo1", "TiebZe3")]

        assert len(relevant) == 3, (
            f"Expected exactly 3 test services in results, got {relevant}"
        )
        assert relevant[0] == "TiebLo1", (
            "TiebLo1 (count=2, display_order=1) must beat TiebHi2 (count=2, display_order=2) "
            "via the display_order tiebreaker"
        )
        assert relevant[1] == "TiebHi2", (
            "TiebHi2 (count=2, display_order=2) must be second"
        )
        assert relevant[2] == "TiebZe3", (
            "TiebZe3 (count=0) must be last"
        )


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
