# Pending Balance & Free Service Feature Guide

## Overview

This feature allows you to:
1. ✅ Create bills without full payment (pending balance)
2. ✅ Record completely free services (₹0 payment)
3. ✅ Track customer pending balances
4. ✅ Collect pending payments (with or without new bills)
5. ✅ Apply overpayments to reduce pending balance

---

## 🎯 Use Cases

### 1. **Free Services (Family/VIP)**
   - Provide complimentary service to family members
   - VIP customer perks
   - Compensation for service issues

### 2. **Credit/Pay Later**
   - Regular customers who pay monthly
   - Corporate accounts
   - Trust-based credit system

### 3. **Partial Payments**
   - Customer doesn't have full amount
   - Split payment across visits
   - Emergency situations

---

## 📱 Frontend Features

### **1. Customer Search (POS)**
- Shows pending balance in RED below customer info
- Example:
  ```
  John Doe
  +91 98765 43210 • 5 visits
  Pending: ₹500.00  ← Shows if customer owes money
  ```

### **2. Payment Modal (POS Checkout)**

#### **A. Pending Balance Alert**
- Yellow alert box showing customer's pending balance
- "Collect Now" button to collect pending separately

#### **B. Complete Bill Buttons**
Two new buttons appear based on context:

**Button 1: "Complete Bill (No Payment)"**
- When: No payments made yet
- Use: For free services or when customer will pay later
- Creates invoice without any payment

**Button 2: "Complete Bill (Pending: ₹XXX)"**
- When: Partial payment already made
- Shows remaining unpaid amount
- Completes bill with pending balance

#### **C. Collect Pending Balance (Inline)**
- Expandable section in payment modal
- Collect pending payment from previous bills
- Without creating new bill
- Updates customer balance immediately

#### **D. Notes Field**
- Add context for pending balance
- Example: "Family member - will pay next month"

### **3. Customers Page**

#### **Stats Cards (Dashboard)**
- New 5th card: **"Pending Balance"** in red
- Shows total pending across all customers

#### **Customer Table**
- New column: **"Pending"** (between Total Spent and Last Visit)
- Shows amount in RED if customer owes money
- Shows "-" if no pending balance

#### **Collect Payment Button**
- Green "Collect" button next to each customer with pending balance
- Opens dedicated payment collection dialog
- Records payment without creating bill

---

## 🔧 Backend Implementation

### **1. Database Changes**
- Added `pending_balance` column to `customers` table
- Migration: `c4d5e6f7g8h9_add_pending_balance_to_customers.py`

### **2. New API Endpoints**

#### **Complete Bill with Pending Balance**
```http
POST /api/pos/bills/{bill_id}/complete
Content-Type: application/json

{
  "notes": "Family member - balance to be collected later"
}
```

**Response:**
```json
{
  "id": "01HXXX...",
  "invoice_number": "SAL-26-0042",
  "status": "posted",
  "pending_balance": 50000,  // ₹500.00
  ...
}
```

#### **Collect Pending Payment**
```http
POST /api/pos/pending-payments/collect
Content-Type: application/json

{
  "customer_id": "01HXXX...",
  "amount": 500.00,
  "payment_method": "cash",
  "reference_number": "optional",
  "notes": "Collected pending balance"
}
```

**Response:**
```json
{
  "customer_id": "01HXXX...",
  "amount_collected": 50000,
  "previous_balance": 50000,
  "remaining_balance": 0,
  "payment_method": "cash",
  "collected_by": "user_id",
  "collected_at": "2026-02-06T..."
}
```

### **3. Overpayment Logic**
- When customer pays more than bill amount
- Overpayment automatically applied to pending balance
- Example:
  - Bill: ₹300
  - Pending Balance: ₹500
  - Customer pays: ₹800
  - Result: ₹300 → bill, ₹500 → pending, New pending: ₹0

---

## 🧪 Testing Scenarios

### **Scenario 1: Free Service**
1. Add service to cart (₹500)
2. Click "Checkout"
3. Click **"Complete Bill (No Payment)"**
4. Print receipt → Shows "COMPLIMENTARY SERVICE"
5. Check customer page → Pending balance = ₹0

### **Scenario 2: Partial Payment with Pending Balance**
1. Create bill for ₹1000
2. Customer pays ₹400 (partial)
3. Click **"Complete Bill (Pending: ₹600)"**
4. Print receipt → Shows "PENDING BALANCE: ₹600.00" in red
5. Check customer page → Shows ₹600 pending in red

