# Pending Payment Tracking & Audit Trail

## ✅ Problem Solved

Your questions about bill tracking and payment mode recording are now fully addressed:

### **1. Bill Status & Resolution** ✅
- Original bills with pending balance remain in "posted" status (invoiced)
- Separate `pending_payment_collections` table tracks when/how pending was collected
- Complete audit trail of all payment collections
- Can see exactly when customer paid off pending balance

### **2. Payment Method Recording** ✅
- Every pending payment collection records:
  - ✅ Payment method (cash/card/UPI)
  - ✅ Reference number (transaction ID)
  - ✅ Collection timestamp
  - ✅ Who collected it
  - ✅ Previous & new balance (audit trail)
  - ✅ Notes
  - ✅ Linked bill (if via overpayment)

---

## 🗄️ Database Structure

### **New Table: `pending_payment_collections`**

Tracks every instance of pending balance collection:

```sql
CREATE TABLE pending_payment_collections (
  id VARCHAR(26) PRIMARY KEY,
  customer_id VARCHAR(26) NOT NULL REFERENCES customers(id),
  amount INTEGER NOT NULL,  -- Amount collected in paise
  payment_method ENUM('cash', 'card', 'upi', 'other') NOT NULL,
  reference_number VARCHAR,  -- Transaction reference
  notes TEXT,

  -- Link to bill if collected via overpayment
  bill_id VARCHAR(26) REFERENCES bills(id),

  -- Audit info
  collected_by VARCHAR(26) NOT NULL REFERENCES users(id),
  collected_at TIMESTAMP NOT NULL,

  -- Balance tracking
  previous_balance INTEGER NOT NULL,  -- Balance before collection
  new_balance INTEGER NOT NULL,       -- Balance after collection

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_pending_payment_collections_customer_id ON pending_payment_collections(customer_id);
CREATE INDEX idx_pending_payment_collections_collected_at ON pending_payment_collections(collected_at);
```

---

## 📊 How It Works

### **Scenario 1: Direct Payment Collection**

**Customer owes ₹500 from previous bill**

```
1. Customer comes to pay pending balance
2. Staff collects ₹500 cash
3. System creates record:
   {
     "amount": 50000,  // ₹500 in paise
     "payment_method": "cash",
     "previous_balance": 50000,
     "new_balance": 0,
     "bill_id": null,  // Not linked to any bill
     "collected_by": "staff_id",
     "collected_at": "2026-02-06T14:30:00"
   }
4. Customer's pending_balance becomes 0
```

**Result:**
- ✅ Complete audit trail
- ✅ Payment method recorded (cash)
- ✅ Timestamp when collected
- ✅ Who collected it
- ✅ Balance before/after

---

### **Scenario 2: Overpayment on New Bill**

**Customer has ₹500 pending, new bill is ₹300, pays ₹800**

```
1. Create new bill for ₹300
2. Customer pays ₹800 total
3. System splits payment:
   - ₹300 → Applied to current bill
   - ₹500 → Applied to pending balance
4. System creates TWO records:

   A. Payment record (for current bill):
   {
     "bill_id": "new_bill_id",
     "amount": 80000,  // ₹800
     "payment_method": "upi",
     "notes": "Applied Rs 500.00 to pending balance"
   }

   B. PendingPaymentCollection record:
   {
     "amount": 50000,  // ₹500
     "payment_method": "upi",
     "previous_balance": 50000,
     "new_balance": 0,
     "bill_id": "new_bill_id",  // ✅ Linked to bill
     "notes": "Overpayment on bill SAL-26-0042"
   }
```

**Result:**
- ✅ Current bill fully paid
- ✅ Pending balance cleared
- ✅ Audit trail shows overpayment reduced pending
- ✅ Can trace which bill the overpayment came from

---

## 🎯 API Endpoints

### **1. Collect Pending Payment**
```http
POST /api/pos/pending-payments/collect
Content-Type: application/json

{
  "customer_id": "01HXXX...",
  "amount": 500.00,
  "payment_method": "cash",
  "reference_number": "TXN123456",
  "notes": "Collected pending balance"
}
```

