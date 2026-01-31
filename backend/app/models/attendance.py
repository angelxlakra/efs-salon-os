"""Attendance tracking models for staff attendance management."""

import enum
from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class AttendanceStatus(str, enum.Enum):
    """Status types for attendance records."""
    PRESENT = "present"         # Full day attendance
    HALF_DAY = "half_day"       # Half day attendance
    ABSENT = "absent"           # Marked absent
    LEAVE = "leave"             # Planned leave


class Attendance(Base, ULIDMixin, TimestampMixin):
    """
    Attendance records for staff members.

    Tracks daily attendance with clock-in/out times and status.
    One record per staff member per day (unique constraint).
    """
    __tablename__ = "attendance"

    # Core fields
    staff_id = Column(String(26), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=False, default=AttendanceStatus.ABSENT)

    # Time tracking
    signed_in_at = Column(DateTime(timezone=True), nullable=True)
    signed_out_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)  # Admin notes (reason for absence, etc.)
    marked_by_id = Column(String(26), ForeignKey("users.id"), nullable=False)  # Who marked attendance

    # Relationships
    staff = relationship("Staff", back_populates="attendance_records")
    marked_by = relationship("User", foreign_keys=[marked_by_id])

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('staff_id', 'date', name='uq_attendance_staff_date'),
        Index('idx_attendance_date', 'date'),
        Index('idx_attendance_staff_date', 'staff_id', 'date'),
    )

    def __repr__(self):
        return f"<Attendance {self.staff_id} {self.date} {self.status}>"
