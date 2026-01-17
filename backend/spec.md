# Spec 4: POS & Billing Module

## Purpose
Implement the complete Point of Sale (POS) system for creating bills, applying discounts, recording payments, generating receipts, and handling refunds.

## Scope
- Cart-based billing flow
- Bill-level discounts with audit logging
- Manual payment confirmation (cash/UPI/card/other)
- Invoice number generation (SAL-YY-NNNN)
- GST calculation (CGST/SGST split)
- 80mm receipt printing via browser
- Receipt send via email/WhatsApp (Phase 1: print only)
- Refund processing
- Idempotency for bill creation

## Business Rules

### Pricing & Tax
- All catalog prices are **tax-inclusive**
- GST Rate: 18% (9% CGST + 9% SGST)
- Tax calculation: `tax = (price * 18) / 118`
- Rounding: Round final total to nearest ₹1

### Discounts
- **Bill-level only** (no line-item discounts in Phase 1)
- Discount applied after subtotal, before tax calculation
- Must log: user_id, device_id, timestamp, amount, optional reason
- Receptionist can apply up to ₹500 without approval
- Owner can apply any amount

### Invoice Numbering
- Format: `SAL-YY-NNNN`
- Example: `SAL-25-0001`, `SAL-25-0002`
- Resets annually on fiscal year (April 1st)
- Sequential, no gaps allowed
- Generated server-side, atomic

### Payment Flow
1. Create bill (status: draft)
2. Add payments (manual confirmation)
3. When payments sum >= total: mark bill as posted
4. Generate invoice number on posting
5. Print/send receipt

### Refunds
- Can only refund posted bills
- Creates negative bill linking to original
- Refund appears in "Adjustments" section of reports
- Does not modify original bill's posted amounts
- Full refund only in Phase 1

## Data Flow

```
Cart (Frontend State)
    ↓
POST /api/pos/bills (Create Bill - draft)
    ↓
Bill Record Created (status: draft)
    ↓
POST /api/pos/bills/:id/payments (Record Payment)
    ↓
Payments Sum >= Total? → Update status to 'posted'
    ↓
Generate Invoice Number (atomic)
    ↓
Emit Event: bill.posted
    ↓
GET /api/pos/bills/:id/receipt → Render 80mm receipt → Print
```

## API Endpoints

### POST /api/pos/bills
**Purpose**: Create a new bill (draft status)

**Auth**: Receptionist or Owner

**Request Body**:
```json
{
  "items": [
    {
      "service_id": "01HXXX...",
      "staff_id": "01HYYY...",  // optional
      "appointment_id": "01HZZZ...",  // optional, links to appointment
      "walkin_id": "01HAAA...",  // optional, links to walkin
      "quantity": 1,
      "notes": "Extra conditioning treatment"  // optional
    }
  ],
  "customer_id": "01HBBB...",  // optional
  "customer_name": "John Doe",  // required if no customer_id
  "customer_phone": "9876543210",  // required if no customer_id
  "discount_amount": 50,  // optional, in rupees
  "discount_reason": "Regular customer discount"  // optional
}
```

**Headers**:
```
Authorization: Bearer {token}
Idempotency-Key: {unique_key}  // Prevents duplicate bills
```

**Response (201)**:
```json
{
  "id": "01HXXX...",
  "status": "draft",
  "subtotal": 1500,  // paise
  "discount_amount": 5000,  // paise (₹50)
  "tax_amount": 22966,  // paise (calculated)
  "cgst_amount": 11483,
  "sgst_amount": 11483,
  "total_amount": 147034,  // paise
  "rounded_total": 147000,  // paise (₹1470)
  "rounding_adjustment": -34,
  "items": [
    {
      "id": "01HYYY...",
      "service_name": "Haircut + Styling",
      "base_price": 75000,  // paise
      "quantity": 1,
      "line_total": 75000,
      "staff_name": "Sarah"
    },
    {
      "id": "01HZZZ...",
      "service_name": "Hair Color",
      "base_price": 80000,
      "quantity": 1,
      "line_total": 80000,
      "staff_name": "Mike"
    }
  ],
  "created_at": "2025-10-15T10:30:00+05:30",
  "created_by": "receptionist1"
}
```

**Validation**:
- At least one item required
- All service_ids must exist
- Discount cannot exceed subtotal
- If discount > ₹500 and user is receptionist, return 403
- Customer name and phone required if no customer_id

**Idempotency**:
- If same Idempotency-Key sent twice, return existing bill (200)
- Keys expire after 24 hours

