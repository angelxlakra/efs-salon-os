from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))
    
    if search:
        search_filter = or_(
            Customer.first_name.ilike(f"%{search}%"),
            Customer.last_name.ilike(f"%{search}%"),
            Customer.phone.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
        
    if phone:
        query = query.filter(Customer.phone.ilike(f"%{phone}%"))

    # Default ordering by most recent first
    query = query.order_by(Customer.created_at.desc())

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

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    existing = db.query(Customer).filter(
        Customer.phone == customer_in.phone,
        Customer.deleted_at.is_(None)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this phone number already exists"
        )
        
    customer = Customer(**customer_in.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.get("/search", response_model=CustomerResponse)
def search_customer_by_phone(
    phone: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search for exact phone match (deprecated - use /autocomplete instead)."""
    customer = db.query(Customer).filter(
        Customer.phone == phone,
        Customer.deleted_at.is_(None)
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@router.get("/autocomplete", response_model=CustomerListResponse)
def autocomplete_customers(
    q: str = Query(..., min_length=2, description="Search query (name or phone)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fast autocomplete search across ALL customers by name or phone.

    Designed for POS customer selection - searches entire database,
    not limited to current page. Returns top matches sorted by relevance.

    Args:
        q: Search query (partial name or phone)
        limit: Maximum results (default 10)

    Returns:
        CustomerListResponse with matching customers
    """
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))

    # Search by name OR phone
    search_filter = or_(
        Customer.first_name.ilike(f"%{q}%"),
        Customer.last_name.ilike(f"%{q}%"),
        Customer.phone.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)

    # Order by most recent first (likely to be searched again)
    query = query.order_by(Customer.last_visit_at.desc().nullslast())

    # Limit results for autocomplete
    items = query.limit(limit).all()

    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "size": limit,
        "pages": 1
    }

@router.get("/{id}", response_model=CustomerResponse)
def get_customer(
    id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.id == id,
        Customer.deleted_at.is_(None)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.patch("/{id}", response_model=CustomerResponse)
def update_customer(
    id: str,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    customer = db.query(Customer).filter(
        Customer.id == id,
        Customer.deleted_at.is_(None)
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    update_data = customer_in.model_dump(exclude_unset=True)
    
    if "phone" in update_data and update_data["phone"] != customer.phone:
        existing = db.query(Customer).filter(
            Customer.phone == update_data["phone"],
            Customer.deleted_at.is_(None),
            Customer.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Customer with this phone number already exists"
            )
            
    for field, value in update_data.items():
        setattr(customer, field, value)
        
    db.commit()
    db.refresh(customer)
    return customer

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    customer = db.query(Customer).filter(
        Customer.id == id,
        Customer.deleted_at.is_(None)
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    customer.soft_delete()
    db.add(customer)
    db.commit()
