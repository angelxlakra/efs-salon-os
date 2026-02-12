# SalonOS - Local-First Salon Management System

## Project Overview

SalonOS is a comprehensive Point of Sale (POS), scheduling, inventory, and accounting system designed specifically for a unisex beauty salon. It operates entirely on the local network (LAN) with no cloud dependencies, ensuring fast performance and data privacy.

## Documentation Guidelines for Claude

**When to create summary/documentation files**:
- ✅ **DO create docs for**: Major features, architectural changes, new subsystems, breaking changes
- ✅ **DO create docs for**: API version updates, migration guides, deployment changes
- ❌ **DON'T create docs for**: Routine bug fixes, small patches, minor code improvements
- ❌ **DON'T create docs for**: Code refactoring without functional changes, typo fixes

**How to document**:
- **Bug fixes**: Add inline comments in code, update existing docs if needed
- **Minor changes**: Update relevant existing documentation
- **Major features**: Create new dedicated documentation file with examples and testing steps
- **Keep it practical**: Focus on what developers need to know, not exhaustive details

## Repository Structure

```
salon-os/
├── backend/           # FastAPI backend service
├── frontend/          # Next.js React frontend
├── nginx/            # Reverse proxy configuration
├── docs/             # Complete technical specifications
├── docker-compose.yml
└── README.md
```

## Tech Stack

- **Frontend**: React 18 + Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + SQLAlchemy + Alembic (Python 3.11)
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7 + RQ
- **Scheduler**: APScheduler
- **Deployment**: Docker Compose (local-first)

## Key Features

### Phase 1 (Current)
- ✅ **POS & Billing**: Cart-based billing with GST calculation, 80mm receipt printing
- ✅ **Appointments**: Reception-driven scheduling with conflict detection
- ✅ **Inventory**: SKU management with approval workflow
- ✅ **Accounting**: Real-time dashboards, daily/monthly reports, cash drawer
- ✅ **Access Control**: Role-based permissions (Owner, Receptionist, Staff)
- ✅ **Background Jobs**: Auto-generation of summaries, nightly backups

### Future Phases
- 📱 Customer self-booking portal
- 💬 WhatsApp integration (reminders, campaigns)
- 📊 Advanced analytics and reporting
- 👥 Staff commission tracking
- 🎥 CCTV analytics integration

## Architecture

### Network Topology
```
LAN (192.168.1.0/24)
    │
    └─── nginx:80 (http://localhost)
           │
           ├─── frontend:3000 (internal)
           └─── api:8000 (internal)
                  │
                  ├─── postgres:5432 (internal only)
                  ├─── redis:6379 (internal only)
                  └─── worker (internal)
```

### Data Flow
```
User → Nginx → Frontend (React) → API (FastAPI) → PostgreSQL
                                 ↓
                              Redis (Queue)
                                 ↓
                              Worker (Background Jobs)
```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- 50GB+ disk space
- Static IP on LAN (recommended)

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd salon-os

# Setup environment
cp .env.example .env
# Edit .env with secure passwords

# Start services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Load seed data
docker-compose exec api python -m app.seeds.initial_data

# Access application
# http://localhost (or http://192.168.1.50)
```

### Windows/WSL2 Deployment

**For Windows 10/11 + WSL2 + Docker Desktop:**

SalonOS fully supports Windows deployment with WSL2. However, WSL2 networking requires additional configuration for external access (LAN devices, Tailscale).

**Quick Fix:**
```powershell
# In PowerShell as Administrator
.\wsl-port-forward.ps1
```

**Detailed Guides:**
- Quick setup: `WSL2-QUICKSTART.md`
- Full documentation: `WSL2-NETWORK-SETUP.md`
- Troubleshooting: `diagnose-network.ps1`

**Included Scripts:**
- `wsl-port-forward.ps1` - Configure port forwarding (run after reboot)
- `setup-auto-forward.ps1` - Auto-configure on Windows startup
- `diagnose-network.ps1` - Network diagnostics tool

### Default Credentials
```
Username: owner
Password: change_me_123
⚠️ CHANGE IMMEDIATELY after first login!
```

## Development

### Running in Development Mode
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Database Migrations
```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback one migration
docker-compose exec api alembic downgrade -1
```

### Testing
```bash
# Run backend tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app tests/
```

### Logs
```bash
# View all logs
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

## Key Concepts

### Invoice & Ticket Numbering
- **Invoices**: `SAL-YY-NNNN` (e.g., `SAL-25-0042`) - Resets yearly on April 1
- **Tickets**: `TKT-YYMMDD-###` (e.g., `TKT-251015-001`) - Resets daily

### Money Handling
- All monetary values stored as **INTEGER paise** (₹1 = 100 paise)
- Ensures precision and avoids floating-point errors
- Example: ₹349.50 → 34950 paise

### Tax Calculation
- All catalog prices are **tax-inclusive**
- GST Rate: 18% (9% CGST + 9% SGST)
- Tax extracted from inclusive price: `tax = (price * 18) / 118`
- Rounding: Final total rounded to nearest ₹1

