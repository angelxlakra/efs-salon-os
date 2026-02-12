#!/bin/bash
#
# SalonOS - Build and Push to DockerHub
# This script builds Docker images and pushes them to DockerHub
#
# Usage: ./scripts/build-and-push.sh [version] [dockerhub-username]
# Example: ./scripts/build-and-push.sh 1.0.0 myusername
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

VERSION="${1:-latest}"
DOCKERHUB_USERNAME="${2:-}"

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

print_usage() {
    echo "Usage: $0 [version] [dockerhub-username]"
    echo ""
    echo "Arguments:"
    echo "  version             Version tag (default: latest)"
    echo "  dockerhub-username  Your DockerHub username (required)"
    echo ""
    echo "Examples:"
    echo "  $0 1.0.0 myusername"
    echo "  $0 latest myusername"
    echo ""
    echo "Before running:"
    echo "  1. Login to DockerHub: docker login"
    echo "  2. Ensure you're on the correct branch: git checkout main"
    echo ""
    exit 1
}

check_requirements() {
    log_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check if running from project root
    if [ ! -f "compose.yaml" ]; then
        log_error "Must run from project root directory"
        exit 1
    fi

    # Check if backend and frontend directories exist
    if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
        log_error "Backend or frontend directory not found"
        exit 1
    fi

    # Check DockerHub username
    if [ -z "$DOCKERHUB_USERNAME" ]; then
        log_error "DockerHub username is required"
        print_usage
    fi

    log_success "All requirements met"
}

check_docker_login() {
    log_info "Checking Docker login status..."

    if ! docker info | grep -q "Username"; then
        log_warning "Not logged into DockerHub"
        log_info "Please login now..."
        docker login
    else
        log_success "Already logged into DockerHub"
    fi
}

build_backend() {
    log_info "Building backend image..."

    cd backend

    # Build the image
    docker build \
        -t ${DOCKERHUB_USERNAME}/salon-backend:${VERSION} \
        -t ${DOCKERHUB_USERNAME}/salon-backend:latest \
        --platform linux/amd64 \
        .

    cd ..

    log_success "Backend image built: ${DOCKERHUB_USERNAME}/salon-backend:${VERSION}"
}

build_frontend() {
    log_info "Building frontend image..."

    cd frontend

    # Build the image
    docker build \
        -t ${DOCKERHUB_USERNAME}/salon-frontend:${VERSION} \
        -t ${DOCKERHUB_USERNAME}/salon-frontend:latest \
        --platform linux/amd64 \
        .

    cd ..

    log_success "Frontend image built: ${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}"
}

push_images() {
    log_info "Pushing images to DockerHub..."

    # Push backend
    log_info "Pushing backend:${VERSION}..."
    docker push ${DOCKERHUB_USERNAME}/salon-backend:${VERSION}

    if [ "$VERSION" != "latest" ]; then
        log_info "Pushing backend:latest..."
        docker push ${DOCKERHUB_USERNAME}/salon-backend:latest
    fi

    # Push frontend
    log_info "Pushing frontend:${VERSION}..."
    docker push ${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}

    if [ "$VERSION" != "latest" ]; then
        log_info "Pushing frontend:latest..."
        docker push ${DOCKERHUB_USERNAME}/salon-frontend:latest
    fi

    log_success "All images pushed to DockerHub"
}

