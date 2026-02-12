# SalonOS - Quick Start Guide

## Prerequisites

- A dedicated computer/server (recommended: Ubuntu 22.04 or later)
- Static IP address on local network (e.g., 192.168.1.50)
- At least 4GB RAM, 50GB storage
- Docker and Docker Compose installed

## Installation Steps

### 1. Install Docker (if not already installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
```

### 2. Extract and Setup

```bash
# Extract the application
tar -xzf salonos-v1.0.tar.gz
cd salonos-release

# Copy environment template
cp .env.example .env

# Edit .env with your details
nano .env
```

**Important:** Change these values in `.env`:
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `POSTGRES_PASSWORD` - Use a strong password
- `REDIS_PASSWORD` - Use a strong password
- `SALON_NAME` - Your salon's name
- `SALON_ADDRESS` - Your salon's address
- `GSTIN` - Your GST number

### 3. Setup HTTPS (Required for Mobile Camera)

```bash
# Run the HTTPS setup script
./setup-https.sh

# Follow the prompts - enter additional IPs if needed
# Example: If your server might use 192.168.1.50 or 192.168.1.51
```

This will:
- Generate SSL certificates
- Configure nginx for HTTPS
- Output your server IP address

### 4. Start the Application

```bash
# Start all services
docker compose up -d

# Wait 30 seconds for services to start

# Run database migrations
docker compose exec api alembic upgrade head

# Load initial data (roles, default user)
docker compose exec api python -m app.seeds.initial_data
```

### 5. Access the Application

**On Desktop/Server:**
```
https://192.168.1.50  (use your actual IP)
```

**Default Login:**
- Username: `owner`
- Password: `change_me_123`

⚠️ **IMPORTANT:** Change the password immediately after first login!

### 6. Install Certificate on Mobile Devices

For mobile barcode scanning to work, install the SSL certificate on your phones/tablets.

**See HTTPS-SETUP.md for detailed mobile certificate installation instructions.**

Quick steps:
1. Copy certificate: `nginx/ssl/salon.crt`
2. Email it to yourself or transfer via USB
3. Install on device (Settings > Security)
4. Trust the certificate
5. Access `https://192.168.1.50` on mobile

## Verification

### Check Services Status
```bash
docker compose ps

# All services should show "healthy" status
```

### Check Logs
```bash
# View all logs
docker compose logs

# View specific service
docker compose logs api
docker compose logs frontend
docker compose logs nginx
```

### Test API
```bash
curl -k https://localhost/api/healthz
# Should return: {"status":"healthy"}
```

## Common Issues

### Port 80/443 Already in Use
```bash
# Find what's using the port
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # if Apache is running
# or change port in compose.yaml
```

### Services Not Starting
```bash
# Check logs
docker compose logs

# Restart services
docker compose down
docker compose up -d
```

### Database Connection Error
```bash
# Verify credentials in .env match
cat .env | grep POSTGRES_PASSWORD

# Restart postgres
docker compose restart postgres
```

### Camera Not Working on Mobile
1. Ensure you're accessing via HTTPS (not HTTP)
2. Check certificate is installed on device
3. Try a different browser (Chrome recommended)
4. See HTTPS-SETUP.md for detailed troubleshooting

## Maintenance

### Backup Database
```bash
# Automatic backups run nightly at 11:30 PM
# Located in: salon-data/backups/

# Manual backup
docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup.dump
```

### Update Application
```bash
# Stop services
docker compose down

# Extract new version
tar -xzf salonos-v1.1.tar.gz

# Start services
docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head
```

### View Application Logs
```bash
# Real-time logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail 100

# Specific service
docker compose logs -f api
```

## Support

- **Documentation:** See README.md and HTTPS-SETUP.md
- **System Requirements:** See CLAUDE.md
- **Issues:** Check logs with `docker compose logs`

## Security Recommendations

1. **Change default passwords immediately**
2. **Set a strong SECRET_KEY**
3. **Configure firewall:**
   ```bash
   # Allow only local network access
   sudo ufw allow from 192.168.0.0/16 to any port 80
   sudo ufw allow from 192.168.0.0/16 to any port 443
   sudo ufw enable
   ```
4. **Regular backups:** Database backups run automatically, but also backup manually before updates
5. **Keep system updated:**
   ```bash
   sudo apt update && sudo apt upgrade
   docker compose pull  # Update docker images
   ```

## Next Steps

1. Log in and change default password
2. Configure salon settings (name, address, GST)
3. Add staff members
4. Add services and products
5. Set up inventory
6. Install certificate on mobile devices
7. Train staff on using the system

---

**Quick Reference:**
- Application URL: `https://[YOUR-SERVER-IP]`
- API Docs: `https://[YOUR-SERVER-IP]/api/docs`
- Start: `docker compose up -d`
- Stop: `docker compose down`
- Logs: `docker compose logs -f`
- Backup: Auto-backup nightly at 11:30 PM IST

**Certificate Location:** `nginx/ssl/salon.crt` (install on mobile devices)
