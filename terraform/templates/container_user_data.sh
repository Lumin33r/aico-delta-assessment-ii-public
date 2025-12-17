#!/bin/bash
# =============================================================================
# AI Personal Tutor - EC2 User Data (Containerized Deployment)
# =============================================================================
# Installs Docker and Docker Compose, clones the repository, and starts
# all services using docker-compose
# =============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== Starting Containerized Deployment Setup ==="
echo "Timestamp: $(date)"
echo "AWS Region: ${aws_region}"
echo "Environment: ${environment}"
echo "Ollama Model: ${ollama_model}"

# -----------------------------------------------------------------------------
# System Updates and Dependencies
# -----------------------------------------------------------------------------
echo "=== Installing system packages ==="
dnf update -y
dnf install -y git docker

# -----------------------------------------------------------------------------
# Install Docker Compose v2
# -----------------------------------------------------------------------------
echo "=== Installing Docker Compose ==="
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Verify installation
docker compose version

# -----------------------------------------------------------------------------
# Start and Enable Docker
# -----------------------------------------------------------------------------
echo "=== Starting Docker service ==="
systemctl enable docker
systemctl start docker

# Wait for Docker to be ready
sleep 5
docker info

# -----------------------------------------------------------------------------
# Create application directory
# -----------------------------------------------------------------------------
echo "=== Setting up application directory ==="
mkdir -p /opt/ai-tutor
cd /opt/ai-tutor

# -----------------------------------------------------------------------------
# Clone Repository
# -----------------------------------------------------------------------------
echo "=== Cloning repository ==="
# Using HTTPS for public repo or configure deploy keys for private repos
git clone ${git_repo_url} app
cd app

# -----------------------------------------------------------------------------
# Create Environment File
# -----------------------------------------------------------------------------
echo "=== Creating environment file ==="
cat > .env << 'ENVFILE'
# AWS Configuration
AWS_REGION=${aws_region}
S3_BUCKET=${s3_bucket}

# Lex Bot Configuration (for frontend build)
VITE_LEX_BOT_ID=${lex_bot_id}
VITE_LEX_BOT_ALIAS_ID=${lex_bot_alias_id}
VITE_AWS_REGION=${aws_region}
VITE_COGNITO_IDENTITY_POOL_ID=${cognito_identity_pool_id}

# API Configuration (nginx proxies /api to backend)
VITE_API_URL=/api

# Ollama Configuration
OLLAMA_MODEL=${ollama_model}

# Application Configuration
LOG_LEVEL=INFO
ENVFILE

# -----------------------------------------------------------------------------
# Build and Start Services
# -----------------------------------------------------------------------------
echo "=== Building and starting Docker containers ==="

# Build images first (takes longer but ensures clean state)
docker compose build --no-cache

# Start all services
docker compose up -d

# Wait for services to be healthy
echo "=== Waiting for services to become healthy ==="
sleep 30

# Check container status
docker compose ps

# -----------------------------------------------------------------------------
# Setup Auto-restart on Boot
# -----------------------------------------------------------------------------
echo "=== Configuring auto-restart ==="
cat > /etc/systemd/system/ai-tutor.service << 'SERVICE'
[Unit]
Description=AI Personal Tutor Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ai-tutor/app
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose up -d
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ai-tutor.service

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
echo "=== Setting up logging ==="
mkdir -p /var/log/ai-tutor

# Create log rotation for docker logs
cat > /etc/logrotate.d/ai-tutor << 'LOGROTATE'
/var/log/ai-tutor/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
}
LOGROTATE

# -----------------------------------------------------------------------------
# Health Check Script
# -----------------------------------------------------------------------------
echo "=== Creating health check script ==="
cat > /opt/ai-tutor/healthcheck.sh << 'HEALTHCHECK'
#!/bin/bash
# Check if all containers are running
if docker compose -f /opt/ai-tutor/app/docker-compose.yml ps | grep -q "unhealthy\|Exit"; then
    echo "UNHEALTHY: Some containers are not running properly"
    exit 1
fi
# Check frontend
if ! curl -sf http://localhost:80/ > /dev/null; then
    echo "UNHEALTHY: Frontend not responding"
    exit 1
fi
# Check backend
if ! curl -sf http://localhost:80/api/health > /dev/null; then
    echo "UNHEALTHY: Backend not responding"
    exit 1
fi
echo "HEALTHY: All services running"
exit 0
HEALTHCHECK
chmod +x /opt/ai-tutor/healthcheck.sh

# -----------------------------------------------------------------------------
# Final Status
# -----------------------------------------------------------------------------
echo "=== Deployment Complete ==="
echo "Timestamp: $(date)"
echo ""
echo "Container Status:"
docker compose ps
echo ""
echo "To check logs: docker compose logs -f"
echo "To restart: docker compose restart"
echo "To rebuild: docker compose up -d --build"
