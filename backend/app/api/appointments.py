"""Appointments and Walk-ins API endpoints.

This module provides REST API endpoints for:
- Creating and managing appointments
- Registering walk-in customers
- Check-in, start, and complete workflows
- Updating service notes
- Filtering appointments by date, staff, status
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db
from app.models.appointment import Appointment, WalkIn, AppointmentStatus
from app.models.customer import Customer
from app.models.billing import Bill, BillStatus
from app.models.service import Service
from app.models.user import User, Staff
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentWithDetails,
    WalkInCreate,
    WalkInResponse,
    StatusUpdate,
    ServiceNotesUpdate,
    CancelRequest,
    BulkWalkInCreate,
    BulkWalkInResponse,
    ActiveWalkInsResponse,
    CustomerSessionGroup,
    WalkInWithDetails,
    MyServicesResponse,
    ServiceResponseBase,
    StaffResponseBase,
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist
from app.auth.permissions import PermissionChecker
from app.utils import generate_ulid, IST

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ============ Helper Functions ============

def _get_or_create_customer(
    db: Session,
    customer_id: Optional[str],
    customer_name: str,
    customer_phone: Optional[str]
) -> Optional[str]:
    """Get existing customer or create new one if phone doesn't exist.

    Args:
        db: Database session
        customer_id: Optional existing customer ID
        customer_name: Customer name
        customer_phone: Optional customer phone number (None for walk-ins without phone)

    Returns:
        Customer ID if found/created, None otherwise
    """
    if customer_id:
        # Verify customer exists
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None)
        ).first()
        if customer:
            return customer.id

    # Try to find by phone (only if phone is provided)
    if customer_phone:
        customer = db.query(Customer).filter(
            Customer.phone == customer_phone,
            Customer.deleted_at.is_(None)
        ).first()

        if customer:
            return customer.id

    # Create new customer
    # Split name into first/last (simple split on first space)
    name_parts = customer_name.strip().split(maxsplit=1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    new_customer = Customer(
        first_name=first_name,
        last_name=last_name,
        phone=customer_phone  # Can be None for walk-ins
    )
    db.add(new_customer)
    db.flush()
    return new_customer.id


def _can_manage_service(
    current_user: User,
    assigned_staff_id: Optional[str],
    db: Session
) -> bool:
    """Check if current user can manage (start/complete) a service.

    Args:
        current_user: The authenticated user
        assigned_staff_id: The staff ID assigned to the service
        db: Database session

    Returns:
        bool: True if user can manage the service

    Rules:
        - Owner/Receptionist: Can manage any service
        - Staff: Can only manage services assigned to them
    """
    # Owner and Receptionist can manage any service
    if current_user.role.name in ["owner", "receptionist"]:
        return True

    # Staff can only manage their own services
    if current_user.role.name == "staff":
        # Find staff profile for current user
        staff = db.query(Staff).filter(Staff.user_id == current_user.id).first()
        if not staff:
            return False

        # Check if service is assigned to this staff member
        return assigned_staff_id == staff.id

    return False


def _check_scheduling_conflict(
    db: Session,
    staff_id: Optional[str],
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_appointment_id: Optional[str] = None
) -> bool:
    """Check if staff member has conflicting appointments.

    Args:
        db: Database session
        staff_id: Staff member ID to check
        scheduled_at: Proposed appointment start time
        duration_minutes: Duration in minutes
        exclude_appointment_id: Exclude this appointment from conflict check (for updates)

    Returns:
        True if conflict exists, False otherwise
    """
    if not staff_id:
        return False  # No conflict if no staff assigned

    end_time = scheduled_at + timedelta(minutes=duration_minutes)

    # Check for overlapping appointments
    conflict_query = db.query(Appointment).filter(
        Appointment.assigned_staff_id == staff_id,
        Appointment.status.in_([
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_PROGRESS
        ]),
        Appointment.scheduled_at < end_time,
        # Check if appointment end time overlaps with new start time
        (Appointment.scheduled_at + timedelta(minutes=Appointment.duration_minutes)) > scheduled_at
    )

    if exclude_appointment_id:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)

    return conflict_query.first() is not None


def _generate_ticket_numbers(db: Session, count: int = 1) -> List[str]:
    """Generate unique sequential ticket numbers.
    
    Queries the database to find the latest ticket number for today from both
    appointments and walk-ins tables to ensure global uniqueness and sequentiality.
    
    Args:
        db: Database session
        count: Number of tickets to generate
        
    Returns:
        List[str]: List of unique ticket numbers
    """
    now = datetime.now(IST)
    date_str = now.strftime("%y%m%d")
    prefix = f"TKT-{date_str}-"
    
    # Query max ticket number from both tables
    # Tickets are formatted as TKT-YYMMDD-XXX
    max_appt = db.query(func.max(Appointment.ticket_number))\
        .filter(Appointment.ticket_number.like(f"{prefix}%")).scalar()
        
    max_walkin = db.query(func.max(WalkIn.ticket_number))\
        .filter(WalkIn.ticket_number.like(f"{prefix}%")).scalar()
    
    current_max = 0
    
    for val in [max_appt, max_walkin]:
        if val:
            try:
                # Extract the number part (XXX) from end of string
                num_part = int(val.split('-')[-1])
                current_max = max(current_max, num_part)
            except (ValueError, IndexError):
                continue
    
    tickets = []
    for i in range(count):
        # Generate next numbers: current_max + 1, current_max + 2, etc.
        tickets.append(f"{prefix}{current_max + i + 1:03d}")
        
    return tickets


# ============ Appointment Endpoints ============

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Create a new appointment.

    Creates a scheduled appointment with automatic ticket number generation.
    Can optionally link to existing customer or create new customer record.

    **Permissions**: Receptionist or Owner

    **Conflict Detection**: Checks for staff scheduling conflicts and returns 409 if conflict exists.

    **Customer Handling**:
    - If customer_id provided and valid: Links to existing customer
    - If phone matches existing customer: Links automatically
    - Otherwise: Creates new customer record

    Args:
        appointment_data: Appointment creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Created appointment

    Raises:
        400: Invalid service_id or assigned_staff_id
        409: Scheduling conflict for staff member
    """
    # Validate service exists
    service = db.query(Service).filter(Service.id == appointment_data.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service not found: {appointment_data.service_id}"
        )

    # Check for scheduling conflicts
    if _check_scheduling_conflict(
        db,
        appointment_data.assigned_staff_id,
        appointment_data.scheduled_at,
        appointment_data.duration_minutes
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Staff member has conflicting appointment at this time"
        )

    # Get or create customer
    customer_id = _get_or_create_customer(
        db,
        appointment_data.customer_id,
        appointment_data.customer_name,
        appointment_data.customer_phone
    )

    # Create appointment
    appointment = Appointment(
        ticket_number=_generate_ticket_numbers(db, 1)[0],
        visit_id=appointment_data.visit_id or generate_ulid(),
        customer_id=customer_id,
        customer_name=appointment_data.customer_name,
        customer_phone=appointment_data.customer_phone,
        service_id=appointment_data.service_id,
        assigned_staff_id=appointment_data.assigned_staff_id,
        scheduled_at=appointment_data.scheduled_at,
        duration_minutes=appointment_data.duration_minutes,
        booking_notes=appointment_data.booking_notes,
        status=AppointmentStatus.SCHEDULED,
        created_by=current_user.id
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return appointment


@router.get("", response_model=List[AppointmentResponse])
def list_appointments(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    staff_id: Optional[str] = Query(None, description="Filter by assigned staff"),
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status", description="Filter by status"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List appointments with optional filters.

    Supports filtering by date, staff, status, and customer.
    Returns appointments ordered by scheduled_at descending.

    **Permissions**: All authenticated users

    Args:
        date: Filter by date (YYYY-MM-DD format)
        staff_id: Filter by assigned staff member
        status_filter: Filter by appointment status
        customer_id: Filter by customer ID
        skip: Number of records to skip (pagination)
        limit: Maximum records to return (max 500)
        db: Database session
        current_user: Authenticated user

    Returns:
        List[AppointmentResponse]: List of appointments
    """
    query = db.query(Appointment)

    # Apply filters
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            # Create timezone-aware datetimes for comparison
            start_of_day = IST.localize(datetime.combine(filter_date, time.min))
            end_of_day = IST.localize(datetime.combine(filter_date, time.max))
            query = query.filter(
                Appointment.scheduled_at >= start_of_day,
                Appointment.scheduled_at <= end_of_day
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    if staff_id:
        query = query.filter(Appointment.assigned_staff_id == staff_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    if customer_id:
        query = query.filter(Appointment.customer_id == customer_id)

    # Order by scheduled time (most recent first)
    query = query.order_by(Appointment.scheduled_at.desc())

    # Pagination
    appointments = query.offset(skip).limit(limit).all()

    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific appointment by ID.

    **Permissions**: All authenticated users

    Args:
        appointment_id: Appointment ID
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Appointment details

    Raises:
        404: Appointment not found
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Update an existing appointment.

    Allows updating service, staff assignment, scheduled time, duration, notes, and status.
    Checks for scheduling conflicts when updating time or staff.

    **Permissions**: Receptionist or Owner

    Args:
        appointment_id: Appointment ID
        update_data: Fields to update
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Updated appointment

    Raises:
        404: Appointment not found
        409: Scheduling conflict after update
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)

    # Check for scheduling conflicts if time/staff/duration changed
    new_staff = update_dict.get("assigned_staff_id", appointment.assigned_staff_id)
    new_time = update_dict.get("scheduled_at", appointment.scheduled_at)
    new_duration = update_dict.get("duration_minutes", appointment.duration_minutes)

    if any(k in update_dict for k in ["assigned_staff_id", "scheduled_at", "duration_minutes"]):
        if _check_scheduling_conflict(
            db, new_staff, new_time, new_duration,
            exclude_appointment_id=appointment_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Staff member has conflicting appointment at this time"
            )

    # Update service notes timestamp if notes changed
    if "service_notes" in update_dict:
        update_dict["service_notes_updated_at"] = datetime.now(IST)

    # Apply updates
    for field, value in update_dict.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Cancel an appointment.

    Sets status to CANCELLED and records cancellation timestamp.

    **Permissions**: Receptionist or Owner

    Args:
        appointment_id: Appointment ID
        db: Database session
        current_user: Authenticated user

    Raises:
        404: Appointment not found
        400: Appointment already completed or cancelled
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status}"
        )

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now(IST)

    db.commit()


@router.post("/{appointment_id}/check-in", response_model=AppointmentResponse)
def check_in_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Check in an appointment.

    Updates status to CHECKED_IN and records check-in timestamp.

    **Permissions**: Receptionist or Owner

    Args:
        appointment_id: Appointment ID
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Updated appointment

    Raises:
        404: Appointment not found
        400: Invalid status transition
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    if appointment.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in appointment with status: {appointment.status}"
        )

    appointment.status = AppointmentStatus.CHECKED_IN
    appointment.checked_in_at = datetime.now(IST)

    db.commit()
    db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/start", response_model=AppointmentResponse)
def start_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Start service for an appointment.

    Updates status to IN_PROGRESS and records start timestamp.

    **Permissions**:
    - Owner/Receptionist: Can start any appointment
    - Staff: Can only start appointments assigned to them

    Args:
        appointment_id: Appointment ID
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Updated appointment

    Raises:
        404: Appointment not found
        403: Not authorized to manage this appointment
        400: Invalid status transition
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check if user can manage this service
    if not _can_manage_service(current_user, appointment.assigned_staff_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only start services assigned to you"
        )

    if appointment.status not in [AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start appointment with status: {appointment.status}"
        )

    appointment.status = AppointmentStatus.IN_PROGRESS
    appointment.started_at = datetime.now(IST)

    # Auto check-in if not already checked in
    if not appointment.checked_in_at:
        appointment.checked_in_at = appointment.started_at

    db.commit()
    db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark appointment as completed.

    Updates status to COMPLETED and records completion timestamp.

    **Permissions**:
    - Owner/Receptionist: Can complete any appointment
    - Staff: Can only complete appointments assigned to them

    Args:
        appointment_id: Appointment ID
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Updated appointment

    Raises:
        404: Appointment not found
        403: Not authorized to manage this appointment
        400: Invalid status transition
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check if user can manage this service
    if not _can_manage_service(current_user, appointment.assigned_staff_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete services assigned to you"
        )

    if appointment.status != AppointmentStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete appointment with status: {appointment.status}. Must be IN_PROGRESS."
        )

    appointment.status = AppointmentStatus.COMPLETED
    appointment.completed_at = datetime.now(IST)

    db.commit()
    db.refresh(appointment)

    return appointment


@router.patch("/{appointment_id}/notes", response_model=AppointmentResponse)
def update_service_notes(
    appointment_id: str,
    notes_data: ServiceNotesUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update service notes for an appointment.

    Staff can add notes during or after service completion.

    **Permissions**: All authenticated users

    Args:
        appointment_id: Appointment ID
        notes_data: Service notes to add
        db: Database session
        current_user: Authenticated user

    Returns:
        AppointmentResponse: Updated appointment

    Raises:
        404: Appointment not found
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    appointment.service_notes = notes_data.service_notes
    appointment.service_notes_updated_at = datetime.now(IST)

    db.commit()
    db.refresh(appointment)

    return appointment


# ============ Walk-In Endpoints ============

@router.post("/walkins", response_model=WalkInResponse, status_code=status.HTTP_201_CREATED)
def create_walkin(
    walkin_data: WalkInCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Register a walk-in customer.

    Creates a walk-in record with status defaulting to CHECKED_IN.
    Similar to appointments but no scheduling required.

    **Permissions**:
    - Receptionist/Owner: Can assign to any staff
    - Staff: Can only create walk-ins assigned to themselves

    Args:
        walkin_data: Walk-in creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Created walk-in record

    Raises:
        400: Invalid service_id or unauthorized staff assignment
        403: Staff trying to assign to someone else
    """
    # Check permissions
    has_permission = PermissionChecker.has_permission(
        current_user.role.name, "walkins", "create"
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create walk-ins"
        )

    # Validate service exists
    service = db.query(Service).filter(Service.id == walkin_data.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service not found: {walkin_data.service_id}"
        )

    # For staff users, auto-assign to themselves and enforce it
    assigned_staff_id = walkin_data.assigned_staff_id
    if current_user.role.name == "staff":
        # Find staff profile for current user
        staff = db.query(Staff).filter(Staff.user_id == current_user.id).first()
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No staff profile found for current user"
            )

        # Staff can only assign to themselves
        if assigned_staff_id and assigned_staff_id != staff.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff members can only create walk-ins assigned to themselves"
            )

        # Auto-assign to themselves
        assigned_staff_id = staff.id

    # Get or create customer
    customer_id = _get_or_create_customer(
        db,
        walkin_data.customer_id,
        walkin_data.customer_name,
        walkin_data.customer_phone
    )

    # Create walk-in
    walkin = WalkIn(
        ticket_number=_generate_ticket_numbers(db, 1)[0],
        visit_id=walkin_data.visit_id or generate_ulid(),
        customer_id=customer_id,
        customer_name=walkin_data.customer_name,
        customer_phone=walkin_data.customer_phone,
        service_id=walkin_data.service_id,
        assigned_staff_id=assigned_staff_id,
        duration_minutes=walkin_data.duration_minutes,
        status=AppointmentStatus.CHECKED_IN,
        created_by=current_user.id
    )

    db.add(walkin)
    db.commit()
    db.refresh(walkin)

    return walkin


