# Ad-Hoc Multi-Staff Assignment Testing Flow
## 🎯 For Services WITHOUT Predefined Templates

**Last Updated**: 2026-02-05
**Status**: Production Ready ✅

---

## Overview

This feature allows you to assign multiple staff members to **ANY service** (even without predefined templates) and adjust their contribution percentages manually.

### Use Cases:
- **Emergency multi-staff situations**: Service normally done by one person, but today you need help
- **Training scenarios**: Senior staff + trainee working together
- **Complex custom services**: One-off services that don't warrant a template
- **Flexible team composition**: Different staff combinations each time

---

## 🚀 Quick Test (2 Minutes)

### Scenario: Haircut with Two Staff (Ad-Hoc Team)

1. **Go to POS** (Dashboard → POS)
2. **Select customer**
3. **Add a regular service** (e.g., "Haircut" - does NOT have templates)
4. Service appears in cart with **single staff** assigned
5. **Click "Add More Staff"** button (below staff name)
6. Dialog opens: "Assign Staff Team"
7. **Add second staff member** from dropdown
8. Percentages **auto-adjust to equal split** (50% each)
9. **Adjust percentages** manually:
   - Staff 1: 60%
   - Staff 2: 40%
10. **Click "Save Team"**
11. Cart updates to show multi-staff team
12. **Checkout** → Payment → Complete

**Expected Result:**
- Bill shows both staff with their contribution amounts
- Staff 1 gets ₹600 (60%)
- Staff 2 gets ₹400 (40%)

---

## 🎬 Complete Testing Flow

### Part A: Add More Staff to Existing Single-Staff Service

#### Test 1: Convert Single-Staff to Multi-Staff

**Setup:**
1. Add any service to cart (e.g., "Haircut" ₹1,000)
2. Assign single staff member (e.g., "John")

**Expected Cart Display:**
```
┌─────────────────────────────────┐
│ Haircut            ₹1,000.00    │
│ ₹1,000.00 each • 30 min         │
│                                  │
│ [John Doe]              [Change]│
│                                  │
│ [➕ Add More Staff]  (Button)   │
│                                  │
│ Qty: [➖] 1 [➕]      ₹1,000.00 │
└─────────────────────────────────┘
```

**Steps:**
1. Click **"Add More Staff"** button
2. Dialog opens with title: "Assign Staff Team"
3. Current staff (John) shows with 100%

**Expected Dialog:**
```
┌─────────────────────────────────────────┐
│  👥 Assign Staff Team                   │
│                                          │
│  Assign multiple staff to Haircut       │
│  and set contribution percentages.      │
│  Total must equal 100%.                 │
├─────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────┐        │
│  │ 1  John Doe       100  %  🗑 │        │
│  │    ₹1,000.00               │        │
│  └─────────────────────────────┘        │
│                                          │
│  Total Contribution: [100%] ✓           │
│                                          │
│  Add Staff Member:                      │
│  [Select staff to add...  ▼]            │
├─────────────────────────────────────────┤
│          [Cancel]    [Save Team]        │
└─────────────────────────────────────────┘
```

4. **Select "Sarah" from dropdown**
5. Percentages auto-adjust:
   - John: 50% (₹500.00)
   - Sarah: 50% (₹500.00)

6. **Manually adjust percentages:**
   - Change John to 60%
   - Change Sarah to 40%

**Expected:**
- Total shows: 100% ✓ (green badge)
- Save button enabled

7. Click **"Save Team"**

**Expected Cart Update:**
```
┌─────────────────────────────────┐
│ Haircut            ₹1,000.00    │
│ ₹1,000.00 each • 30 min         │
│                                  │
│ Staff Team:           [Edit Team]│
│ [Staff 1] [Staff 2]              │
│                                  │
│ Qty: [➖] 1 [➕]      ₹1,000.00 │
└─────────────────────────────────┘
```

✅ **Success:**
- Toast: "Staff team updated"
- "Add More Staff" button replaced with "Edit Team" button
- Staff badges show generic "Staff 1", "Staff 2" labels

#### Test 2: Edit Existing Team

1. Click **"Edit Team"** button
2. Dialog reopens with current team
3. Add third staff member (Tom)
4. Percentages redistribute:
   - John: 33%
   - Sarah: 33%
   - Tom: 34% (gets the remainder)

5. Click **"Equal Split"** button

**Expected:**
- All percentages recalculate:
  - John: 33%
  - Sarah: 33%
  - Tom: 34%
