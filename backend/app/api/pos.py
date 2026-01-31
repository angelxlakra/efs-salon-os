"""POS API endpoints for billing operations.

This module provides REST API endpoints for:
- Creating bills
- Adding payments
- Viewing bills and receipts
- Processing refunds
- Listing bills with filters
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.billing import Bill, BillStatus
from app.services.billing_service import BillingService
from app.services.idempotency_service import IdempotencyService
from app.services.export_service import ExportService
from app.schemas.billing import (
    BillCreate,
    BillResponse,
    PaymentCreate,
    PaymentResponseWithBill,
    VoidCreate,
    RefundCreate,
    RefundResponse,
    BillListResponse,
    BillListItem
)
from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_current_user
from app.auth.permissions import PermissionChecker
from fastapi.responses import Response
from app.services.receipt_service import ReceiptService


router = APIRouter(prefix="/pos", tags=["POS"])


@router.post(
    "/bills",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bill"
)
def create_bill(
    bill_data: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create a new bill in draft status.

    Creates a bill with line items, calculates tax, applies discount,
    and rounds to nearest rupee. Bill starts in 'draft' status.

    **Permissions**: Receptionist or Owner

    **Idempotency**: Include 'Idempotency-Key' header to prevent duplicates.
    If same key is used twice within 24 hours, returns existing bill.

    **Discount Limits**:
    - Receptionist: Max ₹500
    - Owner: No limit

    Args:
        bill_data: Bill creation data with items, customer info, discount.
        db: Database session.
        current_user: Authenticated user.
        idempotency_key: Optional idempotency key for duplicate prevention.

    Returns:
        BillResponse: Created bill in draft status.

    Raises:
        400: Invalid data (bad service ID, discount too high, etc.)
        403: Insufficient permissions (receptionist discount > ₹500)
        409: Idempotency key conflict (returns existing bill)
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create bills"
        )

    # Check idempotency
    if idempotency_key:
        idempotency_service = IdempotencyService()
        existing_bill_id = idempotency_service.check_key(idempotency_key)

        if existing_bill_id:
            # Return existing bill
            existing_bill = db.query(Bill).filter(Bill.id == existing_bill_id).first()
            if existing_bill:
                return BillResponse.model_validate(existing_bill)

    # Validate discount limit for receptionist
    limit = settings.receptionist_discount_limit
    if limit != -1:
        if current_user.is_receptionist and bill_data.discount_amount > limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"""
                    Receptionists can only apply discounts up to ₹{limit}.
                    Please ask owner for approval.
                """
            )

    # Create bill
    billing_service = BillingService(db)

    try:
        # Convert items to dict format
        items_dict = [item.model_dump() for item in bill_data.items]

        bill = billing_service.create_bill(
            items=items_dict,
            created_by_id=current_user.id,
            customer_id=bill_data.customer_id,
            customer_name=bill_data.customer_name,
            customer_phone=bill_data.customer_phone,
            discount_amount=bill_data.discount_amount,
            discount_reason=bill_data.discount_reason,
            session_id=bill_data.session_id
        )

        # Store idempotency key
        if idempotency_key:
            idempotency_service.store_key(idempotency_key, bill.id)

        return BillResponse.model_validate(bill)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/bills/{bill_id}/payments",
    response_model=PaymentResponseWithBill,
    status_code=status.HTTP_200_OK,
    summary="Add payment to bill"
)
def add_payment(
    bill_id: str,
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add payment to a draft bill.

    Records a payment and automatically posts the bill when fully paid.
    When posted, generates invoice number and updates customer stats.

    **Permissions**: Receptionist or Owner

    **Split Payments**: Multiple payments can be added to same bill.

    Args:
        bill_id: ID of the bill to pay.
        payment_data: Payment details (method, amount, reference).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        PaymentResponseWithBill: Payment details + bill status + invoice number.

    Raises:
        400: Invalid data or overpayment.
        403: Insufficient permissions.
        404: Bill not found.
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to add payments"
        )

    billing_service = BillingService(db)

    try:
        payment = billing_service.add_payment(
            bill_id=bill_id,
            payment_method=payment_data.method,
            amount=int(round(payment_data.amount)),  # Round to nearest rupee before int conversion
            confirmed_by_id=current_user.id,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes
        )

        # Get updated bill
        bill = billing_service.get_bill(bill_id)

        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found"
            )

        # Return payment with bill status
        return PaymentResponseWithBill(
            id=payment.id,
            bill_id=payment.bill_id,
            payment_method=payment.payment_method,
            amount=payment.amount,
            reference_number=payment.reference_number,
            notes=payment.notes,
            confirmed_at=payment.confirmed_at,
            confirmed_by=payment.confirmed_by,
            bill_status=bill.status,
            invoice_number=bill.invoice_number
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/bills/{bill_id}",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bill details"
)
def get_bill(
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete bill details including items and payments.

    **Permissions**: Receptionist or Owner

    Args:
        bill_id: Bill ID to retrieve.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Complete bill details.

    Raises:
        403: Insufficient permissions.
        404: Bill not found.
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view bills"
        )

    billing_service = BillingService(db)
    bill = billing_service.get_bill(bill_id)

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill not found: {bill_id}"
        )

    return BillResponse.model_validate(bill)


@router.get(
    "/bills/{bill_id}/receipt",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Get bill receipt PDF"
)
def get_bill_receipt(
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and stream PDF receipt for a bill.

    **Permissions**: Receptionist or Owner

    Args:
        bill_id: Bill ID to get receipt for.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Response: PDF file stream with 'application/pdf' content type.

    Raises:
        403: Insufficient permissions.
        404: Bill not found.
    """
    # Check permissions (read access is enough)
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view receipts"
        )

    billing_service = BillingService(db)
    bill = billing_service.get_bill(bill_id)

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill not found: {bill_id}"
        )

    pdf_buffer = ReceiptService.generate_receipt_pdf(bill, db)

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="receipt_{bill.invoice_number or "draft"}.pdf"'
        }
    )


