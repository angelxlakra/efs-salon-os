# Multi-Staff Service Contribution Tracking Guide

## Overview

This system allows you to track and split contributions among multiple staff members working on a single service. It's designed for complex services like Botox treatments where multiple specialists collaborate on different tasks.

## Key Features

✅ **Predefined Service Templates** - Define standard staff roles and splits for multi-person services
✅ **Flexible Contribution Splitting** - Percentage, fixed amount, equal split, time-based, or hybrid
✅ **Workflow Tracking** - Record the sequence of staff involvement
✅ **Automatic Calculation** - System calculates each staff member's contribution
✅ **Commission Ready** - Foundation for future commission/payout systems

## Architecture

### Database Models

1. **ServiceStaffTemplate** - Predefined staff role templates per service
2. **BillItemStaffContribution** - Actual staff contributions when service is billed

### Key Relationships

```
Service (e.g., "Botox Treatment")
    └─ ServiceStaffTemplates (predefined roles)
        ├─ Role 1: "Application" (50%, 30 min)
        ├─ Role 2: "Hair Wash" (25%, 15 min)
        └─ Role 3: "Styling" (25%, 20 min)

Bill → BillItem (service line)
    └─ BillItemStaffContributions (actual staff who performed)
        ├─ Staff A → Application → ₹2500
        ├─ Staff B → Hair Wash → ₹1250
        └─ Staff C → Styling → ₹1250
```

---

## Step 1: Create Service with Staff Templates

### Example: Botox Treatment

**Service Setup:**
```json
POST /api/catalog/services

{
  "category_id": "01HXXX...",
  "name": "Botox Treatment",
  "description": "Complete botox application with hair treatment",
  "base_price": 500000,  // ₹5000
  "duration_minutes": 65,
  "display_order": 1
}
```

**Add Staff Role Templates:**
```json
POST /api/catalog/services/{service_id}/staff-templates

{
  "role_name": "Botox Application",
  "role_description": "Apply botox to designated facial areas",
  "sequence_order": 1,
  "contribution_type": "percentage",
  "default_contribution_percent": 50,
  "estimated_duration_minutes": 30,
  "is_required": true
}

POST /api/catalog/services/{service_id}/staff-templates

{
  "role_name": "Hair Wash",
  "role_description": "Gentle hair wash post-treatment",
  "sequence_order": 2,
  "contribution_type": "percentage",
  "default_contribution_percent": 25,
  "estimated_duration_minutes": 15,
  "is_required": true
}

POST /api/catalog/services/{service_id}/staff-templates

{
  "role_name": "Hair Drying & Styling",
  "role_description": "Dry and style hair",
  "sequence_order": 3,
  "contribution_type": "percentage",
  "default_contribution_percent": 25,
  "estimated_duration_minutes": 20,
  "is_required": false
}
```

---

## Step 2: Create Bill with Multi-Staff Contributions

### Scenario: Customer gets Botox treatment performed by 3 staff members

**Option A: Simple Percentage-Based Split**

```json
POST /api/pos/bills

{
  "customer_name": "Priya Sharma",
  "customer_phone": "9876543210",
  "items": [
    {
      "service_id": "01HXXX_BOTOX_SERVICE_ID",
      "quantity": 1,
      "staff_contributions": [
        {
          "staff_id": "01STAFF_AAAA",
          "role_in_service": "Botox Application",
          "sequence_order": 1,
          "contribution_split_type": "percentage",
          "contribution_percent": 50
        },
        {
          "staff_id": "01STAFF_BBBB",
          "role_in_service": "Hair Wash",
          "sequence_order": 2,
          "contribution_split_type": "percentage",
          "contribution_percent": 25
        },
        {
          "staff_id": "01STAFF_CCCC",
          "role_in_service": "Hair Drying & Styling",
          "sequence_order": 3,
          "contribution_split_type": "percentage",
          "contribution_percent": 25
        }
      ]
    }
  ]
}
```

**Calculated Contributions:**
- Service Price: ₹5000 (500000 paise)
- Staff A (Application): 50% = ₹2500 (250000 paise)
- Staff B (Hair Wash): 25% = ₹1250 (125000 paise)
- Staff C (Styling): 25% = ₹1250 (125000 paise)
- **Total: 100%**

