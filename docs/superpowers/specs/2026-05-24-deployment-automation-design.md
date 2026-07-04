# Aasan Auto-Update System — Design Spec

**Date:** 2026-05-24  
**Status:** Approved  

---

## Problem

Deploying a new Aasan release to two Windows/WSL2 production machines requires:
1. Building a distribution tarball on the dev Mac
2. SCP'ing it to each machine
3. SSH → `wsl.exe` → copy to WSL → extract → copy `.env` → run `setup-https.sh` → `docker compose up`

This is slow, manual, and especially painful during urgent bug fixes. There are two production machines, both need to stay in sync.

---

## Goals

- Publishing a new release requires one command on the dev Mac
- Target machines check for updates every 30 minutes and deploy automatically
- Updates only fire when the developer pushes (quiet-hours discipline on the push side)
- Full rollback to any of the last 3 releases with a single command
- Zero credentials needed on target machines to download releases

---

## Non-Goals

- No CI/CD pipeline (no GitHub Actions, no build server)
- No in-app UI for update status
- No blue/green zero-downtime deploy (1–3 min downtime on update is acceptable)

---

## Architecture

```
Dev Mac
  └── ./scripts/package-for-distribution.sh --publish 1.0.38
        ├── builds & packages → aasan-1.0.38-20260524.tar.gz (~25 KB)
        ├── uploads tarball   → B2: aasan-releases/aasan-1.0.38-20260524.tar.gz
        └── uploads manifest  → B2: aasan-releases/latest.json  (overwrites)

Backblaze B2 Bucket: aasan-releases  (public download, private upload)
  ├── latest.json  →  {"version":"1.0.38","filename":"aasan-1.0.38-20260524.tar.gz","sha256":"..."}
  ├── aasan-1.0.37-20260523.tar.gz
  └── aasan-1.0.38-20260524.tar.gz

Each Windows/WSL2 Machine (x2)
  └── Task Scheduler → every 30 min → wsl.exe auto-update.sh
        ├── same version? → exit silently (~1 second, zero downtime)
        └── newer version? → full update sequence (see below)
```

The B2 bucket for releases is separate from the existing nightly backup bucket to allow independent lifecycle rules and access policies. Both use the same B2 account/CLI already installed on the machines.

---

## Files Changed

| File | Type | Change |
|------|------|--------|
| `scripts/package-for-distribution.sh` | Modified | Add `--publish` flag: upload tarball + overwrite `latest.json` in B2 |
| `scripts/setup-https.sh` | Modified | Add `--auto` flag: read `TAILSCALE_IP` from `.env`, skip all interactive prompts |
| `scripts/auto-update.sh` | New | Poller + deployer. Runs in WSL every 30 min |
| `scripts/rollback.sh` | New | One-command rollback: `./rollback.sh 1.0.36` |
| `scripts/setup-auto-update.ps1` | New | One-time PowerShell setup: registers the Task Scheduler job |
| `docs/deployment/09-auto-update.md` | New | Operations guide: setup, logs, rollback, troubleshooting |

No changes to Docker configs, compose files, or frontend/backend code.

---

## Detailed Logic

### `package-for-distribution.sh --publish VERSION`

After existing build+package steps complete:

```
1. Compute SHA256 of dist/aasan-{version}-{date}.tar.gz
2. b2 upload-file aasan-releases \
       dist/aasan-{version}-{date}.tar.gz \
       aasan-{version}-{date}.tar.gz
3. Write latest.json:
   {"version":"{version}","filename":"aasan-{version}-{date}.tar.gz","sha256":"{sha256}","released_at":"{iso8601}"}
4. b2 upload-file aasan-releases latest.json latest.json
5. Print: "Published {version} to B2. Machines will pick it up within 30 min."
```

Without `--publish`, the script behaves exactly as before (no B2 changes).

---

### `setup-https.sh --auto`

```
1. Source .env from current directory
2. Use $TAILSCALE_IP for the cert Subject Alternative Name (always 100.x.x.x, stable)
3. Generate self-signed cert silently — no prompts
4. Install cert into nginx config directory
```

`TAILSCALE_IP` is set once in `.env` during initial machine setup and carries forward automatically on every update because `.env` is copied before this script runs.

---

### `auto-update.sh` (runs as root in WSL)

