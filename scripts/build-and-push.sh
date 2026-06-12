#!/bin/bash
#
# SalonOS — Build, Push, and Publish
#
# Usage:
#   ./scripts/build-and-push.sh VERSION DOCKERHUB_USERNAME [--publish]
#
# --publish  Also create a thin tarball, upload to Backblaze B2, and git-tag.
#            Requires B2_KEY_ID, B2_APP_KEY, B2_BUCKET_NAME in your shell env
#            or in a local .env.b2 file.
#
# Examples:
#   ./scripts/build-and-push.sh 1.0.41 angel112
#   ./scripts/build-and-push.sh 1.0.41 angel112 --publish

set -euo pipefail

# ─── Arg parsing ──────────────────────────────────────────────────────────────

VERSION=""
DOCKERHUB_USERNAME=""
PUBLISH=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --publish) PUBLISH=true; shift ;;
        *)
            if [ -z "$VERSION" ]; then
                VERSION="$1"
            elif [ -z "$DOCKERHUB_USERNAME" ]; then
                DOCKERHUB_USERNAME="$1"
            else
                echo "Unknown argument: $1"; exit 1
            fi
            shift ;;
    esac
done

# ─── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Validation ───────────────────────────────────────────────────────────────

[ -z "$VERSION" ]            && { log_error "VERSION is required";            echo "Usage: $0 VERSION DOCKERHUB_USERNAME [--publish]"; exit 1; }
[ -z "$DOCKERHUB_USERNAME" ] && { log_error "DOCKERHUB_USERNAME is required"; echo "Usage: $0 VERSION DOCKERHUB_USERNAME [--publish]"; exit 1; }
[ ! -f "compose.yaml" ]      && { log_error "Must run from project root (compose.yaml not found)"; exit 1; }
[ ! -d "backend" ] || [ ! -d "frontend" ] && { log_error "backend/ or frontend/ directory not found"; exit 1; }

# ─── B2 credentials (needed only for --publish) ───────────────────────────────

if $PUBLISH; then
    # Try sourcing a local B2 env file if the vars aren't already set
    if [ -z "${B2_KEY_ID:-}" ] || [ -z "${B2_APP_KEY:-}" ] || [ -z "${B2_BUCKET_NAME:-}" ]; then
        [ -f ".env.b2" ] && source ".env.b2"
    fi
    [ -z "${B2_KEY_ID:-}" ]     && { log_error "B2_KEY_ID not set (set in env or .env.b2)"; exit 1; }
    [ -z "${B2_APP_KEY:-}" ]    && { log_error "B2_APP_KEY not set (set in env or .env.b2)"; exit 1; }
    [ -z "${B2_BUCKET_NAME:-}" ] && { log_error "B2_BUCKET_NAME not set (set in env or .env.b2)"; exit 1; }
fi

PACKAGE_NAME="salon-os-${VERSION}-$(date +%Y%m%d)"
DIST_DIR="dist"

echo ""
echo "========================================================================"
echo "  SalonOS Build & Push"
echo "  Version:  ${VERSION}"
echo "  User:     ${DOCKERHUB_USERNAME}"
echo "  Publish:  ${PUBLISH}"
echo "========================================================================"
echo ""

# ─── Docker login check ───────────────────────────────────────────────────────

check_docker_login() {
    log_info "Checking Docker login ..."
    if ! docker info 2>/dev/null | grep -q "Username"; then
        log_warn "Not logged in — running docker login ..."
        docker login
    else
        log_success "Already logged in to Docker Hub"
    fi
}

# ─── Build & push images ──────────────────────────────────────────────────────

build_and_push() {
    log_info "Building backend (linux/amd64) ..."
    docker build --platform linux/amd64 \
        -t "${DOCKERHUB_USERNAME}/salon-backend:${VERSION}" \
        -t "${DOCKERHUB_USERNAME}/salon-backend:latest" \
        backend/

    log_info "Building frontend (linux/amd64) ..."
    docker build --platform linux/amd64 \
        -t "${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}" \
        -t "${DOCKERHUB_USERNAME}/salon-frontend:latest" \
        frontend/

    log_info "Pushing images to Docker Hub ..."
    docker push "${DOCKERHUB_USERNAME}/salon-backend:${VERSION}"
    docker push "${DOCKERHUB_USERNAME}/salon-backend:latest"
    docker push "${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}"
    docker push "${DOCKERHUB_USERNAME}/salon-frontend:latest"
    log_success "Images pushed to Docker Hub"
}

# ─── Create thin package directory ────────────────────────────────────────────
# No Docker images — those live on Docker Hub. This tarball (~25KB) contains
# only config, scripts, and alembic migrations that auto-update.sh deploys.

