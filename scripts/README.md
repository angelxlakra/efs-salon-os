# Production Database Migration Scripts

## Overview

These scripts help you safely pull production data to your local dev environment for testing.

## Scripts

1. **`pull-prod-data.sh`** - Pull production DB and replace local dev DB
2. **`sanitize-pii.sh`** - Anonymize customer PII after import
3. **`restore-dev-backup.sh`** - Restore a previous local backup

---

## Quick Start

### First Time Setup

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Configure production server details
nano scripts/pull-prod-data.sh
# Edit these lines:
#   PROD_HOST="your-production-server.com"
#   PROD_USER="your-ssh-user"
#   PROD_PATH="/path/to/salon-os"
```

### Pull Production Data

```bash
# Run the automated script
./scripts/pull-prod-data.sh
```

This will:
1. ✅ Backup your local dev database
2. ✅ Create production database dump
3. ✅ Download dump to local machine
4. ✅ Replace local database with production data
5. ✅ Run pending migrations
6. ✅ Start all services

### Sanitize PII (Recommended)

After pulling production data, sanitize sensitive information:

```bash
# Anonymize customer data
./scripts/sanitize-pii.sh
```

This will:
- ✅ Backup database before sanitization
- ✅ Anonymize customer names, phones, emails
- ✅ Update appointments, walk-ins, bills
- ✅ Preserve data structure for testing

---

## Manual Process (If Scripts Fail)

### Step 1: Configure Production Server Access

Edit your SSH config for easier access:

```bash
# Add to ~/.ssh/config
Host salon-prod
    HostName your-production-server.com
    User your-ssh-user
    IdentityFile ~/.ssh/id_rsa
    Port 22
```

### Step 2: Create Production Dump

```bash
# SSH into production
ssh salon-prod

# Navigate to salon-os directory
cd /path/to/salon-os

# Create dump
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > /tmp/salon_prod.dump

# Exit
exit
```

### Step 3: Download Dump

```bash
# Download to local
scp salon-prod:/tmp/salon_prod.dump backups/
```

### Step 4: Replace Local Database

```bash
# Stop services
docker compose down

# Start PostgreSQL
docker compose up -d postgres
sleep 5

# Drop and recreate database
docker compose exec postgres psql -U salon_user -d postgres -c "DROP DATABASE IF EXISTS salon_db;"
docker compose exec postgres psql -U salon_user -d postgres -c "CREATE DATABASE salon_db OWNER salon_user;"

# Restore production data
docker compose exec -T postgres pg_restore -U salon_user -d salon_db --clean < backups/salon_prod.dump

# Run migrations
docker compose up -d api
sleep 5
docker compose exec api uv run alembic upgrade head

