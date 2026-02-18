# Centralized Backups & Metrics Push

Nightly PostgreSQL backups and daily financial metrics pushed to S3-compatible cloud storage (Backblaze B2), enabling multi-branch monitoring from a single bucket.

---

## Architecture

```
Branch A (Local)                    Branch B (Local)
  worker ──┐                          worker ──┐
            │  22:00 IST: pg_dump + upload      │
            │  21:45 IST: metrics JSON push     │
            ▼                                   ▼
         ┌─────────────────────────────────────────┐
         │  Backblaze B2 Bucket: salon-backups     │
         │                                         │
         │  branch-andheri/                        │
         │    backups/branch-andheri_20260217.dump  │
         │    metrics/2026-02-17.json               │
         │  branch-bandra/                         │
         │    backups/branch-bandra_20260217.dump   │
         │    metrics/2026-02-17.json               │
         └─────────────────────────────────────────┘
```

Each branch runs independently. The worker container handles all backup jobs via APScheduler.

---

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `generate_daily_summary_job` | 21:45 IST daily | Generates DaySummary + pushes metrics JSON |
| `nightly_backup_job` | 22:00 IST daily | pg_dump → local file → cloud upload |
| `_weekly_cloud_cleanup` | Sunday 02:00 IST | Deletes cloud backups older than retention period |
| `catchup_missing_summaries` | On startup | Fills missing DaySummary records |
| `catchup_missing_metrics` | On startup | Pushes metrics for last 14 days if missing from cloud |

---

## Environment Variables

All are optional — without S3 credentials, backups remain local-only.

| Variable | Default | Description |
|----------|---------|-------------|
| `BRANCH_ID` | `default` | Unique identifier per branch (e.g., `branch-andheri`) |
| `BACKUP_RETENTION_DAYS` | `7` | Days to keep local `.dump` files |
| `BACKUP_S3_ENDPOINT` | *(none)* | S3-compatible endpoint URL |
| `BACKUP_S3_BUCKET` | *(none)* | Bucket name |
| `BACKUP_S3_ACCESS_KEY` | *(none)* | Access key / B2 Key ID |
| `BACKUP_S3_SECRET_KEY` | *(none)* | Secret key / B2 Application Key |
| `BACKUP_S3_REGION` | `us-west-004` | S3 region |
| `BACKUP_CLOUD_RETENTION_DAYS` | `90` | Days to keep cloud backups |

---

## Backblaze B2 Setup (One-Time, ~15 min)

1. Create a Backblaze B2 account at [backblaze.com](https://www.backblaze.com/cloud-storage)
2. Create a **private** bucket (e.g., `salon-backups`)
3. Under **App Keys**, create an Application Key scoped to that bucket
4. Note the **keyID** (access key) and **applicationKey** (secret key)
5. The endpoint URL follows the pattern: `https://s3.{region}.backblazeb2.com`

Add to each branch's `.env`:

```env
BRANCH_ID=branch-andheri
BACKUP_S3_ENDPOINT=https://s3.us-west-004.backblazeb2.com
BACKUP_S3_BUCKET=salon-backups
BACKUP_S3_ACCESS_KEY=004xxxxxxxxxxxx
BACKUP_S3_SECRET_KEY=K004xxxxxxxxxxxxxxxxxxxxxxxxxxxx
BACKUP_S3_REGION=us-west-004
```

Then rebuild: `docker compose up --build -d`

---

## Metrics JSON Schema

Pushed to `{branch_id}/metrics/{YYYY-MM-DD}.json` after each daily summary generation.

```json
{
  "schema_version": 1,
  "branch_id": "branch-andheri",
  "branch_name": "Salon Name",
  "summary_date": "2026-02-16",
  "generated_at": "2026-02-16T21:45:00+05:30",
  "is_final": true,
  "currency": "INR",
  "total_bills": 42,
  "refund_count": 1,
  "gross_revenue": 12500000,
  "discount_amount": 500000,
  "refund_amount": 200000,
  "net_revenue": 11800000,
  "cgst_collected": 1062000,
  "sgst_collected": 1062000,
  "total_tax": 2124000,
  "cash_collected": 7000000,
  "digital_collected": 4800000,
  "actual_service_cogs": 2000000,
  "actual_product_cogs": 1500000,
  "total_cogs": 3500000,
  "total_expenses": 1500000,
  "gross_profit": 8300000,
  "net_profit": 6800000,
  "total_tips": 350000
}
```

All monetary values are in **paise** (1/100 of INR). Divide by 100 for rupees.

---

## Restore from Cloud Backup

1. Download the `.dump` file from B2 (via web UI, B2 CLI, or any S3 client):

   ```bash
   # Using AWS CLI with B2 endpoint
   aws s3 cp \
     s3://salon-backups/branch-andheri/backups/branch-andheri_20260217_220005.dump \
     ./restore.dump \
     --endpoint-url https://s3.us-west-004.backblazeb2.com
   ```

2. Stop the API and worker containers:

   ```bash
   docker compose stop api worker
   ```

3. Restore into the database:

   ```bash
   docker compose exec postgres pg_restore \
     -U salon_user -d salon_db --clean --if-exists \
     /path/to/restore.dump
   ```

   Or copy the file into the container first:

   ```bash
   docker cp restore.dump salon-postgres:/tmp/restore.dump
   docker compose exec postgres pg_restore \
     -U salon_user -d salon_db --clean --if-exists \
     /tmp/restore.dump
   ```

4. Run migrations to ensure schema is up to date:

   ```bash
   docker compose exec api alembic upgrade head
   ```

5. Restart services:

   ```bash
   docker compose up -d
   ```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/backup_service.py` | BackupService: upload, metrics push, cloud cleanup |
| `backend/app/jobs/scheduled.py` | pg_dump job, metrics catchup, local cleanup |
| `backend/app/jobs/utils.py` | `parse_database_url()` helper |
| `backend/app/worker.py` | APScheduler wiring, startup catchup |
| `backend/app/config.py` | Settings for branch_id, S3 credentials |

---

## Verification Checklist

- [ ] Local backup: Check `/backups/` volume for `.dump` files after 22:00 IST
- [ ] Cloud upload: Check B2 bucket for `{branch_id}/backups/` objects
- [ ] Metrics push: Check B2 for `{branch_id}/metrics/*.json` after 21:45 IST
- [ ] Catchup: Restart worker, check logs for metrics catchup output
- [ ] Retention: After 7+ days, verify old local files are cleaned up
- [ ] Cloud retention: After 90+ days, verify Sunday cleanup removes old cloud backups
- [ ] Restore: Download a `.dump` from B2 and restore to a test database
