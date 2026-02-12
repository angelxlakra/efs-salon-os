#!/bin/bash
# Script to restore a local database backup

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  Restore Database Backup${NC}"
echo -e "${GREEN}====================================${NC}"

# List available backups
echo -e "\n${YELLOW}Available backups:${NC}"
ls -lh backups/*.dump 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

if [ $# -eq 0 ]; then
    echo -e "\n${YELLOW}Usage:${NC}"
    echo "  $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 backups/dev_backup_20260204_123456.dump"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo -e "\n${YELLOW}⚠️  This will replace your current database with:${NC}"
echo "  $BACKUP_FILE"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Create safety backup of current state
echo -e "\n${GREEN}[1/5]${NC} Creating safety backup of current database..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > backups/pre_restore_$TIMESTAMP.dump 2>/dev/null || true
echo "✓ Safety backup: backups/pre_restore_$TIMESTAMP.dump"

# Stop services
echo -e "\n${GREEN}[2/5]${NC} Stopping services..."
docker compose stop
echo "✓ Services stopped"

# Start PostgreSQL
echo -e "\n${GREEN}[3/5]${NC} Starting PostgreSQL..."
docker compose up -d postgres
sleep 5
echo "✓ PostgreSQL ready"

# Drop and recreate
echo -e "\n${GREEN}[4/5]${NC} Dropping and recreating database..."
docker compose exec postgres psql -U salon_user -d postgres -c "DROP DATABASE IF EXISTS salon_db;" 2>&1 | grep -v "NOTICE" || true
docker compose exec postgres psql -U salon_user -d postgres -c "CREATE DATABASE salon_db OWNER salon_user;"
echo "✓ Database recreated"

# Restore backup
echo -e "\n${GREEN}[5/5]${NC} Restoring backup..."
docker compose exec -T postgres pg_restore -U salon_user -d salon_db --clean --if-exists < $BACKUP_FILE 2>&1 | grep -v "WARNING" | grep -v "NOTICE" || true
echo "✓ Backup restored"

# Start services
echo -e "\n${GREEN}Starting all services...${NC}"
docker compose up -d
sleep 3

echo -e "\n${GREEN}====================================${NC}"
echo -e "${GREEN}  ✓ Restore Complete!${NC}"
echo -e "${GREEN}====================================${NC}"

echo -e "\nDatabase statistics:"
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT
  'Bills' as table_name, COUNT(*) as count FROM bills
UNION ALL
SELECT 'Customers', COUNT(*) FROM customers
UNION ALL
SELECT 'Services', COUNT(*) FROM services;
" 2>/dev/null || echo "Could not fetch statistics"

echo -e "\n${GREEN}Done!${NC}"
