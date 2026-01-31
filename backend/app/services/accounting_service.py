"""Accounting service for financial reporting and dashboard metrics.

This service provides business logic for:
- Real-time dashboard metrics
- Daily summary generation
- Monthly report aggregation
- Tax report generation
- Performance analytics
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.accounting import DaySummary, CashDrawer
from app.models.billing import Bill, BillItem, BillStatus, Payment, PaymentMethod
from app.models.expense import Expense, ExpenseStatus
from app.models.appointment import Appointment, WalkIn, AppointmentStatus
from app.models.service import Service
from app.models.user import Staff
from app.utils import IST
from app.config import settings


class AccountingService:
    """Service for accounting and financial reporting operations."""

    def __init__(self, db: Session):
        """Initialize accounting service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # ============ Dashboard Methods ============

    def get_dashboard_metrics(self, target_date: Optional[date] = None) -> Dict:
        """Get real-time dashboard metrics for a specific date.

        Args:
            target_date: Date to get metrics for (defaults to today in IST)

        Returns:
            Dictionary with dashboard metrics including revenue, taxes, payments,
            cash drawer status, and counts
        """
        if not target_date:
            target_date = datetime.now(IST).date()

        # Get date range for queries
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        # Get bill metrics
        bills_query = self.db.query(Bill).filter(
            Bill.created_at >= start_of_day,
            Bill.created_at <= end_of_day,
            Bill.status.in_([BillStatus.POSTED, BillStatus.REFUNDED])
        )

        total_bills = bills_query.count()

        # Calculate revenue
        gross_revenue = 0
        discount_amount = 0
        net_revenue = 0
        cgst_collected = 0
        sgst_collected = 0
        total_tax = 0

        for bill in bills_query.all():
            if bill.status == BillStatus.REFUNDED:
                # Refunded bills subtract from revenue
                gross_revenue -= bill.rounded_total
                discount_amount -= bill.discount_amount
                net_revenue -= bill.rounded_total
                cgst_collected -= bill.cgst_amount
                sgst_collected -= bill.sgst_amount
                total_tax -= (bill.cgst_amount + bill.sgst_amount)
            else:
                gross_revenue += bill.rounded_total
                discount_amount += bill.discount_amount
                net_revenue += bill.rounded_total
                cgst_collected += bill.cgst_amount
                sgst_collected += bill.sgst_amount
                total_tax += (bill.cgst_amount + bill.sgst_amount)

        # Get payment split
        payments_query = self.db.query(Payment).join(Bill).filter(
            Payment.confirmed_at >= start_of_day,
            Payment.confirmed_at <= end_of_day,
            Bill.status == BillStatus.POSTED
        )

        cash_collected = 0
        digital_collected = 0

        for payment in payments_query.all():
            if payment.payment_method == PaymentMethod.CASH:
                cash_collected += payment.amount
            else:
                digital_collected += payment.amount

        # Get appointment metrics
        appt_query = self.db.query(Appointment).filter(
            Appointment.scheduled_at >= start_of_day,
            Appointment.scheduled_at <= end_of_day
        )

        completed_appointments = appt_query.filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).count()

        active_appointments = appt_query.filter(
            Appointment.status == AppointmentStatus.IN_PROGRESS
        ).count()

        pending_appointments = appt_query.filter(
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CHECKED_IN
            ])
        ).count()

        # Get cash drawer status
        cash_drawer = self.db.query(CashDrawer).filter(
            CashDrawer.opened_at >= start_of_day,
            CashDrawer.opened_at <= end_of_day,
            CashDrawer.closed_at.is_(None)
        ).first()

        cash_drawer_open = cash_drawer is not None
        cash_drawer_opening_float = cash_drawer.opening_float if cash_drawer else None
        cash_drawer_expected_cash = cash_drawer.expected_cash if cash_drawer else None

        return {
            "today": target_date,
            "total_bills": total_bills,
            "completed_appointments": completed_appointments,
            "active_appointments": active_appointments,
            "pending_appointments": pending_appointments,
            "gross_revenue": gross_revenue,
            "discount_amount": discount_amount,
            "net_revenue": net_revenue,
            "cgst_collected": cgst_collected,
            "sgst_collected": sgst_collected,
            "total_tax": total_tax,
            "cash_collected": cash_collected,
            "digital_collected": digital_collected,
            "cash_drawer_open": cash_drawer_open,
            "cash_drawer_opening_float": cash_drawer_opening_float,
            "cash_drawer_expected_cash": cash_drawer_expected_cash,
        }

    def get_top_services(self, target_date: Optional[date] = None, limit: int = 5) -> List[Dict]:
        """Get top performing services for a date.

        Args:
            target_date: Date to get metrics for (defaults to today)
            limit: Maximum number of services to return

        Returns:
            List of dictionaries with service performance data
        """
        if not target_date:
            target_date = datetime.now(IST).date()

        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        # Query completed appointments grouped by service
        from app.models.billing import BillItem

        results = self.db.query(
            Service.id,
            Service.name,
            func.count(BillItem.id).label('count'),
            func.sum(BillItem.line_total).label('total_revenue')
        ).join(
            BillItem, BillItem.service_id == Service.id
        ).join(
            Bill, BillItem.bill_id == Bill.id
        ).filter(
            Bill.created_at >= start_of_day,
            Bill.created_at <= end_of_day,
            Bill.status == BillStatus.POSTED
        ).group_by(
            Service.id, Service.name
        ).order_by(
            func.sum(BillItem.line_total).desc()
        ).limit(limit).all()

        return [
            {
                "service_id": r.id,
                "service_name": r.name,
                "count": r.count,
                "total_revenue": r.total_revenue or 0
            }
            for r in results
        ]

    def get_staff_performance(self, target_date: Optional[date] = None) -> List[Dict]:
        """Get staff performance metrics for a date.

        Args:
            target_date: Date to get metrics for (defaults to today)

        Returns:
            List of dictionaries with staff performance data
        """
        if not target_date:
            target_date = datetime.now(IST).date()

        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        # Query completed appointments grouped by staff
        results = self.db.query(
            Staff.id,
            Staff.display_name,
            func.count(Appointment.id).label('services_completed')
        ).join(
            Appointment, Appointment.assigned_staff_id == Staff.id
        ).filter(
            Appointment.completed_at >= start_of_day,
            Appointment.completed_at <= end_of_day,
            Appointment.status == AppointmentStatus.COMPLETED
        ).group_by(
            Staff.id, Staff.display_name
        ).order_by(
            func.count(Appointment.id).desc()
        ).all()

        # For each staff, calculate revenue (need to join with bills)
        staff_data = []
        for r in results:
            # This is a simplified calculation - in a real system,
            # you'd join through bills to get actual revenue per staff
            staff_data.append({
                "staff_id": r.id,
                "staff_name": r.display_name,
                "services_completed": r.services_completed,
                "total_revenue": 0  # Placeholder - needs bill linking
            })

        return staff_data

    # ============ Day Summary Methods ============

    def generate_daily_summary(
        self,
        target_date: Optional[date] = None,
        generated_by: Optional[str] = None,
        is_final: bool = False
    ) -> DaySummary:
        """Generate daily summary for a specific date.

        This method aggregates all financial data for a day into a summary record.
        Can be run multiple times (e.g., for interim reports) with is_final=False,
        then finalized at end of day with is_final=True.

        Args:
            target_date: Date to generate summary for (defaults to yesterday)
            generated_by: User ID who generated this summary
            is_final: Whether this is the final summary for the day

        Returns:
            DaySummary: Created or updated summary record
        """
        if not target_date:
            # Default to yesterday
            target_date = (datetime.now(IST) - timedelta(days=1)).date()

        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        # Check if summary already exists
        existing = self.db.query(DaySummary).filter(
            DaySummary.summary_date == target_date
        ).first()

        # Calculate bill metrics
        bills_query = self.db.query(Bill).filter(
            Bill.created_at >= start_of_day,
            Bill.created_at <= end_of_day,
            Bill.status.in_([BillStatus.POSTED, BillStatus.REFUNDED])
        )

        total_bills = bills_query.filter(Bill.status == BillStatus.POSTED).count()
        refund_count = bills_query.filter(Bill.status == BillStatus.REFUNDED).count()

        # Calculate revenue and taxes
        gross_revenue = 0
        discount_amount = 0
        refund_amount = 0
        cgst_collected = 0
        sgst_collected = 0

        for bill in bills_query.all():
            if bill.status == BillStatus.REFUNDED:
                refund_amount += bill.rounded_total
            else:
                gross_revenue += bill.rounded_total
                discount_amount += bill.discount_amount
                cgst_collected += bill.cgst_amount
                sgst_collected += bill.sgst_amount

        net_revenue = gross_revenue - discount_amount - refund_amount
        total_tax = cgst_collected + sgst_collected

        # Calculate payment split
        payments_query = self.db.query(Payment).join(Bill).filter(
            Payment.confirmed_at >= start_of_day,
            Payment.confirmed_at <= end_of_day,
            Bill.status == BillStatus.POSTED
        )

        cash_collected = 0
        digital_collected = 0

        for payment in payments_query.all():
            if payment.payment_method == PaymentMethod.CASH:
                cash_collected += payment.amount
            else:
                digital_collected += payment.amount

        # Calculate actual COGS from bill items
        actual_service_cogs = 0
        actual_product_cogs = 0
        total_tips = 0

        for bill in bills_query.all():
            if bill.status == BillStatus.POSTED:
                # Sum COGS from bill items
                for item in bill.items:
                    if item.cogs_amount:
                        if item.service_id:
                            actual_service_cogs += item.cogs_amount
                        elif item.sku_id:
                            actual_product_cogs += item.cogs_amount

                # Sum tips
                if bill.tip_amount:
                    total_tips += bill.tip_amount

        total_cogs = actual_service_cogs + actual_product_cogs

        # Calculate operating expenses for the day
        expenses_query = self.db.query(Expense).filter(
            Expense.expense_date == target_date,
            Expense.status == ExpenseStatus.APPROVED
        )
        total_expenses = sum(exp.amount for exp in expenses_query.all())

        # Calculate accurate profit
        gross_profit = net_revenue - total_cogs
        net_profit = gross_profit - total_expenses

        # Keep estimated values for backward compatibility
        estimated_cogs = int(net_revenue * 0.30)
        estimated_profit = net_revenue - estimated_cogs

        # Create or update summary
        if existing:
            # Update existing summary
            existing.total_bills = total_bills
            existing.refund_count = refund_count
            existing.gross_revenue = gross_revenue
            existing.discount_amount = discount_amount
            existing.refund_amount = refund_amount
            existing.net_revenue = net_revenue
            existing.cgst_collected = cgst_collected
            existing.sgst_collected = sgst_collected
            existing.total_tax = total_tax
            existing.cash_collected = cash_collected
            existing.digital_collected = digital_collected
            existing.estimated_cogs = estimated_cogs
            existing.estimated_profit = estimated_profit
            existing.actual_service_cogs = actual_service_cogs
            existing.actual_product_cogs = actual_product_cogs
            existing.total_cogs = total_cogs
            existing.total_expenses = total_expenses
            existing.gross_profit = gross_profit
            existing.net_profit = net_profit
            existing.total_tips = total_tips
            existing.generated_at = datetime.now(IST)
            existing.generated_by = generated_by
            existing.is_final = is_final

            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new summary
            summary = DaySummary(
                summary_date=target_date,
                total_bills=total_bills,
                refund_count=refund_count,
                gross_revenue=gross_revenue,
                discount_amount=discount_amount,
                refund_amount=refund_amount,
                net_revenue=net_revenue,
                cgst_collected=cgst_collected,
                sgst_collected=sgst_collected,
                total_tax=total_tax,
                cash_collected=cash_collected,
                digital_collected=digital_collected,
                estimated_cogs=estimated_cogs,
                estimated_profit=estimated_profit,
                actual_service_cogs=actual_service_cogs,
                actual_product_cogs=actual_product_cogs,
                total_cogs=total_cogs,
                total_expenses=total_expenses,
                gross_profit=gross_profit,
                net_profit=net_profit,
                total_tips=total_tips,
                generated_at=datetime.now(IST),
                generated_by=generated_by,
                is_final=is_final
            )

            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            return summary

    def get_daily_summaries(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[DaySummary], int]:
        """Get daily summaries with optional date filters and pagination.

        Args:
            start_date: Filter summaries from this date onward
            end_date: Filter summaries up to this date
            page: Page number (1-indexed)
            size: Number of items per page

        Returns:
            Tuple of (list of summaries, total count)
        """
        query = self.db.query(DaySummary)

        if start_date:
            query = query.filter(DaySummary.summary_date >= start_date)

        if end_date:
            query = query.filter(DaySummary.summary_date <= end_date)

        # Order by date descending (most recent first)
        query = query.order_by(DaySummary.summary_date.desc())

        total = query.count()
        summaries = query.offset((page - 1) * size).limit(size).all()

        return summaries, total

    # ============ Monthly Report Methods ============

    def get_monthly_report(self, year: int, month: int) -> Dict:
        """Generate monthly aggregated report.

        Args:
            year: Year (e.g., 2025)
            month: Month number (1-12)

        Returns:
            Dictionary with monthly aggregated data
        """
        # Get all daily summaries for the month
        start_date = date(year, month, 1)

        # Calculate last day of month
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        summaries, _ = self.get_daily_summaries(start_date, end_date, page=1, size=100)

        # Aggregate data
        total_bills = 0
        total_refunds = 0
        gross_revenue = 0
        discount_amount = 0
        refund_amount = 0
        cgst_collected = 0
        sgst_collected = 0
        cash_collected = 0
        digital_collected = 0
        estimated_cogs = 0

        business_days = len(summaries)

        for summary in summaries:
            total_bills += summary.total_bills
            total_refunds += summary.refund_count
            gross_revenue += summary.gross_revenue
            discount_amount += summary.discount_amount
            refund_amount += summary.refund_amount
            cgst_collected += summary.cgst_collected
            sgst_collected += summary.sgst_collected
            cash_collected += summary.cash_collected
            digital_collected += summary.digital_collected
            estimated_cogs += summary.estimated_cogs

        net_revenue = gross_revenue - discount_amount - refund_amount
        total_tax = cgst_collected + sgst_collected
        estimated_profit = net_revenue - estimated_cogs

        return {
            "month": f"{year}-{month:02d}",
            "year": year,
            "month_number": month,
            "total_bills": total_bills,
            "total_refunds": total_refunds,
            "business_days": business_days,
            "gross_revenue": gross_revenue,
            "discount_amount": discount_amount,
            "refund_amount": refund_amount,
            "net_revenue": net_revenue,
            "cgst_collected": cgst_collected,
            "sgst_collected": sgst_collected,
            "total_tax": total_tax,
            "cash_collected": cash_collected,
            "digital_collected": digital_collected,
            "estimated_cogs": estimated_cogs,
            "estimated_profit": estimated_profit,
            "daily_summaries": summaries
        }

    # ============ Tax Report Methods ============

    def generate_tax_report(
        self,
        start_date: date,
        end_date: date,
        generated_by: str
    ) -> Dict:
        """Generate GST tax report for compliance.

        Args:
            start_date: Report period start
            end_date: Report period end
            generated_by: User ID generating report

        Returns:
            Dictionary with tax report data
        """
        summaries, _ = self.get_daily_summaries(start_date, end_date, page=1, size=1000)

        # Build entries
        entries = []
        total_bills = 0
        total_taxable_amount = 0
        total_cgst = 0
        total_sgst = 0

        for summary in summaries:
            # Taxable amount = net revenue - tax
            taxable = summary.net_revenue - summary.total_tax

            entries.append({
                "date": summary.summary_date,
                "bill_count": summary.total_bills,
                "taxable_amount": taxable,
                "cgst_amount": summary.cgst_collected,
                "sgst_amount": summary.sgst_collected,
                "total_tax": summary.total_tax,
                "gross_amount": summary.net_revenue
            })

            total_bills += summary.total_bills
            total_taxable_amount += taxable
            total_cgst += summary.cgst_collected
            total_sgst += summary.sgst_collected

        total_tax = total_cgst + total_sgst
        total_gross_amount = total_taxable_amount + total_tax

        return {
            "period_start": start_date,
            "period_end": end_date,
            "gstin": settings.gstin,
            "salon_name": settings.salon_name,
            "salon_address": settings.salon_address,
            "total_bills": total_bills,
            "total_taxable_amount": total_taxable_amount,
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_tax": total_tax,
            "total_gross_amount": total_gross_amount,
            "entries": entries,
            "generated_at": datetime.now(IST),
            "generated_by": generated_by
        }
