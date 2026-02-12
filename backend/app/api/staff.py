from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User, Staff
from app.models.appointment import Appointment, WalkIn, AppointmentStatus
from app.schemas.user import (
    StaffCreate, StaffUpdate, StaffResponse,
    StaffWithUserResponse, StaffListResponse
)
from app.auth.dependencies import (
    get_current_user, require_owner, require_owner_or_receptionist
)
from app.services.staff_availability_service import StaffAvailabilityService

router = APIRouter(prefix="/staff", tags=["Staff"])


# ========== Helper Functions ==========

def _validate_user_for_staff_creation(db: Session, user_id: str) -> User:
    """Validate user exists, is active, and has no existing staff profile."""
    # Check user exists and not deleted
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or has been deleted"
        )

    # Check user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create staff profile for inactive user"
        )

    # Check no existing staff profile
    existing_staff = db.query(Staff).filter(Staff.user_id == user_id).first()
    if existing_staff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a staff profile"
        )

    return user


def _check_active_appointments(db: Session, staff_id: str) -> int:
    """Count active appointments + walk-ins for staff."""
    active_statuses = [
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.IN_PROGRESS
    ]

    # Count appointments
    appointment_count = db.query(func.count(Appointment.id)).filter(
        Appointment.assigned_staff_id == staff_id,
        Appointment.status.in_(active_statuses)
    ).scalar()

    # Count walk-ins
    walkin_count = db.query(func.count(WalkIn.id)).filter(
        WalkIn.assigned_staff_id == staff_id,
        WalkIn.status.in_(active_statuses)
    ).scalar()

    return appointment_count + walkin_count


# ========== Endpoints ==========

@router.get("", response_model=StaffListResponse)
def list_staff(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    service_providers_only: bool = Query(False, description="Only show staff marked as service providers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    List all staff profiles with pagination and filtering.

    - **page**: Page number (starts at 1)
    - **size**: Items per page (max 100)
    - **search**: Search by display name (case-insensitive)
    - **is_active**: Filter by active status
    - **service_providers_only**: If true, only show staff marked as service providers
    """
    # Query Staff and join with User (filter deleted users)
    query = db.query(Staff).join(User).filter(User.deleted_at.is_(None))

    # Filter to service providers only
    if service_providers_only:
        query = query.filter(Staff.is_service_provider == True)

    # Apply search filter on display_name
    if search:
        query = query.filter(Staff.display_name.ilike(f"%{search}%"))

    # Apply is_active filter
    if is_active is not None:
        query = query.filter(Staff.is_active == is_active)

    # Order by creation date (newest first)
    query = query.order_by(Staff.created_at.desc())

    # Eager load user relationship for response
    query = query.options(joinedload(Staff.user).joinedload(User.role))

    # Get total count
    total = query.count()

    # Paginate
    items = query.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }


@router.post("", response_model=StaffWithUserResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    staff_data: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """
    Create a new staff profile.

    Validates that:
    - User exists and is not deleted
    - User is active
    - User doesn't already have a staff profile
    """
    # Validate user
    user = _validate_user_for_staff_creation(db, staff_data.user_id)

    # Create staff profile
    new_staff = Staff(**staff_data.model_dump())
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    # Load relationships for response
    db.refresh(new_staff)

    return new_staff


@router.get("/{staff_id}", response_model=StaffWithUserResponse)
def get_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Get a single staff profile by ID.
    """
    staff = db.query(Staff).options(
        joinedload(Staff.user).joinedload(User.role)
    ).join(User).filter(
        Staff.id == staff_id,
        User.deleted_at.is_(None)
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found"
        )

    return staff


@router.patch("/{staff_id}", response_model=StaffWithUserResponse)
def update_staff(
    staff_id: str,
    staff_update: StaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """
    Update a staff profile.

    Only display_name, specialization, is_active, and is_service_provider can be updated.
    """
    # Find staff (exclude deleted users)
    staff = db.query(Staff).join(User).filter(
        Staff.id == staff_id,
        User.deleted_at.is_(None)
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found"
        )

    # Update only provided fields
    update_data = staff_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(staff, field, value)

    db.commit()
    db.refresh(staff)

    # Load relationships for response
    staff = db.query(Staff).options(
        joinedload(Staff.user).joinedload(User.role)
    ).filter(Staff.id == staff_id).first()

    return staff


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """
    Delete a staff profile (HARD DELETE).

    ⚠️ WARNING: This is a hard delete. Staff model does not support soft delete.

    Recommended approach: Set is_active=false instead of deleting.

    Safety check: Prevents deletion if staff has active appointments.
    """
    # Find staff
    staff = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found"
        )

    # Check for active appointments
    active_count = _check_active_appointments(db, staff_id)
    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete staff with {active_count} active appointment(s). "
                   "Consider setting is_active=false instead."
        )

    # Perform hard delete
    db.delete(staff)
    db.commit()

    return None


@router.get("/availability/busyness")
def get_staff_busyness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Get busyness information for all active staff members.

    Returns staff availability metrics including:
    - Number of active (in-progress) services
    - Number of queued (checked-in) services
    - Estimated wait time in minutes
    - Overall status (available/busy/very_busy)

    Useful for helping receptionists assign services to the least busy staff.
    """
    service = StaffAvailabilityService(db)
    return service.get_staff_busyness()



    

    
