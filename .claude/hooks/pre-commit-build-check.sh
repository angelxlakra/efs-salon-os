#!/usr/bin/env bash
# Runs `docker compose up -d --build` from the project root before any `git commit`.
# Rebuilds all images (frontend + backend + nginx) and brings the stack up live.
# Blocks the commit if any image fails to build.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Only intercept git commit commands
if [[ "$CMD" != git\ commit* ]]; then
  exit 0
fi

PROJECT_DIR="/Users/angelxlakra/dev/efs-salon/efs-salon-os"

echo "🐳 Pre-commit: rebuilding stack with docker compose…" >&2

if cd "$PROJECT_DIR" && docker compose up -d --build 2>&1; then
  echo '{"systemMessage": "✅ Stack rebuilt and running — commit is safe."}'
else
  echo '{"continue": false, "stopReason": "docker compose build failed. Fix the errors above before committing."}'
fi