@router.get("/walkins", response_model=List[WalkInResponse])
def list_walkins(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    staff_id: Optional[str] = Query(None, description="Filter by assigned staff"),
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List walk-ins with optional filters.

    **Permissions**: All authenticated users

    Args:
        date: Filter by creation date (YYYY-MM-DD format)
        staff_id: Filter by assigned staff member
        status_filter: Filter by status
        skip: Number of records to skip (pagination)
        limit: Maximum records to return (max 500)
        db: Database session
        current_user: Authenticated user

    Returns:
        List[WalkInResponse]: List of walk-ins
    """
    query = db.query(WalkIn)

    # Apply filters
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            # Create timezone-aware datetimes for comparison
            start_of_day = IST.localize(datetime.combine(filter_date, time.min))
            end_of_day = IST.localize(datetime.combine(filter_date, time.max))
            query = query.filter(
                WalkIn.created_at >= start_of_day,
                WalkIn.created_at <= end_of_day
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    if staff_id:
        query = query.filter(WalkIn.assigned_staff_id == staff_id)

    if status_filter:
        query = query.filter(WalkIn.status == status_filter)

    # Order by creation time (most recent first)
    query = query.order_by(WalkIn.created_at.desc())

    # Pagination
    walkins = query.offset(skip).limit(limit).all()

    return walkins


# ============ Specific Walk-In Endpoints (Must Come Before Parameterized Routes) ============

@router.post("/walkins/bulk", response_model=BulkWalkInResponse, status_code=status.HTTP_201_CREATED)
def create_bulk_walkins_v2(
    data: BulkWalkInCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Create multiple walk-in records at once (from POS cart).

    Creates one walk-in per cart item (respecting quantity).
    All walk-ins start in CHECKED_IN status and share the same session_id.

    **Permissions**: Receptionist or Owner

    **Use Case**: When receptionist adds multiple services to cart with staff
    assignments and clicks "Create Service Orders".

    Args:
        data: Bulk walk-in creation data with session_id and items
        db: Database session
        current_user: Authenticated user

    Returns:
        BulkWalkInResponse: Created walk-ins with session info

    Raises:
        400: Invalid service_id or staff_id
    """
    # Use None if phone not provided (walk-ins may not have phone)
    customer_phone = data.customer_phone or None

    # Get or create customer
    customer_id = _get_or_create_customer(
        db,
        data.customer_id,
        data.customer_name,
        customer_phone
    )

    walkins = []
    checked_in_at = datetime.now(IST)

    # Calculate total quantity of tickets needed
    total_quantity = sum(item.quantity for item in data.items)
    ticket_numbers = _generate_ticket_numbers(db, total_quantity)
    ticket_idx = 0

    # Create walk-ins for each item
    for item in data.items:
        # Validate service exists
        service = db.query(Service).filter(Service.id == item.service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service not found: {item.service_id}"
            )

        # Validate staff exists if assigned
        if item.assigned_staff_id:
            staff = db.query(Staff).filter(Staff.id == item.assigned_staff_id).first()
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Staff not found: {item.assigned_staff_id}"
                )

        # Create walk-in for each quantity
        for _ in range(item.quantity):
            walkin = WalkIn(
                ticket_number=ticket_numbers[ticket_idx],
                session_id=data.session_id,
                customer_id=customer_id,
                customer_name=data.customer_name,
                customer_phone=customer_phone,
                service_id=item.service_id,
                assigned_staff_id=item.assigned_staff_id,
                duration_minutes=service.duration_minutes,
                status=AppointmentStatus.CHECKED_IN,
                checked_in_at=checked_in_at,
                created_by=current_user.id
            )
            db.add(walkin)
            walkins.append(walkin)
            ticket_idx += 1

    db.commit()

    # Refresh all walk-ins to get IDs and timestamps
    for walkin in walkins:
        db.refresh(walkin)

    return BulkWalkInResponse(
        session_id=data.session_id,
        walkins=walkins,
        total_items=len(walkins),
        message=f"Created {len(walkins)} walk-in records successfully"
    )


