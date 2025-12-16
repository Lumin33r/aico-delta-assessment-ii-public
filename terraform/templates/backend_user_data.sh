#!/bin/bash
# =============================================================================
# Backend EC2 User Data Script
# =============================================================================
# Installs and configures:
# - Python 3.11 and Flask backend
# - Ollama with specified model
# - Gunicorn for production serving
# =============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== Starting Backend Setup ==="
echo "AWS Region: ${aws_region}"
echo "Environment: ${environment}"
echo "Ollama Model: ${ollama_model}"

# -----------------------------------------------------------------------------
# System Updates
# -----------------------------------------------------------------------------
echo "=== Installing system packages ==="
dnf update -y
dnf install -y python3.11 python3.11-pip python3.11-devel gcc git

# -----------------------------------------------------------------------------
# Create app user and directories
# -----------------------------------------------------------------------------
echo "=== Setting up application user ==="
useradd -r -s /bin/false appuser || true
mkdir -p /opt/ai-tutor/backend
mkdir -p /var/log/ai-tutor
chown -R appuser:appuser /opt/ai-tutor
chown -R appuser:appuser /var/log/ai-tutor

# -----------------------------------------------------------------------------
# Install Ollama
# -----------------------------------------------------------------------------
echo "=== Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

# Configure Ollama as a service
cat > /etc/systemd/system/ollama.service << 'OLLAMA_SERVICE'
[Unit]
Description=Ollama AI Model Server
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
OLLAMA_SERVICE

systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Wait for Ollama to start
echo "=== Waiting for Ollama to start ==="
sleep 10

# Pull the model
echo "=== Pulling Ollama model: ${ollama_model} ==="
ollama pull ${ollama_model}

# -----------------------------------------------------------------------------
# Clone/Setup Backend Application
# -----------------------------------------------------------------------------
echo "=== Setting up backend application ==="
cd /opt/ai-tutor/backend

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
cat > requirements.txt << 'REQUIREMENTS'
Flask==3.0.0
flask-cors==4.0.0
gunicorn==21.2.0
boto3==1.34.0
beautifulsoup4==4.12.2
trafilatura==1.6.0
lxml==5.1.0
requests==2.31.0
python-dotenv==1.0.0
REQUIREMENTS

pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
cat > .env << 'ENVFILE'
AWS_REGION=${aws_region}
S3_BUCKET=${s3_bucket}
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=${ollama_model}
PORT=8000
FLASK_ENV=production
ENVFILE

# Download application code
# TODO: In production, pull from git or S3
# For now, create a placeholder health endpoint
cat > app.py << 'APP'
from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "ai-tutor-backend"})

@app.route('/')
def index():
    return jsonify({
        "service": "AI Personal Tutor API",
        "status": "running",
        "message": "Deploy full application code to complete setup"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
APP

chown -R appuser:appuser /opt/ai-tutor/backend

# -----------------------------------------------------------------------------
# Configure Gunicorn Service
# -----------------------------------------------------------------------------
echo "=== Configuring Gunicorn service ==="
cat > /etc/systemd/system/ai-tutor-backend.service << 'GUNICORN_SERVICE'
[Unit]
Description=AI Tutor Backend Service
After=network.target ollama.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/ai-tutor/backend
Environment="PATH=/opt/ai-tutor/backend/venv/bin"
EnvironmentFile=/opt/ai-tutor/backend/.env
ExecStart=/opt/ai-tutor/backend/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
GUNICORN_SERVICE

systemctl daemon-reload
systemctl enable ai-tutor-backend
systemctl start ai-tutor-backend

# -----------------------------------------------------------------------------
# CloudWatch Agent (Optional)
# -----------------------------------------------------------------------------
echo "=== Installing CloudWatch agent ==="
dnf install -y amazon-cloudwatch-agent

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWAGENT'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/ai-tutor/*.log",
            "log_group_name": "/ai-tutor/backend",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWAGENT

systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

echo "=== Backend setup complete ==="