- Total: 100% ✓

6. Save and verify cart updates

#### Test 3: Remove Staff from Team

1. Open "Edit Team" dialog
2. Click trash icon (🗑) next to Tom
3. Team reduces to 2 staff
4. Percentages auto-redistribute:
   - John: 50%
   - Sarah: 50%

5. Save

**Expected:**
- Cart shows only 2 staff badges
- Contributions recalculated

---

### Part B: Validation Tests

#### Test 4: Percentage Must Equal 100%

1. Open team editor
2. Set percentages:
   - Staff 1: 60%
   - Staff 2: 30%
   - Total: 90%

**Expected:**
- Total badge shows: **90%** (red/destructive variant)
- Error text: "Must equal 100%"
- **Save button DISABLED**

3. Adjust Staff 2 to 40%
4. Total becomes 100%

**Expected:**
- Total badge: **100%** (green/default variant)
- **Save button ENABLED**

#### Test 5: Must Have At Least One Staff

1. Open team editor with 1 staff
2. Try to delete the only staff member

**Expected:**
- Trash icon is **DISABLED** (can't remove last staff)

---

### Part C: Complex Scenarios

#### Test 6: Mixed Cart (Templates + Ad-Hoc)

**Add to cart:**
1. Botox (with templates) - 3 staff via predefined roles
2. Haircut (no template) - 2 staff via ad-hoc assignment
3. Facial (no template) - single staff (no ad-hoc)

**Expected Cart:**
```
┌─────────────────────────────────────┐
│ Botox                    ₹4,000.00  │
│ Staff Team:                [Edit Team]│
│ [Application Specialist]            │
│ [Hair Wash & Dry]                   │
│ [Styling Artist]                    │
├─────────────────────────────────────┤
│ Haircut                  ₹1,000.00  │
│ Staff Team:                [Edit Team]│
│ [Staff 1] [Staff 2]                 │
├─────────────────────────────────────┤
│ Facial                     ₹800.00  │
│ [Maria Santos]              [Change]│
│ [➕ Add More Staff]                 │
└─────────────────────────────────────┘
```

**Checkout:**
- All services process correctly
- Bill shows:
  - Botox: 3 contributions (from templates)
  - Haircut: 2 contributions (ad-hoc)
  - Facial: 1 contribution (single staff)

#### Test 7: Contribution Amount Calculation

**Service Price:** ₹1,500
**Team:**
- Staff A: 50% = ₹750
- Staff B: 30% = ₹450
- Staff C: 20% = ₹300

**Verify in dialog:**
- Each staff shows their rupee amount below their name
- Total contributions = ₹1,500

**After checkout, verify in bill:**
```sql
SELECT
  bi.item_name,
  sc.role_in_service,
  sc.contribution_percent,
  sc.contribution_amount / 100.0 as amount_rupees
FROM bill_item_staff_contributions sc
JOIN bill_items bi ON bi.id = sc.bill_item_id
WHERE bi.item_name = 'Haircut';

-- Expected:
-- Staff 1  |  50  |  750.00
-- Staff 2  |  30  |  450.00
-- Staff 3  |  20  |  300.00
```

---

## ✅ Feature Checklist

### UI/UX
- [ ] "Add More Staff" button appears on single-staff service items
- [ ] "Edit Team" button appears on multi-staff items
- [ ] Dialog opens with current assignments
- [ ] Can add staff from dropdown
- [ ] Can remove staff (except last one)
- [ ] Percentages show next to staff names
- [ ] Rupee amounts calculated and displayed
- [ ] Total percentage badge updates in real-time
- [ ] "Equal Split" button redistributes evenly

### Validation
- [ ] Cannot save if total ≠ 100%
- [ ] Cannot save if no staff assigned
- [ ] Cannot delete last staff member
- [ ] Percentage inputs accept 0-100
- [ ] Save button enabled only when valid

### Data Flow
- [ ] Single staff + percentages → staff_contributions array
- [ ] Multiple staff → each gets a contribution entry
- [ ] Generic roles: "Staff 1", "Staff 2", "Staff 3"
- [ ] Sequence order preserved (1, 2, 3...)
- [ ] contribution_split_type = 'percentage'
- [ ] Backend receives correct payload

### Integration
- [ ] Works with template-based services in same cart
- [ ] Works with single-staff services in same cart
- [ ] Works with products in same cart
- [ ] Checkout creates correct bill structure
- [ ] Bill display shows all contributions
- [ ] Commission reports include ad-hoc contributions

---

## 🔄 Comparison: Templates vs Ad-Hoc

| Feature | With Templates | Ad-Hoc (No Template) |
|---------|---------------|----------------------|
| **Setup Required** | Configure roles in Services page | None - add staff on-the-fly |
| **Role Names** | Predefined (Application Specialist, etc.) | Generic (Staff 1, Staff 2, etc.) |
| **Assignment UI** | Role-based selector in service grid | "Add More Staff" in cart |
| **Default Split** | Predefined percentages | Equal split |
| **Edit in Cart** | ✅ Yes, via "Edit Team" | ✅ Yes, via "Edit Team" |
| **Best For** | Repeatable multi-staff services | One-off or flexible scenarios |

---

## 🎯 User Training Script

**Receptionist:**
> "If you need help from another staff member for a service, just click 'Add More Staff' after adding it to the cart. The system will split it 50/50 automatically, or you can adjust the percentages yourself."

**Example Dialogue:**

**Receptionist:** "John is doing a haircut but Sarah is helping. Let me add both..."

1. Add Haircut → Assigned to John
2. Click "Add More Staff"
3. Select Sarah
4. System shows: John 50%, Sarah 50%
5. Receptionist: "John is doing most of it..."
6. Adjust: John 70%, Sarah 30%
7. Save

**Result:** John gets ₹700, Sarah gets ₹300 from ₹1,000 haircut.

---

## 🐛 Troubleshooting

### Issue: Can't save team
**Check:** Total percentage = 100%?
**Fix:** Adjust percentages until total shows green 100% badge

### Issue: "Add More Staff" button not showing
**Possible causes:**
- Service is a product (products don't have staff)
- Service already has multi-staff team (use "Edit Team" instead)

### Issue: Staff dropdown is empty
**Check:** Are there active staff members?
**Check:** Are all staff already assigned?

### Issue: Contribution amounts don't match percentages
**Verify:** Service price × percentage / 100 = contribution amount
**Example:** ₹1,500 × 60% / 100 = ₹900

### Issue: Bill doesn't show contributions
**Check:** Did you save the team before checkout?
**Check:** API logs for errors during bill creation

---

## 📊 Success Metrics

After testing, you should have:
- ✅ At least 1 bill with ad-hoc multi-staff contributions
- ✅ Verified percentages sum to 100%
- ✅ Verified contribution amounts are correct
- ✅ Database shows:
  - `role_in_service` = "Staff 1", "Staff 2", etc.
  - `contribution_split_type` = "percentage"
  - `contribution_percent` matches what you set

---

## 🚀 Production Tips

### When to Use Ad-Hoc vs Templates

**Use Ad-Hoc when:**
- Service composition varies each time
- One-off custom services
- Emergency help situations
- Training scenarios (mentor + trainee)
- Client requests specific staff combinations

**Use Templates when:**
- Service ALWAYS needs multiple staff
- Roles are consistent (Application → Wash → Style)
- Want to enforce role requirements
- Need role-specific time tracking
- Service is frequently ordered

### Best Practices

1. **Start with Single Staff:**
   - Add service with primary staff first
   - Only add more if actually needed

2. **Quick Equal Split:**
   - Use "Equal Split" button for speed
   - Manual adjustments only when necessary

3. **Communicate with Staff:**
   - Inform staff about split arrangements
   - Ensure they know who's doing what

4. **Review Bills:**
   - Check contribution amounts make sense
   - Verify staff are happy with splits

---

## 🔗 Related Documentation

- **Main Testing Flow**: `MULTI_STAFF_TESTING_FLOW.md`
- **Template Management**: Services → Staff Roles
- **Backend API**: `/docs/MULTI_STAFF_SERVICES_GUIDE.md`
- **Database Schema**: `bill_item_staff_contributions` table

---

## 📝 Quick Reference

### Keyboard Shortcuts
- `Tab`: Navigate between percentage inputs
- `Enter`: Save team (when valid)
- `Esc`: Cancel and close dialog

### Common Percentage Splits
- **Equal (2 staff)**: 50% / 50%
- **Equal (3 staff)**: 33% / 33% / 34%
- **Senior + Junior**: 70% / 30%
- **Lead + 2 Assistants**: 50% / 25% / 25%
- **Trainer + Trainee**: 80% / 20%

---

**Questions? Issues?**
- Check browser console for errors
- Verify API logs: `docker compose logs -f api`
- Test with simple 2-staff scenario first

Happy multi-staffing! 🎉
