# Auto-Update System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate Aasan release distribution so publishing one command on the dev Mac causes both WSL production machines to self-update within 30 minutes.

**Architecture:** A `--publish` flag on the existing packaging script uploads the tarball + a `latest.json` manifest to a public Backblaze B2 bucket. Each Windows machine runs a WSL bash poller every 30 minutes via Task Scheduler: it fetches the manifest, compares to its installed version, and if newer downloads → extracts → swaps symlink → restarts Docker.

**Tech Stack:** Bash (macOS + WSL/Linux), PowerShell (Windows Task Scheduler), Backblaze B2 CLI (`b2`), `curl`, `openssl`, `docker compose`, `sha256sum`/`shasum`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/package-for-distribution.sh` | Modify | Add `--publish` flag: upload tarball + `latest.json` to B2 |
| `scripts/setup-https.sh` | Modify | Add `--auto` flag: read `TAILSCALE_IP` from `.env`, no prompts |
| `scripts/auto-update.sh` | Create | WSL poller + deployer; runs every 30 min |
| `scripts/rollback.sh` | Create | One-command rollback to any retained version |
| `scripts/setup-auto-update.ps1` | Create | One-time Windows Task Scheduler registration |
| `env.txt` | Modify | Add `TAILSCALE_IP` and `B2_PUBLIC_BASE_URL` variables |
| `docs/deployment/09-auto-update.md` | Create | Setup + ops guide |

---

## Task 1: Install b2 CLI and create B2 releases bucket

**Files:**
- No code files; one-time setup on dev Mac

- [ ] **Step 1: Install b2 CLI on the dev Mac**

```bash
pip3 install b2
# Verify
b2 version
```

Expected: prints `b2 command line tool, version 4.x.x`

- [ ] **Step 2: Authenticate b2 with your Backblaze account**

```bash
b2 account authorize
```

Follow prompts: enter your Application Key ID and Application Key from the Backblaze web console (the same account used for database backups).

- [ ] **Step 3: Create the releases bucket**

```bash
b2 bucket create aasan-releases allPublic
```

Expected output includes `"bucketId"` and `"bucketType": "allPublic"`.

- [ ] **Step 4: Note your bucket's public base URL**

In the Backblaze web console → Buckets → `aasan-releases` → Bucket Settings → find the "Friendly URL" or use:

```
https://f003.backblazeb2.com/file/aasan-releases/
```

The exact subdomain (f003, f004, etc.) depends on your account region. Copy the full base URL — you will need it in Task 3 and Task 5.

- [ ] **Step 5: Verify upload works**

```bash
echo "test" > /tmp/test.txt
b2 file upload aasan-releases /tmp/test.txt test.txt
curl https://f003.backblazeb2.com/file/aasan-releases/test.txt
b2 file delete-unfinished-large-files aasan-releases
b2 rm b2://aasan-releases/test.txt
```

Expected: `curl` returns `test`, then cleanup succeeds.

- [ ] **Step 6: Commit (no code changes, just log this step)**

```bash
git commit --allow-empty -m "chore: b2 releases bucket created (aasan-releases)"
```

---

## Task 2: Add `--auto` flag to `setup-https.sh`

**Files:**
- Modify: `scripts/setup-https.sh`

The current script has one interactive prompt (`read -p "Enter additional IPs..."`). In `--auto` mode we skip it and instead read `TAILSCALE_IP` from `.env` in the current directory.

- [ ] **Step 1: Verify current interactive behavior (baseline)**

```bash
bash -n scripts/setup-https.sh
echo "Syntax OK"
```

- [ ] **Step 2: Add `--auto` flag parsing and TAILSCALE_IP support**

Replace the top of `scripts/setup-https.sh` (the section from `set -e` through the `read -p` line) with:

```bash
#!/bin/bash

# Setup HTTPS for Aasan Local Server
# Usage: ./setup-https.sh [--auto]
#   --auto: non-interactive, reads TAILSCALE_IP from .env in current directory