# Start all services
docker compose up -d
```

---

## Troubleshooting

### "Permission denied" when running scripts

```bash
chmod +x scripts/*.sh
```

### "Connection refused" SSH error

Check your production server:
- Is SSH running?
- Is the hostname/IP correct?
- Do you have SSH key access?

```bash
# Test SSH connection
ssh -v your-ssh-user@your-production-server.com
```

### "pg_dump: error: connection to server failed"

Check if PostgreSQL is running in production:

```bash
ssh salon-prod
docker compose ps postgres
docker compose logs postgres
```

### "database does not exist" error

The database might have a different name in production:

```bash
# Check database name
ssh salon-prod
docker compose exec postgres psql -U salon_user -l
```

### Restore fails with "input file appears to be a text format"

Try using psql instead:

```bash
docker compose exec -T postgres psql -U salon_user -d salon_db < backups/prod_dump.dump
```

### Migration errors after restore

Your dev code might have migrations that production doesn't:

```bash
# Check migration status
docker compose exec api uv run alembic current

# Downgrade to match production
docker compose exec api uv run alembic downgrade <revision>

# Or force upgrade
docker compose exec api uv run alembic upgrade head
```

---

## Best Practices

### 1. **Always Backup Before Pulling**

The script does this automatically, but if doing manually:

```bash
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > backups/dev_backup_$(date +%Y%m%d).dump
```

### 2. **Sanitize PII for Local Testing**

Never commit production data with real customer information:

```bash
./scripts/sanitize-pii.sh
```

### 3. **Keep Backups Organized**

```bash
# Create dated subdirectories
mkdir -p backups/2026-02
mv backups/*.dump backups/2026-02/
```

### 4. **Clean Up Old Backups**

```bash
# Delete backups older than 30 days
find backups/ -name "*.dump" -mtime +30 -delete
```

### 5. **Add backups/ to .gitignore**

```bash
echo "backups/" >> .gitignore
```

---

## Restoring a Backup

If you need to restore a previous local backup:

```bash
# Stop services
docker compose down

# Start PostgreSQL
docker compose up -d postgres
sleep 5

# Drop and recreate
docker compose exec postgres psql -U salon_user -d postgres -c "DROP DATABASE IF EXISTS salon_db;"
docker compose exec postgres psql -U salon_user -d postgres -c "CREATE DATABASE salon_db OWNER salon_user;"

# Restore backup
docker compose exec -T postgres pg_restore -U salon_user -d salon_db < backups/dev_backup_20260204.dump

# Start services
docker compose up -d
```

---

## Scheduled Pulls (Optional)

Set up a cron job to automatically pull production data weekly:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 cd /Users/angelxlakra/dev/efs-salon-os && ./scripts/pull-prod-data.sh >> logs/prod-pull.log 2>&1
```

---

## Security Considerations

### SSH Key Authentication

Use SSH keys instead of passwords:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy to production server
ssh-copy-id your-ssh-user@your-production-server.com
```

### Database Credentials

Never commit database credentials to git:

```bash
# Ensure .env is in .gitignore
grep "^\.env$" .gitignore || echo ".env" >> .gitignore
```

### Production Data

- ✅ Store dumps in `backups/` (gitignored)
- ✅ Run sanitization script after import
- ✅ Never commit production dumps
- ✅ Delete old dumps regularly
- ✅ Use encrypted backups for sensitive data

### Network Security

For extra security, use SSH tunneling:

```bash
# Create SSH tunnel to production DB
ssh -L 5433:localhost:5432 salon-prod

# Then dump through tunnel (in another terminal)
pg_dump -h localhost -p 5433 -U salon_user -Fc salon_db > backups/prod_dump.dump
```

---

## Advanced Usage

### Selective Data Import

Import only specific tables:

```bash
# Dump specific tables
ssh salon-prod "docker compose exec -T postgres pg_dump -U salon_user -t bills -t bill_items salon_db" > backups/bills_only.dump

# Restore
docker compose exec -T postgres psql -U salon_user -d salon_db < backups/bills_only.dump
```

### Compress Dumps

Save disk space with compression:

```bash
# Create compressed dump
ssh salon-prod "docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db" | gzip > backups/prod_dump.dump.gz

# Restore
gunzip -c backups/prod_dump.dump.gz | docker compose exec -T postgres pg_restore -U salon_user -d salon_db
```

### Parallel Restore

Speed up large restores:

```bash
docker compose exec -T postgres pg_restore -U salon_user -d salon_db -j 4 < backups/prod_dump.dump
```

---

## Quick Reference

```bash
# Pull production data
./scripts/pull-prod-data.sh

# Sanitize PII
./scripts/sanitize-pii.sh

# Verify data
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT COUNT(*) FROM bills;"

# Check logs
docker compose logs -f api

# Restart services
docker compose restart

# Access database shell
docker compose exec postgres psql -U salon_user -d salon_db
```

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Docker logs: `docker compose logs`
3. Verify SSH access: `ssh -v salon-prod`
4. Check disk space: `df -h`
5. Verify PostgreSQL: `docker compose exec postgres psql -U salon_user -l`

---

**Last Updated**: 2026-02-04
**Version**: 1.0
