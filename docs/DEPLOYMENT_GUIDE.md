# Deployment Guide - Expense Tracking & Retail Sales

**Date:** January 29, 2026
**Status:** ✅ Ready for Production

---

## 🚀 Quick Deployment (Recommended)

Run these commands in order:

```bash
cd /Users/angelxlakra/dev/efs-salon-os

# 1. Apply database migration
docker exec salon-api alembic upgrade head

# 2. Restart backend services
docker restart salon-api salon-worker

# 3. Rebuild and restart frontend
cd frontend
npm run build
cd ..
docker-compose up -d --build frontend

# 4. Verify deployment
curl http://salon.local/api/healthz
curl http://salon.local
```

---

## 📋 Step-by-Step Deployment

### Step 1: Backend Migration

```bash
# Apply database migration (adds expense tables, retail fields, COGS fields)
docker exec salon-api alembic upgrade head

# Verify migration applied
docker exec salon-api alembic current
# Should show: 6a7b8c9d0e1f (head)
```

**What this does:**
- Creates `expenses` table with approval workflow
- Adds `is_sellable`, `retail_price`, `retail_markup_percent` to SKUs
- Modifies `bill_items` to support products (adds `sku_id`, `cogs_amount`)
- Adds `tip_amount`, `tip_staff_id` to bills
- Adds actual profit fields to `day_summary`
- Creates `service_material_usage` table

---

### Step 2: Restart Backend Services

```bash
# Restart API server to load new code
docker restart salon-api

# Restart background worker for recurring expense job
docker restart salon-worker

# Check logs for errors
docker logs salon-api --tail 50
docker logs salon-worker --tail 50
```

**Verify API health:**
```bash
curl http://salon.local/api/healthz
# Should return: {"status":"healthy"}
```

---

### Step 3: Deploy Frontend

```bash
cd frontend

# Build production bundle
npm run build
# Should complete with no errors

# Return to root and rebuild container
cd ..
docker-compose up -d --build frontend

# Check frontend is running
docker ps | grep salon-frontend
```

**Verify frontend:**
```bash
curl http://salon.local
# Should return HTML
```

---

### Step 4: Verify New Features

#### Test Expense Management
1. Navigate to: http://salon.local/dashboard/expenses
2. Click "Create Expense"
3. Fill in details and save
4. Verify expense appears in list

#### Test Inventory Retail Settings
1. Navigate to: http://salon.local/dashboard/inventory
2. Click "Edit" on any SKU
3. Check "Mark as sellable in POS"
4. Enter retail price (e.g., 100)
5. Save changes

#### Test POS Retail Products
1. Navigate to: http://salon.local/dashboard/pos
2. Click "Products" tab
3. Verify sellable products appear
4. Add product to cart
5. Add a service to cart
6. Checkout with mixed cart

#### Test P&L Report
1. Navigate to: http://salon.local/dashboard/reports
2. Click "Profit & Loss Statement"
3. Select date range
4. Click "Generate Report"
5. Verify all sections display correctly

---

## 🔍 Verification Checklist

### Backend Verification

```bash
# 1. Check migration status
docker exec salon-api alembic current

# 2. Verify API endpoints exist
curl http://salon.local/api/docs
# Check for:
# - /api/expenses
# - /api/catalog/retail-products
# - /api/reports/profit-loss

# 3. Test expense creation
curl -X POST http://salon.local/api/expenses \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "utilities",
    "amount": 100000,
    "expense_date": "2026-01-29",
    "description": "Test expense",
    "requires_approval": false
  }'

# 4. Test retail products endpoint
curl http://salon.local/api/catalog/retail-products \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Verify background job scheduled
docker exec salon-worker python -c "from app.jobs.scheduled import scheduler; print([str(job) for job in scheduler.get_jobs()])"
```

### Frontend Verification

- [ ] Can access /dashboard/expenses
- [ ] Can access /dashboard/inventory
- [ ] Can access /dashboard/reports
- [ ] Can access /dashboard/reports/profit-loss
- [ ] POS has Products tab
- [ ] Navigation menu shows Expenses (owner only)
- [ ] Navigation menu shows Inventory

### Database Verification

```bash
# Connect to database
docker exec -it salon-postgres psql -U salon_user -d salon_db

# Check expenses table exists
\d expenses;

# Check SKU has retail fields
\d skus;

# Check bill_items has sku_id
\d bill_items;

# Exit
\q
```

---

## 🐛 Troubleshooting