create_package() {
    log_info "Creating deployment package ${PACKAGE_NAME} ..."

    rm -rf "${DIST_DIR}/${PACKAGE_NAME}"
    mkdir -p "${DIST_DIR}/${PACKAGE_NAME}/scripts"
    mkdir -p "${DIST_DIR}/${PACKAGE_NAME}/nginx"

    # Compose file (docker compose reads compose.yaml by default)
    cp compose.production.yaml "${DIST_DIR}/${PACKAGE_NAME}/compose.yaml"

    # Nginx config
    cp nginx/nginx.conf "${DIST_DIR}/${PACKAGE_NAME}/nginx/"

    # Alembic migrations (needed by alembic upgrade head inside container)
    if [ -d "alembic" ]; then
        cp -r alembic/ "${DIST_DIR}/${PACKAGE_NAME}/alembic/"
    fi

    # All scripts (auto-update.sh, rollback.sh, setup-https.sh, setup-auto-update.sh, etc.)
    cp scripts/*.sh "${DIST_DIR}/${PACKAGE_NAME}/scripts/"
    chmod +x "${DIST_DIR}/${PACKAGE_NAME}/scripts/"*.sh

    # PowerShell helper (kept for reference, cron is the actual scheduler)
    cp scripts/setup-auto-update.ps1 "${DIST_DIR}/${PACKAGE_NAME}/scripts/" 2>/dev/null || true

    # .env template
    cp env.txt "${DIST_DIR}/${PACKAGE_NAME}/env.txt"

    # Version marker (auto-update.sh reads this to name the install dir)
    echo "${VERSION}" > "${DIST_DIR}/${PACKAGE_NAME}/VERSION"

    # CLAUDE.md for context (optional)
    cp .claude/CLAUDE.md "${DIST_DIR}/${PACKAGE_NAME}/" 2>/dev/null || true

    log_success "Package directory created: ${DIST_DIR}/${PACKAGE_NAME}/"
}

# ─── Create tarball ───────────────────────────────────────────────────────────
# COPYFILE_DISABLE=1 prevents macOS tar from embedding ._* Apple Double resource
# fork files, which would cause the safety check on Linux to fail.

create_tarball() {
    log_info "Creating tarball ..."
    cd "$DIST_DIR"
    COPYFILE_DISABLE=1 tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"
    cd ..

    local SIZE
    SIZE=$(du -sh "${DIST_DIR}/${PACKAGE_NAME}.tar.gz" | cut -f1)
    log_success "Tarball: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz (${SIZE})"
}

# ─── Publish to Backblaze B2 ──────────────────────────────────────────────────

publish_to_b2() {
    local tarball="${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
    local remote_filename="${PACKAGE_NAME}.tar.gz"

    log_info "Authenticating with B2 ..."
    local AUTH_RESPONSE
    AUTH_RESPONSE=$(curl -fsSL --connect-timeout 10 --max-time 30 \
        -u "${B2_KEY_ID}:${B2_APP_KEY}" \
        "https://api.backblazeb2.com/b2api/v3/b2_authorize_account") \
        || { log_error "B2 authentication failed"; exit 1; }

    local B2_API_URL B2_AUTH_TOKEN B2_ACCOUNT_ID
    B2_API_URL=$(echo "$AUTH_RESPONSE"   | grep -o '"apiUrl": *"[^"]*"'           | cut -d'"' -f4)
    B2_AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"authorizationToken": *"[^"]*"' | cut -d'"' -f4)
    B2_ACCOUNT_ID=$(echo "$AUTH_RESPONSE" | grep -o '"accountId": *"[^"]*"'         | cut -d'"' -f4)

    [ -z "$B2_API_URL" ] || [ -z "$B2_AUTH_TOKEN" ] || [ -z "$B2_ACCOUNT_ID" ] && \
        { log_error "B2 auth response missing fields"; exit 1; }

    # Get upload URL for this bucket
    log_info "Getting B2 upload URL ..."
    local UPLOAD_RESPONSE
    UPLOAD_RESPONSE=$(curl -fsSL --connect-timeout 10 --max-time 30 \
        -H "Authorization: ${B2_AUTH_TOKEN}" \
        -d "{\"bucketName\": \"${B2_BUCKET_NAME}\"}" \
        "${B2_API_URL}/b2api/v3/b2_get_upload_url_by_bucket_name") \
        || { log_error "Failed to get B2 upload URL"; exit 1; }

    local UPLOAD_URL UPLOAD_TOKEN
    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE"   | grep -o '"uploadUrl": *"[^"]*"'        | cut -d'"' -f4)
    UPLOAD_TOKEN=$(echo "$UPLOAD_RESPONSE" | grep -o '"authorizationToken": *"[^"]*"' | cut -d'"' -f4)

    [ -z "$UPLOAD_URL" ] || [ -z "$UPLOAD_TOKEN" ] && \
        { log_error "B2 upload URL response missing fields"; exit 1; }

    # SHA1 for B2 upload (B2 uses SHA1 for its own integrity, we use SHA256 in latest.json)
    local SHA1
    if command -v sha1sum &>/dev/null; then
        SHA1=$(sha1sum "$tarball" | awk '{print $1}')
    else
        SHA1=$(shasum -a 1 "$tarball" | awk '{print $1}')
    fi

    # SHA256 for latest.json (what auto-update.sh verifies)
    local SHA256
    if command -v sha256sum &>/dev/null; then
        SHA256=$(sha256sum "$tarball" | awk '{print $1}')
    else
        SHA256=$(shasum -a 256 "$tarball" | awk '{print $1}')
    fi

    # Upload tarball
    log_info "Uploading ${remote_filename} to B2 bucket '${B2_BUCKET_NAME}' ..."
    curl -fsSL --connect-timeout 10 --max-time 600 \
        -H "Authorization: ${UPLOAD_TOKEN}" \
        -H "X-Bz-File-Name: ${remote_filename}" \
        -H "Content-Type: application/gzip" \
        -H "X-Bz-Content-Sha1: ${SHA1}" \
        -T "$tarball" \
        "${UPLOAD_URL}" > /dev/null \
        || { log_error "Tarball upload to B2 failed"; exit 1; }
    log_success "Tarball uploaded"

    # Write latest.json
    local LATEST_JSON
    LATEST_JSON=$(printf '{"version":"%s","filename":"%s","sha256":"%s"}' \
        "$VERSION" "$remote_filename" "$SHA256")

    # Upload latest.json (overwrite existing)
    log_info "Updating latest.json ..."

    # Get a fresh upload URL (single-use)
    UPLOAD_RESPONSE=$(curl -fsSL --connect-timeout 10 --max-time 30 \
        -H "Authorization: ${B2_AUTH_TOKEN}" \
        -d "{\"bucketName\": \"${B2_BUCKET_NAME}\"}" \
        "${B2_API_URL}/b2api/v3/b2_get_upload_url_by_bucket_name") \
        || { log_error "Failed to get second B2 upload URL"; exit 1; }

    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE"   | grep -o '"uploadUrl": *"[^"]*"'          | cut -d'"' -f4)
    UPLOAD_TOKEN=$(echo "$UPLOAD_RESPONSE" | grep -o '"authorizationToken": *"[^"]*"' | cut -d'"' -f4)

    local JSON_SHA1
    if command -v sha1sum &>/dev/null; then
        JSON_SHA1=$(echo -n "$LATEST_JSON" | sha1sum | awk '{print $1}')
    else
        JSON_SHA1=$(echo -n "$LATEST_JSON" | shasum -a 1 | awk '{print $1}')
    fi

    echo -n "$LATEST_JSON" | curl -fsSL --connect-timeout 10 --max-time 30 \
        -H "Authorization: ${UPLOAD_TOKEN}" \
        -H "X-Bz-File-Name: latest.json" \
        -H "Content-Type: application/json" \
        -H "X-Bz-Content-Sha1: ${JSON_SHA1}" \
        -d @- \
        "${UPLOAD_URL}" > /dev/null \
        || { log_error "latest.json upload to B2 failed"; exit 1; }

    log_success "latest.json updated: ${LATEST_JSON}"
}

# ─── Tag git release ──────────────────────────────────────────────────────────

tag_git_release() {
    if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
        log_warn "Git tag v${VERSION} already exists, skipping"
    else
        git tag -a "v${VERSION}" -m "Release ${VERSION}"
        log_success "Git tagged: v${VERSION} (push with: git push origin v${VERSION})"
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────

check_docker_login
build_and_push

if $PUBLISH; then
    create_package
    create_tarball
    publish_to_b2
    tag_git_release

    echo ""
    echo "========================================================================"
    echo "  PUBLISHED ${VERSION}"
    echo "  Tarball:  ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
    echo "  B2:       ${B2_BUCKET_NAME}/latest.json → ${VERSION}"
    echo "  Client machines will pick this up within 30 minutes."
    echo "========================================================================"
else
    echo ""
    echo "========================================================================"
    echo "  Images pushed to Docker Hub (no B2 publish — use --publish to release)"
    echo "========================================================================"
fi