---

**Option B: Hybrid Calculation (Base % + Time + Skill Weights)**

```json
POST /api/pos/bills

{
  "customer_name": "Priya Sharma",
  "customer_phone": "9876543210",
  "items": [
    {
      "service_id": "01HXXX_BOTOX_SERVICE_ID",
      "quantity": 1,
      "staff_contributions": [
        {
          "staff_id": "01STAFF_AAAA",
          "role_in_service": "Botox Application",
          "sequence_order": 1,
          "contribution_split_type": "hybrid",
          "contribution_percent": 50,
          "time_spent_minutes": 35,
          "notes": "Senior specialist, took extra time for precision"
        },
        {
          "staff_id": "01STAFF_BBBB",
          "role_in_service": "Hair Wash",
          "sequence_order": 2,
          "contribution_split_type": "hybrid",
          "contribution_percent": 25,
          "time_spent_minutes": 12,
          "notes": "Quick and efficient"
        },
        {
          "staff_id": "01STAFF_CCCC",
          "role_in_service": "Hair Drying & Styling",
          "sequence_order": 3,
          "contribution_split_type": "hybrid",
          "contribution_percent": 25,
          "time_spent_minutes": 18
        }
      ]
    }
  ]
}
```

**Hybrid Calculation Formula:**
```
Total Service Amount = ₹5000 (500000 paise)
Total Time Spent = 35 + 12 + 18 = 65 minutes

For each staff member:

Base Component (40% of total):
  ₹5000 × 40% = ₹2000 pool
  Staff A: ₹2000 × 50% = ₹1000
  Staff B: ₹2000 × 25% = ₹500
  Staff C: ₹2000 × 25% = ₹500

Time Component (30% of total):
  ₹5000 × 30% = ₹1500 pool
  Staff A: ₹1500 × (35/65) = ₹808
  Staff B: ₹1500 × (12/65) = ₹277
  Staff C: ₹1500 × (18/65) = ₹415

Skill Component (30% of total):
  ₹5000 × 30% = ₹1500 pool
  Staff A (Application - high skill): 60% = ₹900
  Staff B (Hair Wash - medium): 20% = ₹300
  Staff C (Styling - medium): 20% = ₹300

Final Contributions:
  Staff A: ₹1000 + ₹808 + ₹900 = ₹2708
  Staff B: ₹500 + ₹277 + ₹300 = ₹1077
  Staff C: ₹500 + ₹415 + ₹300 = ₹1215
  Total: ₹5000 ✓
```

---

**Option C: Equal Split (Simple)**

```json
{
  "service_id": "01HXXX_HAIRCUT_SERVICE_ID",
  "quantity": 1,
  "staff_contributions": [
    {
      "staff_id": "01STAFF_AAAA",
      "role_in_service": "Haircut",
      "sequence_order": 1,
      "contribution_split_type": "equal"
    },
    {
      "staff_id": "01STAFF_BBBB",
      "role_in_service": "Styling",
      "sequence_order": 2,
      "contribution_split_type": "equal"
    }
  ]
}
```

**Calculated Contributions:**
- Service Price: ₹800
- Staff A: ₹400 (equal split)
- Staff B: ₹400 (equal split)

---

**Option D: Fixed Amount Split**

```json
{
  "service_id": "01HXXX_PACKAGE_SERVICE_ID",
  "quantity": 1,
  "staff_contributions": [
    {
      "staff_id": "01STAFF_AAAA",
      "role_in_service": "Haircut",
      "sequence_order": 1,
      "contribution_split_type": "fixed",
      "contribution_fixed": 50000  // ₹500
    },
    {
      "staff_id": "01STAFF_BBBB",
      "role_in_service": "Facial",
      "sequence_order": 2,
      "contribution_split_type": "fixed",
      "contribution_fixed": 30000  // ₹300
    }
  ]
}
```

---

## Step 3: Backend Calculation Logic

### Hybrid Contribution Calculator (Python)