### ID System
- Primary keys use **ULID** (26-character, lexicographically sortable)
- Better than UUID for time-ordered data
- Example: `01HXXX1234ABCD567890EFGH`

## API Documentation

Once running, access interactive API docs:
- **Swagger UI**: http://localhost/api/docs
- **ReDoc**: http://localhost/api/redoc

### Key Endpoints

**Authentication**
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Current user info

**POS & Billing**
- `POST /api/pos/bills` - Create bill
- `POST /api/pos/bills/:id/payments` - Record payment
- `GET /api/pos/bills/:id/receipt` - Get receipt for printing

**Appointments**
- `POST /api/appointments` - Create appointment
- `GET /api/appointments` - List appointments (with filters)
- `POST /api/walkins` - Register walk-in

**Inventory**
- `POST /api/inventory/skus` - Create SKU
- `POST /api/inventory/change-requests` - Submit stock change
- `POST /api/inventory/change-requests/:id/approve` - Approve change (owner only)

**Accounting**
- `GET /api/reports/dashboard` - Real-time dashboard
- `GET /api/reports/daily` - Daily summaries
- `GET /api/reports/monthly` - Monthly report
- `GET /api/reports/tax` - GST tax report

## Role-Based Permissions

| Feature | Owner | Receptionist | Staff |
|---------|-------|--------------|-------|
| Create bills | ✅ | ✅ | ❌ |
| Apply discounts | ✅ | ✅ (≤₹500) | ❌ |
| Refund bills | ✅ | ❌ | ❌ |
| View profit | ✅ | ❌ | ❌ |
| Approve inventory | ✅ | ❌ | ❌ |
| View schedules | ✅ | ✅ | ✅ (limited PII) |
| Mark complete | ✅ | ✅ | ✅ |
| Export reports | ✅ | ✅ | ❌ |

## Background Jobs

Scheduled jobs run automatically:
- **21:45 IST**: Daily summary generation
- **23:30 IST**: Nightly database backup
- **On startup**: Catch-up missing summaries

## Backup & Recovery

### Automatic Backups
- Location: `/salon-data/backups/`
- Format: PostgreSQL custom format
- Frequency: Nightly at 23:30 IST
- Retention: 7 days local, 30 days cloud (optional)

### Manual Backup
```bash
docker-compose exec postgres pg_dump -U salon_user -Fc salon_db > backup.sql
```

### Restore
```bash
docker-compose down
docker-compose run --rm postgres pg_restore -U salon_user -d salon_db --clean backup.sql
docker-compose up -d
```

## Monitoring

### Health Checks
```bash
# Basic health
curl http://localhost/api/healthz

# Readiness (DB + Redis)
curl http://localhost/api/readyz
```

### Metrics to Watch
- API response time (target: <200ms)
- Queue depth (Redis)
- Database connections
- Disk space usage
- Backup job status

## Troubleshooting

docker compose {COMMAND}

### Services Won't Start
```bash
# Check status
docker compose ps

# View logs
docker compose logs api postgres redis

# Restart all
docker compose down && docker-compose up -d
```

### Database Connection Issues
```bash
# Verify PostgreSQL is running
docker compose exec postgres pg_isready -U salon_user

# Check credentials in .env
cat .env | grep DB_PASSWORD
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Verify network connectivity
ping localhost

# Check for slow queries
docker-compose exec postgres psql -U salon_user -d salon_db -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

## Security

### Network Security
- PostgreSQL and Redis NOT exposed to LAN
- Only Nginx on port 80
- Internal Docker network for service communication

### Authentication
- JWT tokens (15-minute access, 7-day refresh)
- Bcrypt password hashing (cost factor 12)
- Rate limiting on auth endpoints (5 attempts/minute)

### Data Protection
- PII fields encrypted at rest
- Audit logging for all critical operations
- Backups encrypted (if cloud storage configured)

## Contributing

### Code Style
- **Python**: Follow PEP 8, use Black formatter
- **TypeScript**: Follow Airbnb style guide
- **Commits**: Conventional commits format

### Pull Request Process
1. Create feature branch from `main`
2. Write tests for new features
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

## Documentation

Complete technical specifications available in `/docs/`:
- Infrastructure setup
- Database schema
- API contracts
- Authentication system
- Business logic
- Deployment procedures

## Support

### Common Issues
Check the troubleshooting guide in each technical spec:
- `/docs/spec-01-infrastructure.md` - Setup issues
- `/docs/spec-02-database-schema.md` - Database issues
- `/docs/spec-03-authentication.md` - Auth issues
- And more...

### Health Status
- Dashboard: http://localhost
- API Health: http://localhost/api/healthz
- API Docs: http://localhost/api/docs

## License

[Your License Here]

## Version

**Phase 1 v1.0** - Production Ready ✅
- Core POS, Scheduling, Inventory, Accounting
- Role-based access control
- Background jobs and automation
- Production deployment ready

---

**Last Updated**: October 15, 2025  
**Status**: Phase 1 Complete, Phase 2 Planning