# SalonOS - Client Installation Guide

**Version:** 1.0.0
**Last Updated:** January 2026

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Installation Steps](#installation-steps)
4. [Initial Configuration](#initial-configuration)
5. [First-Time Setup](#first-time-setup)
6. [Network Configuration](#network-configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)
10. [Support](#support)

---

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores, 2.0 GHz | 4 cores, 2.5+ GHz |
| **RAM** | 4 GB | 8 GB or more |
| **Storage** | 50 GB free | 100 GB+ free (SSD preferred) |
| **Network** | 100 Mbps Ethernet | 1 Gbps Ethernet |

### Software Requirements

- **Operating System**:
  - Ubuntu 20.04 LTS or later
  - Debian 11 or later
  - CentOS 8 or later
  - Windows 10/11 Pro (with WSL2)
  - macOS 11+ (for development only)

- **Docker**: Version 24.0 or later
- **Docker Compose**: Version 2.20 or later

### Network Requirements

- Static IP address on local network
- Access to local DNS (optional but recommended)
- Firewall rules allowing port 80 (HTTP)
- Port 443 (HTTPS) if SSL is configured

---

## Pre-Installation Checklist

Before beginning installation, ensure you have:

- [ ] Downloaded the SalonOS distribution package (`salon-os-x.x.x-xxxxxxxx.tar.gz`)
- [ ] Verified package checksum matches the provided SHA256 sum
- [ ] Installed Docker and Docker Compose
- [ ] Configured static IP for the installation machine
- [ ] Administrator/root access to the installation machine
- [ ] Salon business information (name, address, GSTIN)
- [ ] Access to `openssl` for generating secure keys

---

## Installation Steps

### Step 1: Prepare the Installation Directory

```bash
# Create installation directory
sudo mkdir -p /opt/salon-os
cd /opt/salon-os

# Extract the distribution package
sudo tar -xzf /path/to/salon-os-x.x.x-xxxxxxxx.tar.gz
cd salon-os-x.x.x-xxxxxxxx

# Verify extraction
ls -la
# You should see: docker-images, scripts, docs, compose.yaml, etc.
```

### Step 2: Load Docker Images

This step loads all required Docker images from the distribution package.

```bash
# Run the installation script
sudo ./scripts/install.sh

# Expected output:
# Loading docker-images/backend.tar.gz...
# Loading docker-images/frontend.tar.gz...
# Loading docker-images/postgres.tar.gz...
# Loading docker-images/redis.tar.gz...
# Loading docker-images/nginx.tar.gz...
# Installation complete!
```

### Step 3: Verify Docker Images

```bash
# List loaded images
docker images | grep -E 'salon-os|postgres|redis|nginx'

# Expected output should include:
# salon-os/backend
# salon-os/frontend
# postgres:15-alpine
# redis:7-alpine
# nginx:alpine
```

---

## Initial Configuration

### Step 1: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Secure the file (only readable by root)
chmod 600 .env
```

### Step 2: Generate Secure Credentials

```bash
# Generate SECRET_KEY (copy this value)
openssl rand -hex 32

# Generate POSTGRES_PASSWORD (copy this value)
openssl rand -base64 32

# Generate REDIS_PASSWORD (copy this value)
openssl rand -base64 32
```

### Step 3: Edit Configuration File

```bash
# Edit the .env file
sudo nano .env
```

**Required Configuration (MUST be changed):**

```env
# Database Configuration
POSTGRES_DB=salon_db
POSTGRES_USER=salon_user
POSTGRES_PASSWORD=<paste password from step 2>

# Redis Configuration
REDIS_PASSWORD=<paste password from step 2>

# Security Configuration
SECRET_KEY=<paste secret key from step 2>

# Application
ENVIRONMENT=production
DEBUG=false

# Salon Information
SALON_NAME=Your Actual Salon Name
SALON_ADDRESS=Your Full Salon Address\nCity, State - PIN\nPhone: +91-XXXXXXXXXX
GSTIN=29XXXXX1234X1ZX

# CORS (use your actual domain or IP)
CORS_ORIGINS=http://salon.local
```

**Validation Checklist:**
- [ ] All `CHANGE_ME` values replaced
- [ ] POSTGRES_PASSWORD is 32+ characters
- [ ] REDIS_PASSWORD is 32+ characters
- [ ] SECRET_KEY is 64 characters (hex)
- [ ] ENVIRONMENT is "production"
- [ ] DEBUG is "false"
- [ ] SALON_NAME, SALON_ADDRESS, GSTIN are correct

Save and exit (Ctrl+X, then Y, then Enter).

---

## First-Time Setup

### Step 1: Start the Services

```bash
# Start SalonOS in production mode
sudo docker compose -f compose.yaml -f compose.prod.yaml up -d

# Monitor startup (Ctrl+C to exit)
sudo docker compose logs -f

# Wait for all services to be healthy (about 1-2 minutes)
```

### Step 2: Check Service Health

```bash
# Check all services are running
sudo docker compose ps

# All services should show "Up" or "Up (healthy)"
# If any service is unhealthy, see Troubleshooting section
```

### Step 3: Run Database Migrations

```bash
# Apply database schema
sudo docker compose exec api alembic upgrade head

# Verify migration completed
sudo docker compose exec api alembic current
```

### Step 4: Load Initial Data

```bash
# Load seed data (creates default owner account)
sudo docker compose exec api python -m app.seeds.initial_data

# Expected output:
# ✓ Created roles
# ✓ Created default owner account
# ✓ Created initial categories
```

### Step 5: First Login

1. Open a web browser on any machine in the network
2. Navigate to: `http://<server-ip>` (e.g., `http://192.168.1.50`)
3. You should see the SalonOS login page

**Default Credentials:**
```
Username: owner
Password: change_me_123
```

⚠️ **CRITICAL: Change the default password immediately!**

### Step 6: Change Default Password

1. After logging in, click on your profile icon
2. Select "Change Password"
3. Enter current password: `change_me_123`
4. Enter a strong new password (min 8 characters)
5. Save changes
6. Log out and log back in with new password

---

## Network Configuration

### Option 1: Access by IP Address

The simplest option - no configuration needed.

**Access URL:** `http://192.168.1.50` (use your actual server IP)

**Pros:**
- No DNS configuration needed
- Works immediately

**Cons:**
- Less user-friendly
- Need to remember IP address

### Option 2: Local DNS (Recommended)

Configure your router or local DNS server.

#### Option 2A: Router Configuration

1. Log into your router admin panel
2. Find "DNS Settings" or "Local DNS"
3. Add entry:
   ```
   salon.local → 192.168.1.50
   ```
4. Save and reboot router if needed

**Access URL:** `http://salon.local`

#### Option 2B: Hosts File (Per-Computer)

Edit the hosts file on each computer:

**Windows:**
```cmd
# Open Notepad as Administrator
# Edit: C:\Windows\System32\drivers\etc\hosts
# Add line:
192.168.1.50    salon.local
```

**macOS/Linux:**
```bash
sudo nano /etc/hosts
# Add line:
192.168.1.50    salon.local
```

**Access URL:** `http://salon.local`

### Option 3: mDNS (Avahi/Bonjour)

For automatic discovery on the network.

```bash
# Install Avahi (Ubuntu/Debian)
sudo apt-get install avahi-daemon

# Configure hostname
sudo hostnamectl set-hostname salon

# Service will advertise as: salon.local
```

**Access URL:** `http://salon.local`

---

## Verification

### Health Checks

```bash
# 1. Check service status
sudo docker compose ps

# 2. API health check
curl http://localhost/api/healthz
# Expected: {"status":"healthy"}

# 3. Database connection
sudo docker compose exec api python -c "from app.database import engine; engine.connect()"
# Expected: No errors

# 4. Redis connection
sudo docker compose exec redis redis-cli -a <REDIS_PASSWORD> ping
# Expected: PONG

# 5. Frontend access
curl http://localhost
# Expected: HTML response
```

### Functional Verification

Test each major feature:

- [ ] Can log in with owner credentials
- [ ] Can access POS page
- [ ] Can access Appointments page
- [ ] Can access Inventory page
- [ ] Can access Reports page
- [ ] Can create a test bill
- [ ] Can view dashboard

---

## Troubleshooting

### Services Won't Start

**Check logs:**
```bash
sudo docker compose logs api
sudo docker compose logs postgres
sudo docker compose logs redis
```

**Common issues:**
- **Port 80 already in use**: Stop conflicting service or change nginx port
- **Permission denied**: Run commands with `sudo`
- **Out of memory**: Check system resources with `docker stats`

### Database Connection Failed

```bash
# 1. Check PostgreSQL is running
sudo docker compose exec postgres pg_isready -U salon_user

# 2. Verify credentials match .env file
cat .env | grep POSTGRES

# 3. Check DATABASE_URL is correct
sudo docker compose exec api env | grep DATABASE_URL
```

### Cannot Access Web Interface

**From server itself:**
```bash
curl http://localhost
```

If this works but remote access doesn't:
- Check firewall: `sudo ufw status`
- Allow port 80: `sudo ufw allow 80/tcp`
- Check CORS_ORIGINS in .env includes your access URL

**From remote machine:**
```bash
# Test connectivity
ping 192.168.1.50

# Test HTTP
curl http://192.168.1.50
```

### Migration Fails

```bash
# Check current migration version
sudo docker compose exec api alembic current

# View migration history
sudo docker compose exec api alembic history

# If stuck, rollback and retry
sudo docker compose exec api alembic downgrade -1
sudo docker compose exec api alembic upgrade head
```

### Forgot Owner Password

```bash
# Reset password via database
sudo docker compose exec postgres psql -U salon_user -d salon_db

# In psql prompt:
UPDATE users SET password_hash = '$2b$12$...' WHERE username = 'owner';
\q

# Contact support for password reset script
```

---

## Maintenance

### Daily Tasks

- Check service health: `sudo docker compose ps`
- Monitor disk space: `df -h`

### Weekly Tasks

- Review logs for errors
- Test backup restoration
- Check for updates

### Monthly Tasks

- Clean old logs: `sudo docker compose exec api find /app/logs -mtime +30 -delete`
- Review and optimize database
- Update documentation if workflows change

### Backup

**Automated Backups:**
Backups run automatically at 23:30 IST daily (configured in worker).

**Manual Backup:**
```bash
# Create manual backup
sudo ./scripts/backup.sh

# Backups are stored in: ./salon-data/backups/
```

**Restore from Backup:**
```bash
# Stop services
sudo docker compose down

# Restore database
sudo docker compose up -d postgres
sleep 10
sudo docker compose exec -T postgres pg_restore \
  -U salon_user -d salon_db --clean < backups/backup-file.sql

# Restart all services
sudo docker compose -f compose.yaml -f compose.prod.yaml up -d
```

### Updates

**Check for Updates:**
Contact your vendor for update packages.

**Apply Updates:**
```bash
# Stop services
sudo ./scripts/stop.sh

# Backup database first!
sudo ./scripts/backup.sh

# Load new images
cd /path/to/new-package
sudo ./scripts/install.sh

# Apply new migrations
sudo docker compose exec api alembic upgrade head

# Restart services
sudo ./scripts/start.sh
```

---

## Support

### Documentation

- **README.md**: General overview
- **PROJECT_OVERVIEW.md**: Technical details
- **DEPLOYMENT_GUIDE.md**: Deployment procedures

### Logs

Access logs for troubleshooting:

```bash
# Application logs
sudo docker compose logs api -f

# Worker logs
sudo docker compose logs worker -f

# Database logs
sudo docker compose logs postgres -f
```

### Common Commands

```bash
# Start services
sudo ./scripts/start.sh

# Stop services
sudo ./scripts/stop.sh

# Restart services
sudo docker compose restart

# View status
sudo docker compose ps

# Create backup
sudo ./scripts/backup.sh
```

### Getting Help

1. Check this documentation first
2. Review logs for error messages
3. Consult troubleshooting section
4. Contact your vendor with:
   - SalonOS version (check VERSION file)
   - Error logs
   - Steps to reproduce issue

---

## Security Best Practices

1. **Change Default Passwords**: Change owner password on first login
2. **Secure .env File**: Keep file permissions at 600 (`chmod 600 .env`)
3. **Regular Backups**: Verify backups are running and test restoration
4. **Update Regularly**: Apply security updates promptly
5. **Network Security**: Use firewall, restrict access to trusted IPs
6. **Physical Security**: Secure the server machine physically
7. **Access Control**: Create individual user accounts, don't share passwords
8. **Monitor Logs**: Review logs regularly for suspicious activity

---

## Quick Reference Card

```bash
# Start SalonOS
sudo docker compose -f compose.yaml -f compose.prod.yaml up -d

# Stop SalonOS
sudo docker compose -f compose.yaml -f compose.prod.yaml down

# View Status
sudo docker compose ps

# View Logs
sudo docker compose logs -f api

# Backup Database
sudo ./scripts/backup.sh

# Access Web Interface
http://salon.local  (or http://192.168.1.50)

# Default Login
Username: owner
Password: change_me_123 (CHANGE IMMEDIATELY!)
```

---

**Installation Complete! 🎉**

Your SalonOS is now ready to use. Access it at `http://salon.local` or your configured URL.

For detailed feature documentation, see the user manual (provided separately).

---

**Document Version:** 1.0.0
**Last Updated:** January 2026
**Package Compatibility:** SalonOS 1.0.0+
