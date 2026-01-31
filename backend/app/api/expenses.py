"""Expense management API endpoints."""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.expense import Expense, ExpenseCategory, ExpenseStatus
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseApproval,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseListItem,
    ExpenseSummary
)
from app.utils import generate_ulid


router = APIRouter()


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(require_permission("expenses", "create")),
    db: Session = Depends(get_db)
):
    """
    Create a new expense record.

    **Permissions:** Owner only

    Creates an expense with automatic approval if requires_approval=False,
    otherwise sets status to PENDING.
    """
    # Determine initial status
    initial_status = ExpenseStatus.PENDING if expense_data.requires_approval else ExpenseStatus.APPROVED

    expense = Expense(
        id=generate_ulid(),
        category=expense_data.category,
        amount=expense_data.amount,
        expense_date=expense_data.expense_date,
        description=expense_data.description,
        vendor_name=expense_data.vendor_name,
        invoice_number=expense_data.invoice_number,
        notes=expense_data.notes,
        is_recurring=expense_data.is_recurring,
        recurrence_type=expense_data.recurrence_type,
        staff_id=expense_data.staff_id,
        status=initial_status,
        requires_approval=expense_data.requires_approval,
        recorded_by=current_user.id,
        recorded_at=datetime.utcnow(),
        approved_by=None if expense_data.requires_approval else current_user.id,
        approved_at=None if expense_data.requires_approval else datetime.utcnow()
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    return expense


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter to this date"),
    category: Optional[ExpenseCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[ExpenseStatus] = Query(None, alias="status", description="Filter by status"),
    staff_id: Optional[str] = Query(None, description="Filter by staff (for salaries)"),
    is_recurring: Optional[bool] = Query(None, description="Filter recurring expenses"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("expenses", "read")),
    db: Session = Depends(get_db)
):
    """
    List expenses with optional filters.

    **Permissions:** Owner only

    Supports filtering by date range, category, status, staff, and recurring flag.
    Returns paginated results.
    """
    query = db.query(Expense)

    # Apply filters
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if category:
        query = query.filter(Expense.category == category)
    if status_filter:
        query = query.filter(Expense.status == status_filter)
    if staff_id:
        query = query.filter(Expense.staff_id == staff_id)
    if is_recurring is not None:
        query = query.filter(Expense.is_recurring == is_recurring)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    expenses = query.order_by(Expense.expense_date.desc()).offset(offset).limit(size).all()

    # Calculate total pages
    pages = (total + size - 1) // size if total > 0 else 0

    return ExpenseListResponse(
        items=[ExpenseListItem.model_validate(exp) for exp in expenses],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/summary", response_model=ExpenseSummary)
def get_expense_summary(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter to this date"),
    current_user: User = Depends(require_permission("expenses", "read")),
    db: Session = Depends(get_db)
):
    """
    Get expense summary for a period.

    **Permissions:** Owner only

    Returns total amount, breakdown by category, and counts by status.
    """
    query = db.query(Expense)

    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.all()

    # Calculate totals
    total_amount = sum(exp.amount for exp in expenses if exp.status == ExpenseStatus.APPROVED)

    # Breakdown by category
    by_category = {}
    for exp in expenses:
        if exp.status == ExpenseStatus.APPROVED:
            category_name = exp.category.value
            by_category[category_name] = by_category.get(category_name, 0) + exp.amount

    # Count by status
    approved_count = sum(1 for exp in expenses if exp.status == ExpenseStatus.APPROVED)
    pending_count = sum(1 for exp in expenses if exp.status == ExpenseStatus.PENDING)
    rejected_count = sum(1 for exp in expenses if exp.status == ExpenseStatus.REJECTED)

    return ExpenseSummary(
        total_amount=total_amount,
        by_category=by_category,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: str,
    current_user: User = Depends(require_permission("expenses", "read")),
    db: Session = Depends(get_db)
):
    """
    Get expense by ID.

    **Permissions:** Owner only
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}"
        )

    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: str,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(require_permission("expenses", "update")),
    db: Session = Depends(get_db)
):
    """
    Update an expense record.

    **Permissions:** Owner only

    Only pending or rejected expenses can be updated.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}"
        )

    if expense.status == ExpenseStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update approved expenses"
        )

    # Update fields
    if expense_data.amount is not None:
        expense.amount = expense_data.amount
    if expense_data.expense_date is not None:
        expense.expense_date = expense_data.expense_date
    if expense_data.description is not None:
        expense.description = expense_data.description
    if expense_data.vendor_name is not None:
        expense.vendor_name = expense_data.vendor_name
    if expense_data.invoice_number is not None:
        expense.invoice_number = expense_data.invoice_number
    if expense_data.notes is not None:
        expense.notes = expense_data.notes
    if expense_data.staff_id is not None:
        expense.staff_id = expense_data.staff_id

    db.commit()
    db.refresh(expense)

    return expense


@router.post("/{expense_id}/approve", response_model=ExpenseResponse)
def approve_or_reject_expense(
    expense_id: str,
    approval: ExpenseApproval,
    current_user: User = Depends(require_permission("expenses", "approve")),
    db: Session = Depends(get_db)
):
    """
    Approve or reject an expense.

    **Permissions:** Owner only

    Changes expense status to APPROVED or REJECTED and records the reviewer.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}"
        )

    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only approve/reject pending expenses. Current status: {expense.status}"
        )

    if approval.approved:
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()
    else:
        expense.status = ExpenseStatus.REJECTED
        expense.rejected_by = current_user.id
        expense.rejected_at = datetime.utcnow()
        expense.rejection_reason = approval.notes

    db.commit()
    db.refresh(expense)

    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str,
    current_user: User = Depends(require_permission("expenses", "delete")),
    db: Session = Depends(get_db)
):
    """
    Delete an expense record.

    **Permissions:** Owner only

    Only pending or rejected expenses can be deleted.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense not found: {expense_id}"
        )

    if expense.status == ExpenseStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete approved expenses"
        )

    db.delete(expense)
    db.commit()

    return None