### POST /api/pos/bills/:id/payments
**Purpose**: Record payment for a bill

**Auth**: Receptionist or Owner

**Request Body**:
```json
{
  "method": "cash",  // enum: cash, upi, card, other
  "amount": 1470.00,  // rupees (will convert to paise)
  "reference_number": "UPI123456",  // optional
  "notes": "Paid via PhonePe"  // optional
}
```

**Response (200)**:
```json
{
  "payment_id": "01HXXX...",
  "bill_id": "01HYYY...",
  "method": "cash",
  "amount": 147000,  // paise
  "confirmed_at": "2025-10-15T10:32:00+05:30",
  "confirmed_by": "receptionist1",
  "bill_status": "posted",  // Updated if payments sum >= total
  "invoice_number": "SAL-25-0042"  // Generated on posting
}
```

**Behavior**:
- Can record multiple payments (split payments)
- When sum of payments >= bill total:
  - Update bill status to 'posted'
  - Generate invoice number atomically
  - Emit `bill.posted` event
  - Update customer.total_spent if customer_id exists

**Validation**:
- Bill must be in 'draft' status
- Payment amount > 0
- Cannot overpay (sum of payments must not exceed total + ₹10 tolerance)

### GET /api/pos/bills/:id
**Purpose**: Get bill details

**Auth**: Receptionist or Owner

**Response (200)**:
```json
{
  "id": "01HXXX...",
  "invoice_number": "SAL-25-0042",
  "status": "posted",
  "customer": {
    "id": "01HBBB...",
    "name": "John Doe",
    "phone": "9876543210"
  },
  "subtotal": 155000,
  "discount_amount": 5000,
  "tax_amount": 22966,
  "cgst_amount": 11483,
  "sgst_amount": 11483,
  "total_amount": 147034,
  "rounded_total": 147000,
  "rounding_adjustment": -34,
  "items": [ /* bill items */ ],
  "payments": [
    {
      "id": "01HYYY...",
      "method": "cash",
      "amount": 100000,
      "confirmed_at": "2025-10-15T10:32:00+05:30"
    },
    {
      "id": "01HZZZ...",
      "method": "upi",
      "amount": 47000,
      "confirmed_at": "2025-10-15T10:32:30+05:30"
    }
  ],
  "posted_at": "2025-10-15T10:32:30+05:30",
  "created_at": "2025-10-15T10:30:00+05:30",
  "created_by": {
    "id": "01HAAA...",
    "username": "receptionist1",
    "full_name": "Jane Smith"
  }
}
```

### GET /api/pos/bills/:id/receipt
**Purpose**: Get receipt HTML for printing

**Auth**: Receptionist or Owner

**Query Params**:
- `format=html` (default) or `format=json`

**Response (200) - HTML**:
Returns 80mm-width HTML receipt ready for printing via `window.print()`

**Response (200) - JSON**:
```json
{
  "salon_name": "Unisex Beauty Salon",
  "address": "123 Main St, City, State",
  "gstin": "29XXXXX1234X1ZX",
  "invoice_number": "SAL-25-0042",
  "date": "15 Oct 2025",
  "time": "10:32 AM",
  "customer_name": "John Doe",
  "items": [
    {
      "name": "Haircut + Styling",
      "staff": "Sarah",
      "amount": "₹750.00"
    }
  ],
  "subtotal": "₹1,550.00",
  "discount": "₹50.00",
  "cgst": "₹114.83",
  "sgst": "₹114.83",
  "total": "₹1,470.00",
  "payment_method": "Cash, UPI",
  "footer_message": "Thank you for visiting!"
}
```

### POST /api/pos/bills/:id/refund
**Purpose**: Create refund for a posted bill

**Auth**: Owner only

**Request Body**:
```json
{
  "reason": "Customer dissatisfaction",  // required
  "notes": "Issue with hair color result"  // optional
}
```

**Response (200)**:
```json
{
  "refund_bill_id": "01HXXX...",
  "original_bill_id": "01HYYY...",
  "original_invoice_number": "SAL-25-0042",
  "refund_invoice_number": "SAL-25-0043",
  "refund_amount": 147000,  // paise
  "status": "refunded",
  "refunded_at": "2025-10-15T15:30:00+05:30"
}
```

**Behavior**:
- Creates new bill with negative amounts
- Links to original bill via `original_bill_id`
- Original bill status → 'refunded'
- Emits `bill.refunded` event
- Updates customer.total_spent (subtract refund amount)

**Validation**:
- Bill must be 'posted' status
- Cannot refund already refunded bills
- Only owner can refund

