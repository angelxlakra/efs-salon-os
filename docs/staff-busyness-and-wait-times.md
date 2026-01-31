# Staff Busyness & Wait Time Estimation

## Overview

This feature provides real-time staff availability information and estimated wait times based on historical service duration data. It helps receptionists make informed decisions when assigning services to staff members.

## Key Features

### 1. Staff Busyness Indicators
When selecting a staff member for a service in the POS, you'll now see:
- **Available** (Green) - No active or queued services
- **Busy** (Yellow) - 1-2 services in progress/queue
- **Very Busy** (Red) - 3+ services in progress/queue

### 2. Estimated Wait Times
- Displays approximate wait time for each staff member
- Based on current queue and average service durations
- Updates in real-time as services are completed
- Format: "~30 min" or "~1h 15m"

### 3. Smart Sorting
Staff are automatically sorted by availability:
1. Available staff first
2. Busy staff next (sorted by shortest wait time)
3. Very busy staff last

### 4. Historical Duration Tracking
- System learns average service durations from completed services
- Uses last 90 days of historical data
- More accurate over time as more services are completed

## How It Works

### Initial State
- New services use the default `duration_minutes` set by admin
- Average duration is `NULL` until historical data is collected

### Learning Phase
- As services are completed, the system tracks actual duration
- Actual duration = `completed_at` - `started_at`
- Only completed, non-cancelled services are counted

### Calculation
Every time average durations are updated (manually or via scheduled job):
1. Queries last 90 days of completed services
2. Calculates average duration per service
3. Updates `average_duration_minutes` field
4. Wait time = Sum of (remaining time for active services + full duration for queued services)

## API Endpoints

### Get Staff Busyness
```http
GET /api/staff/availability/busyness
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "staff_id": "01STAFF123...",
    "staff_name": "John Doe",
    "active_services": 1,
    "queued_services": 2,
    "total_wait_minutes": 45,
    "status": "busy"
  }
]
```

**Permissions**: Owner or Receptionist

### Update Average Service Durations
```http
POST /api/catalog/services/update-average-durations
Authorization: Bearer <token>
```

**Response:**
```json
{
  "updated_count": 12,
  "averages": {
    "01SERVICE1...": 35,
    "01SERVICE2...": 48
  },
  "message": "Successfully updated average durations for 12 service(s)"
}
```

**Permissions**: Owner only

## Database Schema

### Services Table
```sql
ALTER TABLE services
ADD COLUMN average_duration_minutes INTEGER NULL;
```

- `duration_minutes` - Default/estimated duration (set by admin)
- `average_duration_minutes` - Calculated from historical data (NULL initially)

## Usage Guide

### For Receptionists

1. **Booking a Walk-in Service**:
   - Select customer
   - Choose service
   - When selecting staff, you'll see:
     - Green badge for available staff (best choice)
     - Yellow badge for busy staff (may have short wait)
     - Red badge for very busy staff (longer wait)
   - Estimated wait time appears next to each staff member
   - Staff are automatically sorted by availability

2. **Interpreting Wait Times**:
   - "No wait" - Staff is completely free
   - "~15 min" - Customer will wait approximately 15 minutes
   - "~1h 30m" - Customer will wait approximately 1.5 hours
   - Choose the staff with shortest wait for best customer experience

### For Owners/Admins

1. **Initial Setup**:
   - Set realistic `duration_minutes` for each service
   - After a few weeks of operation, run the update endpoint
   - Average durations will start appearing

2. **Updating Averages** (Manual):
   - Use the API endpoint or schedule a background job
   - Recommended frequency: Weekly or monthly
   - Can be run anytime without disrupting operations

3. **Monitoring Accuracy**:
   - Compare `duration_minutes` vs `average_duration_minutes`
   - Large differences indicate:
     - Need to update default duration
     - Service complexity varies significantly
     - Staff efficiency differences

## Implementation Details

### Wait Time Calculation Logic

```python
def calculate_wait_time(staff_id):
    total_wait = 0

    # Get all active/queued services for staff
    for service in staff_services:
        # Use average if available, else use default
        duration = service.average_duration or service.duration_minutes

        # If service is in progress
        if service.status == IN_PROGRESS:
            elapsed = now - service.started_at
            remaining = max(0, duration - elapsed)
            total_wait += remaining
        else:
            # Service is queued (not started)
            total_wait += duration

    return total_wait
```

### Status Determination

```python
def determine_status(active_services, queued_services):
    total = active_services + queued_services

    if total == 0:
        return "available"
    elif total <= 2:
        return "busy"
    else:
        return "very_busy"
```

## Benefits

### For Customers
- Reduced wait times through intelligent staff assignment
- Better service experience
- Realistic expectations about wait times

### For Receptionists
- Data-driven staff assignment decisions
- Reduced guesswork
- Balanced workload across staff

### For Business
- Improved efficiency
- Better resource utilization
- Customer satisfaction insights
- Identify bottlenecks and slow services

## Future Enhancements

### Planned Features
1. **Automatic Updates**: Background job to update averages nightly
2. **Staff Performance Dashboard**: Compare actual vs. expected durations
3. **Peak Hours Analysis**: Identify busy times for better staffing
4. **Service Complexity Scoring**: Flag services with high duration variance
5. **Customer Wait Time Display**: Show estimated wait on customer-facing screens

### Potential Improvements
- Factor in staff skill level for duration estimates
- Account for service add-ons in duration calculations
- Predictive wait times based on day/time patterns
- Real-time notifications when wait times exceed thresholds

## Troubleshooting

### Issue: Wait times seem inaccurate

**Possible Causes:**
- Not enough historical data yet
- Staff not marking services as completed promptly
- Average durations not updated recently

**Solutions:**
1. Ensure staff are completing services in the system
2. Run the update averages endpoint
3. Check `average_duration_minutes` is populated for services
4. Give system time to collect more data (2-4 weeks)

### Issue: All staff show as "available" but services are queued

**Possible Causes:**
- Services not assigned to staff yet
- Services in "checked_in" status but staff not assigned

**Solutions:**
1. Ensure services are properly assigned to staff members
2. Check that services progress through status workflow correctly

### Issue: Negative or zero wait times

**Possible Causes:**
- Service took longer than expected (in progress > duration)
- System time issues

**Solutions:**
1. This is normal for services that run over
2. Wait time calculation uses `max(0, remaining)` to prevent negatives

## Migration Guide

The database migration adds the `average_duration_minutes` column:

```bash
# Migration already applied automatically
# To verify:
docker compose exec api alembic current

# Should show: 1a137ed244c2 (head)
```

## Testing

### Manual Testing Steps

1. Create a few test walk-ins assigned to different staff
2. Open POS and select a service
3. Open staff selector dropdown
4. Verify you see:
   - Staff names
   - Busyness badges (Available/Busy/Very Busy)
   - Wait time estimates
   - Staff sorted by availability

### API Testing

```bash
# Test staff busyness endpoint
curl -H "Authorization: Bearer <token>" \
  http://salon.local/api/staff/availability/busyness

# Test update averages endpoint (owner only)
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://salon.local/api/catalog/services/update-average-durations
```

## Technical Notes

- Historical window: 90 days (configurable in code)
- Duration calculation uses PostgreSQL `EXTRACT(epoch, ...)` for precision
- Busyness data fetched in parallel with staff list for performance
- Frontend caches busyness data for the duration of staff selection
- All times stored in IST (Indian Standard Time)

---

**Version**: 1.0
**Date**: January 25, 2026
**Status**: Production Ready ✅
