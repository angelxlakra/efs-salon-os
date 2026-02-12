"""Pydantic schemas for catalog/services API requests and responses.

These schemas validate incoming requests and serialize outgoing responses
for the service catalog endpoints (categories, services, and addons).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ContributionTypeEnum(str, Enum):
    """How staff contribution is calculated."""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    EQUAL = "equal"


# ========== Service Category Schemas ==========

class ServiceCategoryCreate(BaseModel):
    """Schema for creating a service category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500)
    display_order: int = Field(default=0, ge=0, description="Sort order")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Haircut",
                "description": "All haircut services",
                "display_order": 1
            }
        }


class ServiceCategoryUpdate(BaseModel):
    """Schema for updating a service category."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Hair Styling",
                "display_order": 2
            }
        }


class ServiceCategoryResponse(BaseModel):
    """Schema for service category in response."""

    id: str
    name: str
    description: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceCategoryWithServices(ServiceCategoryResponse):
    """Category response including its services."""

    services: List["ServiceResponse"] = []


# ========== Service Addon Schemas ==========

class ServiceAddonCreate(BaseModel):
    """Schema for creating a service addon."""

    name: str = Field(..., min_length=1, max_length=100, description="Addon name")
    price: int = Field(..., gt=0, description="Price in paise (tax-inclusive)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Head Massage",
                "price": 15000
            }
        }


class ServiceAddonUpdate(BaseModel):
    """Schema for updating a service addon."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[int] = Field(None, gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Head Massage",
                "price": 20000
            }
        }


class ServiceAddonResponse(BaseModel):
    """Schema for service addon in response."""

    id: str
    service_id: str
    name: str
    price: int  # paise
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def price_rupees(self) -> float:
        """Get price in rupees."""
        return self.price / 100.0


# ========== Service Schemas ==========

class ServiceCreate(BaseModel):
    """Schema for creating a service."""

    category_id: str = Field(..., min_length=26, max_length=26, description="Category ID")
    name: str = Field(..., min_length=1, max_length=200, description="Service name")
    description: Optional[str] = Field(None, max_length=1000)
    base_price: int = Field(..., gt=0, description="Price in paise (tax-inclusive)")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duration in minutes")
    display_order: int = Field(default=0, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "category_id": "01HXXX1234567890ABCDEFGHIJ",
                "name": "Men's Haircut",
                "description": "Classic haircut with styling",
                "base_price": 40000,
                "duration_minutes": 30,
                "display_order": 1
            }
        }


class ServiceUpdate(BaseModel):
    """Schema for updating a service."""

    category_id: Optional[str] = Field(None, min_length=26, max_length=26)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[int] = Field(None, gt=0)
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "base_price": 45000,
                "duration_minutes": 35
            }
        }


class ServiceResponse(BaseModel):
    """Schema for service in response."""

    id: str
    category_id: str
    name: str
    description: Optional[str] = None
    base_price: int  # paise
    duration_minutes: int
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def base_price_rupees(self) -> float:
        """Get base price in rupees."""
        return self.base_price / 100.0


class ServiceWithAddons(ServiceResponse):
    """Service response including its addons."""

    addons: List[ServiceAddonResponse] = []
    category: Optional[ServiceCategoryResponse] = None


class ServiceWithCategory(ServiceResponse):
    """Service response with category info."""

    category: Optional[ServiceCategoryResponse] = None


# ========== Service Staff Template Schemas ==========

