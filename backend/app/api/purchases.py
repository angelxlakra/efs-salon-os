"""Purchase management API endpoints."""

from datetime import datetime, date
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.purchase import PurchaseInvoice, PurchaseItem, SupplierPayment, PurchaseStatus
from app.models.inventory import Supplier, SKU, StockLedger, InventoryCategory
from app.schemas.purchase import (
    SupplierCreate, SupplierUpdate, SupplierResponse, SupplierListResponse, SupplierListItem,
    PurchaseInvoiceCreate, PurchaseInvoiceUpdate, PurchaseInvoiceResponse,
    PurchaseInvoiceListResponse, PurchaseInvoiceListItem,
    SupplierPaymentCreate, SupplierPaymentResponse, SupplierPaymentListResponse,
    GoodsReceiptRequest, BarcodeSearchRequest, BarcodeSearchResponse,
)
from app.utils import generate_ulid


router = APIRouter()


# ============ Supplier Endpoints ============

@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier_data: SupplierCreate,
    current_user: User = Depends(require_permission("purchases", "create")),
    db: Session = Depends(get_db)
):
    """Create a new supplier. Owner only."""
    supplier = Supplier(
        id=generate_ulid(),
        **supplier_data.model_dump()
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/suppliers", response_model=SupplierListResponse)
def list_suppliers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """List all suppliers with pagination."""
    query = db.query(Supplier)

    if active_only:
        query = query.filter(Supplier.is_active == True)

    if search:
        query = query.filter(
            or_(
                Supplier.name.ilike(f"%{search}%"),
                Supplier.contact_person.ilike(f"%{search}%"),
                Supplier.phone.ilike(f"%{search}%")
            )
        )

    total = query.count()
    offset = (page - 1) * size
    suppliers = query.order_by(Supplier.name).offset(offset).limit(size).all()

    pages = (total + size - 1) // size if total > 0 else 0

    return SupplierListResponse(
        items=[SupplierListItem.model_validate(s) for s in suppliers],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: str,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """Get supplier by ID."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: str,
    supplier_data: SupplierUpdate,
    current_user: User = Depends(require_permission("purchases", "update")),
    db: Session = Depends(get_db)
):
    """Update supplier details. Owner only."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    for field, value in supplier_data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier


# ============ Purchase Invoice Endpoints ============

@router.post("/invoices", response_model=PurchaseInvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_invoice(
    invoice_data: PurchaseInvoiceCreate,
    current_user: User = Depends(require_permission("purchases", "create")),
    db: Session = Depends(get_db)
):
    """Create a new purchase invoice. Owner/Receptionist."""
    # Verify supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == invoice_data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Create invoice record first
    invoice_id = generate_ulid()
    invoice = PurchaseInvoice(
        id=invoice_id,
        supplier_id=invoice_data.supplier_id,
        invoice_number=invoice_data.invoice_number,
        invoice_date=invoice_data.invoice_date,
        due_date=invoice_data.due_date,
        notes=invoice_data.notes,
        invoice_file_url=invoice_data.invoice_file_url,
        status=PurchaseStatus.DRAFT,
        created_by=current_user.id
    )

    # Create line items
    for item_data in invoice_data.items:
        sku_id = item_data.sku_id
        barcode = item_data.barcode
        
        # If no sku_id but has barcode, try to find or create SKU
        if not sku_id and barcode:
            sku = db.query(SKU).filter(SKU.barcode == barcode).first()
            if not sku:
                # Create default category if not exists
                category = db.query(InventoryCategory).filter(InventoryCategory.name == "General").first()
                if not category:
                    category = InventoryCategory(
                        id=generate_ulid(), 
                        name="General",
                        description="Default category for automatically created SKUs"
                    )
                    db.add(category)
                    db.flush()
                
                # Check if we should use barcode as SKU code or generate one
                # SKU code is unique, so we use barcode if it's not already used as a code
                sku_code = barcode
                existing_sku_by_code = db.query(SKU).filter(SKU.sku_code == sku_code).first()
                if existing_sku_by_code:
                    sku_code = f"AUTO-{barcode}"
                
                # Create SKU
                sku = SKU(
                    id=generate_ulid(),
                    category_id=category.id,
                    supplier_id=invoice_data.supplier_id,
                    sku_code=sku_code,
                    name=item_data.product_name,
                    barcode=barcode,
                    uom=item_data.uom,
                    avg_cost_per_unit=item_data.unit_cost,
                    current_stock=0,
                    is_active=True
                )
                db.add(sku)
                db.flush()
            
            sku_id = sku.id

        item = PurchaseItem(
            id=generate_ulid(),
            purchase_invoice_id=invoice.id,
            sku_id=sku_id,
            product_name=item_data.product_name,
            barcode=item_data.barcode,
            uom=item_data.uom,
            quantity=item_data.quantity,
            unit_cost=item_data.unit_cost
        )
        item.calculate_total()
        invoice.items.append(item)

    # Calculate totals
    invoice.calculate_totals()

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Add supplier name to response
    response = PurchaseInvoiceResponse.model_validate(invoice)
    response.supplier_name = supplier.name
    return response


@router.get("/invoices", response_model=PurchaseInvoiceListResponse)
def list_purchase_invoices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[str] = None,
    status_filter: Optional[PurchaseStatus] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """List purchase invoices with filters."""
    query = db.query(PurchaseInvoice)

    if supplier_id:
        query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
    if status_filter:
        query = query.filter(PurchaseInvoice.status == status_filter)
    if start_date:
        query = query.filter(PurchaseInvoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(PurchaseInvoice.invoice_date <= end_date)

    total = query.count()
    offset = (page - 1) * size
    invoices = query.order_by(PurchaseInvoice.invoice_date.desc()).offset(offset).limit(size).all()

    pages = (total + size - 1) // size if total > 0 else 0

    items = []
    for inv in invoices:
        item = PurchaseInvoiceListItem(
            id=inv.id,
            supplier_id=inv.supplier_id,
            supplier_name=inv.supplier.name if inv.supplier else "Unknown",
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            total_amount=inv.total_amount,
            paid_amount=inv.paid_amount or 0,
            balance_due=inv.balance_due,
            status=inv.status,
            created_at=inv.created_at,
        )
        items.append(item)

    return PurchaseInvoiceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/invoices/{invoice_id}", response_model=PurchaseInvoiceResponse)
def get_purchase_invoice(
    invoice_id: str,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """Get purchase invoice by ID."""
    invoice = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")

    response = PurchaseInvoiceResponse.model_validate(invoice)
    response.supplier_name = invoice.supplier.name if invoice.supplier else "Unknown"
    return response


@router.patch("/invoices/{invoice_id}", response_model=PurchaseInvoiceResponse)
def update_purchase_invoice(
    invoice_id: str,
    invoice_data: PurchaseInvoiceUpdate,
    current_user: User = Depends(require_permission("purchases", "update")),
    db: Session = Depends(get_db)
):
    """Update purchase invoice (draft only). Owner/Receptionist."""
    invoice = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")

    if invoice.status != PurchaseStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Can only update draft invoices"
        )

    # Update basic fields
    for field in ["invoice_number", "invoice_date", "due_date", "notes", "invoice_file_url"]:
        value = getattr(invoice_data, field, None)
        if value is not None:
            setattr(invoice, field, value)

    # Update items if provided
    if invoice_data.items is not None:
        # Delete existing items
        for item in invoice.items:
            db.delete(item)

        # Clear existing items collection to ensure fresh start
        invoice.items = []

        # Create new items
        for item_data in invoice_data.items:
            sku_id = item_data.sku_id
            barcode = item_data.barcode
            
            # If no sku_id but has barcode, try to find or create SKU
            if not sku_id and barcode:
                sku = db.query(SKU).filter(SKU.barcode == barcode).first()
                if not sku:
                    # Create default category if not exists
                    category = db.query(InventoryCategory).filter(InventoryCategory.name == "General").first()
                    if not category:
                        category = InventoryCategory(
                            id=generate_ulid(), 
                            name="General",
                            description="Default category for automatically created SKUs"
                        )
                        db.add(category)
                        db.flush()
                    
                    # Create SKU
                    sku_code = barcode
                    existing_sku_by_code = db.query(SKU).filter(SKU.sku_code == sku_code).first()
                    if existing_sku_by_code:
                        sku_code = f"AUTO-{barcode}"

                    sku = SKU(
                        id=generate_ulid(),
                        category_id=category.id,
                        supplier_id=invoice.supplier_id,
                        sku_code=sku_code,
                        name=item_data.product_name,
                        barcode=barcode,
                        uom=item_data.uom,
                        avg_cost_per_unit=item_data.unit_cost,
                        current_stock=0,
                        is_active=True
                    )
                    db.add(sku)
                    db.flush()
                
                sku_id = sku.id

            item = PurchaseItem(
                id=generate_ulid(),
                purchase_invoice_id=invoice.id,
                sku_id=sku_id,
                product_name=item_data.product_name,
                barcode=item_data.barcode,
                uom=item_data.uom,
                quantity=item_data.quantity,
                unit_cost=item_data.unit_cost
            )
            item.calculate_total()
            invoice.items.append(item)

        # Recalculate totals
        invoice.calculate_totals()

    db.commit()
    db.refresh(invoice)

    response = PurchaseInvoiceResponse.model_validate(invoice)
    response.supplier_name = invoice.supplier.name if invoice.supplier else "Unknown"
    return response


@router.post("/invoices/{invoice_id}/receive", response_model=PurchaseInvoiceResponse)
def mark_goods_received(
    invoice_id: str,
    receipt_data: GoodsReceiptRequest,
    current_user: User = Depends(require_permission("purchases", "update")),
    db: Session = Depends(get_db)
):
    """
    Mark goods as received and update inventory.

    This will:
    1. Update inventory stock levels
    2. Update avg_cost_per_unit (weighted average)
    3. Create stock ledger entries
    4. Mark invoice as RECEIVED
    """
    invoice = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")

    if invoice.status != PurchaseStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Invoice already received")

    received_at = receipt_data.received_at or datetime.utcnow()

    # Process each item
    for item in invoice.items:
        sku_id = item.sku_id
        
        # Safety check: if no sku_id but has barcode, try to link it now
        if not sku_id and item.barcode:
            sku = db.query(SKU).filter(SKU.barcode == item.barcode).first()
            if not sku:
                # Create default category if not exists
                category = db.query(InventoryCategory).filter(InventoryCategory.name == "General").first()
                if not category:
                    category = InventoryCategory(
                        id=generate_ulid(), 
                        name="General",
                        description="Default category for automatically created SKUs"
                    )
                    db.add(category)
                    db.flush()
                
                # Create SKU
                sku_code = item.barcode
                existing_sku_by_code = db.query(SKU).filter(SKU.sku_code == sku_code).first()
                if existing_sku_by_code:
                    sku_code = f"AUTO-{item.barcode}"
                
                sku = SKU(
                    id=generate_ulid(),
                    category_id=category.id,
                    supplier_id=invoice.supplier_id,
                    sku_code=sku_code,
                    name=item.product_name,
                    barcode=item.barcode,
                    uom=item.uom,
                    avg_cost_per_unit=item.unit_cost,
                    current_stock=0,
                    is_active=True
                )
                db.add(sku)
                db.flush()
            
            # Update item with the SKU link
            item.sku_id = sku.id
            sku_id = sku.id

        if sku_id:
            # Update existing SKU
            sku = db.query(SKU).filter(SKU.id == sku_id).first()
            if sku:
                # Update barcode if provided and not already set
                if item.barcode and not sku.barcode:
                    sku.barcode = item.barcode

                # Calculate new weighted average cost
                old_value = int(Decimal(str(sku.current_stock)) * sku.avg_cost_per_unit)
                new_value = item.total_cost
                new_quantity = sku.current_stock + item.quantity

                if new_quantity > 0:
                    sku.avg_cost_per_unit = int((old_value + new_value) / Decimal(str(new_quantity)))

                # Update stock
                sku.current_stock += item.quantity

                # Create stock ledger entry
                ledger = StockLedger(
                    id=generate_ulid(),
                    sku_id=sku.id,
                    transaction_type="receive",
                    quantity_change=item.quantity,
                    quantity_after=sku.current_stock,
                    unit_cost=item.unit_cost,
                    total_value=item.total_cost,
                    avg_cost_after=sku.avg_cost_per_unit,
                    reference_type="purchase",
                    reference_id=invoice.id,
                    created_by=current_user.id,
                    notes=f"Purchase from {invoice.supplier.name}, Invoice: {invoice.invoice_number}"
                )
                db.add(ledger)

    # Update invoice status
    invoice.received_at = received_at
    invoice.received_by = current_user.id
    invoice.update_status()

    db.commit()
    db.refresh(invoice)

    response = PurchaseInvoiceResponse.model_validate(invoice)
    response.supplier_name = invoice.supplier.name if invoice.supplier else "Unknown"
    return response


# ============ Supplier Payment Endpoints ============

@router.post("/payments", response_model=SupplierPaymentResponse, status_code=status.HTTP_201_CREATED)
def record_supplier_payment(
    payment_data: SupplierPaymentCreate,
    current_user: User = Depends(require_permission("purchases", "create")),
    db: Session = Depends(get_db)
):
    """
    Record a payment to supplier.

    Payment can be linked to specific invoice or be a general payment.
    Updates invoice balance and status automatically.
    """
    # Verify supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == payment_data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # If payment is for specific invoice, verify it exists
    invoice = None
    if payment_data.purchase_invoice_id:
        invoice = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.id == payment_data.purchase_invoice_id
        ).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Purchase invoice not found")

        if invoice.balance_due <= 0:
            raise HTTPException(status_code=400, detail="Invoice already fully paid")

        if payment_data.amount > invoice.balance_due:
            raise HTTPException(
                status_code=400,
                detail=f"Payment amount exceeds balance due (₹{invoice.balance_due / 100:.2f})"
            )

    # Create payment record
    payment = SupplierPayment(
        id=generate_ulid(),
        **payment_data.model_dump(),
        recorded_by=current_user.id,
        recorded_at=datetime.utcnow()
    )
    db.add(payment)

    # Update invoice if payment is linked
    if invoice:
        invoice.paid_amount += payment_data.amount
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        invoice.update_status()

    db.commit()
    db.refresh(payment)

    # Build response with additional details
    response = SupplierPaymentResponse.model_validate(payment)
    response.supplier_name = supplier.name
    if invoice:
        response.invoice_number = invoice.invoice_number

    return response


@router.get("/payments", response_model=SupplierPaymentListResponse)
def list_supplier_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """List supplier payments with filters."""
    query = db.query(SupplierPayment)

    if supplier_id:
        query = query.filter(SupplierPayment.supplier_id == supplier_id)
    if invoice_id:
        query = query.filter(SupplierPayment.purchase_invoice_id == invoice_id)
    if start_date:
        query = query.filter(SupplierPayment.payment_date >= start_date)
    if end_date:
        query = query.filter(SupplierPayment.payment_date <= end_date)

    total = query.count()
    offset = (page - 1) * size
    payments = query.order_by(SupplierPayment.payment_date.desc()).offset(offset).limit(size).all()

    pages = (total + size - 1) // size if total > 0 else 0

    items = []
    for pmt in payments:
        item = SupplierPaymentResponse.model_validate(pmt)
        item.supplier_name = pmt.supplier.name if pmt.supplier else "Unknown"
        if pmt.invoice:
            item.invoice_number = pmt.invoice.invoice_number
        items.append(item)

    return SupplierPaymentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


# ============ Barcode Lookup Endpoint ============

@router.post("/barcode-search", response_model=BarcodeSearchResponse)
def search_by_barcode(
    search_data: BarcodeSearchRequest,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db)
):
    """
    Search for product by barcode.

    Returns existing SKU if found, or looks up recent purchase items if not in SKU catalog.
    Used for quick product lookup when creating purchase invoices.
    """
    # First, try to find in SKU table
    sku = db.query(SKU).filter(SKU.barcode == search_data.barcode).first()

    if sku:
        return BarcodeSearchResponse(
            found=True,
            sku_id=sku.id,
            product_name=sku.name,
            barcode=sku.barcode,
            avg_cost_per_unit=sku.avg_cost_per_unit,
            uom=sku.uom.value,
            current_stock=sku.current_stock
        )

    # If not in SKU, look up in recent purchase items
    purchase_item = (
        db.query(PurchaseItem)
        .filter(PurchaseItem.barcode == search_data.barcode)
        .order_by(PurchaseItem.created_at.desc())
        .first()
    )

    if purchase_item:
        return BarcodeSearchResponse(
            found=True,
            sku_id=purchase_item.sku_id,  # May be None
            product_name=purchase_item.product_name,
            barcode=purchase_item.barcode,
            avg_cost_per_unit=purchase_item.unit_cost,
            uom=purchase_item.uom,
            current_stock=None  # Not tracked in purchase items
        )

    return BarcodeSearchResponse(found=False)
