# Bug Fixes: Timezone & Customer Search

## Issues Fixed

### 1. ❌ Receipt Shows Wrong Time (UTC instead of IST)
### 2. ❌ Customer Search Only Works on Current Page
### 3. ❌ Customer List Missing Pagination Controls

---

## Issue 1: Receipt Time Shows UTC Instead of IST

### Root Cause
Throughout the codebase, `datetime.utcnow()` was used which creates timezone-naive UTC timestamps. When displayed on receipts, they weren't converted to IST, showing wrong times (5.5 hours behind).

### Files Fixed

#### A. **Billing Service** (`app/services/billing_service.py`)
**Changed**: All `datetime.utcnow()` → `datetime.now(IST)`

Affected operations:
- Payment confirmation timestamps
- Bill posting timestamps  
- Refund timestamps
- Customer last visit tracking

```python
# BEFORE
payment.confirmed_at = datetime.utcnow()
bill.posted_at = datetime.utcnow()
customer.last_visit_at = datetime.utcnow()

# AFTER  
payment.confirmed_at = datetime.now(IST)
bill.posted_at = datetime.now(IST)
customer.last_visit_at = datetime.now(IST)
```

#### B. **Expenses API** (`app/api/expenses.py`)
**Changed**: Expense recording and approval timestamps now use IST

```python
# BEFORE
recorded_at=datetime.utcnow()
approved_at=datetime.utcnow()

# AFTER
recorded_at=datetime.now(IST)
approved_at=datetime.now(IST)
```

#### C. **Purchases API** (`app/api/purchases.py`)
**Changed**: Purchase receipt timestamps now use IST

```python
# BEFORE
received_at = receipt_data.received_at or datetime.utcnow()
recorded_at=datetime.utcnow()

# AFTER
received_at = receipt_data.received_at or datetime.now(IST)
recorded_at=datetime.now(IST)
```

#### D. **Auth Router** (`app/auth/router.py`)
**Changed**: User login timestamps now use IST

```python
# BEFORE
user.last_login_at = datetime.utcnow()

# AFTER
user.last_login_at = datetime.now(IST)
```

#### E. **Receipt Service** (`app/services/receipt_service.py`)
**Changed**: Receipt display now converts timestamps to IST

```python
# BEFORE (direct formatting, no timezone conversion)
invoice_date = bill.created_at.strftime("%d/%m/%Y %I:%M %p")

# AFTER (converts UTC to IST before formatting)
if bill.created_at.tzinfo is None:
    # If naive, assume UTC and convert to IST
    bill_time_ist = pytz.utc.localize(bill.created_at).astimezone(IST)
else:
    # If aware, convert to IST
    bill_time_ist = bill.created_at.astimezone(IST)

invoice_date = bill_time_ist.strftime("%d/%m/%Y %I:%M %p")
```

**Why this approach?**
- Handles both timezone-aware and naive datetimes
- Backward compatible with existing data (assumes UTC for naive timestamps)
- Future-proof for when database fully uses timezone-aware timestamps

### What Wasn't Changed

**JWT Tokens** (`app/auth/jwt.py`):
- Still uses `datetime.utcnow()` 
- **This is correct** - JWT standard requires UTC timestamps
- Tokens are validated, not displayed to users

---

## Issue 2: Customer Search Only Works on Current Page

### Root Cause
The frontend was likely filtering search results AFTER fetching paginated data, so it could only search the 20 customers on the current page.

### Solution
Added dedicated autocomplete endpoint that searches **entire database**, not just current page.

### New Endpoint: `/api/customers/autocomplete`

**File**: `app/api/customers.py`

```python
@router.get("/autocomplete", response_model=CustomerListResponse)
def autocomplete_customers(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fast autocomplete search across ALL customers by name or phone."""
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))

    # Search by name OR phone
    search_filter = or_(
        Customer.first_name.ilike(f"%{q}%"),
        Customer.last_name.ilike(f"%{q}%"),
        Customer.phone.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)

    # Order by most recent first
    query = query.order_by(Customer.last_visit_at.desc().nullslast())

    # Limit results for autocomplete
    items = query.limit(limit).all()

    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "size": limit,
        "pages": 1
    }
```

### Key Features

✅ **Searches entire database** - not limited to current page  
✅ **Fast** - limits results to 10 by default  
✅ **Flexible search** - matches first name, last name, OR phone  
✅ **Smart ordering** - shows recently visited customers first  
✅ **Partial matching** - finds "john" in "Johnny Smith"  