### GET /api/pos/bills
**Purpose**: List bills with filters

**Auth**: Receptionist or Owner

**Query Params**:
- `status` - filter by status (draft, posted, refunded)
- `from` - start date (ISO format)
- `to` - end date (ISO format)
- `customer_id` - filter by customer
- `invoice_number` - search by invoice number
- `page` - page number (default: 1)
- `limit` - items per page (default: 50, max: 100)

**Response (200)**:
```json
{
  "bills": [ /* array of bill summaries */ ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 243,
    "pages": 5
  }
}
```

## Implementation Details

### Invoice Number Generation (Atomic)

```python
# backend/app/services/billing.py
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime

class InvoiceNumberGenerator:
    """Generate sequential invoice numbers safely."""
    
    @staticmethod
    def generate(db: Session) -> str:
        """
        Generate next invoice number atomically.
        Format: SAL-YY-NNNN
        """
        current_year = datetime.now().strftime("%y")
        
        # Use advisory lock to prevent race conditions
        db.execute(text("SELECT pg_advisory_lock(12345)"))
        
        try:
            # Get current max number for this year
            result = db.execute(
                text("""
                    SELECT COALESCE(MAX(
                        CAST(SPLIT_PART(invoice_number, '-', 3) AS INTEGER)
                    ), 0) as max_num
                    FROM bills
                    WHERE invoice_number LIKE :pattern
                """),
                {"pattern": f"SAL-{current_year}-%"}
            ).first()
            
            next_num = (result.max_num or 0) + 1
            invoice_number = f"SAL-{current_year}-{next_num:04d}"
            
            return invoice_number
            
        finally:
            db.execute(text("SELECT pg_advisory_unlock(12345)"))
```

### GST Calculation

```python
# backend/app/services/billing.py
from decimal import Decimal, ROUND_HALF_UP

class TaxCalculator:
    """Calculate GST breakdown from tax-inclusive prices."""
    
    GST_RATE = Decimal("0.18")  # 18%
    CGST_RATE = Decimal("0.09")  # 9%
    SGST_RATE = Decimal("0.09")  # 9%
    
    @classmethod
    def calculate_tax_breakdown(cls, inclusive_price: int) -> dict:
        """
        Calculate tax breakdown from inclusive price.
        
        Args:
            inclusive_price: Price in paise (tax-inclusive)
        
        Returns:
            dict with taxable_value, cgst, sgst, total_tax
        """
        # Convert to Decimal for precision
        price = Decimal(inclusive_price)
        
        # Calculate taxable value: price / (1 + tax_rate)
        taxable_value = price / (Decimal("1") + cls.GST_RATE)
        
        # Calculate CGST and SGST
        cgst = taxable_value * cls.CGST_RATE
        sgst = taxable_value * cls.SGST_RATE
        total_tax = cgst + sgst
        
        # Round to nearest paise
        return {
            "taxable_value": int(taxable_value.quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )),
            "cgst": int(cgst.quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )),
            "sgst": int(sgst.quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )),
            "total_tax": int(total_tax.quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            ))
        }
    
    @classmethod
    def round_to_rupee(cls, amount_paise: int) -> tuple[int, int]:
        """
        Round amount to nearest rupee.
        
        Returns:
            (rounded_amount_paise, adjustment_paise)
        """
        rupees = Decimal(amount_paise) / Decimal("100")
        rounded_rupees = rupees.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        rounded_paise = int(rounded_rupees * 100)
        adjustment = rounded_paise - amount_paise
        
        return rounded_paise, adjustment
```

### Bill Creation Service

