"""
Unit tests for Appointments and Walk-ins API functionality.

This tests appointment and walk-in management operations:
- Create appointments with conflict detection
- List appointments with filters (date, staff, status, customer)
- Get, update, cancel appointments
- Workflow: check-in → start → complete
- Update service notes
- Walk-in registration and workflows
- Customer creation/linking

To run:
    uv run pytest tests/unit/test_appointments.py -v -s
"""

import pytest
from datetime import datetime, timedelta, timezone, date, time
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, WalkIn, AppointmentStatus
from app.models.customer import Customer
from app.models.service import Service
from app.models.user import User, Staff
from app.utils import IST


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_staff(db_session, test_role):
    """Create a test staff member."""
    from app.models.user import User, Staff

    # Create a user for the staff member
    user = User(
        role_id=test_role.id,
        username="test_staff",
        email="staff@example.com",
        password_hash="fake_hash",
        full_name="Test Staff Member",
        is_active=True
    )

    db_session.add(user)
    db_session.flush()

    # Create staff profile linked to user
    staff = Staff(
        user_id=user.id,
        display_name="Test Staff",
        specialization=["haircut"],
        is_active=True
    )

    db_session.add(staff)
    db_session.flush()

    return staff


@pytest.fixture
def test_appointment(db_session, test_customer, test_service, test_user, test_staff):
    """Create a test appointment."""
    now = datetime.now(IST)
    scheduled_time = now + timedelta(hours=2)

    appointment = Appointment(
        ticket_number="TKT-260118-001",
        visit_id="test_visit_id",
        customer_id=test_customer.id,
        customer_name=test_customer.full_name,
        customer_phone=test_customer.phone,
        service_id=test_service.id,
        assigned_staff_id=test_staff.id,
        scheduled_at=scheduled_time,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        booking_notes="Test booking",
        created_by=test_user.id
    )

    db_session.add(appointment)
    db_session.flush()

    return appointment


# =============================================================================
# APPOINTMENT MODEL TESTS
# =============================================================================

class TestAppointmentModel:
    """Tests for Appointment model operations."""

    def test_create_appointment(self, db_session, test_customer, test_service, test_user, test_staff):
        """
        TEST CASE 1: Create an appointment

        SCENARIO: Receptionist creates a scheduled appointment
        EXPECTED:
            - Appointment created with all fields
            - ULID generated for ID
            - Status defaults to SCHEDULED
            - Timestamps set correctly
        """
        now = datetime.now(IST)
        scheduled_time = now + timedelta(hours=3)

        appointment = Appointment(
            ticket_number="TKT-260118-002",
            customer_id=test_customer.id,
            customer_name=test_customer.full_name,
            customer_phone=test_customer.phone,
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=scheduled_time,
            duration_minutes=45,
            booking_notes="Customer requested specific stylist",
            created_by=test_user.id
        )

        db_session.add(appointment)
        db_session.flush()

        assert appointment.id is not None, "Appointment should have an ID"
        assert len(appointment.id) == 26, "ID should be a 26-char ULID"
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.ticket_number == "TKT-260118-002"
        assert appointment.checked_in_at is None
        assert appointment.started_at is None
        assert appointment.completed_at is None
        assert appointment.created_at is not None

        print(f"✅ Created appointment: {appointment.ticket_number} for {appointment.customer_name}")

    def test_appointment_is_active(self, db_session, test_appointment):
        """
        TEST CASE 2: Check appointment is_active property

        SCENARIO: Verify active/cancelled status
        EXPECTED:
            - is_active returns True for non-cancelled appointments
            - is_active returns False after cancellation
        """
        assert test_appointment.is_active is True, "New appointment should be active"
        assert test_appointment.cancelled_at is None

        # Cancel appointment
        test_appointment.cancelled_at = datetime.now(IST)
        db_session.flush()

        assert test_appointment.is_active is False, "Cancelled appointment should not be active"

        print("✅ is_active property works correctly")

    def test_appointment_workflow_states(self, db_session, test_appointment):
        """
        TEST CASE 3: Appointment workflow state transitions

        SCENARIO: Move appointment through workflow states
        EXPECTED: SCHEDULED → CHECKED_IN → IN_PROGRESS → COMPLETED
        """
        now = datetime.now(IST)

        # Initial state
        assert test_appointment.status == AppointmentStatus.SCHEDULED

        # Check in
        test_appointment.status = AppointmentStatus.CHECKED_IN
        test_appointment.checked_in_at = now
        db_session.flush()

        assert test_appointment.status == AppointmentStatus.CHECKED_IN
        assert test_appointment.checked_in_at is not None

        # Start service
        test_appointment.status = AppointmentStatus.IN_PROGRESS
        test_appointment.started_at = now + timedelta(minutes=5)
        db_session.flush()

        assert test_appointment.status == AppointmentStatus.IN_PROGRESS
        assert test_appointment.started_at is not None

        # Complete
        test_appointment.status = AppointmentStatus.COMPLETED
        test_appointment.completed_at = now + timedelta(minutes=35)
        db_session.flush()

        assert test_appointment.status == AppointmentStatus.COMPLETED
        assert test_appointment.completed_at is not None

        print("✅ Appointment workflow transitions completed successfully")

    def test_appointment_service_notes(self, db_session, test_appointment):
        """
        TEST CASE 4: Update service notes

        SCENARIO: Staff adds notes during/after service
        EXPECTED:
            - Service notes can be updated
            - Timestamp recorded when notes updated
        """
        assert test_appointment.service_notes is None
        assert test_appointment.service_notes_updated_at is None

        now = datetime.now(IST)
        test_appointment.service_notes = "Customer requested layered cut. Very satisfied with result."
        test_appointment.service_notes_updated_at = now
        db_session.flush()

        assert test_appointment.service_notes is not None
        assert len(test_appointment.service_notes) > 0
        assert test_appointment.service_notes_updated_at == now

        print(f"✅ Service notes updated: {test_appointment.service_notes[:50]}...")