```python
# app/services/contribution_calculator.py

from typing import List, Dict
from decimal import Decimal

class ContributionCalculator:
    """Calculate staff contributions for multi-staff services."""

    # Hybrid split weights (must sum to 100)
    BASE_PERCENT_WEIGHT = 40  # % of total allocated by base percentage
    TIME_WEIGHT = 30          # % of total allocated by time spent
    SKILL_WEIGHT = 30         # % of total allocated by skill complexity

    @staticmethod
    def calculate_hybrid(
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate hybrid contributions based on base %, time, and skill.

        Args:
            line_total_paise: Total amount to split (in paise)
            contributions: List of staff contribution dicts with:
                - contribution_percent: base percentage
                - time_spent_minutes: actual time spent
                - role_in_service: role name (for skill weighting)

        Returns:
            Updated contributions with calculated amounts
        """
        total_time = sum(c.get("time_spent_minutes", 0) for c in contributions)

        # Skill weights by role (you can customize these)
        SKILL_WEIGHTS = {
            "Botox Application": 3,  # High skill
            "Hair Wash": 1,          # Low skill
            "Hair Drying & Styling": 2,  # Medium skill
            "Coloring": 3,
            "Cutting": 2,
            # Add more roles as needed
        }

        # Calculate components
        base_pool = int(line_total_paise * ContributionCalculator.BASE_PERCENT_WEIGHT / 100)
        time_pool = int(line_total_paise * ContributionCalculator.TIME_WEIGHT / 100)
        skill_pool = int(line_total_paise * ContributionCalculator.SKILL_WEIGHT / 100)

        total_skill_weight = sum(
            SKILL_WEIGHTS.get(c.get("role_in_service", ""), 1)
            for c in contributions
        )

        for contrib in contributions:
            base_percent = contrib.get("contribution_percent", 0)
            time_minutes = contrib.get("time_spent_minutes", 0)
            role = contrib.get("role_in_service", "")
            skill_weight = SKILL_WEIGHTS.get(role, 1)

            # Base component
            base_component = int(base_pool * base_percent / 100)

            # Time component
            time_component = int(time_pool * time_minutes / total_time) if total_time > 0 else 0

            # Skill component
            skill_component = int(skill_pool * skill_weight / total_skill_weight)

            # Total contribution
            contrib["base_percent_component"] = base_component
            contrib["time_component"] = time_component
            contrib["skill_component"] = skill_component
            contrib["contribution_amount"] = base_component + time_component + skill_component

        # Handle rounding differences (distribute remainder to first staff)
        total_allocated = sum(c["contribution_amount"] for c in contributions)
        remainder = line_total_paise - total_allocated
        if remainder != 0:
            contributions[0]["contribution_amount"] += remainder

        return contributions

    @staticmethod
    def calculate_percentage(
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """Calculate simple percentage-based contributions."""
        total_percent = sum(c.get("contribution_percent", 0) for c in contributions)

        if total_percent != 100:
            raise ValueError(f"Contribution percentages must sum to 100, got {total_percent}")

        for contrib in contributions:
            percent = contrib.get("contribution_percent", 0)
            contrib["contribution_amount"] = int(line_total_paise * percent / 100)

        # Handle rounding
        total_allocated = sum(c["contribution_amount"] for c in contributions)
        remainder = line_total_paise - total_allocated
        if remainder != 0:
            contributions[0]["contribution_amount"] += remainder

        return contributions

    @staticmethod
    def calculate_equal(
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """Calculate equal split among all staff."""
        num_staff = len(contributions)
        base_amount = line_total_paise // num_staff
        remainder = line_total_paise % num_staff

        for i, contrib in enumerate(contributions):
            contrib["contribution_amount"] = base_amount
            # Give remainder to first staff member
            if i == 0:
                contrib["contribution_amount"] += remainder

        return contributions

    @staticmethod
    def calculate_fixed(
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """Use predefined fixed amounts."""
        total_fixed = sum(c.get("contribution_fixed", 0) for c in contributions)

        if total_fixed != line_total_paise:
            raise ValueError(
                f"Fixed contributions ({total_fixed}) must equal line total ({line_total_paise})"
            )

        for contrib in contributions:
            contrib["contribution_amount"] = contrib.get("contribution_fixed", 0)

        return contributions
```

