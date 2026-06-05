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

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, status
from sqlalchemy import or_, func, select as sa_select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.billing import Bill, BillStatus, Payment
from app.models.pending_payment import PendingPaymentCollection
from app.services.billing_service import BillingService
from app.services.idempotency_service import IdempotencyService
from app.services.export_service import ExportService
from app.schemas.billing import (
    BillCreate,
    BillResponse,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponseWithBill,
    CompleteBillCreate,
    PendingPaymentCollect,
    PendingPaymentCollectionResponse,
    VoidCreate,
    RefundCreate,
    RefundResponse,
    BillListResponse,
    BillListItem,
    BillAssignCustomer,
    BillDiscountUpdate,
    BillWriteOff,
    AddBillItemRequest,
    AddBillItemResponse,
    BillItemResponse,
)
from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_current_user
from app.auth.permissions import PermissionChecker
from fastapi.responses import Response
from app.services.receipt_service import ReceiptService
from app.utils import IST


router = APIRouter(prefix="/pos", tags=["POS"])


def _push_metrics_background(target_date) -> None:
    """Fire-and-forget metrics push. Creates its own DB session (request session already closed)."""
    from app.database import SessionLocal
    from app.services.central_sync_service import CentralSyncService

    db = SessionLocal()
    try:
        service = CentralSyncService(db)
        try:
            service.push_metrics_snapshot(target_date)
        finally:
            service.close()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Background metrics push failed: %s", exc)
    finally:
        db.close()


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

    # Note: Discount limit removed - receptionists can apply any discount

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
    background_tasks: BackgroundTasks,
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

        # Trigger metrics push when a bill is posted
        if bill.status == BillStatus.POSTED and settings.central_sync_enabled:
            today_ist = datetime.now(IST).date()
            background_tasks.add_task(_push_metrics_background, today_ist)

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


