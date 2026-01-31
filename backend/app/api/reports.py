"""Reports and Dashboard API endpoints.

This module provides REST API endpoints for:
- Real-time dashboard metrics
- Daily summaries
- Monthly reports
- Tax reports for GST compliance
"""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.accounting_service import AccountingService
from app.schemas.reports import (
    DashboardResponse,
    DashboardMetrics,
    ServicePerformance,
    StaffPerformance,
    DaySummaryResponse,
    DaySummaryListResponse,
    MonthlyReportResponse,
    TaxReportResponse,
    ProfitLossResponse,
    PLRevenue,
    PLCostOfGoodsSold,
    PLOperatingExpenses,
    PLProfitability,
    ReportFilters,
)
from app.auth.dependencies import get_current_user, require_owner_or_receptionist, require_owner
from app.auth.permissions import PermissionChecker
from app.utils import IST

router = APIRouter(prefix="/reports", tags=["Reports"])


# ============ Dashboard Endpoints ============

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get real-time dashboard metrics.

    Provides current-day metrics including:
    - Revenue (gross, discounts, net)
    - Tax breakdown (CGST, SGST)
    - Payment methods (cash vs digital)
    - Bill and appointment counts
    - Cash drawer status
    - Top performing services
    - Staff performance

    **Permissions**: All authenticated users

    Args:
        target_date: Optional date to get metrics for (YYYY-MM-DD), defaults to today
        db: Database session
        current_user: Authenticated user

    Returns:
        DashboardResponse: Complete dashboard with metrics and performance data
    """
    service = AccountingService(db)

    # Parse target date if provided
    date_obj = None
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    # Get metrics
    metrics_data = service.get_dashboard_metrics(date_obj)
    metrics = DashboardMetrics(**metrics_data)

    # Get top services
    top_services_data = service.get_top_services(date_obj, limit=5)
    top_services = [ServicePerformance(**s) for s in top_services_data]

    # Get staff performance
    staff_perf_data = service.get_staff_performance(date_obj)
    staff_performance = [StaffPerformance(**s) for s in staff_perf_data]

    return DashboardResponse(
        metrics=metrics,
        top_services=top_services,
        staff_performance=staff_performance
    )


# ============ Daily Summary Endpoints ============

@router.get("/daily", response_model=DaySummaryListResponse)
def list_daily_summaries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """List daily summaries with optional filters.

    Returns paginated list of daily business summaries.
    Supports filtering by date range.

    **Permissions**: Receptionist or Owner

    Args:
        start_date: Filter from this date onward (YYYY-MM-DD)
        end_date: Filter up to this date (YYYY-MM-DD)
        page: Page number (1-indexed)
        size: Items per page (max 100)
        db: Database session
        current_user: Authenticated user

    Returns:
        DaySummaryListResponse: Paginated list of daily summaries

    Raises:
        400: Invalid date format
    """
    service = AccountingService(db)

    # Parse dates
    start_date_obj = None
    end_date_obj = None

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )

    # Get summaries
    summaries, total = service.get_daily_summaries(
        start_date=start_date_obj,
        end_date=end_date_obj,
        page=page,
        size=size
    )

    # Calculate pages
    pages = (total + size - 1) // size

    return DaySummaryListResponse(
        items=[DaySummaryResponse.model_validate(s) for s in summaries],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/daily/generate", response_model=DaySummaryResponse, status_code=status.HTTP_201_CREATED)
def generate_daily_summary(
    target_date: Optional[str] = Query(None, description="Date to generate summary for (YYYY-MM-DD)"),
    is_final: bool = Query(False, description="Mark as final summary"),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Generate or update daily summary for a specific date.

    Creates a new daily summary or updates existing one.
    Can be run multiple times during the day (is_final=False) for interim reports,
    then finalized at end of day (is_final=True).

    **Permissions**: Receptionist or Owner

    **Note**: This is typically run automatically by background jobs at 21:45 IST,
    but can be triggered manually if needed.

    Args:
        target_date: Date to generate summary for (defaults to yesterday)
        is_final: Whether to mark as final (end-of-day) summary
        db: Database session
        current_user: Authenticated user

    Returns:
        DaySummaryResponse: Generated or updated daily summary

    Raises:
        400: Invalid date format
    """
    service = AccountingService(db)

    # Parse date
    date_obj = None
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    # Generate summary
    summary = service.generate_daily_summary(
        target_date=date_obj,
        generated_by=current_user.id,
        is_final=is_final
    )

    return DaySummaryResponse.model_validate(summary)


