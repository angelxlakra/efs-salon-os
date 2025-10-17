"""Audit and event logging models."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class Event(Base, ULIDMixin, TimestampMixin):
    """
    Event sourcing table for business events.

    Records all significant business events for audit and replay.
    """
    __tablename__ = "events"

    event_type = Column(String, nullable=False, index=True)  # 'bill.posted', 'payment.captured', etc.

    aggregate_type = Column(String, nullable=False, index=True)  # 'bill', 'appointment', etc.
    aggregate_id = Column(String(26), nullable=False, index=True)

    payload = Column(JSONB, nullable=False)
    event_metadata = Column(JSONB)

    def __repr__(self):
        return f"<Event {self.event_type} - {self.aggregate_id}>"


class AuditLog(Base, ULIDMixin, TimestampMixin):
    """
    Detailed audit trail of all user actions.

    Captures before/after state for sensitive operations.
    """
    __tablename__ = "audit_log"

    user_id = Column(String(26), ForeignKey("users.id"), index=True)
    action = Column(String, nullable=False)  # 'create', 'update', 'delete', 'approve', etc.

    entity_type = Column(String, nullable=False, index=True)  # 'bill', 'discount', etc.
    entity_id = Column(String(26), nullable=False, index=True)

    # Before/after snapshots
    old_values = Column(JSONB)
    new_values = Column(JSONB)

    # Context
    ip_address = Column(String)
    user_agent = Column(String)
    device_id = Column(String)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
