# Admin Scripts - Quick Reference

## 📦 Database Backup

### Create Backup
```bash
# Simplest method (from host machine)
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_$(date +%Y%m%d_%H%M%S).dump

# Using Python script
docker compose exec api python -m app.scripts.backup_database
```

### Restore Backup
```bash
docker compose down
docker compose up -d postgres
docker compose exec postgres pg_restore -U salon_user -d salon_db --clean backup.dump
docker compose up -d
```

---

## 🗑️ Purge Transactional Data

### Quick Commands

```bash
# Dry run (preview what would be deleted)
docker compose exec api python -m app.scripts.purge_transactional_data --dry-run

# Interactive purge (with confirmation) - RECOMMENDED
docker compose exec api python -m app.scripts.purge_transactional_data --interactive

# Keep audit logs
docker compose exec api python -m app.scripts.purge_transactional_data --interactive --keep-audit-logs
```

### What Gets Deleted ❌
- Bills & invoices
- Bill items
- Payments
- Walk-ins
- Appointments
- Daily reconciliations
- Cash drawer records
- Day summaries
- Export logs
- Audit logs (optional)

### What Gets Preserved ✅
- Customers
- Users & Staff
- Services & Categories
- Inventory
- Settings

---

## 🚨 Safety Checklist

Before purging data:

- [ ] Create backup
- [ ] Test with `--dry-run`
- [ ] Verify backup file size
- [ ] Notify users of maintenance
- [ ] Use `--interactive` mode
- [ ] Keep terminal output

---

## 📚 Full Documentation

See detailed documentation in:
- `/docs/admin-scripts.md` - Complete guide
- `/backend/app/scripts/` - Script source code

---

## ⚡ Common Scenarios

### Scenario 1: Clear Test Data
```bash
# 1. Backup
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup.dump

# 2. Preview
docker compose exec api python -m app.scripts.purge_transactional_data --dry-run

# 3. Purge
docker compose exec api python -m app.scripts.purge_transactional_data --interactive
```

### Scenario 2: Monthly Archival
```bash
# 1. Archive old data
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > archive_$(date +%Y%m).dump

# 2. Export reports (via UI)

# 3. Purge old transactions
docker compose exec api python -m app.scripts.purge_transactional_data --interactive --keep-audit-logs
```

---

## 🆘 Emergency Recovery

If something goes wrong:

```bash
# 1. Stop app
docker compose down

# 2. Restore backup
docker compose up -d postgres
docker compose exec postgres pg_restore -U salon_user -d salon_db --clean backup.dump

# 3. Start app
docker compose up -d

# 4. Verify
docker compose exec postgres psql -U salon_user -d salon_db -c "SELECT COUNT(*) FROM bills;"
```

---

**⚠️ Remember**: Always backup before purging!

For detailed documentation, see `/docs/admin-scripts.md`
