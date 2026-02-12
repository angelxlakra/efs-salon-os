#!/bin/bash
# Script to sanitize PII (Personally Identifiable Information) in local dev database

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  PII Sanitization Script${NC}"
echo -e "${GREEN}====================================${NC}"

echo -e "${YELLOW}⚠️  This will anonymize all customer data in your LOCAL database.${NC}"
echo -e "${YELLOW}   - Customer names → 'Customer XXXX'${NC}"
echo -e "${YELLOW}   - Phone numbers → Random 10-digit numbers${NC}"
echo -e "${YELLOW}   - Emails → test@local addresses${NC}"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo -e "\n${GREEN}[1/5]${NC} Creating backup before sanitization..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > backups/pre_sanitize_$TIMESTAMP.dump
echo "✓ Backup saved: backups/pre_sanitize_$TIMESTAMP.dump"

echo -e "\n${GREEN}[2/5]${NC} Anonymizing customer records..."
docker compose exec postgres psql -U salon_user -d salon_db <<EOF
UPDATE customers
SET
  name = 'Customer ' || SUBSTRING(id, 1, 8),
  phone = '98765' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0'),
  email = CASE WHEN email IS NOT NULL THEN 'customer' || SUBSTRING(id, 1, 8) || '@test.local' ELSE NULL END;
EOF
echo "✓ Customers anonymized"

echo -e "\n${GREEN}[3/5]${NC} Anonymizing appointment data..."
docker compose exec postgres psql -U salon_user -d salon_db <<EOF
UPDATE appointments
SET
  customer_name = 'Customer ' || SUBSTRING(id, 1, 8),
  customer_phone = CASE WHEN customer_phone IS NOT NULL THEN '98765' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0') ELSE NULL END;
EOF
echo "✓ Appointments anonymized"

echo -e "\n${GREEN}[4/5]${NC} Anonymizing walk-in data..."
docker compose exec postgres psql -U salon_user -d salon_db <<EOF
UPDATE walkins
SET
  customer_name = 'Customer ' || SUBSTRING(id, 1, 8),
  customer_phone = CASE WHEN customer_phone IS NOT NULL THEN '98765' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0') ELSE NULL END;
EOF
echo "✓ Walk-ins anonymized"

echo -e "\n${GREEN}[5/5]${NC} Anonymizing bill customer data..."
docker compose exec postgres psql -U salon_user -d salon_db <<EOF
UPDATE bills
SET
  customer_name = CASE WHEN customer_name IS NOT NULL THEN 'Customer ' || SUBSTRING(id, 1, 8) ELSE NULL END,
  customer_phone = CASE WHEN customer_phone IS NOT NULL THEN '98765' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0') ELSE NULL END;
EOF
echo "✓ Bills anonymized"

echo -e "\n${GREEN}====================================${NC}"
echo -e "${GREEN}  ✓ Sanitization Complete!${NC}"
echo -e "${GREEN}====================================${NC}"

echo -e "\nVerification:"
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT
  'Customers' as table_name,
  COUNT(*) as total,
  COUNT(DISTINCT name) as unique_names,
  COUNT(DISTINCT phone) as unique_phones
FROM customers
UNION ALL
SELECT
  'Bills',
  COUNT(*),
  COUNT(DISTINCT customer_name),
  COUNT(DISTINCT customer_phone)
FROM bills;
"

echo -e "\n${YELLOW}Sample anonymized data:${NC}"
docker compose exec postgres psql -U salon_user -d salon_db -c "
SELECT name, phone, email FROM customers LIMIT 5;
"

echo -e "\n${GREEN}Done! You can now safely use this data for testing.${NC}"
echo -e "${YELLOW}Backup location: backups/pre_sanitize_$TIMESTAMP.dump${NC}"
