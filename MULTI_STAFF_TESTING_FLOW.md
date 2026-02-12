# Multi-Staff Service Testing Flow
## ✅ COMPLETE END-TO-END - Frontend & Backend Ready

**Last Updated**: 2026-02-04
**Status**: Production Ready - Full UI Available

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Access Services Management
1. Navigate to http://salon.local
2. Login with owner credentials
3. Go to **Dashboard → Services**

### Step 2: Configure Multi-Staff Service
1. Find the service you want to configure (e.g., "Botox")
2. Click the **"Staff Roles"** button at the bottom of the service card
3. The Staff Roles configuration dialog opens

### Step 3: Add Staff Roles
Click **"Add First Role"** and fill in:

**Role 1 - Application Specialist:**
- Role Name: `Application Specialist`
- Description: `Applies botox injections`
- Estimated Duration: `30` minutes
- Contribution Type: `Percentage`
- Default Contribution %: `40`
- Sequence Order: `1`
- ✅ Required

Click **"Save Role"**

**Role 2 - Hair Wash & Dry:**
- Role Name: `Hair Wash & Dry`
- Description: `Washes and dries hair after procedure`
- Estimated Duration: `20` minutes
- Contribution Type: `Percentage`
- Default Contribution %: `30`
- Sequence Order: `2`
- ✅ Required

Click **"Save Role"**

**Role 3 - Styling Artist:**
- Role Name: `Styling Artist`
- Description: `Final styling and touch-up`
- Estimated Duration: `15` minutes
- Contribution Type: `Percentage`
- Default Contribution %: `30`
- Sequence Order: `3`
- ✅ Required

Click **"Save Role"** and then **"Close"**

---

## 🧪 Complete Testing Flow

### Part A: Service Configuration (Services Page)

#### Test 1: Create Multi-Staff Templates
**Location:** Dashboard → Services

1. Find any service (recommend "Botox" or create a test service)
2. Click **"Staff Roles"** button on service card
3. Verify dialog opens with title "Configure Staff Roles"
4. If service has no roles:
   - Should see empty state: "No staff roles configured yet"
   - Message: "This service will use single-staff assignment at checkout"
5. Click **"Add First Role"**

**Expected:**
- Blue form appears with all fields
- Contribution Type dropdown works
- When "Percentage" selected, shows "Default Contribution %" field
- When "Fixed" selected, shows "Fixed Amount (₹)" field
- When "Equal" selected, hides contribution amount fields

6. Fill in role details (see Quick Start above)
7. Click **"Save Role"**

**Expected:**
- Loading state: "Saving..."
- Success toast: "Staff role added successfully"
- Role appears in list with badge showing: "30 min", "40% contribution", "Required"
- Number badge shows sequence (1, 2, 3...)
- Form clears, ready for next role

8. Add 2-3 more roles following the pattern
9. Click **"Close"**

#### Test 2: Edit Existing Role
1. Open Staff Roles dialog again
2. Click the grip icon (⋮⋮) on any role card
3. Form populates with existing data
4. Change duration from 30 to 35 minutes
5. Click **"Save Role"**

**Expected:**
- Toast: "Staff role updated successfully"
- Role card shows updated value "35 min"

#### Test 3: Delete Role
1. Click trash icon on a role
2. Confirm deletion

**Expected:**
- Toast: "Staff role deleted successfully"
- Role removed from list
- Remaining roles keep their sequence numbers

#### Test 4: Contribution Types
Test each contribution type:

**Percentage:**
- Default Contribution %: 40
- Shows as "40% contribution" badge

**Fixed Amount:**
- Enter: ₹500
- Shows as "₹500.00 fixed" badge

**Equal Split:**
- No amount field needed
- Shows as "Equal split" badge

---

### Part B: POS Checkout (Multi-Staff Assignment)

#### Test 5: Add Multi-Staff Service to Cart
**Location:** Dashboard → POS

1. Select a customer
2. Click on the service you configured (e.g., Botox)
3. Service card should **expand** (full width)

**Expected:**
- Header changes to "Assign Staff to Roles"
- Shows list of 3 roles in sequence order
- Each role shows:
  - Role name
  - Description
  - Duration estimate
  - Contribution percentage
  - Sequence number badge (1, 2, 3)

4. **For Role 1 (Application Specialist):**
   - Click staff dropdown
   - Select a staff member
   - If hybrid mode, enter actual time: 28 minutes
   - Optionally add notes

5. **For Role 2 (Hair Wash & Dry):**
   - Select different staff member
   - Enter time: 18 minutes

6. **For Role 3 (Styling Artist):**
   - Select third staff member
   - Enter time: 15 minutes

