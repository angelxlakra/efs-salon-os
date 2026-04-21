# Mobile Access Troubleshooting Script for SalonOS
# Run this as Administrator in PowerShell
#
# This script helps diagnose why mobile devices can't connect
# while laptops on the same WiFi can

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script should be run as Administrator for complete diagnostics!"
    Write-Host "Some tests will be skipped. Press Enter to continue anyway..."
    Read-Host
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Mobile Access Troubleshooting" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Get all network interfaces
Write-Host "[1/7] Checking network interfaces..." -ForegroundColor Yellow
$wifiAdapters = Get-NetAdapter | Where-Object {$_.Status -eq "Up" -and $_.InterfaceDescription -like "*Wi-Fi*" -or $_.InterfaceDescription -like "*Wireless*"}
$allActiveAdapters = Get-NetAdapter | Where-Object {$_.Status -eq "Up"}

Write-Host "      Active network adapters:" -ForegroundColor White
foreach ($adapter in $allActiveAdapters) {
    $ip = (Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
    Write-Host "      - $($adapter.Name): $($adapter.InterfaceDescription) [$ip]" -ForegroundColor Gray
}
Write-Host ""

# Test 2: Check WiFi IP and subnet
Write-Host "[2/7] Checking WiFi IP configuration..." -ForegroundColor Yellow
if ($wifiAdapters) {
    foreach ($wifi in $wifiAdapters) {
        $wifiIP = Get-NetIPAddress -InterfaceIndex $wifi.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        Write-Host "      WiFi IP: $($wifiIP.IPAddress)" -ForegroundColor Green
        Write-Host "      Subnet Mask: $($wifiIP.PrefixLength) bits" -ForegroundColor White
        Write-Host "      Interface: $($wifi.InterfaceDescription)" -ForegroundColor White

        # Calculate network range
        $ipParts = $wifiIP.IPAddress -split '\.'
        $networkBase = "$($ipParts[0]).$($ipParts[1]).$($ipParts[2])"
        Write-Host "      Expected mobile IP range: $networkBase.1-254" -ForegroundColor Cyan
    }
} else {
    Write-Host "      WARNING: No active WiFi adapter found" -ForegroundColor Yellow
    Write-Host "      Are you using Ethernet? That's fine, checking all adapters..." -ForegroundColor Gray
}
Write-Host ""

# Test 3: Check Windows Firewall profile for each network
Write-Host "[3/7] Checking Windows Firewall profiles..." -ForegroundColor Yellow
$profiles = Get-NetConnectionProfile
foreach ($profile in $profiles) {
    Write-Host "      Network: $($profile.Name)" -ForegroundColor White
    Write-Host "      Profile: $($profile.NetworkCategory)" -ForegroundColor $(if ($profile.NetworkCategory -eq "Public") {"Red"} else {"Green"})
    Write-Host "      Interface: $($profile.InterfaceAlias)" -ForegroundColor Gray

    if ($profile.NetworkCategory -eq "Public") {
        Write-Host "      WARNING: Public network has stricter firewall rules!" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Test 4: Check if SalonOS firewall rules exist and are enabled for ALL profiles
Write-Host "[4/7] Checking SalonOS firewall rules..." -ForegroundColor Yellow
$httpRule = Get-NetFirewallRule -DisplayName "SalonOS HTTP" -ErrorAction SilentlyContinue
$httpsRule = Get-NetFirewallRule -DisplayName "SalonOS HTTPS" -ErrorAction SilentlyContinue

if ($httpRule -and $httpsRule) {
    Write-Host "      SalonOS HTTP Rule:" -ForegroundColor White
    Write-Host "        Enabled: $($httpRule.Enabled)" -ForegroundColor $(if ($httpRule.Enabled) {"Green"} else {"Red"})
    Write-Host "        Profiles: $($httpRule.Profile)" -ForegroundColor White

    Write-Host "      SalonOS HTTPS Rule:" -ForegroundColor White
    Write-Host "        Enabled: $($httpsRule.Enabled)" -ForegroundColor $(if ($httpsRule.Enabled) {"Green"} else {"Red"})
    Write-Host "        Profiles: $($httpsRule.Profile)" -ForegroundColor White

    # Check if rules apply to current network profile
    $currentProfile = (Get-NetConnectionProfile | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Ethernet*"} | Select-Object -First 1).NetworkCategory
    if ($httpRule.Profile -notlike "*$currentProfile*" -and $httpRule.Profile -ne "Any") {
        Write-Host "      WARNING: Firewall rules may not apply to your current network profile!" -ForegroundColor Red
        Write-Host "      Action: Re-run wsl-port-forward.ps1 to fix" -ForegroundColor Yellow
    }
} else {
    Write-Host "      FAIL: SalonOS firewall rules not found!" -ForegroundColor Red
    Write-Host "      Action: Run wsl-port-forward.ps1 as Administrator" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Check port forwarding rules
Write-Host "[5/7] Checking port forwarding rules..." -ForegroundColor Yellow
$portProxy = netsh interface portproxy show all
if ($portProxy -match "80") {
    Write-Host "      OK: Port forwarding rules exist" -ForegroundColor Green
    netsh interface portproxy show all | Out-String | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
} else {
    Write-Host "      FAIL: No port forwarding rules found!" -ForegroundColor Red
    Write-Host "      Action: Run wsl-port-forward.ps1 as Administrator" -ForegroundColor Yellow
}
Write-Host ""

# Test 6: Check if ports 80 and 443 are listening
Write-Host "[6/7] Checking if ports are listening..." -ForegroundColor Yellow
$listeningPorts = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -eq 80 -or $_.LocalPort -eq 443}
if ($listeningPorts) {
    foreach ($port in $listeningPorts) {
        Write-Host "      OK: Port $($port.LocalPort) is listening on $($port.LocalAddress)" -ForegroundColor Green
    }
} else {
    Write-Host "      WARNING: Ports 80/443 not listening" -ForegroundColor Yellow
    Write-Host "      This might be normal if using port forwarding" -ForegroundColor Gray
}
Write-Host ""

# Test 7: Test actual connectivity
Write-Host "[7/7] Testing connectivity..." -ForegroundColor Yellow
$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.InterfaceAlias -notlike "*WSL*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

Write-Host "      Testing http://$windowsIP ..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "http://$windowsIP" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "      SUCCESS: HTTP is accessible (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "      FAIL: Cannot connect to HTTP" -ForegroundColor Red
    Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Gray
}
Write-Host ""

# Summary and recommendations
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Diagnosis & Recommendations" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "MOBILE DEVICE CHECKLIST:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. VERIFY MOBILE IS ON THE CORRECT NETWORK:" -ForegroundColor White
Write-Host "   - Check WiFi settings on your mobile" -ForegroundColor Gray
Write-Host "   - Is it on the same WiFi network name?" -ForegroundColor Gray
Write-Host "   - Is it on a 'Guest' network? (Guest networks often isolate devices)" -ForegroundColor Gray
if ($wifiIP) {
    $networkBase = ($wifiIP.IPAddress -split '\.')[0..2] -join '.'
    Write-Host "   - Mobile IP should be in range: $networkBase.1-254" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "2. CHECK ROUTER SETTINGS:" -ForegroundColor White
Write-Host "   - Log into your WiFi router admin panel" -ForegroundColor Gray
Write-Host "   - Look for 'AP Isolation' or 'Client Isolation' - DISABLE it" -ForegroundColor Gray
Write-Host "   - Check if mobile is on a separate guest SSID" -ForegroundColor Gray
Write-Host "   - Some routers have '2.4GHz/5GHz isolation' - disable it" -ForegroundColor Gray
Write-Host ""

Write-Host "3. TRY DIFFERENT URLS ON MOBILE:" -ForegroundColor White
Write-Host "   Try accessing these URLs from your mobile browser:" -ForegroundColor Gray
Write-Host "   - http://$windowsIP (HTTP, no HTTPS)" -ForegroundColor Cyan
Write-Host "   - http://$windowsIP:80" -ForegroundColor Cyan
Write-Host "   Mobile browsers may have strict SSL requirements" -ForegroundColor Gray
Write-Host ""

Write-Host "4. CHECK MOBILE BROWSER SETTINGS:" -ForegroundColor White
Write-Host "   - Try a different browser (Chrome, Firefox, Safari)" -ForegroundColor Gray
Write-Host "   - Clear browser cache and cookies" -ForegroundColor Gray
Write-Host "   - Check if mobile has a VPN or firewall app active" -ForegroundColor Gray
Write-Host ""

Write-Host "5. TEST FROM MOBILE USING PING:" -ForegroundColor White
Write-Host "   - Install a network tools app on mobile (e.g., 'Network Analyzer')" -ForegroundColor Gray
Write-Host "   - Try to ping: $windowsIP" -ForegroundColor Cyan
Write-Host "   - If ping fails, it's a network/router isolation issue" -ForegroundColor Gray
Write-Host ""

Write-Host "WINDOWS PC ACTIONS:" -ForegroundColor Yellow
Write-Host ""

$currentProfile = (Get-NetConnectionProfile | Select-Object -First 1).NetworkCategory
if ($currentProfile -eq "Public") {
    Write-Host "ACTION: Change network to Private:" -ForegroundColor Red
    Write-Host "   1. Open Settings → Network & Internet" -ForegroundColor White
    Write-Host "   2. Click on your WiFi/Ethernet connection" -ForegroundColor White
    Write-Host "   3. Under 'Network profile', select 'Private'" -ForegroundColor White
    Write-Host "   4. Re-run wsl-port-forward.ps1" -ForegroundColor White
    Write-Host ""
}

if (-not $portProxy -or $portProxy -notmatch "80") {
    Write-Host "ACTION: Setup port forwarding:" -ForegroundColor Red
    Write-Host "   Run: .\wsl-port-forward.ps1" -ForegroundColor White
    Write-Host ""
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Quick Test Instructions for Mobile" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ON YOUR MOBILE DEVICE:" -ForegroundColor Yellow
Write-Host "  1. Make sure you're on WiFi: $($profiles[0].Name)" -ForegroundColor White
Write-Host "  2. Open mobile browser" -ForegroundColor White
Write-Host "  3. Go to: http://$windowsIP" -ForegroundColor Cyan
Write-Host "  4. If it asks about certificates, click 'Advanced' → 'Proceed'" -ForegroundColor White
Write-Host ""
Write-Host "If still doesn't work:" -ForegroundColor Yellow
Write-Host "  - The issue is likely router-level AP isolation" -ForegroundColor White
Write-Host "  - Access router admin (usually http://192.168.1.1)" -ForegroundColor White
Write-Host "  - Disable 'AP Isolation' or move mobile off guest network" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