@router.get("/walkins/active", response_model=ActiveWalkInsResponse)
def get_active_walkins_v2(
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Get all active walk-ins (CHECKED_IN, IN_PROGRESS) grouped by session_id.

    Returns walk-ins that are currently in progress, grouped by customer session.
    Used by the live tracking dashboard to show real-time status.

    **Permissions**: Receptionist or Owner

    **Polling**: Frontend should poll this endpoint every 10 seconds for real-time updates.

    Args:
        db: Database session
        current_user: Authenticated user

    Returns:
        ActiveWalkInsResponse: Active sessions with walk-ins and totals
    """
    # Query active walk-ins (CHECKED_IN, IN_PROGRESS, COMPLETED) that are NOT fully billed (Posted)
    walkins_query = db.query(WalkIn).outerjoin(Bill, WalkIn.bill_id == Bill.id).filter(
        WalkIn.session_id.isnot(None),
        WalkIn.status.in_([
            AppointmentStatus.CHECKED_IN, 
            AppointmentStatus.IN_PROGRESS, 
            AppointmentStatus.COMPLETED
        ]),
        or_(
            WalkIn.bill_id.is_(None),
            Bill.status == BillStatus.DRAFT
        )
    ).order_by(WalkIn.checked_in_at.asc())

    walkins = walkins_query.all()

    # Group by session_id
    sessions_dict = {}
    for walkin in walkins:
        session_id = walkin.session_id
        if session_id not in sessions_dict:
            sessions_dict[session_id] = {
                "session_id": session_id,
                "customer_name": walkin.customer_name,
                "customer_phone": walkin.customer_phone,
                "customer_id": walkin.customer_id,
                "walkins": [],
                "checked_in_at": walkin.checked_in_at
            }

        # Build walk-in with details
        walkin_detail = WalkInWithDetails(
            id=walkin.id,
            ticket_number=walkin.ticket_number,
            customer_name=walkin.customer_name,
            customer_phone=walkin.customer_phone,
            customer_id=walkin.customer_id,
            service=ServiceResponseBase(
                id=walkin.service.id,
                name=walkin.service.name,
                base_price=walkin.service.base_price,
                duration_minutes=walkin.service.duration_minutes
            ),
            assigned_staff=StaffResponseBase(
                id=walkin.assigned_staff.id,
                display_name=walkin.assigned_staff.display_name
            ),
            status=walkin.status,
            checked_in_at=walkin.checked_in_at,
            started_at=walkin.started_at,
            completed_at=walkin.completed_at,
            service_notes=walkin.service_notes,
            duration_minutes=walkin.duration_minutes,
            session_id=walkin.session_id
        )
        sessions_dict[session_id]["walkins"].append(walkin_detail)

    # Build response sessions
    sessions = []
    for session_data in sessions_dict.values():
        # Calculate total amount
        total_amount = sum(w.service.base_price for w in session_data["walkins"])

        # Calculate time since check-in
        time_since_checkin = 0
        if session_data["checked_in_at"]:
            delta = datetime.now(IST) - session_data["checked_in_at"]
            time_since_checkin = int(delta.total_seconds() / 60)

        # Check if all completed
        all_completed = all(w.status == AppointmentStatus.COMPLETED for w in session_data["walkins"])

        session = CustomerSessionGroup(
            session_id=session_data["session_id"],
            customer_name=session_data["customer_name"],
            customer_phone=session_data["customer_phone"],
            customer_id=session_data["customer_id"],
            walkins=session_data["walkins"],
            total_amount=total_amount,
            time_since_checkin=time_since_checkin,
            all_completed=all_completed
        )
        sessions.append(session)

    return ActiveWalkInsResponse(
        sessions=sessions,
        total_customers=len(sessions)
    )


@router.get("/walkins/my-services", response_model=MyServicesResponse)
def get_my_services_v2(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all walk-ins assigned to current user's staff profile.

    Returns services assigned to the logged-in staff member.
    Used by staff dashboard to show their daily service queue.

    **Permissions**: All authenticated users

    **Staff Role**: Only sees their own assigned services
    **Owner/Receptionist**: Can see services for date but filtered by staff if they have a staff profile

    Args:
        date: Filter by date (YYYY-MM-DD), defaults to today
        db: Database session
        current_user: Authenticated user

    Returns:
        MyServicesResponse: List of assigned walk-ins

    Raises:
        404: Staff profile not found for current user
    """
    # Find staff profile for current user
    staff = db.query(Staff).filter(
        Staff.user_id == current_user.id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No staff profile found for current user"
        )

    # Parse date filter (default to today)
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        filter_date = datetime.now(IST).date()

    # Create timezone-aware datetimes for comparison
    start_of_day = IST.localize(datetime.combine(filter_date, time.min))
    end_of_day = IST.localize(datetime.combine(filter_date, time.max))

    # Query walk-ins assigned to this staff
    walkins_query = db.query(WalkIn).filter(
        WalkIn.assigned_staff_id == staff.id,
        WalkIn.created_at >= start_of_day,
        WalkIn.created_at <= end_of_day
    ).order_by(
        # Order by status priority, then by check-in time
        WalkIn.status.desc(),
        WalkIn.checked_in_at.asc()
    )

    walkins = walkins_query.all()

    # Build detailed response
    services = []
    for walkin in walkins:
        walkin_detail = WalkInWithDetails(
            id=walkin.id,
            ticket_number=walkin.ticket_number,
            customer_name=walkin.customer_name,
            customer_phone=walkin.customer_phone,
            customer_id=walkin.customer_id,
            service=ServiceResponseBase(
                id=walkin.service.id,
                name=walkin.service.name,
                base_price=walkin.service.base_price,
                duration_minutes=walkin.service.duration_minutes
            ),
            assigned_staff=StaffResponseBase(
                id=walkin.assigned_staff.id,
                display_name=walkin.assigned_staff.display_name
            ),
            status=walkin.status,
            checked_in_at=walkin.checked_in_at,
            started_at=walkin.started_at,
            completed_at=walkin.completed_at,
            service_notes=walkin.service_notes,
            duration_minutes=walkin.duration_minutes,
            session_id=walkin.session_id
        )
        services.append(walkin_detail)

    return MyServicesResponse(
        services=services,
        date=filter_date.isoformat(),
        total=len(services)
    )


# ============ Parameterized Walk-In Endpoints ============

@router.get("/walkins/{walkin_id}", response_model=WalkInResponse)
def get_walkin(
    walkin_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific walk-in by ID.

    **Permissions**: All authenticated users

    Args:
        walkin_id: Walk-in ID
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Walk-in details

    Raises:
        404: Walk-in not found
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
        )

    return walkin


@router.post("/walkins/{walkin_id}/start", response_model=WalkInResponse)
def start_walkin(
    walkin_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Start service for a walk-in.

    Updates status to IN_PROGRESS and records start timestamp.

    **Permissions**:
    - Owner/Receptionist: Can start any walk-in
    - Staff: Can only start walk-ins assigned to them

    Args:
        walkin_id: Walk-in ID
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Updated walk-in

    Raises:
        404: Walk-in not found
        403: Not authorized to manage this walk-in
        400: Invalid status transition
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
        )

    # Check if user can manage this service
    if not _can_manage_service(current_user, walkin.assigned_staff_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only start services assigned to you"
        )

    if walkin.status != AppointmentStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start walk-in with status: {walkin.status}"
        )

    walkin.status = AppointmentStatus.IN_PROGRESS
    walkin.started_at = datetime.now(IST)

    db.commit()
    db.refresh(walkin)

    return walkin


