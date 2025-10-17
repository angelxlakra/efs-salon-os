#!/bin/bash
echo "🚀 Starting SalonOS..."
docker compose up -d
echo ""
echo "✅ Services started!"
echo ""
echo "🌐 Access points:"
echo "  - Frontend: http://localhost"
echo "  - API Docs: http://localhost/api/docs"
echo "  - Health: http://localhost/healthz"
echo ""
echo "📊 Check status: docker compose ps"
echo "📝 View logs: docker compose logs -f"