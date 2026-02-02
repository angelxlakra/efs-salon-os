"""Pydantic schemas for appointments and walk-ins."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.appointment import AppointmentStatus


# ============ Appointment Schemas ============

class AppointmentCreate(BaseModel):
    """Schema for creating a new appointment."""
    customer_id: Optional[str] = Field(None, description="Existing customer ID (optional)")
    customer_name: str = Field(..., min_length=2, description="Customer name (required)")
    customer_phone: str = Field(..., min_length=10, max_length=15, description="Customer phone")
    service_id: str = Field(..., description="Service to be performed")
    assigned_staff_id: Optional[str] = Field(None, description="Assigned staff member (optional)")
    scheduled_at: datetime = Field(..., description="Appointment date and time (IST)")
    duration_minutes: int = Field(..., ge=15, le=480, description="Duration in minutes (15min-8hrs)")
    booking_notes: Optional[str] = Field(None, description="Notes from receptionist")
    visit_id: Optional[str] = Field(None, description="Group multiple services for same visit")


class AppointmentUpdate(BaseModel):
    """Schema for updating an existing appointment."""
    service_id: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    booking_notes: Optional[str] = None
    service_notes: Optional[str] = None
    status: Optional[AppointmentStatus] = None


class AppointmentResponse(BaseModel):
    """Schema for returning appointment data."""
    id: str
    ticket_number: str
    visit_id: Optional[str]
    customer_id: Optional[str]
    customer_name: str
    customer_phone: Optional[str]  # Nullable for walk-ins without phone
    service_id: str
    assigned_staff_id: Optional[str]
    scheduled_at: datetime
    duration_minutes: int
    status: AppointmentStatus
    checked_in_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    booking_notes: Optional[str]
    service_notes: Optional[str]
    service_notes_updated_at: Optional[datetime]
    created_by: str
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentWithDetails(AppointmentResponse):
    """Extended appointment response with related data."""
    service_name: Optional[str] = None
    staff_name: Optional[str] = None
    customer_email: Optional[str] = None


# ============ Walk-In Schemas ============

class WalkInCreate(BaseModel):
    """Schema for creating a walk-in customer."""
    customer_id: Optional[str] = Field(None, description="Existing customer ID (optional)")
    customer_name: str = Field(..., min_length=2, description="Customer name (required)")
    customer_phone: str = Field(..., min_length=10, max_length=15, description="Customer phone")
    service_id: str = Field(..., description="Service to be performed")
    assigned_staff_id: Optional[str] = Field(None, description="Assigned staff member (optional)")
    duration_minutes: int = Field(..., ge=15, le=480, description="Duration in minutes")
    visit_id: Optional[str] = Field(None, description="Group multiple services for same visit")


class WalkInResponse(BaseModel):
    """Schema for returning walk-in data."""
    id: str
    ticket_number: str
    visit_id: Optional[str]
    session_id: Optional[str]
    customer_id: Optional[str]
    customer_name: str
    customer_phone: Optional[str]  # Nullable for walk-ins without phone
    service_id: str
    assigned_staff_id: Optional[str]
    duration_minutes: int
    status: AppointmentStatus
    checked_in_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    service_notes: Optional[str]
    service_notes_updated_at: Optional[datetime]
    bill_id: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Status Update Schemas ============

class StatusUpdate(BaseModel):
    """Schema for updating appointment/walk-in status."""
    status: AppointmentStatus


class ServiceNotesUpdate(BaseModel):
    """Schema for updating service notes."""
    service_notes: str = Field(..., min_length=1, max_length=2000)


class CancelRequest(BaseModel):
    """Schema for cancelling a walk-in or appointment."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for cancellation")


# ============ List/Filter Schemas ============

class AppointmentFilters(BaseModel):
    """Query parameters for filtering appointments."""
    date: Optional[str] = Field(None, description="Filter by date (YYYY-MM-DD)")
    staff_id: Optional[str] = Field(None, description="Filter by assigned staff")
    status: Optional[AppointmentStatus] = Field(None, description="Filter by status")
    customer_id: Optional[str] = Field(None, description="Filter by customer")
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)


# ============ Bulk Walk-In Schemas ============

class BulkWalkInItemCreate(BaseModel):
    """Schema for a single item in bulk walk-in creation."""
    service_id: str = Field(..., description="Service to be performed")
    assigned_staff_id: str = Field(..., description="Staff member assigned to this service")
    quantity: int = Field(1, ge=1, le=10, description="Number of times this service is performed")


class BulkWalkInCreate(BaseModel):
    """Schema for creating multiple walk-ins at once (from POS cart)."""
    session_id: str = Field(..., description="Session ID to group all services for this customer")
    customer_name: str = Field(..., min_length=2, description="Customer name")
    customer_phone: str = Field(default="", description="Customer phone (optional for walk-ins)")
    customer_id: Optional[str] = Field(None, description="Existing customer ID (optional)")
    items: List[BulkWalkInItemCreate] = Field(..., min_length=1, description="List of services")


class BulkWalkInResponse(BaseModel):
    """Response after creating bulk walk-ins."""
    session_id: str
    walkins: List[WalkInResponse]
    total_items: int
    message: str


# ============ Staff Dashboard Schemas ============

class ServiceResponseBase(BaseModel):
    """Basic service information."""
    id: str
    name: str
    base_price: int
    duration_minutes: int

    model_config = ConfigDict(from_attributes=True)


class StaffResponseBase(BaseModel):
    """Basic staff information."""
    id: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class WalkInWithDetails(BaseModel):
    """Walk-in with related service and staff details."""
    id: str
    ticket_number: str
    customer_name: str
    customer_phone: Optional[str]  # Nullable for walk-ins without phone
    customer_id: Optional[str]
    service: ServiceResponseBase
    assigned_staff: StaffResponseBase
    status: AppointmentStatus
    checked_in_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    service_notes: Optional[str]
    duration_minutes: int
    session_id: Optional[str]


class MyServicesResponse(BaseModel):
    """Response for staff's assigned services."""
    services: List[WalkInWithDetails]
    total: int
    date: str


# ============ Live Dashboard Schemas ============

class CustomerSessionGroup(BaseModel):
    """Group of walk-ins for a single customer session."""
    session_id: str
    customer_name: str
    customer_phone: Optional[str]  # Nullable for walk-ins without phone
    customer_id: Optional[str]
    walkins: List[WalkInWithDetails]
    total_amount: int = Field(..., description="Total amount in paise")
    time_since_checkin: int = Field(..., description="Minutes since first check-in")
    all_completed: bool = Field(..., description="Whether all services are completed")


class ActiveWalkInsResponse(BaseModel):
    """Response for active walk-ins (live dashboard)."""
    sessions: List[CustomerSessionGroup]
    total_customers: int
