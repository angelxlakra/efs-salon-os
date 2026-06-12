#!/bin/bash
#
# SalonOS Auto-Update Setup (WSL / Linux)
# Run once on each machine as root:
#   sudo bash /opt/salon-os/scripts/setup-auto-update.sh
#
# Installs a root crontab entry that polls B2 every 30 minutes.
# WSL: also ensures cron starts at WSL boot via /etc/wsl.conf.

set -euo pipefail

[ "$(id -u)" -ne 0 ] && { echo "ERROR: run as root (sudo bash $0)"; exit 1; }

AUTO_UPDATE_SCRIPT="/opt/salon-os/scripts/auto-update.sh"
[ ! -f "$AUTO_UPDATE_SCRIPT" ] && { echo "ERROR: $AUTO_UPDATE_SCRIPT not found"; exit 1; }

# ─── WSL: ensure cron starts at boot ──────────────────────────────────────────
# Docker keeps WSL alive 24/7, so cron runs reliably even without a logged-in user.

WSL_CONF="/etc/wsl.conf"
if grep -q 'microsoft\|WSL' /proc/version 2>/dev/null; then
    echo "WSL detected — configuring cron autostart in ${WSL_CONF} ..."
    if ! grep -q '^\[boot\]' "$WSL_CONF" 2>/dev/null; then
        printf '\n[boot]\ncommand = service cron start\n' >> "$WSL_CONF"
        echo "Added [boot] section to ${WSL_CONF}"
    elif ! grep -A5 '^\[boot\]' "$WSL_CONF" | grep -q 'service cron start'; then
        sed -i '/^\[boot\]/a command = service cron start' "$WSL_CONF"
        echo "Added cron start command to existing [boot] section"
    else
        echo "cron autostart already configured in ${WSL_CONF}"
    fi
fi

# ─── Start cron now if not running ────────────────────────────────────────────

if ! service cron status &>/dev/null; then
    echo "Starting cron ..."
    service cron start
else
    echo "cron is already running"
fi

# ─── Install crontab entry ────────────────────────────────────────────────────

CRON_JOB="*/30 * * * * bash ${AUTO_UPDATE_SCRIPT} >> /var/log/salon-os-updater.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "auto-update.sh"; then
    echo "Cron entry already exists:"
    crontab -l | grep "auto-update.sh"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron entry installed:"
    echo "  ${CRON_JOB}"
fi

# ─── Ensure log file is writable by root cron ────────────────────────────────

touch /var/log/salon-os-updater.log
chmod 644 /var/log/salon-os-updater.log

echo ""
echo "Done. Auto-update will run every 30 minutes."
echo "Logs: tail -f /var/log/salon-os-updater.log"
echo "Test now: sudo bash ${AUTO_UPDATE_SCRIPT}"
