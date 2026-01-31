"""Pydantic schemas for attendance management."""

from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, ConfigDict
from datetime import date as DateType, datetime as DateTimeType
from typing import Optional, List, Dict, Any
import enum


class AttendanceStatus(str, enum.Enum):
    """Attendance status enum."""
    PRESENT = "present"
    HALF_DAY = "half_day"
    ABSENT = "absent"
    LEAVE = "leave"


# Create schema
class AttendanceCreate(BaseModel):
    """Schema for creating a new attendance record."""
    staff_id: str = Field(..., min_length=26, max_length=26, description="ULID of staff member")
    date: DateType = Field(..., description="Date of attendance")
    status: AttendanceStatus = Field(..., description="Attendance status")
    signed_in_at: Optional[DateTimeType] = Field(None, description="Clock-in timestamp (required for PRESENT/HALF_DAY)")
    signed_out_at: Optional[DateTimeType] = Field(None, description="Clock-out timestamp")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes (reason for absence, etc.)")

    @model_validator(mode='after')
    def validate_attendance(self):
        """Validate attendance constraints."""
        # Ensure signed_in_at is provided for PRESENT/HALF_DAY status
        if self.status in [AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY]:
            if not self.signed_in_at:
                raise ValueError(f'signed_in_at is required when status is {self.status.value}')

        # Ensure sign out time is after sign in time
        if self.signed_out_at and self.signed_in_at and self.signed_out_at < self.signed_in_at:
            raise ValueError('Sign out time must be after sign in time')

        return self


# Update schema
class AttendanceUpdate(BaseModel):
    """Schema for updating an existing attendance record."""
    status: Optional[AttendanceStatus] = None
    signed_in_at: Optional[DateTimeType] = None
    signed_out_at: Optional[DateTimeType] = None
    notes: Optional[str] = Field(None, max_length=500)


# Response schema
class AttendanceResponse(BaseModel):
    """Schema for attendance record response."""
    id: str
    staff_id: str
    date: DateType
    status: AttendanceStatus
    signed_in_at: Optional[DateTimeType] = None
    signed_out_at: Optional[DateTimeType] = None
    notes: Optional[str] = None
    marked_by_id: str
    created_at: DateTimeType
    updated_at: DateTimeType

    model_config = ConfigDict(from_attributes=True)


# With relationships
class AttendanceWithStaffResponse(BaseModel):
    """Attendance record with staff details."""
    id: str
    staff_id: str
    date: DateType
    status: AttendanceStatus
    signed_in_at: Optional[DateTimeType] = None
    signed_out_at: Optional[DateTimeType] = None
    notes: Optional[str] = None
    marked_by_id: str
    created_at: DateTimeType
    updated_at: DateTimeType
    staff: Dict[str, Any]  # Staff info dict


# List response
class AttendanceListResponse(BaseModel):
    """Paginated list of attendance records."""
    items: List[AttendanceWithStaffResponse]
    total: int
    page: int
    size: int
    pages: int


# Daily summary
class DailyAttendanceSummary(BaseModel):
    """Daily attendance summary with counts and records."""
    date: DateType
    total_staff: int
    present: int
    half_day: int
    absent: int
    leave: int
    attendance_records: List[AttendanceWithStaffResponse]


# Monthly summary for individual staff
class MonthlyAttendanceSummary(BaseModel):
    """Monthly attendance summary for a single staff member."""
    year: int
    month: int
    staff_id: str
    staff_name: str
    total_days: int  # Working days in month (excluding Sundays/holidays)
    present_days: int
    half_days: int
    absent_days: int
    leave_days: int
    attendance_percentage: float
    records: List[AttendanceResponse]


# Monthly summary for all staff
class MonthlyAllStaffSummary(BaseModel):
    """Monthly attendance summary for all staff members."""
    year: int
    month: int
    summaries: List[MonthlyAttendanceSummary]
