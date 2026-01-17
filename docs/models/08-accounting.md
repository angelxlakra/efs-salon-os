# Accounting Models

**File**: `backend/app/models/accounting.py`

Models for cash management, daily summaries, and export tracking.

---

## CashDrawer

Cash drawer sessions for tracking physical cash on hand.

**Table**: `cash_drawer`

**Mixins**: `ULIDMixin` (no TimestampMixin - has custom tracking)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | String(26) | No (PK) | ULID primary key |
| `opened_by` | String(26) | No | FK to users.id |
| `opened_at` | DateTime(tz) | No | When drawer was opened |
| `opening_float` | Integer | No | Starting cash in paise |
| `closed_by` | String(26) | Yes | FK to users.id |
| `closed_at` | DateTime(tz) | Yes | When drawer was closed |
| `closing_counted` | Integer | Yes | Counted cash at close in paise |
| `expected_cash` | Integer | No | Calculated expected cash in paise (default: 0) |
| `variance` | Integer | Yes | Difference: counted - expected in paise |
| `reopened_at` | DateTime(tz) | Yes | When drawer was reopened |
| `reopened_by` | String(26) | Yes | FK to users.id |
| `reopen_reason` | Text | Yes | Reason for reopening |
| `notes` | Text | Yes | Additional notes |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `opener` | User | Many-to-One | Who opened the drawer |
| `closer` | User | Many-to-One | Who closed the drawer |
| `reopener` | User | Many-to-One | Who reopened (if applicable) |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `opening_float_rupees` | float | Opening float in rupees |
| `closing_counted_rupees` | float | Closing count in rupees |
| `variance_rupees` | float | Variance in rupees |

### Cash Drawer Workflow

```
┌─────────────────────────────────────────────────────────┐
│                    DAILY WORKFLOW                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐                                        │
│  │  OPEN DRAWER │ ─── Enter opening float (e.g., Rs 500)│
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                        │
│  │  DRAWER OPEN │ ─── Accept cash payments all day      │
│  │   (Active)   │     Expected cash auto-calculated     │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼ End of day                                     │
│  ┌──────────────┐                                        │
│  │ COUNT & CLOSE│ ─── Enter counted cash                │
│  └──────┬───────┘     System calculates variance         │
│         │                                                │
│         │  ┌────────────────────────────────────┐        │
│         │  │ Variance = Counted - Expected     │        │
│         │  │ Positive = Over                   │        │
│         │  │ Negative = Short                  │        │
│         │  └────────────────────────────────────┘        │
│         │                                                │
│         ├──────────────────────────────────────────┐     │
│         │                                          │     │
│         ▼                                          ▼     │
│  ┌──────────────┐                          ┌───────────┐ │
│  │ DRAWER CLOSED│                          │  REOPEN?  │ │
│  │  (for day)   │◄─────────────────────────│(no approval│ │
│  └──────────────┘                          │ needed)   │ │
│                                            └───────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Expected Cash Calculation

```python
# Expected = Opening Float + Cash Payments - Cash Refunds

opening_float = 50000  # Rs 500

# During the day:
cash_payments = db.query(func.sum(Payment.amount)).filter(
    Payment.payment_method == PaymentMethod.CASH,
    Payment.confirmed_at >= drawer.opened_at,
    Payment.confirmed_at <= drawer.closed_at
).scalar() or 0

# Cash refunds (if any)
cash_refunds = ...  # Similar query for refund payments

expected_cash = opening_float + cash_payments - cash_refunds
```

### Reopen Policy

- **No owner approval required** for reopen
- Reason is **automatically logged**
- Allows fixing errors without overhead
- Audit trail preserved

---

## DaySummary

Daily business summary auto-generated each night.

**Table**: `day_summary`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `summary_date` | Date | No | Yes (unique) | Date of summary |
| `total_bills` | Integer | No | - | Number of bills posted (default: 0) |
| `refund_count` | Integer | No | - | Number of refunds (default: 0) |
| `gross_revenue` | Integer | No | - | Total before discounts/refunds in paise |
| `discount_amount` | Integer | No | - | Total discounts in paise |
| `refund_amount` | Integer | No | - | Total refunds in paise |
| `net_revenue` | Integer | No | - | Net revenue in paise |
| `cgst_collected` | Integer | No | - | Central GST in paise |
| `sgst_collected` | Integer | No | - | State GST in paise |
| `total_tax` | Integer | No | - | Total tax in paise |
| `cash_collected` | Integer | No | - | Cash payments in paise |
| `digital_collected` | Integer | No | - | UPI/Card payments in paise |
| `estimated_cogs` | Integer | No | - | Cost of goods sold estimate in paise |
| `estimated_profit` | Integer | No | - | Profit estimate in paise (owner only) |
| `generated_at` | DateTime(tz) | No | - | When summary was generated |
| `generated_by` | String(26) | Yes | - | FK to users.id (NULL if auto-generated) |
| `is_final` | Boolean | No | - | Locked status (default: false) |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `generator` | User | Many-to-One | Who generated (if manual) |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `net_revenue_rupees` | float | Net revenue in rupees |

### Revenue Calculation

```
Gross Revenue         = Sum of all posted bill totals
- Discounts           = Sum of all discount_amount
- Refunds             = Sum of all refund bill totals
= Net Revenue

