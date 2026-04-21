# Setup Automatic Port Forwarding on Windows Startup
# Run this script ONCE as Administrator
#
# This will create a scheduled task that runs the port forwarding script
# automatically when Windows starts
#
# Usage:
#   Right-click PowerShell → Run as Administrator
#   cd path\to\efs-salon-os
#   .\setup-auto-forward.ps1

# Require Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script must be run as Administrator!"
    pause
    exit
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "SalonOS Auto-Start Configuration" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$portForwardScript = Join-Path $scriptDir "wsl-port-forward.ps1"

# Verify the port forward script exists
if (-not (Test-Path $portForwardScript)) {
    Write-Error "Could not find wsl-port-forward.ps1 in $scriptDir"
    Write-Host "Make sure both scripts are in the same folder."
    pause
    exit 1
}

Write-Host "Found port forwarding script at:" -ForegroundColor Green
Write-Host "  $portForwardScript" -ForegroundColor White
Write-Host ""

# Create a wrapper script that doesn't show a window
$wrapperScript = Join-Path $scriptDir "wsl-port-forward-silent.ps1"
$wrapperContent = @"
# Silent wrapper for wsl-port-forward.ps1
# This runs the main script without showing a window

# Wait for WSL to be ready
Start-Sleep -Seconds 10

# Run the main script
& "$portForwardScript" *> `$null
"@

Set-Content -Path $wrapperScript -Value $wrapperContent
Write-Host "Created silent wrapper script" -ForegroundColor Green
Write-Host ""

# Remove existing task if it exists
Write-Host "Removing old scheduled task (if any)..." -ForegroundColor Yellow
Unregister-ScheduledTask -TaskName "SalonOS-PortForward" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host ""

# Create scheduled task
Write-Host "Creating scheduled task..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$wrapperScript`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "SalonOS-PortForward" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Automatically forward ports for SalonOS WSL2" | Out-Null

Write-Host "Scheduled task created successfully!" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Configuration Complete!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The port forwarding will now run automatically:" -ForegroundColor Green
Write-Host "  - When Windows starts" -ForegroundColor White
Write-Host "  - 10 seconds after boot (to allow WSL2 to initialize)" -ForegroundColor White
Write-Host ""
Write-Host "You can also run the forwarding manually anytime:" -ForegroundColor Yellow
Write-Host "  .\wsl-port-forward.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To verify the task was created:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName 'SalonOS-PortForward'" -ForegroundColor White
Write-Host ""
Write-Host "To remove auto-start (if needed):" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName 'SalonOS-PortForward'" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