@router.get("/daily/{summary_id}", response_model=DaySummaryResponse)
def get_daily_summary(
    summary_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Get a specific daily summary by ID.

    **Permissions**: Receptionist or Owner

    Args:
        summary_id: Daily summary ID
        db: Database session
        current_user: Authenticated user

    Returns:
        DaySummaryResponse: Daily summary details

    Raises:
        404: Summary not found
    """
    from app.models.accounting import DaySummary

    summary = db.query(DaySummary).filter(DaySummary.id == summary_id).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily summary not found"
        )

    return DaySummaryResponse.model_validate(summary)


# ============ Monthly Report Endpoints ============

@router.get("/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int = Query(..., ge=2020, le=2100, description="Year (e.g., 2025)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Get monthly aggregated report.

    Provides monthly summary with:
    - Aggregated revenue, taxes, payments
    - Daily breakdown for the month
    - Business days count
    - Performance metrics

    **Permissions**: Receptionist or Owner

    Args:
        year: Year (e.g., 2025)
        month: Month number (1-12)
        db: Database session
        current_user: Authenticated user

    Returns:
        MonthlyReportResponse: Complete monthly report with daily breakdown
    """
    service = AccountingService(db)

    # Generate monthly report
    report_data = service.get_monthly_report(year, month)

    # Convert daily_summaries to response models
    report_data["daily_summaries"] = [
        DaySummaryResponse.model_validate(s)
        for s in report_data["daily_summaries"]
    ]

    return MonthlyReportResponse(**report_data)


# ============ Tax Report Endpoints ============

@router.get("/tax", response_model=TaxReportResponse)
def get_tax_report(
    start_date: str = Query(..., description="Period start (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Period end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Generate GST tax report for compliance.

    Provides detailed tax report with:
    - CGST and SGST breakdown
    - Daily taxable amounts
    - Total tax collected
    - Business information (GSTIN, address)

    **Permissions**: Receptionist or Owner

    **Use Case**: For GST filing and tax compliance

    Args:
        start_date: Report period start (YYYY-MM-DD)
        end_date: Report period end (YYYY-MM-DD)
        db: Database session
        current_user: Authenticated user

    Returns:
        TaxReportResponse: Complete tax report for the period

    Raises:
        400: Invalid date format or date range
    """
    service = AccountingService(db)

    # Parse dates
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Validate date range
    if start_date_obj > end_date_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Generate tax report
    report_data = service.generate_tax_report(
        start_date=start_date_obj,
        end_date=end_date_obj,
        generated_by=current_user.id
    )

    return TaxReportResponse(**report_data)


# ============ Profit & Loss Report Endpoint ============

@router.get("/profit-loss", response_model=ProfitLossResponse)
def get_profit_loss_report(
    start_date: str = Query(..., description="Period start (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Period end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    """Generate detailed Profit & Loss statement.

    **Permissions**: Owner only

    Provides comprehensive P&L statement with:
    - Revenue breakdown (gross, discounts, refunds, net)
    - Cost of Goods Sold (service materials + retail products)
    - Operating expenses by category (rent, salaries, utilities, etc.)
    - Profitability metrics (gross profit, net profit, margins)

    This report uses actual COGS from bill items and approved expenses.

    Args:
        start_date: Report period start (YYYY-MM-DD)
        end_date: Report period end (YYYY-MM-DD)
        db: Database session
        current_user: Authenticated owner

    Returns:
        ProfitLossResponse: Complete P&L statement

    Raises:
        400: Invalid date format or date range
    """
    from app.models.accounting import DaySummary
    from app.models.expense import Expense, ExpenseStatus, ExpenseCategory

    # Parse dates
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Validate date range
    if start_date_obj > end_date_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Get day summaries for the period
    summaries = db.query(DaySummary).filter(
        DaySummary.summary_date >= start_date_obj,
        DaySummary.summary_date <= end_date_obj
    ).all()

    # Aggregate revenue
    total_bills = sum(s.total_bills for s in summaries)
    gross_revenue = sum(s.gross_revenue for s in summaries)
    discount_amount = sum(s.discount_amount for s in summaries)
    refund_amount = sum(s.refund_amount for s in summaries)
    net_revenue = gross_revenue - discount_amount - refund_amount

    # Aggregate COGS
    service_cogs = sum(s.actual_service_cogs for s in summaries)
    product_cogs = sum(s.actual_product_cogs for s in summaries)
    total_cogs = service_cogs + product_cogs

    # Get operating expenses for the period
    expenses = db.query(Expense).filter(
        Expense.expense_date >= start_date_obj,
        Expense.expense_date <= end_date_obj,
        Expense.status == ExpenseStatus.APPROVED
    ).all()

    # Breakdown expenses by category
    expenses_by_category = {}
    for exp in expenses:
        category_name = exp.category.value
        expenses_by_category[category_name] = expenses_by_category.get(category_name, 0) + exp.amount

    total_expenses = sum(expenses_by_category.values())

    # Calculate profitability
    gross_profit = net_revenue - total_cogs
    net_profit = gross_profit - total_expenses

    # Calculate margins (avoid division by zero)
    gross_margin_percent = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0
    net_margin_percent = (net_profit / net_revenue * 100) if net_revenue > 0 else 0

    # Tips
    total_tips = sum(s.total_tips for s in summaries)

    return ProfitLossResponse(
        period_start=start_date_obj,
        period_end=end_date_obj,
        revenue=PLRevenue(
            gross_revenue=gross_revenue,
            discount_amount=discount_amount,
            refund_amount=refund_amount,
            net_revenue=net_revenue
        ),
        cogs=PLCostOfGoodsSold(
            service_cogs=service_cogs,
            product_cogs=product_cogs,
            total_cogs=total_cogs
        ),
        operating_expenses=PLOperatingExpenses(
            by_category=expenses_by_category,
            total_expenses=total_expenses
        ),
        profitability=PLProfitability(
            gross_profit=gross_profit,
            net_profit=net_profit,
            gross_margin_percent=gross_margin_percent,
            net_margin_percent=net_margin_percent
        ),
        total_bills=total_bills,
        tips_collected=total_tips,
        generated_at=datetime.now(IST)
    )


# ============ Export Endpoints ============

@router.post("/export", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def export_report(
    db: Session = Depends(get_db),
    current_user = Depends(require_owner_or_receptionist)
):
    """Export reports to PDF/Excel.

    **Status**: Not Implemented Yet

    This endpoint will be implemented in a future phase to support:
    - PDF export of reports
    - Excel export for accounting
    - CSV export for data analysis

    **Permissions**: Receptionist or Owner

    Raises:
        501: Not implemented
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report export will be implemented in Phase 2"
    )
