"""Packages HTTP API — catalog, sales, eligibility, redemption endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.auth.dependencies import require_permission
from app.models.user import User
from app.models.package import PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionUpdate, PackageDefinitionResponse,
)
from app.services import package_catalog_service

router = APIRouter(prefix="/packages", tags=["packages"])


# ---------- Catalog ----------

@router.get("/definitions", response_model=List[PackageDefinitionResponse])
def list_definitions(
    status_filter: Optional[PackageDefinitionStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None, max_length=255),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    q = db.query(PackageDefinition).options(
        joinedload(PackageDefinition.items).joinedload(PackageDefinitionItem.service)
    ).filter(PackageDefinition.deleted_at.is_(None))
    if status_filter:
        q = q.filter(PackageDefinition.status == status_filter)
    if search:
        q = q.filter(PackageDefinition.name.ilike(f"%{search}%"))
    return q.order_by(PackageDefinition.updated_at.desc()).all()


@router.get("/definitions/{def_id}", response_model=PackageDefinitionResponse)
def get_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    pkg = db.query(PackageDefinition).options(
        joinedload(PackageDefinition.items).joinedload(PackageDefinitionItem.service)
    ).filter(PackageDefinition.id == def_id).first()
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    return pkg


@router.post("/definitions", response_model=PackageDefinitionResponse, status_code=201)
def create_definition(
    payload: PackageDefinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "create")),
):
    try:
        pkg = package_catalog_service.create_definition(db, payload, user.id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.put("/definitions/{def_id}", response_model=PackageDefinitionResponse)
def update_definition(
    def_id: str,
    payload: PackageDefinitionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "update")),
):
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    try:
        pkg = package_catalog_service.update_definition(db, def_id, payload)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/definitions/{def_id}/publish", response_model=PackageDefinitionResponse)
def publish_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "update")),
):
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    try:
        pkg = package_catalog_service.publish(db, def_id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/definitions/{def_id}/archive", response_model=PackageDefinitionResponse)
def archive_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "update")),
):
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    try:
        pkg = package_catalog_service.archive(db, def_id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.delete("/definitions/{def_id}", status_code=204)
def delete_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "delete")),
):
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    try:
        package_catalog_service.soft_delete(db, def_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
