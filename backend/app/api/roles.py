"""Roles API - Simple endpoint to list available roles."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import Role, User
from app.schemas.user import RoleResponse
from app.auth.dependencies import require_owner

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """
    List all available roles.

    Returns role IDs needed for user creation.

    **Permission:** Owner only
    """
    roles = db.query(Role).all()
    return roles