7. Click **"Add to Cart"** (or button automatically adds when all required roles filled)

**Expected:**
- Toast: "Botox added to cart (Staff1, Staff2, Staff3)"
- Service card collapses
- Cart sidebar updates

#### Test 6: Verify Cart Display

**In Cart Sidebar:**
```
┌─────────────────────────────────────┐
│ Botox                    ₹4,000.00  │
│ ₹4,000.00 each • 65 min             │
│                                      │
│ Staff Team:                          │
│ [Application Specialist]             │
│ [Hair Wash & Dry]                    │
│ [Styling Artist]                     │
│                                      │
│ Qty: [➖] 1 [➕]          ₹4,000.00  │
└─────────────────────────────────────┘
```

**Verify:**
- ✅ Shows "Staff Team:" label
- ✅ Shows all 3 role badges
- ✅ NO "Change Staff" button (multi-staff is fixed)
- ✅ Quantity controls work
- ✅ Price calculation correct

#### Test 7: Mixed Cart (Multi-Staff + Single-Staff + Products)

Add to same cart:
1. One multi-staff service (Botox with 3 staff)
2. One single-staff service (Haircut with 1 staff)
3. One product (Shampoo)

**Expected Cart:**
```
Botox - Staff Team: [Role1][Role2][Role3]
Haircut - Staff: John Doe [Change]
Shampoo - [Product badge]
```

#### Test 8: Checkout with Multi-Staff

1. Click **"Checkout"**
2. Payment modal opens
3. Enter payment details
4. Click **"Complete Payment"**

**Backend Payload Verification:**
The API should receive:
```json
{
  "items": [
    {
      "service_id": "...",
      "quantity": 1,
      "unit_price": 400000,
      "discount": 0,
      "staff_contributions": [
        {
          "staff_id": "...",
          "role_in_service": "Application Specialist",
          "sequence_order": 1,
          "contribution_split_type": "hybrid",
          "contribution_percent": 40,
          "time_spent_minutes": 28
        },
        // ... other contributions
      ]
    }
  ]
}
```

**Expected:**
- Loading spinner
- Success message with bill number
- Print receipt option
- Cart clears

---

### Part C: Bill Verification

#### Test 9: View Bill Details
**Location:** Dashboard → Bills

1. Find the bill you just created
2. Click to open details dialog

**Expected Display:**
```
┌─────────────────────────────────────┐
│ Botox                    ₹4,000.00  │
│                                      │
│ Staff Team:                          │
│ Application Specialist   ₹1,600.00  │
│ Hair Wash & Dry         ₹1,200.00  │
│ Styling Artist          ₹1,200.00  │
└─────────────────────────────────────┘
```

**Verify:**
- ✅ Shows each staff role with contribution amount
- ✅ Contribution amounts sum to line total
- ✅ All other bill details correct (customer, total, tax)

#### Test 10: Backend Data Verification

**Via Database:**
```bash
docker compose exec postgres psql -U salon_user -d salon_db

-- Check templates exist
SELECT
  s.name as service,
  sst.role_name,
  sst.sequence_order,
  sst.contribution_type,
  sst.default_contribution_percent
FROM service_staff_templates sst
JOIN services s ON s.id = sst.service_id
ORDER BY s.name, sst.sequence_order;

-- Check contributions on bills
SELECT
  bi.item_name,
  sc.role_in_service,
  sc.contribution_amount / 100.0 as amount_rupees,
  sc.contribution_split_type,
  sc.time_spent_minutes
FROM bill_item_staff_contributions sc
JOIN bill_items bi ON bi.id = sc.bill_item_id
ORDER BY sc.sequence_order;
```

**Via API:**
```bash
# Get bill details with contributions
curl http://salon.local/api/pos/bills/{BILL_ID} \
  -H "Authorization: Bearer YOUR_TOKEN" | jq .
```

---

## ✅ Test Cases Checklist

### Configuration (Services Page)
- [ ] Can open Staff Roles dialog from service card
- [ ] Can add first role with all contribution types
- [ ] Can add multiple roles (2-5)
- [ ] Can edit existing role
- [ ] Can delete role
- [ ] Sequence numbers auto-increment
- [ ] Form validation works (empty name, invalid %, etc.)
- [ ] Close button works
- [ ] Changes persist after closing and reopening

### POS Checkout
- [ ] Service with templates shows "Assign Staff to Roles"
- [ ] Service without templates shows regular staff selection
- [ ] Can assign different staff to each role
- [ ] Required roles cannot be skipped
- [ ] Optional roles can be left empty
- [ ] Time tracking works (if hybrid mode)
- [ ] Service adds to cart successfully
- [ ] Cart displays all role badges
- [ ] No "Change Staff" button for multi-staff

