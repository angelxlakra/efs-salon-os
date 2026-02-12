#!/bin/bash
# Script to pull production database and replace local dev database

set -e  # Exit on error

# Configuration
PROD_HOST="your-production-server.com"
PROD_USER="your-ssh-user"
PROD_PATH="/path/to/salon-os"
LOCAL_BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  Production DB → Dev DB Migration${NC}"
echo -e "${GREEN}====================================${NC}"

# Confirmation
echo -e "${YELLOW}⚠️  WARNING: This will replace your local dev database with production data!${NC}"
read -p "Are you sure you want to continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Create local backup
echo -e "\n${GREEN}[1/8]${NC} Backing up local dev database..."
mkdir -p $LOCAL_BACKUP_DIR
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > $LOCAL_BACKUP_DIR/dev_backup_$TIMESTAMP.dump
echo "✓ Local backup saved: $LOCAL_BACKUP_DIR/dev_backup_$TIMESTAMP.dump"

# Step 2: Create production dump
echo -e "\n${GREEN}[2/8]${NC} Creating production database dump..."
ssh $PROD_USER@$PROD_HOST "cd $PROD_PATH && docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db" > $LOCAL_BACKUP_DIR/prod_dump_$TIMESTAMP.dump
echo "✓ Production dump created and downloaded"

# Step 3: Stop local services
echo -e "\n${GREEN}[3/8]${NC} Stopping local services..."
docker compose stop
echo "✓ Services stopped"

# Step 4: Start PostgreSQL
echo -e "\n${GREEN}[4/8]${NC} Starting PostgreSQL..."
docker compose up -d postgres
sleep 5
echo "✓ PostgreSQL ready"

# Step 5: Drop and recreate database
echo -e "\n${GREEN}[5/8]${NC} Dropping and recreating local database..."
docker compose exec postgres psql -U salon_user -d postgres -c "DROP DATABASE IF EXISTS salon_db;" 2>&1 | grep -v "NOTICE" || true
docker compose exec postgres psql -U salon_user -d postgres -c "CREATE DATABASE salon_db OWNER salon_user;"
echo "✓ Database recreated"

# Step 6: Restore production data
echo -e "\n${GREEN}[6/8]${NC} Restoring production data..."
docker compose exec -T postgres pg_restore -U salon_user -d salon_db --clean --if-exists < $LOCAL_BACKUP_DIR/prod_dump_$TIMESTAMP.dump 2>&1 | grep -v "WARNING" | grep -v "NOTICE" || true
echo "✓ Production data restored"

# Step 7: Run migrations
echo -e "\n${GREEN}[7/8]${NC} Running database migrations..."
docker compose up -d api
sleep 5
docker compose exec api uv run alembic upgrade head
echo "✓ Migrations complete"

# Step 8: Start all services
echo -e "\n${GREEN}[8/8]${NC} Starting all services..."
docker compose up -d
sleep 3
echo "✓ All services running"

# Verify
echo -e "\n${GREEN}====================================${NC}"
echo -e "${GREEN}  ✓ Migration Complete!${NC}"
echo -e "${GREEN}====================================${NC}"

echo -e "\nDatabase statistics:"
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT
  'Bills' as table_name, COUNT(*) as count FROM bills
UNION ALL
SELECT 'Customers', COUNT(*) FROM customers
UNION ALL
SELECT 'Services', COUNT(*) FROM services
UNION ALL
SELECT 'Staff', COUNT(*) FROM staff
UNION ALL
SELECT 'Appointments', COUNT(*) FROM appointments;
" 2>/dev/null || echo "Could not fetch statistics"

echo -e "\n${YELLOW}Backups saved:${NC}"
echo "  - Dev backup: $LOCAL_BACKUP_DIR/dev_backup_$TIMESTAMP.dump"
echo "  - Prod dump:  $LOCAL_BACKUP_DIR/prod_dump_$TIMESTAMP.dump"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. Access frontend: http://localhost:3000"
echo "  2. Check logs: docker compose logs -f api"
echo "  3. Optional: Run sanitization script to anonymize PII"

echo -e "\n${GREEN}Done!${NC}"
