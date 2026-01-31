"""End of Day Reconciliation API endpoints."""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.billing import Bill, Payment, BillStatus, PaymentMethod
from app.models.reconciliation import DailyReconciliation
from app.models.user import User
from app.schemas.reconciliation import (
    EODSummary,
    EODReport,
    CashReconciliation,
    PaymentMethodBreakdown,
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist
from app.utils import IST

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.get(
    "/eod-summary",
    response_model=EODSummary,
    status_code=status.HTTP_200_OK,
    summary="Get end-of-day summary"
)
def get_eod_summary(
    reconciliation_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """Get end-of-day summary for a specific date.

    Calculates totals and payment breakdown for all bills on the date.

    **Permissions**: Owner or Receptionist

    Args:
        reconciliation_date: Date to reconcile (YYYY-MM-DD). Defaults to today.
        db: Database session
        current_user: Authenticated user

    Returns:
        EODSummary: Summary data for the day
    """
    # Parse date
    if reconciliation_date:
        target_date = datetime.strptime(reconciliation_date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now(IST).date()

    # Get all bills for the date
    bills = db.query(Bill).filter(
        func.date(Bill.created_at) == target_date
    ).all()

    # Calculate totals
    total_bills = len(bills)
    total_revenue = sum(bill.rounded_total for bill in bills if bill.status == BillStatus.POSTED)
    total_tax = sum(bill.tax_amount for bill in bills if bill.status == BillStatus.POSTED)
    total_discount = sum(bill.discount_amount for bill in bills if bill.status == BillStatus.POSTED)

    # Payment breakdown
    payment_breakdown = PaymentMethodBreakdown()

    for bill in bills:
        if bill.status != BillStatus.POSTED:
            continue

        for payment in bill.payments:
            if payment.payment_method == PaymentMethod.CASH:
                payment_breakdown.cash += payment.amount
            elif payment.payment_method == PaymentMethod.CARD:
                payment_breakdown.card += payment.amount
            elif payment.payment_method == PaymentMethod.UPI:
                payment_breakdown.upi += payment.amount
            elif payment.payment_method == PaymentMethod.BANK_TRANSFER:
                payment_breakdown.bank_transfer += payment.amount

    # Bills by status
    bills_by_status = {}
    for bill in bills:
        status_key = bill.status.value
        bills_by_status[status_key] = bills_by_status.get(status_key, 0) + 1

    return EODSummary(
        date=target_date.isoformat(),
        total_bills=total_bills,
        total_revenue=total_revenue,
        total_tax=total_tax,
        total_discount=total_discount,
        payment_breakdown=payment_breakdown,
        bills_by_status=bills_by_status
    )


@router.get(
    "/eod-report",
    response_model=EODReport,
    status_code=status.HTTP_200_OK,
    summary="Get complete EOD report"
)
def get_eod_report(
    reconciliation_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """Get complete end-of-day report including reconciliation status.

    **Permissions**: Owner or Receptionist

    Args:
        reconciliation_date: Date to get report for (YYYY-MM-DD). Defaults to today.
        db: Database session
        current_user: Authenticated user

    Returns:
        EODReport: Complete EOD report with reconciliation data
    """
    # Parse date
    if reconciliation_date:
        target_date = datetime.strptime(reconciliation_date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now(IST).date()

    # Get summary
    summary = get_eod_summary(
        reconciliation_date=target_date.isoformat(),
        db=db,
        current_user=current_user
    )

    # Expected cash from system
    expected_cash = summary.payment_breakdown.cash

    # Check if already reconciled
    reconciliation = db.query(DailyReconciliation).filter(
        DailyReconciliation.reconciliation_date == target_date
    ).first()

    if reconciliation:
        return EODReport(
            date=target_date.isoformat(),
            summary=summary,
            expected_cash=expected_cash,
            actual_cash=reconciliation.actual_cash,
            cash_difference=reconciliation.cash_difference,
            reconciled=reconciliation.reconciled,
            reconciled_at=reconciliation.reconciled_at,
            reconciled_by=reconciliation.reconciled_by,
            notes=reconciliation.notes
        )
    else:
        return EODReport(
            date=target_date.isoformat(),
            summary=summary,
            expected_cash=expected_cash,
            actual_cash=None,
            cash_difference=None,
            reconciled=False,
            reconciled_at=None,
            reconciled_by=None,
            notes=None
        )


@router.post(
    "/reconcile",
    response_model=EODReport,
    status_code=status.HTTP_200_OK,
    summary="Submit cash reconciliation"
)
def submit_reconciliation(
    reconciliation_data: CashReconciliation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist)
):
    """Submit end-of-day cash reconciliation.

    Records actual cash count and marks the day as reconciled.

    **Permissions**: Owner or Receptionist

    Args:
        reconciliation_data: Reconciliation data (date, expected, actual, notes)
        db: Database session
        current_user: Authenticated user

    Returns:
        EODReport: Updated EOD report

    Raises:
        400: Invalid date or data
    """
    # Parse date
    target_date = datetime.strptime(reconciliation_data.date, "%Y-%m-%d").date()

    # Check if already reconciled
    existing = db.query(DailyReconciliation).filter(
        DailyReconciliation.reconciliation_date == target_date
    ).first()

    if existing:
        # Update existing record
        existing.actual_cash = reconciliation_data.actual_cash
        existing.cash_difference = reconciliation_data.actual_cash - reconciliation_data.expected_cash
        existing.reconciled = True
        existing.reconciled_at = datetime.now(IST)
        existing.reconciled_by = current_user.id
        existing.notes = reconciliation_data.notes
        db.commit()
        db.refresh(existing)
    else:
        # Create new record
        new_reconciliation = DailyReconciliation(
            reconciliation_date=target_date,
            expected_cash=reconciliation_data.expected_cash,
            actual_cash=reconciliation_data.actual_cash,
            cash_difference=reconciliation_data.actual_cash - reconciliation_data.expected_cash,
            reconciled=True,
            reconciled_at=datetime.now(IST),
            reconciled_by=current_user.id,
            notes=reconciliation_data.notes
        )
        db.add(new_reconciliation)
        db.commit()
        db.refresh(new_reconciliation)

    # Return updated report
    return get_eod_report(
        reconciliation_date=target_date.isoformat(),
        db=db,
        current_user=current_user
    )
