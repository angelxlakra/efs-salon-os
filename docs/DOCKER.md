# SalonOS Docker Deployment Guide

Complete guide for running SalonOS with Docker Compose.

## Quick Start

### Production Mode

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Access the application at: **http://localhost** or **http://salon.local**

### Development Mode (with hot reload)

```bash
# Build and start with development overrides
docker compose -f compose.yaml -f compose.dev.yaml up -d

# View frontend logs
docker compose logs -f frontend

# Stop all services
docker compose down
```

Frontend changes will hot-reload automatically.

## Services Overview

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| **postgres** | salon-postgres | 5432 | PostgreSQL 15 database |
| **redis** | salon-redis | 6379 | Redis cache & queue |
| **api** | salon-api | 8000 (internal) | FastAPI backend |
| **worker** | salon-worker | - | Background job processor |
| **frontend** | salon-frontend | 3000 (internal) | Next.js 16 frontend |
| **nginx** | salon-nginx | **80** | Reverse proxy |

## Network Architecture

```
External Access (Port 80)
         ↓
    nginx (reverse proxy)
    ├── / → frontend:3000 (Next.js)
    ├── /api/ → api:8000 (FastAPI)
    └── /docs → api:8000 (API docs)
         ↓
Internal Network (salon_internal)
    ├── postgres:5432
    └── redis:6379
```

**Security**: PostgreSQL and Redis are NOT exposed externally, only accessible within Docker network.

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
POSTGRES_DB=salon_db
POSTGRES_USER=salon_user
POSTGRES_PASSWORD=your_secure_password_here

# Backend
SECRET_KEY=your_secret_key_here
ENVIRONMENT=production

# Frontend
NEXT_PUBLIC_API_URL=http://salon.local/api
```

### Default Values (Development)

If `.env` is not provided, these defaults are used:

```bash
POSTGRES_PASSWORD=change_me_123
SECRET_KEY=change_me_please
ENVIRONMENT=development
```

⚠️ **Never use default credentials in production!**

## Service Management

### Start Specific Services

```bash
# Start only database and redis
docker compose up -d postgres redis

# Start backend (api + worker)
docker compose up -d api worker

# Start frontend only
docker compose up -d frontend
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f frontend
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 frontend
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart frontend
docker compose restart api
```

### Rebuild After Code Changes

```bash
# Rebuild all services
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build frontend
docker compose up -d --build api
```

## Database Management

### Run Migrations

```bash
# Apply all pending migrations
docker compose exec api alembic upgrade head

# Rollback one migration
docker compose exec api alembic downgrade -1

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"
```

### Load Seed Data

```bash
# Load initial data (users, roles, etc.)
docker compose exec api python -m app.seeds.initial_data
```

### Database Backup

```bash
# Manual backup
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup.dump

# Restore from backup
docker compose down
docker compose up -d postgres
docker compose exec -T postgres pg_restore -U salon_user -d salon_db --clean < backup.dump
docker compose up -d
```

## Development Workflow

### Frontend Development

1. **Start in dev mode with hot reload:**
   ```bash
   docker compose -f compose.yaml -f compose.dev.yaml up -d frontend
   ```

2. **Make changes** to files in `frontend/` directory

3. **Changes auto-reload** - refresh browser to see updates

4. **View logs** for errors:
   ```bash
   docker compose logs -f frontend
   ```

### Backend Development

Backend runs in development mode by default with auto-reload:

```bash
# View API logs
docker compose logs -f api

# Restart API if needed
docker compose restart api
```

### Working with Dependencies

**Frontend:**
```bash
# Install new npm package
cd frontend
npm install <package-name>

# Rebuild container
docker compose up -d --build frontend
```

**Backend:**
```bash
# Update requirements.txt first, then:
docker compose up -d --build api worker
```

## Production Deployment

### Initial Setup

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd salon-os
   ```

2. **Create `.env` file** with secure credentials

3. **Start all services:**
   ```bash
   docker compose up -d
   ```

4. **Run migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. **Load initial data:**
   ```bash
   docker compose exec api python -m app.seeds.initial_data
   ```

6. **Access application:**
   - Frontend: http://salon.local or http://localhost
   - API Docs: http://salon.local/docs

### Health Checks

```bash
# Check all service status
docker compose ps

# Test nginx health
curl http://localhost/healthz

# Test API health
curl http://localhost/api/healthz
```

### Updating to New Version

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build

# Run new migrations
docker compose exec api alembic upgrade head
```

## Troubleshooting

### Frontend Won't Start

```bash
# Check logs
docker compose logs frontend

# Common fixes:
# 1. Rebuild with no cache
docker compose build --no-cache frontend
docker compose up -d frontend

# 2. Remove node_modules volume
docker compose down
docker volume prune
docker compose up -d --build
```

### API Connection Issues

```bash
# Check API health
docker compose exec api curl http://localhost:8000/healthz

# Check database connection
docker compose exec api python -c "from app.db.session import engine; print('DB OK' if engine else 'DB Fail')"

# Restart API
docker compose restart api
```

### Database Connection Failed

```bash
# Check postgres is running
docker compose ps postgres

# Check postgres logs
docker compose logs postgres

# Verify credentials in .env match compose.yaml
```

### Port Already in Use

```bash
# Find what's using port 80
lsof -i :80

# Stop conflicting service or change port in compose.yaml:
# nginx:
#   ports:
#     - "8080:80"  # Access via http://localhost:8080
```

### Nginx 502 Bad Gateway

```bash
# Check if frontend/api are running
docker compose ps

# Check nginx logs
docker compose logs nginx

# Restart nginx
docker compose restart nginx
```

## Performance Tuning

### Production Optimizations

1. **Enable Postgres connection pooling:**
   - Default: 100 max connections
   - Adjust `max_connections` in postgres config if needed

2. **Redis persistence:**
   - AOF (Append-Only File) enabled by default
   - Data persisted to `./salon-data/redis`

3. **Frontend optimizations:**
   - Production build is automatically optimized
   - Static assets cached by nginx

### Resource Limits

Add to `compose.yaml` if needed:

```yaml
services:
  frontend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

## Data Persistence

All data is stored in `./salon-data/`:

```
salon-data/
├── postgres/     # Database files
├── redis/        # Redis AOF files
├── backups/      # Nightly backups
└── logs/         # Application logs
```

**Backup this directory** for complete data recovery.

## Security Checklist

- [ ] Change default database password
- [ ] Change SECRET_KEY to random value
- [ ] Use HTTPS in production (add SSL to nginx)
- [ ] Enable firewall rules (allow only port 80/443)
- [ ] Regular database backups
- [ ] Keep Docker images updated
- [ ] Review nginx access logs regularly

## Monitoring

### Real-time Monitoring

```bash
# Resource usage
docker stats

# Disk usage
docker system df

# Network inspection
docker network inspect efs-salon-os_salon_internal
```

### Log Aggregation

Logs are available via Docker:

```bash
# Export all logs
docker compose logs --no-color > logs.txt

# JSON formatted nginx logs
docker compose exec nginx cat /var/log/nginx/access.log
```

## Common Commands Reference

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild and restart
docker compose up -d --build

# View logs
docker compose logs -f [service]

# Execute command in container
docker compose exec [service] [command]

# Clean up everything (⚠️ destroys data!)
docker compose down -v
```

## Support

- **Health Endpoints:**
  - Nginx: http://localhost/healthz
  - API: http://localhost/api/healthz

- **API Documentation:**
  - Swagger: http://localhost/docs
  - ReDoc: http://localhost/redoc

---

**Last Updated:** January 19, 2026
**Docker Compose Version:** 2.x
