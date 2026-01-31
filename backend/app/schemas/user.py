"""User management schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import RoleEnum


# ========== Role Schemas ==========

class RoleResponse(BaseModel):
    """Role response schema."""
    id: str
    name: RoleEnum
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ========== User Schemas ==========

class UserBase(BaseModel):
    """Base user fields shared across schemas."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9_]+$")
    email: Optional[EmailStr] = None
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)
    role_id: str = Field(..., min_length=26, max_length=26)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user details."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-z0-9_]+$")
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    role_id: Optional[str] = Field(None, min_length=26, max_length=26)
    is_active: Optional[bool] = None


class UserPasswordChange(BaseModel):
    """Schema for changing user password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserPasswordReset(BaseModel):
    """Schema for admin resetting user password (owner only)."""
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(BaseModel):
    """User response schema (without password)."""
    id: str
    username: str
    email: Optional[str] = None
    full_name: str
    phone: Optional[str] = None
    role: RoleResponse
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated list of users."""
    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


# ========== Staff Schemas ==========

class StaffBase(BaseModel):
    """Base staff fields."""
    display_name: str = Field(..., min_length=1, max_length=100)
    specialization: Optional[List[str]] = None
    is_active: bool = True


class StaffCreate(StaffBase):
    """Schema for creating staff profile."""
    user_id: str = Field(..., min_length=26, max_length=26)


class StaffUpdate(BaseModel):
    """Schema for updating staff profile."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    specialization: Optional[List[str]] = None
    is_active: Optional[bool] = None


class StaffResponse(StaffBase):
    """Staff profile response."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithStaffResponse(UserResponse):
    """User response with staff profile if applicable."""
    staff: Optional[StaffResponse] = None

    class Config:
        from_attributes = True

class StaffWithUserResponse(StaffResponse):
    """Staff response with user details."""
    user: UserResponse

    class Config: 
        from_attributes = True

class StaffListResponse(BaseModel):
    """Paginated list of staff."""
    items: List[StaffWithUserResponse]
    total: int
    page: int
    size: int
    pages: int
