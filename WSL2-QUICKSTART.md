# WSL2 Quick Start - Fix External Access

Your SalonOS works on the Windows PC but not on other devices? Here's the fix.

## The Problem

✅ Works on Windows PC browser
❌ Doesn't work on phones/laptops on WiFi
❌ Doesn't work via Tailscale

**Cause**: WSL2 networking isolation - Windows blocks external traffic to WSL2 by default.

## The Solution (2 minutes)

### Step 1: Open PowerShell as Administrator

Right-click PowerShell → "Run as Administrator"

### Step 2: Navigate to your project

```powershell
cd C:\path\to\efs-salon-os
```

### Step 3: Run the port forwarding script

```powershell
.\wsl-port-forward.ps1
```

The script will show you the URLs to access SalonOS.

### Step 4: Test from another device

From your phone or laptop on the same WiFi:

```
https://192.168.x.x
```

Use the IP address the script showed you.

**Important**: You'll see a security warning (self-signed certificate). Click "Advanced" → "Proceed".

## Make It Permanent (Optional)

The fix above resets when Windows restarts. To make it permanent:

```powershell
# In PowerShell as Administrator
.\setup-auto-forward.ps1
```

This creates an automatic task that runs on Windows startup.

## Troubleshooting

### Still not working?

Run the diagnostic script:

```powershell
.\diagnose-network.ps1
```

This will check everything and tell you exactly what's wrong.

### Need detailed help?

See [WSL2-NETWORK-SETUP.md](WSL2-NETWORK-SETUP.md) for:
- Detailed troubleshooting
- Tailscale configuration
- Network architecture diagrams
- Common error solutions

## Quick Commands Reference

| Task | Command |
|------|---------|
| Fix external access | `.\wsl-port-forward.ps1` (as Admin) |
| Make it permanent | `.\setup-auto-forward.ps1` (as Admin) |
| Diagnose issues | `.\diagnose-network.ps1` |
| Check if running | `wsl docker compose ps` |
| View logs | `wsl docker compose logs` |
| Restart services | `wsl docker compose restart` |

## What the Script Does

1. Finds your WSL2 IP address
2. Sets up port forwarding: Windows ports 80/443 → WSL2 ports 80/443
3. Opens Windows Firewall for external access
4. Shows you the URLs to use

## Files Created

- `wsl-port-forward.ps1` - Main port forwarding script (run after each reboot)
- `setup-auto-forward.ps1` - One-time setup for automatic port forwarding
- `diagnose-network.ps1` - Troubleshooting and diagnostics
- `WSL2-NETWORK-SETUP.md` - Detailed documentation

## Common Questions

**Q: Do I need to run this every time Windows restarts?**
A: Yes, unless you run `setup-auto-forward.ps1` to make it automatic.

**Q: Can I use Tailscale?**
A: Yes! Either:
- Install Tailscale in WSL2 (recommended) - see full guide
- Use Windows Tailscale with port forwarding active

**Q: Is this secure?**
A: The scripts open ports 80 and 443 on your Windows machine. This is standard for a web server. Make sure your Windows PC has a strong password.

**Q: Why do I see a security warning?**
A: You're using self-signed SSL certificates (normal for local deployment). Click "Advanced" → "Proceed" to continue.

**Q: What if I only want LAN access, not Tailscale?**
A: The scripts work for both. If you don't use Tailscale, it just won't be accessible via Tailscale (which is fine).

## Need Help?

1. Run `.\diagnose-network.ps1` to identify the issue
2. Check `WSL2-NETWORK-SETUP.md` for detailed troubleshooting
3. Review Docker logs: `wsl docker compose logs`

---

**TL;DR**: Run `.\wsl-port-forward.ps1` as Administrator. That's it.