class ServiceStaffTemplateCreate(BaseModel):
    """Schema for creating a staff template for multi-person services."""

    role_name: str = Field(..., min_length=1, max_length=100, description="Role name (e.g., 'Botox Application')")
    role_description: Optional[str] = Field(None, max_length=500)
    sequence_order: int = Field(..., ge=1, description="Order in workflow (1, 2, 3...)")
    contribution_type: ContributionTypeEnum = Field(default=ContributionTypeEnum.PERCENTAGE)
    default_contribution_percent: Optional[int] = Field(None, ge=0, le=100, description="Percentage for PERCENTAGE type")
    default_contribution_fixed: Optional[int] = Field(None, gt=0, description="Fixed amount in paise for FIXED type")
    estimated_duration_minutes: int = Field(..., gt=0, le=480, description="Estimated time for this role")
    is_required: bool = Field(default=True, description="Can this role be skipped?")

    class Config:
        json_schema_extra = {
            "example": {
                "role_name": "Botox Application",
                "role_description": "Apply botox to designated areas",
                "sequence_order": 1,
                "contribution_type": "percentage",
                "default_contribution_percent": 50,
                "estimated_duration_minutes": 30,
                "is_required": True
            }
        }


class ServiceStaffTemplateUpdate(BaseModel):
    """Schema for updating a staff template."""

    role_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role_description: Optional[str] = Field(None, max_length=500)
    sequence_order: Optional[int] = Field(None, ge=1)
    contribution_type: Optional[ContributionTypeEnum] = None
    default_contribution_percent: Optional[int] = Field(None, ge=0, le=100)
    default_contribution_fixed: Optional[int] = Field(None, gt=0)
    estimated_duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None


class ServiceStaffTemplateResponse(BaseModel):
    """Schema for staff template in response."""

    id: str
    service_id: str
    role_name: str
    role_description: Optional[str] = None
    sequence_order: int
    contribution_type: str
    default_contribution_percent: Optional[int] = None
    default_contribution_fixed: Optional[int] = None
    estimated_duration_minutes: int
    is_required: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def contribution_display(self) -> str:
        """Human-readable contribution display."""
        if self.contribution_type == "percentage":
            return f"{self.default_contribution_percent}%"
        elif self.contribution_type == "fixed":
            return f"₹{self.default_contribution_fixed / 100:.2f}" if self.default_contribution_fixed else "N/A"
        else:
            return "Equal Split"


class ServiceWithTemplates(ServiceResponse):
    """Service response including staff templates for multi-person services."""

    staff_templates: List[ServiceStaffTemplateResponse] = []
    category: Optional[ServiceCategoryResponse] = None


# ========== List Response Schemas ==========

class ServiceCategoryListResponse(BaseModel):
    """Response for listing service categories."""

    categories: List[ServiceCategoryResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    {
                        "id": "01HXXX...",
                        "name": "Haircut",
                        "description": "All haircut services",
                        "display_order": 1,
                        "is_active": True,
                        "created_at": "2025-10-15T10:00:00",
                        "updated_at": "2025-10-15T10:00:00"
                    }
                ],
                "total": 5
            }
        }


class ServiceListResponse(BaseModel):
    """Response for listing services."""

    services: List[ServiceWithCategory]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "services": [
                    {
                        "id": "01HYYY...",
                        "category_id": "01HXXX...",
                        "name": "Men's Haircut",
                        "description": "Classic haircut with styling",
                        "base_price": 40000,
                        "duration_minutes": 30,
                        "display_order": 1,
                        "is_active": True,
                        "created_at": "2025-10-15T10:00:00",
                        "updated_at": "2025-10-15T10:00:00",
                        "category": {
                            "id": "01HXXX...",
                            "name": "Haircut"
                        }
                    }
                ],
                "total": 25
            }
        }


class CatalogResponse(BaseModel):
    """Full catalog response with categories and their services."""

    categories: List[ServiceCategoryWithServices]

    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    {
                        "id": "01HXXX...",
                        "name": "Haircut",
                        "display_order": 1,
                        "is_active": True,
                        "services": [
                            {
                                "id": "01HYYY...",
                                "name": "Men's Haircut",
                                "base_price": 40000,
                                "duration_minutes": 30
                            }
                        ]
                    }
                ]
            }
        }


# Update forward references
ServiceCategoryWithServices.model_rebuild()
