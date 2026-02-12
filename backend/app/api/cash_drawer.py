from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import require_owner_or_receptionist
from app.models.accounting import CashDrawer
from app.models.billing import Payment, PaymentMethod, Bill
from app.models.user import User
from app.schemas.cash_drawer import (
    CashDrawerResponse,
    CashDrawerSummary,
    DrawerCloseRequest,
    DrawerOpenRequest,
    DrawerReopenRequest,
)
from app.utils import IST, generate_ulid

router = APIRouter(prefix="/cash", tags=["cash-drawer"])

def get_todays_drawer(db: Session, today_local: Optional[date] = None) -> Optional[CashDrawer]:
    if not today_local:
        today_local = datetime.now(IST).date()
    # Get start and end of day for date range query (works with both PostgreSQL and SQLite)
    start_of_day = datetime.combine(today_local, datetime.min.time())
    end_of_day = datetime.combine(today_local, datetime.max.time())
    return db.query(CashDrawer).filter(
        CashDrawer.opened_at >= start_of_day,
        CashDrawer.opened_at <= end_of_day
    ).first()

def calculate_drawer_totals(db: Session, drawer: CashDrawer):
    # Time range
    start_time = drawer.opened_at
    end_time = drawer.closed_at if drawer.closed_at else datetime.now(IST)

    # Base query for cash payments associated with bills
    # Cash In: Regular bills (original_bill_id is NULL)
    cash_in = db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Bill).filter(
        Payment.payment_method == PaymentMethod.CASH,
        Payment.confirmed_at >= start_time,
        Payment.confirmed_at <= end_time,
        Bill.original_bill_id.is_(None)
    ).scalar()

    # Cash Out: Refund bills (original_bill_id is NOT NULL)
    cash_out = db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Bill).filter(
        Payment.payment_method == PaymentMethod.CASH,
        Payment.confirmed_at >= start_time,
        Payment.confirmed_at <= end_time,
        Bill.original_bill_id.isnot(None)
    ).scalar()

    return cash_in, cash_out

@router.post("/open", response_model=CashDrawerResponse)
def open_drawer(
    req: DrawerOpenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    if get_todays_drawer(db):
        raise HTTPException(status_code=400, detail="Cash drawer already opened for today")

    opening_float_paise = req.get_opening_float_paise()

    drawer = CashDrawer(
        id=generate_ulid(),
        opened_by=current_user.id,
        opened_at=datetime.now(IST),
        opening_float=opening_float_paise,
        opening_denominations=req.opening_denominations.to_dict() if req.opening_denominations else None,
        expected_cash=opening_float_paise,  # Initial expected
    )
    db.add(drawer)
    db.commit()
    db.refresh(drawer)
    return drawer

@router.post("/close", response_model=CashDrawerResponse)
def close_drawer(
    req: DrawerCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    drawer = get_todays_drawer(db)
    if not drawer:
        raise HTTPException(status_code=404, detail="No drawer found for today")

    if drawer.closed_at:
        raise HTTPException(status_code=400, detail="Drawer already closed")

    closing_counted_paise = req.get_closing_counted_paise()

    # Use server time for close
    drawer.closed_at = datetime.now(IST)
    drawer.closed_by = current_user.id
    drawer.closing_counted = closing_counted_paise
    drawer.closing_denominations = req.closing_denominations.to_dict() if req.closing_denominations else None
    drawer.cash_taken_out = req.cash_taken_out
    drawer.cash_taken_out_reason = req.cash_taken_out_reason
    drawer.notes = req.notes

    # Calculate expected cash accounting for cash taken out
    cash_in, cash_out = calculate_drawer_totals(db, drawer)
    drawer.expected_cash = drawer.opening_float + cash_in - cash_out - req.cash_taken_out
    drawer.variance = drawer.closing_counted - drawer.expected_cash

    db.commit()
    db.refresh(drawer)
    return drawer

@router.post("/reopen", response_model=CashDrawerResponse)
def reopen_drawer(
    req: DrawerReopenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    drawer = get_todays_drawer(db)
    if not drawer:
        raise HTTPException(status_code=404, detail="No drawer found for today")
    
    if not drawer.closed_at:
        raise HTTPException(status_code=400, detail="Drawer is currently open")

    drawer.reopened_at = datetime.now(IST)
    drawer.reopened_by = current_user.id
    drawer.reopen_reason = req.reason
    
    # Reset closed state
    drawer.closed_at = None
    drawer.closed_by = None
    drawer.closing_counted = None
    drawer.variance = None
    # expected_cash remains, but will be recalculated on next close

    db.commit()
    db.refresh(drawer)
    return drawer

@router.get("/current", response_model=CashDrawerSummary)
def get_current_drawer_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    drawer = get_todays_drawer(db)
    
    today = datetime.now(IST)
    
    if not drawer:
        return CashDrawerSummary(
            date=today,
            is_open=False,
            opening_float=0,
            cash_payments=0,
            cash_refunds=0,
            expected_cash=0,
        )

    # Calculate live totals
    cash_in, cash_out = calculate_drawer_totals(db, drawer)
    cash_taken_out = drawer.cash_taken_out or 0
    expected = drawer.opening_float + cash_in - cash_out - cash_taken_out

    return CashDrawerSummary(
        session_id=drawer.id,
        date=drawer.opened_at,
        is_open=drawer.closed_at is None,
        opening_float=drawer.opening_float,
        cash_payments=cash_in,
        cash_refunds=cash_out,
        expected_cash=expected,
        closing_counted=drawer.closing_counted,
        variance=drawer.variance
    )

@router.get("/history", response_model=List[CashDrawerResponse])
def get_drawer_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_receptionist),
):
    drawers = db.query(CashDrawer).order_by(CashDrawer.opened_at.desc()).limit(limit).all()
    return drawers