---

## API Endpoints

### Service Template Management

```bash
# Create service with templates
POST /api/catalog/services
POST /api/catalog/services/{service_id}/staff-templates

# List templates for a service
GET /api/catalog/services/{service_id}/staff-templates

# Update template
PATCH /api/catalog/services/{service_id}/staff-templates/{template_id}

# Delete template
DELETE /api/catalog/services/{service_id}/staff-templates/{template_id}

# Get service with templates
GET /api/catalog/services/{service_id}?include_templates=true
```

### Billing with Multi-Staff

```bash
# Create bill with staff contributions
POST /api/pos/bills
Body: { items: [ { service_id, staff_contributions: [...] } ] }

# View bill with contributions
GET /api/pos/bills/{bill_id}
Response includes: items[].staff_contributions[]

# Staff earnings report (future)
GET /api/reports/staff-earnings?staff_id={id}&date_from={date}&date_to={date}
```

---

## Frontend Integration Examples

### React Component: Service Selection with Templates

```typescript
interface ServiceStaffTemplate {
  id: string;
  role_name: string;
  sequence_order: number;
  contribution_type: string;
  default_contribution_percent?: number;
  estimated_duration_minutes: number;
}

interface Service {
  id: string;
  name: string;
  base_price: number;
  staff_templates: ServiceStaffTemplate[];
}

function MultiStaffServiceSelector({ service }: { service: Service }) {
  const [staffAssignments, setStaffAssignments] = useState<{
    [templateId: string]: string; // template ID -> staff ID
  }>({});

  return (
    <div>
      <h3>{service.name} - ₹{service.base_price / 100}</h3>
      <p>This service requires {service.staff_templates.length} staff members:</p>

      {service.staff_templates
        .sort((a, b) => a.sequence_order - b.sequence_order)
        .map(template => (
          <div key={template.id} className="staff-assignment">
            <span>
              {template.sequence_order}. {template.role_name}
            </span>
            <span>
              ({template.contribution_display}) -
              ~{template.estimated_duration_minutes} min
            </span>
            <StaffDropdown
              role={template.role_name}
              onChange={(staffId) => setStaffAssignments({
                ...staffAssignments,
                [template.id]: staffId
              })}
            />
          </div>
        ))}

      <button onClick={() => addToCart(service, staffAssignments)}>
        Add to Cart
      </button>
    </div>
  );
}
```

---

## Migration Plan

### Phase 1: Deploy Infrastructure (Now)
1. ✅ Run database migration
2. ✅ Deploy updated backend models
3. ✅ Test API endpoints

### Phase 2: Service Configuration
1. Identify multi-staff services (Botox, Complex Treatments, etc.)
2. Create staff role templates for each service
3. Define contribution splits (percentage, hybrid, etc.)

### Phase 3: Frontend Updates
1. Update service selection UI to show multi-staff requirements
2. Add staff assignment interface at checkout
3. Update billing confirmation to show per-staff contributions

### Phase 4: Reporting & Commission (Future)
1. Staff earnings aggregation queries
2. Commission calculation rules
3. Payout tracking system

---

## Frequently Asked Questions

### Q: Can I mix single-staff and multi-staff services on the same bill?
**A:** Yes! Use `staff_id` for single-staff services and `staff_contributions` for multi-staff services.

### Q: What happens if contribution percentages don't add up to 100%?
**A:** The system will reject the request with a validation error. Always ensure percentages sum to exactly 100%.

### Q: Can I change the hybrid calculation weights?
**A:** Yes, update the constants in `ContributionCalculator` class:
- `BASE_PERCENT_WEIGHT`
- `TIME_WEIGHT`
- `SKILL_WEIGHT`

### Q: How do I handle tips for multi-staff services?
**A:** Currently, tips can only be assigned to one staff member via `tip_staff_id` on the Bill. For multi-staff tip splitting, you'll need to either:
- Split tips manually based on contributions
- Create a future feature for multi-staff tip distribution

### Q: Can staff members work on multiple services in the same bill?
**A:** Absolutely! Each `BillItem` has its own `staff_contributions` list.

