from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db

from app.models.inventory import (
    SKU, Supplier, InventoryCategory, InventoryChangeRequest, StockLedger,
    ChangeType, ChangeStatus, UOMEnum
)
from app.models.inventory_transfer import InventoryTransfer
from app.models.user import User
from app.schemas.inventory import (
    SKUCreate, SKUUpdate, SKUResponse, SKUListResponse,
    SupplierCreate, SupplierUpdate, SupplierResponse,
    CategoryCreate, CategoryResponse,
    ChangeRequestCreate, ChangeRequestResponse,
    LedgerEntryResponse
)
from app.utils import generate_ulid, IST

from app.auth.dependencies import get_current_user, require_owner, require_owner_or_receptionist


# ---------------------------------------------------------------------------
# Transfer schemas (inline — only used by these 2 endpoints)
# ---------------------------------------------------------------------------

class TransferInitiateRequest(BaseModel):
    sku_id: str
    destination_store_id: str
    destination_store_name: str
    quantity: int
    notes: Optional[str] = None

class TransferResponse(BaseModel):
    id: str
    central_transfer_id: Optional[str]
    direction: str
    other_store_name: str
    sku_id: Optional[str]
    product_name: str
    product_sku: Optional[str]
    quantity: int
    unit_cost_paise: int
    total_cost_paise: int
    expense_id: Optional[str]
    status: str
    initiated_at: Optional[datetime]
    applied_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True

class TransferListResponse(BaseModel):
    transfers: List[TransferResponse]
    total: int
    page: int
    size: int

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# --- Suppliers ---

@router.get("/suppliers", response_model=List[SupplierResponse])
def list_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).offset(skip).limit(limit).all()
    return suppliers