### Usage

**For POS Customer Selection (Frontend)**:
```javascript
// OLD (paginated search - only searches current page)
GET /api/customers?page=1&size=20&search=john

// NEW (autocomplete - searches all customers)
GET /api/customers/autocomplete?q=john&limit=10
```

**Response**:
```json
{
  "items": [
    {
      "id": "01HXX...",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+91 98765 43210",
      "email": "john@example.com",
      "total_visits": 5,
      "total_spent": 350000
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### Frontend Integration Needed

The frontend POS component needs to be updated to use the new endpoint:

```javascript
// In your POS customer search component
const searchCustomers = async (query) => {
  if (query.length < 2) return [];
  
  const response = await fetch(
    `/api/customers/autocomplete?q=${encodeURIComponent(query)}&limit=10`
  );
  
  return response.json();
};
```

---

## Issue 3: Customer List Missing Pagination Controls

### Status
**Backend is ready** - the `/api/customers` endpoint already supports proper pagination:

```http
GET /api/customers?page=1&size=20&search=john
```

Returns:
```json
{
  "items": [...],
  "total": 45,     // Total matching customers
  "page": 1,       // Current page
  "size": 20,      // Items per page
  "pages": 3       // Total pages
}
```

### Frontend Fix Needed
The frontend customer list component needs to add pagination controls using the `page` and `pages` fields from the response.

---

## Testing the Fixes

### Test 1: Receipt Timezone
```bash
# Create a bill and generate receipt
curl -X POST http://salon.local/api/pos/bills \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'

# Check receipt PDF - time should show IST (5.5 hours ahead of UTC)
# Example: If created at 14:30 UTC, receipt should show 20:00 IST
```

### Test 2: Customer Autocomplete
```bash
# Search all customers (not just current page)
curl "http://salon.local/api/customers/autocomplete?q=john&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Should return matching customers from entire database
```

### Test 3: Customer Pagination
```bash
# Page 1
curl "http://salon.local/api/customers?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"

# Page 2  
curl "http://salon.local/api/customers?page=2&size=20" \
  -H "Authorization: Bearer $TOKEN"

# Check "pages" field to know total pages available
```

---

## Verification Checklist

After restarting the application:

### Timezone Fixes
- [ ] Receipt shows IST time (not UTC)
- [ ] Bill timestamps in database are IST
- [ ] Payment timestamps are IST
- [ ] Expense timestamps are IST
- [ ] User last login shows IST

### Customer Search
- [ ] POS customer search finds all customers (not just current page)
- [ ] Autocomplete shows recent customers first
- [ ] Search works with partial names
- [ ] Search works with partial phone numbers
- [ ] Results limited to 10 for performance

### Customer List
- [ ] Frontend shows pagination controls (Next/Previous)
- [ ] Can navigate through all customer pages
- [ ] Page indicator shows current page number
- [ ] Search works across all pages

---

## Database Migration Note

**Existing Data**: Old timestamps in database are stored as UTC (timezone-naive). The receipt fix handles this by:

1. Checking if timestamp has timezone info
2. If naive (old data), assumes UTC and converts to IST
3. If aware (new data), converts to IST

This means:
- ✅ Old receipts will NOW show correct IST time
- ✅ New bills will be stored in IST
- ✅ No database migration needed
- ✅ Backward compatible

---

## Summary of Changes

| File | Changes | Impact |
|------|---------|--------|
| `app/services/billing_service.py` | Added IST import, replaced 6 `utcnow()` calls | All new bills/payments use IST |
| `app/api/expenses.py` | Replaced 3 `utcnow()` calls | All new expenses use IST |
| `app/api/purchases.py` | Replaced 2 `utcnow()` calls | All new purchases use IST |
| `app/auth/router.py` | Replaced 1 `utcnow()` call | Login timestamps use IST |
| `app/services/receipt_service.py` | Added timezone conversion on display | Receipts show IST time |
| `app/api/customers.py` | Added `/autocomplete` endpoint | POS can search all customers |

---

## Next Steps

1. **Deploy**: Restart the application to apply fixes
2. **Test**: Run verification checklist above
3. **Frontend**: Update POS to use `/autocomplete` endpoint
4. **Frontend**: Add pagination controls to customer list

---

**Fixed**: February 6, 2026  
**Status**: ✅ Backend Ready, Frontend Integration Needed  
**Breaking Changes**: None (backward compatible)
