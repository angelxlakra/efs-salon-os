from app.auth.dependencies import require_owner_or_receptionist, get_current_user, require_owner
from app.auth.password import PasswordHandler
from typing import Optional
from fastapi import Depends, APIRouter, status, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.schemas.user import (
    UserListResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    UserPasswordChange,
    UserPasswordReset
)
from app.models.user import User, Role, RoleEnum
from app.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    query = db.query(User).filter(User.deleted_at.is_(None))

    if search:
        search_filter = or_(
            User.full_name.ilike(f"%{search}%"),
            User.phone.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    query = query.order_by(User.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    # Check for duplicate username, email, or phone
    filters = [User.username == user_in.username]
    if user_in.email:
        filters.append(User.email == user_in.email)
    if user_in.phone:
        filters.append(User.phone == user_in.phone)

    existing = db.query(User).filter(
        or_(*filters),
        User.deleted_at.is_(None)
    ).first()

    if existing:
        if existing.username == user_in.username:
            raise HTTPException(status_code=400, detail="Username already exists")
        elif user_in.email and existing.email == user_in.email:
            raise HTTPException(status_code=400, detail="Email already exists")
        elif user_in.phone and existing.phone == user_in.phone:
            raise HTTPException(status_code=400, detail="Phone already exists")

    role = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role_id")

    user_data = user_in.model_dump()
    password = user_data.pop("password")
    is_valid, errors = PasswordHandler.validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"message": "Password validation failed", "errors": errors})
    
    user_data["password_hash"] = PasswordHandler.hash_password(password)

    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{id}", response_model=UserResponse)
def get_user(
    id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    user = db.query(User).filter(
        User.id == id,
        User.deleted_at.is_(None)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{id}", response_model=UserResponse)
def update_user(
    id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    user = db.query(User).filter(
        User.id == id,
        User.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)

    # Prevent users from changing their own role
    if "role_id" in update_data and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    if "email" in update_data and update_data["email"] != user.email:
        existing = db.query(User).filter(
            User.email == update_data["email"],
            User.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    if "phone" in update_data and update_data["phone"] != user.phone:
        existing = db.query(User).filter(
            User.phone == update_data["phone"],
            User.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone already exists")

    if "username" in update_data and update_data["username"] != user.username:
        existing = db.query(User).filter(
            User.username == update_data["username"],
            User.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

    if "role_id" in update_data and update_data["role_id"] != user.role_id:
        role_exists = db.query(Role).filter(Role.id == update_data["role_id"]).first()
        if not role_exists:
            raise HTTPException(status_code=400, detail="Invalid role_id")

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    user = db.query(User).filter(
        User.id == id,
        User.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Prevent deleting the last owner
    if user.role.name == RoleEnum.OWNER:
        owner_count = db.query(User).join(Role).filter(
            Role.name == RoleEnum.OWNER,
            User.deleted_at.is_(None)
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last owner account")

    user.soft_delete()
    db.add(user)
    db.commit()

@router.post("/{id}/reset-password", response_model=UserResponse)
def reset_user_password(
    id: str,
    password_reset: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Admin password reset endpoint (owner only).

    Allows owners to reset any user's password without knowing the current password.
    """
    user = db.query(User).filter(
        User.id == id,
        User.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate new password strength
    is_valid, errors = PasswordHandler.validate_password_strength(password_reset.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Password validation failed", "errors": errors}
        )

    # Hash new password
    new_password_hash = PasswordHandler.hash_password(password_reset.new_password)

    # Check password history
    password_history = user.password_history or []
    if PasswordHandler.check_password_history(new_password_hash, password_history):
        raise HTTPException(
            status_code=400,
            detail="Cannot reuse recent passwords"
        )

    # Update password and password history
    new_history = password_history + [user.password_hash]
    from app.config import settings
    user.password_history = new_history[-settings.password_history_count:]
    user.password_hash = new_password_hash

    db.commit()
    db.refresh(user)
    return user


