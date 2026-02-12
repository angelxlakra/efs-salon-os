# Quick Start: Pull Production Data to Dev

## 🚀 TL;DR (5 Minutes)

```bash
# 1. Configure production server (one-time)
nano scripts/pull-prod-data.sh
# Edit: PROD_HOST, PROD_USER, PROD_PATH

# 2. Pull production data
./scripts/pull-prod-data.sh

# 3. Sanitize PII (recommended)
./scripts/sanitize-pii.sh

# Done! Your dev database now has production data ✓
```

---

## 📝 First Time Setup (10 minutes)

### Step 1: Configure Production Access

Edit the pull script with your production server details:

```bash
nano scripts/pull-prod-data.sh
```

Change these lines:
```bash
PROD_HOST="your-production-server.com"  # Your actual production hostname/IP
PROD_USER="your-ssh-user"               # Your SSH username
PROD_PATH="/path/to/salon-os"          # Where salon-os is installed
```

### Step 2: Test SSH Connection

```bash
# Test if you can SSH into production
ssh your-ssh-user@your-production-server.com

# If successful, you'll see the production terminal
# Type 'exit' to return to local

# If it fails, you need to:
# - Set up SSH key authentication
# - Check firewall/security group rules
# - Verify hostname/IP is correct
```

### Step 3: Set Up SSH Key (If Needed)

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy to production server
ssh-copy-id your-ssh-user@your-production-server.com

# Test again
ssh your-ssh-user@your-production-server.com
```

---

## 🔄 Regular Usage (2 minutes)

### Pull Latest Production Data

```bash
cd /Users/angelxlakra/dev/efs-salon-os
./scripts/pull-prod-data.sh
```

**What it does:**
1. ✅ Backs up your current dev database
2. ✅ Creates dump from production database
3. ✅ Downloads dump to local machine
4. ✅ Replaces local dev database
5. ✅ Runs any pending migrations
6. ✅ Starts all services
7. ✅ Shows you statistics

**Time:** ~2-5 minutes depending on database size

### Sanitize Customer Data (Recommended)

```bash
./scripts/sanitize-pii.sh
```

**What it anonymizes:**
- Customer names → "Customer XXXX"
- Phone numbers → Random 10-digit numbers
- Email addresses → test@local addresses

**Why?** So you don't accidentally use real customer data in testing.

---

## 🛟 Common Scenarios

### Scenario 1: "I messed up my dev database"

```bash
# Restore from today's backup
./scripts/restore-backup.sh backups/dev_backup_20260204_143022.dump

# Or pull fresh from production
./scripts/pull-prod-data.sh
```

### Scenario 2: "I want to test with real data but keep PII"

```bash
# Just pull without sanitizing
./scripts/pull-prod-data.sh
# Skip the sanitize step
```

**⚠️ Warning:** Be careful not to send test emails/SMS to real customers!

### Scenario 3: "I need data from last week's production"

```bash
# SSH to production and create historical dump
ssh salon-prod
cd /path/to/salon-os

# Restore production backup from last week first
docker compose exec -T postgres pg_restore -U salon_user -d salon_db < /path/to/old/backup.dump

# Then dump it
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > /tmp/historical.dump

# Download to local
exit
scp salon-prod:/tmp/historical.dump backups/

# Restore locally
./scripts/restore-backup.sh backups/historical.dump
```

### Scenario 4: "Pull failed halfway through"

```bash
# Check what went wrong
docker compose logs postgres

# Your original dev data is backed up in backups/
# Restore it:
ls -lh backups/dev_backup_*.dump  # Find the latest
./scripts/restore-backup.sh backups/dev_backup_20260204_120000.dump
```

---

## 📊 Verify Data After Pull

### Quick Check

```bash
# Access PostgreSQL
docker compose exec postgres psql -U salon_user -d salon_db

# Run these queries:
SELECT COUNT(*) FROM bills;
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM staff;

# Check latest bills
SELECT invoice_number, customer_name, rounded_total
FROM bills
ORDER BY created_at DESC
LIMIT 10;