# =============================================================================
# APPOINTMENT QUERIES & FILTERS
# =============================================================================

class TestAppointmentQueries:
    """Tests for appointment query and filter patterns."""

    def test_filter_by_date(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 1: Filter appointments by date

        SCENARIO: List appointments for a specific day
        EXPECTED: Only appointments on that date returned
        """
        now = datetime.now(IST)
        today = now.date()
        tomorrow = today + timedelta(days=1)

        # Create appointments for today and tomorrow
        appt_today = Appointment(
            ticket_number="TKT-260118-010",
            customer_name="Today Customer",
            customer_phone="9876543210",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=datetime.combine(today, time(10, 0)),
            duration_minutes=30,
            created_by=test_user.id
        )

        appt_tomorrow = Appointment(
            ticket_number="TKT-260119-001",
            customer_name="Tomorrow Customer",
            customer_phone="9876543211",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=datetime.combine(tomorrow, time(10, 0)),
            duration_minutes=30,
            created_by=test_user.id
        )

        db_session.add_all([appt_today, appt_tomorrow])
        db_session.flush()

        # Filter by today's date
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        todays_appointments = db_session.query(Appointment).filter(
            Appointment.scheduled_at >= start_of_day,
            Appointment.scheduled_at <= end_of_day
        ).all()

        assert len(todays_appointments) == 1
        assert todays_appointments[0].customer_name == "Today Customer"

        print(f"✅ Filtered {len(todays_appointments)} appointments for today")

    def test_filter_by_staff(self, db_session, test_service, test_user, test_staff, test_role):
        """
        TEST CASE 2: Filter appointments by staff member

        SCENARIO: View all appointments for a specific staff
        EXPECTED: Only appointments assigned to that staff returned
        """
        # Create another staff member
        from app.models.user import User, Staff

        user2 = User(
            role_id=test_role.id,
            username="staff2",
            email="staff2@example.com",
            password_hash="fake_hash",
            full_name="Staff Two",
            is_active=True
        )
        db_session.add(user2)
        db_session.flush()

        staff2 = Staff(
            user_id=user2.id,
            display_name="Staff Two",
            specialization=["coloring"],
            is_active=True
        )
        db_session.add(staff2)
        db_session.flush()

        now = datetime.now(IST)

        # Create appointments for different staff
        appt1 = Appointment(
            ticket_number="TKT-260118-020",
            customer_name="Customer 1",
            customer_phone="9876543220",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=now + timedelta(hours=1),
            duration_minutes=30,
            created_by=test_user.id
        )

        appt2 = Appointment(
            ticket_number="TKT-260118-021",
            customer_name="Customer 2",
            customer_phone="9876543221",
            service_id=test_service.id,
            assigned_staff_id=staff2.id,
            scheduled_at=now + timedelta(hours=2),
            duration_minutes=30,
            created_by=test_user.id
        )

        db_session.add_all([appt1, appt2])
        db_session.flush()

        # Filter by first staff
        staff1_appointments = db_session.query(Appointment).filter(
            Appointment.assigned_staff_id == test_staff.id
        ).all()

        assert len(staff1_appointments) >= 1
        for appt in staff1_appointments:
            assert appt.assigned_staff_id == test_staff.id

        print(f"✅ Found {len(staff1_appointments)} appointments for staff")

    def test_filter_by_status(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 3: Filter appointments by status

        SCENARIO: List only completed appointments
        EXPECTED: Appointments filtered by status correctly
        """
        now = datetime.now(IST)

        # Create appointments with different statuses
        appt_scheduled = Appointment(
            ticket_number="TKT-260118-030",
            customer_name="Scheduled Customer",
            customer_phone="9876543230",
            service_id=test_service.id,
            scheduled_at=now + timedelta(hours=1),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_by=test_user.id
        )

        appt_completed = Appointment(
            ticket_number="TKT-260118-031",
            customer_name="Completed Customer",
            customer_phone="9876543231",
            service_id=test_service.id,
            scheduled_at=now - timedelta(hours=1),
            duration_minutes=30,
            status=AppointmentStatus.COMPLETED,
            completed_at=now,
            created_by=test_user.id
        )

        db_session.add_all([appt_scheduled, appt_completed])
        db_session.flush()

        # Filter by completed status
        completed = db_session.query(Appointment).filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).all()

        assert len(completed) >= 1
        for appt in completed:
            assert appt.status == AppointmentStatus.COMPLETED

        print(f"✅ Found {len(completed)} completed appointments")

    def test_filter_by_customer(self, db_session, test_customer, test_service, test_user, test_staff):
        """
        TEST CASE 4: Filter appointments by customer

        SCENARIO: View all appointments for a specific customer
        EXPECTED: Customer's appointment history returned
        """
        now = datetime.now(IST)

        # Create multiple appointments for same customer
        appt1 = Appointment(
            ticket_number="TKT-260118-040",
            customer_id=test_customer.id,
            customer_name=test_customer.full_name,
            customer_phone=test_customer.phone,
            service_id=test_service.id,
            scheduled_at=now + timedelta(days=1),
            duration_minutes=30,
            created_by=test_user.id
        )

        appt2 = Appointment(
            ticket_number="TKT-260118-041",
            customer_id=test_customer.id,
            customer_name=test_customer.full_name,
            customer_phone=test_customer.phone,
            service_id=test_service.id,
            scheduled_at=now + timedelta(days=7),
            duration_minutes=45,
            created_by=test_user.id
        )

        db_session.add_all([appt1, appt2])
        db_session.flush()

        # Filter by customer
        customer_appointments = db_session.query(Appointment).filter(
            Appointment.customer_id == test_customer.id
        ).all()

        assert len(customer_appointments) >= 2
        for appt in customer_appointments:
            assert appt.customer_id == test_customer.id

        print(f"✅ Found {len(customer_appointments)} appointments for customer")