set -e

AUTO_MODE=false
if [[ "${1:-}" == "--auto" ]]; then
    AUTO_MODE=true
fi

if [[ "$AUTO_MODE" == "false" ]]; then
    echo "========================================="
    echo "Aasan HTTPS Setup"
    echo "========================================="
    echo ""
fi

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
else
    LOCAL_IP=$(hostname -I | awk '{print $1}')
fi

if [[ "$AUTO_MODE" == "false" ]]; then
    echo "Detected local IP: $LOCAL_IP"
    echo ""
fi

# Build Subject Alternative Names
SAN="DNS:localhost,IP:127.0.0.1"

if [ -n "$LOCAL_IP" ]; then
    SAN="$SAN,IP:$LOCAL_IP"
fi

if [[ "$AUTO_MODE" == "true" ]]; then
    # Source .env from current directory to get TAILSCALE_IP
    if [ -f ".env" ]; then
        # shellcheck disable=SC1091
        set -a; source .env; set +a
    fi
    if [ -n "${TAILSCALE_IP:-}" ]; then
        SAN="$SAN,IP:$TAILSCALE_IP"
    fi
    ADDITIONAL_IPS=""
else
    echo "Do you want to add additional IP addresses to the certificate?"
    echo "(Useful if you have multiple network interfaces or want to support IP range)"
    echo ""
    read -p "Enter additional IPs (comma-separated, or press Enter to skip): " ADDITIONAL_IPS
fi

# Add additional IPs if provided (interactive mode only)
if [ -n "$ADDITIONAL_IPS" ]; then
    IFS=',' read -ra IPS <<< "$ADDITIONAL_IPS"
    for ip in "${IPS[@]}"; do
        ip=$(echo "$ip" | xargs)
        if [ -n "$ip" ]; then
            SAN="$SAN,IP:$ip"
        fi
    done
fi

if [[ "$AUTO_MODE" == "false" ]]; then
    echo ""
    echo "Certificate will be valid for:"
    echo "$SAN" | tr ',' '\n' | sed 's/^/  - /'
    echo ""
fi
```

The remainder of the file (from `# Create SSL directory` onwards) stays unchanged.

- [ ] **Step 3: Check syntax**

```bash
bash -n scripts/setup-https.sh
echo "Syntax OK"
```

- [ ] **Step 4: Test auto mode doesn't prompt**

```bash
# Run with --auto; should complete without waiting for input
# Create a minimal .env for the test
echo "TAILSCALE_IP=100.99.99.99" > /tmp/test-auto-env
cd /tmp && mkdir -p test-https/nginx && cd test-https
cp /tmp/test-auto-env .env
bash /Users/angelxlakra/dev/efs-salon/efs-salon-os/scripts/setup-https.sh --auto
# Verify cert was created
openssl x509 -in nginx/ssl/salon.crt -text -noout | grep "100.99.99.99"
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
```

Expected: `IP Address:100.99.99.99` appears in the cert output, no interactive prompts.

- [ ] **Step 5: Commit**

```bash
git add scripts/setup-https.sh
git commit -m "feat: add --auto flag to setup-https.sh for non-interactive cert generation"
```

---

## Task 3: Add `TAILSCALE_IP` and `B2_PUBLIC_BASE_URL` to `env.txt`

**Files:**
- Modify: `env.txt`

- [ ] **Step 1: Add auto-update section to `env.txt`**

Open `env.txt` and append at the end:

```bash
# =============================================================================
# AUTO-UPDATE CONFIGURATION (set once per machine)
# =============================================================================

# Stable Tailscale IP of THIS machine (100.x.x.x)
# Find it with: tailscale ip -4
# Used by setup-https.sh --auto for the SSL certificate SAN
TAILSCALE_IP=100.x.x.x

# Public base URL for the Backblaze B2 releases bucket
# Example: https://f003.backblazeb2.com/file/aasan-releases
# Find it in the B2 console under Bucket Settings > Friendly URL
B2_PUBLIC_BASE_URL=https://f003.backblazeb2.com/file/aasan-releases
```