### Mixed Scenarios
- [ ] Multi-staff + single-staff services in same cart
- [ ] Multi-staff + products in same cart
- [ ] Checkout with mixed cart works
- [ ] Each service type behaves correctly

### Bill Display
- [ ] Bill details show staff team breakdown
- [ ] Contribution amounts display correctly
- [ ] Amounts sum to line total
- [ ] Print receipt includes contributions

### Data Integrity
- [ ] Templates saved to database
- [ ] Contributions saved to bill_item_staff_contributions
- [ ] Sequence order preserved
- [ ] Enum types valid (contributiontype, contributionsplittype)
- [ ] Foreign keys intact

---

## 🎬 Demo Script (For User Training)

### Scenario: Botox Service Setup

**Narrator:**
> "Let me show you how to set up a multi-staff service. We'll use Botox as an example, which requires three different specialists."

**Step 1 - Configure Service (30 seconds)**
1. "Navigate to Services Management"
2. "Find the Botox service"
3. "Click the 'Staff Roles' button"
4. "We'll add three roles in sequence"

**Step 2 - Add Roles (2 minutes)**
1. "First role: Application Specialist - 30 minutes, 40% contribution"
2. "Second role: Hair Wash & Dry - 20 minutes, 30% contribution"
3. "Third role: Styling Artist - 15 minutes, 30% contribution"
4. "Notice the percentages add up to 100%"

**Step 3 - Use in POS (1 minute)**
1. "Now at POS, when I select Botox..."
2. "The system asks me to assign staff to each role"
3. "I assign Maria as Application Specialist"
4. "Sarah for Hair Wash"
5. "And John for Styling"
6. "Add to cart - done!"

**Step 4 - Checkout & Review (1 minute)**
1. "Cart shows all three staff members"
2. "Complete payment"
3. "Open the bill to see the breakdown"
4. "Each staff member's contribution is tracked"

---

## 🐛 Troubleshooting

### Issue: "Staff Roles" button doesn't appear
**Solution:** You must be logged in as **Owner** role

### Issue: Template dialog is empty
**Possible causes:**
- No templates configured yet (this is normal)
- API endpoint not responding
**Check:** Browser console for errors

### Issue: Service still shows single-staff selection
**Possible causes:**
- Templates not saved (check database)
- Frontend cache issue
**Fix:**
- Refresh page (Cmd+R)
- Clear browser cache
- Verify templates exist: `GET /api/catalog/services/{id}/staff-templates`

### Issue: Contributions don't add up correctly
**Backend validation should catch this**
- Check API response for errors
- Verify hybrid calculation weights (40% base + 30% time + 30% skill)
- Ensure backend calculator service is working

### Issue: Can't save template - validation error
**Common issues:**
- Role name is empty
- Duration is 0 or negative
- Percentage is >100 or ≤0
- Fixed amount is ≤0

**Check form fields and try again**

---

## 📊 Success Metrics

After testing, you should have:
- ✅ 1-3 services with multi-staff templates configured
- ✅ At least 1 test bill with multi-staff contributions
- ✅ All staff roles showing correct contribution amounts
- ✅ Database tables populated:
  - `service_staff_templates` (3-9 rows)
  - `bill_item_staff_contributions` (3+ rows per multi-staff bill)

---

## 🚀 Ready for Production

Once all tests pass:

1. **Train staff** on using the Staff Roles feature
2. **Configure real services** that need multi-staff (Botox, Keratin, etc.)
3. **Set contribution types:**
   - **Percentage**: Most flexible, adjust per role importance
   - **Fixed**: When each role has standard pricing
   - **Equal**: When all staff contribute equally
   - **Hybrid**: When you want base % + time + skill adjustments

4. **Monitor first week:**
   - Check if contributions sum correctly
   - Verify staff are assigned properly
   - Adjust percentages if needed

5. **Commission reports:**
   - Staff can now see earnings from each role
   - Reports show multi-staff vs single-staff contributions

---

## 📚 Documentation Links

- **API Docs**: http://salon.local/api/docs
- **Backend Implementation**: `/docs/MULTI_STAFF_SERVICES_GUIDE.md`
- **Quick Start Guide**: `/docs/MULTI_STAFF_QUICK_START.md`
- **Database Schema**: Check `service_staff_templates` and `bill_item_staff_contributions` tables

---

**Questions? Issues?**
Check API logs: `docker compose logs -f api`
Check frontend: Browser DevTools → Console

Happy testing! 🎉