### Migration Fails

**Error:** `Target database is not up to date`

```bash
# Check current version
docker exec salon-api alembic current

# View migration history
docker exec salon-api alembic history

# If needed, rollback one step
docker exec salon-api alembic downgrade -1

# Then retry upgrade
docker exec salon-api alembic upgrade head
```

---

### API Container Unhealthy

**Check logs:**
```bash
docker logs salon-api --tail 100
```

**Common issues:**
- Missing environment variables
- Database connection failed
- Import errors

**Fix:**
```bash
# Restart with fresh logs
docker restart salon-api
docker logs salon-api -f
```

---

### Frontend Build Errors

**If build fails:**
```bash
cd frontend

# Check for TypeScript errors
npm run build

# If errors, check recent file changes
git status
git diff
```

**Common issues:**
- Missing dependencies: `npm install`
- Type errors: Check error message and fix types
- Import errors: Verify file paths

---

### Products Not Showing in POS

**Checklist:**
1. SKU marked as `is_sellable=true`
2. SKU has `retail_price` set
3. SKU has `current_stock > 0`
4. API endpoint returns products:
   ```bash
   curl http://salon.local/api/catalog/retail-products \
     -H "Authorization: Bearer TOKEN"
   ```

**Fix via database:**
```bash
docker exec -it salon-postgres psql -U salon_user -d salon_db

UPDATE skus
SET is_sellable = true,
    retail_price = 10000,  -- ₹100 in paise
    retail_markup_percent = 50.0
WHERE id = 'YOUR_SKU_ID';

\q
```

---

### Recurring Expense Job Not Running

**Verify job is scheduled:**
```bash
docker logs salon-worker | grep "recurring_expenses"
```

**Check scheduler:**
```bash
docker exec salon-worker python -c "
from app.jobs.scheduled import scheduler
from datetime import datetime
print('Jobs:', scheduler.get_jobs())
print('Next run:', scheduler.get_jobs()[0].next_run_time if scheduler.get_jobs() else 'No jobs')
"
```

**Manual trigger (for testing):**
```bash
docker exec salon-worker python -c "
from app.database import SessionLocal
from app.jobs.scheduled import generate_recurring_expenses_job
db = SessionLocal()
try:
    generate_recurring_expenses_job()
    print('Job executed successfully')
finally:
    db.close()
"
```

---

## 📊 Post-Deployment Tasks

### 1. Initial Data Setup

**Create recurring expenses (rent, salaries):**
1. Go to http://salon.local/dashboard/expenses
2. Click "Create Expense"
3. Fill in:
   - Category: Rent
   - Amount: Your monthly rent
   - Date: First day of current month
   - Description: "Monthly rent"
   - ✅ Recurring Expense
   - Frequency: Monthly
4. Submit
5. Repeat for salaries, utilities, etc.

**Mark products as sellable:**
1. Go to http://salon.local/dashboard/inventory
2. For each retail product:
   - Click "Edit"
   - ✅ Mark as sellable in POS
   - Enter retail price
   - Save

### 2. Train Staff

**Show staff:**
- How to add products to cart (Products tab in POS)
- Mixed cart checkout (services + products)
- Product stock indicators

**Show owner:**
- Expense creation and approval
- P&L report generation
- Inventory retail settings

### 3. Generate First Reports

**After 1 week:**
1. Record all expenses for the week
2. Sell some retail products
3. Generate P&L report
4. Compare actual profit vs old 30% estimate

---

## 🎯 Success Criteria

Your deployment is successful when:

- [x] Migration applied without errors
- [x] All API endpoints respond
- [x] Frontend builds and loads
- [x] Can create and approve expenses
- [x] Can mark SKUs as sellable
- [x] Products appear in POS
- [x] Can checkout with products
- [x] P&L report displays data
- [x] Recurring expense job scheduled
- [x] No errors in logs

---

## 📞 Support

**Check documentation:**
- IMPLEMENTATION_COMPLETE.md - Full feature overview
- BUILD_FIXES_SUMMARY.md - Recent fixes
- API docs: http://salon.local/api/docs

**Check logs:**
```bash
# API logs
docker logs salon-api -f

# Worker logs
docker logs salon-worker -f

# Frontend logs
docker logs salon-frontend -f

# Database logs
docker logs salon-postgres -f
```

---

**Deployment Date:** January 29, 2026
**Version:** 1.0.0 (Expense Tracking & Retail Sales)
**Status:** ✅ Production Ready
