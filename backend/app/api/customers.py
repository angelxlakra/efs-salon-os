from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from app.database import get_db
from app.models.customer import Customer
from app.models.billing import Bill, BillItem, BillStatus
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerStatsResponse,
    CustomerBillSummary,
    CustomerBillItemSummary,
    CustomerBillsListResponse,
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/stats", response_model=CustomerStatsResponse)
def get_customer_stats(
    exclude_walkins: bool = Query(False),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Aggregate stats across all customers (not limited to current page)."""
    from datetime import datetime, timezone

    base_q = db.query(Customer).filter(Customer.deleted_at.is_(None))
    if exclude_walkins:
        base_q = base_q.filter(Customer.phone.isnot(None), Customer.phone != '')

    totals = base_q.with_entities(
        func.count(Customer.id).label("total_customers"),
        func.coalesce(func.sum(Customer.total_visits), 0).label("total_visits"),
        func.coalesce(func.sum(Customer.total_spent), 0).label("total_revenue"),
        func.coalesce(func.sum(Customer.pending_balance), 0).label("total_pending"),
    ).one()

    # Active this month = last_visit_at >= start of current month (UTC)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    active_this_month = base_q.filter(Customer.last_visit_at >= month_start).count()

    return {
        "total_customers": totals.total_customers,
        "active_this_month": active_this_month,
        "total_visits": totals.total_visits,
        "total_revenue": totals.total_revenue,
        "total_pending": totals.total_pending,
    }


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    phone: Optional[str] = None,
    exclude_walkins: bool = Query(False, description="Exclude walk-in customers (those without a phone number)"),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))

    if exclude_walkins:
        query = query.filter(Customer.phone.isnot(None), Customer.phone != '')

    if search:
        search_filter = or_(
            Customer.first_name.ilike(f"%{search}%"),
            Customer.last_name.ilike(f"%{search}%"),
            Customer.phone.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    if phone:
        query = query.filter(Customer.phone.ilike(f"%{phone}%"))

    # Order by visit frequency (most frequent first)
    query = query.order_by(Customer.total_visits.desc(), Customer.last_visit_at.desc().nullslast())

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

@router.get("/{id}/bills", response_model=CustomerBillsListResponse)
def get_customer_bills(
    id: str,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist),
):
    """Paginated visit history (POSTED bills) for a specific customer."""
    customer = db.query(Customer).filter(
        Customer.id == id,
        Customer.deleted_at.is_(None),
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    base_q = db.query(Bill).filter(
        Bill.customer_id == id,
        Bill.status == BillStatus.POSTED,
    )
    total = base_q.count()
    pages = (total + size - 1) // size

    bills = (
        base_q
        .options(
            joinedload(Bill.items).joinedload(BillItem.staff),
            joinedload(Bill.items).joinedload(BillItem.staff_contributions),
            joinedload(Bill.payments),
        )
        .order_by(Bill.posted_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    result = []
    for bill in bills:
        items = []
        for item in bill.items:
            has_multi = bool(item.staff_contributions)
            if has_multi:
                staff_name = "Multiple"
            elif item.staff:
                staff_name = item.staff.display_name
            else:
                staff_name = None
            items.append(CustomerBillItemSummary(
                item_name=item.item_name,
                base_price=item.base_price,
                quantity=item.quantity,
                line_total=item.line_total,
                staff_name=staff_name,
                has_multi_staff=has_multi,
            ))
        payment_methods = list({p.payment_method.value for p in bill.payments})
        result.append(CustomerBillSummary(
            id=bill.id,
            invoice_number=bill.invoice_number,
            posted_at=bill.posted_at,
            rounded_total=bill.rounded_total,
            payment_methods=payment_methods,
            items=items,
        ))

    return {"items": result, "total": total, "page": page, "size": size, "pages": pages}


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
