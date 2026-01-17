"""FastAPI dependencies for authentication and authorization.

This module provides reusable FastAPI dependencies for:
- Extracting and validating current user from JWT tokens
- Role-based access control
- Permission checking
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, RoleEnum
from app.auth.jwt import JWTHandler
from app.auth.permissions import PermissionChecker
from app.auth.session import session_manager


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current authenticated user.

    Extracts JWT token from Authorization header, validates it,
    and returns the corresponding User object.

    Args:
        credentials: HTTP Bearer token credentials.
        db: Database session.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found.

    Example:
        >>> @app.get("/profile")
        >>> async def get_profile(current_user: User = Depends(get_current_user)):
        ...     return {"username": current_user.username}
    """
    try:
        token = credentials.credentials
        payload = JWTHandler.decode_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Check if token is blacklisted (optional: if jti is in payload)
        jti = payload.get("jti")
        if jti and await session_manager.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Fetch user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return user

    except ValueError as e:
        # JWT decode errors (expired, invalid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_role(*allowed_roles: RoleEnum):
    """Dependency factory to require specific roles.

    Creates a dependency that checks if the current user has
    one of the allowed roles.

    Args:
        *allowed_roles: Variable number of allowed role enums.

    Returns:
        Dependency function that validates user role.

    Raises:
        HTTPException: 403 if user role not in allowed roles.

    Example:
        >>> # Only owners can access this endpoint
        >>> @app.delete("/users/{user_id}")
        >>> async def delete_user(
        ...     user_id: str,
        ...     current_user: User = Depends(require_role(RoleEnum.OWNER))
        ... ):
        ...     # Delete user logic
        ...     pass
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(r.value for r in allowed_roles)}"
            )
        return current_user

    return role_checker


def require_permission(resource: str, action: str):
    """Dependency factory to require specific permission.

    Creates a dependency that checks if the current user's role
    has permission for a specific resource.action.

    Args:
        resource: The resource name (e.g., "billing", "appointments").
        action: The action name (e.g., "create", "read").

    Returns:
        Dependency function that validates permission.

    Raises:
        HTTPException: 403 if user lacks required permission.

    Example:
        >>> # Only users with billing.refund permission can access
        >>> @app.post("/bills/{bill_id}/refund")
        >>> async def refund_bill(
        ...     bill_id: str,
        ...     current_user: User = Depends(require_permission("billing", "refund"))
        ... ):
        ...     # Refund logic
        ...     pass
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not PermissionChecker.has_permission(
            current_user.role.name,
            resource,
            action
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {resource}.{action}"
            )
        return current_user

    return permission_checker


# ========== Common Role Dependencies ==========
# Pre-defined dependencies for common role requirements

# Owner only
require_owner = require_role(RoleEnum.OWNER)

# Owner or Receptionist
require_owner_or_receptionist = require_role(
    RoleEnum.OWNER,
    RoleEnum.RECEPTIONIST
)

# Any authenticated user
require_authenticated = get_current_user


# ========== Optional Authentication ==========

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token provided, otherwise None.

    Useful for endpoints that work both authenticated and unauthenticated.

    Args:
        credentials: Optional HTTP Bearer token credentials.
        db: Database session.

    Returns:
        User or None: The authenticated user if token valid, else None.

    Example:
        >>> @app.get("/public-data")
        >>> async def get_public_data(
        ...     current_user: Optional[User] = Depends(get_current_user_optional)
        ... ):
        ...     if current_user:
        ...         # Return personalized data
        ...         pass
        ...     else:
        ...         # Return public data
        ...         pass
    """
    if not credentials:
        return None

    try:
        # Reuse the main get_current_user logic
        token = credentials.credentials
        payload = JWTHandler.decode_token(token)

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active == True
        ).first()

        return user

    except Exception:
        # Silently fail for optional authentication
        return None


# ========== Rate Limiting Dependency ==========

async def check_rate_limit(request: Request):
    """Check rate limit for login endpoint.

    Uses client IP address for rate limiting.

    Args:
        request: FastAPI request object.

    Raises:
        HTTPException: 429 if rate limit exceeded.

    Example:
        >>> @app.post("/auth/login", dependencies=[Depends(check_rate_limit)])
        >>> async def login(credentials: LoginRequest):
        ...     # Login logic
        ...     pass
    """
    client_ip = request.client.host if request.client else "unknown"

    allowed = await session_manager.check_login_rate_limit(client_ip)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
