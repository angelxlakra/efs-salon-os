# SalonOS Network Diagnostic Script
# Run this to diagnose networking issues
#
# Usage:
#   .\diagnose-network.ps1
#
# No Administrator rights required for this script

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "SalonOS Network Diagnostics" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if WSL2 is running
Write-Host "[1/8] Checking WSL2 status..." -ForegroundColor Yellow
try {
    $wslIP = (wsl hostname -I).Trim()
    if ([string]::IsNullOrWhiteSpace($wslIP)) {
        Write-Host "      FAIL: Could not get WSL2 IP" -ForegroundColor Red
        Write-Host "      Action: Start WSL2 and try again" -ForegroundColor Yellow
    } else {
        Write-Host "      OK: WSL2 is running" -ForegroundColor Green
        Write-Host "      WSL2 IP: $wslIP" -ForegroundColor White
    }
} catch {
    Write-Host "      FAIL: WSL2 is not running or not installed" -ForegroundColor Red
    Write-Host "      Action: Start WSL2 and try again" -ForegroundColor Yellow
}
Write-Host ""

# Test 2: Check Windows IP
Write-Host "[2/8] Checking Windows network..." -ForegroundColor Yellow
$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.InterfaceAlias -notlike "*WSL*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1)
if ($null -eq $windowsIP) {
    Write-Host "      FAIL: No network adapter found" -ForegroundColor Red
    Write-Host "      Action: Check your network connection" -ForegroundColor Yellow
} else {
    Write-Host "      OK: Network adapter found" -ForegroundColor Green
    Write-Host "      Windows IP: $($windowsIP.IPAddress)" -ForegroundColor White
    Write-Host "      Interface: $($windowsIP.InterfaceAlias)" -ForegroundColor White
}
Write-Host ""

# Test 3: Check if Docker is running in WSL2
Write-Host "[3/8] Checking Docker status in WSL2..." -ForegroundColor Yellow
try {
    $dockerRunning = wsl docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      OK: Docker is running" -ForegroundColor Green
    } else {
        Write-Host "      FAIL: Docker is not running" -ForegroundColor Red
        Write-Host "      Action: Start Docker Desktop" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      FAIL: Could not check Docker status" -ForegroundColor Red
    Write-Host "      Action: Start Docker Desktop and ensure WSL2 integration is enabled" -ForegroundColor Yellow
}
Write-Host ""

