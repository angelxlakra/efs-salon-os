# SalonOS - Local-First Salon Management System

> A comprehensive Point of Sale (POS), scheduling, inventory, and accounting system designed specifically for unisex beauty salons. Operates entirely on your local network with no cloud dependencies.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

### Current Phase 1 (In Development)

- **POS & Billing**: Cart-based checkout, GST calculation, 80mm receipt printing
- **Appointments**: Schedule management with conflict detection
- **Inventory**: SKU management with approval workflows
- **Accounting**: Real-time dashboards, daily/monthly reports, cash drawer tracking
- **Access Control**: Role-based permissions (Owner, Receptionist, Staff)
- **Background Jobs**: Auto-generation of reports, nightly backups

### Future Phases

- Customer self-booking portal
- WhatsApp integration (reminders, campaigns)
- Advanced analytics and reporting
- Staff commission tracking
- CCTV analytics integration

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | React 18 + Next.js 14 + TypeScript + Tailwind CSS |
| **Backend** | FastAPI + SQLAlchemy + Alembic (Python 3.11) |
| **Database** | PostgreSQL 15 |
| **Cache/Queue** | Redis 7 + RQ |
| **Scheduler** | APScheduler |
| **Deployment** | Docker Compose (local-first) |
| **Reverse Proxy** | Nginx |

## Architecture

### Network Topology

```
LAN (192.168.1.0/24)
    │
    └─── nginx:80 (http://salon.local)
           │
           ├─── frontend:3000 (internal)
           └─── api:8000 (internal)
                  │
                  ├─── postgres:5432 (internal only)
                  ├─── redis:6379 (internal only)
                  └─── worker (background jobs)
```

### Services

- **nginx**: Reverse proxy, handles all external traffic on port 80
- **api**: FastAPI backend service with REST API
- **worker**: Background job processor (reports, backups)
- **postgres**: Primary database (not exposed to LAN)
- **redis**: Job queue and caching (not exposed to LAN)

## Getting Started

### Prerequisites

- Docker & Docker Compose
- 50GB+ disk space
- Static IP on LAN (recommended)

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd efs-salon-os

# Copy environment configuration
cp .env.example .env

# Edit .env with your secure passwords
# IMPORTANT: Change all default passwords!
nano .env

# Start all services
./start.sh

# Access the application
# http://salon.local (or http://192.168.1.50)
```

### First Time Setup

```bash
# Run database migrations
docker compose exec api alembic upgrade head

# Load initial seed data
docker compose exec api python -m app.seeds.initial_data

# Access the application
# Default credentials:
# Username: owner
# Password: change_me_123
# ⚠️ CHANGE IMMEDIATELY after first login!
```

## Development

### Running in Development Mode

```bash
# Start with hot-reload enabled
./dev.sh

# Or manually with docker compose
docker compose up --build
```

### Backend Development

The backend uses `uv` (fast Python package manager) and modern Python tooling:

```bash
# Navigate to backend
cd backend

# Install dependencies
uv sync --group dev

# Run locally (without Docker)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest

# Format code
uv run black app/

# Lint code
uv run ruff check app/
```

See [backend/CLAUDE.md](backend/claude.md) for detailed backend development guide.

### Database Migrations

```bash
# Create a new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec api alembic upgrade head

# Rollback one migration
docker compose exec api alembic downgrade -1

# View migration history
docker compose exec api alembic history
```

### Viewing Logs

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f postgres

# View last 100 lines
docker compose logs --tail=100 api
```

## Project Structure

```
efs-salon-os/
├── backend/              # FastAPI backend service
│   ├── app/             # Application code
│   │   ├── main.py      # FastAPI app entry point
│   │   ├── worker.py    # Background worker
│   │   ├── models/      # Database models
│   │   ├── api/         # API routes
│   │   ├── services/    # Business logic
│   │   ├── auth/        # Authentication
│   │   └── utils/       # Utilities
│   ├── alembic/         # Database migrations
│   ├── tests/           # Test suite
│   ├── Dockerfile       # Production Docker image
│   └── pyproject.toml   # Dependencies & config
│
├── frontend/            # Next.js React frontend
│   └── src/            # Frontend source code
│
├── nginx/              # Reverse proxy configuration
│   └── nginx.conf      # Nginx config
│
├── salon-data/         # Data persistence (gitignored)
│   ├── postgres/       # Database files
│   ├── redis/          # Redis persistence
│   ├── logs/           # Application logs
│   └── backups/        # Automated backups
│
├── compose.yaml        # Docker Compose configuration
├── .env.example        # Environment variables template
├── start.sh            # Quick start script
├── stop.sh             # Quick stop script
├── dev.sh              # Development mode script
├── claude.md           # Project instructions
└── README.md           # This file
```

## Key Concepts

### Invoice & Ticket Numbering

