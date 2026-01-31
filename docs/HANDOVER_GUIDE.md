# SalonOS - Handover & Deployment Flow

**Complete guide from development to client installation**

---

## 📋 Table of Contents

1. [Pre-Handover: What YOU Do](#pre-handover-what-you-do)
2. [Handover Day: What YOU Do](#handover-day-what-you-do)
3. [Installation: What CLIENT Does](#installation-what-client-does)
4. [Post-Installation: What YOU Do](#post-installation-what-you-do)
5. [Training: What YOU Do](#training-what-you-do)
6. [Handover Checklist](#handover-checklist)

---

## 🔧 Pre-Handover: What YOU Do

**Timeline: 1-2 days before handover**

### Step 1: Prepare Your Development Environment

```bash
# Navigate to project directory
cd /Users/angelxlakra/dev/efs-salon-os

# Ensure you're on the main branch
git checkout main

# Pull latest changes
git pull origin main

# Verify application is working
docker compose up -d
docker compose ps  # All services should be healthy
```

### Step 2: Test the Application

```bash
# 1. Access the application
open http://localhost

# 2. Test core features:
# - Login with owner account
# - Create a test bill
# - Create an appointment
# - Add inventory item
# - Generate a report
# - Create an expense

# 3. Verify background jobs
docker compose logs worker | grep "daily_summary"

# 4. Test backup
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > test-backup.sql

# 5. Stop services
docker compose down
```

### Step 3: Create the Distribution Package

```bash
# Run the packaging script
./scripts/package-for-distribution.sh 1.0.0

# This will:
# - Build Docker images
# - Export images to tar files (compressed)
# - Package configuration files
# - Include documentation
# - Create a single distributable tarball

# Expected output location:
# dist/salon-os-1.0.0-YYYYMMDD.tar.gz
```

**What gets created:**
```
dist/
└── salon-os-1.0.0-20260131/
    ├── docker-images/
    │   ├── backend.tar.gz         (FastAPI app)
    │   ├── frontend.tar.gz        (Next.js app)
    │   ├── postgres.tar.gz        (Database)
    │   ├── redis.tar.gz           (Cache/Queue)
    │   ├── nginx.tar.gz           (Reverse proxy)
    │   └── checksums.txt          (Verification)
    ├── scripts/
    │   ├── install.sh             (Load images)
    │   ├── start.sh               (Start services)
    │   ├── stop.sh                (Stop services)
    │   └── backup.sh              (Backup database)
    ├── docs/
    │   ├── README.md
    │   ├── PROJECT_OVERVIEW.md
    │   └── DEPLOYMENT_GUIDE.md
    ├── nginx/
    │   └── nginx.conf
    ├── backend/
    │   └── alembic/               (Database migrations)
    ├── compose.yaml               (Docker config)
    ├── compose.prod.yaml          (Production overrides)
    ├── .env.example               (Config template)
    ├── CLIENT_INSTALL.md          (Installation guide)
    └── VERSION                    (Version info)
```

### Step 4: Verify the Package

```bash
# Check package was created
ls -lh dist/salon-os-1.0.0-*.tar.gz

# Typical size: 500MB - 1GB (compressed)

# Verify checksum
cat dist/salon-os-1.0.0-*.tar.gz.sha256
sha256sum dist/salon-os-1.0.0-*.tar.gz
```

### Step 5: Test Installation (Optional but Recommended)

**Use a clean test machine or VM:**

```bash
# Copy package to test machine
scp dist/salon-os-1.0.0-*.tar.gz user@test-machine:/tmp/

# SSH to test machine
ssh user@test-machine

# Extract and test installation
cd /tmp
tar -xzf salon-os-1.0.0-*.tar.gz
cd salon-os-1.0.0-*
./scripts/install.sh

# Configure
cp .env.example .env
nano .env  # Add test values

# Start
./scripts/start.sh

# Verify
docker compose ps
curl http://localhost/api/healthz

# Clean up
./scripts/stop.sh
docker compose down -v
```

### Step 6: Prepare Handover Materials

**Create a USB drive or prepare for transfer with:**

1. **Distribution Package**
   ```
   salon-os-1.0.0-YYYYMMDD.tar.gz
   salon-os-1.0.0-YYYYMMDD.tar.gz.sha256
   ```

2. **Documentation** (PDFs for offline access)
   ```
   CLIENT_INSTALL.pdf
   USER_MANUAL.pdf (if available)
   HANDOVER_CHECKLIST.pdf
   ```

3. **Support Materials**
   ```
   - Your contact information
   - Support agreement (if any)
   - License information
   - Warranty details
   ```

### Step 7: Pre-Site Survey (If Possible)

**Gather information from client:**

- [ ] Server specifications (CPU, RAM, disk)
- [ ] Operating system (Ubuntu/Debian/CentOS)
- [ ] Network setup (router, static IP availability)
- [ ] Internet connection (for Docker installation if needed)
- [ ] Printer details (for receipt printing)
- [ ] Number of client machines
- [ ] Network topology (LAN setup)

---

## 📦 Handover Day: What YOU Do

**Timeline: Day of installation (4-6 hours)**

### Phase 1: Pre-Installation Setup (1 hour)

#### 1.1 Verify Server Hardware

```bash
# Check CPU
lscpu | grep "CPU(s)"
# Minimum: 2 cores, Recommended: 4 cores

# Check RAM
free -h
# Minimum: 4GB, Recommended: 8GB

# Check disk space
df -h
# Minimum: 50GB free, Recommended: 100GB+

# Check network
ip addr show
ifconfig
```

#### 1.2 Install Docker & Docker Compose

**If not already installed:**

**Ubuntu/Debian:**
```bash
# Update packages
sudo apt update
sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Add user to docker group (optional)
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

#### 1.3 Configure Network

**Set Static IP:**

```bash
# Ubuntu with Netplan
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.50/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply
```

**Configure Firewall:**

```bash
# Ubuntu
sudo ufw allow 80/tcp
sudo ufw enable

# CentOS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

### Phase 2: Installation (1-2 hours)

#### 2.1 Transfer and Extract Package

```bash
# Create installation directory
sudo mkdir -p /opt/salon-os
cd /opt/salon-os

# Transfer package (from USB or network)
# Option A: From USB
sudo cp /media/usb/salon-os-1.0.0-*.tar.gz .

# Option B: Via SCP
scp salon-os-1.0.0-*.tar.gz client@192.168.1.50:/opt/salon-os/

# Verify checksum
sha256sum -c salon-os-1.0.0-*.tar.gz.sha256

# Extract
sudo tar -xzf salon-os-1.0.0-*.tar.gz
cd salon-os-1.0.0-*

# Set ownership
sudo chown -R $USER:$USER .
```

#### 2.2 Load Docker Images

```bash
# Run installation script
sudo ./scripts/install.sh

# This loads all Docker images (takes 5-10 minutes)
# Expected output:
# Loading docker-images/backend.tar.gz...
# Loading docker-images/frontend.tar.gz...
# Loading docker-images/postgres.tar.gz...
# Loading docker-images/redis.tar.gz...
# Loading docker-images/nginx.tar.gz...
# Installation complete!

# Verify images loaded
docker images | grep -E 'salon-os|postgres|redis|nginx'
```

#### 2.3 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Secure the file
chmod 600 .env

# Generate secure credentials
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env.tmp
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> .env.tmp
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env.tmp

# Show generated values
cat .env.tmp
```

**Now edit .env with client's information:**

```bash
nano .env
```

**Fill in these values WITH the client:**

```env
# Database (use generated password)
POSTGRES_DB=salon_db
POSTGRES_USER=salon_user
POSTGRES_PASSWORD=<paste from .env.tmp>

# Redis (use generated password)
REDIS_PASSWORD=<paste from .env.tmp>

# Security (use generated key)
SECRET_KEY=<paste from .env.tmp>

# Application
ENVIRONMENT=production
DEBUG=false
TZ=Asia/Kolkata

# CORS (use their actual IP or domain)
CORS_ORIGINS=http://salon.local,http://192.168.1.50

# Salon Information (ask client for these)
SALON_NAME=Glamour Beauty Salon
SALON_ADDRESS=123 MG Road\nBengaluru, Karnataka - 560001\nPhone: +91-9876543210
GSTIN=29ABCDE1234F1Z5
```

**Save and secure:**
```bash
# Remove temporary file with credentials
rm .env.tmp

# Verify .env permissions
ls -la .env
# Should show: -rw------- (600)
```

#### 2.4 Start Services

```bash
# Start in production mode
sudo ./scripts/start.sh

# Or manually:
sudo docker compose -f compose.yaml -f compose.prod.yaml up -d

# Monitor startup (Ctrl+C to exit)
sudo docker compose logs -f

# Wait for all services to be healthy (1-2 minutes)
```

#### 2.5 Verify Services

```bash
# Check all containers are running
sudo docker compose ps

# Expected output:
# NAME               STATUS         PORTS
# salon-api          Up (healthy)
# salon-frontend     Up (healthy)
# salon-nginx        Up (healthy)   0.0.0.0:80->80/tcp
# salon-postgres     Up (healthy)
# salon-redis        Up (healthy)
# salon-worker       Up (healthy)

# Health checks
curl http://localhost/api/healthz
# Expected: {"status":"healthy"}

curl http://localhost
# Expected: HTML response
```

#### 2.6 Initialize Database

```bash
# Run migrations
sudo docker compose exec api alembic upgrade head

# Verify migration
sudo docker compose exec api alembic current
# Expected: Shows current migration ID

# Load seed data
sudo docker compose exec api python -m app.seeds.initial_data

# Expected output:
# ✓ Created roles: owner, receptionist, staff
# ✓ Created default owner account
# ✓ Created service categories
# ✓ Created expense categories
```

### Phase 3: Client Testing (30 minutes)

**Guide client through first login:**

#### 3.1 Access from Client Machine

```bash
# From any computer on the network
# Open browser and go to:
http://192.168.1.50
# or
http://salon.local (if DNS configured)
```

#### 3.2 First Login

**Show client the login screen:**
```
Username: owner
Password: change_me_123
```

**IMMEDIATELY change password:**
1. After login, click profile icon (top right)
2. Click "Change Password"
3. Current: `change_me_123`
4. New: [Client chooses strong password]
5. **Write it down in a secure location!**

#### 3.3 Quick Feature Tour

**Walk through each section:**

1. **Dashboard** - Overview of today's activity
2. **POS** - Create a test bill
   - Add a service
   - Add customer name
   - Process payment
   - View receipt

3. **Appointments** - Schedule a test appointment
   - Select date/time
   - Choose service
   - Assign staff
   - Add customer details

4. **Inventory** - Add a test product
   - Create SKU
   - Set initial stock
   - Mark as sellable (if retail product)

5. **Expenses** - Record a test expense
   - Select category
   - Enter amount
   - Add description

6. **Reports** - View reports
   - Daily summary
   - Profit & Loss

#### 3.4 Verify Backups

```bash
# Check backup schedule
sudo docker compose exec worker python -c "
from app.jobs.scheduled import scheduler
print('Scheduled jobs:')
for job in scheduler.get_jobs():
    print(f'- {job.name}: next run at {job.next_run_time}')
"

# Create manual backup to test
sudo ./scripts/backup.sh

# Verify backup file created
ls -lh salon-data/backups/
```

### Phase 4: Network Configuration (30 minutes)

#### 4.1 Configure DNS (Recommended)

**Option A: Router Configuration**

1. Access router admin panel (usually 192.168.1.1)
2. Navigate to DNS or DHCP settings
3. Add local DNS entry:
   ```
   Hostname: salon
   IP Address: 192.168.1.50
   ```
4. Save and reboot router

**Option B: Hosts File (Each Computer)**

**On Windows client machines:**
```cmd
# Run Notepad as Administrator
# Edit: C:\Windows\System32\drivers\etc\hosts
# Add line:
192.168.1.50    salon.local
```

**On macOS/Linux client machines:**
```bash
sudo nano /etc/hosts
# Add line:
192.168.1.50    salon.local
```

#### 4.2 Test from Multiple Machines

```bash
# From receptionist computer
ping salon.local
curl http://salon.local

# From staff computer
ping salon.local
# Access in browser: http://salon.local
```

### Phase 5: Printer Configuration (If Applicable)

#### 5.1 Thermal Printer Setup

**For 80mm thermal receipt printer:**

1. Connect printer to network
2. Note printer IP address (e.g., 192.168.1.100)
3. Configure in SalonOS:
   - Go to Settings → Printer
   - Enter printer IP
   - Test print

**Or connect via USB:**
```bash
# Check printer is detected
lsusb
ls /dev/usb/lp*

# Configure CUPS (if needed)
sudo apt install cups
sudo usermod -aG lpadmin $USER
```

### Phase 6: Final Verification (15 minutes)

#### 6.1 Complete System Test

**Checklist:**
- [ ] Can access from server: `http://localhost`
- [ ] Can access from receptionist PC: `http://salon.local`
- [ ] Can access from staff PC: `http://salon.local`
- [ ] Can log in as owner (new password works)
- [ ] Can create and complete a bill
- [ ] Can schedule an appointment
- [ ] Can add inventory item
- [ ] Can record expense
- [ ] Can view reports
- [ ] Backup job is scheduled
- [ ] All services are healthy
- [ ] Receipts can print (if printer configured)

#### 6.2 Document Installation

**Create installation summary document for client:**

```bash
# Create summary file
cat > /opt/salon-os/INSTALLATION_SUMMARY.txt << EOF
SalonOS Installation Summary
============================

Installation Date: $(date)
Version: 1.0.0
Server IP: 192.168.1.50
Access URL: http://salon.local

Credentials:
- Username: owner
- Password: [Client's chosen password - DO NOT WRITE HERE]

Services Status:
$(docker compose ps)

Backup Schedule: Daily at 23:30 IST
Backup Location: /opt/salon-os/salon-data/backups/

Support Contact: [Your contact information]

Important Commands:
- Start services: sudo /opt/salon-os/scripts/start.sh
- Stop services: sudo /opt/salon-os/scripts/stop.sh
- Create backup: sudo /opt/salon-os/scripts/backup.sh
- View logs: sudo docker compose logs -f
- Check status: sudo docker compose ps

Notes:
- Keep this file secure
- Regular backups are automated
- For support, contact: [your email/phone]
EOF

cat /opt/salon-os/INSTALLATION_SUMMARY.txt
```

---

## 🎓 Training: What YOU Do

**Timeline: 2-4 hours (same day or next day)**

### Owner Training (2-3 hours)

**Session 1: System Overview (30 min)**
- Navigate interface
- Dashboard overview
- User roles and permissions

**Session 2: Daily Operations (1 hour)**
- POS operations
  - Create bills
  - Process payments
  - Apply discounts
  - Handle refunds
- Appointment management
  - Schedule appointments
  - Handle walk-ins
  - Mark complete/cancel

**Session 3: Management (1 hour)**
- Inventory management
  - Add products
  - Update stock
  - Set retail prices
  - Approval workflow
- Expense tracking
  - Record expenses
  - Create recurring expenses
  - Approve expenses
- User management
  - Create receptionist/staff accounts
  - Assign permissions

**Session 4: Reports & Backup (30 min)**
- Generate reports
  - Daily summary
  - Monthly report
  - Profit & Loss
  - Tax report
- Backup verification
  - Check backup status
  - Manual backup
  - Restore procedure (overview)

### Receptionist Training (1-2 hours)

**Session 1: Daily Operations (1 hour)**
- Login and navigation
- POS operations
- Appointment scheduling
- Customer management

**Session 2: Reporting (30 min)**
- View daily reports
- Generate receipts
- Basic troubleshooting

### Staff Training (30 minutes)

- Login and navigation
- View schedule
- Mark appointments complete
- Basic system usage

---

## ✅ Post-Installation: What YOU Do

**Timeline: 1-2 days after installation**

### Day 1 After Installation

#### Remote Check-In

```bash
# SSH to server (if remote access configured)
ssh client@192.168.1.50

# Check services
cd /opt/salon-os
sudo docker compose ps

# Check logs for errors
sudo docker compose logs --tail=100 | grep ERROR

# Check disk usage
df -h

# Check backup
ls -lh salon-data/backups/
```

**Call/Email Client:**
- Any issues encountered?
- Is everything working smoothly?
- Any questions from staff?
- Printer working correctly?

### Week 1 After Installation

**Schedule Follow-Up Visit or Call:**

**Checklist:**
- [ ] System stability (no crashes/restarts)
- [ ] All features being used correctly
- [ ] Backups running successfully
- [ ] Performance acceptable (no slowness)
- [ ] Staff comfortable with system
- [ ] Any requested changes/features
- [ ] Review first week's data
- [ ] Address any concerns

### Month 1 After Installation

**Monthly Review:**

- Review system performance
- Check backup integrity (test restore)
- Review usage patterns
- Optimize if needed
- Collect feedback
- Plan any updates/improvements

---

## 📋 Handover Checklist

### Pre-Handover

- [ ] Application tested thoroughly
- [ ] Distribution package created
- [ ] Package verified on test machine
- [ ] Documentation prepared (USB/printed)
- [ ] Support materials ready
- [ ] Client site survey completed
- [ ] Installation schedule confirmed

### Installation Day

**Phase 1: Setup**
- [ ] Server hardware verified
- [ ] Docker & Docker Compose installed
- [ ] Static IP configured
- [ ] Firewall configured

**Phase 2: Installation**
- [ ] Package transferred and extracted
- [ ] Checksum verified
- [ ] Docker images loaded
- [ ] Environment configured with client info
- [ ] Services started successfully
- [ ] All containers healthy

**Phase 3: Database**
- [ ] Migrations applied
- [ ] Seed data loaded
- [ ] Default owner account accessible

**Phase 4: Testing**
- [ ] Web interface accessible
- [ ] First login successful
- [ ] Password changed
- [ ] All features tested
- [ ] Backups scheduled

**Phase 5: Network**
- [ ] DNS configured (salon.local)
- [ ] Accessible from multiple machines
- [ ] Network performance acceptable

**Phase 6: Extras**
- [ ] Printer configured (if applicable)
- [ ] Installation summary created
- [ ] Credentials documented (securely)

### Training

**Owner:**
- [ ] System overview completed
- [ ] Daily operations trained
- [ ] Management features trained
- [ ] Reports and backup trained
- [ ] Questions answered

**Receptionist:**
- [ ] Daily operations trained
- [ ] POS operations comfortable
- [ ] Appointment scheduling understood

**Staff:**
- [ ] Basic navigation trained
- [ ] Schedule viewing understood
- [ ] Marking appointments comfortable

### Handover

- [ ] System fully operational
- [ ] All users can log in
- [ ] Client has admin password
- [ ] Installation summary provided
- [ ] Support contact information provided
- [ ] Emergency procedures explained
- [ ] Backup verification shown
- [ ] Follow-up scheduled
- [ ] Payment/contract finalized
- [ ] Handover signed off

---

## 📞 Emergency Contacts

**For Client Reference:**

```
Technical Support: [Your Name]
Phone: [Your Phone]
Email: [Your Email]
Hours: [Your Support Hours]

Emergency (System Down):
Phone: [Emergency Contact]
Available: 24/7

General Inquiries:
Email: [Support Email]
Response Time: 24 hours
```

---

## 💡 Tips for Smooth Handover

### For YOU

1. **Be Early**: Arrive 30 minutes before scheduled time
2. **Bring Backup**: Have package on multiple USB drives
3. **Test Network**: Test client's network first
4. **Document Everything**: Take notes of any customizations
5. **Be Patient**: Clients may need things explained multiple times
6. **Leave Materials**: Leave printed documentation
7. **Set Expectations**: Explain what's normal (startup time, etc.)
8. **Follow Up**: Schedule follow-up within a week

### For CLIENT

1. **Be Available**: Owner should be present entire time
2. **Prepare Server**: Have server ready and accessible
3. **Network Info**: Know router admin credentials
4. **Business Info**: Have GSTIN, address ready
5. **Staff Present**: Have key staff for training
6. **Take Notes**: Encourage them to write things down
7. **Ask Questions**: No question is too small
8. **Backup Password**: Write it down in secure location

---

## 🎯 Success Criteria

**Handover is successful when:**

- ✅ All services running and healthy
- ✅ Accessible from all client machines
- ✅ Owner can log in and use all features
- ✅ Receptionist can perform daily tasks
- ✅ Staff can view schedules
- ✅ Backups are running
- ✅ Client feels confident using the system
- ✅ All questions answered
- ✅ Support contact established
- ✅ Follow-up scheduled

---

**Document Version:** 1.0
**Last Updated:** January 2026
**For:** SalonOS v1.0.0