create_deployment_package() {
    log_info "Creating deployment package for clients..."

    PACKAGE_DIR="dist/salon-os-${VERSION}"
    rm -rf "$PACKAGE_DIR"
    mkdir -p "$PACKAGE_DIR"

    # Copy compose file
    cp compose.production.yaml "$PACKAGE_DIR/docker-compose.yml"

    # Update compose file with actual username
    sed -i.bak "s/yourusername/$DOCKERHUB_USERNAME/g" "$PACKAGE_DIR/docker-compose.yml"
    sed -i.bak "s/VERSION:-latest/VERSION:-$VERSION/g" "$PACKAGE_DIR/docker-compose.yml"
    rm "$PACKAGE_DIR/docker-compose.yml.bak"

    # Copy nginx config directory (includes SSL setup for HTTPS)
    mkdir -p "$PACKAGE_DIR/nginx"
    cp nginx/nginx.conf "$PACKAGE_DIR/nginx/"

    # Copy environment example
    cp .env.example "$PACKAGE_DIR/"

    # Copy HTTPS setup files (CRITICAL for mobile camera)
    cp setup-https.sh "$PACKAGE_DIR/"
    chmod +x "$PACKAGE_DIR/setup-https.sh"
    cp HTTPS-SETUP.md "$PACKAGE_DIR/" 2>/dev/null || true

    # Copy quick start guide
    cp QUICKSTART.md "$PACKAGE_DIR/" 2>/dev/null || true

    # Copy main documentation
    cp README.md "$PACKAGE_DIR/" 2>/dev/null || true

    # Copy installation guide
    cp CLIENT_INSTALL_DOCKERHUB.md "$PACKAGE_DIR/INSTALL.md" 2>/dev/null || true

    # Copy utility scripts
    mkdir -p "$PACKAGE_DIR/scripts"

    # Copy Windows/WSL2 networking scripts
    cp wsl-port-forward.ps1 "$PACKAGE_DIR/scripts/" 2>/dev/null || true
    cp setup-auto-forward.ps1 "$PACKAGE_DIR/scripts/" 2>/dev/null || true
    cp diagnose-network.ps1 "$PACKAGE_DIR/scripts/" 2>/dev/null || true

    # Create start script
    cat > "$PACKAGE_DIR/scripts/start.sh" << 'EOF'
#!/bin/bash
docker compose up -d
EOF
    chmod +x "$PACKAGE_DIR/scripts/start.sh"

    # Create stop script
    cat > "$PACKAGE_DIR/scripts/stop.sh" << 'EOF'
#!/bin/bash
docker compose down
EOF
    chmod +x "$PACKAGE_DIR/scripts/stop.sh"

    # Create backup script
    cat > "$PACKAGE_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="./backups"
BACKUP_FILE="salon-backup-$(date +%Y%m%d-%H%M%S).sql"
mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U salon_user -Fc salon_db > "$BACKUP_DIR/$BACKUP_FILE"
echo "Backup created: $BACKUP_DIR/$BACKUP_FILE"
EOF
    chmod +x "$PACKAGE_DIR/scripts/backup.sh"

    # Create README
    cat > "$PACKAGE_DIR/README.txt" << EOF
SalonOS - Installation Package
================================

Version: ${VERSION}
DockerHub: ${DOCKERHUB_USERNAME}/salon-backend:${VERSION}
           ${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}

IMPORTANT: This version requires HTTPS for mobile camera scanning!

Quick Start:
1. Install Docker and Docker Compose
2. Copy .env.example to .env and configure
3. Run HTTPS setup: ./setup-https.sh
4. Run: docker compose pull
5. Run: docker compose up -d
6. Install SSL certificate on mobile devices
7. Access: https://[YOUR-SERVER-IP]

For detailed instructions, see:
- QUICKSTART.md - Simple 6-step setup
- HTTPS-SETUP.md - Mobile certificate installation
- INSTALL.md - DockerHub deployment

HTTPS Setup (Required for Mobile):
The setup-https.sh script will:
- Generate SSL certificates
- Configure nginx for HTTPS
- Enable camera access on mobile devices

Certificate location: nginx/ssl/salon.crt
Install this certificate on mobile devices for camera scanning.

Default Login:
Username: owner
Password: change_me_123
(Change immediately after first login!)

Support: [Your contact information]
EOF

    # Create tarball
    cd dist
    tar -czf salon-os-${VERSION}.tar.gz salon-os-${VERSION}
    cd ..

    log_success "Deployment package created: dist/salon-os-${VERSION}.tar.gz"
}

print_summary() {
    echo ""
    echo "================================================================================"
    echo "                         BUILD & PUSH COMPLETE"
    echo "================================================================================"
    echo ""
    echo "Version:          ${VERSION}"
    echo "DockerHub User:   ${DOCKERHUB_USERNAME}"
    echo ""
    echo "Images Published:"
    echo "  - ${DOCKERHUB_USERNAME}/salon-backend:${VERSION}"
    echo "  - ${DOCKERHUB_USERNAME}/salon-backend:latest"
    echo "  - ${DOCKERHUB_USERNAME}/salon-frontend:${VERSION}"
    echo "  - ${DOCKERHUB_USERNAME}/salon-frontend:latest"
    echo ""
    echo "Client Package:   dist/salon-os-${VERSION}.tar.gz"
    echo ""
    echo "Package Contents:"
    echo "  ✓ Docker Compose configuration"
    echo "  ✓ Nginx config (HTTPS-enabled)"
    echo "  ✓ setup-https.sh (HTTPS setup script)"
    echo "  ✓ HTTPS-SETUP.md (Mobile certificate guide)"
    echo "  ✓ QUICKSTART.md (Simple setup guide)"
    echo "  ✓ .env.example (Environment template)"
    echo "  ✓ Utility scripts (start, stop, backup)"
    echo "  ✓ Windows/WSL2 scripts (port forwarding, diagnostics)"
    echo ""
    echo "Next Steps:"
    echo "  1. Test the images: docker compose -f compose.production.yaml pull"
    echo "  2. Distribute: dist/salon-os-${VERSION}.tar.gz to clients"
    echo "  3. Clients setup HTTPS: ./setup-https.sh"
    echo "  4. Clients run: docker compose pull && docker compose up -d"
    echo "  5. Install SSL certificate on mobile devices (see HTTPS-SETUP.md)"
    echo ""
    echo "DockerHub URLs:"
    echo "  Backend:  https://hub.docker.com/r/${DOCKERHUB_USERNAME}/salon-backend"
    echo "  Frontend: https://hub.docker.com/r/${DOCKERHUB_USERNAME}/salon-frontend"
    echo ""
    echo "================================================================================"
}

tag_git_release() {
    if [ "$VERSION" != "latest" ]; then
        log_info "Tagging git release..."

        if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
            log_warning "Git tag v${VERSION} already exists, skipping..."
        else
            git tag -a "v${VERSION}" -m "Release version ${VERSION}"
            log_success "Git tagged: v${VERSION}"
            log_info "Don't forget to push tags: git push origin v${VERSION}"
        fi
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "================================================================================"
    echo "              SalonOS - Build and Push to DockerHub"
    echo "================================================================================"
    echo ""
    echo "Version: ${VERSION}"
    echo "DockerHub Username: ${DOCKERHUB_USERNAME}"
    echo ""

    check_requirements
    check_docker_login

    # Build images
    build_backend
    build_frontend

    # Push to DockerHub
    push_images

    # Create deployment package
    create_deployment_package

    # Tag git release
    tag_git_release

    # Print summary
    print_summary

    log_success "All done! 🎉"
}

# Run main function
main
