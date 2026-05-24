#!/bin/bash
#
# SalonOS Auto-Update Script
# Runs every 30 min via Windows Task Scheduler → wsl.exe
# Checks B2 for a newer version; deploys if found.
#
# Requires (set once in /opt/salon-os/.env):
#   B2_PUBLIC_BASE_URL=https://f003.backblazeb2.com/file/salon-os-releases
#   TAILSCALE_IP=100.x.x.x

set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────

INSTALL_ROOT="/opt"
INSTALL_LINK="${INSTALL_ROOT}/salon-os"
VERSION_FILE="${INSTALL_ROOT}/salon-os-current-version"
LOG_FILE="/var/log/salon-os-updater.log"
TMP_DIR="/tmp"

# ─── Helpers ──────────────────────────────────────────────────────────────────

log() {
    local level="$1"; shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') [${level}] $*" | tee -a "$LOG_FILE"
}

die() {
    log "ERROR" "$*"
    exit 1
}

# ─── Load config from current install's .env ──────────────────────────────────

if [ ! -L "$INSTALL_LINK" ]; then
    die "No symlink at $INSTALL_LINK — run initial install first"
fi

ENV_FILE="${INSTALL_LINK}/.env"
if [ ! -f "$ENV_FILE" ]; then
    die ".env not found at $ENV_FILE"
fi

B2_PUBLIC_BASE_URL=$(grep -E '^B2_PUBLIC_BASE_URL=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'" | head -1)
if [ -z "$B2_PUBLIC_BASE_URL" ]; then
    die "B2_PUBLIC_BASE_URL not set in $ENV_FILE"
fi

# ─── Check latest version ─────────────────────────────────────────────────────

LATEST_JSON=$(curl -fsSL "${B2_PUBLIC_BASE_URL}/latest.json") \
    || die "Failed to fetch latest.json from B2"

LATEST_VERSION=$(echo "$LATEST_JSON" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
LATEST_FILENAME=$(echo "$LATEST_JSON" | grep -o '"filename":"[^"]*"' | cut -d'"' -f4)
LATEST_SHA256=$(echo "$LATEST_JSON"  | grep -o '"sha256":"[^"]*"'   | cut -d'"' -f4)

if [ -z "$LATEST_VERSION" ] || [ -z "$LATEST_FILENAME" ] || [ -z "$LATEST_SHA256" ]; then
    die "latest.json is malformed or missing required fields"
fi

CURRENT_VERSION=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE")
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    log "INFO" "already at ${LATEST_VERSION}, nothing to do"
    exit 0
fi

log "INFO" "new version ${LATEST_VERSION} detected (current: ${CURRENT_VERSION:-none}), starting update"

# ─── Download ─────────────────────────────────────────────────────────────────

START_TIME=$(date +%s)
TMP_TARBALL="${TMP_DIR}/${LATEST_FILENAME}"

log "INFO" "downloading ${LATEST_FILENAME} ..."
curl -fsSL -o "$TMP_TARBALL" "${B2_PUBLIC_BASE_URL}/${LATEST_FILENAME}" \
    || die "Download failed"

# ─── Verify SHA256 ────────────────────────────────────────────────────────────

if command -v sha256sum &> /dev/null; then
    ACTUAL_SHA256=$(sha256sum "$TMP_TARBALL" | awk '{print $1}')
else
    ACTUAL_SHA256=$(shasum -a 256 "$TMP_TARBALL" | awk '{print $1}')
fi

if [ "$ACTUAL_SHA256" != "$LATEST_SHA256" ]; then
    rm -f "$TMP_TARBALL"
    die "SHA256 mismatch — expected ${LATEST_SHA256}, got ${ACTUAL_SHA256}. Aborting."
fi

log "INFO" "SHA256 verified OK"

# ─── Extract ──────────────────────────────────────────────────────────────────

TARBALL_INNER_DIR=$(tar -tzf "$TMP_TARBALL" | head -1 | cut -d'/' -f1)
NEW_INSTALL_DIR="${INSTALL_ROOT}/${TARBALL_INNER_DIR}"

if [ -d "$NEW_INSTALL_DIR" ]; then
    log "INFO" "removing existing dir ${NEW_INSTALL_DIR}"
    rm -rf "$NEW_INSTALL_DIR"
fi

log "INFO" "extracting to ${NEW_INSTALL_DIR} ..."
tar -xzf "$TMP_TARBALL" -C "$INSTALL_ROOT"
chmod +x "${NEW_INSTALL_DIR}/scripts/"*.sh 2>/dev/null || true

# ─── Copy .env ────────────────────────────────────────────────────────────────

cp "${INSTALL_LINK}/.env" "${NEW_INSTALL_DIR}/.env"
log "INFO" ".env copied"

# ─── Generate HTTPS cert ──────────────────────────────────────────────────────

log "INFO" "running setup-https.sh --auto ..."
cd "$NEW_INSTALL_DIR"
bash scripts/setup-https.sh --auto \
    || die "setup-https.sh --auto failed"

# ─── Stop old containers ──────────────────────────────────────────────────────

log "INFO" "stopping current containers ..."
cd "$INSTALL_LINK"
docker compose down || true

# ─── Atomic symlink swap ──────────────────────────────────────────────────────

ln -sfn "$NEW_INSTALL_DIR" "$INSTALL_LINK"
echo "$LATEST_VERSION" > "$VERSION_FILE"
log "INFO" "symlink updated → ${NEW_INSTALL_DIR}"

# ─── Start new version ────────────────────────────────────────────────────────

log "INFO" "starting new containers ..."
cd "$INSTALL_LINK"
docker compose up -d \
    || die "docker compose up failed — run: bash ${INSTALL_LINK}/scripts/rollback.sh <previous-version>"

# ─── Run migrations ───────────────────────────────────────────────────────────

log "INFO" "running database migrations ..."
docker compose exec -T api alembic upgrade head \
    || die "alembic upgrade failed — check logs"

# ─── Cleanup ──────────────────────────────────────────────────────────────────

rm -f "$TMP_TARBALL"
log "INFO" "cleaned up temp tarball"

# ─── Prune old versions (keep newest 3) ───────────────────────────────────────

mapfile -t OLD_DIRS < <(
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "salon-os-*" \
    | sort -V | head -n -3
)
for old_dir in "${OLD_DIRS[@]}"; do
    log "INFO" "pruning old version: ${old_dir}"
    rm -rf "$old_dir"
done

# ─── Done ─────────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log "INFO" "update to ${LATEST_VERSION} complete in ${ELAPSED}s"
