# SalonOS - Client Installation Guide (DockerHub)

**Version:** 1.0.0
**Distribution Method:** DockerHub (Internet Required for Initial Setup)

---

## 🚀 Quick Overview

SalonOS is distributed via **DockerHub** - Docker's public image registry. This means:

✅ **Advantages:**
- Small download package (~10MB instead of 500MB)
- Easy updates (just pull new images)
- No need to transfer large files
- Industry-standard distribution method

⚠️ **Requirements:**
- Internet connection during initial setup
- After setup, works 100% offline on local network

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [First-Time Setup](#first-time-setup)
5. [Network Access](#network-access)
6. [Daily Operations](#daily-operations)
7. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 50 GB | 100 GB (SSD) |
| **Network** | 100 Mbps | 1 Gbps |

### Software

- **Operating System**: Ubuntu 20.04+, Debian 11+, CentOS 8+, Windows 10 Pro+
- **Docker**: Version 24.0+
- **Docker Compose**: Version 2.20+
- **Internet**: Required for initial setup only

---

## Installation Steps

### Step 1: Install Docker & Docker Compose

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

**CentOS/RHEL:**
```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y
sudo systemctl start docker
sudo systemctl enable docker
```

**Windows:**
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Enable WSL2 during installation
- Restart computer

### Step 2: Extract Installation Package

You should have received a file named `salon-os-x.x.x.tar.gz` from your vendor.

```bash
# Create installation directory
sudo mkdir -p /opt/salon-os
cd /opt/salon-os

# Extract package
sudo tar -xzf /path/to/salon-os-*.tar.gz

# Enter directory
cd salon-os-*

# Verify files
ls -la
# You should see:
# - docker-compose.yml
# - nginx.conf
# - .env.example
# - scripts/
# - INSTALL.md (this file)
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Secure the file
chmod 600 .env

# Generate secure credentials
echo "Generating secure passwords..."
echo "Copy these values:"
echo ""
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
```

**Edit the .env file:**

```bash
nano .env
```

**Fill in these values** (replace with actual values from above):

```env
# Database
POSTGRES_DB=salon_db
POSTGRES_USER=salon_user
POSTGRES_PASSWORD=<paste generated password>

# Redis
REDIS_PASSWORD=<paste generated password>

# Security
SECRET_KEY=<paste generated key>

# Application
ENVIRONMENT=production
DEBUG=false

# Your Salon Information
SALON_NAME=Your Salon Name
SALON_ADDRESS=Your Full Address\nCity, State - PIN\nPhone: +91-XXXXXXXXXX
GSTIN=29XXXXX1234X1ZX

# Network (change to your server IP or domain)
CORS_ORIGINS=http://salon.local,http://192.168.1.50

# Timezone
TZ=Asia/Kolkata
```

**Important:** Replace all `<paste...>` values with your actual values!

Save and exit (Ctrl+X, then Y, then Enter in nano).

### Step 4: Download Docker Images

This step requires internet connection.

```bash
# Pull all required images from DockerHub
docker compose pull

# This downloads:
# - Backend API (FastAPI)
# - Frontend (Next.js)
# - PostgreSQL database
# - Redis cache
# - Nginx reverse proxy

# Takes 5-10 minutes depending on internet speed
```

**Expected output:**
```
[+] Pulling api         ... done
[+] Pulling frontend    ... done
[+] Pulling postgres    ... done
[+] Pulling redis       ... done
[+] Pulling nginx       ... done
[+] Pulling worker      ... done
```

### Step 5: Start Services

```bash
# Start all services
docker compose up -d

# Monitor startup (Ctrl+C to exit)
docker compose logs -f

# Wait for "healthy" status (1-2 minutes)
```

**Check all services are running:**

```bash
docker compose ps
```

**Expected output:**
```
NAME               STATUS         PORTS
salon-api          Up (healthy)
salon-frontend     Up (healthy)
salon-nginx        Up (healthy)   0.0.0.0:80->80/tcp
salon-postgres     Up (healthy)
salon-redis        Up (healthy)
salon-worker       Up (healthy)
```

All services should show **"Up (healthy)"** status.

### Step 6: Initialize Database

```bash
# Run database migrations
docker compose exec api alembic upgrade head

# Load initial data (creates owner account, categories, etc.)
docker compose exec api python -m app.seeds.initial_data
```

**Expected output:**
```
✓ Created roles: owner, receptionist, staff
✓ Created default owner account
✓ Created service categories
✓ Created expense categories
```

---

## Configuration

### Network Configuration

#### Configure Static IP

**Ubuntu with Netplan:**

```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:  # Your network interface name
      dhcp4: no
      addresses:
        - 192.168.1.50/24  # Your chosen IP
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply
```

#### Configure Firewall

```bash
# Ubuntu
sudo ufw allow 80/tcp
sudo ufw enable

# CentOS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

### DNS Configuration (Optional but Recommended)

**Option 1: Router DNS**
1. Access your router admin panel (usually http://192.168.1.1)
2. Find DNS or DHCP settings
3. Add local DNS entry:
   - Hostname: `salon`
   - IP: `192.168.1.50` (your server IP)
4. Save and restart router

**Option 2: Hosts File (each computer)**

**Windows:**
```
1. Run Notepad as Administrator
2. Open: C:\Windows\System32\drivers\etc\hosts
3. Add line: 192.168.1.50    salon.local
4. Save
```

**macOS/Linux:**
```bash
sudo nano /etc/hosts
# Add: 192.168.1.50    salon.local
```

---

## First-Time Setup

### Step 1: Access Web Interface

Open a web browser and go to:
- `http://salon.local` (if DNS configured)
- OR `http://192.168.1.50` (your server IP)

You should see the SalonOS login page.

### Step 2: First Login

**Default Credentials:**
```
Username: owner
Password: change_me_123
```

⚠️ **CRITICAL: Change the password immediately!**

### Step 3: Change Password

1. After logging in, click your profile icon (top-right)
2. Select "Change Password"
3. Current password: `change_me_123`
4. New password: Choose a strong password (min 8 characters)
5. Confirm new password
6. Click "Save"
7. **Write down your new password in a secure location!**

### Step 4: Explore the System

Take a quick tour:

1. **Dashboard** - View today's summary
2. **POS** - Try creating a test bill
3. **Appointments** - Schedule a test appointment
4. **Inventory** - Add a test product
5. **Expenses** - Record a test expense
6. **Reports** - View reports and analytics

---

## Daily Operations

### Starting the System

If the server was shut down or restarted:

```bash
cd /opt/salon-os/salon-os-*
sudo docker compose up -d
```

Or use the script:
```bash
sudo ./scripts/start.sh
```

### Stopping the System

```bash
cd /opt/salon-os/salon-os-*
sudo docker compose down
```

Or use the script:
```bash
sudo ./scripts/stop.sh
```

### Checking System Status

```bash
# View service status
docker compose ps

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f api
```

### Creating Manual Backup

```bash
sudo ./scripts/backup.sh
```

Backups are saved in `./backups/` directory.

---

## Network Access

### Accessing from Other Computers

1. **From Windows PC:**
   - Open browser
   - Go to: `http://salon.local` or `http://192.168.1.50`

2. **From iPad/Tablet:**
   - Open Safari/Chrome
   - Go to: `http://salon.local` or `http://192.168.1.50`

3. **From Phone:**
   - Open browser
   - Go to: `http://salon.local` or `http://192.168.1.50`

### Printer Setup

If you have a thermal receipt printer:

1. Connect printer to network
2. Note printer IP address
3. In SalonOS, go to Settings → Printer
4. Enter printer IP and test

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs api postgres redis

# Restart services
docker compose down
docker compose up -d
```

### Can't Access from Browser

**Check firewall:**
```bash
sudo ufw status
sudo ufw allow 80/tcp
```

**Check services are running:**
```bash
docker compose ps
# All should show "Up (healthy)"
```

**Test from server itself:**
```bash
curl http://localhost
# Should return HTML
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker compose exec postgres pg_isready -U salon_user

# If not, restart
docker compose restart postgres
```

### Forgot Owner Password

Contact your vendor for password reset assistance.

### Images Won't Download

```bash
# Check internet connection
ping google.com

# Try pulling again
docker compose pull

# If specific image fails
docker pull yourusername/salon-backend:1.0.0
```

### Disk Space Full

```bash
# Check disk usage
df -h

# Clean old Docker images
docker system prune -a

# Clean old backups (keep last 7 days)
find ./backups -name "*.sql" -mtime +7 -delete
```

---

## Updates

### Updating to New Version

When your vendor releases an update:

```bash
# 1. Backup first!
sudo ./scripts/backup.sh

# 2. Stop services
sudo docker compose down

# 3. Pull new images
sudo docker compose pull

# 4. Start services
sudo docker compose up -d

# 5. Run migrations (if any)
sudo docker compose exec api alembic upgrade head

# 6. Verify
docker compose ps
```

---

## Maintenance

### Daily

- System runs automatically
- Backups run at 23:30 IST (automated)

### Weekly

- Check disk space: `df -h`
- Review logs for errors: `docker compose logs | grep ERROR`

### Monthly

- Test backup restoration
- Clean old backups
- Review system performance

---

## Support

### System Information

When contacting support, provide:

```bash
# Get version info
cat VERSION  # or README.txt

# Get service status
docker compose ps

# Get recent logs
docker compose logs --tail=100
```

### Useful Commands

```bash
# Start system
sudo docker compose up -d

# Stop system
sudo docker compose down

# View status
docker compose ps

# View logs
docker compose logs -f api

# Create backup
sudo ./scripts/backup.sh

# Restart specific service
docker compose restart api
```

### Emergency Contacts

**Vendor Support:**
- Name: [Your Name/Company]
- Phone: [Your Phone]
- Email: [Your Email]
- Hours: [Your Hours]

---

## Security Checklist

After installation, verify:

- [ ] Changed owner password from default
- [ ] .env file has secure permissions (600)
- [ ] Firewall is enabled and configured
- [ ] Only port 80 is exposed
- [ ] PostgreSQL and Redis NOT accessible from network
- [ ] Backups are running (check `./backups/` folder)
- [ ] All users have strong passwords
- [ ] .env file passwords are strong (32+ characters)

---

## Quick Reference

```bash
# Essential Commands
cd /opt/salon-os/salon-os-*

# Start
sudo docker compose up -d

# Stop
sudo docker compose down

# Status
docker compose ps

# Logs
docker compose logs -f

# Backup
sudo ./scripts/backup.sh

# Update
docker compose pull && docker compose up -d
```

**Access URLs:**
- Web Interface: http://salon.local
- API Docs: http://salon.local/api/docs
- Health Check: http://salon.local/api/healthz

**Default Login:**
- Username: `owner`
- Password: `change_me_123` (CHANGE IMMEDIATELY!)

---

**Installation Complete! 🎉**

Your SalonOS is ready to use. Access it at `http://salon.local`

For support, contact your vendor.

---

**Version:** 1.0.0
**Distribution:** DockerHub
**Last Updated:** January 2026
