# Aasan - Handover Guide (DockerHub Distribution)

**Simple, streamlined deployment using DockerHub**

---

## 🎯 Overview - What Changed

### Old Method (Tar Files)
- ❌ Build images locally
- ❌ Export to 500MB+ tar files
- ❌ Transfer large files via USB
- ❌ Client loads tar files
- Time: 30 minutes

### New Method (DockerHub)
- ✅ Build and push to DockerHub once
- ✅ Give client small package (~10MB)
- ✅ Client pulls images from internet
- ✅ Much simpler and faster
- Time: 5 minutes

---

## 📅 Complete Flow

```
[YOU - Prepare]  →  [YOU - Publish]  →  [CLIENT - Install]
   1 day            30 minutes           2-4 hours
```

---

## 🔧 PART 1: What YOU Do (Before Client Meeting)

### Day Before Installation

#### Step 1: Test Your Application

```bash
cd /Users/angelxlakra/dev/efs-salon-os

# Test locally
docker compose up -d
# Test all features...
# Verify everything works
docker compose down
```

#### Step 2: Create DockerHub Account (One-Time)

1. Go to https://hub.docker.com
2. Create account (free)
3. Note your username (e.g., `angel112`)

#### Step 3: Build and Push to DockerHub

```bash
# Login to DockerHub
docker login
# Enter your username and password

# Build and push images
./scripts/build-and-push.sh 1.0.0 angel112

# This script:
# - Builds backend and frontend images
# - Tags with version (1.0.0 and latest)
# - Pushes to DockerHub
# - Creates client distribution package
# Takes: ~10-15 minutes
```

**Output:**
```
✓ Built angel112/salon-backend:1.0.0
✓ Built angel112/salon-frontend:1.0.0
✓ Pushed to DockerHub
✓ Created dist/aasan-1.0.0.tar.gz
```

#### Step 4: Verify Images on DockerHub

1. Go to https://hub.docker.com/u/angel112
2. You should see:
   - `salon-backend` repository
   - `salon-frontend` repository
3. Click each to verify images are public

#### Step 5: Prepare for Client

**What to bring:**
- [ ] USB drive with `dist/aasan-1.0.0.tar.gz` (~10MB)
- [ ] Printed installation guide
- [ ] Your laptop
- [ ] This checklist

**The package contains:**
- `docker-compose.yml` (references your DockerHub images)
- `nginx.conf`
- `.env.example`
- `scripts/setup-https.sh` (HTTPS/SSL setup for mobile camera access)
- `scripts/` (start, stop, backup)
- `INSTALL.md`

---

## 👥 PART 2: At Client Site (Installation Day)

### Hour 1: Server Setup

#### 1.1 Verify Hardware

```bash
# Check CPU (need 2+, prefer 4+)
lscpu | grep "CPU(s)"

# Check RAM (need 4GB+, prefer 8GB+)
free -h

# Check disk (need 50GB+, prefer 100GB+)
df -h
```

#### 1.2 Install Docker & Docker Compose

**Ubuntu/Debian:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

**Takes: 5-10 minutes**

#### 1.3 Configure Network

```bash
# Set static IP (e.g., 192.168.1.50)
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.1.50/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply

# Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**Takes: 5 minutes**

### Hour 2: Installation

#### 2.1 Transfer Package

```bash
# Create installation directory
sudo mkdir -p /opt/aasan
cd /opt/aasan

# Copy from USB
sudo cp /media/usb/aasan-1.0.0.tar.gz .

# Extract (very fast - only 10MB)
sudo tar -xzf aasan-1.0.0.tar.gz
cd aasan-1.0.0

# Verify contents
ls -la
```

**Takes: 2 minutes**

#### 2.2 Configure Environment

```bash
# Copy template
cp .env.example .env
chmod 600 .env

# Generate passwords
openssl rand -hex 32        # SECRET_KEY
openssl rand -base64 32     # POSTGRES_PASSWORD
openssl rand -base64 32     # REDIS_PASSWORD