### **Scenario 3: Collect Pending Payment (From Customers Page)**
1. Go to Customers page
2. Find customer with pending balance
3. Click green **"Collect"** button
4. Enter amount (₹600)
5. Select payment method
6. Click "Collect ₹600"
7. Customer's pending balance updated

### **Scenario 4: Collect Pending from POS**
1. Select customer with pending balance in POS
2. See alert: "Customer has pending balance: ₹600"
3. Click **"Collect Now"**
4. Enter amount and payment method
5. Click "Collect from Pending"
6. Balance updated, no new bill created

### **Scenario 5: Overpayment on New Bill**
1. Customer has ₹500 pending
2. New bill is ₹300
3. Customer pays ₹800
4. System applies:
   - ₹300 → current bill
   - ₹500 → pending balance
5. Pending becomes ₹0

---

## 🎨 UI Elements Summary

### **Colors & Indicators**
- 🔴 **Red Text**: Pending balance (alerts, amounts)
- 🟢 **Green Button**: "Collect" payment button
- 🟡 **Yellow Box**: Pending balance alert/section
- ⚪ **Gray Dash**: No pending balance (-)

### **Buttons Added**
1. "Complete Bill (No Payment)" - Secondary button
2. "Complete Bill (Pending: ₹XXX)" - Outline button
3. "Collect Now" - Small outline button in alert
4. "Collect" - Green outline button (customers table)
5. "Collect ₹XXX from Pending" - Button in expandable section

---

## 📊 Receipt Updates

### **Free Service Receipt**
```
TAX INVOICE
#SAL-26-0042

[Items...]
TOTAL: ₹0.00

================================
COMPLIMENTARY SERVICE
================================
```

### **Pending Balance Receipt**
```
TAX INVOICE
#SAL-26-0042

[Items...]
TOTAL: ₹1000.00

Payment Method    Amount
CASH              ₹400.00

================================
PENDING BALANCE: ₹600.00
================================
```

### **Full Pending Receipt (No Payment)**
```
TAX INVOICE
#SAL-26-0042

[Items...]
TOTAL: ₹500.00

================================
FULL AMOUNT PENDING: ₹500.00
================================
```

---

## 🔐 Permissions

### **Receptionist Can:**
- ✅ Complete bills with pending balance
- ✅ Collect pending payments
- ✅ View customer pending balances

### **Owner Can:**
- ✅ Everything receptionist can do
- ✅ Delete customers (with pending balances)

---

## 🚀 Migration Steps

1. **Run Database Migration:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

2. **Restart Services:**
   ```bash
   docker compose restart
   ```

3. **Verify Migration:**
   - Check customers table has `pending_balance` column
   - All existing customers should have `pending_balance = 0`

---

## 💡 Tips & Best Practices

1. **Always add notes** when creating pending balance
2. **Print receipt** immediately (shows pending balance)
3. **Follow up** regularly on customers with pending balance
4. **Use overpayment** when customer pays for new service + old balance
5. **Track collections** via customer notes (auto-recorded)

---

## 🐛 Troubleshooting

### **Can't collect pending payment**
- ✅ Check customer has pending balance > 0
- ✅ Verify receptionist permissions
- ✅ Check amount doesn't exceed pending balance

### **Overpayment rejected**
- ✅ Ensure customer has pending balance
- ✅ Verify overpayment <= pending balance
- ✅ Check customer_id is set on bill

### **Pending balance not showing**
- ✅ Run migration
- ✅ Refresh browser cache
- ✅ Check API response includes pending_balance field

---

## 📝 API Reference

### **Endpoints**
- `POST /api/pos/bills/{bill_id}/complete` - Complete with pending
- `POST /api/pos/pending-payments/collect` - Collect pending
- `GET /api/customers/{id}` - Returns pending_balance
- `GET /api/customers` - List includes pending_balance

### **Schema Changes**
- `Customer.pending_balance` - Integer (paise)
- `Customer.pending_balance_rupees` - Float property
- `BillResponse.total_paid` - Integer (paise) property
- `BillResponse.pending_balance` - Integer (paise) property

---

**Version:** 1.0
**Date:** 2026-02-06
**Status:** ✅ Production Ready
