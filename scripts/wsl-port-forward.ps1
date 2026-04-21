# WSL2 Port Forwarding Script for SalonOS
# Run this script as Administrator in PowerShell on Windows
#
# This script:
# 1. Finds your WSL2 IP address
# 2. Sets up port forwarding for ports 80 and 443
# 3. Configures Windows Firewall to allow external access
#
# Usage:
#   Right-click PowerShell → Run as Administrator
#   cd path\to\efs-salon-os
#   .\wsl-port-forward.ps1

# Require Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script must be run as Administrator!"
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again."
    pause
    exit
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "SalonOS WSL2 Port Forwarding Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Get WSL2 IP Address
Write-Host "[1/5] Finding WSL2 IP address..." -ForegroundColor Yellow
$wslIP = (wsl hostname -I).Trim()
if ([string]::IsNullOrWhiteSpace($wslIP)) {
    Write-Error "Could not find WSL2 IP address. Is WSL2 running?"
    pause
    exit 1
}
Write-Host "      WSL2 IP: $wslIP" -ForegroundColor Green
Write-Host ""

# Get Windows IP Address (for information)
Write-Host "[2/5] Finding Windows IP address..." -ForegroundColor Yellow
$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.InterfaceAlias -notlike "*WSL*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress
Write-Host "      Windows IP: $windowsIP" -ForegroundColor Green
Write-Host ""

# Remove existing port forwarding rules (if any)
Write-Host "[3/5] Removing old port forwarding rules..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=443 listenaddress=0.0.0.0 2>$null
Write-Host "      Old rules removed" -ForegroundColor Green
Write-Host ""

# Add new port forwarding rules
Write-Host "[4/5] Adding port forwarding rules..." -ForegroundColor Yellow
Write-Host "      Forwarding 0.0.0.0:80 -> $wslIP:80"
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=$wslIP
Write-Host "      Forwarding 0.0.0.0:443 -> $wslIP:443"
netsh interface portproxy add v4tov4 listenport=443 listenaddress=0.0.0.0 connectport=443 connectaddress=$wslIP
Write-Host "      Port forwarding configured" -ForegroundColor Green
Write-Host ""

# Configure Windows Firewall
Write-Host "[5/5] Configuring Windows Firewall..." -ForegroundColor Yellow

# Remove existing rules (if any)
Remove-NetFirewallRule -DisplayName "SalonOS HTTP" -ErrorAction SilentlyContinue 2>$null
Remove-NetFirewallRule -DisplayName "SalonOS HTTPS" -ErrorAction SilentlyContinue 2>$null

# Add new firewall rules for EXTERNAL access
New-NetFirewallRule -DisplayName "SalonOS HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow -Profile Any | Out-Null
New-NetFirewallRule -DisplayName "SalonOS HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow -Profile Any | Out-Null

Write-Host "      Firewall rules configured" -ForegroundColor Green
Write-Host ""

# Display current configuration
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Configuration Complete!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Port Forwarding Rules:" -ForegroundColor Yellow
netsh interface portproxy show all
Write-Host ""

Write-Host "Access your SalonOS application at:" -ForegroundColor Green
Write-Host "  - From this PC:          https://localhost" -ForegroundColor White
Write-Host "  - From LAN devices:      https://$windowsIP" -ForegroundColor White
Write-Host "  - From Tailscale:        https://<your-tailscale-ip>" -ForegroundColor White
Write-Host ""
Write-Host "Note: You may see a security warning about the self-signed certificate." -ForegroundColor Yellow
Write-Host "      This is normal - click 'Advanced' and 'Proceed' to continue." -ForegroundColor Yellow
Write-Host ""

Write-Host "IMPORTANT: This configuration will reset when Windows restarts." -ForegroundColor Red
Write-Host "           Run this script again after each reboot, OR" -ForegroundColor Red
Write-Host "           Set up automatic startup (see instructions below)." -ForegroundColor Red
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Testing Connectivity..." -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Testing if SalonOS is running in WSL2..." -ForegroundColor Yellow
$testResult = wsl curl -s -o /dev/null -w "%{http_code}" -k https://localhost 2>$null
if ($testResult -eq "200" -or $testResult -eq "301" -or $testResult -eq "302") {
    Write-Host "SUCCESS: SalonOS is responding!" -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not reach SalonOS (HTTP $testResult)" -ForegroundColor Red
    Write-Host "         Make sure Docker containers are running:" -ForegroundColor Yellow
    Write-Host "         wsl -d Ubuntu -- docker compose -f compose.production.yaml ps" -ForegroundColor White
}
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