# Edit configuration
nano .env
```

**Fill in WITH client:**
```env
SECRET_KEY=<paste from above>
POSTGRES_PASSWORD=<paste from above>
REDIS_PASSWORD=<paste from above>

SALON_NAME=Glamour Beauty Salon
SALON_ADDRESS=123 MG Road\nBangalore - 560001\nPhone: +91-9876543210
GSTIN=29ABCDE1234F1Z5

CORS_ORIGINS=http://localhost,http://192.168.1.50
```

**Takes: 10 minutes**

#### 2.3 Set Up HTTPS (Required for Mobile Camera)

HTTPS is required for barcode/camera scanning on mobile devices. The `scripts/setup-https.sh` script generates a self-signed SSL certificate and configures nginx for HTTPS.

```bash
# Run the HTTPS setup script
./scripts/setup-https.sh

# This script:
# - Generates a self-signed SSL certificate
# - Configures nginx to serve over HTTPS (port 443)
# - Enables camera access on mobile browsers

# After running, install the generated certificate on mobile devices:
# Certificate location: nginx/ssl/salon.crt
# See HTTPS-SETUP.md for device-specific instructions
```

**Takes: 5 minutes**

#### 2.4 Pull Images from DockerHub

```bash
# This requires internet connection
docker compose pull

# Downloads from DockerHub:
# - angel112/salon-backend:1.0.0
# - angel112/salon-frontend:1.0.0
# - postgres:15-alpine
# - redis:7-alpine
# - nginx:alpine
```

**Takes: 5-10 minutes (depends on internet speed)**

**Progress will show:**
```
[+] Pulling api        ... done
[+] Pulling frontend   ... done
[+] Pulling postgres   ... done
[+] Pulling redis      ... done
[+] Pulling nginx      ... done
[+] Pulling worker     ... done
```

#### 2.5 Start Services

```bash
# Start all containers
docker compose up -d

# Monitor startup
docker compose logs -f
# Wait for "healthy" status... (Ctrl+C to exit)

# Check status
docker compose ps
```

**All services should show "Up (healthy)"**

**Takes: 2-3 minutes**

#### 2.6 Initialize Database

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Load seed data
docker compose exec api python -m app.seeds.initial_data
```

**Expected output:**
```
✓ Created roles
✓ Created owner account
✓ Created categories
```

**Takes: 1 minute**

### Hour 3: Testing & Network Setup

#### 3.1 First Login

**From server or any PC on network:**
```
Browser: http://192.168.1.50
```

**Login:**
```
Username: owner
Password: change_me_123
```

**IMMEDIATELY change password!**

#### 3.2 Verify Network Access

**From other machines on the LAN, access via server IP:**
`http://192.168.1.50`

**Takes: 5 minutes**

#### 3.3 Test from Multiple Computers

```bash
# From receptionist PC
ping 192.168.1.50
# Browser: http://192.168.1.50

# From staff PC
ping 192.168.1.50
# Browser: http://192.168.1.50
```

**Takes: 5 minutes**

### Hour 4: Training

#### Owner Training (1-2 hours)

Walk through:
1. **Dashboard** - Today's overview
2. **POS** - Create test bill
   - Add service
   - Add customer
   - Process payment
   - View/print receipt
3. **Appointments** - Schedule test appointment
   - Choose date/time
   - Select service and staff
   - Add customer details
4. **Inventory** - Add test product
   - Create SKU
   - Set stock level
   - Mark as sellable (if retail)
5. **Expenses** - Record test expense
   - Choose category
   - Enter amount
   - Set recurring if needed
6. **Reports** - View reports
   - Daily summary
   - Monthly report
   - Profit & Loss
7. **Users** - Create receptionist/staff accounts
8. **Backups** - Show backup schedule

#### Receptionist Training (30 minutes)

Focus on:
- POS operations
- Appointment scheduling
- Customer management

#### Staff Training (15 minutes)

Focus on:
- Login
- View schedule
- Mark appointments complete

---

## 📋 PART 3: Handover

### Final Verification Checklist

