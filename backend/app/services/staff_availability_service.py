"""Staff availability and busyness calculation service."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.appointment import WalkIn, AppointmentStatus
from app.models.user import Staff
from app.models.service import Service
from app.utils import IST


class StaffAvailabilityService:
    """Service for calculating staff availability and wait times."""

    def __init__(self, db: Session):
        self.db = db

    def get_staff_busyness(self) -> List[Dict]:
        """Get busyness information for all active staff.

        Returns:
            List of staff with busyness metrics:
            - staff_id: Staff ID
            - staff_name: Staff name
            - active_services: Number of services currently in progress
            - queued_services: Number of services checked in but not started
            - total_wait_minutes: Estimated wait time in minutes
            - status: 'available', 'busy', 'very_busy'
        """
        # Get all active staff
        staff_list = self.db.query(Staff).filter(Staff.is_active == True).all()

        result = []
        for staff in staff_list:
            busyness = self._calculate_staff_busyness(staff.id)
            result.append({
                "staff_id": staff.id,
                "staff_name": staff.display_name,
                "active_services": busyness["active_services"],
                "queued_services": busyness["queued_services"],
                "total_wait_minutes": busyness["total_wait_minutes"],
                "status": busyness["status"],
            })

        return result

    def _calculate_staff_busyness(self, staff_id: str) -> Dict:
        """Calculate busyness metrics for a specific staff member.

        Args:
            staff_id: ID of the staff member

        Returns:
            Dict with metrics:
            - active_services: Number of in-progress services
            - queued_services: Number of checked-in but not started
            - total_wait_minutes: Estimated wait time
            - status: Overall busyness status
        """
        now = datetime.now(IST)

        # Count active (in-progress) services
        active_services = self.db.query(func.count(WalkIn.id)).filter(
            and_(
                WalkIn.assigned_staff_id == staff_id,
                WalkIn.status == AppointmentStatus.IN_PROGRESS,
                WalkIn.cancelled_at.is_(None)
            )
        ).scalar() or 0

        # Count queued (checked-in) services
        queued_services = self.db.query(func.count(WalkIn.id)).filter(
            and_(
                WalkIn.assigned_staff_id == staff_id,
                WalkIn.status == AppointmentStatus.CHECKED_IN,
                WalkIn.cancelled_at.is_(None)
            )
        ).scalar() or 0

        # Calculate estimated wait time
        total_wait_minutes = self._estimate_wait_time(staff_id)

        # Determine status
        if active_services == 0 and queued_services == 0:
            status = "available"
        elif active_services <= 1 and queued_services <= 1:
            status = "busy"
        else:
            status = "very_busy"

        return {
            "active_services": active_services,
            "queued_services": queued_services,
            "total_wait_minutes": total_wait_minutes,
            "status": status,
        }

    def _estimate_wait_time(self, staff_id: str) -> int:
        """Estimate wait time for a staff member based on current queue.

        Args:
            staff_id: ID of the staff member

        Returns:
            Estimated wait time in minutes
        """
        # Get all active and queued services for this staff
        services = self.db.query(WalkIn).filter(
            and_(
                WalkIn.assigned_staff_id == staff_id,
                WalkIn.status.in_([
                    AppointmentStatus.IN_PROGRESS,
                    AppointmentStatus.CHECKED_IN
                ]),
                WalkIn.cancelled_at.is_(None)
            )
        ).order_by(WalkIn.checked_in_at).all()

        total_wait = 0
        now = datetime.now(IST)

        for service in services:
            # Get the service details to check for average duration
            service_details = self.db.query(Service).filter(
                Service.id == service.service_id
            ).first()

            if not service_details:
                continue

            # Use average duration if available, otherwise use default duration
            duration = service_details.average_duration_minutes or service_details.duration_minutes

            # If in progress, calculate remaining time
            if service.status == AppointmentStatus.IN_PROGRESS and service.started_at:
                elapsed = (now - service.started_at).total_seconds() / 60
                remaining = max(0, duration - elapsed)
                total_wait += remaining
            else:
                # Not started yet, add full duration
                total_wait += duration

        return int(total_wait)

    def calculate_service_average_durations(self) -> Dict[str, int]:
        """Calculate average durations for all services based on historical data.

        Only considers completed services from the last 90 days.

        Returns:
            Dict mapping service_id to average duration in minutes
        """
        ninety_days_ago = datetime.now(IST) - timedelta(days=90)

        # Query completed walk-ins with actual start and end times
        completed_services = self.db.query(
            WalkIn.service_id,
            func.avg(
                func.extract('epoch', WalkIn.completed_at - WalkIn.started_at) / 60
            ).label('avg_duration')
        ).filter(
            and_(
                WalkIn.status == AppointmentStatus.COMPLETED,
                WalkIn.started_at.isnot(None),
                WalkIn.completed_at.isnot(None),
                WalkIn.completed_at >= ninety_days_ago,
                WalkIn.cancelled_at.is_(None)
            )
        ).group_by(WalkIn.service_id).all()

        return {
            service_id: int(avg_duration)
            for service_id, avg_duration in completed_services
            if avg_duration is not None
        }

    def update_service_average_durations(self) -> int:
        """Update average_duration_minutes for all services based on historical data.

        Returns:
            Number of services updated
        """
        averages = self.calculate_service_average_durations()

        updated_count = 0
        for service_id, avg_duration in averages.items():
            service = self.db.query(Service).filter(Service.id == service_id).first()
            if service:
                service.average_duration_minutes = avg_duration
                updated_count += 1

        self.db.commit()
        return updated_count
