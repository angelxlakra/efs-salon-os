"""Appointment and WalkIn models for scheduling."""

import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class AppointmentStatus(str, enum.Enum):
    """Status lifecycle for appointments and walk-ins."""
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base, ULIDMixin, TimestampMixin):
    """
    Pre-scheduled appointments.

    Ticket Number Format: TKT-YYMMDD-### (e.g., TKT-251015-001)
    """
    __tablename__ = "appointments"

    ticket_number = Column(String, nullable=False, unique=True, index=True)
    visit_id = Column(String(26))  # Groups multiple services for same customer
    customer_id = Column(String(26), ForeignKey("customers.id"), index=True)
    service_id = Column(String(26), ForeignKey("services.id"), nullable=False)
    assigned_staff_id = Column(String(26), ForeignKey("staff.id"), index=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)

    # Status tracking
    status = Column(
        Enum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        index=True
    )
    checked_in_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Customer info (required even if no customer record)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)  # Nullable for walk-ins without phone

    # Notes
    booking_notes = Column(Text)
    service_notes = Column(Text)  # Staff adds during/after service
    service_notes_updated_at = Column(DateTime(timezone=True))

    # Audit
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    cancelled_at = Column(DateTime(timezone=True))

    # Relationships
    customer = relationship("Customer")
    service = relationship("Service")
    assigned_staff = relationship("Staff")
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Appointment {self.ticket_number} - {self.customer_name}>"

    @property
    def is_active(self) -> bool:
        """Check if appointment is active (not cancelled)."""
        return self.cancelled_at is None


class WalkIn(Base, ULIDMixin, TimestampMixin):
    """
    Walk-in customers (no prior appointment).

    Similar to Appointment but defaults to checked_in status.
    """
    __tablename__ = "walkins"

    ticket_number = Column(String, nullable=False, unique=True, index=True)
    visit_id = Column(String(26))
    session_id = Column(String(26), index=True)  # Groups services for same customer visit
    customer_id = Column(String(26), ForeignKey("customers.id"), index=True)
    service_id = Column(String(26), ForeignKey("services.id"), nullable=False)
    assigned_staff_id = Column(String(26), ForeignKey("staff.id"), index=True)

    duration_minutes = Column(Integer, nullable=False)
    status = Column(
        Enum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.CHECKED_IN,
        index=True
    )
    checked_in_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)  # Nullable for walk-ins without phone
    service_notes = Column(Text)
    service_notes_updated_at = Column(DateTime(timezone=True))

    # Billing integration
    bill_id = Column(String(26), ForeignKey("bills.id"), nullable=True, index=True)

    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    cancelled_at = Column(DateTime(timezone=True))
    cancellation_reason = Column(Text)

    # Relationships
    customer = relationship("Customer")
    service = relationship("Service")
    assigned_staff = relationship("Staff")
    created_by_user = relationship("User", foreign_keys=[created_by])
    bill = relationship("Bill", foreign_keys=[bill_id])

    def __repr__(self):
        return f"<WalkIn {self.ticket_number} - {self.customer_name}>"