**Technical:**
- [ ] All services show "healthy": `docker compose ps`
- [ ] Can access from server: `curl http://localhost`
- [ ] Can access from receptionist PC
- [ ] Can access from staff PC
- [ ] HTTPS working for mobile camera scanning
- [ ] Owner password changed from default
- [ ] Test bill created successfully
- [ ] Test appointment scheduled
- [ ] Backups scheduled (check logs)

**Business:**
- [ ] Owner trained and comfortable
- [ ] Receptionist can use POS
- [ ] Staff can view schedules
- [ ] Client has password written down securely
- [ ] Support contact info provided

### Documentation Handover

**Give client:**
1. **Installation Summary** (create this on-site):

```bash
cat > INSTALLATION_SUMMARY.txt << EOF
Aasan Installation
====================

Date: $(date)
Version: 1.0.0
Server IP: 192.168.1.50
Access: http://localhost or http://192.168.1.50

Login:
- Username: owner
- Password: [their new password - DON'T WRITE HERE]

Support:
- Name: [Your name]
- Phone: [Your phone]
- Email: [Your email]

Quick Commands:
cd /opt/aasan/aasan-1.0.0

Start:  docker compose up -d
Stop:   docker compose down
Status: docker compose ps
Backup: ./scripts/backup.sh

Backups: Automatic daily at 23:30 IST
Location: docker volume (managed by Docker)
EOF
```

2. **Printed/PDF guides:**
   - INSTALL.md (for reference)
   - HTTPS-SETUP.md (for mobile certificate installation)
   - Quick reference card
   - Your contact info

---

## 🧾 Enabling GST (when the salon registers)

When the client obtains GST registration, activate dual-rate split billing
(see [GST Split Billing](../features/11-gst-billing.md) for the full scheme):

1. Update and run migrations: `docker compose exec api alembic upgrade head`.
   This adds the GST columns and **zeroes the tax fields on existing bills**
   (totals unchanged — no GST was collected before registration).
2. In **Settings**: enter the **GSTIN**, turn on **GST registered**, and set
   **GST effective from** to the registration date.
3. Verify: a service-only sale prints an `SRV-` TAX INVOICE with 5% added on
   top; a product-only sale prints a `PRD-` invoice with 18% shown as included
   in MRP; a mixed cart produces both bills with one combined payment.

---

## 🔄 PART 4: Post-Installation

### Day 1 After Installation

**Call/Email client:**
- "How is everything going?"
- Any issues overnight?
- All staff able to log in?
- Any questions?

**Remote check (if access configured):**
```bash
ssh client@192.168.1.50
cd /opt/aasan/aasan-1.0.0
docker compose ps
docker compose logs --tail=50 | grep ERROR
```

### Week 1 Follow-Up

**Schedule call or visit:**
- Review system usage
- Check backup status: `ls -lh backups/`
- Answer any questions
- Address any concerns
- Check performance

### Month 1 Review

**Comprehensive review:**
- System stability
- Feature usage
- Performance
- Feedback collection
- Plan improvements

---

## 🆙 PART 5: Updates (Future)

### When You Release New Version

#### You Do:

```bash
# Build and push new version
./scripts/build-and-push.sh 1.1.0 angel112

# Notify clients via email:
# "Version 1.1.0 is available with [features/fixes]"
```

#### Client Does:

```bash
# Backup first
cd /opt/aasan/aasan-1.0.0
./scripts/backup.sh

# Stop services
docker compose down

# Pull new images
docker compose pull

# Start services
docker compose up -d

# Run migrations (if needed)
docker compose exec api alembic upgrade head

# Verify
docker compose ps
```

**Takes: 5 minutes**

---

## ⚡ Quick Command Reference

### For YOU (During Installation)

```bash
# 1. Transfer package
cd /opt/aasan
tar -xzf aasan-1.0.0.tar.gz
cd aasan-1.0.0

# 2. Configure
cp .env.example .env
nano .env

# 3. Set up HTTPS (required for mobile camera)
./scripts/setup-https.sh

# 4. Install
docker compose pull
docker compose up -d

# 5. Initialize
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seeds.initial_data

# 6. Verify
docker compose ps
curl http://localhost/api/healthz
```

