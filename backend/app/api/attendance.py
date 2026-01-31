"""Attendance management API endpoints."""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_
import calendar

from app.database import get_db
from app.models.user import User, Staff
from app.models.attendance import Attendance, AttendanceStatus
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceResponse,
    AttendanceWithStaffResponse,
    AttendanceListResponse,
    DailyAttendanceSummary,
    MonthlyAttendanceSummary,
    MonthlyAllStaffSummary,
)
from app.auth.dependencies import (
    get_current_user,
    require_owner,
    require_owner_or_receptionist,
)


router = APIRouter()


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    attendance_data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Mark attendance for a staff member.

    - Upserts attendance record (creates or updates if exists for same staff+date)
    - Requires PRESENT/HALF_DAY status to have signed_in_at timestamp
    - Only accessible by Owner or Receptionist
    """
    # Validate staff exists and is active
    staff = db.query(Staff).join(User).filter(
        Staff.id == attendance_data.staff_id,
        Staff.is_active == True,
        User.deleted_at.is_(None)
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active staff member not found"
        )

    # Check if attendance already exists (upsert behavior)
    existing = db.query(Attendance).filter(
        Attendance.staff_id == attendance_data.staff_id,
        Attendance.date == attendance_data.date
    ).first()

    if existing:
        # Update existing record
        for field, value in attendance_data.model_dump(exclude_unset=True).items():
            if field not in ['staff_id', 'date']:  # Don't update keys
                setattr(existing, field, value)
        existing.marked_by_id = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    # Create new record
    new_attendance = Attendance(
        **attendance_data.model_dump(),
        marked_by_id=current_user.id
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    return new_attendance


@router.get("", response_model=AttendanceListResponse)
def list_attendance(
    date_filter: Optional[date] = Query(None, description="Filter by date (default: today)"),
    staff_id: Optional[str] = Query(None, description="Filter by staff ID"),
    status_filter: Optional[AttendanceStatus] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    List attendance records with filters and pagination.

    - Supports filtering by date, staff, and status
    - Returns paginated results with staff details
    - Only accessible by Owner or Receptionist
    """
    # Build query
    query = db.query(Attendance).options(
        joinedload(Attendance.staff).joinedload(Staff.user)
    )

    # Apply filters
    if date_filter:
        query = query.filter(Attendance.date == date_filter)
    else:
        query = query.filter(Attendance.date == date.today())

    if staff_id:
        query = query.filter(Attendance.staff_id == staff_id)

    if status_filter:
        query = query.filter(Attendance.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    records = query.order_by(Attendance.date.desc(), Attendance.created_at.desc()).offset(offset).limit(size).all()

    # Transform to response with staff info
    items = []
    for record in records:
        items.append(AttendanceWithStaffResponse(
            id=record.id,
            staff_id=record.staff_id,
            date=record.date,
            status=record.status,
            signed_in_at=record.signed_in_at,
            signed_out_at=record.signed_out_at,
            notes=record.notes,
            marked_by_id=record.marked_by_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            staff={
                "id": record.staff.id,
                "display_name": record.staff.display_name,
                "full_name": record.staff.user.full_name,
                "is_active": record.staff.is_active
            }
        ))

    pages = (total + size - 1) // size  # Ceiling division

    return AttendanceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/daily-summary", response_model=DailyAttendanceSummary)
def get_daily_summary(
    date_filter: date = Query(default_factory=date.today, description="Date for summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Get daily attendance summary with counts by status.

    - Shows total staff count and breakdown by status
    - Includes all attendance records for the day
    - Staff without records are counted as absent
    - Only accessible by Owner or Receptionist
    """
    # Get all active staff
    all_staff = db.query(Staff).join(User).filter(
        Staff.is_active == True,
        User.deleted_at.is_(None)
    ).all()

    # Get attendance records for the date
    attendance_records = db.query(Attendance).options(
        joinedload(Attendance.staff).joinedload(Staff.user)
    ).filter(
        Attendance.date == date_filter
    ).all()

    # Build summary counts
    status_counts = {
        "present": 0,
        "half_day": 0,
        "absent": 0,
        "leave": 0
    }

    for record in attendance_records:
        status_counts[record.status.value] += 1

    # Staff without records are marked as absent
    marked_staff_ids = {r.staff_id for r in attendance_records}
    unmarked_count = len([s for s in all_staff if s.id not in marked_staff_ids])

    # Transform to response with staff info
    items = []
    for record in attendance_records:
        items.append(AttendanceWithStaffResponse(
            id=record.id,
            staff_id=record.staff_id,
            date=record.date,
            status=record.status,
            signed_in_at=record.signed_in_at,
            signed_out_at=record.signed_out_at,
            notes=record.notes,
            marked_by_id=record.marked_by_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            staff={
                "id": record.staff.id,
                "display_name": record.staff.display_name,
                "full_name": record.staff.user.full_name,
                "is_active": record.staff.is_active
            }
        ))

    return DailyAttendanceSummary(
        date=date_filter,
        total_staff=len(all_staff),
        present=status_counts["present"],
        half_day=status_counts["half_day"],
        absent=status_counts["absent"] + unmarked_count,
        leave=status_counts["leave"],
        attendance_records=items
    )


@router.get("/monthly/{staff_id}", response_model=MonthlyAttendanceSummary)
def get_monthly_report(
    staff_id: str,
    year: int = Query(default_factory=lambda: datetime.now().year, description="Year"),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly attendance report for a specific staff member.

    - Shows attendance percentage and breakdown by status
    - Includes all attendance records for the month
    - Owner/Receptionist can view any staff, Staff can only view own records
    """
    # Validate staff exists
    staff = db.query(Staff).join(User).filter(
        Staff.id == staff_id,
        User.deleted_at.is_(None)
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )

    # Permission check: Staff can only view own records
    if current_user.is_staff and (not current_user.staff or current_user.staff.id != staff_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff members can only view their own attendance"
        )

    # Get attendance records for the month
    records = db.query(Attendance).filter(
        Attendance.staff_id == staff_id,
        extract('year', Attendance.date) == year,
        extract('month', Attendance.date) == month
    ).order_by(Attendance.date).all()

    # Calculate statistics
    status_counts = {
        "present": 0,
        "half_day": 0,
        "absent": 0,
        "leave": 0
    }

    for record in records:
        status_counts[record.status.value] += 1

    # Calculate working days (total days in month - Sundays)
    _, total_days_in_month = calendar.monthrange(year, month)
    working_days = 0
    for day in range(1, total_days_in_month + 1):
        day_date = date(year, month, day)
        if day_date.weekday() != 6:  # 6 = Sunday
            working_days += 1

    # Calculate attendance percentage
    # Present = full day, Half day = 0.5 day
    effective_present_days = status_counts["present"] + (status_counts["half_day"] * 0.5)
    attendance_percentage = (effective_present_days / working_days * 100) if working_days > 0 else 0.0

    return MonthlyAttendanceSummary(
        year=year,
        month=month,
        staff_id=staff_id,
        staff_name=staff.user.full_name,
        total_days=working_days,
        present_days=status_counts["present"],
        half_days=status_counts["half_day"],
        absent_days=status_counts["absent"],
        leave_days=status_counts["leave"],
        attendance_percentage=round(attendance_percentage, 2),
        records=[AttendanceResponse.model_validate(r) for r in records]
    )


@router.get("/monthly-all", response_model=MonthlyAllStaffSummary)
def get_monthly_all_staff(
    year: int = Query(default_factory=lambda: datetime.now().year, description="Year"),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Get monthly attendance report for all active staff members.

    - Returns summary for each staff member
    - Only accessible by Owner or Receptionist
    """
    # Get all active staff
    all_staff = db.query(Staff).join(User).filter(
        Staff.is_active == True,
        User.deleted_at.is_(None)
    ).all()

    summaries = []
    for staff in all_staff:
        # Get attendance records for this staff member
        records = db.query(Attendance).filter(
            Attendance.staff_id == staff.id,
            extract('year', Attendance.date) == year,
            extract('month', Attendance.date) == month
        ).order_by(Attendance.date).all()

        # Calculate statistics
        status_counts = {
            "present": 0,
            "half_day": 0,
            "absent": 0,
            "leave": 0
        }

        for record in records:
            status_counts[record.status.value] += 1

        # Calculate working days
        _, total_days_in_month = calendar.monthrange(year, month)
        working_days = 0
        for day in range(1, total_days_in_month + 1):
            day_date = date(year, month, day)
            if day_date.weekday() != 6:  # 6 = Sunday
                working_days += 1

        # Calculate attendance percentage
        effective_present_days = status_counts["present"] + (status_counts["half_day"] * 0.5)
        attendance_percentage = (effective_present_days / working_days * 100) if working_days > 0 else 0.0

        summaries.append(MonthlyAttendanceSummary(
            year=year,
            month=month,
            staff_id=staff.id,
            staff_name=staff.user.full_name,
            total_days=working_days,
            present_days=status_counts["present"],
            half_days=status_counts["half_day"],
            absent_days=status_counts["absent"],
            leave_days=status_counts["leave"],
            attendance_percentage=round(attendance_percentage, 2),
            records=[AttendanceResponse.model_validate(r) for r in records]
        ))

    return MonthlyAllStaffSummary(
        year=year,
        month=month,
        summaries=summaries
    )


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: str,
    update_data: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """
    Update an existing attendance record.

    - Can modify status, times, and notes
    - Only accessible by Owner or Receptionist
    """
    # Find attendance record
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(attendance, field, value)

    # Update marked_by to current user
    attendance.marked_by_id = current_user.id

    db.commit()
    db.refresh(attendance)

    return attendance


@router.get("/my-attendance", response_model=AttendanceListResponse)
def get_my_attendance(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get own attendance records (for staff members).

    - Staff can only view their own attendance
    - Supports date range filtering
    - Returns paginated results
    """
    # Ensure user has a staff profile
    if not current_user.staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No staff profile found for current user"
        )

    # Default date range: last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        from datetime import timedelta
        start_date = end_date - timedelta(days=30)

    # Build query
    query = db.query(Attendance).options(
        joinedload(Attendance.staff).joinedload(Staff.user)
    ).filter(
        Attendance.staff_id == current_user.staff.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    records = query.order_by(Attendance.date.desc()).offset(offset).limit(size).all()

    # Transform to response
    items = []
    for record in records:
        items.append(AttendanceWithStaffResponse(
            id=record.id,
            staff_id=record.staff_id,
            date=record.date,
            status=record.status,
            signed_in_at=record.signed_in_at,
            signed_out_at=record.signed_out_at,
            notes=record.notes,
            marked_by_id=record.marked_by_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            staff={
                "id": record.staff.id,
                "display_name": record.staff.display_name,
                "full_name": record.staff.user.full_name,
                "is_active": record.staff.is_active
            }
        ))

    pages = (total + size - 1) // size

    return AttendanceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )
