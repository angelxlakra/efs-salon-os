# SalonOS Administrative Scripts

This document describes the administrative scripts available for managing the SalonOS database and data.

## Table of Contents

- [Database Backup](#database-backup)
- [Purge Transactional Data](#purge-transactional-data)
- [Common Use Cases](#common-use-cases)
- [Safety Guidelines](#safety-guidelines)

---

## Database Backup

### Overview

Creates timestamped backups of the entire SalonOS database in PostgreSQL custom format (compressed).

### Quick Commands

```bash
# Create backup (simplest method - from host)
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_$(date +%Y%m%d_%H%M%S).dump

# Using Python script
docker compose exec api python -m app.scripts.backup_database

# List existing backups
docker compose exec api python -m app.scripts.backup_database --list

# Custom output path
docker compose exec api python -m app.scripts.backup_database --output /backups/custom_name.dump
```

### Restore from Backup

```bash
# 1. Stop the application
docker compose down

# 2. Start only PostgreSQL
docker compose up -d postgres

# 3. Restore from backup
docker compose exec postgres pg_restore -U salon_user \
  -d salon_db --clean backup_20260125_143000.dump

# 4. Start application
docker compose up -d
```

### Automated Backups

Create a cron job on the host machine:

```bash
# Edit crontab
crontab -e

# Add entry for nightly backup at 11:30 PM
30 23 * * * cd /path/to/salon-os && docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > /backups/salon_backup_$(date +\%Y\%m\%d_\%H\%M\%S).dump 2>&1 | logger -t salon-backup
```

### Backup Best Practices

1. **Frequency**:
   - Daily backups for production
   - Before major operations (upgrades, purges)
   - After significant data entry

2. **Retention**:
   - Keep 7 daily backups
   - Keep 4 weekly backups (every Sunday)
   - Keep 12 monthly backups (first of month)

3. **Storage**:
   - Store on different physical drive
   - Consider cloud storage for critical backups
   - Test restore process monthly

---

## Purge Transactional Data

### Overview

Removes all POS transactional data while preserving master data (customers, staff, services, settings).

**⚠️ WARNING**: This is a destructive operation. Always backup first!

### What Gets Deleted

- ❌ Bills (invoices)
- ❌ Bill items
- ❌ Payments
- ❌ Walk-ins
- ❌ Appointments
- ❌ Daily reconciliations
- ❌ Cash drawer records
- ❌ Day summaries
- ❌ Export logs
- ❌ Audit logs (optional - can be preserved)

### What Gets Preserved

- ✅ Customers
- ✅ Users & Staff
- ✅ Services & Categories
- ✅ Service Addons
- ✅ Inventory (SKUs, Suppliers, Stock)
- ✅ Salon Settings
- ✅ Roles

### Commands

```bash
# Dry run (see what would be deleted without actually deleting)
docker compose exec api python -m app.scripts.purge_transactional_data --dry-run

# Interactive mode (with confirmation prompt) - RECOMMENDED
docker compose exec api python -m app.scripts.purge_transactional_data --interactive

# Keep audit logs (delete everything except audit trail)
docker compose exec api python -m app.scripts.purge_transactional_data --interactive --keep-audit-logs

# Non-interactive (skip confirmation) - DANGEROUS
docker compose exec api python -m app.scripts.purge_transactional_data --yes
```

### Step-by-Step Purge Process

#### 1. Create Backup

```bash
# Create backup BEFORE purging
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_before_purge_$(date +%Y%m%d_%H%M%S).dump
```

#### 2. Test with Dry Run

```bash
# See what would be deleted
docker compose exec api python -m app.scripts.purge_transactional_data --dry-run
```

Output example:
```
Scanning database...

⚠️  WARNING: DESTRUCTIVE OPERATION

The following records will be PERMANENTLY DELETED:

  • payments: 1,234 records
  • bill_items: 2,456 records
  • bills: 567 records
  • walkins: 345 records
  • appointments: 123 records
  • daily_reconciliations: 45 records
  • cash_drawers: 12 records
  • day_summaries: 45 records
  • export_logs: 5 records
  • audit_logs: 3,456 records
  • events: 4,567 records

  TOTAL: 13,855 records will be deleted
```

#### 3. Execute Purge

```bash
# Run with confirmation prompt
docker compose exec api python -m app.scripts.purge_transactional_data --interactive
```

You'll be prompted to type `DELETE ALL DATA` to confirm.

#### 4. Verify Results

```bash
# Check database
docker compose exec postgres psql -U salon_user -d salon_db

# Check bills table
SELECT COUNT(*) FROM bills;  -- Should be 0

# Check customers (should still have data)
SELECT COUNT(*) FROM customers;

# Check services (should still have data)
SELECT COUNT(*) FROM services;
```

### Script Options

| Option | Description |
|--------|-------------|
| `--interactive` | Prompt for confirmation before deleting (recommended) |
| `--dry-run` | Show what would be deleted without actually deleting |
| `--keep-audit-logs` | Preserve audit logs and events |
| `--yes` | Skip confirmation (dangerous - use with caution) |

---

## Common Use Cases

### Use Case 1: Clear Test Data After Development

**Scenario**: You've been testing the system and want to start fresh with clean data.

```bash
# 1. Backup first
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_before_test_purge.dump

# 2. Purge transactional data
docker compose exec api python -m app.scripts.purge_transactional_data --interactive

# 3. Verify master data is intact
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT COUNT(*) FROM services;"
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT COUNT(*) FROM users;"
```

### Use Case 2: End of Trial Period

**Scenario**: Trial period is over, keep system setup but remove all trial transactions.

```bash
# 1. Create backup of trial data for reference
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > trial_data_archive.dump

# 2. Purge transactional data, keep audit logs for compliance
docker compose exec api python -m app.scripts.purge_transactional_data \
  --interactive --keep-audit-logs

# 3. Update salon settings if needed
# (e.g., change salon name from "Test Salon" to actual name)
```

### Use Case 3: Annual Data Archival

**Scenario**: Archive old year's data and start fresh for new financial year.

```bash
# 1. Create full backup of previous year
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > archive_FY2025.dump

# 2. Export reports for the year (via API or UI)
# Download:
# - Annual revenue report
# - Tax reports
# - Customer history

# 3. Purge transactional data
docker compose exec api python -m app.scripts.purge_transactional_data --interactive

# 4. Update year-specific settings
# - Reset invoice counter (if applicable)
# - Update tax rates (if changed)
```

### Use Case 4: Migrate to New System

**Scenario**: Moving from test environment to production.

```bash
# On TEST system:
# 1. Export current configuration
docker compose exec postgres pg_dump -U salon_user \
  -t services -t service_categories -t users -t roles \
  salon_db > config_export.sql

# On PRODUCTION system:
# 2. Import configuration
docker compose exec postgres psql -U salon_user -d salon_db < config_export.sql

# 3. Update settings
# - Change salon name
# - Update GSTIN
# - Configure for production
```

---

## Safety Guidelines

### Before Running Scripts

1. **Always Backup First**
   ```bash
   docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup.dump
   ```

2. **Test in Development First**
   - Never run purge scripts on production without testing
   - Use `--dry-run` to preview changes

3. **Verify Backup is Valid**
   ```bash
   # Check backup file exists and has size
   ls -lh backup.dump

   # Test restore in separate container (optional but recommended)
   ```

4. **Notify Users**
   - Schedule maintenance window
   - Inform staff of downtime
   - Post notice in salon

### During Script Execution

1. **Monitor Progress**
   - Scripts show real-time progress
   - Watch for errors

2. **Don't Interrupt**
   - Let scripts complete
   - If interrupted, check database state

3. **Keep Terminal Output**
   - Save output for reference
   - Useful for troubleshooting

### After Script Execution

1. **Verify Results**
   ```bash
   # Check record counts
   docker compose exec postgres psql -U salon_user -d salon_db

   \dt  -- List tables
   SELECT COUNT(*) FROM bills;  -- Should be 0 after purge
   SELECT COUNT(*) FROM customers;  -- Should have data
   ```

2. **Test Application**
   - Login to application
   - Create test transaction
   - Verify functionality

3. **Document Changes**
   - Record what was deleted
   - Save output logs
   - Update runbook

### Recovery Plan

If something goes wrong:

```bash
# 1. Stop application immediately
docker compose down

# 2. Start only PostgreSQL
docker compose up -d postgres

# 3. Restore from backup
docker compose exec postgres pg_restore -U salon_user \
  -d salon_db --clean backup.dump

# 4. Verify restoration
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT COUNT(*) FROM bills;"

# 5. Start application
docker compose up -d

# 6. Test thoroughly
```

---

## Troubleshooting

### Error: "relation does not exist"

**Cause**: Table doesn't exist in database

**Solution**:
```bash
# Run migrations
docker compose exec api alembic upgrade head
```

### Error: "permission denied"

**Cause**: Insufficient PostgreSQL permissions

**Solution**:
```bash
# Check database user
docker compose exec postgres psql -U salon_user -d salon_db -c "\du"

# Verify connection
docker compose exec api python -c "from app.database import engine; print(engine.connect())"
```

### Error: "database is being accessed by other users"

**Cause**: Active connections to database

**Solution**:
```bash
# Terminate active connections
docker compose exec postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='salon_db' AND pid <> pg_backend_pid();"
```

### Script Hangs or Freezes

**Cause**: Large dataset, foreign key locks

**Solution**:
1. Wait for completion (large datasets take time)
2. Check container logs: `docker compose logs -f api`
3. If truly frozen, Ctrl+C and check database state

### Backup File is Too Large

**Cause**: Lots of transactional data

**Solution**:
```bash
# Use compression
docker compose exec postgres pg_dump -U salon_user -Fc salon_db | gzip > backup.dump.gz

# Or split into smaller files
docker compose exec postgres pg_dump -U salon_user -Fc salon_db | split -b 100M - backup.dump.
```

---

## Script Reference

### purge_transactional_data.py

**Location**: `backend/app/scripts/purge_transactional_data.py`

**Purpose**: Remove all POS transactional data

**Options**:
- `--interactive` - Require confirmation (safe)
- `--dry-run` - Preview without deleting
- `--keep-audit-logs` - Preserve audit trail
- `--yes` - Skip confirmation (dangerous)

**Exit Codes**:
- `0` - Success
- `1` - Error or cancelled by user

### backup_database.py

**Location**: `backend/app/scripts/backup_database.py`

**Purpose**: Create database backups

**Options**:
- `--output`, `-o` - Custom output path
- `--list`, `-l` - List existing backups

**Exit Codes**:
- `0` - Success
- `1` - Error

---

## Best Practices Summary

✅ **DO**:
- Always backup before purging
- Test with `--dry-run` first
- Use `--interactive` mode for safety
- Schedule regular automated backups
- Test restore process monthly
- Document all operations
- Keep multiple backup versions

❌ **DON'T**:
- Run purge without backup
- Use `--yes` flag unless automated
- Delete audit logs unless necessary
- Run on production without testing
- Interrupt running scripts
- Delete backup files immediately after restore
- Trust single backup - keep multiple versions

---

**Version**: 1.0
**Last Updated**: January 27, 2026
**Status**: Production Ready ✅