**Response:**
```json
{
  "id": "01COLLECT...",
  "customer_id": "01HXXX...",
  "amount": 50000,
  "payment_method": "cash",
  "reference_number": "TXN123456",
  "notes": "Collected pending balance",
  "bill_id": null,
  "collected_by": "01USER...",
  "collected_at": "2026-02-06T14:30:00Z",
  "previous_balance": 50000,
  "new_balance": 0
}
```

### **2. Get Payment Collection History**
```http
GET /api/pos/pending-payments/customer/{customer_id}
```

**Response:**
```json
[
  {
    "id": "01COLLECT...",
    "amount": 50000,
    "payment_method": "cash",
    "collected_at": "2026-02-06T14:30:00Z",
    "previous_balance": 50000,
    "new_balance": 0,
    "bill_id": null,
    "notes": "Direct collection"
  },
  {
    "id": "01COLLECT2...",
    "amount": 30000,
    "payment_method": "upi",
    "collected_at": "2026-02-05T10:15:00Z",
    "previous_balance": 80000,
    "new_balance": 50000,
    "bill_id": "01BILL...",
    "notes": "Overpayment on bill SAL-26-0041"
  }
]
```

---

## 🎨 Frontend Features

### **1. Pending Column in Customers Table**
- Shows current pending balance
- ✅ NEW: **History icon button** next to amount
- Click to view complete payment collection history

### **2. Payment Collection History Dialog**
Shows complete timeline:
```
┌─────────────────────────────────────┐
│ Pending Payment Collection History  │
├─────────────────────────────────────┤
│ ₹500.00  [CASH]                     │
│ Feb 6, 2026 2:30 PM                 │
│ Balance: ₹500 → ₹0                  │
│ Direct collection                    │
├─────────────────────────────────────┤
│ ₹300.00  [UPI]                      │
│ Feb 5, 2026 10:15 AM                │
│ Balance: ₹800 → ₹500                │
│ Via overpayment on bill             │
│ Ref: UPI123456                      │
└─────────────────────────────────────┘
```

### **3. Collection Record Details**
Each entry shows:
- ✅ Amount collected (green)
- ✅ Payment method badge (colored by type)
- ✅ Date & time
- ✅ Balance change (before → after)
- ✅ Source (direct or via bill)
- ✅ Reference number
- ✅ Notes

---

## 📝 Audit Trail Example

**Customer "John Doe" - Complete History:**

```
Jan 15, 2026:
  Bill SAL-26-0010 for ₹1000
  Paid: ₹500 (cash)
  Status: POSTED with ₹500 pending
  → pending_balance = ₹500

Jan 20, 2026:
  Direct Collection Record:
  - Amount: ₹200 (UPI)
  - Previous: ₹500 → New: ₹300
  - Ref: UPI789012
  → pending_balance = ₹300

Jan 25, 2026:
  Bill SAL-26-0015 for ₹400
  Paid: ₹700 (cash)
  Overpayment Collection Record:
  - Amount: ₹300 (cash)
  - Previous: ₹300 → New: ₹0
  - Bill: SAL-26-0015
  → pending_balance = ₹0

Result:
✅ Bill SAL-26-0010 stays as "posted" (invoiced)
✅ Two collection records track when pending was paid
✅ Complete audit trail with payment methods
✅ Can generate reports on pending collections
```

---

## 🔍 Reporting Capabilities

With the new tracking system, you can now:

1. **Customer Payment History**
   - When did customer pay pending balance?
   - What payment method was used?
   - Who collected the payment?

2. **Staff Performance**
   - Which staff collected most pending payments?
   - Total collections per staff member

3. **Payment Method Analysis**
   - How many pending payments via cash vs UPI?
   - Reference numbers for digital payments

4. **Outstanding Balance Tracking**
   - Which customers still owe money?
   - How long has balance been pending?
   - Collection success rate