# Test 4: Check if SalonOS containers are running
Write-Host "[4/8] Checking SalonOS containers..." -ForegroundColor Yellow
try {
    $containers = wsl docker compose -f compose.production.yaml ps --format json 2>&1 | ConvertFrom-Json
    if ($containers) {
        $runningCount = ($containers | Where-Object {$_.State -eq "running"}).Count
        $totalCount = $containers.Count

        if ($runningCount -eq $totalCount -and $runningCount -gt 0) {
            Write-Host "      OK: All $runningCount containers are running" -ForegroundColor Green
        } elseif ($runningCount -gt 0) {
            Write-Host "      WARNING: Only $runningCount of $totalCount containers running" -ForegroundColor Yellow
            Write-Host "      Action: Check logs with: wsl docker compose logs" -ForegroundColor Yellow
        } else {
            Write-Host "      FAIL: No containers are running" -ForegroundColor Red
            Write-Host "      Action: Start services with: wsl docker compose -f compose.production.yaml up -d" -ForegroundColor Yellow
        }
    } else {
        Write-Host "      FAIL: Could not find SalonOS containers" -ForegroundColor Red
        Write-Host "      Action: Start services with: wsl docker compose -f compose.production.yaml up -d" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      WARNING: Could not check container status" -ForegroundColor Yellow
    Write-Host "      This might be normal - checking connectivity instead..." -ForegroundColor Gray
}
Write-Host ""

# Test 5: Check port forwarding rules
Write-Host "[5/8] Checking port forwarding..." -ForegroundColor Yellow
$portProxy = netsh interface portproxy show all
if ($portProxy -match "80") {
    Write-Host "      OK: Port forwarding is configured" -ForegroundColor Green
    Write-Host "      Current rules:" -ForegroundColor White
    netsh interface portproxy show all | Write-Host -ForegroundColor Gray
} else {
    Write-Host "      FAIL: Port forwarding is NOT configured" -ForegroundColor Red
    Write-Host "      Action: Run wsl-port-forward.ps1 as Administrator" -ForegroundColor Yellow
}
Write-Host ""

# Test 6: Check Windows Firewall rules
Write-Host "[6/8] Checking Windows Firewall..." -ForegroundColor Yellow
$firewallRules = Get-NetFirewallRule -DisplayName "SalonOS*" -ErrorAction SilentlyContinue
if ($firewallRules) {
    $enabledRules = ($firewallRules | Where-Object {$_.Enabled -eq $true}).Count
    if ($enabledRules -ge 2) {
        Write-Host "      OK: Firewall rules are configured and enabled" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: Firewall rules exist but may be disabled" -ForegroundColor Yellow
        Write-Host "      Action: Run wsl-port-forward.ps1 as Administrator" -ForegroundColor Yellow
    }
} else {
    Write-Host "      FAIL: Firewall rules are NOT configured" -ForegroundColor Red
    Write-Host "      Action: Run wsl-port-forward.ps1 as Administrator" -ForegroundColor Yellow
}
Write-Host ""

# Test 7: Test connectivity from WSL2
Write-Host "[7/8] Testing connectivity from WSL2..." -ForegroundColor Yellow
try {
    $httpCode = wsl curl -k -s -o /dev/null -w "%{http_code}" https://localhost 2>&1
    if ($httpCode -match "200|301|302") {
        Write-Host "      OK: SalonOS is responding in WSL2 (HTTP $httpCode)" -ForegroundColor Green
    } else {
        Write-Host "      FAIL: SalonOS is not responding (HTTP $httpCode)" -ForegroundColor Red
        Write-Host "      Action: Check Docker logs with: wsl docker compose logs" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      WARNING: Could not test connectivity" -ForegroundColor Yellow
}
Write-Host ""

# Test 8: Check Tailscale
Write-Host "[8/8] Checking Tailscale..." -ForegroundColor Yellow
$tailscaleWindows = Get-Process "tailscaled" -ErrorAction SilentlyContinue
if ($tailscaleWindows) {
    Write-Host "      OK: Tailscale is running on Windows" -ForegroundColor Green
} else {
    Write-Host "      INFO: Tailscale not detected on Windows" -ForegroundColor Gray
}

try {
    $tailscaleWSL = wsl tailscale status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      OK: Tailscale is running in WSL2" -ForegroundColor Green
        $tailscaleIP = wsl tailscale ip -4 2>&1
        if ($tailscaleIP -match "\d+\.\d+\.\d+\.\d+") {
            Write-Host "      WSL2 Tailscale IP: $tailscaleIP" -ForegroundColor White
        }
    }
} catch {
    Write-Host "      INFO: Tailscale not detected in WSL2" -ForegroundColor Gray
}
Write-Host ""

# Summary
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Summary & Next Steps" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Determine what needs to be fixed
$needsPortForward = $portProxy -notmatch "80"
$needsFirewall = -not $firewallRules
$needsDocker = $false

Write-Host "Based on the diagnostics above:" -ForegroundColor Yellow
Write-Host ""

if ($needsPortForward -or $needsFirewall) {
    Write-Host "ACTION REQUIRED:" -ForegroundColor Red
    Write-Host "  1. Open PowerShell as Administrator" -ForegroundColor White
    Write-Host "  2. Run: .\wsl-port-forward.ps1" -ForegroundColor White
    Write-Host "  3. Test access from another device" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "CONFIGURATION:" -ForegroundColor Green
    Write-Host "  Port forwarding and firewall appear to be configured correctly!" -ForegroundColor White
    Write-Host ""
}

Write-Host "ACCESS URLS:" -ForegroundColor Yellow
if ($windowsIP) {
    Write-Host "  From this PC:       https://localhost" -ForegroundColor White
    Write-Host "  From LAN devices:   https://$($windowsIP.IPAddress)" -ForegroundColor White
}
Write-Host "  From Tailscale:     https://<tailscale-ip>" -ForegroundColor White
Write-Host "                      (run 'tailscale ip -4' in WSL2 or check Windows Tailscale app)" -ForegroundColor Gray
Write-Host ""

Write-Host "TROUBLESHOOTING:" -ForegroundColor Yellow
Write-Host "  - If it doesn't work after port forwarding:" -ForegroundColor White
Write-Host "    Check that Docker containers are running:" -ForegroundColor White
Write-Host "    wsl docker compose -f compose.production.yaml ps" -ForegroundColor Gray
Write-Host ""
Write-Host "  - For detailed setup instructions:" -ForegroundColor White
Write-Host "    See WSL2-NETWORK-SETUP.md" -ForegroundColor Gray
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
