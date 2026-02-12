# Multi-Staff Services - Quick Start Guide

## 🎯 What Problem Does This Solve?

Your salon has services like Botox where **multiple staff work together**:
1. One person does application
2. Another does hair wash
3. Another does drying/styling

**Problem:** Currently, you can only track ONE staff member per service.

**Solution:** This system lets you record ALL staff involved and split the contribution fairly.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Run the Migration

```bash
cd /Users/angelxlakra/dev/efs-salon-os
docker compose exec api uv run alembic upgrade head
```

This creates the new database tables for multi-staff tracking.

---

### Step 2: Configure Your Multi-Staff Services

For each service that needs multiple staff (e.g., Botox), define the roles:

**Example: Botox Treatment (₹5000)**

| Step | Role | Staff Member | Contribution % | Time |
|------|------|--------------|----------------|------|
| 1 | Botox Application | (Any qualified staff) | 50% (₹2500) | 30 min |
| 2 | Hair Wash | (Any staff) | 25% (₹1250) | 15 min |
| 3 | Styling | (Any staff) | 25% (₹1250) | 20 min |

Use the admin panel or API to create these "Service Staff Templates" for each multi-person service.

---

### Step 3: Use at Checkout

When creating a bill for Botox:

**Old Way (Single Staff):**
```json
{
  "service_id": "botox_service",
  "staff_id": "staff_a"  ❌ Only tracks 1 person
}
```

**New Way (Multi-Staff):**
```json
{
  "service_id": "botox_service",
  "staff_contributions": [
    {
      "staff_id": "staff_a",
      "role_in_service": "Botox Application",
      "sequence_order": 1,
      "contribution_percent": 50
    },
    {
      "staff_id": "staff_b",
      "role_in_service": "Hair Wash",
      "sequence_order": 2,
      "contribution_percent": 25
    },
    {
      "staff_id": "staff_c",
      "role_in_service": "Styling",
      "sequence_order": 3,
      "contribution_percent": 25
    }
  ]
}
```

✅ System automatically calculates:
- Staff A earns ₹2500
- Staff B earns ₹1250
- Staff C earns ₹1250

---

## 📊 Contribution Split Methods

### 1. **Percentage-Based (Recommended)**
Best for services with clear role hierarchies.

```
Example: Botox (₹5000)
- Application Specialist: 50% = ₹2500
- Hair Wash Tech: 25% = ₹1250
- Stylist: 25% = ₹1250
Total: 100% ✓
```

### 2. **Equal Split**
Simplest - everyone gets the same amount.

```
Example: Haircut with 2 stylists (₹800)
- Staff A: ₹400
- Staff B: ₹400
```

### 3. **Fixed Amount**
Predefined amounts per role.

```
Example: Package Service (₹2000)
- Haircut: ₹600 (fixed)
- Facial: ₹800 (fixed)
- Massage: ₹600 (fixed)
```

### 4. **Hybrid (Advanced)**
Combines base %, time spent, and skill level.

```
Example: Botox with actual time tracking
- 40% split by base percentage
- 30% split by actual time spent
- 30% split by skill complexity
```

---

## 🔧 Implementation Checklist

- [ ] **Database**: Run migration (`alembic upgrade head`)
- [ ] **Backend**: Models and schemas already created
- [ ] **Services**: Identify which services need multi-staff tracking
- [ ] **Templates**: Create staff role templates for each service
- [ ] **UI**: Update checkout to support staff assignment
- [ ] **Testing**: Test with a few services before full rollout
- [ ] **Training**: Train receptionists on new workflow
- [ ] **Go Live**: Enable for all multi-staff services

---

## 📝 Real-World Example

### Before: Single Staff Tracking ❌

**Scenario:** Priya gets Botox treatment
- 3 staff work on the service
- System only records: "Staff A performed Botox - ₹5000"
- No record of Staff B and C's involvement
- Commission disputes and unfair splits

### After: Multi-Staff Tracking ✅

**Scenario:** Priya gets Botox treatment
- System records:
  - Staff A (Application): ₹2500
  - Staff B (Hair Wash): ₹1250
  - Staff C (Styling): ₹1250
- Clear audit trail of who did what
- Fair contribution splits
- Ready for future commission payouts

---

## 🎨 Frontend Integration

### Service Selection Screen

```
┌─────────────────────────────────────────┐
│  Service: Botox Treatment               │
│  Price: ₹5000                           │
│                                         │
│  This service requires 3 staff:         │
│                                         │
│  1. Botox Application (50%, 30 min)    │
│     [Dropdown: Select Staff ▼]          │
│                                         │
│  2. Hair Wash (25%, 15 min)            │
│     [Dropdown: Select Staff ▼]          │
│                                         │
│  3. Styling (25%, 20 min)              │
│     [Dropdown: Select Staff ▼]          │
│                                         │
│  [Add to Cart]                          │
└─────────────────────────────────────────┘
```

### Bill Summary

```
┌─────────────────────────────────────────┐
│  Invoice: SAL-25-0123                   │
│  Customer: Priya Sharma                 │
│                                         │
│  Services:                              │
│  1. Botox Treatment         ₹5000       │
│     Staff Contributions:                │
│     • Anjali (Application)  ₹2500       │
│     • Pooja (Hair Wash)     ₹1250       │
│     • Meena (Styling)       ₹1250       │
│                                         │
│  Total: ₹5000                           │
└─────────────────────────────────────────┘
```

---

## 🔮 Future Enhancements

### Phase 2 (After Rollout)
- [ ] Staff earnings dashboard
- [ ] Commission calculation rules
- [ ] Automated commission payouts
- [ ] Performance analytics per role
- [ ] Multi-staff tip splitting

### Phase 3 (Advanced)
- [ ] Dynamic contribution adjustment
- [ ] Customer satisfaction impact on splits
- [ ] Skill-based automatic weighting
- [ ] Predictive staffing recommendations

---

## ❓ FAQs

**Q: Do ALL services need multi-staff setup?**
No! Only services that genuinely require multiple people working together. Regular haircuts can stay single-staff.

**Q: Can I change contribution % later?**
Templates are just defaults. You can override contributions at checkout time.

**Q: What if someone calls in sick?**
If a role is marked `is_required: false`, you can skip it. Otherwise, assign another staff member to that role.

**Q: How do I handle tips?**
Currently, tips still go to one staff member (`tip_staff_id`). Multi-staff tip splitting is a future feature.

**Q: Can contributions be different from the template?**
Yes! Templates provide defaults, but you can customize at checkout.

---

## 📞 Support

Need help?
- Check the full guide: `/docs/MULTI_STAFF_SERVICES_GUIDE.md`
- API Reference: `/docs/API_REFERENCE.md`
- File an issue: GitHub Issues

---

**Ready to deploy?** Run the migration and start configuring your multi-staff services! 🚀