# =============================================================================
# CONFLICT DETECTION TESTS
# =============================================================================

class TestAppointmentConflicts:
    """Tests for scheduling conflict detection."""

    def test_detect_overlapping_appointments(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 1: Detect overlapping appointments for same staff

        SCENARIO: Try to schedule two overlapping appointments for same staff
        EXPECTED: Conflict detected
        """
        now = datetime.now(IST)
        base_time = now + timedelta(hours=2)

        # Create first appointment: 2pm - 2:30pm
        appt1 = Appointment(
            ticket_number="TKT-260118-050",
            customer_name="Customer 1",
            customer_phone="9876543250",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=base_time,
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_by=test_user.id
        )

        db_session.add(appt1)
        db_session.flush()

        # Try to create overlapping appointment: 2:15pm - 2:45pm
        conflict_time = base_time + timedelta(minutes=15)
        end_time = conflict_time + timedelta(minutes=30)

        # Check for conflicts
        conflicts = db_session.query(Appointment).filter(
            Appointment.assigned_staff_id == test_staff.id,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]),
            Appointment.scheduled_at < end_time
        ).all()

        # Should find the existing appointment as a conflict
        assert len(conflicts) > 0, "Should detect scheduling conflict"

        print(f"✅ Conflict detected: {len(conflicts)} overlapping appointments")

    def test_no_conflict_different_staff(self, db_session, test_service, test_user, test_staff, test_role):
        """
        TEST CASE 2: Allow simultaneous appointments for different staff

        SCENARIO: Schedule appointments at same time for different staff
        EXPECTED: No conflict
        """
        # Create second staff member
        from app.models.user import User, Staff

        user2 = User(
            role_id=test_role.id,
            username="staff2_conflict",
            email="staff2conflict@example.com",
            password_hash="fake_hash",
            full_name="Staff Two Conflict",
            is_active=True
        )
        db_session.add(user2)
        db_session.flush()

        staff2 = Staff(
            user_id=user2.id,
            display_name="Staff Two Conflict",
            specialization=["spa"],
            is_active=True
        )
        db_session.add(staff2)
        db_session.flush()

        now = datetime.now(IST)
        same_time = now + timedelta(hours=3)

        # Create appointments at same time for different staff
        appt1 = Appointment(
            ticket_number="TKT-260118-060",
            customer_name="Customer 1",
            customer_phone="9876543260",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=same_time,
            duration_minutes=30,
            created_by=test_user.id
        )

        appt2 = Appointment(
            ticket_number="TKT-260118-061",
            customer_name="Customer 2",
            customer_phone="9876543261",
            service_id=test_service.id,
            assigned_staff_id=staff2.id,
            scheduled_at=same_time,
            duration_minutes=30,
            created_by=test_user.id
        )

        db_session.add_all([appt1, appt2])
        db_session.flush()

        # Both should be created successfully
        assert appt1.id is not None
        assert appt2.id is not None

        print("✅ No conflict: Different staff can have simultaneous appointments")

    def test_no_conflict_cancelled_appointment(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 3: Cancelled appointments don't cause conflicts

        SCENARIO: Schedule new appointment at time of cancelled one
        EXPECTED: No conflict
        """
        now = datetime.now(IST)
        appt_time = now + timedelta(hours=4)

        # Create and cancel first appointment
        appt1 = Appointment(
            ticket_number="TKT-260118-070",
            customer_name="Cancelled Customer",
            customer_phone="9876543270",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=appt_time,
            duration_minutes=30,
            status=AppointmentStatus.CANCELLED,
            cancelled_at=now,
            created_by=test_user.id
        )

        db_session.add(appt1)
        db_session.flush()

        # Create new appointment at same time
        appt2 = Appointment(
            ticket_number="TKT-260118-071",
            customer_name="New Customer",
            customer_phone="9876543271",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=appt_time,
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_by=test_user.id
        )

        db_session.add(appt2)
        db_session.flush()

        # Check for conflicts (excluding cancelled)
        conflicts = db_session.query(Appointment).filter(
            Appointment.assigned_staff_id == test_staff.id,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS
            ]),
            Appointment.scheduled_at == appt_time
        ).all()

        # Should only find the new appointment, not the cancelled one
        assert len(conflicts) == 1
        assert conflicts[0].status == AppointmentStatus.SCHEDULED

        print("✅ No conflict: Cancelled appointments don't block new ones")


