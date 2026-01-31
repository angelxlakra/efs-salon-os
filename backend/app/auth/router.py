"""Authentication API endpoints.

This module provides REST API endpoints for:
- User login and logout
- Token refresh
- Password change
- User profile retrieval
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.user import User
from app.auth.jwt import JWTHandler
from app.auth.password import PasswordHandler
from app.auth.session import session_manager
from app.auth.permissions import PermissionChecker
from app.auth.dependencies import (
    get_current_user,
    check_rate_limit
)


# ========== Request/Response Models ==========

class LoginRequest(BaseModel):
    """Login request payload."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    device_id: Optional[str] = Field(None, max_length=100)


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    user: dict


class RefreshRequest(BaseModel):
    """Token refresh request payload."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Logout request payload."""
    refresh_token: Optional[str] = None
    logout_all_devices: bool = False


class LogoutResponse(BaseModel):
    """Logout response."""
    message: str


class ChangePasswordRequest(BaseModel):
    """Password change request payload."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordResponse(BaseModel):
    """Password change response."""
    message: str


class UserInfoResponse(BaseModel):
    """User information response."""
    id: str
    username: str
    full_name: str
    email: Optional[str]
    role: str
    permissions: dict
    last_login_at: Optional[datetime]
    is_active: bool


# ========== Router ==========

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ========== Endpoints ==========

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_rate_limit)]
)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and issue tokens.

    **Rate Limit:** 5 attempts per minute per IP.
    **Account Lockout:** 10 failed attempts locks account for 15 minutes.

    Args:
        credentials: Login credentials (username, password, optional device_id).
        request: FastAPI request object.
        db: Database session.

    Returns:
        LoginResponse: Access token, refresh token, and user information.

    Raises:
        401: Invalid credentials.
        403: Account locked due to too many failed attempts.
        429: Rate limit exceeded.

    Example:
        ```bash
        curl -X POST http://localhost/api/auth/login \\
          -H "Content-Type: application/json" \\
          -d '{"username":"owner","password":"MySecure123"}'
        ```
    """
    # Check if account is locked
    if await session_manager.is_account_locked(credentials.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily locked due to too many failed login attempts"
        )

    # Find user by username
    user = db.query(User).filter(
        User.username == credentials.username,
        User.deleted_at.is_(None)
    ).first()

    # Verify user exists and password is correct
    if not user or not PasswordHandler.verify_password(
        credentials.password,
        user.password_hash
    ):
        # Increment failed login counter
        await session_manager.increment_failed_login(credentials.username)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Reset failed login counter on successful login
    await session_manager.reset_failed_login(credentials.username)

    # Create tokens
    access_token = JWTHandler.create_access_token(
        user=user,
        device_id=credentials.device_id
    )
    refresh_token, jti = JWTHandler.create_refresh_token(
        user=user,
        device_id=credentials.device_id
    )

    # Store refresh token in Redis
    await session_manager.store_refresh_token(
        user_id=user.id,
        jti=jti,
        token=refresh_token,
        device_id=credentials.device_id
    )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Get user permissions
    permissions = PermissionChecker.get_role_permissions(user.role.name)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.name.value,
            "permissions": permissions
        }
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK
)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Get new access token using refresh token.

    The refresh token is rotated (invalidated and replaced) on use.

    Args:
        refresh_request: Refresh token.
        db: Database session.

    Returns:
        RefreshResponse: New access token and new refresh token.

    Raises:
        401: Invalid or expired refresh token.
        403: Token revoked or user disabled.

    Example:
        ```bash
        curl -X POST http://localhost/api/auth/refresh \\
          -H "Content-Type: application/json" \\
          -d '{"refresh_token":"eyJhbGc..."}'
        ```
    """
    try:
        # Decode refresh token
        payload = JWTHandler.decode_token(refresh_request.refresh_token)

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Validate refresh token exists in Redis
        if not await session_manager.validate_refresh_token(user_id, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        # Fetch user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found or inactive"
            )

        # Revoke old refresh token (token rotation)
        await session_manager.revoke_refresh_token(user_id, jti)

        # Create new tokens
        device_id = payload.get("device_id")
        new_access_token = JWTHandler.create_access_token(user, device_id)
        new_refresh_token, new_jti = JWTHandler.create_refresh_token(user, device_id)

        # Store new refresh token
        await session_manager.store_refresh_token(
            user_id=user.id,
            jti=new_jti,
            token=new_refresh_token,
            device_id=device_id
        )

        return RefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK
)
async def logout(
    logout_request: LogoutRequest,
    current_user: User = Depends(get_current_user)
):
    """Logout user and invalidate tokens.

    Args:
        logout_request: Logout options (refresh token, logout from all devices).
        current_user: Current authenticated user.

    Returns:
        LogoutResponse: Success message.

    Example:
        ```bash
        curl -X POST http://localhost/api/auth/logout \\
          -H "Authorization: Bearer {access_token}" \\
          -H "Content-Type: application/json" \\
          -d '{"refresh_token":"eyJhbGc...","logout_all_devices":false}'
        ```
    """
    if logout_request.logout_all_devices:
        # Revoke all refresh tokens for user
        await session_manager.revoke_all_user_tokens(current_user.id)
        message = "Logged out from all devices successfully"
    elif logout_request.refresh_token:
        # Revoke specific refresh token
        try:
            payload = JWTHandler.decode_token(logout_request.refresh_token)
            jti = payload.get("jti")
            if jti:
                await session_manager.revoke_refresh_token(current_user.id, jti)
        except Exception:
            # Token might already be invalid, that's okay
            pass
        message = "Logged out successfully"
    else:
        message = "Logged out successfully"

    return LogoutResponse(message=message)


@router.get(
    "/me",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information.

    Args:
        current_user: Current authenticated user.

    Returns:
        UserInfoResponse: User profile information and permissions.

    Example:
        ```bash
        curl http://localhost/api/auth/me \\
          -H "Authorization: Bearer {access_token}"
        ```
    """
    permissions = PermissionChecker.get_role_permissions(current_user.role.name)

    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role.name.value,
        permissions=permissions,
        last_login_at=current_user.last_login_at,
        is_active=current_user.is_active
    )