# Exit
\q
```

### Full Verification

```bash
# Check all table counts
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT
  schemaname,
  tablename,
  n_tup_ins as rows_inserted,
  n_tup_upd as rows_updated,
  n_tup_del as rows_deleted
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"
```

---

## 🔧 Troubleshooting

### "Permission denied" when running scripts

```bash
chmod +x scripts/*.sh
```

### "Cannot connect to production server"

```bash
# Test SSH manually
ssh -v your-ssh-user@your-production-server.com

# Check if you can ping the server
ping your-production-server.com

# Verify SSH port is open
nc -zv your-production-server.com 22
```

### "pg_dump: command not found" on production

PostgreSQL might not be in Docker:

```bash
# Check if PostgreSQL is running natively
ssh salon-prod "pg_dump --version"

# If yes, modify the script to use native pg_dump instead of docker exec
```

### "Database restoration warnings"

These are usually safe to ignore:
- `WARNING: errors ignored on restore`
- `NOTICE: extension "uuid-ossp" already exists`

These are NOT safe:
- `ERROR: relation does not exist`
- `FATAL: database does not exist`

### "Migration fails after restore"

```bash
# Check current migration state
docker compose exec api uv run alembic current

# See pending migrations
docker compose exec api uv run alembic heads

# Force upgrade (if you're sure)
docker compose exec api uv run alembic upgrade head

# Or downgrade to production version first
docker compose exec api uv run alembic downgrade <revision>
```

---

## 📋 Checklist

Before running for the first time:
- [ ] Can SSH into production server
- [ ] Know where salon-os is installed on production
- [ ] Edited scripts/pull-prod-data.sh with correct details
- [ ] Made scripts executable (`chmod +x scripts/*.sh`)
- [ ] `backups/` is in .gitignore (already done ✓)

After pulling production data:
- [ ] Verify services are running (`docker compose ps`)
- [ ] Check data counts match expectations
- [ ] Run sanitize-pii.sh if testing with real data
- [ ] Test login with production credentials
- [ ] Verify recent bills/appointments load

---

## 🎯 Pro Tips

### 1. Create SSH Config Alias

Add to `~/.ssh/config`:

```
Host salon-prod
    HostName your-production-server.com
    User your-ssh-user
    IdentityFile ~/.ssh/id_rsa
    Port 22
```

Then you can just: `ssh salon-prod`

### 2. Schedule Weekly Pulls

```bash
# Edit crontab
crontab -e

# Run every Sunday at 2 AM
0 2 * * 0 cd /Users/angelxlakra/dev/efs-salon-os && ./scripts/pull-prod-data.sh >> logs/prod-pull.log 2>&1
```

### 3. Keep Backups Organized

```bash
# Archive old backups monthly
mkdir -p backups/archive/2026-02
mv backups/*_202602*.dump backups/archive/2026-02/
```

### 4. Compare Data Sizes

```bash
# Before pull
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT pg_size_pretty(pg_database_size('salon_db'));"

# After pull (should be similar to production)
```

### 5. Test Multi-Staff Features

Since you just implemented multi-staff contributions:

```bash
# After pulling production data, check if any services have templates
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT s.name, COUNT(sst.id) as template_count
FROM services s
LEFT JOIN service_staff_templates sst ON sst.service_id = s.id
GROUP BY s.id, s.name
HAVING COUNT(sst.id) > 0;
"
```

---

## 📚 Related Documentation

- **Detailed Guide**: `scripts/README.md`
- **Script Configurations**: `scripts/prod-config.example`
- **Database Docs**: `docs/spec-02-database-schema.md`

---

## ⚡ Quick Commands Reference

```bash
# Pull production data
./scripts/pull-prod-data.sh

# Sanitize PII
./scripts/sanitize-pii.sh

# Restore a backup
./scripts/restore-backup.sh backups/filename.dump

# List backups
ls -lh backups/

# Check database size
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT pg_size_pretty(pg_database_size('salon_db'));"

# Verify services
docker compose ps

# Check logs
docker compose logs -f api

# Access database
docker compose exec postgres psql -U salon_user -d salon_db

# Restart everything
docker compose restart
```

---

**Last Updated**: 2026-02-04
**Status**: Production Ready ✅

🚀 **You're ready to go!** Run `./scripts/pull-prod-data.sh` to get started.
