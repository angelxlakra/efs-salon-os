"""User, Role, and Staff models for authentication and access control."""

import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


class RoleEnum(str, enum.Enum):
    """Role types in the system."""
    OWNER = "owner"
    RECEPTIONIST = "receptionist"
    STAFF = "staff"


class Role(Base, ULIDMixin, TimestampMixin):
    """
    Roles define access levels in the system.

    Three predefined roles:
    - owner: Full system access
    - receptionist: Can create bills, manage appointments, limited reports
    - staff: Can view schedules, mark services complete, view limited data
    """
    __tablename__ = "roles"

    name = Column(Enum(RoleEnum), nullable=False, unique=True)
    description = Column(Text)
    permissions = Column(JSONB, nullable=False, default=dict)

    # Relationships
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    User accounts for system access.

    All users must have a role (owner, receptionist, or staff).
    Staff users may also have a Staff profile for service assignments.
    """
    __tablename__ = "users"

    role_id = Column(String(26), ForeignKey("roles.id"), nullable=False, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, unique=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String)  # Encrypted in production
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    role = relationship("Role", back_populates="users")
    staff = relationship("Staff", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User {self.username} ({self.role.name if self.role else 'No Role'})>"

    @property
    def is_owner(self) -> bool:
        """Check if user is an owner."""
        return self.role and self.role.name == RoleEnum.OWNER

    @property
    def is_receptionist(self) -> bool:
        """Check if user is a receptionist."""
        return self.role and self.role.name == RoleEnum.RECEPTIONIST

    @property
    def is_staff(self) -> bool:
        """Check if user is staff."""
        return self.role and self.role.name == RoleEnum.STAFF


class Staff(Base, ULIDMixin, TimestampMixin):
    """
    Staff profile for service providers.

    Links to a User account and adds service-specific information like
    specialization and display name for customer-facing contexts.
    """
    __tablename__ = "staff"

    user_id = Column(String(26), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)  # What customers see
    specialization = Column(ARRAY(String))  # ['haircut', 'coloring', 'spa']
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="staff")

    def __repr__(self):
        return f"<Staff {self.display_name}>"
