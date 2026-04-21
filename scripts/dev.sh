#!/bin/bash
echo "🚀 Starting SalonOS in DEVELOPMENT mode (hot reload enabled)"
echo ""

# Use --build only on first run or when dependencies change
if [ "$1" = "--build" ] || [ "$1" = "-b" ]; then
    echo "🔨 Building images..."
    docker compose -f docker-compose.dev.yml up --build
else
    docker compose -f docker-compose.dev.yml up
fi
