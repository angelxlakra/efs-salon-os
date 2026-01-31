#!/bin/bash
#
# SalonOS Distribution Packaging Script
# This script creates a complete, distributable package for client deployment
#
# Usage: ./scripts/package-for-distribution.sh [version]
# Example: ./scripts/package-for-distribution.sh 1.0.0
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

VERSION="${1:-latest}"
BUILD_DATE=$(date +%Y%m%d)
PACKAGE_NAME="salon-os-${VERSION}-${BUILD_DATE}"
DIST_DIR="./dist"
PACKAGE_DIR="${DIST_DIR}/${PACKAGE_NAME}"
IMAGES_DIR="${PACKAGE_DIR}/docker-images"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check if running from project root
    if [ ! -f "compose.yaml" ]; then
        log_error "Must run from project root directory"
        exit 1
    fi

    log_success "All requirements met"
}

create_directories() {
    log_info "Creating package directories..."

    rm -rf "${DIST_DIR:?}"
    mkdir -p "${PACKAGE_DIR}"
    mkdir -p "${IMAGES_DIR}"
    mkdir -p "${PACKAGE_DIR}/scripts"
    mkdir -p "${PACKAGE_DIR}/docs"

    log_success "Directories created"
}

build_docker_images() {
    log_info "Building Docker images..."

    # Build backend image
    log_info "Building backend image..."
    docker build -t salon-os/backend:${VERSION} ./backend

    # Build frontend image
    log_info "Building frontend image..."
    docker build -t salon-os/frontend:${VERSION} ./frontend

    log_success "Docker images built"
}

export_docker_images() {
    log_info "Exporting Docker images to tar files..."

    # Export backend
    log_info "Exporting backend image..."
    docker save salon-os/backend:${VERSION} -o "${IMAGES_DIR}/backend.tar"
    gzip "${IMAGES_DIR}/backend.tar"

    # Export frontend
    log_info "Exporting frontend image..."
    docker save salon-os/frontend:${VERSION} -o "${IMAGES_DIR}/frontend.tar"
    gzip "${IMAGES_DIR}/frontend.tar"

    # Pull and export PostgreSQL
    log_info "Exporting PostgreSQL image..."
    docker pull postgres:15-alpine
    docker save postgres:15-alpine -o "${IMAGES_DIR}/postgres.tar"
    gzip "${IMAGES_DIR}/postgres.tar"

    # Pull and export Redis
    log_info "Exporting Redis image..."
    docker pull redis:7-alpine
    docker save redis:7-alpine -o "${IMAGES_DIR}/redis.tar"
    gzip "${IMAGES_DIR}/redis.tar"

    # Pull and export Nginx
    log_info "Exporting Nginx image..."
    docker pull nginx:alpine
    docker save nginx:alpine -o "${IMAGES_DIR}/nginx.tar"
    gzip "${IMAGES_DIR}/nginx.tar"

    log_success "Docker images exported"
}

generate_checksums() {
    log_info "Generating checksums..."

    cd "${IMAGES_DIR}"
    sha256sum *.tar.gz > checksums.txt
    cd - > /dev/null

    log_success "Checksums generated"
}

copy_configuration_files() {
    log_info "Copying configuration files..."

    # Copy compose files
    cp compose.yaml "${PACKAGE_DIR}/"
    cp compose.prod.yaml "${PACKAGE_DIR}/"

    # Copy nginx configuration
    cp -r nginx "${PACKAGE_DIR}/"

    # Copy environment example
    cp .env.example "${PACKAGE_DIR}/"

    # Copy backend migrations
    mkdir -p "${PACKAGE_DIR}/backend/alembic"
    cp -r backend/alembic/versions "${PACKAGE_DIR}/backend/alembic/"
    cp backend/alembic.ini "${PACKAGE_DIR}/backend/"
    cp backend/alembic/env.py "${PACKAGE_DIR}/backend/alembic/"

    log_success "Configuration files copied"
}

