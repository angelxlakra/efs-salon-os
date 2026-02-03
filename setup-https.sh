#!/bin/bash

# Setup HTTPS for SalonOS Local Server
# This script generates a self-signed SSL certificate for local development

set -e

echo "========================================="
echo "SalonOS HTTPS Setup"
echo "========================================="
echo ""

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
else
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}')
fi

echo "Detected local IP: $LOCAL_IP"
echo ""

# Ask if user wants to add additional IPs
echo "Do you want to add additional IP addresses to the certificate?"
echo "(Useful if you have multiple network interfaces or want to support IP range)"
echo ""
read -p "Enter additional IPs (comma-separated, or press Enter to skip): " ADDITIONAL_IPS

# Build Subject Alternative Names
SAN="DNS:salon.local,DNS:localhost,IP:127.0.0.1"

# Add detected IP
if [ -n "$LOCAL_IP" ]; then
    SAN="$SAN,IP:$LOCAL_IP"
fi

# Add additional IPs if provided
if [ -n "$ADDITIONAL_IPS" ]; then
    IFS=',' read -ra IPS <<< "$ADDITIONAL_IPS"
    for ip in "${IPS[@]}"; do
        # Trim whitespace
        ip=$(echo "$ip" | xargs)
        if [ -n "$ip" ]; then
            SAN="$SAN,IP:$ip"
        fi
    done
fi

echo ""
echo "Certificate will be valid for:"
echo "$SAN" | tr ',' '\n' | sed 's/^/  - /'
echo ""

# Create SSL directory
SSL_DIR="./nginx/ssl"
mkdir -p "$SSL_DIR"

# Certificate details
CERT_FILE="$SSL_DIR/salon.crt"
KEY_FILE="$SSL_DIR/salon.key"
DOMAIN="salon.local"

echo "Generating self-signed SSL certificate..."
echo ""

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -subj "/C=IN/ST=State/L=City/O=SalonOS/CN=$DOMAIN" \
  -addext "subjectAltName=$SAN"

echo "✓ Certificate generated successfully!"
echo ""
echo "Certificate files:"
echo "  - Certificate: $CERT_FILE"
echo "  - Private Key: $KEY_FILE"
echo ""

# Backup existing nginx config
if [ -f "./nginx/nginx.conf" ]; then
    cp ./nginx/nginx.conf ./nginx/nginx.conf.backup
    echo "✓ Backed up nginx.conf to nginx.conf.backup"
fi

# Create HTTPS-enabled nginx config
cat > ./nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Client settings
    client_max_body_size 50M;

    # Upstream services
    upstream frontend {
        server frontend:3000;
    }

    upstream api {
        server api:8000;
    }

    # HTTP Server - Redirect to HTTPS (except healthcheck)
    server {
        listen 80;
        server_name _;  # Catch all (including IP addresses)

        # Health check (allow on HTTP for Docker healthcheck)
        location /healthz {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # Redirect all other traffic to HTTPS
        location / {
            return 301 https://$host$request_uri;  # Preserve the hostname/IP user entered
        }
    }

    # HTTPS Server
    server {
        listen 443 ssl;
        http2 on;
        server_name _;  # Accept all hostnames/IPs

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/salon.crt;
        ssl_certificate_key /etc/nginx/ssl/salon.key;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;

        # Frontend (Next.js)
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;

            # Next.js hot reload
            proxy_read_timeout 86400;
        }

        # API (FastAPI)
        location /api/ {
            proxy_pass http://api;  # No trailing slash - preserve /api prefix
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # CORS headers (if needed)
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        }

        # Health check
        location /healthz {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF

echo "✓ Updated nginx.conf with HTTPS configuration"
echo ""

# Update docker-compose to mount SSL certificates
if grep -q "nginx/ssl" docker-compose.yml 2>/dev/null; then
    echo "✓ docker-compose.yml already configured for SSL"
else
    echo "⚠ Please add SSL volume mount to docker-compose.yml:"
    echo ""
    echo "  nginx:"
    echo "    volumes:"
    echo "      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro"
    echo "      - ./nginx/ssl:/etc/nginx/ssl:ro  # Add this line"
    echo ""
fi

# Update docker-compose ports
if grep -q "443:443" docker-compose.yml 2>/dev/null; then
    echo "✓ docker-compose.yml already has port 443"
else
    echo "⚠ Please add HTTPS port to docker-compose.yml:"
    echo ""
    echo "  nginx:"
    echo "    ports:"
    echo "      - \"80:80\""
    echo "      - \"443:443\"  # Add this line"
    echo ""
fi

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Update docker-compose.yml (if needed - see warnings above)"
echo ""
echo "2. Restart nginx:"
echo "   docker compose restart nginx"
echo ""
echo "3. Trust the certificate on your mobile device:"
echo ""
echo "   For Android:"
echo "   a. Copy the certificate to your phone:"
echo "      adb push $CERT_FILE /sdcard/Download/"
echo "   b. Go to Settings > Security > Install from storage"
echo "   c. Select the salon.crt file"
echo "   d. Name it 'SalonOS Local' and select 'VPN and apps'"
echo ""
echo "   For iOS:"
echo "   a. Email the certificate to yourself or use AirDrop"
echo "   b. Open the certificate file"
echo "   c. Go to Settings > General > VPN & Device Management"
echo "   d. Install the profile"
echo "   e. Go to Settings > General > About > Certificate Trust Settings"
echo "   f. Enable full trust for 'SalonOS Local'"
echo ""
echo "4. Access your app at:"
echo "   https://salon.local (if DNS is configured)"
echo "   https://$LOCAL_IP (from mobile devices on same network)"
echo ""
echo "IMPORTANT FOR MOBILE ACCESS:"
echo "  - You can access via any IP address included in the certificate"
echo "  - If your server IP changes, re-run this script to regenerate the certificate"
echo "  - For static IP: Configure your router to assign a fixed IP to the server"
echo ""
echo "Certificate valid for 365 days"
echo "========================================="