- **Invoices**: `SAL-YY-NNNN` (e.g., `SAL-25-0042`) - Resets yearly on April 1
- **Tickets**: `TKT-YYMMDD-###` (e.g., `TKT-251015-001`) - Resets daily

### Money Handling

All monetary values are stored as **INTEGER paise** (₹1 = 100 paise) to ensure precision and avoid floating-point errors.

Example: ₹349.50 → 34950 paise

### Tax Calculation

- All catalog prices are **tax-inclusive**
- GST Rate: 18% (9% CGST + 9% SGST)
- Tax extracted from inclusive price: `tax = (price × 18) / 118`
- Final total rounded to nearest ₹1

### ID System

Primary keys use **ULID** (26-character, lexicographically sortable) instead of traditional UUIDs for better time-ordered data management.

Example: `01HXXX1234ABCD567890EFGH`

## API Documentation

Once running, access interactive API documentation:

- **Swagger UI**: http://salon.local/api/docs
- **ReDoc**: http://salon.local/api/redoc
- **Health Check**: http://salon.local/healthz

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

- **Location**: `./salon-data/backups/`
- **Format**: PostgreSQL custom format
- **Frequency**: Nightly at 23:30 IST
- **Retention**: 7 days local

### Manual Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose down
docker compose up -d postgres
docker compose exec -T postgres pg_restore -U salon_user -d salon_db --clean < backup_20251017.sql
docker compose up -d
```

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://salon.local/healthz

# Readiness check (will include DB + Redis in future)
curl http://salon.local/readyz

# Service status
docker compose ps
```

### Metrics to Watch

- API response time (target: <200ms)
- Queue depth (Redis)
- Database connections
- Disk space usage
- Backup job status

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker compose ps

# View service logs
docker compose logs api postgres redis

# Restart all services
docker compose down
docker compose up -d
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker compose exec postgres pg_isready -U salon_user

# Check database credentials
cat .env | grep POSTGRES

# Test database connection
docker compose exec api python -c "from app.database import engine; print(engine.connect())"
```

### Port Already in Use

```bash
# Check what's using port 80
sudo lsof -i :80

# Stop conflicting service or change port in compose.yaml
```

### Permission Issues

```bash
# Fix ownership of data directory
sudo chown -R $USER:$USER salon-data/

# Restart services
docker compose restart
```

## Security

### Network Security

- PostgreSQL and Redis **NOT** exposed to LAN
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

## Utility Scripts

### start.sh

Starts all services in production mode:

```bash
./start.sh
```

### stop.sh

Stops all services (data is preserved):

```bash
./stop.sh
```

### dev.sh

Starts services in development mode with build:

```bash
./dev.sh
```

## Environment Variables

Required variables in `.env`:

```env
# Database
POSTGRES_DB=salon_db
POSTGRES_USER=salon_user
POSTGRES_PASSWORD=your_secure_password_here

# Security
SECRET_KEY=your_secret_key_here_use_openssl_rand_hex_32

# Application
ENVIRONMENT=production
TZ=Asia/Kolkata

# Salon Details
SALON_NAME=Your Salon Name
SALON_ADDRESS=Your Salon Address
GSTIN=29XXXXX1234X1ZX
```

Generate secure keys:

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate random password
openssl rand -base64 32
```

## Contributing

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **TypeScript**: Follow Airbnb style guide
- **Commits**: Use conventional commits format

### Pull Request Process

1. Create feature branch from `main`
2. Write tests for new features
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

## Testing

```bash
# Run backend tests
docker compose exec api uv run pytest

# Run with coverage
docker compose exec api uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
docker compose exec api uv run pytest tests/test_api/test_pos.py
```

## Documentation

Complete technical specifications available in:

- [claude.md](claude.md) - Project overview and instructions
- [backend/claude.md](backend/claude.md) - Backend development guide

## Version

**Phase 1 v0.1.0** - In Development 🚧

- ✅ Core infrastructure setup
- ✅ Docker Compose configuration
- ✅ Backend API skeleton
- ✅ Database setup with PostgreSQL
- 🚧 POS & Billing (in progress)
- 🚧 Appointments (in progress)
- 🚧 Inventory (in progress)
- 🚧 Accounting (in progress)

## Support

### Common Issues

- **Services won't start**: Check Docker is running and ports are available
- **Database connection failed**: Verify credentials in `.env`
- **Permission denied**: Check file ownership of `salon-data/`
- **Slow performance**: Check disk space and Docker resource limits

### Health Status Endpoints

- Dashboard: http://salon.local
- API Health: http://salon.local/healthz
- API Readiness: http://salon.local/readyz
- API Docs: http://salon.local/api/docs

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built with modern Python tooling:
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations

---

**Last Updated**: October 17, 2025
**Status**: Phase 1 Development
**Repository**: [efs-salon-os](https://github.com/yourusername/efs-salon-os)

For detailed development instructions, see [claude.md](claude.md)