```python
# backend/app/services/billing.py
from sqlalchemy.orm import Session
from app.models import Bill, BillItem, Service, Customer
from app.schemas import BillCreate
from ulid import ULID

class BillingService:
    """Handle bill creation and management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_bill(
        self,
        data: BillCreate,
        created_by_id: str
    ) -> Bill:
        """Create a new bill (draft status)."""
        
        # Validate items and calculate subtotal
        subtotal = 0
        bill_items = []
        
        for item_data in data.items:
            service = self.db.query(Service).filter(
                Service.id == item_data.service_id
            ).first()
            
            if not service:
                raise ValueError(f"Service not found: {item_data.service_id}")
            
            line_total = service.base_price * item_data.quantity
            subtotal += line_total
            
            bill_items.append({
                "service_id": service.id,
                "item_name": service.name,
                "base_price": service.base_price,
                "quantity": item_data.quantity,
                "line_total": line_total,
                "staff_id": item_data.staff_id,
                "appointment_id": item_data.appointment_id,
                "walkin_id": item_data.walkin_id,
                "notes": item_data.notes
            })
        
        # Apply discount
        discount_amount = (data.discount_amount or 0) * 100  # Convert to paise
        
        if discount_amount > subtotal:
            raise ValueError("Discount cannot exceed subtotal")
        
        amount_after_discount = subtotal - discount_amount
        
        # Calculate tax
        tax_breakdown = TaxCalculator.calculate_tax_breakdown(
            amount_after_discount
        )
        
        # Calculate total and rounding
        total_amount = amount_after_discount + tax_breakdown["total_tax"]
        rounded_total, rounding_adjustment = TaxCalculator.round_to_rupee(
            total_amount
        )
        
        # Create bill
        bill = Bill(
            id=str(ULID()),
            customer_id=data.customer_id,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            subtotal=subtotal,
            discount_amount=discount_amount,
            discount_reason=data.discount_reason,
            tax_amount=tax_breakdown["total_tax"],
            cgst_amount=tax_breakdown["cgst"],
            sgst_amount=tax_breakdown["sgst"],
            total_amount=total_amount,
            rounded_total=rounded_total,
            rounding_adjustment=rounding_adjustment,
            status="draft",
            created_by=created_by_id
        )
        
        self.db.add(bill)
        self.db.flush()
        
        # Create bill items
        for item_data in bill_items:
            bill_item = BillItem(
                id=str(ULID()),
                bill_id=bill.id,
                **item_data
            )
            self.db.add(bill_item)
        
        self.db.commit()
        self.db.refresh(bill)
        
        return bill
    
    def add_payment(
        self,
        bill_id: str,
        payment_data: PaymentCreate,
        confirmed_by_id: str
    ) -> Payment:
        """Add payment to bill and post if fully paid."""
        
        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        
        if not bill:
            raise ValueError("Bill not found")
        
        if bill.status != "draft":
            raise ValueError("Can only add payments to draft bills")
        
        # Calculate current payment total
        existing_payments = self.db.query(Payment).filter(
            Payment.bill_id == bill_id
        ).all()
        
        current_total = sum(p.amount for p in existing_payments)
        new_total = current_total + (payment_data.amount * 100)  # Convert to paise
        
        if new_total > bill.rounded_total + 1000:  # ₹10 tolerance
            raise ValueError("Payment exceeds bill total")
        
        # Create payment
        payment = Payment(
            id=str(ULID()),
            bill_id=bill_id,
            payment_method=payment_data.method,
            amount=payment_data.amount * 100,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes,
            confirmed_by=confirmed_by_id
        )
        
        self.db.add(payment)
        
        # Check if bill is fully paid
        if new_total >= bill.rounded_total:
            # Generate invoice number
            invoice_number = InvoiceNumberGenerator.generate(self.db)
            
            bill.invoice_number = invoice_number
            bill.status = "posted"
            bill.posted_at = datetime.utcnow()
            
            # Update customer stats if applicable
            if bill.customer_id:
                customer = self.db.query(Customer).filter(
                    Customer.id == bill.customer_id
                ).first()
                
                if customer:
                    customer.total_visits += 1
                    customer.total_spent += bill.rounded_total
                    customer.last_visit_at = datetime.utcnow()
            
            # Emit event for accounting updates
            from app.events import emit_event
            emit_event(self.db, "bill.posted", {
                "bill_id": bill.id,
                "invoice_number": invoice_number,
                "total": bill.rounded_total,
                "customer_id": bill.customer_id
            })
        
        self.db.commit()
        self.db.refresh(payment)
        
        return payment
```

## 80mm Receipt Template

### HTML Template (80mm width = 302px)

