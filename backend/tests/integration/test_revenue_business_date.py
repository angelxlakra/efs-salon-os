"""Revenue is attributed to the day the WORK was done (business_date), not the
day a late 'pay later' checkout posted the bill."""

from datetime import datetime, timedelta

from app.services.billing_service import BillingService
from app.services.accounting_service import AccountingService
from app.models.billing import BillStatus
from app.models.appointment import WalkIn, AppointmentStatus
from app.utils import IST, generate_ulid


def test_create_bill_attributes_to_walkin_work_day(
    db_session, service_factory, customer_factory, test_user
):
    """A bill that settles a walk-in booked earlier takes the walk-in's day."""
    svc = service_factory(base_price=50000)
    customer = customer_factory()
    work_dt = datetime.now(IST) - timedelta(days=2)
    session_id = generate_ulid()

    db_session.add(WalkIn(
        ticket_number=f"WK-{generate_ulid()[:8]}",
        session_id=session_id, service_id=svc.id, duration_minutes=30,
        status=AppointmentStatus.CHECKED_IN, checked_in_at=work_dt,
        customer_name="Walk In", customer_id=customer.id, created_by=test_user.id,
    ))
    db_session.flush()

    bill = BillingService(db_session).create_bill(
        items=[{"service_id": svc.id, "quantity": 1}],
        created_by_id=test_user.id, customer_id=customer.id, session_id=session_id,
    )
    # Created today, but the work was done 2 days ago.
    assert bill.business_date == work_dt.astimezone(IST).date()
    assert bill.business_date != datetime.now(IST).date()


def test_create_bill_without_walkins_uses_today(
    db_session, service_factory, customer_factory, test_user
):
    svc = service_factory(base_price=50000)
    customer = customer_factory()
    bill = BillingService(db_session).create_bill(
        items=[{"service_id": svc.id, "quantity": 1}],
        created_by_id=test_user.id, customer_id=customer.id,
    )
    assert bill.business_date == datetime.now(IST).date()


def test_dashboard_counts_revenue_on_business_date_not_checkout_day(
    db_session, service_factory, customer_factory, test_user
):
    """The forgotten pay-later bill: posted today but worked yesterday → its
    revenue lands on yesterday, not today."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    bs = BillingService(db_session)
    bill = bs.create_bill(
        items=[{"service_id": svc.id, "quantity": 1}],
        created_by_id=test_user.id, customer_id=customer.id,
    )
    # Simulate: posted at the (late) checkout today, but work was yesterday.
    yesterday = (datetime.now(IST) - timedelta(days=1)).date()
    today = datetime.now(IST).date()
    bill.status = BillStatus.POSTED
    bill.business_date = yesterday
    db_session.flush()

    acct = AccountingService(db_session)
    assert acct.get_dashboard_metrics(yesterday)["net_revenue"] == bill.rounded_total
    assert acct.get_dashboard_metrics(today)["net_revenue"] == 0
