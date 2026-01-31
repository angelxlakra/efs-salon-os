# SalonOS - Complete Deployment Flow

**Quick visual guide: From development to production**

---

## 🎯 Overview

```
[YOU - Dev]  →  [Package]  →  [Transfer]  →  [CLIENT - Install]  →  [CLIENT - Use]
   1-2 days      30 mins       Travel        4-6 hours              Ongoing
```

---

## 📅 Timeline Summary

| Phase | Duration | Who | Location |
|-------|----------|-----|----------|
| **Preparation** | 1-2 days | YOU | Your office |
| **Package Creation** | 30 mins | YOU | Your office |
| **Travel to Client** | Varies | YOU | - |
| **Installation** | 4-6 hours | YOU + CLIENT | Client site |
| **Training** | 2-4 hours | YOU + CLIENT | Client site |
| **Follow-up** | Ongoing | YOU | Remote |

---

## 📊 Detailed Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PREPARATION (YOU)                   │
│                         1-2 Days Before                          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Test Application        │
                    │  - All features working  │
                    │  - No errors in logs     │
                    │  - Backups working       │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Create Package          │
                    │  $ ./scripts/package-    │
                    │    for-distribution.sh   │
                    │  Output: .tar.gz file    │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Test Package (Optional) │
                    │  - Install on clean VM   │
                    │  - Verify everything OK  │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Prepare Materials       │
                    │  - Package on USB        │
                    │  - Print documentation   │
                    │  - Checklist ready       │
                    └──────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 2: INSTALLATION DAY (YOU + CLIENT)        │
│                           4-6 Hours                              │
└─────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┴───────────────────────────┐
        │                                                        │
        ▼                                                        ▼
┌──────────────────┐                                  ┌──────────────────┐
│  YOU: Technical  │                                  │ CLIENT: Business │
│  Setup           │                                  │ Information      │
├──────────────────┤                                  ├──────────────────┤
│ • Install Docker │                                  │ • Salon name     │
│ • Configure IP   │                                  │ • Address        │
│ • Setup firewall │                                  │ • GSTIN          │
│ • Load images    │                                  │ • Choose password│
└──────────────────┘                                  └──────────────────┘
        │                                                        │
        └──────────────────────────┬───────────────────────────┘
                                   ▼
                    ┌──────────────────────────┐
                    │  Configure .env File     │
                    │  - Generate passwords    │
                    │  - Add salon info        │
                    │  - Set production mode   │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Start Services          │
                    │  $ ./scripts/start.sh    │
                    │  Wait 1-2 minutes        │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Initialize Database     │
                    │  - Run migrations        │
                    │  - Load seed data        │
                    │  - Create owner account  │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  First Login & Test      │
                    │  - Access web interface  │
                    │  - Login as owner        │
                    │  - CHANGE PASSWORD       │
                    │  - Test all features     │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Network Setup           │
                    │  - Configure DNS         │
                    │  - Test from other PCs   │
                    │  - Setup printer         │
                    └──────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 3: TRAINING (YOU + CLIENT)              │
│                           2-4 Hours                              │
└─────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        │                          │                            │
        ▼                          ▼                            ▼
┌──────────────┐          ┌──────────────┐           ┌──────────────┐
│ Owner        │          │ Receptionist │           │ Staff        │
│ (2-3 hours)  │          │ (1-2 hours)  │           │ (30 minutes) │
├──────────────┤          ├──────────────┤           ├──────────────┤
│ • POS        │          │ • POS        │           │ • View       │
│ • Inventory  │          │ • Scheduling │           │   schedule   │
│ • Expenses   │          │ • Reports    │           │ • Mark       │
│ • Reports    │          │              │           │   complete   │
│ • Users      │          │              │           │              │
│ • Backups    │          │              │           │              │
└──────────────┘          └──────────────┘           └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 4: HANDOVER (YOU + CLIENT)               │
│                           30 Minutes                             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Final Verification      │
                    │  ✓ All services healthy  │
                    │  ✓ All users can login   │
                    │  ✓ Backups scheduled     │
                    │  ✓ Network accessible    │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Documentation Handover  │
                    │  - Installation summary  │
                    │  - User credentials      │
                    │  - Support contacts      │
                    │  - Emergency procedures  │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Schedule Follow-up      │
                    │  - Day 1 check-in        │
                    │  - Week 1 review         │
                    │  - Month 1 review        │
                    └──────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 5: POST-INSTALLATION (YOU)              │
