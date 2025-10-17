"""Service catalog models for managing salon services."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


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
    duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    display_order = Column(Integer, nullable=False, default=0)

    # Relationships
    category = relationship("ServiceCategory", back_populates="services")
    addons = relationship("ServiceAddon", back_populates="service")

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
