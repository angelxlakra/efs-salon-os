# Backend Utility Scripts

Maintenance and validation scripts for SalonOS backend.

## Available Scripts

### `validate_settings.py`

Validates and fixes salon settings database.

**What it does:**
- ✅ Checks if settings record exists
- ✅ Creates default settings if missing
- ✅ Fixes NULL values in required fields
- ✅ Validates data integrity
- ✅ Displays current configuration
- ⚠️ Warns about default/placeholder values

**Usage:**

```bash
# Run directly in container
docker compose exec api python scripts/validate_settings.py

# Or if running locally with uv
cd backend
uv run python scripts/validate_settings.py
```

**When to use:**
- After initial deployment
- After running migrations
- When getting 500 errors from `/api/settings`
- After database restore from backup
- As part of health checks

**Safe to run multiple times** - it's idempotent and won't overwrite existing valid data.

## Adding New Scripts

1. Create script in `backend/scripts/`
2. Add shebang: `#!/usr/bin/env python3`
3. Add docstring explaining usage
4. Make executable: `chmod +x script_name.py`
5. Update this README