│                           Ongoing                                │
└─────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        │                          │                            │
        ▼                          ▼                            ▼
┌──────────────┐          ┌──────────────┐           ┌──────────────┐
│ Day 1        │          │ Week 1       │           │ Month 1      │
├──────────────┤          ├──────────────┤           ├──────────────┤
│ • Call       │          │ • Visit or   │           │ • Review     │
│   client     │          │   call       │           │   usage      │
│ • Check logs │          │ • Check      │           │ • Test       │
│ • Any issues?│          │   backups    │           │   restore    │
│              │          │ • Review     │           │ • Collect    │
│              │          │   usage      │           │   feedback   │
└──────────────┘          └──────────────┘           └──────────────┘
```

---

## 🛠️ Key Commands Reference

### For YOU (During Installation)

```bash
# 1. Load package
cd /opt/salon-os
tar -xzf salon-os-*.tar.gz
cd salon-os-*

# 2. Install
./scripts/install.sh

# 3. Configure
cp .env.example .env
nano .env

# 4. Start
./scripts/start.sh

# 5. Initialize
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seeds.initial_data

# 6. Verify
docker compose ps
curl http://localhost/api/healthz
```

### For CLIENT (Daily Use)

```bash
# Start system (if stopped)
cd /opt/salon-os
sudo ./scripts/start.sh

# Stop system (for maintenance)
sudo ./scripts/stop.sh

# Create backup
sudo ./scripts/backup.sh

# Check status
sudo docker compose ps

# View logs (if issues)
sudo docker compose logs -f
```

---

## 📦 What You Bring

### Physical Items

- [ ] Laptop with package
- [ ] USB drive with package (backup)
- [ ] Network cable (just in case)
- [ ] Printed documentation
- [ ] Checklist (this document)
- [ ] Business cards
- [ ] Contract/invoice

### Digital Items

- [ ] `salon-os-1.0.0-YYYYMMDD.tar.gz`
- [ ] `CLIENT_INSTALL.md`
- [ ] `HANDOVER_GUIDE.md`
- [ ] Support contact template
- [ ] Installation checklist

---

## 📋 Client Responsibilities

### Before You Arrive

Client should have:
- [ ] Server machine ready (meets requirements)
- [ ] Ubuntu/Debian installed (or ready to install)
- [ ] Internet connection (for Docker installation)
- [ ] Network router accessible
- [ ] Static IP range available
- [ ] Business information ready (name, address, GSTIN)
- [ ] Owner available for full duration
- [ ] Receptionist/staff available for training

### During Installation

Client provides:
- [ ] Server admin access
- [ ] Router admin access (for DNS)
- [ ] Salon business details
- [ ] Choose admin password
- [ ] Test the system
- [ ] Attend training

### After Installation

Client should:
- [ ] Use the system daily
- [ ] Verify backups are running
- [ ] Contact you with any issues
- [ ] Attend follow-up sessions
- [ ] Keep credentials secure

---

## ⏱️ Detailed Time Breakdown

### Installation Day Schedule

**08:00 - 09:00** (1 hour)
- Arrive at site
- Server hardware check
- Install Docker if needed
- Network configuration

**09:00 - 10:00** (1 hour)
- Transfer package
- Load Docker images
- Configure environment

**10:00 - 10:30** (30 mins)
- Start services
- Initialize database
- First login

**10:30 - 11:00** (30 mins)
- Network configuration
- DNS setup
- Multi-machine testing

**11:00 - 11:30** (30 mins)
- Printer setup (if applicable)
- Final verification
- **BREAK**

**11:30 - 13:30** (2 hours)
- Owner training
- System walkthrough
- Feature demonstrations

**13:30 - 14:00** (30 mins)
- **LUNCH BREAK**

**14:00 - 15:00** (1 hour)
- Receptionist training
- Staff training

**15:00 - 15:30** (30 mins)
- Documentation handover
- Final Q&A
- Schedule follow-up
- Handover sign-off

---

## 🚨 Common Issues & Solutions

### Issue: Docker Not Installed

**Solution:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y
```
*Time: 10-15 minutes*

