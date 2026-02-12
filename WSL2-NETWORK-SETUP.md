# WSL2 Network Setup Guide for SalonOS

## Problem Summary

SalonOS works on the Windows PC browser (localhost, all IPs work), but **cannot be accessed from**:
- ❌ Other devices on the same WiFi network (phones, laptops)
- ❌ Other devices on Tailscale network

## Root Cause

**WSL2 networking isolation**: WSL2 runs in a separate network namespace. By default:
- Windows can reach WSL2 (that's why localhost works on Windows)
- External devices CANNOT reach WSL2 (they can only reach Windows)
- Port forwarding and firewall rules are needed to bridge this gap

## Quick Fix (Manual - Resets on Reboot)

### Step 1: Run the Port Forwarding Script

On your **Windows PC**, open PowerShell **as Administrator**:

```powershell
cd C:\path\to\efs-salon-os
.\wsl-port-forward.ps1
```

This script will:
1. Find your WSL2 IP address
2. Set up port forwarding for ports 80 and 443
3. Configure Windows Firewall to allow external access
4. Show you the URLs to access the app

### Step 2: Test from Another Device

From your phone or another laptop on the same WiFi:

```
https://192.168.x.x
```

Replace `192.168.x.x` with the **Windows IP address** shown by the script.

**Note**: You'll see a security warning about the self-signed certificate. Click "Advanced" → "Proceed" to continue.

## Permanent Fix (Survives Reboots)

To make the port forwarding automatic on Windows startup:

### Step 1: Run the Auto-Setup Script

On your **Windows PC**, open PowerShell **as Administrator**:

```powershell
cd C:\path\to\efs-salon-os
.\setup-auto-forward.ps1
```

This creates a Windows scheduled task that runs the port forwarding automatically when Windows starts.

### Step 2: Verify It's Working

After running the script, restart your Windows PC to test.

After restart:
1. Wait 1-2 minutes for services to start
2. Try accessing from another device: `https://192.168.x.x`

## Tailscale Setup

For Tailscale access from outside your network, you have two options:

### Option A: Install Tailscale in WSL2 (Recommended)

This gives WSL2 its own Tailscale IP that works from anywhere.

**In WSL2 terminal:**

```bash
# Install Tailscale in WSL2
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
sudo tailscale up

# Get your WSL2 Tailscale IP
tailscale ip -4
```

**Access the app:**
```
https://100.x.x.x  (use the Tailscale IP shown above)
```

### Option B: Use Windows Tailscale (Requires Port Forwarding)

If you already have Tailscale on Windows:

1. Run the port forwarding script (see Quick Fix above)
2. Find your Windows Tailscale IP:
   - Open Tailscale on Windows
   - Look for IP address (usually starts with `100.`)
3. Access the app using Windows Tailscale IP:
   ```
   https://100.x.x.x  (Windows Tailscale IP)
   ```

**Important**: This option requires the port forwarding to be active. If it doesn't work:
- Make sure you ran `wsl-port-forward.ps1` as Administrator
- Check Windows Firewall isn't blocking Tailscale
- Try Option A instead (Tailscale in WSL2)

## Troubleshooting

### "Connection refused" or "Can't reach this page"

**Check 1: Are Docker containers running?**

In WSL2 terminal:
```bash
docker compose -f compose.production.yaml ps
```

All services should show "Up (healthy)". If not:
```bash
docker compose -f compose.production.yaml up -d
```

**Check 2: Is port forwarding active?**

In Windows PowerShell (as Administrator):
```powershell
netsh interface portproxy show all
```

You should see rules for ports 80 and 443. If empty:
```powershell
.\wsl-port-forward.ps1
```

**Check 3: Is Windows Firewall blocking?**

In Windows PowerShell (as Administrator):
```powershell
Get-NetFirewallRule -DisplayName "SalonOS*" | Select-Object DisplayName, Enabled, Action
```

Should show two enabled rules. If not:
```powershell
.\wsl-port-forward.ps1
```

### "This site can't provide a secure connection"

This usually means nginx is redirecting to HTTPS but can't complete the SSL handshake.

**Check nginx is running:**

In WSL2 terminal:
```bash
docker logs salon-nginx
```

Look for errors about SSL certificates.

**Quick fix - Use HTTP temporarily:**

If you want to test without SSL complexity, we can create an HTTP-only config. Let me know if you want this.

### Works on Windows but not on other devices

This is the exact problem we're solving. Make sure:

1. ✅ Port forwarding script was run **as Administrator**
2. ✅ You're using the **Windows IP** (not WSL2 IP) from other devices
3. ✅ Windows Firewall rules are active (check with Get-NetFirewallRule)
4. ✅ Your router isn't blocking traffic (unlikely on local WiFi, but check)

### Tailscale works on Windows but not externally

**For Option B (Windows Tailscale):**
- Port forwarding must be active
- Use Windows Tailscale IP, not WSL2 IP
- If it doesn't work, try Option A (Tailscale in WSL2)

**For Option A (WSL2 Tailscale):**
- Make sure you used the WSL2 Tailscale IP (run `tailscale ip -4` in WSL2)
- Check Tailscale is running: `sudo tailscale status` in WSL2

### Port forwarding resets after Windows reboot

This is expected. Two solutions:

1. **Automatic (recommended)**: Run `setup-auto-forward.ps1` once
2. **Manual**: Run `wsl-port-forward.ps1` after each reboot

## Network Architecture

```
┌─────────────────────────────────────────────────┐
│ Windows 10 PC                                   │
│                                                 │
│  Windows IP: 192.168.x.x (LAN)                 │
│  Tailscale IP: 100.x.x.x (if installed)        │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │ Port Forwarding (our scripts)            │  │
│  │  - 0.0.0.0:80 → WSL2:80                  │  │
│  │  - 0.0.0.0:443 → WSL2:443                │  │
│  └──────────────────────────────────────────┘  │
│                    ↓                            │
│  ┌──────────────────────────────────────────┐  │
│  │ WSL2 (Ubuntu)                            │  │
│  │  WSL2 IP: 172.x.x.x (internal)           │  │
│  │  Tailscale IP: 100.y.y.y (if installed)  │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐ │  │
│  │  │ Docker Containers                  │ │  │
│  │  │  - nginx:80,443 (public)          │ │  │
│  │  │  - frontend:3000 (internal)       │ │  │
│  │  │  - api:8000 (internal)            │ │  │
│  │  │  - postgres:5432 (internal)       │ │  │
│  │  │  - redis:6379 (internal)          │ │  │
│  │  └────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Access Methods After Setup

| From | Use This URL | Notes |
|------|-------------|-------|
| Same Windows PC | `https://localhost` | Direct WSL2 access |
| LAN device (phone/laptop) | `https://192.168.x.x` | Windows IP, requires port forwarding |
| Tailscale (Option A) | `https://100.y.y.y` | WSL2 Tailscale IP |
| Tailscale (Option B) | `https://100.x.x.x` | Windows Tailscale IP, requires port forwarding |

## Security Notes

1. **Self-signed SSL certificates**: You'll see security warnings. This is expected for local deployment.
   - Click "Advanced" → "Proceed to site"
   - For production, consider Let's Encrypt or a proper CA certificate

2. **Firewall rules**: The scripts open ports 80 and 443 to ALL networks.
   - If you only want LAN access, modify the script to use `-Profile Private`
   - For Tailscale-only access, consider Tailscale ACLs

3. **Port forwarding security**: Forwarding to 0.0.0.0 means all interfaces.
   - This is necessary for both LAN and Tailscale access
   - Ensure your Windows PC has a strong password
   - Consider using Tailscale ACLs to restrict access

## Getting Help

If you're still having issues:

1. **Check Docker logs:**
   ```bash
   docker compose -f compose.production.yaml logs
   ```

2. **Check connectivity from WSL2:**
   ```bash
   curl -k https://localhost
   ```

3. **Check port forwarding:**
   ```powershell
   netsh interface portproxy show all
   ```

4. **Check firewall:**
   ```powershell
   Get-NetFirewallRule -DisplayName "SalonOS*"
   ```

5. **Get your IPs:**
   ```bash
   # In WSL2 - get WSL2 IP
   hostname -I

   # In WSL2 - get WSL2 Tailscale IP (if installed)
   tailscale ip -4
   ```

   ```powershell
   # In Windows PowerShell - get Windows IP
   ipconfig

   # In Windows - get Windows Tailscale IP (if installed)
   # Check Tailscale system tray icon
   ```

## Summary

**For LAN access:**
1. Run `wsl-port-forward.ps1` as Administrator
2. Access from other devices: `https://192.168.x.x` (Windows IP)
3. Optional: Run `setup-auto-forward.ps1` for automatic startup

**For Tailscale access:**
- **Option A (recommended)**: Install Tailscale in WSL2, use WSL2 Tailscale IP
- **Option B**: Use Windows Tailscale IP with port forwarding active

**After Windows reboot:**
- Manual: Run `wsl-port-forward.ps1` again
- Automatic: If you ran `setup-auto-forward.ps1`, it happens automatically