- [ ] **Step 2: Commit**

```bash
git add env.txt
git commit -m "docs: add TAILSCALE_IP and B2_PUBLIC_BASE_URL to env.txt"
```

---

## Task 4: Add `--publish` flag to `package-for-distribution.sh`

**Files:**
- Modify: `scripts/package-for-distribution.sh`

The publish step runs *after* `create_tarball` succeeds. Without `--publish`, the script behaves exactly as before.

- [ ] **Step 1: Replace the argument parsing block at the top of `package-for-distribution.sh`**

The current line is:
```bash
VERSION="${1:-latest}"
```

Replace it with:

```bash
VERSION="latest"
PUBLISH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --publish)
            PUBLISH=true
            shift
            ;;
        *)
            VERSION="$1"
            shift
            ;;
    esac
done
```

- [ ] **Step 2: Add `publish_to_b2` function**

After the `cleanup` function (around line 336) and before the `main` function, add:

```bash
publish_to_b2() {
    if [[ "$PUBLISH" != "true" ]]; then
        return 0
    fi

    local tarball="${DIST_DIR}/${PACKAGE_NAME}.tar.gz"

    log_info "Publishing to Backblaze B2..."

    # Verify b2 CLI is available
    if ! command -v b2 &> /dev/null; then
        log_error "b2 CLI not found. Install with: pip3 install b2"
        exit 1
    fi

    # Compute SHA256 (macOS uses shasum, Linux uses sha256sum)
    local sha256
    if command -v shasum &> /dev/null; then
        sha256=$(shasum -a 256 "$tarball" | awk '{print $1}')
    else
        sha256=$(sha256sum "$tarball" | awk '{print $1}')
    fi

    log_info "SHA256: $sha256"

    # Upload tarball
    log_info "Uploading ${PACKAGE_NAME}.tar.gz ..."
    b2 file upload aasan-releases "$tarball" "${PACKAGE_NAME}.tar.gz"

    # Write and upload latest.json
    local tmp_json
    tmp_json=$(mktemp /tmp/latest.XXXXXX.json)
    printf '{"version":"%s","filename":"%s.tar.gz","sha256":"%s","released_at":"%s"}' \
        "${VERSION}" "${PACKAGE_NAME}" "${sha256}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        > "$tmp_json"

    log_info "Uploading latest.json ..."
    b2 file upload aasan-releases "$tmp_json" latest.json
    rm "$tmp_json"

    log_success "Published ${VERSION} to B2. Machines will pick it up within 30 min."
    echo ""
    echo "  latest.json SHA256:  $sha256"
    echo "  Tarball:             ${PACKAGE_NAME}.tar.gz"
}
```

- [ ] **Step 3: Call `publish_to_b2` inside `main()`**

Inside the `main()` function, add `publish_to_b2` after `print_summary`:

```bash
    print_summary
    publish_to_b2
    cleanup
```