### Issue: Port 80 Already in Use

**Solution:**
```bash
# Check what's using it
sudo lsof -i :80

# Stop the service (e.g., Apache)
sudo systemctl stop apache2
sudo systemctl disable apache2
```
*Time: 5 minutes*

### Issue: Services Won't Start

**Solution:**
```bash
# Check logs
docker compose logs api postgres redis

# Common fix: restart
docker compose down
docker compose up -d
```
*Time: 5-10 minutes*

### Issue: Can't Access from Other Machines

**Solution:**
```bash
# Check firewall
sudo ufw status
sudo ufw allow 80/tcp

# Check network
ping 192.168.1.50  # from client machine
```
*Time: 10 minutes*

---

## ✅ Final Checklist (Before Leaving)

### Technical

- [ ] All containers show "healthy"
- [ ] Can access from server: `http://localhost`
- [ ] Can access from client PC: `http://salon.local`
- [ ] Owner can log in with NEW password
- [ ] Test bill created successfully
- [ ] Test appointment created
- [ ] Test inventory item added
- [ ] Backups scheduled and running
- [ ] Logs show no errors

### Business

- [ ] Owner trained and comfortable
- [ ] Receptionist can use POS
- [ ] Staff can view schedules
- [ ] Client has admin password (written down)
- [ ] Installation summary provided
- [ ] Support contacts provided
- [ ] Emergency procedures explained

### Administrative

- [ ] Contract signed
- [ ] Payment received/scheduled
- [ ] Follow-up scheduled
- [ ] Client satisfied
- [ ] Handover document signed

---

## 📞 Support After Handover

### Your Responsibilities

**Day 1:**
- Call client in evening
- "How is everything going?"
- Check for any issues
- Remote log check

**Week 1:**
- Schedule call or visit
- Review system usage
- Answer questions
- Check backups

**Month 1:**
- Comprehensive review
- Performance check
- Feature optimization
- Feedback collection

### Client Responsibilities

**Call you if:**
- System won't start
- Can't access from network
- Forgot password
- Backups not running
- Any errors or crashes
- Need additional training

**Don't call for:**
- How to use feature (refer to manual first)
- Business decisions
- New feature requests (use email)

---

## 🎯 Success Metrics

**Installation is successful when:**

1. **Technical:**
   - ✅ 99%+ uptime
   - ✅ <200ms response time
   - ✅ Backups running daily
   - ✅ No critical errors

2. **User Adoption:**
   - ✅ Used daily by owner
   - ✅ Used for all transactions
   - ✅ Appointments being scheduled
   - ✅ Reports being generated

3. **Client Satisfaction:**
   - ✅ Client feels confident
   - ✅ Staff trained adequately
   - ✅ Business value realized
   - ✅ Would recommend to others

---

## 📄 Documents Created

After reading this guide, you now have:

1. **HANDOVER_GUIDE.md** - Detailed step-by-step guide (this document)
2. **DEPLOYMENT_FLOW.md** - Visual flow diagram (current document)
3. **CLIENT_INSTALL.md** - Technical installation guide
4. **PRODUCTION_READY.md** - Production readiness checklist
5. **Package script** - `scripts/package-for-distribution.sh`

**You're ready to deploy! 🚀**

---

**Last Updated:** January 2026
**Version:** 1.0.0
**For:** SalonOS Production Deployment