copy_scripts() {
    log_info "Copying utility scripts..."

    # Create install script
    cat > "${PACKAGE_DIR}/scripts/install.sh" << 'EOF'
#!/bin/bash
# SalonOS Installation Script
set -e

echo "=== SalonOS Installation ==="
echo ""

# Load Docker images
echo "Loading Docker images..."
for image in docker-images/*.tar.gz; do
    echo "Loading $image..."
    gunzip -c "$image" | docker load
done

echo ""
echo "Installation complete!"
echo "Next steps:"
echo "1. Copy .env.example to .env and configure"
echo "2. Run: docker compose -f compose.yaml -f compose.prod.yaml up -d"
echo "3. See CLIENT_INSTALL.md for detailed instructions"
EOF
    chmod +x "${PACKAGE_DIR}/scripts/install.sh"

    # Create start script
    cat > "${PACKAGE_DIR}/scripts/start.sh" << 'EOF'
#!/bin/bash
# Start SalonOS in production mode
docker compose -f compose.yaml -f compose.prod.yaml up -d
EOF
    chmod +x "${PACKAGE_DIR}/scripts/start.sh"

    # Create stop script
    cat > "${PACKAGE_DIR}/scripts/stop.sh" << 'EOF'
#!/bin/bash
# Stop SalonOS
docker compose -f compose.yaml -f compose.prod.yaml down
EOF
    chmod +x "${PACKAGE_DIR}/scripts/stop.sh"

    # Create backup script
    cat > "${PACKAGE_DIR}/scripts/backup.sh" << 'EOF'
#!/bin/bash
# Backup SalonOS database
BACKUP_DIR="./backups"
BACKUP_FILE="salon-backup-$(date +%Y%m%d-%H%M%S).sql"

mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > "$BACKUP_DIR/$BACKUP_FILE"
echo "Backup created: $BACKUP_DIR/$BACKUP_FILE"
EOF
    chmod +x "${PACKAGE_DIR}/scripts/backup.sh"

    log_success "Scripts copied"
}

copy_documentation() {
    log_info "Copying documentation..."

    # Copy main README
    cp README.md "${PACKAGE_DIR}/docs/"

    # Copy CLAUDE.md as project overview
    cp claude.md "${PACKAGE_DIR}/docs/PROJECT_OVERVIEW.md"

    # Copy deployment guides
    if [ -f "DEPLOYMENT_GUIDE.md" ]; then
        cp DEPLOYMENT_GUIDE.md "${PACKAGE_DIR}/docs/"
    fi

    log_success "Documentation copied"
}

create_version_manifest() {
    log_info "Creating version manifest..."

    cat > "${PACKAGE_DIR}/VERSION" << EOF
SalonOS Version ${VERSION}
Build Date: ${BUILD_DATE}
Built at: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

Components:
- Backend: salon-os/backend:${VERSION}
- Frontend: salon-os/frontend:${VERSION}
- PostgreSQL: 15-alpine
- Redis: 7-alpine
- Nginx: alpine

Package Contents:
- Docker images (compressed tar files)
- Configuration files
- Documentation
- Utility scripts

For installation instructions, see docs/CLIENT_INSTALL.md
EOF

    log_success "Version manifest created"
}

create_tarball() {
    log_info "Creating distribution tarball..."

    cd "${DIST_DIR}"
    tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"

    # Generate checksum for the tarball
    sha256sum "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"

    cd - > /dev/null

    log_success "Distribution tarball created: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
}

print_summary() {
    echo ""
    echo "================================================================================"
    echo "                     PACKAGING COMPLETE"
    echo "================================================================================"
    echo ""
    echo "Package Name:    ${PACKAGE_NAME}"
    echo "Package Location: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
    echo "Package Size:    $(du -h "${DIST_DIR}/${PACKAGE_NAME}.tar.gz" | cut -f1)"
    echo ""
    echo "Contents:"
    echo "  - Docker images (backend, frontend, postgres, redis, nginx)"
    echo "  - Configuration files (compose.yaml, .env.example, nginx.conf)"
    echo "  - Installation scripts"
    echo "  - Documentation"
    echo ""
    echo "Next Steps:"
    echo "  1. Test the package on a clean machine"
    echo "  2. Distribute to clients: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
    echo "  3. Include the installation guide: docs/CLIENT_INSTALL.md"
    echo ""
    echo "Checksum:"
    echo "  $(cat "${DIST_DIR}/${PACKAGE_NAME}.tar.gz.sha256")"
    echo ""
    echo "================================================================================"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    # Add any cleanup if needed
    log_success "Cleanup complete"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "================================================================================"
    echo "           SalonOS Distribution Packaging Script"
    echo "================================================================================"
    echo ""
    echo "Version: ${VERSION}"
    echo "Build Date: ${BUILD_DATE}"
    echo "Package Name: ${PACKAGE_NAME}"
    echo ""

    check_requirements
    create_directories
    build_docker_images
    export_docker_images
    generate_checksums
    copy_configuration_files
    copy_scripts
    copy_documentation
    create_version_manifest
    create_tarball
    cleanup
    print_summary

    log_success "All done! 🎉"
}

# Run main function
main
