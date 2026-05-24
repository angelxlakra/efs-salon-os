#!/bin/bash
#
# SalonOS Rollback Script
# Usage: bash /opt/salon-os/scripts/rollback.sh 1.0.36
#
# Rolls back to a previously installed version (must still exist under /opt/)

set -euo pipefail

INSTALL_ROOT="/opt"
INSTALL_LINK="${INSTALL_ROOT}/salon-os"
VERSION_FILE="${INSTALL_ROOT}/salon-os-current-version"

TARGET_VERSION="${1:-}"
if [ -z "$TARGET_VERSION" ]; then
    echo "Usage: $0 <version>"
    echo ""
    echo "Available versions:"
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "salon-os-*" | sort -V | sed 's|.*/||'
    exit 1
fi

TARGET_DIR="${INSTALL_ROOT}/salon-os-${TARGET_VERSION}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: ${TARGET_DIR} does not exist"
    echo ""
    echo "Available versions:"
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "salon-os-*" | sort -V | sed 's|.*/||'
    exit 1
fi

echo "Rolling back to ${TARGET_VERSION} ..."

cd "$INSTALL_LINK"
docker compose down || true

ln -sfn "$TARGET_DIR" "$INSTALL_LINK"
echo "$TARGET_VERSION" > "$VERSION_FILE"

cd "$INSTALL_LINK"
docker compose up -d

echo "Rolled back to ${TARGET_VERSION}"
echo "Run: docker compose logs -f   to watch startup"
