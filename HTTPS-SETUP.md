# HTTPS Setup Guide for SalonOS

## Why HTTPS is Needed

Modern mobile browsers (Chrome, Safari) **require HTTPS** to access device cameras for security reasons. Without HTTPS, the barcode scanner will not work on mobile devices.

## Quick Setup (5 minutes)

### Step 1: Generate SSL Certificate

Run the setup script:

```bash
./setup-https.sh
```

**For IP-based access (192.168.x.x):**
- The script will auto-detect your current IP and include it in the certificate
- You can add additional IPs when prompted (useful if your IP might change)
- Example: `192.168.1.50,192.168.1.51,192.168.0.100`

This will:
- ✅ Generate a self-signed SSL certificate
- ✅ Include your local IP address in the certificate
- ✅ Update nginx configuration for HTTPS
- ✅ Configure redirect from HTTP to HTTPS

### Step 2: Update Environment Variables

If you haven't already, update your `.env` file:

```bash
# Update CORS_ORIGINS to include HTTPS
CORS_ORIGINS=http://salon.local,https://salon.local,http://localhost,https://localhost
```

### Step 3: Restart Services

```bash
docker compose down
docker compose up -d
```

### Step 4: Trust Certificate on Mobile Devices

The self-signed certificate needs to be trusted on each device that will access the app.

#### For Android Devices

1. **Transfer the certificate:**
   ```bash
   # Connect your Android device via USB
   adb push ./nginx/ssl/salon.crt /sdcard/Download/
   ```

   Or email the file `nginx/ssl/salon.crt` to yourself and open it on your phone.

2. **Install the certificate:**
   - Go to **Settings** > **Security** (or **Biometrics and security**)
   - Scroll down to **Install from device storage** (or **Install a certificate**)
   - Select **CA certificate** (you may see a warning - tap "Install anyway")
   - Browse to **Downloads** and select `salon.crt`
   - Name it "SalonOS Local" when prompted
   - Select usage: **VPN and apps** or **Wi-Fi**

3. **Verify installation:**
   - Go to **Settings** > **Security** > **Trusted credentials**
   - Under **User** tab, you should see "SalonOS Local"

#### For iOS Devices (iPhone/iPad)

1. **Transfer the certificate:**
   - Email `nginx/ssl/salon.crt` to yourself, OR
   - Use AirDrop to send the file from your Mac

2. **Install the profile:**
   - Open the certificate file (tap it in Mail or Files)
   - iOS will say "Profile Downloaded"
   - Go to **Settings** > **General** > **VPN & Device Management**
   - Tap on "SalonOS Local" profile
   - Tap **Install** (enter your passcode if prompted)
   - Tap **Install** again to confirm

3. **Enable full trust:**
   - Go to **Settings** > **General** > **About** > **Certificate Trust Settings**
   - Under "Enable Full Trust for Root Certificates", toggle **ON** for "SalonOS Local"
   - Tap **Continue** on the warning

4. **Verify installation:**
   - The certificate should now show as trusted
   - You can access HTTPS sites without warnings

### Step 5: Access the App

You can now access the app via HTTPS:

- **By domain:** `https://salon.local`
- **By IP:** `https://192.168.1.x` (replace with your server's actual IP)

**For IP-based access (most common for mobile):**
```
Example: https://192.168.1.50
         https://192.168.0.100
```

The certificate includes your IP address, so you won't see any warnings once it's installed on the mobile device.

The barcode scanner will now work on mobile devices! 🎉

## Best Practices for IP-Based Access

### Set a Static IP Address

To avoid regenerating the certificate when your server's IP changes:

1. **Find your server's MAC address:**
   ```bash
   # On Linux
   ip addr show | grep ether

   # On macOS
   ifconfig | grep ether
   ```

2. **Configure your router:**
   - Log into your router's admin panel (usually 192.168.1.1 or 192.168.0.1)
   - Find "DHCP Settings" or "Address Reservation"
   - Add a reservation for your server's MAC address
   - Assign a fixed IP (e.g., 192.168.1.50)

3. **Recommended static IPs:**
   - Use an IP outside your DHCP range
   - Example: If DHCP range is 192.168.1.100-200, use 192.168.1.50
   - Document the IP for easy reference

### Multiple Locations/Networks

If you use the app on different networks (e.g., home and salon):

1. **Generate certificate with multiple IPs:**
   ```bash
   ./setup-https.sh
   # When prompted, enter: 192.168.1.50,192.168.0.50,10.0.0.50
   ```

2. **Or use different ports on each network:**
   - Configure router port forwarding if needed
   - Access via `https://192.168.x.x:443`

### When Your IP Changes

If your server IP changes and you get certificate warnings:

```bash
# Regenerate certificate with new IP
./setup-https.sh

# Restart nginx
docker compose restart nginx

# Re-install certificate on mobile devices (only if IP changed significantly)
# Most of the time, just regenerating is enough
```

## Troubleshooting

### Certificate Not Trusted Error

If you see "Your connection is not private" or similar:

1. Make sure you installed the certificate correctly on your mobile device
2. For iOS, ensure you enabled full trust in Certificate Trust Settings
3. For Android, ensure the certificate is installed under "User" certificates
4. Try clearing browser cache and restarting the browser app

### Camera Still Not Working

1. **Check browser permissions:**
   - Tap the lock icon in the address bar
   - Ensure Camera is set to "Allow"

2. **Try a different browser:**
   - Chrome and Safari work best
   - Firefox on Android may have issues

3. **Verify HTTPS is active:**
   - URL should show `https://` with a lock icon
   - If you see warnings, the certificate isn't trusted yet

4. **Check browser console:**
   - On desktop, open DevTools (F12) and check Console tab
   - Look for security or permission errors

### Port 443 Already in Use

If port 443 is already taken:

```bash
# Find what's using port 443
sudo lsof -i :443

# Stop the conflicting service or change nginx port
# Edit compose.yaml:
ports:
  - "8443:443"  # Use port 8443 instead
```

Then access via `https://salon.local:8443`

### Certificate Expired

Certificates are valid for 365 days. To renew:

```bash
# Backup old certificate (optional)
mv ./nginx/ssl ./nginx/ssl.backup

# Generate new certificate
./setup-https.sh

# Restart nginx
docker compose restart nginx

# Re-install certificate on mobile devices
```

## Security Notes

### Self-Signed vs. Trusted Certificate

This guide uses a **self-signed certificate** which:
- ✅ Works for local network use
- ✅ Free and instant
- ✅ Enables camera access on mobile
- ❌ Shows security warnings until installed
- ❌ Requires manual installation on each device
- ❌ Not suitable for public internet access

For production use on the internet, you would need a trusted certificate from:
- Let's Encrypt (free, automated)
- Commercial CA (costs money)

### Local Network Only

These instructions assume you're using the app on your local network (LAN) only. If you need to access the app from the internet:

1. Use a proper domain name
2. Get a Let's Encrypt certificate
3. Configure your router for port forwarding
4. Consider security implications

## Alternative Solutions

If HTTPS setup is too complex, you can:

1. **Use a USB barcode scanner** instead of mobile camera scanning
2. **Type barcodes manually** in the product fields
3. **Use localhost on Android emulator** (localhost doesn't require HTTPS)

## Help & Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all steps were completed in order
3. Check Docker logs: `docker compose logs nginx`
4. Create an issue on GitHub with error details

---

**Certificate Location:** `./nginx/ssl/salon.crt` and `./nginx/ssl/salon.key`
**Valid For:** 365 days from generation
**Renewal:** Run `./setup-https.sh` again
