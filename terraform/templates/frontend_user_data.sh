#!/bin/bash
# =============================================================================
# Frontend EC2 User Data Script
# =============================================================================
# Installs and configures:
# - Node.js for building React app
# - Nginx for serving static files
# =============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== Starting Frontend Setup ==="
echo "AWS Region: ${aws_region}"
echo "Environment: ${environment}"
echo "API URL: ${api_url}"

# -----------------------------------------------------------------------------
# System Updates
# -----------------------------------------------------------------------------
echo "=== Installing system packages ==="
dnf update -y
dnf install -y nginx git

# Install Node.js 20
dnf module enable -y nodejs:20
dnf install -y nodejs npm

# -----------------------------------------------------------------------------
# Setup Nginx
# -----------------------------------------------------------------------------
echo "=== Configuring Nginx ==="

# Create Nginx config for React SPA
cat > /etc/nginx/conf.d/ai-tutor.conf << 'NGINX_CONF'
server {
    listen 80;
    server_name _;
    root /var/www/ai-tutor;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # React SPA - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /nginx-health {
        return 200 'healthy';
        add_header Content-Type text/plain;
    }
}
NGINX_CONF

# Remove default server block
rm -f /etc/nginx/conf.d/default.conf

# Create web root
mkdir -p /var/www/ai-tutor

# -----------------------------------------------------------------------------
# Create placeholder frontend
# -----------------------------------------------------------------------------
echo "=== Creating placeholder frontend ==="

cat > /var/www/ai-tutor/index.html << 'INDEX_HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Personal Tutor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 2.5rem; margin-bottom: 20px; }
        .subtitle { color: #a0a0a0; margin-bottom: 30px; }
        .status {
            display: inline-block;
            padding: 10px 20px;
            background: #4CAF50;
            border-radius: 25px;
            font-size: 0.9rem;
        }
        .hosts {
            margin-top: 30px;
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        .host {
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            width: 150px;
        }
        .host-name { font-weight: bold; color: #64B5F6; }
        .host-role { font-size: 0.8rem; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 AI Personal Tutor</h1>
        <p class="subtitle">Learn from any URL with podcast-style lessons</p>
        <span class="status">✓ Server Running</span>
        <div class="hosts">
            <div class="host">
                <div class="host-name">Alex</div>
                <div class="host-role">Senior Engineer</div>
            </div>
            <div class="host">
                <div class="host-name">Sam</div>
                <div class="host-role">Curious Learner</div>
            </div>
        </div>
        <p style="margin-top: 30px; color: #666; font-size: 0.9rem;">
            Deploy the full frontend to enable Lex chat interface
        </p>
    </div>
</body>
</html>
INDEX_HTML

# Create runtime config for frontend
cat > /var/www/ai-tutor/config.js << 'RUNTIME_CONFIG'
window.__RUNTIME_CONFIG__ = {
    AWS_REGION: "${aws_region}",
    COGNITO_IDENTITY_POOL_ID: "${cognito_identity_pool}",
    LEX_BOT_ID: "${lex_bot_id}",
    LEX_BOT_ALIAS_ID: "${lex_bot_alias_id}",
    API_URL: "${api_url}"
};
RUNTIME_CONFIG

# Set permissions
chown -R nginx:nginx /var/www/ai-tutor

# -----------------------------------------------------------------------------
# Start Nginx
# -----------------------------------------------------------------------------
echo "=== Starting Nginx ==="
systemctl enable nginx
systemctl start nginx

echo "=== Frontend setup complete ==="
