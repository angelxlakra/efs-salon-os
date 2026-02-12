# Backend Development Guide - SalonOS

Quick reference for backend development with FastAPI, uv, and pyproject.toml.

## Documentation Guidelines

**When to create summary documents**:
- ✅ **DO**: Major feature additions, architectural changes, new subsystems
- ✅ **DO**: Breaking changes, migration guides, API version updates
- ❌ **DON'T**: Routine bug fixes, small patches, minor improvements
- ❌ **DON'T**: Code refactoring without functional changes

**Format**:
- Use inline code comments for bug fixes
- Update existing docs for minor changes
- Create new docs only for significant features or breaking changes

## Tech Stack

- **Python**: 3.11+
- **Framework**: FastAPI 0.115+
- **Package Manager**: uv (Rust-based, 10-100x faster than pip)
- **Dependencies**: pyproject.toml (modern Python standard)
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0
- **Migrations**: Alembic
- **Task Queue**: Redis + RQ
- **Scheduler**: APScheduler
- **Testing**: pytest + httpx
- **Linting**: ruff + black + mypy

## Project Structure

```
backend/
├── .venv/                      # Virtual environment (created by uv)
├── .python-version             # Python version (3.11)
├── pyproject.toml              # Dependencies & config (like package.json)
├── uv.lock                     # Lock file (like package-lock.json)
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy setup
│   │
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── bill.py
│   │   ├── appointment.py
│   │   └── inventory.py
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── auth.py             # /api/auth/*
│   │   ├── pos.py              # /api/pos/*
│   │   ├── appointments.py     # /api/appointments/*
│   │   ├── inventory.py        # /api/inventory/*
│   │   └── accounting.py       # /api/accounting/*
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── billing_service.py
│   │   └── accounting_service.py
│   │
│   ├── auth/                   # Authentication
│   │   ├── __init__.py
│   │   ├── jwt.py              # Token handling
│   │   ├── permissions.py      # RBAC
│   │   └── dependencies.py     # FastAPI dependencies
│   │
│   ├── workers/                # Background jobs
│   │   ├── __init__.py
│   │   ├── events.py           # Event processing
│   │   └── jobs.py             # Scheduled jobs
│   │
│   ├── utils/                  # Utilities
│   │   ├── __init__.py
│   │   ├── logging.py          # JSON logging
│   │   ├── ulid.py             # ULID generation
│   │   └── encryption.py       # PII encryption
│   │
│   └── seeds/                  # Seed data
│       ├── __init__.py
│       └── initial_data.py     # Initial roles, users
│
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_api/
│   ├── test_services/
│   └── test_models/
│
├── Dockerfile
├── Dockerfile.dev
├── alembic.ini
├── worker.py                   # Background worker entry point
└── README.md
```

## Quick Start

### Initial Setup

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project (if starting fresh)
cd backend
uv init

# Install all dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Verify installation
uv run python --version
```

### Development Workflow

```bash
# Add a new dependency
uv add fastapi sqlalchemy

# Add a dev dependency
uv add --dev pytest black

# Remove a dependency
uv remove package-name

# Update all dependencies
uv lock --upgrade

# Run the app with hot reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run migrations
uv run alembic upgrade head

# Run tests
uv run pytest

# Format code
uv run black app/ tests/

# Lint code
uv run ruff check app/

# Type checking
uv run mypy app/
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Add new field"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current version
uv run alembic current

# Show migration history
uv run alembic history
```

## Key Modules

### main.py - Application Entry Point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, pos, appointments, inventory, accounting, health
from app.database import engine
from app.models import Base

app = FastAPI(
    title="SalonOS API",
    version="1.0.0",
    description="Local-first salon management system"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://salon.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(pos.router, prefix="/api/pos", tags=["POS"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(accounting.router, prefix="/api/accounting", tags=["Accounting"])
```

### config.py - Settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Application
    environment: str = "development"
    debug: bool = False
    
    # Salon
    salon_name: str
    salon_address: str
    gstin: str

settings = Settings()
```

### database.py - SQLAlchemy Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Authentication

### JWT Token Handling

```python
# app/auth/jwt.py
from datetime import datetime, timedelta
from jose import jwt
from app.config import settings

def create_access_token(data: dict) -> str:
    """Create JWT access token (15 min expiry)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token (7 day expiry)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
```

### Permission Checking

```python
# app/auth/permissions.py
from functools import wraps
from fastapi import HTTPException, status, Depends
from app.auth.dependencies import get_current_user
from app.models.user import User

class PermissionChecker:
    PERMISSIONS = {
        "owner": ["*"],  # All permissions
        "receptionist": [
            "bills.create", "bills.read", "bills.update",
            "appointments.create", "appointments.read", "appointments.update",
            "customers.create", "customers.read", "customers.update",
        ],
        "staff": [
            "appointments.read",
            "bills.read",
        ],
    }
    
    @staticmethod
    def has_permission(role: str, resource: str, action: str) -> bool:
        """Check if role has permission for resource.action."""
        role_perms = PermissionChecker.PERMISSIONS.get(role, [])
        
        if "*" in role_perms:
            return True
            
        required_perm = f"{resource}.{action}"
        return required_perm in role_perms

def require_permission(resource: str, action: str):
    """Dependency to check permission."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        if not PermissionChecker.has_permission(
            current_user.role.name,
            resource,
            action
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {resource}.{action}"
            )
        return current_user
    return permission_checker
