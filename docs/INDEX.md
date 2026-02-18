# SalonOS Documentation Index

Complete technical documentation for SalonOS - a local-first salon management system.

---

## Architecture

High-level system design, specifications, and project planning.

| # | Document | Description |
|---|----------|-------------|
| 01 | [Phase 1 Overview](./architecture/01-phase-1-overview.md) | Phase 1 development plan and 4-week timeline |
| 02 | [Frontend Scope](./architecture/02-frontend-scope.md) | Next.js 16 + React 19 frontend implementation scope |
| 03 | [Production Ready](./architecture/03-production-ready.md) | Production deployment checklist and security hardening |
| 04 | [Backend Spec](./architecture/04-backend-spec.md) | FastAPI backend specification: API contracts, billing, POS logic |
| 05 | [Roadmap](./architecture/05-roadmap.md) | Project roadmap across all phases (1-4 complete, Phase 5 planning) |

---

## Deployment

Guides for Docker setup, client installation, and Windows/WSL2 deployment.

| # | Document | Description |
|---|----------|-------------|
| 01 | [Deployment Flow](./deployment/01-deployment-flow.md) | Visual guide from development to production |
| 02 | [Docker Guide](./deployment/02-docker.md) | Docker Compose setup, service management, and troubleshooting |
| 03 | [Client Installation](./deployment/03-client-install.md) | Step-by-step client site installation via DockerHub |
| 04 | [Handover Guide](./deployment/04-handover-guide.md) | Complete handover checklist for client installations |
| 05 | [WSL2 Quickstart](./deployment/05-wsl2-quickstart.md) | Quick setup for Windows 10/11 + WSL2 + Docker Desktop |
| 06 | [WSL2 Network Setup](./deployment/06-wsl2-network-setup.md) | Full WSL2 networking guide: port forwarding, Tailscale, LAN access |
| 07 | [Quickstart](./deployment/07-quickstart.md) | Quick start guide: prerequisites, installation, first login |
| 08 | [Prod Data Quickstart](./deployment/08-prod-data-quickstart.md) | Pull production data to dev environment and sanitize PII |

---

## Features

Documentation for specific feature implementations.

| # | Document | Description |
|---|----------|-------------|
| 01 | [Multi-Staff Services](./features/01-multi-staff-services.md) | Staff contribution splitting for collaborative services |
| 02 | [Attendance](./features/02-attendance.md) | Staff attendance tracking with clock-in/out and half-day support |
| 03 | [Staff Busyness & Wait Times](./features/03-staff-busyness-wait-times.md) | Real-time staff availability and estimated wait times |
| 04 | [Admin Scripts](./features/04-admin-scripts.md) | Administrative database and data management scripts |
| 05 | [Services Management](./features/05-services-management.md) | Service CRUD, categories, addons, and material usage |
| 06 | [Customers Management](./features/06-customers-management.md) | Customer CRUD, search, and pending payment tracking |
| 07 | [Pending Balance](./features/07-pending-balance.md) | Pending balance and free service feature: partial payments, overpayments |
| 08 | [Pending Payment Tracking](./features/08-pending-payment-tracking.md) | Payment collection audit trail, bill resolution, and payment methods |
| 09 | [Centralized Backups](./features/09-centralized-backups.md) | Nightly pg_dump to B2, daily metrics JSON push, multi-branch support |

---

## Database Models

SQLAlchemy model documentation for all 34+ tables.

| # | Document | Description |
|---|----------|-------------|
| - | [Models README](./models/README.md) | Overview, conventions (ULID, paise, UTC), ER diagram, enums |
| 01 | [Base Mixins](./models/01-base-mixins.md) | TimestampMixin, SoftDeleteMixin, ULIDMixin |
| 02 | [User & Auth](./models/02-user-auth.md) | Role, User, Staff models and RBAC |
| 03 | [Billing](./models/03-billing.md) | Bill, BillItem, BillItemStaffContribution, Payment |
| 04 | [Appointments](./models/04-appointments.md) | Appointment, WalkIn models |
| 05 | [Services](./models/05-services.md) | ServiceCategory, Service, ServiceAddon, ServiceMaterialUsage, ServiceStaffTemplate |
| 06 | [Customers](./models/06-customers.md) | Customer, PendingPaymentCollection models |
| 07 | [Inventory](./models/07-inventory.md) | SKU, Supplier, InventoryChangeRequest, StockLedger |
| 08 | [Accounting](./models/08-accounting.md) | CashDrawer, DaySummary, ExportLog |
| 09 | [Audit](./models/09-audit.md) | Event, AuditLog models |

---

## Audits

Technical audits and improvement tracking.

| # | Document | Description |
|---|----------|-------------|
| 01 | [Mobile Responsiveness Audit](./audits/01-mobile-responsiveness-audit.md) | Comprehensive mobile UI audit across all pages and breakpoints |
| 02 | [Redis Cache Audit](./audits/02-redis-cache-audit.md) | Cache invalidation audit with stale-data risk analysis |

---

## Other

| Document | Description |
|----------|-------------|
| [Salon OS Software Development Plan.pdf](./Salon%20OS%20Software%20Development%20Plan.pdf) | Original software development plan (PDF) |
| [HTTPS-SETUP.md](../HTTPS-SETUP.md) | HTTPS certificate setup for mobile camera access (kept in root for dist packaging) |

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Application | `http://localhost` |
| API Docs (Swagger) | `http://localhost/api/docs` |
| API Docs (ReDoc) | `http://localhost/api/redoc` |
| Health Check | `http://localhost/api/healthz` |

**Default Login:** `owner` / `change_me_123` (change immediately!)

---

**Last Updated:** February 2026
**Total Documents:** 34
