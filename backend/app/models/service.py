"""Service catalog models for managing salon services."""

import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


class ContributionType(str, enum.Enum):
    """How staff contribution is calculated."""
    PERCENTAGE = "percentage"  # Percentage of service price
    FIXED = "fixed"           # Fixed amount in paise
    EQUAL = "equal"           # Equal split among all staff


class ServiceCategory(Base, ULIDMixin, TimestampMixin):
    """
    Service categories for grouping services.

    Examples: Haircut, Hair Color, Spa, Makeup, etc.
    """
    __tablename__ = "service_categories"

    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    services = relationship("Service", back_populates="category")

    def __repr__(self):
        return f"<ServiceCategory {self.name}>"


class Service(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Individual salon services.

    All prices are tax-inclusive and stored in paise (Rs 1 = 100 paise).
    """
    __tablename__ = "services"

    category_id = Column(String(26), ForeignKey("service_categories.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    base_price = Column(Integer, nullable=False)  # in paise, tax-inclusive
    duration_minutes = Column(Integer, nullable=False)  # Estimated duration
    average_duration_minutes = Column(Integer, nullable=True)  # Calculated from actual history
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    display_order = Column(Integer, nullable=False, default=0)

    # Relationships
    category = relationship("ServiceCategory", back_populates="services")
    addons = relationship("ServiceAddon", back_populates="service")
    material_usage = relationship("ServiceMaterialUsage", back_populates="service")
    staff_templates = relationship("ServiceStaffTemplate", back_populates="service", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Service {self.name}>"

    @property
    def base_price_rupees(self) -> float:
        """Get base price in rupees."""
        return self.base_price / 100.0


class ServiceAddon(Base, ULIDMixin, TimestampMixin):
    """
    Optional add-ons for services.

    Example: Extra conditioning treatment for a haircut.
    """
    __tablename__ = "service_addons"

    service_id = Column(String(26), ForeignKey("services.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)  # in paise, tax-inclusive

    # Relationships
    service = relationship("Service", back_populates="addons")

    def __repr__(self):
        return f"<ServiceAddon {self.name} for {self.service.name if self.service else 'Unknown'}>"

    @property
    def price_rupees(self) -> float:
        """Get price in rupees."""
        return self.price / 100.0


class ServiceMaterialUsage(Base, ULIDMixin, TimestampMixin):
    """
    Track inventory items (SKUs) consumed when a service is performed.

    Enables accurate COGS calculation for services.
    Example: Men's haircut uses 5ml shampoo + 2ml conditioner.
    """
    __tablename__ = "service_material_usage"

    service_id = Column(String(26), ForeignKey("services.id"), nullable=False, index=True)
    sku_id = Column(String(26), ForeignKey("skus.id"), nullable=False, index=True)

    # Quantity consumed per service performance
    quantity_per_service = Column(Numeric(10, 2), nullable=False)

    # Optional notes
    notes = Column(Text)

    # Relationships
    service = relationship("Service", back_populates="material_usage")
    sku = relationship("SKU")

    def __repr__(self):
        return f"<ServiceMaterialUsage {self.service.name if self.service else 'Unknown'} uses {self.quantity_per_service} {self.sku.uom if self.sku else ''}>"


class ServiceStaffTemplate(Base, ULIDMixin, TimestampMixin):
    """
    Predefined staff roles for multi-person services.

    Defines the standard workflow and contribution split for services
    that require multiple staff members (e.g., Botox, Complex Treatments).

    Example:
    - Botox Treatment requires 3 staff:
      1. Application Specialist (50% contribution, 30 min)
      2. Hair Wash Technician (25% contribution, 15 min)
      3. Styling Artist (25% contribution, 20 min)
    """
    __tablename__ = "service_staff_templates"

    service_id = Column(String(26), ForeignKey("services.id"), nullable=False, index=True)

    # Role definition
    role_name = Column(String(100), nullable=False)  # e.g., "Botox Application", "Hair Wash"
    role_description = Column(Text)  # Detailed description of what this role does

    # Workflow ordering
    sequence_order = Column(Integer, nullable=False)  # 1, 2, 3... (order of execution)

    # Contribution settings
    contribution_type = Column(Enum(ContributionType), nullable=False, default=ContributionType.PERCENTAGE)
    default_contribution_percent = Column(Integer, nullable=True)  # 0-100 (for PERCENTAGE type)
    default_contribution_fixed = Column(Integer, nullable=True)  # paise (for FIXED type)

    # Time estimation
    estimated_duration_minutes = Column(Integer, nullable=False)

    # Requirements
    is_required = Column(Boolean, nullable=False, default=True)  # Can this role be skipped?

    # Active status
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    service = relationship("Service", back_populates="staff_templates")

    def __repr__(self):
        return f"<ServiceStaffTemplate {self.role_name} for {self.service.name if self.service else 'Unknown'}>"

    @property
    def contribution_percent_display(self) -> str:
        """Human-readable contribution display."""
        if self.contribution_type == ContributionType.PERCENTAGE:
            return f"{self.default_contribution_percent}%"
        elif self.contribution_type == ContributionType.FIXED:
            return f"₹{self.default_contribution_fixed / 100:.2f}"
        else:
            return "Equal Split"