(Move `cleanup` to after `publish_to_b2` so temp files aren't removed before upload.)

- [ ] **Step 4: Check syntax**

```bash
bash -n scripts/package-for-distribution.sh
echo "Syntax OK"
```

- [ ] **Step 5: Dry-run test (without actual B2 upload)**

```bash
# Run without --publish to confirm existing behavior unchanged
./scripts/package-for-distribution.sh 1.0.37-test 2>&1 | tail -10
# Should succeed and NOT mention B2
```

Expected: packaging completes, no B2 output.

- [ ] **Step 6: Commit**

```bash
git add scripts/package-for-distribution.sh
git commit -m "feat: add --publish flag to package-for-distribution.sh — uploads to B2"
```

---

## Task 5: Create `scripts/auto-update.sh`

**Files:**
- Create: `scripts/auto-update.sh`

This is the core poller/deployer that runs in WSL as root every 30 minutes.

- [ ] **Step 1: Create `scripts/auto-update.sh`**

```bash
#!/bin/bash
#
# Aasan Auto-Update Script
# Runs every 30 min via Windows Task Scheduler → wsl.exe
# Checks B2 for a newer version; deploys if found.
#
# Requires (set once in /opt/aasan/.env):
#   B2_PUBLIC_BASE_URL=https://f003.backblazeb2.com/file/aasan-releases
#   TAILSCALE_IP=100.x.x.x

set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────

INSTALL_ROOT="/opt"
INSTALL_LINK="${INSTALL_ROOT}/aasan"
VERSION_FILE="${INSTALL_ROOT}/aasan-current-version"
LOG_FILE="/var/log/aasan-updater.log"
TMP_DIR="/tmp"

# ─── Helpers ──────────────────────────────────────────────────────────────────

log() {
    local level="$1"; shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') [${level}] $*" | tee -a "$LOG_FILE"
}

die() {
    log "ERROR" "$*"
    exit 1
}

# ─── Load config from current install's .env ──────────────────────────────────

if [ ! -L "$INSTALL_LINK" ]; then
    die "No symlink at $INSTALL_LINK — run initial install first"
fi

ENV_FILE="${INSTALL_LINK}/.env"
if [ ! -f "$ENV_FILE" ]; then
    die ".env not found at $ENV_FILE"
fi

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

: "${B2_PUBLIC_BASE_URL:?B2_PUBLIC_BASE_URL not set in .env}"

# ─── Check latest version ─────────────────────────────────────────────────────

LATEST_JSON=$(curl -fsSL "${B2_PUBLIC_BASE_URL}/latest.json") \
    || die "Failed to fetch latest.json from B2"

LATEST_VERSION=$(echo "$LATEST_JSON" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
LATEST_FILENAME=$(echo "$LATEST_JSON" | grep -o '"filename":"[^"]*"' | cut -d'"' -f4)
LATEST_SHA256=$(echo "$LATEST_JSON"  | grep -o '"sha256":"[^"]*"'   | cut -d'"' -f4)

CURRENT_VERSION=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE")
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    log "INFO" "already at ${LATEST_VERSION}, nothing to do"
    exit 0
fi

log "INFO" "new version ${LATEST_VERSION} detected (current: ${CURRENT_VERSION:-none}), starting update"

# ─── Download ─────────────────────────────────────────────────────────────────

START_TIME=$(date +%s)
TMP_TARBALL="${TMP_DIR}/${LATEST_FILENAME}"

log "INFO" "downloading ${LATEST_FILENAME} ..."
curl -fsSL -o "$TMP_TARBALL" "${B2_PUBLIC_BASE_URL}/${LATEST_FILENAME}" \
    || die "Download failed"

# ─── Verify SHA256 ────────────────────────────────────────────────────────────

ACTUAL_SHA256=$(sha256sum "$TMP_TARBALL" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$LATEST_SHA256" ]; then
    rm -f "$TMP_TARBALL"
    die "SHA256 mismatch — expected ${LATEST_SHA256}, got ${ACTUAL_SHA256}. Aborting."
fi

log "INFO" "SHA256 verified OK"

# ─── Extract ──────────────────────────────────────────────────────────────────

# Tarball contains a directory named like aasan-1.0.38-20260524
TARBALL_INNER_DIR=$(tar -tzf "$TMP_TARBALL" | head -1 | cut -d'/' -f1)
NEW_INSTALL_DIR="${INSTALL_ROOT}/${TARBALL_INNER_DIR}"

if [ -d "$NEW_INSTALL_DIR" ]; then
    log "INFO" "removing existing dir ${NEW_INSTALL_DIR}"
    rm -rf "$NEW_INSTALL_DIR"
fi

log "INFO" "extracting to ${NEW_INSTALL_DIR} ..."
tar -xzf "$TMP_TARBALL" -C "$INSTALL_ROOT"
chmod +x "${NEW_INSTALL_DIR}/scripts/"*.sh 2>/dev/null || true

# ─── Copy .env ────────────────────────────────────────────────────────────────

cp "${INSTALL_LINK}/.env" "${NEW_INSTALL_DIR}/.env"
log "INFO" ".env copied"

# ─── Generate HTTPS cert ──────────────────────────────────────────────────────

log "INFO" "running setup-https.sh --auto ..."
cd "$NEW_INSTALL_DIR"
bash scripts/setup-https.sh --auto \
    || die "setup-https.sh --auto failed"
cd /

# ─── Stop old containers ──────────────────────────────────────────────────────

log "INFO" "stopping current containers ..."
cd "$INSTALL_LINK"
docker compose down || true

# ─── Atomic symlink swap ──────────────────────────────────────────────────────

ln -sfn "$NEW_INSTALL_DIR" "$INSTALL_LINK"
echo "$LATEST_VERSION" > "$VERSION_FILE"
log "INFO" "symlink updated → ${NEW_INSTALL_DIR}"

# ─── Start new version ────────────────────────────────────────────────────────

log "INFO" "starting new containers ..."
cd "$INSTALL_LINK"
docker compose up -d \
    || die "docker compose up failed — run: bash ${INSTALL_LINK}/scripts/rollback.sh <previous-version>"

# ─── Run migrations ───────────────────────────────────────────────────────────

log "INFO" "running database migrations ..."
docker compose exec -T api alembic upgrade head \
    || die "alembic upgrade failed — check logs"

# ─── Cleanup ──────────────────────────────────────────────────────────────────

rm -f "$TMP_TARBALL"
log "INFO" "cleaned up temp tarball"

# ─── Prune old versions (keep newest 3) ───────────────────────────────────────

mapfile -t OLD_DIRS < <(
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "aasan-*" \
    | sort -V | head -n -3
)
for old_dir in "${OLD_DIRS[@]}"; do
    log "INFO" "pruning old version: ${old_dir}"
    rm -rf "$old_dir"
done

# ─── Done ─────────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log "INFO" "update to ${LATEST_VERSION} complete in ${ELAPSED}s"
```

- [ ] **Step 2: Make executable and check syntax**

```bash
chmod +x scripts/auto-update.sh
bash -n scripts/auto-update.sh
echo "Syntax OK"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/auto-update.sh
git commit -m "feat: add auto-update.sh — WSL poller/deployer for B2 releases"
```

---

## Task 6: Create `scripts/rollback.sh`

**Files:**
- Create: `scripts/rollback.sh`

- [ ] **Step 1: Create `scripts/rollback.sh`**

```bash
#!/bin/bash
#
# Aasan Rollback Script
# Usage: bash /opt/aasan/scripts/rollback.sh 1.0.36
#
# Rolls back to a previously installed version (must still exist under /opt/)

set -euo pipefail

INSTALL_ROOT="/opt"
INSTALL_LINK="${INSTALL_ROOT}/aasan"
VERSION_FILE="${INSTALL_ROOT}/aasan-current-version"

TARGET_VERSION="${1:-}"
if [ -z "$TARGET_VERSION" ]; then
    echo "Usage: $0 <version>"
    echo ""
    echo "Available versions:"
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "aasan-*" | sort -V | sed 's|.*/||'
    exit 1
fi

TARGET_DIR="${INSTALL_ROOT}/aasan-${TARGET_VERSION}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: ${TARGET_DIR} does not exist"
    echo ""
    echo "Available versions:"
    find "$INSTALL_ROOT" -maxdepth 1 -type d -name "aasan-*" | sort -V | sed 's|.*/||'
    exit 1
fi

echo "Rolling back to ${TARGET_VERSION} ..."

cd "$INSTALL_LINK"
docker compose down || true

ln -sfn "$TARGET_DIR" "$INSTALL_LINK"
echo "$TARGET_VERSION" > "$VERSION_FILE"

cd "$INSTALL_LINK"
docker compose up -d

echo "Rolled back to ${TARGET_VERSION}"
echo "Run: docker compose logs -f   to watch startup"
```

- [ ] **Step 2: Make executable and check syntax**

```bash
chmod +x scripts/rollback.sh
bash -n scripts/rollback.sh
echo "Syntax OK"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/rollback.sh
git commit -m "feat: add rollback.sh — one-command version rollback"
```

---

## Task 7: Create `scripts/setup-auto-update.ps1`

**Files:**
- Create: `scripts/setup-auto-update.ps1`

Run this PowerShell script once on each Windows machine (as Administrator) to register the Task Scheduler job.

- [ ] **Step 1: Create `scripts/setup-auto-update.ps1`**

```powershell
# Aasan Auto-Update — Task Scheduler Setup
# Run once on each Windows machine as Administrator:
#   PowerShell -ExecutionPolicy Bypass -File setup-auto-update.ps1
#
# Registers a Task Scheduler job that runs auto-update.sh in WSL
# every 30 minutes starting at system boot.

$TaskName = "Aasan-AutoUpdate"

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'"
}

# Action: run WSL bash as root
$Action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-u root -e bash /opt/aasan/scripts/auto-update.sh"

# Trigger: at system boot, then repeat every 30 minutes forever
$BootTrigger = New-ScheduledTaskTrigger -AtStartup

# RepetitionInterval requires a TimeSpan
$RepetitionInterval = New-TimeSpan -Minutes 30

# Apply repetition to the trigger
$BootTrigger.Repetition = New-Object `
    Microsoft.Management.Infrastructure.CimInstance `
    "MSFT_TaskRepetitionPattern", "Root/Microsoft/Windows/TaskScheduler"
$BootTrigger.Repetition.Interval = "PT30M"
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
    -Description "Polls B2 for Aasan updates every 30 min and auto-deploys"

Write-Host ""
Write-Host "Task '$TaskName' registered successfully."
Write-Host "It will run at next boot, then every 30 minutes."
Write-Host ""
Write-Host "To run it immediately:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To view logs inside WSL:"
Write-Host "  wsl.exe -u root -e tail -f /var/log/aasan-updater.log"
```

- [ ] **Step 2: Commit**

```bash
git add scripts/setup-auto-update.ps1
git commit -m "feat: add setup-auto-update.ps1 — registers WSL updater in Task Scheduler"
```

---

## Task 8: Create `docs/deployment/09-auto-update.md`

**Files:**
- Create: `docs/deployment/09-auto-update.md`

- [ ] **Step 1: Create ops guide**

```markdown
# 09 — Auto-Update System

Aasan machines self-update via a Backblaze B2 release bucket.
The developer publishes with one command; machines poll every 30 minutes.

---

## How it works

1. Dev Mac runs `./scripts/package-for-distribution.sh --publish 1.0.38`
2. Tarball + `latest.json` uploaded to `aasan-releases` B2 bucket
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

Do this once per Windows/WSL machine after the initial Aasan install.

### 1. Add variables to `.env`

Inside WSL, edit `/opt/aasan/.env` and add:

```
TAILSCALE_IP=100.x.x.x          # Run: tailscale ip -4
B2_PUBLIC_BASE_URL=https://f003.backblazeb2.com/file/aasan-releases
```

### 2. Register the Task Scheduler job

In a PowerShell terminal **as Administrator**:

```powershell
PowerShell -ExecutionPolicy Bypass -File C:\path\to\setup-auto-update.ps1
```

### 3. Test it manually

```powershell
Start-ScheduledTask -TaskName "Aasan-AutoUpdate"
# Then check WSL logs:
wsl.exe -u root -e tail -f /var/log/aasan-updater.log
```

---

## Checking update logs

```bash
# Inside WSL
tail -50 /var/log/aasan-updater.log

# From Windows PowerShell
wsl.exe -u root -e tail -50 /var/log/aasan-updater.log
```

---

## Rollback

Each update retains the 3 most recent versioned directories under `/opt/`.

```bash
# List available versions
wsl.exe -u root -e bash -c "ls /opt | grep aasan-"

# Roll back to a specific version
wsl.exe -u root -e bash /opt/aasan/scripts/rollback.sh 1.0.36
```

---

## Troubleshooting

**Update not firing:**
- Check Task Scheduler: `Get-ScheduledTask -TaskName Aasan-AutoUpdate`
- Check WSL is running: `wsl.exe --status`
- Manually trigger: `Start-ScheduledTask -TaskName Aasan-AutoUpdate`

**SHA256 mismatch in logs:**
- Re-publish: `./scripts/package-for-distribution.sh --publish <version>`
- The previous partial upload may have been corrupted

**docker compose up failed after update:**
- Check logs: `wsl.exe -u root -e bash -c "cd /opt/aasan && docker compose logs --tail=50"`
- Roll back: `wsl.exe -u root -e bash /opt/aasan/scripts/rollback.sh <previous>`

**alembic upgrade failed:**
- The new version is running; only the migration step failed
- Run manually: `wsl.exe -u root -e bash -c "cd /opt/aasan && docker compose exec api alembic upgrade head"`
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment/09-auto-update.md
git commit -m "docs: add 09-auto-update.md — ops guide for the auto-update system"
```

---

## Task 9: End-to-end smoke test

- [ ] **Step 1: Publish a test release from the dev Mac**

```bash
# Build and publish (requires a real version that exists in dist or rebuilds)
./scripts/package-for-distribution.sh --publish 1.0.37
```

Expected: tarball uploaded, `latest.json` visible at `${B2_PUBLIC_BASE_URL}/latest.json`

- [ ] **Step 2: Verify `latest.json` is publicly reachable**

```bash
curl -s "${B2_PUBLIC_BASE_URL}/latest.json"
```

Expected: `{"version":"1.0.37","filename":"aasan-1.0.37-...tar.gz","sha256":"...","released_at":"..."}`

- [ ] **Step 3: Simulate the poller on one WSL machine**

On the Windows machine (inside WSL as root):

```bash
# Run the updater once manually
bash /opt/aasan/scripts/auto-update.sh

# Watch the log
tail -20 /var/log/aasan-updater.log
```

Expected: either `already at 1.0.37, nothing to do` (if already on 1.0.37) or full update cycle completes.

- [ ] **Step 4: Verify rollback works**

On the WSL machine (after at least one update has been applied):

```bash
# List retained versions
ls /opt | grep aasan-

# Roll back to previous
bash /opt/aasan/scripts/rollback.sh <previous-version>

# Verify app is reachable
curl -k https://localhost/healthz
```

Expected: `healthy`

- [ ] **Step 5: Final commit**

```bash
git add -A
git status   # should be clean
```

---

## Self-Review Checklist

- [x] B2 CLI install step included (Task 1) — spec said "not yet installed"
- [x] `setup-https.sh --auto` reads `TAILSCALE_IP` from `.env`, no prompts (Task 2)
- [x] `--publish` flag uses `while [[ $# -gt 0 ]]` so it works as `script --publish 1.0.38` or `script 1.0.38 --publish` (Task 4)
- [x] `auto-update.sh` writes `.current-version` BEFORE `docker compose up` — so rollback knows what's deployed even if Docker fails (Task 5)
- [x] Old version dirs are pruned (keep newest 3) to prevent unbounded disk growth (Task 5)
- [x] `rollback.sh` lists available versions when called with no args (Task 6)
- [x] `alembic upgrade head` failure does not tear down running containers — just logs a die message (Task 5)
- [x] Compose commands use `cd /opt/aasan && docker compose` not `-f` flag — matches existing dist `start.sh` pattern