# =============================================================================
# WALK-IN TESTS
# =============================================================================

class TestWalkInModel:
    """Tests for WalkIn model operations."""

    def test_create_walkin(self, db_session, test_service, test_user):
        """
        TEST CASE 1: Create a walk-in

        SCENARIO: Walk-in customer arrives without appointment
        EXPECTED:
            - Walk-in created successfully
            - Status defaults to CHECKED_IN
            - No scheduled_at field
        """
        walkin = WalkIn(
            ticket_number="TKT-260118-080",
            customer_name="Walk-in Customer",
            customer_phone="9876543280",
            service_id=test_service.id,
            duration_minutes=30,
            status=AppointmentStatus.CHECKED_IN,
            created_by=test_user.id
        )

        db_session.add(walkin)
        db_session.flush()

        assert walkin.id is not None
        assert len(walkin.id) == 26
        assert walkin.status == AppointmentStatus.CHECKED_IN
        assert walkin.ticket_number == "TKT-260118-080"

        print(f"✅ Created walk-in: {walkin.ticket_number} for {walkin.customer_name}")

    def test_walkin_workflow(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 2: Walk-in workflow

        SCENARIO: Walk-in goes through service workflow
        EXPECTED: CHECKED_IN → IN_PROGRESS → COMPLETED
        """
        now = datetime.now(IST)

        walkin = WalkIn(
            ticket_number="TKT-260118-081",
            customer_name="Workflow Walk-in",
            customer_phone="9876543281",
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            duration_minutes=45,
            status=AppointmentStatus.CHECKED_IN,
            created_by=test_user.id
        )

        db_session.add(walkin)
        db_session.flush()

        # Start service
        walkin.status = AppointmentStatus.IN_PROGRESS
        walkin.started_at = now
        db_session.flush()

        assert walkin.status == AppointmentStatus.IN_PROGRESS
        assert walkin.started_at is not None

        # Complete service
        walkin.status = AppointmentStatus.COMPLETED
        walkin.completed_at = now + timedelta(minutes=45)
        db_session.flush()

        assert walkin.status == AppointmentStatus.COMPLETED
        assert walkin.completed_at is not None

        print("✅ Walk-in workflow completed successfully")

    def test_walkin_with_customer_link(self, db_session, test_customer, test_service, test_user):
        """
        TEST CASE 3: Link walk-in to existing customer

        SCENARIO: Returning customer walks in
        EXPECTED: Walk-in linked to customer record
        """
        walkin = WalkIn(
            ticket_number="TKT-260118-082",
            customer_id=test_customer.id,
            customer_name=test_customer.full_name,
            customer_phone=test_customer.phone,
            service_id=test_service.id,
            duration_minutes=30,
            status=AppointmentStatus.CHECKED_IN,
            created_by=test_user.id
        )

        db_session.add(walkin)
        db_session.flush()

        assert walkin.customer_id == test_customer.id
        assert walkin.customer_name == test_customer.full_name

        print(f"✅ Walk-in linked to customer: {test_customer.full_name}")


# =============================================================================
# CUSTOMER AUTO-CREATION TESTS
# =============================================================================

class TestCustomerAutoCreation:
    """Tests for automatic customer creation during appointment booking."""

    def test_create_appointment_new_customer(self, db_session, test_service, test_user, test_staff):
        """
        TEST CASE 1: Create appointment for new customer

        SCENARIO: Receptionist books appointment for first-time customer
        EXPECTED:
            - New customer record created automatically
            - Appointment linked to customer
        """
        initial_customer_count = db_session.query(Customer).count()

        # In real API, this would trigger customer creation
        # For this test, we'll simulate it
        new_customer = Customer(
            first_name="New",
            last_name="Customer",
            phone="9999999999"
        )
        db_session.add(new_customer)
        db_session.flush()

        now = datetime.now(IST)
        appointment = Appointment(
            ticket_number="TKT-260118-090",
            customer_id=new_customer.id,
            customer_name=new_customer.full_name,
            customer_phone=new_customer.phone,
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=now + timedelta(days=1),
            duration_minutes=30,
            created_by=test_user.id
        )

        db_session.add(appointment)
        db_session.flush()

        final_customer_count = db_session.query(Customer).count()

        assert final_customer_count == initial_customer_count + 1
        assert appointment.customer_id == new_customer.id

        print("✅ New customer created and linked to appointment")

    def test_link_appointment_existing_customer_by_phone(self, db_session, test_customer, test_service, test_user, test_staff):
        """
        TEST CASE 2: Link appointment to existing customer by phone

        SCENARIO: Customer books another appointment (recognized by phone)
        EXPECTED:
            - No duplicate customer created
            - Appointment linked to existing customer
        """
        initial_customer_count = db_session.query(Customer).count()

        now = datetime.now(IST)
        appointment = Appointment(
            ticket_number="TKT-260118-091",
            customer_id=test_customer.id,
            customer_name=test_customer.full_name,
            customer_phone=test_customer.phone,
            service_id=test_service.id,
            assigned_staff_id=test_staff.id,
            scheduled_at=now + timedelta(days=2),
            duration_minutes=30,
            created_by=test_user.id
        )

        db_session.add(appointment)
        db_session.flush()

        final_customer_count = db_session.query(Customer).count()

        assert final_customer_count == initial_customer_count
        assert appointment.customer_id == test_customer.id

        print("✅ Appointment linked to existing customer (no duplicate)")