```html
<!-- templates/receipt.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Receipt - {{ invoice_number }}</title>
    <style>
        @page {
            size: 80mm auto;
            margin: 0;
        }
        body {
            width: 80mm;
            margin: 0 auto;
            padding: 10mm 5mm;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.4;
        }
        .center { text-align: center; }
        .bold { font-weight: bold; }
        .line {
            border-top: 1px dashed #000;
            margin: 5px 0;
        }
        .row {
            display: flex;
            justify-content: space-between;
            margin: 2px 0;
        }
        .item {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
        }
        .staff { font-size: 10px; color: #666; }
    </style>
</head>
<body>
    <div class="center bold" style="font-size: 16px;">
        UNISEX BEAUTY SALON
    </div>
    <div class="center" style="font-size: 10px;">
        123 Main Street, City, State<br>
        Phone: 9876543210<br>
        GSTIN: 29XXXXX1234X1ZX
    </div>
    
    <div class="line"></div>
    
    <div class="row">
        <span>Invoice: <span class="bold">{{ invoice_number }}</span></span>
        <span>{{ date }}</span>
    </div>
    <div class="row">
        <span>Time: {{ time }}</span>
    </div>
    <div class="row">
        <span>Customer: {{ customer_name }}</span>
    </div>
    
    <div class="line"></div>
    
    {% for item in items %}
    <div class="item">
        <div style="flex: 1;">
            {{ item.name }}<br>
            <span class="staff">by {{ item.staff }}</span>
        </div>
        <div style="text-align: right;">
            {{ item.amount }}
        </div>
    </div>
    {% endfor %}
    
    <div class="line"></div>
    
    <div class="row">
        <span>Subtotal:</span>
        <span>{{ subtotal }}</span>
    </div>
    
    {% if discount > 0 %}
    <div class="row">
        <span>Discount:</span>
        <span>-{{ discount }}</span>
    </div>
    {% endif %}
    
    <div class="row" style="font-size: 10px;">
        <span>CGST (9%):</span>
        <span>{{ cgst }}</span>
    </div>
    <div class="row" style="font-size: 10px;">
        <span>SGST (9%):</span>
        <span>{{ sgst }}</span>
    </div>
    
    <div class="line"></div>
    
    <div class="row bold" style="font-size: 14px;">
        <span>TOTAL:</span>
        <span>{{ total }}</span>
    </div>
    
    <div class="row" style="font-size: 10px;">
        <span>Paid: {{ payment_method }}</span>
    </div>
    
    <div class="line"></div>
    
    <div class="center" style="font-size: 10px; margin-top: 10px;">
        {{ footer_message }}<br>
        Visit Again!
    </div>
</body>
</html>
```

### Print Function (Frontend)

```typescript
// frontend/src/lib/printing.ts
export async function printReceipt(billId: string) {
  // Open receipt in new window
  const receiptWindow = window.open(
    `/api/pos/bills/${billId}/receipt?format=html`,
    '_blank',
    'width=302,height=600,menubar=no,toolbar=no'
  );
  
  if (!receiptWindow) {
    throw new Error('Could not open print window');
  }
  
  // Wait for content to load, then print
  receiptWindow.onload = () => {
    setTimeout(() => {
      receiptWindow.print();
      receiptWindow.close();
    }, 500);
  };
}
```

## Acceptance Criteria

- [ ] Can create bill with multiple services
- [ ] Bill-level discount applies correctly
- [ ] GST calculates CGST/SGST split accurately
- [ ] Rounding to nearest ₹1 works
- [ ] Invoice number generates sequentially
- [ ] Cannot create duplicate bills with same Idempotency-Key
- [ ] Can record split payments (cash + digital)
- [ ] Bill posts automatically when fully paid
- [ ] 80mm receipt prints correctly via browser
- [ ] Refund creates negative bill linking to original
- [ ] Only owner can refund bills
- [ ] Discount audit log captures all required fields
- [ ] Customer stats update on bill posting
- [ ] bill.posted event emitted after posting
- [ ] Cannot overpay beyond tolerance
- [ ] Receipt shows all items with staff names
- [ ] Tax breakdown shows on receipt
- [ ] List bills with pagination works

## Testing Checklist

```bash
# 1. Create bill
curl -X POST http://localhost/api/pos/bills \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{
    "items": [{"service_id": "01HXX...", "quantity": 1}],
    "customer_name": "Test Customer",
    "customer_phone": "9876543210"
  }'

# 2. Add payment
curl -X POST http://localhost/api/pos/bills/{bill_id}/payments \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"method": "cash", "amount": 750.00}'

# 3. Get receipt
curl http://localhost/api/pos/bills/{bill_id}/receipt \
  -H "Authorization: Bearer {token}"

# 4. Test refund (as owner)
curl -X POST http://localhost/api/pos/bills/{bill_id}/refund \
  -H "Authorization: Bearer {owner_token}" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test refund"}'

# 5. Test idempotency
curl -X POST http://localhost/api/pos/bills \
  -H "Idempotency-Key: test-123" \
  ... # Same payload, should return existing bill
```

## Next Steps
After POS module is validated:
1. Proceed to Spec 5: Appointments & Scheduling
2. Integrate billing with appointment completion
3. Add print confirmation dialog in frontend