@router.patch(
    "/bills/{bill_id}/payments/{payment_id}",
    response_model=PaymentResponseWithBill,
    status_code=status.HTTP_200_OK,
    summary="Update an existing payment"
)
def update_payment(
    bill_id: str,
    payment_id: str,
    payment_data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing payment on a bill.

    Allows modification of payment method, amount, reference number, and notes.
    Automatically recalculates bill status if amount changes.

    **Permissions**: Receptionist or Owner

    **Restrictions**:
    - Cannot update payments on refunded bills
    - Updated amount cannot cause overpayment

    Args:
        bill_id: ID of the bill (for validation).
        payment_id: ID of the payment to update.
        payment_data: Updated payment details.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        PaymentResponseWithBill: Updated payment + bill status.

    Raises:
        400: Invalid data or would cause overpayment.
        403: Insufficient permissions.
        404: Payment or bill not found.
    """
    # Check permissions - same as add_payment
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to edit payments"
        )

    billing_service = BillingService(db)

    try:
        # Convert amount to paise if provided
        amount_paise = None
        if payment_data.amount is not None:
            amount_paise = int(round(payment_data.amount * 100))

        payment = billing_service.update_payment(
            payment_id=payment_id,
            payment_method=payment_data.method,
            amount=amount_paise,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes,
            updated_by_id=current_user.id
        )

        # Get updated bill
        bill = billing_service.get_bill(bill_id)

        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found"
            )

        # Return payment with updated bill status
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


@router.delete(
    "/bills/{bill_id}/payments/{payment_id}",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a payment"
)
def delete_payment(
    bill_id: str,
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment from a bill.

    Removes the payment and recalculates bill status.
    If bill was posted and becomes underpaid, reverts to draft.

    **Permissions**: Receptionist or Owner

    **Restrictions**:
    - Cannot delete payments from refunded bills
    - Stock and customer stats are not reversed (audit trail preserved)

    Args:
        bill_id: ID of the bill (for validation).
        payment_id: ID of the payment to delete.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Updated bill after payment deletion.

    Raises:
        400: Invalid operation (e.g., refunded bill).
        403: Insufficient permissions.
        404: Payment or bill not found.
    """
    # Check permissions - same as add_payment
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete payments"
        )

    billing_service = BillingService(db)

    try:
        bill = billing_service.delete_payment(
            payment_id=payment_id,
            deleted_by_id=current_user.id
        )

        return BillResponse.model_validate(bill)

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
    "/bills/{bill_id}/complete",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete bill with pending balance"
)
def complete_bill(
    bill_id: str,
    complete_data: CompleteBillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete a bill even with pending balance.

    Allows posting a bill that hasn't been fully paid yet. Generates invoice
    number and marks bill as posted. Useful for:
    - Free services (family members, complimentary services)
    - Credit customers who will pay later
    - Partial payments with pending balance

    **Permissions**: Owner or Receptionist

    **Note**: Customer stats are updated with actual paid amount, not bill total.
    Pending balance is tracked and can be collected later.

    Args:
        bill_id: ID of bill to complete.
        complete_data: Optional notes about pending payment.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Completed bill with invoice number and pending balance info.

    Raises:
        403: Insufficient permissions.
        404: Bill not found.
        400: Bill is not in draft status.
    """
    # Check permissions (same as create bills and add payments)
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to complete bills"
        )

    billing_service = BillingService(db)

    try:
        completed_bill = billing_service.complete_bill(
            bill_id=bill_id,
            completed_by_id=current_user.id,
            notes=complete_data.notes
        )

        return BillResponse.model_validate(completed_bill)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/pending-payments/collect",
    response_model=PendingPaymentCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Collect pending payment from customer"
)
def collect_pending_payment(
    payment_data: PendingPaymentCollect,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Collect pending payment from customer without creating a bill.

    Used when customers want to pay off their pending balance without
    making a new purchase. The payment reduces their pending_balance and
    creates a permanent record of the collection.

    **Permissions**: Owner or Receptionist

    **Records Created**: PendingPaymentCollection (permanent audit trail)

    Args:
        payment_data: Payment collection details (customer, amount, method).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        PendingPaymentCollectionResponse: Complete payment collection record with audit info.

    Raises:
        400: Invalid data or amount exceeds pending balance.
        403: Insufficient permissions.
        404: Customer not found or no pending balance.
    """
    # Check permissions (same as billing operations)
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to collect payments"
        )

    billing_service = BillingService(db)

    try:
        collection = billing_service.collect_pending_payment(
            customer_id=payment_data.customer_id,
            amount=int(payment_data.amount * 100),  # Convert to paise
            payment_method=payment_data.payment_method,
            collected_by_id=current_user.id,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes
        )

        return PendingPaymentCollectionResponse.model_validate(collection)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/pending-payments/customer/{customer_id}",
    response_model=list[PendingPaymentCollectionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get pending payment collection history for customer"
)
def get_customer_pending_payment_history(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending payment collections for a customer.

    Returns complete history of pending balance collections, including:
    - Direct collections (without bills)
    - Overpayments applied to pending balance

    **Permissions**: Owner or Receptionist

    Args:
        customer_id: Customer ID to get history for.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List[PendingPaymentCollectionResponse]: All payment collections, newest first.

    Raises:
        403: Insufficient permissions.
    """
    # Check permissions
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view payment history"
        )

    from app.models.pending_payment import PendingPaymentCollection

    collections = db.query(PendingPaymentCollection).filter(
        PendingPaymentCollection.customer_id == customer_id
    ).order_by(PendingPaymentCollection.collected_at.desc()).all()

    return [PendingPaymentCollectionResponse.model_validate(c) for c in collections]


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
    """Void a bill.

    Voids a draft bill (any permitted user) or a posted bill (Owner only).
    Used for cancellations or billing mistakes.

    **Permissions**: Owner or Receptionist (draft); Owner only (posted)

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
            reason=void_data.reason,
            allow_posted=current_user.is_owner,
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
    search: Optional[str] = None,
    pending_only: bool = False,
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
        query = query.filter(Bill.invoice_number.ilike(f"%{invoice_number}%"))

    if search:
        query = query.filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )

    if pending_only:
        payment_subquery = (
            sa_select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.bill_id == Bill.id)
            .correlate(Bill)
            .scalar_subquery()
        )
        # Also count pending_payment_collections linked to the bill so that
        # bills whose pending amount was collected via the Collect workflow
        # no longer appear in the "Pending Payment" filter.
        collection_subquery = (
            sa_select(func.coalesce(func.sum(PendingPaymentCollection.amount), 0))
            .where(PendingPaymentCollection.bill_id == Bill.id)
            .correlate(Bill)
            .scalar_subquery()
        )
        query = query.filter(
            Bill.status == BillStatus.POSTED,
            Bill.rounded_total > payment_subquery + collection_subquery + Bill.write_off_amount,
        )

    # Get total count
    total = query.count()

    # Calculate pagination
    total_pages = math.ceil(total / limit)
    offset = (page - 1) * limit

    # Get paginated results
    bills = query.order_by(Bill.created_at.desc()).offset(offset).limit(limit).all()

    # Batch-fetch collection totals per bill (single query, not N queries)
    bill_ids = [b.id for b in bills]
    bill_collection_totals: dict[str, int] = {}
    if bill_ids:
        rows = (
            db.query(PendingPaymentCollection.bill_id, func.sum(PendingPaymentCollection.amount))
            .filter(PendingPaymentCollection.bill_id.in_(bill_ids))
            .group_by(PendingPaymentCollection.bill_id)
            .all()
        )
        bill_collection_totals = {row[0]: row[1] for row in rows}

    # Convert to response format: total_paid includes direct payments
    # + any pending collections that have been linked back to this bill.
    bill_items = []
    for bill in bills:
        item = BillListItem.model_validate(bill)
        item.total_paid = (
            sum(p.amount for p in bill.payments)
            + bill_collection_totals.get(bill.id, 0)
        )
        item.write_off_amount = bill.write_off_amount or 0
        bill_items.append(item)

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