Tax Breakdown:
  CGST Collected      = Sum of all cgst_amount
  SGST Collected      = Sum of all sgst_amount
  Total Tax           = CGST + SGST

Payment Split:
  Cash Collected      = Sum of cash payments
  Digital Collected   = Sum of UPI + Card + Other payments
```

### Profit Estimate (Owner Only)

```python
# Simplified profit estimate
estimated_profit = net_revenue - estimated_cogs

# COGS can be estimated from:
# 1. Product sales (using avg_cost from SKU)
# 2. Percentage-based estimate for services
```

### Generation Schedule

| Trigger | Time | Description |
|---------|------|-------------|
| Auto | 21:45 IST | Nightly scheduled job |
| Manual | Any time | Owner/receptionist can trigger |
| Catch-up | On startup | Generates missing summaries |

### Snapshot Immutability

Once `is_final = True`:
- Summary cannot be modified
- Used for month-end close
- Required for tax compliance

---

## ExportLog

Audit trail for report exports.

**Table**: `export_log`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `export_type` | String | No | - | Type of export |
| `export_format` | String | No | - | File format |
| `file_path` | String | No | - | Path to exported file |
| `file_size` | Integer | Yes | - | File size in bytes |
| `parameters` | JSONB | Yes | - | Export parameters/filters |
| `exported_by` | String(26) | No | - | FK to users.id |
| `exported_at` | DateTime(tz) | No | Yes | When export was created |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `exporter` | User | Many-to-One | Who exported |

### Export Types

| Type | Description |
|------|-------------|
| `daily_summary` | Single day summary |
| `monthly_summary` | Monthly aggregated summary |
| `monthly_tax` | GST tax report for filing |
| `bill_detail` | Detailed bill listing |
| `inventory_report` | Stock status report |
| `customer_list` | Customer export |

### Export Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| `pdf` | .pdf | Printing, archival |
| `xlsx` | .xlsx | Spreadsheet analysis |
| `csv` | .csv | Data import/export |

### File Path Convention

```
/salon-data/exports/{year}/{month}/{type}_{date}_{timestamp}.{ext}

Examples:
/salon-data/exports/2025/10/daily_summary_2025-10-15_1697385600.pdf
/salon-data/exports/2025/10/monthly_tax_2025-10_1698681600.xlsx
```

### Parameters JSONB

Records the filters used for the export:

```json
{
  "date_from": "2025-10-01",
  "date_to": "2025-10-31",
  "include_refunds": true,
  "group_by": "day"
}
```

---

## Entity Relationship

```
┌─────────────────┐
│   CashDrawer    │
├─────────────────┤
│ id (PK)         │
│ opened_by (FK)  │───┐
│ closed_by (FK)  │───┤
│ reopened_by(FK) │───┤
│ opening_float   │   │
│ closing_counted │   │
│ expected_cash   │   │     ┌──────────────┐
│ variance        │   └────►│     User     │
└─────────────────┘         └──────────────┘
                                   ▲
┌─────────────────┐                │
│   DaySummary    │                │
├─────────────────┤                │
│ id (PK)         │                │
│ summary_date    │                │
│ gross_revenue   │                │
│ net_revenue     │                │
│ total_tax       │                │
│ generated_by(FK)│────────────────┘
│ is_final        │
└─────────────────┘

┌─────────────────┐
│   ExportLog     │
├─────────────────┤
│ id (PK)         │
│ export_type     │
│ export_format   │
│ file_path       │
│ exported_by(FK) │────────────────►User
│ exported_at     │
└─────────────────┘
```

---

## Dashboard Metrics

Real-time dashboard shows:

| Metric | Description | Visible To |
|--------|-------------|------------|
| Today's Revenue | Net revenue so far | Owner, Receptionist |
| Bill Count | Number of bills today | Owner, Receptionist |
| Cash vs Digital | Payment method breakdown | Owner, Receptionist |
| CGST/SGST | Tax collected today | Owner, Receptionist |
| Discounts Given | Total discounts today | Owner, Receptionist |
| Refunds | Total refunds today | Owner, Receptionist |
| Profit Estimate | Revenue - COGS | **Owner Only** |

### Auto-Refresh

Dashboard auto-refreshes every **150 seconds** (2.5 minutes).

---

## Monthly Tax Report

For GST filing, generate monthly report:

```json
{
  "month": "October 2025",
  "total_taxable_value": 12500000,  // Rs 1,25,000
  "cgst_collected": 1125000,        // Rs 11,250
  "sgst_collected": 1125000,        // Rs 11,250
  "total_gst": 2250000,             // Rs 22,500
  "bill_count": 342,
  "refund_adjustments": -45000      // Rs 450
}
```

---

## API Usage Notes

### Open Cash Drawer

```json
POST /api/cash/open
{
  "opening_float": 50000
}
```

### Close Cash Drawer

```json
POST /api/cash/close
{
  "closing_counted": 285000,
  "notes": "End of day close"
}
```

### Reopen Cash Drawer

```json
POST /api/cash/reopen
{
  "reason": "Need to process late payment"
}
```

### Generate Daily Summary

```json
POST /api/reports/daily/generate
{
  "date": "2025-10-15"
}
```

### Get Monthly Tax Report

```json
GET /api/reports/tax?month=2025-10
```