@router.post("/suppliers", response_model=SupplierResponse)
def create_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner) # Only owner can manage master data? 
    # Prompt said "Create SKU (owner only)", implicit for master data too probably.
):
    supplier = Supplier(
        id=generate_ulid(),
        **supplier_in.dict()
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: str,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier

# --- Categories ---

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categories = db.query(InventoryCategory).offset(skip).limit(limit).all()
    return categories

@router.post("/categories", response_model=CategoryResponse)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    category = InventoryCategory(
        id=generate_ulid(),
        **category_in.dict()
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

# --- SKUs ---

@router.get("/skus", response_model=SKUListResponse)
def list_skus(
    page: int = 1,
    size: int = 20,
    category_id: Optional[str] = None,
    low_stock: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SKU)
    
    if category_id:
        query = query.filter(SKU.category_id == category_id)
    
    if low_stock:
        # SKU.current_stock <= SKU.reorder_point
        query = query.filter(SKU.current_stock <= SKU.reorder_point)
    
    if search:
        query = query.filter(SKU.name.ilike(f"%{search}%") | SKU.sku_code.ilike(f"%{search}%")) 

    total = query.count()
    skus = query.offset((page - 1) * size).limit(size).all()
    
    # Enrich with names (though relationships should handle this if configured in Pydantic with ORM)
    response_items = []
    for sku in skus:
        resp = SKUResponse.from_orm(sku)
        resp.category_name = sku.category.name if sku.category else None
        resp.supplier_name = sku.supplier.name if sku.supplier else None
        response_items.append(resp)

    return SKUListResponse(
        items=response_items,
        total=total,
        page=page,
        size=size
    )

@router.post("/skus", response_model=SKUResponse)
def create_sku(
    sku_in: SKUCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    # Check duplicate SKU code
    if db.query(SKU).filter(SKU.sku_code == sku_in.sku_code).first():
        raise HTTPException(status_code=400, detail="SKU code already exists")

    sku = SKU(
        id=generate_ulid(),
        **sku_in.dict()
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
    return sku

@router.get("/skus/{sku_id}", response_model=SKUResponse)
def get_sku(
    sku_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sku = db.query(SKU).filter(SKU.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    resp = SKUResponse.from_orm(sku)
    resp.category_name = sku.category.name if sku.category else None
    resp.supplier_name = sku.supplier.name if sku.supplier else None
    return resp

@router.patch("/skus/{sku_id}", response_model=SKUResponse)
def update_sku(
    sku_id: str,
    sku_in: SKUUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    sku = db.query(SKU).filter(SKU.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    if sku_in.sku_code and sku_in.sku_code != sku.sku_code:
        if db.query(SKU).filter(SKU.sku_code == sku_in.sku_code).first():
            raise HTTPException(status_code=400, detail="SKU code already exists")

    if sku_in.barcode is not None and sku_in.barcode != sku.barcode:
        if sku_in.barcode and db.query(SKU).filter(SKU.barcode == sku_in.barcode, SKU.id != sku_id).first():
            raise HTTPException(status_code=400, detail="Barcode already assigned to another SKU")

    update_data = sku_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sku, field, value)
    
    db.commit()
    db.refresh(sku)
    return sku

# --- Change Requests ---

@router.post("/change-requests", response_model=ChangeRequestResponse)
def create_change_request(
    request_in: ChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    sku = db.query(SKU).filter(SKU.id == request_in.sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    if request_in.change_type == ChangeType.RECEIVE and request_in.unit_cost is None:
        raise HTTPException(status_code=400, detail="Unit cost is required for receiving stock")

    change_req = InventoryChangeRequest(
        id=generate_ulid(),
        sku_id=request_in.sku_id,
        change_type=request_in.change_type,
        quantity=request_in.quantity,
        unit_cost=request_in.unit_cost,
        reason_code=request_in.reason_code,
        notes=request_in.notes,
        status=ChangeStatus.PENDING,
        requested_by=current_user.id,
        requested_at=datetime.now(IST)
    )
    db.add(change_req)
    db.commit()
    db.refresh(change_req)
    return change_req

@router.get("/change-requests", response_model=List[ChangeRequestResponse])
def list_change_requests(
    status: Optional[ChangeStatus] = None,
    sku_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    query = db.query(InventoryChangeRequest)
    
    if status:
        query = query.filter(InventoryChangeRequest.status == status)
    
    if sku_id:
        query = query.filter(InventoryChangeRequest.sku_id == sku_id)
        
    requests = query.order_by(InventoryChangeRequest.requested_at.desc()).all()
    
    # Enrich
    response_items = []
    for req in requests:
        resp = ChangeRequestResponse.from_orm(req)
        resp.sku_code = req.sku.sku_code if req.sku else None
        resp.sku_name = req.sku.name if req.sku else None
        # resp.requester_name = req.requester.full_name if req.requester else None # Assuming user has full_name
        response_items.append(resp)
        
    return response_items

@router.post("/change-requests/{request_id}/approve", response_model=ChangeRequestResponse)
def approve_change_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    change_req = db.query(InventoryChangeRequest).filter(InventoryChangeRequest.id == request_id).first()
    if not change_req:
        raise HTTPException(status_code=404, detail="Change request not found")
    
    if change_req.status != ChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {change_req.status}")

    sku = db.query(SKU).filter(SKU.id == change_req.sku_id).with_for_update().first()
    
    # Calculate impacts
    # Calculate impacts
    # Use Decimal for high precision math
    from decimal import Decimal
    
    qty_change = Decimal(0)
    total_val_change = 0
    new_avg_cost = sku.avg_cost_per_unit
    final_unit_cost = None  # For RECEIVE type, will be calculated after discounts

    if change_req.change_type == ChangeType.RECEIVE:
        qty_change = change_req.quantity

        # Calculate final unit cost after supplier discounts
        base_unit_cost = change_req.unit_cost or 0
        final_unit_cost = base_unit_cost

        # Apply percentage discount if provided
        if change_req.supplier_discount_percent and change_req.supplier_discount_percent > 0:
            discount_amount = int(base_unit_cost * float(change_req.supplier_discount_percent) / 100)
            final_unit_cost = base_unit_cost - discount_amount

        # Apply fixed discount if provided (additive)
        if change_req.supplier_discount_fixed and change_req.supplier_discount_fixed > 0:
            final_unit_cost = final_unit_cost - change_req.supplier_discount_fixed

        # Ensure final cost doesn't go negative
        final_unit_cost = max(0, final_unit_cost)

        # unit_cost is int (paise), quantity is Decimal. result is Decimal.
        total_val_change = int(qty_change * final_unit_cost)

        # Recalculate Avg Cost using final discounted cost
        # Current Value + Incoming Value / New Quantity
        current_value = sku.current_stock * sku.avg_cost_per_unit
        in_value = qty_change * final_unit_cost
        new_total_qty = sku.current_stock + qty_change

        if new_total_qty > 0:
            new_avg_cost = int((current_value + in_value) / new_total_qty)
            
    elif change_req.change_type == ChangeType.CONSUME:
        qty_change = -change_req.quantity
        if sku.current_stock + qty_change < 0:
             raise HTTPException(status_code=400, detail="Insufficient stock for consumption")
             
    elif change_req.change_type == ChangeType.ADJUST:
        qty_change = change_req.quantity

    # Update SKU
    sku.current_stock += qty_change
    sku.avg_cost_per_unit = new_avg_cost
    
    # Create Ledger Entry
    # Use final_unit_cost (with discounts) for RECEIVE, otherwise use avg cost
    ledger_unit_cost = final_unit_cost if change_req.change_type == ChangeType.RECEIVE and final_unit_cost is not None else sku.avg_cost_per_unit
    ledger_total_value = int(qty_change * ledger_unit_cost) if ledger_unit_cost else 0

    ledger = StockLedger(
        id=generate_ulid(),
        sku_id=sku.id,
        change_request_id=change_req.id,
        transaction_type=change_req.change_type.value,
        quantity_change=qty_change,
        quantity_after=sku.current_stock,
        unit_cost=ledger_unit_cost,
        total_value=ledger_total_value,
        avg_cost_after=sku.avg_cost_per_unit,
        created_by=current_user.id,
        notes=change_req.notes
    )
    db.add(ledger)
    
    # Update Request
    change_req.status = ChangeStatus.APPROVED
    change_req.reviewed_by = current_user.id
    change_req.reviewed_at = datetime.now(IST)
    
    db.commit()
    db.refresh(change_req)
    return change_req

@router.post("/change-requests/{request_id}/reject", response_model=ChangeRequestResponse)
def reject_change_request(
    request_id: str,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    change_req = db.query(InventoryChangeRequest).filter(InventoryChangeRequest.id == request_id).first()
    if not change_req:
        raise HTTPException(status_code=404, detail="Change request not found")
        
    if change_req.status != ChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {change_req.status}")

    change_req.status = ChangeStatus.REJECTED
    change_req.reviewed_by = current_user.id
    change_req.reviewed_at = datetime.now(IST)
    if notes:
        change_req.review_notes = notes
        
    db.commit()
    db.refresh(change_req)
    return change_req

# --- Ledger ---

@router.get("/ledger/{sku_id}", response_model=List[LedgerEntryResponse])
def get_sku_ledger(
    sku_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    entries = db.query(StockLedger).filter(
        StockLedger.sku_id == sku_id
    ).order_by(
        desc(StockLedger.created_at)
    ).offset(skip).limit(limit).all()

    return entries


# --- Inventory Transfers ---

@router.get("/transfers/available-stores")
def get_available_stores(current_user: User = Depends(get_current_user)):
    """Return list of other stores this store can transfer inventory to.

    When CENTRAL_SYNC_ENABLED=true, fetches live from central API so no
    manual CENTRAL_OTHER_STORES_JSON config is needed. Falls back to that
    env var on any error.
    """
    import json
    from app.config import settings

    if settings.central_sync_enabled and settings.central_api_url:
        try:
            with httpx.Client(
                base_url=settings.central_api_url,
                headers={"X-Store-API-Key": settings.central_api_key},
                timeout=5.0,
            ) as client:
                resp = client.get("/v1/stores/peers")
                resp.raise_for_status()
                return resp.json()
        except Exception:
            pass  # fall through to env var fallback

    try:
        return json.loads(settings.central_other_stores_json)
    except Exception:
        return []


@router.post("/transfers", response_model=TransferResponse, status_code=201)
def initiate_transfer(
    request: TransferInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    """Initiate an outgoing transfer to another store.

    Requires CENTRAL_SYNC_ENABLED=true. Atomically decrements stock,
    creates a TRANSFER_OUT expense, and posts the transfer to central.
    """
    from app.config import settings
    if not settings.central_sync_enabled:
        raise HTTPException(
            status_code=503,
            detail="Inventory transfers require CENTRAL_SYNC_ENABLED=true",
        )

    from app.services.inventory_transfer_service import InventoryTransferService
    service = InventoryTransferService(db)
    try:
        transfer = service.initiate_transfer(
            sku_id=request.sku_id,
            destination_store_id=request.destination_store_id,
            destination_store_name=request.destination_store_name,
            quantity=request.quantity,
            user_id=current_user.id,
            notes=request.notes,
        )
        return transfer
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Central API error: {exc.response.status_code}",
        )
    finally:
        service.close()


@router.get("/transfers", response_model=TransferListResponse)
def list_transfers(
    page: int = 1,
    size: int = 20,
    direction: Optional[str] = None,  # 'IN' or 'OUT'
    transfer_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List this store's transfer history (both IN and OUT)."""
    query = db.query(InventoryTransfer)

    if direction:
        query = query.filter(InventoryTransfer.direction == direction.upper())
    if transfer_status:
        query = query.filter(InventoryTransfer.status == transfer_status.upper())

    total = query.count()
    transfers = (
        query.order_by(desc(InventoryTransfer.initiated_at))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return TransferListResponse(transfers=transfers, total=total, page=page, size=size)


@router.patch("/transfers/{transfer_id}/cancel", response_model=TransferResponse)
def cancel_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    """Cancel a pending outgoing transfer."""
    from app.config import settings
    if not settings.central_sync_enabled:
        raise HTTPException(
            status_code=503,
            detail="Inventory transfers require CENTRAL_SYNC_ENABLED=true",
        )

    from app.services.inventory_transfer_service import InventoryTransferService
    service = InventoryTransferService(db)
    try:
        transfer = service.cancel_transfer(
            local_transfer_id=transfer_id,
            user_id=current_user.id,
        )
        return transfer
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Central API error: {exc.response.status_code}",
        )
    finally:
        service.close()
