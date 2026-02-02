#!/bin/bash
# Script to create staff profiles for existing users
# Usage: ./create_staff_profiles.sh

cd "$(dirname "$0")"

echo "Creating staff profiles for existing users..."
echo ""

# Run in Docker if docker-compose is being used
if docker compose ps api &>/dev/null; then
    echo "Running inside Docker container..."
    docker compose exec api python -m app.scripts.create_staff_profiles
else
    echo "Running locally..."
    python -m app.scripts.create_staff_profiles
fi