### Q: What if actual time spent differs from estimated?
**A:** For TIME_BASED or HYBRID calculations, use the actual `time_spent_minutes` when creating the bill item. Templates only provide estimates.

---

## Database Schema Reference

### service_staff_templates
```sql
CREATE TABLE service_staff_templates (
    id VARCHAR(26) PRIMARY KEY,
    service_id VARCHAR(26) NOT NULL REFERENCES services(id),
    role_name VARCHAR(100) NOT NULL,
    role_description TEXT,
    sequence_order INTEGER NOT NULL,
    contribution_type contributiontype NOT NULL DEFAULT 'percentage',
    default_contribution_percent INTEGER,
    default_contribution_fixed INTEGER,
    estimated_duration_minutes INTEGER NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX ON service_staff_templates(service_id);
```

### bill_item_staff_contributions
```sql
CREATE TABLE bill_item_staff_contributions (
    id VARCHAR(26) PRIMARY KEY,
    bill_item_id VARCHAR(26) NOT NULL REFERENCES bill_items(id) ON DELETE CASCADE,
    staff_id VARCHAR(26) NOT NULL REFERENCES staff(id),
    role_in_service VARCHAR(100) NOT NULL,
    sequence_order INTEGER NOT NULL,
    contribution_split_type contributionsplittype NOT NULL DEFAULT 'percentage',
    contribution_percent INTEGER,
    contribution_fixed INTEGER,
    contribution_amount INTEGER NOT NULL,
    time_spent_minutes INTEGER,
    base_percent_component INTEGER,
    time_component INTEGER,
    skill_component INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX ON bill_item_staff_contributions(bill_item_id);
CREATE INDEX ON bill_item_staff_contributions(staff_id);
```

---

## Complete Example: End-to-End Flow

### 1. Owner creates "Botox Treatment" service with 3 staff roles
```bash
curl -X POST http://salon.local/api/catalog/services \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Botox Treatment",
    "category_id": "01HCAT001",
    "base_price": 500000,
    "duration_minutes": 65
  }'

# Returns: { "id": "01SERV_BOTOX", ... }

# Add role templates
curl -X POST http://salon.local/api/catalog/services/01SERV_BOTOX/staff-templates \
  -d '{ "role_name": "Application", "sequence_order": 1, "contribution_percent": 50, ... }'
# Repeat for other roles
```

### 2. Receptionist schedules appointment
```bash
curl -X POST http://salon.local/api/appointments \
  -d '{
    "customer_name": "Priya",
    "service_id": "01SERV_BOTOX",
    "scheduled_at": "2025-10-20T14:00:00+05:30"
  }'
```

### 3. Staff perform service, Receptionist creates bill
```bash
curl -X POST http://salon.local/api/pos/bills \
  -d '{
    "customer_name": "Priya",
    "items": [{
      "service_id": "01SERV_BOTOX",
      "staff_contributions": [
        { "staff_id": "01STF_A", "role_in_service": "Application", "sequence_order": 1, "contribution_percent": 50 },
        { "staff_id": "01STF_B", "role_in_service": "Hair Wash", "sequence_order": 2, "contribution_percent": 25 },
        { "staff_id": "01STF_C", "role_in_service": "Styling", "sequence_order": 3, "contribution_percent": 25 }
      ]
    }]
  }'

# Returns: Bill with calculated contributions
# Staff A: ₹2500, Staff B: ₹1250, Staff C: ₹1250
```

### 4. Customer pays, invoice generated
```bash
curl -X POST http://salon.local/api/pos/bills/{bill_id}/payments \
  -d '{ "method": "upi", "amount": 5000.00 }'

# Invoice SAL-25-0123 generated with contribution details
```

---

## Next Steps

1. **Run Migration**: `docker compose exec api uv run alembic upgrade head`
2. **Configure Services**: Add staff templates for multi-person services
3. **Update UI**: Integrate staff assignment at checkout
4. **Train Staff**: Educate receptionists on new workflow
5. **Monitor**: Track contribution accuracy for first few weeks
6. **Iterate**: Adjust contribution formulas based on feedback

---

**Version**: 1.0
**Created**: 2026-02-04
**Status**: Production Ready ✅