@router.patch(
    "/bills/{bill_id}/discount",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Update discount on a draft bill"
)
def update_bill_discount(
    bill_id: str,
    discount_data: BillDiscountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the discount on a draft bill and recalculate totals.

    Use this when a discount was missed or entered incorrectly at billing time.
    If the revised total is now fully covered by any existing partial payments,
    the bill is automatically posted.

    **Permissions**: Owner or Receptionist (billing.discount)

    Args:
        bill_id: ID of the draft bill to update.
        discount_data: New discount amount (paise) and optional reason.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Updated bill (status may change to posted if fully paid).

    Raises:
        400: Bill is not in draft status, or discount exceeds subtotal.
        403: Insufficient permissions.
        404: Bill not found.
    """
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "discount"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to apply discounts"
        )

    billing_service = BillingService(db)

    try:
        updated_bill = billing_service.apply_discount(
            bill_id=bill_id,
            discount_amount=discount_data.discount_amount,
            discount_reason=discount_data.reason,
            applied_by_id=current_user.id,
        )
        return BillResponse.model_validate(updated_bill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/bills/{bill_id}/collect-pending",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Collect payment against a posted bill with pending balance"
)
def collect_pending_bill_payment(
    bill_id: str,
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Collect a payment directly against a specific posted bill with a pending balance.

    Creates a Payment record on the bill and reduces the customer's
    pending_balance. Amount must not exceed the remaining pending
    (rounded_total - total_paid - write_off_amount).

    **Permissions**: Receptionist or Owner

    Raises:
        400: Bill not posted, no pending balance, or amount exceeds pending.
        403: Insufficient permissions.
        404: Bill not found.
    """
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to collect payments"
        )

    billing_service = BillingService(db)
    try:
        updated_bill = billing_service.collect_pending_bill_payment(
            bill_id=bill_id,
            payment_method=payment_data.method,
            amount_paise=int(round(payment_data.amount * 100)),
            confirmed_by_id=current_user.id,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes,
        )
        return BillResponse.model_validate(updated_bill)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/bills/{bill_id}/write-off",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Write off pending balance on a posted bill"
)
def write_off_pending_balance(
    bill_id: str,
    data: BillWriteOff,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Write off (forgive) some or all pending balance on a posted bill.

    Increases the bill's discount by write_off_amount, recalculates totals
    (including GST breakdown), and reduces the linked customer's pending_balance.

    **Permissions**: Owner only.

    Args:
        bill_id: ID of the posted bill.
        data: Write-off amount (paise) and required reason.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Updated bill with reduced rounded_total.

    Raises:
        400: Bill not posted, no pending balance, or amount exceeds pending.
        403: Not owner.
        404: Bill not found.
    """
    if not current_user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can write off pending balances"
        )

    billing_service = BillingService(db)
    try:
        updated_bill = billing_service.write_off_pending_discount(
            bill_id=bill_id,
            write_off_amount=data.write_off_amount,
            reason=data.reason,
            approved_by_id=current_user.id,
        )
        return BillResponse.model_validate(updated_bill)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/bills/{bill_id}/customer",
    response_model=BillResponse,
    summary="Assign a customer to a walk-in bill"
)
def assign_customer_to_bill(
    bill_id: str,
    payload: BillAssignCustomer,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a registered customer to a walk-in bill.

    Only walk-in bills (no customer_id) can have a customer assigned.

    **Permissions**: billing.update (Owner, Receptionist)

    Args:
        bill_id: Bill ID to update.
        payload: Customer ID to assign.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        BillResponse: Updated bill with customer info.

    Raises:
        403: Insufficient permissions.
        404: Bill or customer not found.
        400: Bill already has a customer assigned.
    """
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update bills"
        )

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill not found: {bill_id}"
        )

    if bill.customer_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill already has a customer assigned. Only walk-in bills can be updated."
        )

    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {payload.customer_id}"
        )

    # Assign customer to bill
    bill.customer_id = customer.id
    bill.customer_name = f"{customer.first_name} {customer.last_name}".strip()
    bill.customer_phone = customer.phone

    # If bill is posted with pending balance, update customer's pending_balance
    if bill.status == BillStatus.POSTED:
        total_paid = sum(payment.amount for payment in bill.payments)
        pending_amount = bill.rounded_total - total_paid
        if pending_amount > 0:
            customer.pending_balance += pending_amount

    db.commit()
    db.refresh(bill)

    return bill


