from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, RoleEnum

# Placeholder for actual auth implementation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user.
    
    NOTE: This is a placeholder implementation since the auth module
    was not found in the current tree. It returns the first user found
    to allow development/testing to proceed.
    """
    # In a real implementation: decode token -> user_id -> db.get(user_id)
    
    # For dev: Just return first user
    user = db.query(User).first()
    if not user:
        # Fallback if DB is empty, though in real usage this should 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials (No users in DB)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def check_receptionist_permission(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Allow access to Receptionists and Owners.
    """
    # RoleEnum values: 'owner', 'receptionist', 'staff'
    # We check if role is mapped or check properties if they exist
    # User model has is_owner, is_receptionist properties
    if not (current_user.is_receptionist or current_user.is_owner):
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