@router.post("/walkins/{walkin_id}/complete", response_model=WalkInResponse)
def complete_walkin(
    walkin_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark walk-in as completed.

    Updates status to COMPLETED and records completion timestamp.

    **Permissions**:
    - Owner/Receptionist: Can complete any walk-in
    - Staff: Can only complete walk-ins assigned to them

    Args:
        walkin_id: Walk-in ID
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Updated walk-in

    Raises:
        404: Walk-in not found
        403: Not authorized to manage this walk-in
        400: Invalid status transition
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
        )

    # Check if user can manage this service
    if not _can_manage_service(current_user, walkin.assigned_staff_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete services assigned to you"
        )

    if walkin.status != AppointmentStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete walk-in with status: {walkin.status}. Must be IN_PROGRESS."
        )

    walkin.status = AppointmentStatus.COMPLETED
    walkin.completed_at = datetime.now(IST)

    db.commit()
    db.refresh(walkin)

    return walkin


@router.patch("/walkins/{walkin_id}/notes", response_model=WalkInResponse)
def update_walkin_notes(
    walkin_id: str,
    notes_data: ServiceNotesUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update service notes for a walk-in.

    Staff can add notes during or after service completion.

    **Permissions**: All authenticated users

    Args:
        walkin_id: Walk-in ID
        notes_data: Service notes to add
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Updated walk-in

    Raises:
        404: Walk-in not found
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
        )

    walkin.service_notes = notes_data.service_notes
    walkin.service_notes_updated_at = datetime.now(IST)

    db.commit()
    db.refresh(walkin)

    return walkin


@router.post("/walkins/{walkin_id}/cancel", response_model=WalkInResponse)
def cancel_walkin(
    walkin_id: str,
    cancel_data: CancelRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Cancel a walk-in service.

    Used for customer cancellations, no-shows, or mistakes.
    Only walk-ins that haven't been billed can be cancelled.

    **Permissions**: Owner or Receptionist

    Args:
        walkin_id: Walk-in ID to cancel
        cancel_data: Cancellation reason (optional)
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Cancelled walk-in

    Raises:
        404: Walk-in not found
        400: Walk-in already billed or already cancelled
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
        )

    # Can't cancel if already cancelled
    if walkin.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Walk-in is already cancelled"
        )

    # Can't cancel if already billed
    if walkin.bill_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel walk-in that has been billed. Void or refund the bill instead."
        )

    # Update status to cancelled
    walkin.status = AppointmentStatus.CANCELLED
    walkin.cancelled_at = datetime.now(IST)
    walkin.cancellation_reason = cancel_data.reason

    db.commit()
    db.refresh(walkin)

    return walkin