@router.post(
    "/bills/{bill_id}/items",
    response_model=AddBillItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a service item to a draft bill with auto-redemption check",
)
def add_bill_item(
    bill_id: str,
    item_data: AddBillItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a single service item to an existing DRAFT bill.

    Recalculates bill totals after adding the item. Runs a package eligibility
    check for the customer; if exactly one eligible package has auto_apply=True,
    the redemption is applied automatically.

    **Permissions**: Receptionist or Owner (billing.create)

    Returns:
        AddBillItemResponse: new BillItem + auto-apply metadata.

    Raises:
        400: Bill not found, not in DRAFT state, or service not found/inactive.
        403: Insufficient permissions.
    """
    if not PermissionChecker.has_permission(current_user.role.name, "billing", "create"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    billing_svc = BillingService(db)
    try:
        result = billing_svc.add_bill_item(
            bill_id=bill_id,
            service_id=item_data.service_id,
            quantity=item_data.quantity,
            staff_id=item_data.staff_id,
            appointment_id=item_data.appointment_id,
            walkin_id=item_data.walkin_id,
            notes=item_data.notes,
            user_id=current_user.id,
        )
        db.commit()
        return AddBillItemResponse(
            bill_item=BillItemResponse.model_validate(result["bill_item"]),
            auto_applied_package_sale_id=result["auto_applied_package_sale_id"],
            eligible_packages=result["eligible_packages"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
