# SalonOS Phase 1 Development Plan

## Timeline: Weeks 1-4

## Overview
Phase 1 establishes the core operational system: POS/Billing, Reception-driven Appointments, basic Inventory management, real-time Accounting dashboards, Cash drawer operations, and Role-based Access Control.

## Deliverables

### 1. Infrastructure & Foundation
- Docker Compose stack (nginx, api, worker, postgres, redis)
- Database schema + Alembic migrations
- Authentication & authorization system
- Base API structure with FastAPI

### 2. POS & Billing Module
- Cart-based billing with services
- Bill-level discounts with audit logging
- Manual payment confirmation (cash/UPI/card)
- 80mm receipt printing (browser-based)
- Invoice numbering: SAL-YY-NNNN
- GST calculation (CGST/SGST)

### 3. Appointments & Scheduling Module
- Reception-driven appointment creation/editing
- Required fields: name, phone, service, time slot
- Conflict detection
- Day/week calendar views
- Walk-in support
- Staff assignment (optional at booking)

### 4. Inventory Module
- SKU management (categories, UOM, reorder points)
- Supplier management
- Change request workflow (receive/adjust)
- Owner approval system
- Stock ledger tracking
- Low-stock visual filters
- Weighted average costing

### 5. Accounting & Dashboards Module
- Real-time dashboard with 150s auto-refresh
- Daily summary generation (manual + scheduled 21:45 IST)
- Cash vs digital split
- CGST/SGST breakdown
- Discount tracking
- Refund/void tracking (separate section)
- Monthly tax reports
- Export functionality (PDF/XLS)

### 6. Cash Drawer Operations
- Open drawer with float
- Close drawer with counted cash
- Reopen capability (logged, no approval needed)
- Reconciliation tracking

### 7. Access Control & Privacy
- Role-based permissions (Owner, Receptionist, Staff)
- Staff privacy mode (first name + ticket only)
- Staff service notes (editable 15 min)
- Staff landing = today's schedule

### 8. Background Jobs
- Daily summary auto-generation (21:45 IST)
- Catch-up job on startup
- Event processing (bill.posted, payment.captured, etc.)
- Nightly backups (23:30 IST)

## Technical Stack Confirmation

**Frontend**: React + Next.js
**Backend**: FastAPI + SQLAlchemy + Alembic
**Database**: PostgreSQL
**Cache/Queue**: Redis + RQ worker
**Scheduler**: APScheduler
**Reverse Proxy**: Nginx
**Deployment**: Docker Compose

## Development Order

### Week 1: Foundation
1. Infrastructure setup spec
2. Database schema spec
3. Authentication system spec

### Week 2: Core Operations
4. POS & Billing spec
5. Appointments & Scheduling spec

### Week 3: Inventory & Accounting
6. Inventory management spec
7. Accounting dashboards spec
8. Cash drawer spec

### Week 4: Access & Jobs
9. Access control & privacy spec
10. Background jobs spec

## Acceptance Criteria Summary

- All Docker services start successfully
- Database migrations run cleanly
- JWT authentication working with role-based access
- POS creates bills with correct GST calculations
- 80mm receipts print correctly
- Appointments can be created with conflict detection
- Inventory change requests require owner approval
- Real-time dashboard updates within 1.5s
- Daily summaries generate automatically
- Staff see limited PII (first name + ticket)
- Cash drawer flows logged correctly
- Exports save to /salon-data/exports/

## Files Generated
Each spec will be created in detail with:
- Purpose & scope
- Requirements
- Data models
- API endpoints
- UI components
- Validation rules
- Error handling
- Testing checklist