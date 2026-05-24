# SalonOS Auto-Update — Task Scheduler Setup
# Run once on each Windows machine as Administrator:
#   PowerShell -ExecutionPolicy Bypass -File setup-auto-update.ps1
#
# Registers a Task Scheduler job that runs auto-update.sh in WSL
# every 30 minutes starting at system boot.

$TaskName = "SalonOS-AutoUpdate"

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'"
}

# Action: run WSL bash as root
$Action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-u root -e bash /opt/salon-os/scripts/auto-update.sh"

# Trigger: at system boot, then repeat every 30 minutes forever
$BootTrigger = New-ScheduledTaskTrigger -AtStartup

# Apply repetition to the trigger
$RepetitionInterval = [System.TimeSpan]::FromMinutes(30)
$BootTrigger.Repetition.Interval = [System.Xml.XmlConvert]::ToString($RepetitionInterval)
$BootTrigger.Repetition.StopAtDurationEnd = $false

# Settings: run whether user is logged on or not
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable

# Principal: run as SYSTEM
$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $BootTrigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Polls B2 for SalonOS updates every 30 min and auto-deploys"

Write-Host ""
Write-Host "Task '$TaskName' registered successfully."
Write-Host "It will run at next boot, then every 30 minutes."
Write-Host ""
Write-Host "To run it immediately:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To view logs inside WSL:"
Write-Host "  wsl.exe -u root -e tail -f /var/log/salon-os-updater.log"
