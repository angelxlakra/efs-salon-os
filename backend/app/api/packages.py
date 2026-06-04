"""Packages HTTP API — catalog, sales, eligibility, redemption endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.auth.dependencies import require_permission
from app.models.user import User
from app.models.package import PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus
from app.models.package import PackageSale, PackageSaleItem, PackageSaleStatus
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionUpdate, PackageDefinitionResponse,
)
from app.schemas.package import (
    PackageSaleResponse, PackageSaleSummary, RefundRequest, ExtendExpiryRequest,
)
from app.services import package_catalog_service, package_refund_service, package_expiry_service

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


# ---------- Sales ----------

@router.get("/sales", response_model=List[PackageSaleResponse])
def list_sales(
    customer_id: Optional[str] = None,
    status_filter: Optional[PackageSaleStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    q = db.query(PackageSale).options(
        joinedload(PackageSale.customer),
        joinedload(PackageSale.definition),
        joinedload(PackageSale.items).joinedload(PackageSaleItem.service),
    )
    if customer_id:
        q = q.filter(PackageSale.customer_id == customer_id)
    if status_filter:
        q = q.filter(PackageSale.status == status_filter)
    return q.order_by(PackageSale.sold_at.desc()).all()


@router.get("/sales/active-for-customer/{customer_id}", response_model=List[PackageSaleSummary])
def list_active_for_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return (
        db.query(PackageSale)
        .filter(
            PackageSale.customer_id == customer_id,
            PackageSale.status == PackageSaleStatus.ACTIVE,
            PackageSale.expires_at > now,
        )
        .order_by(PackageSale.expires_at.asc())
        .all()
    )


@router.get("/sales/{sale_id}", response_model=PackageSaleResponse)
def get_sale(
    sale_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    sale = db.query(PackageSale).options(
        joinedload(PackageSale.customer),
        joinedload(PackageSale.definition),
        joinedload(PackageSale.items).joinedload(PackageSaleItem.service),
    ).filter(PackageSale.id == sale_id).first()
    if not sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sale not found")
    return sale


@router.post("/sales/{sale_id}/extend", response_model=PackageSaleResponse)
def extend_sale(
    sale_id: str,
    payload: ExtendExpiryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "extend_expiry")),
):
    try:
        sale = package_expiry_service.extend_expiry(
            db, sale_id, payload.new_expires_at, payload.reason, user.id,
        )
        db.commit()
        return sale
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/sales/{sale_id}/refund", response_model=dict)
def refund_sale(
    sale_id: str,
    payload: RefundRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "refund")),
):
    try:
        credit_note = package_refund_service.issue_refund(
            db, sale_id, payload.payment_method, payload.reason, user.id,
        )
        db.commit()
        return {"credit_note_bill_id": credit_note.id, "status": "refunded"}
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