### For CLIENT (Daily Use)

```bash
# Start
cd /opt/aasan/aasan-1.0.0
docker compose up -d

# Stop
docker compose down

# Status
docker compose ps

# Logs
docker compose logs -f

# Backup
./scripts/backup.sh

# Update (when notified)
docker compose pull && docker compose up -d
```

---

## 🎯 Success Criteria

Installation successful when:

✅ **Technical:**
- All 6 services showing "Up (healthy)"
- Accessible from all client PCs
- HTTPS configured for mobile camera scanning
- No errors in logs
- Backups scheduled

✅ **User Adoption:**
- Owner can log in and use POS
- Receptionist can schedule appointments
- Staff can view schedules
- All comfortable with basics

✅ **Client Satisfaction:**
- Client feels confident
- Questions answered
- Support contact established
- Follow-up scheduled

---

## 📊 Comparison: Old vs New Method

| Aspect | Tar Files (Old) | DockerHub (New) |
|--------|-----------------|-----------------|
| **Package Size** | 500MB-1GB | ~10MB |
| **Transfer Method** | USB drive | Internet download |
| **Installation Time** | 30 minutes | 5 minutes |
| **Updates** | New tar file needed | Just `docker compose pull` |
| **Complexity** | High | Low |
| **Industry Standard** | No | Yes |
| **Scalability** | Poor | Excellent |
| **Client Internet** | Not needed | Needed once |

---

## 🚨 Common Issues

### "Cannot pull images"

**Solution:**
```bash
# Check internet
ping google.com

# Check Docker login (if private repo)
docker login

# Try manual pull
docker pull angel112/salon-backend:1.0.0
```

### "Services won't start"

**Solution:**
```bash
# Check logs
docker compose logs api postgres redis

# Restart
docker compose down
docker compose up -d
```

### "Can't access from other PCs"

**Solution:**
```bash
# Check firewall
sudo ufw allow 80/tcp

# Test from server
curl http://localhost

# Check network
ping 192.168.1.50  # from client PC
```

### "Mobile camera not working"

**Solution:**
```bash
# HTTPS is required for camera access on mobile browsers
# Run the HTTPS setup script
./scripts/setup-https.sh

# Install the SSL certificate on the mobile device
# See HTTPS-SETUP.md for instructions
```

---

## ✅ Installation Day Checklist

**Before you arrive:**
- [ ] Images pushed to DockerHub
- [ ] Client package created
- [ ] USB drive with package
- [ ] Printed documentation
- [ ] Laptop and tools

**At client site:**
- [ ] Docker installed
- [ ] Network configured
- [ ] Package extracted
- [ ] .env configured
- [ ] HTTPS set up (`./scripts/setup-https.sh`)
- [ ] Images pulled
- [ ] Services started
- [ ] Database initialized
- [ ] First login tested
- [ ] Password changed
- [ ] Tested from multiple PCs
- [ ] Mobile camera scanning verified
- [ ] Owner trained
- [ ] Receptionist trained
- [ ] Staff trained
- [ ] Documentation handed over
- [ ] Support info provided
- [ ] Follow-up scheduled

---

## 🎉 Summary

**What makes DockerHub better:**

1. **Simpler for YOU:**
   - Build once, push to DockerHub
   - Small package to distribute
   - Easy to update

2. **Simpler for CLIENT:**
   - Faster installation
   - Easy updates (`docker compose pull`)
   - Industry-standard method

3. **Better for Everyone:**
   - No large file transfers
   - Versioned releases
   - Automatic image management
   - Professional distribution

**Your workflow:**
```
Test → Build → Push to DockerHub → Give client package → They install
```

**Client workflow:**
```
Extract package → Configure .env → Setup HTTPS (scripts/setup-https.sh) → Pull images → Start → Use daily
```

**That's it! Much simpler than before! 🚀**

---

**Version:** 1.0.0
**Distribution:** DockerHub
**Last Updated:** February 2026