5. **Bill Resolution**
   - Which bills had pending balances?
   - When were they fully resolved?
   - Link between bill and subsequent collections

---

## 🚀 Migration Steps

Run **TWO** migrations:

```bash
# 1. Add pending_balance column to customers
docker compose exec api alembic upgrade c4d5e6f7g8h9

# 2. Create pending_payment_collections table
docker compose exec api alembic upgrade d5e6f7g8h9i0

# Verify
docker compose exec api alembic current
# Should show: d5e6f7g8h9i0
```

---

## 💡 Key Benefits

### **Before (Without Tracking):**
❌ No record of when/how pending was collected
❌ Payment method not recorded for pending collections
❌ Can't audit pending payment collections
❌ No link between bills and pending payments
❌ Customer notes cluttered with payment info

### **After (With Tracking):**
✅ Complete audit trail for every collection
✅ Payment method, reference, timestamp recorded
✅ Link to bill if via overpayment
✅ Query payment history per customer
✅ Generate reports on collections
✅ Clean separation of data

---

## 🧪 Testing Scenarios

### **Test 1: Direct Collection**
```bash
1. Customer has ₹500 pending
2. POST /api/pos/pending-payments/collect
   {
     "customer_id": "...",
     "amount": 500,
     "payment_method": "cash"
   }
3. Check:
   ✅ Customer pending_balance = 0
   ✅ Collection record created
   ✅ Payment method recorded
4. GET /api/pos/pending-payments/customer/{id}
   ✅ Shows collection history
```

### **Test 2: Overpayment**
```bash
1. Customer has ₹500 pending
2. Create bill for ₹300
3. Pay ₹800 (overpay by ₹500)
4. Check:
   ✅ Bill fully paid
   ✅ Pending balance = 0
   ✅ PendingPaymentCollection created
   ✅ bill_id links to current bill
   ✅ Payment method recorded
```

### **Test 3: View History**
```bash
1. Go to Customers page
2. Click history icon (⏱️) next to pending balance
3. Dialog shows:
   ✅ All past collections
   ✅ Payment methods
   ✅ Balance changes
   ✅ Timestamps
   ✅ Sources (direct vs overpayment)
```

---

## 📊 Example Reports

### **Daily Collections Report**
```sql
SELECT
  DATE(collected_at) as date,
  payment_method,
  COUNT(*) as count,
  SUM(amount) as total_collected
FROM pending_payment_collections
WHERE collected_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(collected_at), payment_method
ORDER BY date DESC;
```

### **Customer Outstanding Report**
```sql
SELECT
  c.first_name,
  c.last_name,
  c.pending_balance,
  MAX(ppc.collected_at) as last_payment,
  COUNT(ppc.id) as payment_count
FROM customers c
LEFT JOIN pending_payment_collections ppc ON c.id = ppc.customer_id
WHERE c.pending_balance > 0
GROUP BY c.id
ORDER BY c.pending_balance DESC;
```

---

## 🎯 Summary

Your questions are now **fully answered**:

### **Q1: How does this reflect in bills?**
**A:** Bills remain in "posted" status with their invoice numbers. The `pending_payment_collections` table tracks when/how the pending balance was eventually collected. You can query this table to see which bills had pending balances and when they were resolved.

### **Q2: Will old bills with pending payment get resolved?**
**A:** Old bills stay as "posted" (they were invoiced). The resolution of pending balance is tracked separately in `pending_payment_collections`. This is correct because:
- The bill was completed and invoiced
- The pending balance is a customer-level debt
- Multiple bills can contribute to pending balance
- Collections can be partial or full

### **Q3: Should we record payment mode?**
**A:** ✅ **YES - Now fully implemented!** Every collection records:
- Payment method (cash/card/UPI)
- Reference number
- Timestamp
- Collector
- Previous & new balance
- Notes
- Linked bill (if via overpayment)

---

**Version:** 2.0
**Date:** 2026-02-06
**Status:** ✅ Complete Audit Trail Implemented