@router.post(
    "/bills/{bill_id}/void",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Void a draft bill"
)
def void_bill(
    bill_id: str,
    void_data: VoidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Void a draft bill.

    Voids a bill that hasn't been posted yet. Used for cancellations
    or mistakes. Only draft bills can be voided.

    **Permissions**: Owner or Receptionist

    Args:
        bill_id: ID of bill to void.
        void_data: Void reason (optional).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Voided bill.

    Raises:
        403: Insufficient permissions.
        404: Bill not found.
        400: Bill is not in draft status.
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to void bills"
        )

    billing_service = BillingService(db)

    try:
        voided_bill = billing_service.void_bill(
            bill_id=bill_id,
            voided_by_id=current_user.id,
            reason=void_data.reason
        )

        return BillResponse.model_validate(voided_bill)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/bills/{bill_id}/refund",
    response_model=RefundResponse,
    status_code=status.HTTP_200_OK,
    summary="Refund a posted bill"
)
def refund_bill(
    bill_id: str,
    refund_data: RefundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create refund for a posted bill.

    Creates a negative bill linked to original, updates original status
    to 'refunded', and decrements customer stats.

    **Permissions**: Owner only

    Args:
        bill_id: ID of bill to refund.
        refund_data: Refund reason and notes.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        RefundResponse: Refund bill details.

    Raises:
        400: Bill not posted or already refunded.
        403: Insufficient permissions (not owner).
        404: Bill not found.
    """
    # Check permissions - OWNER ONLY
    if not current_user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can process refunds"
        )

    billing_service = BillingService(db)

    try:
        refund_bill = billing_service.refund_bill(
            bill_id=bill_id,
            reason=refund_data.reason,
            refunded_by_id=current_user.id,
            notes=refund_data.notes
        )

        # Get original bill
        original_bill = billing_service.get_bill(bill_id)

        return RefundResponse(
            refund_bill_id=refund_bill.id,
            original_bill_id=bill_id,
            original_invoice_number=original_bill.invoice_number,
            refund_invoice_number=refund_bill.invoice_number,
            refund_amount=refund_bill.rounded_total,
            status=refund_bill.status,
            refunded_at=refund_bill.refunded_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/bills",
    response_model=BillListResponse,
    status_code=status.HTTP_200_OK,
    summary="List bills with filters"
)
def list_bills(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    customer_id: Optional[str] = None,
    invoice_number: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List bills with optional filters and pagination.

    **Permissions**: Receptionist or Owner

    **Filters**:
    - status: Filter by bill status (draft, posted, refunded)
    - from_date: Start date (ISO format: 2025-10-01)
    - to_date: End date (ISO format: 2025-10-31)
    - customer_id: Filter by customer
    - invoice_number: Search by invoice number (exact match)

    **Pagination**:
    - page: Page number (default: 1)
    - limit: Items per page (default: 50, max: 100)

    Args:
        status: Optional bill status filter.
        from_date: Optional start date filter.
        to_date: Optional end date filter.
        customer_id: Optional customer filter.
        invoice_number: Optional invoice number search.
        page: Page number.
        limit: Items per page.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillListResponse: Paginated list of bills.

    Raises:
        403: Insufficient permissions.
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list bills"
        )

    # Validate limit
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 50

    # Build query
    query = db.query(Bill)

    # Apply filters
    if status:
        try:
            bill_status = BillStatus(status)
            query = query.filter(Bill.status == bill_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    if from_date:
        query = query.filter(Bill.created_at >= from_date)

    if to_date:
        query = query.filter(Bill.created_at <= to_date)

    if customer_id:
        query = query.filter(Bill.customer_id == customer_id)

    if invoice_number:
        query = query.filter(Bill.invoice_number == invoice_number)

    # Get total count
    total = query.count()

    # Calculate pagination
    total_pages = math.ceil(total / limit)
    offset = (page - 1) * limit

    # Get paginated results
    bills = query.order_by(Bill.created_at.desc()).offset(offset).limit(limit).all()

    # Convert to response format
    bill_items = [BillListItem.model_validate(bill) for bill in bills]

    return BillListResponse(
        bills=bill_items,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages
        }
    )


@router.get(
    "/bills/export",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Export bills to CSV or PDF"
)
def export_bills(
    format: str = "csv",
    status_filter: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export bills to CSV or PDF format.

    **Permissions**: Receptionist or Owner

    **Formats**:
    - csv: Comma-separated values (for Excel)
    - pdf: PDF document with formatted table

    **Filters**:
    - status: Filter by bill status (draft, posted, void, refunded)
    - from_date: Start date (ISO format: 2025-10-01)
    - to_date: End date (ISO format: 2025-10-31)
    - customer_id: Filter by customer

    Args:
        format: Export format (csv or pdf)
        status_filter: Optional bill status filter
        from_date: Optional start date filter
        to_date: Optional end date filter
        customer_id: Optional customer filter
        db: Database session
        current_user: Authenticated user

    Returns:
        Response: File download (CSV or PDF)

    Raises:
        403: Insufficient permissions
        400: Invalid format
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to export bills"
        )

    # Validate format
    if format not in ["csv", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be 'csv' or 'pdf'"
        )

    # Build query (same as list_bills but without pagination)
    query = db.query(Bill)

    # Apply filters
    if status_filter:
        try:
            bill_status = BillStatus(status_filter)
            query = query.filter(Bill.status == bill_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    if from_date:
        query = query.filter(Bill.created_at >= from_date)

    if to_date:
        query = query.filter(Bill.created_at <= to_date)

    if customer_id:
        query = query.filter(Bill.customer_id == customer_id)

    # Get all matching bills (no pagination for export)
    bills = query.order_by(Bill.created_at.desc()).all()

    if not bills:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bills found matching the criteria"
        )

    # Generate export based on format
    if format == "csv":
        csv_content = ExportService.export_bills_to_csv(bills)

        # Build filename
        filename = f"bills_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    else:  # pdf
        # Build date range string for PDF title
        date_range = None
        if from_date or to_date:
            date_range = f"From {from_date or 'start'} to {to_date or 'now'}"

        pdf_content = ExportService.export_bills_to_pdf(
            bills,
            salon_name="SalonOS",  # TODO: Get from settings
            date_range=date_range
        )

        # Build filename
        filename = f"bills_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
