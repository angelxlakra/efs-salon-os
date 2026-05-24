# 09 — Auto-Update System

SalonOS machines self-update via a Backblaze B2 release bucket.
The developer publishes with one command; machines poll every 30 minutes.

---

## How it works

1. Dev Mac runs `./scripts/package-for-distribution.sh --publish 1.0.38`
2. Tarball + `latest.json` uploaded to `salon-os-releases` B2 bucket
3. Each WSL machine polls `latest.json` every 30 min via Task Scheduler
4. If a newer version is detected: downloads, verifies SHA256, extracts,
   copies `.env`, regenerates HTTPS cert, swaps symlink, restarts Docker

---

## Publishing a new release

```bash
./scripts/package-for-distribution.sh --publish 1.0.38
```

Machines will pick it up within 30 minutes. No further action needed.

---

## One-time machine setup

Do this once per Windows/WSL machine after the initial SalonOS install.

### 1. Add variables to `.env`

Inside WSL, edit `/opt/salon-os/.env` and add:

```
TAILSCALE_IP=100.x.x.x          # Run: tailscale ip -4
B2_PUBLIC_BASE_URL=https://f003.backblazeb2.com/file/salon-os-releases
```

### 2. Register the Task Scheduler job

In a PowerShell terminal **as Administrator**:

```powershell
PowerShell -ExecutionPolicy Bypass -File C:\path\to\setup-auto-update.ps1
```

### 3. Test it manually

```powershell
Start-ScheduledTask -TaskName "SalonOS-AutoUpdate"
# Then check WSL logs:
wsl.exe -u root -e tail -f /var/log/salon-os-updater.log
```

---

## Checking update logs

```bash
# Inside WSL
tail -50 /var/log/salon-os-updater.log

# From Windows PowerShell
wsl.exe -u root -e tail -50 /var/log/salon-os-updater.log
```

---

## Rollback

Each update retains the 3 most recent versioned directories under `/opt/`.

```bash
# List available versions
wsl.exe -u root -e bash -c "ls /opt | grep salon-os-"

# Roll back to a specific version
wsl.exe -u root -e bash /opt/salon-os/scripts/rollback.sh 1.0.36
```

---

## Troubleshooting

**Update not firing:**
- Check Task Scheduler: `Get-ScheduledTask -TaskName SalonOS-AutoUpdate`
- Check WSL is running: `wsl.exe --status`
- Manually trigger: `Start-ScheduledTask -TaskName SalonOS-AutoUpdate`

**SHA256 mismatch in logs:**
- Re-publish: `./scripts/package-for-distribution.sh --publish <version>`
- The previous partial upload may have been corrupted

**docker compose up failed after update:**
- Check logs: `wsl.exe -u root -e bash -c "cd /opt/salon-os && docker compose logs --tail=50"`
- Roll back: `wsl.exe -u root -e bash /opt/salon-os/scripts/rollback.sh <previous>`

**alembic upgrade failed:**
- The new version is running; only the migration step failed
- Run manually: `wsl.exe -u root -e bash -c "cd /opt/salon-os && docker compose exec api alembic upgrade head"`
