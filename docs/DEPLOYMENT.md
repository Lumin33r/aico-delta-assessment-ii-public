# AI Personal Tutor - Production Deployment Guide

A comprehensive guide for deploying the AI Personal Tutor to AWS using Terraform, including EC2 setup, service configuration, and production validation.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Phase 1: Infrastructure Deployment](#phase-1-infrastructure-deployment)
  - [1.1 AWS Credentials Setup](#11-aws-credentials-setup)
  - [1.2 Terraform Variables Configuration](#12-terraform-variables-configuration)
  - [1.3 Initialize and Apply Terraform](#13-initialize-and-apply-terraform)
  - [1.4 Create Lex Bot Alias](#14-create-lex-bot-alias-post-apply)
- [Phase 2: EC2 Instance Configuration](#phase-2-ec2-instance-configuration)
  - [2.1 SSH Access Setup](#21-ssh-access-setup)
  - [2.2 Verify User Data Execution](#22-verify-user-data-execution)
  - [2.3 Deploy Backend Application Code](#23-deploy-backend-application-code)
  - [2.4 Configure and Start Services](#24-configure-and-start-services)
- [Phase 3: Frontend Deployment](#phase-3-frontend-deployment)
  - [3.1 Build Frontend for Production](#31-build-frontend-for-production)
  - [3.2 Deploy to S3 + CloudFront (Recommended)](#32-deploy-to-s3--cloudfront-recommended)
  - [3.3 Alternative: Deploy to EC2/Nginx](#33-alternative-deploy-to-ec2nginx)
- [Phase 4: Production Validation](#phase-4-production-validation)
  - [4.1 Health Check Verification](#41-health-check-verification)
  - [4.2 API Endpoint Testing](#42-api-endpoint-testing)
  - [4.3 Lex Bot Testing](#43-lex-bot-testing)
  - [4.4 End-to-End Workflow Test](#44-end-to-end-workflow-test)
- [Environment Variables Reference](#environment-variables-reference)
- [Monitoring and Observability](#monitoring-and-observability)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)
- [Cleanup and Teardown](#cleanup-and-teardown)

---

## Prerequisites

### Required Tools

| Tool      | Version  | Installation                                                                                                                    |
| --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| AWS CLI   | v2.x     | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install` |
| Terraform | >= 1.5.0 | `brew install terraform` or [tfenv](https://github.com/tfutils/tfenv)                                                           |
| Node.js   | >= 18    | `nvm install 18`                                                                                                                |
| Python    | >= 3.11  | `pyenv install 3.11`                                                                                                            |
| jq        | latest   | `brew install jq` or `apt install jq`                                                                                           |

### Required AWS Permissions

Ensure your IAM user/role has permissions for:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "elasticloadbalancing:*",
        "autoscaling:*",
        "s3:*",
        "iam:*",
        "lambda:*",
        "lex:*",
        "cognito-identity:*",
        "polly:*",
        "cloudwatch:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                   │
│                                                                          │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────────────────────┐  │
│  │ CloudFront│────▶│     ALB     │────▶│  EC2 (Auto Scaling Group)   │  │
│  │ (Frontend)│     │  (Backend)  │     │  - Flask API                │  │
│  └──────────┘     └─────────────┘     │  - Ollama LLM               │  │
│       │                                │  - Gunicorn                 │  │
│       │                                └──────────────────────────────┘  │
│       │                                              │                   │
│       ▼                                              ▼                   │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────────────────────┐  │
│  │    S3    │     │  Lex V2 Bot │────▶│     Lambda Fulfillment      │  │
│  │ (Static) │     │             │     │                              │  │
│  └──────────┘     └─────────────┘     └──────────────────────────────┘  │
│                          │                                               │
│                          ▼                                               │
│                   ┌─────────────┐     ┌──────────────────────────────┐  │
│                   │  Cognito    │     │         S3 (Audio)           │  │
│                   │Identity Pool│     │                              │  │
│                   └─────────────┘     └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Infrastructure Deployment

### 1.1 AWS Credentials Setup

```bash
# Option A: Configure AWS CLI profile
aws configure --profile ai-tutor
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-west-2
# Default output format: json

export AWS_PROFILE=ai-tutor

# Option B: Use environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-west-2"

# Verify credentials
aws sts get-caller-identity
```

Expected output:

```json
{
  "UserId": "AIDA...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

### 1.2 Terraform Variables Configuration

```bash
cd terraform

# Create terraform.tfvars for your environment
cat > terraform.tfvars << 'EOF'
# =============================================================================
# AI Personal Tutor - Terraform Variables
# =============================================================================

# Project Configuration
project_name = "ai-tutor"
environment  = "prod"
aws_region   = "us-west-2"

# EC2 Configuration
instance_type    = "t3.medium"    # Minimum for Ollama
key_name         = "your-keypair" # Your EC2 key pair name
min_instances    = 1
max_instances    = 3
desired_capacity = 1

# Networking
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-west-2a", "us-west-2b"]
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]

# Application Configuration
ollama_model = "llama3.2:1b"  # Use smaller model for faster startup
backend_port = 8000

# Feature Flags
create_lex_bot = true
create_cognito = true

# Tags
tags = {
  Project     = "ai-personal-tutor"
  Owner       = "your-team"
  CostCenter  = "engineering"
}
EOF
```

### 1.3 Initialize and Apply Terraform

```bash
# Step 1: Initialize Terraform (downloads providers)
terraform init

# Expected output:
# Terraform has been successfully initialized!

# Step 2: Validate configuration
terraform validate

# Expected output:
# Success! The configuration is valid.

# Step 3: Preview changes
terraform plan -out=tfplan

# Review the plan carefully - should create ~40-50 resources:
# - VPC, Subnets, Internet Gateway, Route Tables
# - Security Groups
# - Application Load Balancer + Target Group
# - Launch Template + Auto Scaling Group
# - S3 Bucket for audio
# - IAM Roles and Policies
# - Lambda Function
# - Lex Bot + Intent + Slot Types
# - Cognito Identity Pool

# Step 4: Apply infrastructure
terraform apply tfplan

# Type 'yes' when prompted
# Wait 5-10 minutes for resources to create

# Step 5: Save outputs for later use
terraform output -json > ../deployment-outputs.json

# Display key outputs
terraform output connection_info
```

**Key Outputs to Note:**

```bash
# Get ALB DNS (your API endpoint)
export ALB_DNS=$(terraform output -raw alb_dns_name)
echo "API Endpoint: http://${ALB_DNS}"

# Get S3 bucket name
export S3_BUCKET=$(terraform output -raw audio_bucket_name)
echo "Audio Bucket: ${S3_BUCKET}"

# Get Lex Bot ID (if created)
export LEX_BOT_ID=$(terraform output -raw lex_bot_id)
echo "Lex Bot ID: ${LEX_BOT_ID}"

# Get Cognito Identity Pool ID (if created)
export COGNITO_POOL_ID=$(terraform output -raw cognito_identity_pool_id)
echo "Cognito Pool: ${COGNITO_POOL_ID}"
```

### 1.4 Create Lex Bot Alias (Post-Apply)

Terraform cannot fully manage Lex bot aliases with Lambda hooks. Create manually:

```bash
# Get required values from Terraform output
LEX_BOT_ID=$(terraform output -raw lex_bot_id)
LEX_BOT_VERSION=$(terraform output -raw lex_bot_version)
LAMBDA_ARN=$(terraform output -raw lambda_function_arn)

# Create the bot alias with Lambda fulfillment
aws lexv2-models create-bot-alias \
  --bot-alias-name "prod" \
  --bot-id "${LEX_BOT_ID}" \
  --bot-version "${LEX_BOT_VERSION}" \
  --bot-alias-locale-settings '{
    "en_US": {
      "enabled": true,
      "codeHookSpecification": {
        "lambdaCodeHook": {
          "lambdaARN": "'"${LAMBDA_ARN}"'",
          "codeHookInterfaceVersion": "1.0"
        }
      }
    }
  }'

# Save the alias ID from the response
export LEX_BOT_ALIAS_ID="<alias-id-from-response>"
echo "Lex Bot Alias ID: ${LEX_BOT_ALIAS_ID}"
```

---

## Phase 2: EC2 Instance Configuration

### 2.1 SSH Access Setup

```bash
# Get instance IP from ASG
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $(terraform output -raw backend_asg_name) \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids ${INSTANCE_ID} \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Instance IP: ${INSTANCE_IP}"

# SSH to the instance
ssh -i ~/.ssh/your-keypair.pem ec2-user@${INSTANCE_IP}
```

### 2.2 Verify User Data Execution

Once connected via SSH:

```bash
# Check user data log for errors
sudo cat /var/log/user-data.log

# Verify Ollama is running
sudo systemctl status ollama
ollama list  # Should show the pulled model

# Verify backend service is running
sudo systemctl status ai-tutor-backend

# Check if placeholder app is responding
curl http://localhost:8000/health
```

Expected health check response:

```json
{ "status": "healthy", "service": "ai-tutor-backend" }
```

### 2.3 Deploy Backend Application Code

**Option A: Deploy from Git Repository**

```bash
# On the EC2 instance
sudo -u appuser bash

cd /opt/ai-tutor
rm -rf backend

# Clone your repository
git clone https://github.com/your-org/aico-delta-assessment-ii.git repo
mv repo/backend ./backend
rm -rf repo

cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
cat > .env << 'EOF'
AWS_REGION=us-west-2
S3_BUCKET=<your-s3-bucket-from-terraform>
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
PORT=8000
FLASK_ENV=production
LOG_LEVEL=INFO
EOF

exit  # Exit appuser shell
```

**Option B: Deploy from S3 Archive**

```bash
# From your local machine, create and upload archive
cd aico-delta-assessment-ii/backend
tar -czvf backend.tar.gz src/ requirements.txt

aws s3 cp backend.tar.gz s3://${S3_BUCKET}/deployments/backend.tar.gz

# On EC2 instance
sudo -u appuser bash
cd /opt/ai-tutor/backend

aws s3 cp s3://${S3_BUCKET}/deployments/backend.tar.gz .
tar -xzvf backend.tar.gz
rm backend.tar.gz

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt
exit
```

**Option C: Deploy with rsync (Development)**

```bash
# From local machine - sync code directly
rsync -avz --exclude='venv' --exclude='.venv' --exclude='__pycache__' \
  -e "ssh -i ~/.ssh/your-keypair.pem" \
  backend/ ec2-user@${INSTANCE_IP}:/tmp/backend-code/

# On EC2 instance
sudo mv /tmp/backend-code/* /opt/ai-tutor/backend/
sudo chown -R appuser:appuser /opt/ai-tutor/backend/
```

### 2.4 Configure and Start Services

```bash
# Update the systemd service to point to actual app
sudo tee /etc/systemd/system/ai-tutor-backend.service << 'EOF'
[Unit]
Description=AI Tutor Backend Service
After=network.target ollama.service
Requires=ollama.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/ai-tutor/backend
Environment="PATH=/opt/ai-tutor/backend/venv/bin"
Environment="PYTHONPATH=/opt/ai-tutor/backend"
EnvironmentFile=/opt/ai-tutor/backend/.env
ExecStart=/opt/ai-tutor/backend/venv/bin/gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --timeout 300 \
    --access-logfile /var/log/ai-tutor/access.log \
    --error-logfile /var/log/ai-tutor/error.log \
    "src.app:app"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/ai-tutor
sudo chown -R appuser:appuser /var/log/ai-tutor

# Reload and restart services
sudo systemctl daemon-reload
sudo systemctl restart ai-tutor-backend

# Verify service is running
sudo systemctl status ai-tutor-backend

# Check logs for errors
sudo journalctl -u ai-tutor-backend -f --no-pager -n 50
```

**Verify Full Backend Health:**

```bash
# Test health endpoint locally
curl http://localhost:8000/health | jq

# Expected output:
{
  "status": "healthy",
  "services": {
    "ollama": {
      "healthy": true,
      "model": "llama3.2:1b"
    },
    "polly": {
      "healthy": true
    }
  }
}

# Test from ALB (external)
curl http://${ALB_DNS}/health | jq
```

---

## Phase 3: Frontend Deployment

### 3.1 Build Frontend for Production

```bash
# On your local machine
cd aico-delta-assessment-ii/frontend

# Create production environment file
cat > .env.production << EOF
VITE_AWS_REGION=us-west-2
VITE_COGNITO_IDENTITY_POOL_ID=${COGNITO_POOL_ID}
VITE_LEX_BOT_ID=${LEX_BOT_ID}
VITE_LEX_BOT_ALIAS_ID=${LEX_BOT_ALIAS_ID}
VITE_API_URL=http://${ALB_DNS}
EOF

# Install dependencies
npm install

# Build for production
npm run build

# Verify build output
ls -la dist/
# Should contain: index.html, assets/
```

### 3.2 Deploy to S3 + CloudFront (Recommended)

```bash
# Create S3 bucket for frontend (if not exists)
FRONTEND_BUCKET="ai-tutor-frontend-$(aws sts get-caller-identity --query Account --output text)"

aws s3 mb s3://${FRONTEND_BUCKET} --region us-west-2

# Configure for static website hosting
aws s3 website s3://${FRONTEND_BUCKET} \
  --index-document index.html \
  --error-document index.html

# Set bucket policy for public read
cat > /tmp/bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${FRONTEND_BUCKET}/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket ${FRONTEND_BUCKET} \
  --policy file:///tmp/bucket-policy.json

# Disable block public access (required for website hosting)
aws s3api put-public-access-block \
  --bucket ${FRONTEND_BUCKET} \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Upload frontend build with caching headers
aws s3 sync dist/ s3://${FRONTEND_BUCKET}/ \
  --delete \
  --cache-control "max-age=31536000" \
  --exclude "index.html"

# Upload index.html with no-cache
aws s3 cp dist/index.html s3://${FRONTEND_BUCKET}/index.html \
  --cache-control "no-cache, no-store, must-revalidate"

# Get website URL
echo "Frontend URL: http://${FRONTEND_BUCKET}.s3-website-us-west-2.amazonaws.com"
```

### 3.3 Alternative: Deploy to EC2/Nginx

```bash
# SSH to a frontend EC2 instance (or use backend instance)
ssh -i ~/.ssh/your-keypair.pem ec2-user@${INSTANCE_IP}

# Install Nginx
sudo dnf install -y nginx

# Create site configuration
sudo tee /etc/nginx/conf.d/ai-tutor.conf << 'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/ai-tutor;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Handle SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy API requests to backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://localhost:8000;
    }
}
EOF

# Create web directory
sudo mkdir -p /var/www/ai-tutor
sudo chown -R nginx:nginx /var/www/ai-tutor

# Exit SSH and upload build files from local
exit

# From local machine
scp -i ~/.ssh/your-keypair.pem -r dist/* ec2-user@${INSTANCE_IP}:/tmp/frontend/

# Back on EC2
ssh -i ~/.ssh/your-keypair.pem ec2-user@${INSTANCE_IP}
sudo mv /tmp/frontend/* /var/www/ai-tutor/
sudo chown -R nginx:nginx /var/www/ai-tutor/

# Test nginx config
sudo nginx -t

# Start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Verify
curl http://localhost/
```

---

## Phase 4: Production Validation

### 4.1 Health Check Verification

```bash
# Backend health via ALB
curl -s http://${ALB_DNS}/health | jq

# Expected response:
{
  "status": "healthy",
  "services": {
    "ollama": {"healthy": true, "model": "llama3.2:1b"},
    "polly": {"healthy": true}
  },
  "cache": {"entries": 0, "max_entries": 100}
}

# Check ALB target group health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names "*backend*" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text) \
  | jq '.TargetHealthDescriptions[].TargetHealth'

# Expected: {"State": "healthy"}
```

### 4.2 API Endpoint Testing

```bash
# Test URL validation endpoint
curl -s -X POST http://${ALB_DNS}/api/validate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Python_(programming_language)"}' | jq

# Expected:
{
  "is_valid": true,
  "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
  "domain": "en.wikipedia.org",
  "content_type": "text/html"
}

# Test session creation (may take 30-60 seconds)
echo "Creating session (this takes ~60 seconds)..."
curl -s -X POST http://${ALB_DNS}/api/v2/sessions \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Machine_learning"}' \
  --max-time 120 | jq

# Expected:
{
  "id": "session-uuid-here",
  "url": "https://en.wikipedia.org/wiki/Machine_learning",
  "status": "ready",
  "lessons": [...]
}

# List sessions
curl -s http://${ALB_DNS}/api/v2/sessions | jq

# Get cache stats
curl -s http://${ALB_DNS}/api/cache/stats | jq
```

### 4.3 Lex Bot Testing

```bash
# Test Lex bot via AWS CLI
aws lexv2-runtime recognize-text \
  --bot-id ${LEX_BOT_ID} \
  --bot-alias-id ${LEX_BOT_ALIAS_ID} \
  --locale-id en_US \
  --session-id "test-session-$(date +%s)" \
  --text "I want to learn about Python" | jq

# Check Lambda fulfillment logs
aws logs tail /aws/lambda/$(terraform output -raw lambda_function_name) --follow
```

### 4.4 End-to-End Workflow Test

Create and run this test script:

```bash
#!/bin/bash
# e2e-test.sh - End-to-end production test

set -e

ALB_DNS="${1:-$ALB_DNS}"
BASE_URL="http://${ALB_DNS}"

echo "=============================================="
echo " AI Personal Tutor - E2E Production Test"
echo "=============================================="
echo "Base URL: ${BASE_URL}"
echo ""

# Test 1: Health Check
echo "1. Health Check..."
HEALTH=$(curl -sf "${BASE_URL}/health")
if echo "${HEALTH}" | jq -e '.status == "healthy"' > /dev/null; then
    echo "   ✅ Backend healthy"
    echo "   └── Ollama: $(echo ${HEALTH} | jq -r '.services.ollama.healthy')"
    echo "   └── Polly: $(echo ${HEALTH} | jq -r '.services.polly.healthy')"
else
    echo "   ❌ Backend unhealthy"
    echo "   Response: ${HEALTH}"
    exit 1
fi
echo ""

# Test 2: URL Validation
echo "2. URL Validation..."
VALIDATE=$(curl -sf -X POST "${BASE_URL}/api/validate" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com"}')
if echo "${VALIDATE}" | jq -e '.is_valid == true' > /dev/null; then
    echo "   ✅ URL validation working"
else
    echo "   ❌ URL validation failed"
    echo "   Response: ${VALIDATE}"
    exit 1
fi
echo ""

# Test 3: Session Creation
echo "3. Creating session (this may take 60+ seconds)..."
SESSION=$(curl -sf -X POST "${BASE_URL}/api/v2/sessions" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}' \
    --max-time 180)

SESSION_ID=$(echo "${SESSION}" | jq -r '.id')
if [ -n "${SESSION_ID}" ] && [ "${SESSION_ID}" != "null" ]; then
    echo "   ✅ Session created: ${SESSION_ID}"
    LESSON_COUNT=$(echo "${SESSION}" | jq '.lessons | length')
    echo "   └── Lessons generated: ${LESSON_COUNT}"
else
    echo "   ❌ Session creation failed"
    echo "   Response: ${SESSION}"
    exit 1
fi
echo ""

# Test 4: Get Session
echo "4. Retrieving session..."
GET_SESSION=$(curl -sf "${BASE_URL}/api/v2/sessions/${SESSION_ID}")
STATUS=$(echo "${GET_SESSION}" | jq -r '.status')
echo "   ✅ Session status: ${STATUS}"
echo ""

# Test 5: List Sessions
echo "5. Listing all sessions..."
LIST=$(curl -sf "${BASE_URL}/api/v2/sessions")
TOTAL=$(echo "${LIST}" | jq '. | length')
echo "   ✅ Total sessions: ${TOTAL}"
echo ""

# Test 6: Delete Session
echo "6. Deleting session..."
DELETE_CODE=$(curl -sf -X DELETE "${BASE_URL}/api/v2/sessions/${SESSION_ID}" \
    -w "%{http_code}" -o /dev/null)
if [ "${DELETE_CODE}" == "204" ]; then
    echo "   ✅ Session deleted (HTTP 204)"
else
    echo "   ❌ Delete failed with status ${DELETE_CODE}"
fi
echo ""

# Test 7: Verify Deletion
echo "7. Verifying deletion..."
GET_DELETED=$(curl -s "${BASE_URL}/api/v2/sessions/${SESSION_ID}" -w "%{http_code}" -o /dev/null)
if [ "${GET_DELETED}" == "404" ]; then
    echo "   ✅ Session not found (HTTP 404) - deletion confirmed"
else
    echo "   ⚠️  Unexpected status: ${GET_DELETED}"
fi
echo ""

echo "=============================================="
echo " ✅ All Tests Passed!"
echo "=============================================="
echo ""
echo "Production URLs:"
echo "  API:      ${BASE_URL}"
echo "  Health:   ${BASE_URL}/health"
echo "  Sessions: ${BASE_URL}/api/v2/sessions"
```

Run the test:

```bash
chmod +x e2e-test.sh
./e2e-test.sh "${ALB_DNS}"
```

---

## Environment Variables Reference

### Backend (.env)

| Variable       | Description               | Required | Default      | Example                   |
| -------------- | ------------------------- | -------- | ------------ | ------------------------- |
| `AWS_REGION`   | AWS region for services   | Yes      | -            | `us-west-2`               |
| `S3_BUCKET`    | S3 bucket for audio files | Yes      | -            | `ai-tutor-audio-abc123`   |
| `OLLAMA_HOST`  | Ollama server URL         | Yes      | -            | `http://localhost:11434`  |
| `OLLAMA_MODEL` | LLM model to use          | Yes      | -            | `llama3.2:1b`             |
| `PORT`         | Backend server port       | No       | `8000`       | `8000`                    |
| `FLASK_ENV`    | Flask environment         | No       | `production` | `production`              |
| `LOG_LEVEL`    | Logging verbosity         | No       | `INFO`       | `DEBUG`                   |
| `CORS_ORIGINS` | Allowed CORS origins      | No       | `*`          | `https://app.example.com` |

### Frontend (.env.production)

| Variable                        | Description           | Required | Example                        |
| ------------------------------- | --------------------- | -------- | ------------------------------ |
| `VITE_AWS_REGION`               | AWS region            | Yes      | `us-west-2`                    |
| `VITE_COGNITO_IDENTITY_POOL_ID` | Cognito pool for auth | Yes      | `us-west-2:abc-123-def`        |
| `VITE_LEX_BOT_ID`               | Lex bot ID            | Yes      | `ABCDEFGHIJ`                   |
| `VITE_LEX_BOT_ALIAS_ID`         | Lex alias ID          | Yes      | `TSTALIASID`                   |
| `VITE_API_URL`                  | Backend API URL       | Yes      | `http://alb-dns.amazonaws.com` |

---

## Monitoring and Observability

### CloudWatch Logs

```bash
# View backend application logs
aws logs tail /ai-tutor/backend --follow --since 1h

# View Lambda fulfillment logs
aws logs tail /aws/lambda/ai-tutor-lex-fulfillment --follow

# View EC2 user data logs (if configured)
aws logs tail /ai-tutor/user-data --follow

# Search logs for errors
aws logs filter-log-events \
  --log-group-name /ai-tutor/backend \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000)
```

### CloudWatch Metrics Dashboard

```bash
# ALB request count (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/ai-tutor-alb/xxxxx \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum

# EC2 CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=$(terraform output -raw backend_asg_name) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average

# Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=$(terraform output -raw lambda_function_name) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

### Simple Health Monitor Script

```bash
#!/bin/bash
# monitor.sh - Simple health monitor

while true; do
    clear
    echo "========================================"
    echo " AI Tutor Health Monitor"
    echo " $(date)"
    echo "========================================"
    echo ""

    # Backend health
    echo "Backend Health:"
    curl -s http://${ALB_DNS}/health | jq -c '.' 2>/dev/null || echo "  ❌ Unreachable"
    echo ""

    # ASG status
    echo "ASG Instances:"
    aws autoscaling describe-auto-scaling-groups \
      --auto-scaling-group-names $(terraform output -raw backend_asg_name) \
      --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]' \
      --output table 2>/dev/null || echo "  ❌ Failed to query ASG"
    echo ""

    echo "Press Ctrl+C to exit..."
    sleep 30
done
```

---

## Troubleshooting

### Issue: ALB Returns 502 Bad Gateway

**Symptoms:** Browser shows 502 error when accessing the API.

**Diagnosis:**

```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# SSH to instance and check service
ssh -i key.pem ec2-user@${INSTANCE_IP}
sudo systemctl status ai-tutor-backend
sudo journalctl -u ai-tutor-backend -n 100 --no-pager

# Check if port 8000 is listening
sudo ss -tlnp | grep 8000
```

**Solutions:**

1. Restart the backend service: `sudo systemctl restart ai-tutor-backend`
2. Check logs for Python errors: `sudo tail -100 /var/log/ai-tutor/error.log`
3. Verify Gunicorn can import the app: `cd /opt/ai-tutor/backend && source venv/bin/activate && python -c "from src.app import app"`

### Issue: Ollama Not Responding

**Symptoms:** Health check shows `ollama.healthy: false`

**Diagnosis:**

```bash
# On EC2 instance
sudo systemctl status ollama
sudo journalctl -u ollama -n 50

# Check if model is loaded
ollama list

# Test Ollama directly
curl http://localhost:11434/api/tags
```

**Solutions:**

1. Restart Ollama: `sudo systemctl restart ollama`
2. Pull model if missing: `ollama pull llama3.2:1b`
3. Check disk space: `df -h` (models need ~2-4GB)
4. Increase instance type if OOM: Consider `t3.large` or `t3.xlarge`

### Issue: Session Creation Timeout

**Symptoms:** POST to `/api/v2/sessions` takes forever or times out.

**Diagnosis:**

```bash
# Check Ollama response time
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.2:1b", "prompt": "Hello", "stream": false}'

# Check backend logs during session creation
sudo journalctl -u ai-tutor-backend -f
```

**Solutions:**

1. Use smaller model: `llama3.2:1b` instead of `llama3.2`
2. Increase EC2 instance type
3. Increase Gunicorn timeout in systemd service
4. Check if content extraction is hanging on bad URLs

### Issue: Lex Bot Not Working

**Symptoms:** Lex bot doesn't respond or returns errors.

**Diagnosis:**

```bash
# Check Lambda logs
aws logs tail /aws/lambda/ai-tutor-lex-fulfillment --follow

# Test Lambda directly
aws lambda invoke \
  --function-name ai-tutor-lex-fulfillment \
  --payload '{"test": true}' \
  /tmp/response.json && cat /tmp/response.json

# Verify bot alias exists
aws lexv2-models list-bot-aliases --bot-id ${LEX_BOT_ID}

# Check Cognito permissions
aws cognito-identity get-identity-pool-roles \
  --identity-pool-id ${COGNITO_POOL_ID}
```

**Solutions:**

1. Create bot alias if missing (see Phase 1.4)
2. Rebuild bot version in AWS Console
3. Check Lambda has permission to call backend

### Issue: Audio Not Generating

**Symptoms:** Podcast audio fails to generate or play.

**Diagnosis:**

```bash
# Test Polly directly
aws polly synthesize-speech \
  --text "Hello world" \
  --output-format mp3 \
  --voice-id Matthew \
  /tmp/test.mp3 && file /tmp/test.mp3

# Check S3 bucket permissions
aws s3 ls s3://${S3_BUCKET}/

# Check IAM role on EC2
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

**Solutions:**

1. Verify IAM role has `polly:SynthesizeSpeech` permission
2. Check S3 bucket CORS configuration
3. Ensure S3 bucket exists and is accessible

---

## Rollback Procedures

### Rollback Application Code

```bash
# SSH to instance
ssh -i key.pem ec2-user@${INSTANCE_IP}

# Option 1: Git rollback
cd /opt/ai-tutor/backend
sudo -u appuser git log --oneline -5  # Find previous commit
sudo -u appuser git checkout <previous-commit>
sudo systemctl restart ai-tutor-backend

# Option 2: Restore from backup
sudo mv /opt/ai-tutor/backend /opt/ai-tutor/backend-broken
sudo mv /opt/ai-tutor/backend-backup /opt/ai-tutor/backend
sudo systemctl restart ai-tutor-backend
```

### Rollback Infrastructure

```bash
cd terraform

# Option 1: Revert Terraform code and apply
git checkout HEAD~1 -- .
terraform plan
terraform apply

# Option 2: Import from backup state
cp terraform.tfstate.backup terraform.tfstate
terraform plan
```

### Emergency: Force Replace Instance

```bash
# Terminate unhealthy instance (ASG will replace it)
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $(terraform output -raw backend_asg_name) \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

aws autoscaling terminate-instance-in-auto-scaling-group \
  --instance-id ${INSTANCE_ID} \
  --no-should-decrement-desired-capacity

# Watch new instance come up
watch -n 10 "aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $(terraform output -raw backend_asg_name) \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]' \
  --output table"
```

---

## Cleanup and Teardown

### Complete Infrastructure Destruction

```bash
cd terraform

# Step 1: Empty S3 buckets (required before destroy)
S3_BUCKET=$(terraform output -raw audio_bucket_name)
aws s3 rm s3://${S3_BUCKET} --recursive

# If you created a frontend bucket
aws s3 rm s3://${FRONTEND_BUCKET} --recursive

# Step 2: Delete Lex bot alias (manual resource)
LEX_BOT_ID=$(terraform output -raw lex_bot_id)
aws lexv2-models list-bot-aliases --bot-id ${LEX_BOT_ID} --query 'botAliasSummaries[*].botAliasId' --output text | \
  xargs -I {} aws lexv2-models delete-bot-alias --bot-alias-id {} --bot-id ${LEX_BOT_ID}

# Step 3: Destroy all infrastructure
terraform destroy

# Type 'yes' to confirm
# Wait 5-10 minutes for all resources to be deleted
```

### Partial Cleanup (Scale Down to Save Costs)

```bash
# Scale ASG to zero instances
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name $(terraform output -raw backend_asg_name) \
  --min-size 0 \
  --max-size 0 \
  --desired-capacity 0

# To scale back up
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name $(terraform output -raw backend_asg_name) \
  --min-size 1 \
  --max-size 3 \
  --desired-capacity 1
```

---

## Quick Reference Commands

```bash
# =============================================
# INFRASTRUCTURE
# =============================================

# Get ALB URL
terraform output alb_dns_name

# Get all outputs
terraform output -json | jq

# Validate Terraform
terraform validate && terraform plan

# =============================================
# EC2 ACCESS
# =============================================

# SSH to backend instance
ssh -i ~/.ssh/key.pem ec2-user@$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*backend*" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# =============================================
# SERVICE MANAGEMENT (on EC2)
# =============================================

# Restart services
sudo systemctl restart ai-tutor-backend
sudo systemctl restart ollama

# View logs
sudo journalctl -u ai-tutor-backend -f
sudo journalctl -u ollama -f

# Check status
sudo systemctl status ai-tutor-backend ollama

# =============================================
# TESTING
# =============================================

# Health check
curl http://$(terraform output -raw alb_dns_name)/health | jq

# Create session
curl -X POST http://$(terraform output -raw alb_dns_name)/api/v2/sessions \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq

# =============================================
# LOGS
# =============================================

# Backend logs
aws logs tail /ai-tutor/backend --follow

# Lambda logs
aws logs tail /aws/lambda/$(terraform output -raw lambda_function_name) --follow
```

---

## Appendix: Cost Estimates

| Resource                   | Monthly Cost (Estimate) |
| -------------------------- | ----------------------- |
| EC2 t3.medium (1 instance) | ~$30                    |
| ALB                        | ~$20                    |
| S3 (10GB audio)            | ~$0.25                  |
| Lambda (1M requests)       | ~$0.20                  |
| Lex (10K requests)         | ~$0.75                  |
| CloudWatch Logs (10GB)     | ~$5                     |
| **Total (minimum)**        | **~$60/month**          |

> **Note:** Costs increase with more instances, higher traffic, and more audio storage. Use AWS Cost Explorer for accurate tracking.