```
1.  curl B2_PUBLIC_URL/latest.json → parse version, filename, sha256
2.  Read /opt/aasan/.current-version
3.  Versions match → log "already at {version}, nothing to do" → exit 0

4.  Log "new version {new} detected (current: {old}), starting update"
5.  curl -o /tmp/aasan-{version}.tar.gz  B2_PUBLIC_URL/{filename}
6.  Verify SHA256 → mismatch → log error → exit 1  (old version untouched)
7.  tar -xzf /tmp/aasan-{version}.tar.gz -C /opt/
8.  cp /opt/aasan/.env /opt/aasan-{version}/.env
9.  cd /opt/aasan-{version} && ./scripts/setup-https.sh --auto
10. cd /opt/aasan && docker compose down                   ← old symlink still active
11. ln -sfn /opt/aasan-{version} /opt/aasan            ← atomic swap
12. cd /opt/aasan && docker compose up -d                  ← new version
13. cd /opt/aasan && docker compose exec -T api alembic upgrade head
14. echo "{version}" > /opt/aasan/.current-version
15. Prune: keep newest 3 versioned dirs under /opt/, delete older ones
16. rm /tmp/aasan-{version}.tar.gz
17. Log "update to {version} complete in {elapsed}s"
```

**Error safety:** Steps 6–9 operate on the new dir without touching the running system. The old version continues serving traffic until step 10. If the script dies before step 11 (the symlink swap), the old version is untouched. If it dies after step 11, `rollback.sh` recovers in seconds.

---

### `rollback.sh VERSION`

```bash
#!/bin/bash
# Usage: ./rollback.sh 1.0.36
TARGET_VERSION=$1
TARGET_DIR="/opt/aasan-${TARGET_VERSION}"

if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: $TARGET_DIR does not exist"
  exit 1
fi

docker compose -f /opt/aasan/compose.yaml down
ln -sfn "$TARGET_DIR" /opt/aasan
docker compose -f /opt/aasan/compose.yaml up -d
echo "$TARGET_VERSION" > /opt/aasan/.current-version
echo "Rolled back to $TARGET_VERSION"
```

---

### `setup-auto-update.ps1` (one-time per machine)

Registers a Windows Task Scheduler job:
- **Name:** `Aasan-AutoUpdate`
- **Trigger:** At system startup + repeat every 30 minutes indefinitely
- **Action:** `wsl.exe -u root -e bash /opt/aasan/scripts/auto-update.sh`
- **Run as:** SYSTEM (runs without user login)

---

## `.env` additions (per machine, set once)

```
# Auto-update
TAILSCALE_IP=100.x.x.x           # Stable Tailscale IP of this machine
B2_PUBLIC_BASE_URL=https://...    # Public download URL for aasan-releases bucket
```

---

## Logging

All update activity appended to `/var/log/aasan-updater.log`:

```
2026-05-24 23:15:01 [INFO] already at 1.0.37, nothing to do
2026-05-25 00:15:01 [INFO] new version 1.0.38 detected (current: 1.0.37), starting update
2026-05-25 00:15:12 [INFO] update to 1.0.38 complete in 47s
```

---

## B2 Bucket Setup

- **Bucket name:** `aasan-releases`
- **Access:** Public (download without auth) — 25 KB files contain no secrets
- **Lifecycle:** Keep all files (versions are small; manual cleanup if ever needed)
- The dev Mac needs the `b2` CLI installed and authenticated (one-time setup step, covered in the implementation plan). Target machines need only `curl` — downloads are via public URL, no credentials required.
- Docker named volumes (PostgreSQL data, Redis data) survive `docker compose down/up` — confirmed by production history. Data is never at risk during updates.

---

## Rollback Strategy

The last 3 versioned dirs are always retained under `/opt/`. To roll back:

```bash
wsl.exe -u root -e bash /opt/aasan/scripts/rollback.sh 1.0.36
```

---

## Open Questions / Assumptions

- The B2 CLI (`b2`) is already installed and authenticated on the dev Mac for uploads. Target machines only need `curl` (already present in WSL).
- Docker volumes (PostgreSQL data, Redis data) are defined as named volumes in `compose.yaml` and survive across `docker compose down/up` — data is never lost during updates.
- The initial machine setup (first install, Task Scheduler registration) is still manual; only subsequent updates are automated.
