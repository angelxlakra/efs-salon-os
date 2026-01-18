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
from sqlalchemy import and_, or_

from app.database import get_db
from app.models.appointment import Appointment, WalkIn, AppointmentStatus
from app.models.customer import Customer
from app.models.service import Service
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentWithDetails,
    WalkInCreate,
    WalkInResponse,
    StatusUpdate,
    ServiceNotesUpdate,
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist
from app.auth.permissions import PermissionChecker
from app.utils import generate_ticket_number, generate_ulid, IST

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ============ Helper Functions ============

def _get_or_create_customer(
    db: Session,
    customer_id: Optional[str],
    customer_name: str,
    customer_phone: str
) -> Optional[str]:
    """Get existing customer or create new one if phone doesn't exist.

    Args:
        db: Database session
        customer_id: Optional existing customer ID
        customer_name: Customer name
        customer_phone: Customer phone number

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

    # Try to find by phone
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
        phone=customer_phone
    )
    db.add(new_customer)
    db.flush()
    return new_customer.id


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
        ticket_number=generate_ticket_number(),
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
            start_of_day = datetime.combine(filter_date, time.min)
            end_of_day = datetime.combine(filter_date, time.max)
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

    **Permissions**: All authenticated users (staff can start their own appointments)

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

    **Permissions**: All authenticated users (staff can complete their own appointments)

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
    current_user = Depends(require_owner_or_receptionist)
):
    """Register a walk-in customer.

    Creates a walk-in record with status defaulting to CHECKED_IN.
    Similar to appointments but no scheduling required.

    **Permissions**: Receptionist or Owner

    Args:
        walkin_data: Walk-in creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Created walk-in record

    Raises:
        400: Invalid service_id
    """
    # Validate service exists
    service = db.query(Service).filter(Service.id == walkin_data.service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service not found: {walkin_data.service_id}"
        )

    # Get or create customer
    customer_id = _get_or_create_customer(
        db,
        walkin_data.customer_id,
        walkin_data.customer_name,
        walkin_data.customer_phone
    )

    # Create walk-in
    walkin = WalkIn(
        ticket_number=generate_ticket_number(),
        visit_id=walkin_data.visit_id or generate_ulid(),
        customer_id=customer_id,
        customer_name=walkin_data.customer_name,
        customer_phone=walkin_data.customer_phone,
        service_id=walkin_data.service_id,
        assigned_staff_id=walkin_data.assigned_staff_id,
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
            start_of_day = datetime.combine(filter_date, time.min)
            end_of_day = datetime.combine(filter_date, time.max)
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

    **Permissions**: All authenticated users

    Args:
        walkin_id: Walk-in ID
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Updated walk-in

    Raises:
        404: Walk-in not found
        400: Invalid status transition
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
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

    **Permissions**: All authenticated users

    Args:
        walkin_id: Walk-in ID
        db: Database session
        current_user: Authenticated user

    Returns:
        WalkInResponse: Updated walk-in

    Raises:
        404: Walk-in not found
        400: Invalid status transition
    """
    walkin = db.query(WalkIn).filter(WalkIn.id == walkin_id).first()

    if not walkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walk-in not found"
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