```

## Background Workers

### Worker Entry Point

```python
# worker.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from app.database import SessionLocal
from app.services.accounting import AccountingService

scheduler = BlockingScheduler(timezone=timezone('Asia/Kolkata'))

@scheduler.scheduled_job(CronTrigger(hour=21, minute=45))
def daily_summary_job():
    """Generate daily summary at 21:45 IST."""
    db = SessionLocal()
    try:
        service = AccountingService(db)
        service.generate_daily_summary()
    finally:
        db.close()

if __name__ == '__main__':
    scheduler.start()
```

## Testing

### Pytest Configuration

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def client(db_session):
    """Create test client with test database."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    from fastapi.testclient import TestClient
    yield TestClient(app)
    
    app.dependency_overrides.clear()
```

### Example Test

```python
# tests/test_api/test_pos.py
def test_create_bill(client, db_session):
    # Login
    response = client.post("/api/auth/login", json={
        "username": "owner",
        "password": "test123"
    })
    token = response.json()["access_token"]
    
    # Create bill
    response = client.post(
        "/api/pos/bills",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"service_id": "01HXX...", "quantity": 1}],
            "customer_name": "Test Customer"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
```

## Running the Application

### Development (Local - without Docker)
```bash
# Install dependencies
uv sync --group dev

# Run migrations
uv run alembic upgrade head

# Start server with hot reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start worker (in another terminal)
uv run python worker.py
```

### Development (Docker)
```bash
# Build and start
docker compose up --build

# Run migrations inside container
docker compose exec api uv run alembic upgrade head

# View logs
docker compose logs -f api

# Run tests inside container
docker compose exec api uv run pytest
```

### Production
```bash
# Dependencies are installed in Dockerfile using:
# RUN uv sync --frozen --no-dev

# Start with multiple workers
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# Start worker
uv run python worker.py
```

## Environment Variables

Required in `.env`:
```env
# Security
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://salon_user:password@postgres:5432/salon_db

# Redis
REDIS_URL=redis://redis:6379/0

# Application
ENVIRONMENT=production
TZ=Asia/Kolkata

# Salon
SALON_NAME=Your Salon Name
SALON_ADDRESS=Your Address
GSTIN=29XXXXX1234X1ZX
```

## Common Tasks

### Dependency Management

```bash
# View installed packages
uv pip list

# Check for outdated packages
uv tree

# Export to requirements.txt (for compatibility)
uv export --no-hashes --format requirements-txt > requirements.txt

# Lock dependencies
uv lock

# Upgrade all dependencies
uv lock --upgrade
```

### Code Quality

```bash
# Format code (auto-fix)
uv run black app/ tests/

# Lint code
uv run ruff check app/

# Lint and auto-fix
uv run ruff check app/ --fix

# Type checking
uv run mypy app/

# Run all checks
uv run black app/ && uv run ruff check app/ && uv run mypy app/
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_api/test_pos.py

# Run tests matching pattern
uv run pytest -k "test_auth"

# Run with verbose output
uv run pytest -v

# Run tests in parallel (install pytest-xdist first)
uv add --dev pytest-xdist
uv run pytest -n auto
```

## Key Design Patterns

- **Repository Pattern**: Services layer abstracts database access
- **Dependency Injection**: FastAPI's Depends() for clean architecture
- **Factory Pattern**: Permission checking, token creation
- **Event-Driven**: Redis queue for async operations
- **Idempotency**: Header-based idempotent request handling

## Performance Tips

- Use database indexes on frequently queried columns
- Implement connection pooling (already configured)
- Cache frequently accessed data in Redis
- Use bulk operations for large datasets
- Profile slow queries with `EXPLAIN ANALYZE`

## Troubleshooting

### uv Issues

```bash
# Clear uv cache
uv cache clean

# Reinstall all dependencies
rm -rf .venv uv.lock
uv sync

# Check Python version
uv run python --version

# Verify uv installation
uv --version
```

### Import Errors
```bash
# Ensure PYTHONPATH is set (if running outside Docker)
export PYTHONPATH=/app

# Or run with uv (which handles this automatically)
uv run python script.py
```

### Database Connection
```bash
# Test connection
uv run python -c "from app.database import engine; print(engine.connect())"
```

### Migration Issues
```bash
# Check current version
uv run alembic current

# Rollback one version
uv run alembic downgrade -1

# Show full history
uv run alembic history --verbose
```

## Comparison: npm vs uv

| Task | npm/yarn | uv | Notes |
|------|----------|----|----|
| Initialize | `npm init` | `uv init` | Creates pyproject.toml |
| Install all | `npm install` | `uv sync` | Respects lock file |
| Add package | `npm install express` | `uv add fastapi` | Updates pyproject.toml |
| Add dev | `npm install -D jest` | `uv add --dev pytest` | Dev dependencies |
| Remove | `npm uninstall pkg` | `uv remove pkg` | Updates files |
| Run script | `npm run dev` | `uv run command` | Activates venv |
| List packages | `npm list` | `uv pip list` | Show installed |
| Update all | `npm update` | `uv lock --upgrade` | Update lock file |

---

**Version**: 1.0.0  
**Python**: 3.11+  
**Package Manager**: uv (Rust-based)  
**FastAPI**: 0.115+  
**Status**: Production Ready ✅