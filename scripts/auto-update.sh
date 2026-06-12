#!/bin/bash
#
# SalonOS Auto-Update Script
# Runs every 30 min via WSL cron (started at boot by /etc/wsl.conf)
# Checks B2 for a newer version; deploys if found.
#
# Requires in /opt/salon-os/.env:
#   B2_KEY_ID=...
#   B2_APP_KEY=...
#   B2_BUCKET_NAME=efs-salon-versions
#   DOCKERHUB_USERNAME=...
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

[ ! -L "$INSTALL_LINK" ] && die "No symlink at $INSTALL_LINK — run initial install first"

ENV_FILE="${INSTALL_LINK}/.env"
[ ! -f "$ENV_FILE" ] && die ".env not found at $ENV_FILE"

B2_KEY_ID=$(grep -E '^B2_KEY_ID=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'" | head -1)
B2_APP_KEY=$(grep -E '^B2_APP_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'" | head -1)
B2_BUCKET_NAME=$(grep -E '^B2_BUCKET_NAME=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'" | head -1)

[ -z "$B2_KEY_ID" ] || [ -z "$B2_APP_KEY" ] || [ -z "$B2_BUCKET_NAME" ] && \
    die "B2_KEY_ID / B2_APP_KEY / B2_BUCKET_NAME missing from $ENV_FILE"

# ─── Authenticate with B2 ─────────────────────────────────────────────────────

AUTH_RESPONSE=$(curl -fsSL --connect-timeout 10 --max-time 30 \
    -u "${B2_KEY_ID}:${B2_APP_KEY}" \
    "https://api.backblazeb2.com/b2api/v3/b2_authorize_account") \
    || die "Failed to authenticate with B2"

# B2 JSON has spaces after colons: "downloadUrl": "https://..."
B2_DOWNLOAD_URL=$(echo "$AUTH_RESPONSE" | grep -o '"downloadUrl": *"[^"]*"' | cut -d'"' -f4)
B2_AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"authorizationToken": *"[^"]*"' | cut -d'"' -f4)

[ -z "$B2_DOWNLOAD_URL" ] || [ -z "$B2_AUTH_TOKEN" ] && \
    die "B2 auth response missing downloadUrl or authorizationToken"

log "INFO" "authenticated with B2 (downloadUrl: ${B2_DOWNLOAD_URL})"

# ─── Check latest version ─────────────────────────────────────────────────────

LATEST_JSON=$(curl -fsSL --connect-timeout 10 --max-time 30 \
    -H "Authorization: ${B2_AUTH_TOKEN}" \
    "${B2_DOWNLOAD_URL}/file/${B2_BUCKET_NAME}/latest.json") \
    || die "Failed to fetch latest.json from B2"

LATEST_VERSION=$(echo "$LATEST_JSON" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
LATEST_FILENAME=$(echo "$LATEST_JSON" | grep -o '"filename":"[^"]*"' | cut -d'"' -f4)
LATEST_SHA256=$(echo "$LATEST_JSON"  | grep -o '"sha256":"[^"]*"'   | cut -d'"' -f4)

[ -z "$LATEST_VERSION" ] || [ -z "$LATEST_FILENAME" ] || [ -z "$LATEST_SHA256" ] && \
    die "latest.json is malformed or missing required fields"

[[ "$LATEST_FILENAME" != salon-os-*.tar.gz ]] || \
[[ "$LATEST_FILENAME" == *"/"* ]] || \
[[ "$LATEST_FILENAME" == *".."* ]] && \
    die "LATEST_FILENAME '${LATEST_FILENAME}' failed safety check"

CURRENT_VERSION=""
[ -f "$VERSION_FILE" ] && CURRENT_VERSION=$(cat "$VERSION_FILE")

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    log "INFO" "already at ${LATEST_VERSION}, nothing to do"
    exit 0
fi

log "INFO" "new version ${LATEST_VERSION} detected (current: ${CURRENT_VERSION:-none}), starting update"

# ─── Download ─────────────────────────────────────────────────────────────────

START_TIME=$(date +%s)
TMP_TARBALL="${TMP_DIR}/${LATEST_FILENAME}"
trap 'rm -f "$TMP_TARBALL"' EXIT

log "INFO" "downloading ${LATEST_FILENAME} ..."
curl -fsSL --connect-timeout 10 --max-time 300 \
    -H "Authorization: ${B2_AUTH_TOKEN}" \
    -o "$TMP_TARBALL" \
    "${B2_DOWNLOAD_URL}/file/${B2_BUCKET_NAME}/${LATEST_FILENAME}" \
    || die "Download failed"

# ─── Verify SHA256 ────────────────────────────────────────────────────────────

if command -v sha256sum &>/dev/null; then
    ACTUAL_SHA256=$(sha256sum "$TMP_TARBALL" | awk '{print $1}')
else
    ACTUAL_SHA256=$(shasum -a 256 "$TMP_TARBALL" | awk '{print $1}')
fi

[ "$ACTUAL_SHA256" != "$LATEST_SHA256" ] && { rm -f "$TMP_TARBALL"; die "SHA256 mismatch"; }
log "INFO" "SHA256 verified OK"

# ─── Extract ──────────────────────────────────────────────────────────────────
# grep '^salon-os-' skips macOS ._* Apple Double resource fork entries in the tarball.
# '|| true' prevents SIGPIPE from head -1 killing the script under set -euo pipefail.

TARBALL_INNER_DIR=$(tar -tzf "$TMP_TARBALL" 2>/dev/null | grep '^salon-os-' | head -1 | cut -d'/' -f1 || true)

if [ -z "$TARBALL_INNER_DIR" ] || \
   [[ "$TARBALL_INNER_DIR" != salon-os-* ]] || \
   [[ "$TARBALL_INNER_DIR" == *".."* ]]; then
    rm -f "$TMP_TARBALL"
    die "Unexpected tarball structure — inner dir '${TARBALL_INNER_DIR}' failed safety check"
fi

NEW_INSTALL_DIR="${INSTALL_ROOT}/${TARBALL_INNER_DIR}"
[ -d "$NEW_INSTALL_DIR" ] && { log "INFO" "removing existing dir ${NEW_INSTALL_DIR}"; rm -rf "$NEW_INSTALL_DIR"; }

log "INFO" "extracting to ${NEW_INSTALL_DIR} ..."
tar -xzf "$TMP_TARBALL" -C "$INSTALL_ROOT"
chmod +x "${NEW_INSTALL_DIR}/scripts/"*.sh 2>/dev/null || true

# ─── Copy .env + inject VERSION ───────────────────────────────────────────────

cp "${INSTALL_LINK}/.env" "${NEW_INSTALL_DIR}/.env"
# Remove any existing VERSION line then append the correct one
grep -v '^VERSION=' "${NEW_INSTALL_DIR}/.env" > "${NEW_INSTALL_DIR}/.env.tmp" && \
    mv "${NEW_INSTALL_DIR}/.env.tmp" "${NEW_INSTALL_DIR}/.env"
echo "VERSION=${LATEST_VERSION}" >> "${NEW_INSTALL_DIR}/.env"
log "INFO" ".env copied (VERSION=${LATEST_VERSION})"

# ─── Generate HTTPS cert ──────────────────────────────────────────────────────

log "INFO" "running setup-https.sh --auto ..."
cd "$NEW_INSTALL_DIR"
bash scripts/setup-https.sh --auto || die "setup-https.sh --auto failed"

# ─── Stop old containers ──────────────────────────────────────────────────────

log "INFO" "stopping current containers ..."
cd "$INSTALL_LINK"
docker compose down || log "WARN" "docker compose down returned non-zero"

# ─── Atomic symlink swap ──────────────────────────────────────────────────────

ln -sfn "$NEW_INSTALL_DIR" "$INSTALL_LINK"
echo "$LATEST_VERSION" > "$VERSION_FILE"
log "INFO" "symlink updated → ${NEW_INSTALL_DIR}"

# ─── Pull new images + start ──────────────────────────────────────────────────

log "INFO" "pulling new images from Docker Hub ..."
cd "$INSTALL_LINK"
docker compose pull || die "docker compose pull failed"

log "INFO" "starting new containers ..."
docker compose up -d || die "docker compose up failed — run rollback.sh"

# ─── Run migrations ───────────────────────────────────────────────────────────

log "INFO" "waiting for api container to become healthy ..."
READY=false
for i in $(seq 1 30); do
    docker compose exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null && READY=true && break
    sleep 2
done
[ "$READY" != "true" ] && die "api container did not become ready after 60s"

log "INFO" "running database migrations ..."
docker compose exec -T api alembic upgrade head || die "alembic upgrade failed"

# ─── Cleanup ──────────────────────────────────────────────────────────────────

rm -f "$TMP_TARBALL"
log "INFO" "cleaned up temp tarball"
trap - EXIT

# ─── Prune old versions (keep newest 3) ───────────────────────────────────────

mapfile -t OLD_DIRS < <(
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "salon-os-*" | sort -V | head -n -3
)
for old_dir in "${OLD_DIRS[@]}"; do
    log "INFO" "pruning old version: ${old_dir}"
    rm -rf "$old_dir"
done

# ─── Done ─────────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log "INFO" "update to ${LATEST_VERSION} complete in ${ELAPSED}s"
