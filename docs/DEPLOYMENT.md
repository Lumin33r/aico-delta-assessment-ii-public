# AI Personal Tutor - Production Deployment Guide

A comprehensive guide for deploying the AI Personal Tutor to AWS using Terraform with containerized services (Docker + Docker Compose).

---

## Quick Start (TL;DR)

For experienced users, here's the streamlined deployment:

```bash
# 1. Deploy Infrastructure
cd terraform

# Update variables for your environment
export TF_VAR_git_repo_url="https://github.com/your-org/ai-personal-tutor.git"
export TF_VAR_lex_bot_alias_id="EU0RH7BDUK"

terraform init && terraform apply -auto-approve

# 2. Create Lex Bot Alias (one-time after initial deploy)
aws lexv2-models create-bot-alias \
  --bot-alias-name prod \
  --bot-id $(terraform output -raw lex_bot_id) \
  --bot-version $(terraform output -raw lex_bot_version) \
  --bot-alias-locale-settings '{"en_US":{"enabled":true}}' \
  --region us-west-2

# 3. Update Terraform with alias ID and redeploy
export TF_VAR_lex_bot_alias_id="<alias-id-from-step-2>"
terraform apply -auto-approve

# 4. Test the deployment
ALB_DNS=$(terraform output -raw alb_dns_name)
curl http://$ALB_DNS/api/health
```

The EC2 instances will automatically:

- Install Docker and Docker Compose
- Clone the repository
- Build and start all containers (Frontend, Backend, Ollama)
- Pull the LLM model

---

## Containerized Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (VPC)                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Application Load Balancer                         │    │
│  │                         (Port 80/443)                                │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│            ┌────────────────────┼────────────────────┐                      │
│            ▼                    │                    ▼                      │
│  ┌──────────────────┐          │          ┌──────────────────┐             │
│  │   EC2 Instance 1 │          │          │   EC2 Instance 2 │             │
│  │   (us-west-2a)   │          │          │   (us-west-2b)   │             │
│  │                  │          │          │                  │             │
│  │ ┌──────────────┐ │          │          │ ┌──────────────┐ │             │
│  │ │   Frontend   │ │          │          │ │   Frontend   │ │             │
│  │ │ (Nginx:80)   │◀┼──────────┘──────────┼▶│ (Nginx:80)   │ │             │
│  │ └──────┬───────┘ │                     │ └──────┬───────┘ │             │
│  │        │ /api    │                     │        │ /api    │             │
│  │        ▼         │                     │        ▼         │             │
│  │ ┌──────────────┐ │                     │ ┌──────────────┐ │             │
│  │ │   Backend    │ │                     │ │   Backend    │ │             │
│  │ │(Flask:8000)  │ │                     │ │(Flask:8000)  │ │             │
│  │ └──────┬───────┘ │                     │ └──────┬───────┘ │             │
│  │        │         │                     │        │         │             │
│  │        ▼         │                     │        ▼         │             │
│  │ ┌──────────────┐ │                     │ ┌──────────────┐ │             │
│  │ │   Ollama     │ │                     │ │   Ollama     │ │             │
│  │ │ (LLM:11434) │ │                     │ │ (LLM:11434) │ │             │
│  │ └──────────────┘ │                     │ └──────────────┘ │             │
│  └──────────────────┘                     └──────────────────┘             │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │  S3 Audio   │  │   Lex Bot   │  │   Cognito   │  │     Lambda      │    │
│  │   Bucket    │  │    (V2)     │  │Identity Pool│  │  Fulfillment    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Container Stack (per EC2 instance)

| Service  | Image            | Port  | Description                    |
| -------- | ---------------- | ----- | ------------------------------ |
| Frontend | nginx:alpine     | 80    | Serves React app, proxies /api |
| Backend  | python:3.11-slim | 8000  | Flask API with Gunicorn        |
| Ollama   | ollama/ollama    | 11434 | Local LLM inference            |

---

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

## Phase 2: Containerized EC2 Deployment

With the containerized deployment, EC2 instances are automatically configured by the user data script to:

1. Install Docker and Docker Compose
2. Clone the repository
3. Build and start all containers

### 2.1 Verify Automatic Deployment

After Terraform applies, wait 5-10 minutes for EC2 instances to fully initialize.

```bash
# Get ALB DNS from Terraform output
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test that the frontend is serving
curl http://${ALB_DNS}/

# Test backend health via API
curl http://${ALB_DNS}/api/health
```

### 2.2 Connect to EC2 for Debugging (if needed)

**Option A: AWS Session Manager (Recommended - No SSH Key Required)**

```bash
# Get instance ID from ASG
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $(terraform output -raw backend_asg_name) \
  --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId | [0]' \
  --output text \
  --region us-west-2)

echo "Instance ID: ${INSTANCE_ID}"

# Connect via Session Manager
aws ssm start-session --target ${INSTANCE_ID} --region us-west-2
```

**Option B: SSH Access**

```bash
# Get instance public IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids ${INSTANCE_ID} \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region us-west-2)

ssh -i ~/.ssh/your-keypair.pem ec2-user@${INSTANCE_IP}
```

### 2.3 Check Container Status

```bash
# Switch to root (containers run as root)
sudo su -

# Navigate to app directory
cd /opt/ai-tutor/app

# Check all container status
docker compose ps

# Expected output:
# NAME                    STATUS                   PORTS
# ai-tutor-frontend       Up (healthy)             0.0.0.0:80->80/tcp
# ai-tutor-backend        Up (healthy)             8000/tcp
# ai-tutor-ollama         Up (healthy)             11434/tcp
```

### 2.4 View Container Logs

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f ollama

# View user-data setup log
cat /var/log/user-data.log
```

### 2.5 Restart Services

```bash
# Restart all containers
docker compose restart

# Restart specific service
docker compose restart backend

# Full rebuild and restart
docker compose down && docker compose up -d --build
```

### 2.6 Update Deployed Code

```bash
cd /opt/ai-tutor/app

# Pull latest code
git pull origin main

# Rebuild and restart containers
docker compose up -d --build

# Check status
docker compose ps
```

### 2.7 Manual Environment Changes

If you need to modify environment variables:

```bash
cd /opt/ai-tutor/app

# Edit the .env file
nano .env

# Restart to pick up changes
docker compose up -d --force-recreate
```

### 2.8 Health Check Script

A health check script is installed at `/opt/ai-tutor/healthcheck.sh`:

```bash
# Run health check
/opt/ai-tutor/healthcheck.sh

# Expected output: "HEALTHY: All services running"
```

# Check logs for errors

sudo journalctl -u ai-tutor-backend -f --no-pager -n 50

````

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
````

---

## Phase 3: Frontend Deployment

With the containerized deployment, the frontend is **automatically deployed** as part of the Docker Compose stack. Nginx serves the React app and proxies API requests to the backend container.

### 3.1 Automatic Deployment (Default)

The frontend is built and deployed automatically when the EC2 instance starts:

1. User data script clones the repository
2. Docker Compose builds the frontend container (multi-stage: Node → Nginx)
3. Environment variables are baked in during build time
4. Nginx serves the app on port 80

**Verify Frontend is Running:**

```bash
# From your local machine
ALB_DNS=$(terraform output -raw alb_dns_name)
curl http://${ALB_DNS}/
```

### 3.2 Rebuild Frontend (After Code Changes)

If you need to rebuild the frontend with new code or environment variables:

```bash
# Connect to EC2
aws ssm start-session --target ${INSTANCE_ID} --region us-west-2
sudo su -

cd /opt/ai-tutor/app

# Update environment variables if needed
nano .env

# Rebuild and restart frontend only
docker compose up -d --build frontend

# Or rebuild all services
docker compose up -d --build
```

### 3.3 Alternative: Local Frontend Development

For active development, run the frontend locally against the deployed backend:

```bash
# On your LOCAL machine
cd frontend

# Create local development environment
cat > .env.local << EOF
VITE_AWS_REGION=us-west-2
VITE_API_URL=http://<ALB_DNS>/api
VITE_LEX_BOT_ID=<your-bot-id>
VITE_LEX_BOT_ALIAS_ID=<your-alias-id>
VITE_COGNITO_IDENTITY_POOL_ID=<your-pool-id>
EOF

# Install dependencies and start dev server
npm install
npm run dev

# Access at http://localhost:3000
```

### 3.4 Alternative: S3 + CloudFront (Production)

For production with global CDN and HTTPS:

```bash
# Build frontend locally
cd frontend
npm install
npm run build

# Create S3 bucket for static hosting
aws s3 mb s3://ai-tutor-frontend-prod --region us-west-2

# Enable static website hosting
aws s3 website s3://ai-tutor-frontend-prod --index-document index.html --error-document index.html

# Upload build
aws s3 sync dist/ s3://ai-tutor-frontend-prod --delete

# Create CloudFront distribution (optional - for HTTPS)
# See AWS documentation for CloudFront setup
```

sudo systemctl enable nginx
sudo systemctl start nginx

# Verify nginx is running

sudo systemctl status nginx

# Test locally

curl http://localhost/

````

**Step 5: Update ALB Target Group for Frontend**

The ALB needs to route traffic to port 80 (Nginx) for the frontend:

```bash
# Check current target group configuration
# Frontend should go to port 80, API to port 8000
````

### 3.3 Option B: Deploy to S3 + CloudFront (Production)

For production deployments with global CDN and HTTPS:

```bash
# On your LOCAL machine
cd ~/codeplatoon/projects/aico-delta-assessment-ii/frontend

# Create S3 bucket for frontend
FRONTEND_BUCKET="ai-tutor-frontend-$(aws sts get-caller-identity --query Account --output text)-$(date +%s)"

aws s3 mb s3://${FRONTEND_BUCKET} --region us-west-2

# Configure for static website hosting
aws s3 website s3://${FRONTEND_BUCKET} \
  --index-document index.html \
  --error-document index.html

# Disable block public access
aws s3api put-public-access-block \
  --bucket ${FRONTEND_BUCKET} \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

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

# Upload frontend build
aws s3 sync dist/ s3://${FRONTEND_BUCKET}/ \
  --delete \
  --cache-control "max-age=31536000" \
  --exclude "index.html"

aws s3 cp dist/index.html s3://${FRONTEND_BUCKET}/index.html \
  --cache-control "no-cache, no-store, must-revalidate"

# Get website URL
echo "Frontend URL: http://${FRONTEND_BUCKET}.s3-website-us-west-2.amazonaws.com"
```

### 3.4 Option C: Run Frontend Locally (Development)

For local development and testing:

```bash
# Terminal 1: Backend (on EC2 or local)
# If testing locally, you need Ollama running locally too

# Terminal 2: Frontend (local machine)
cd ~/codeplatoon/projects/aico-delta-assessment-ii/frontend

# Create local development environment
cat > .env.local << 'EOF'
VITE_AWS_REGION=us-west-2
VITE_API_URL=http://Troy-ai-tutor-dev-alb-148039826.us-west-2.elb.amazonaws.com
VITE_LEX_BOT_ID=YWLKQSVH3F
VITE_LEX_BOT_ALIAS_ID=EU0RH7BDUK
VITE_COGNITO_IDENTITY_POOL_ID=us-west-2:25db7c7c-824a-499b-8968-6cee3d1a6d77
EOF

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend available at http://localhost:5173 (or port shown)
```

### 3.5 Updating the Frontend

When you need to deploy updated frontend code:

**For EC2 deployment:**

```bash
# On local machine
cd ~/codeplatoon/projects/aico-delta-assessment-ii/frontend
npm run build
tar -czvf frontend-dist.tar.gz dist/
aws s3 cp frontend-dist.tar.gz s3://troy-ai-tutor-audio-dev-6344f749/deployments/

# On EC2
cd /home/ec2-user
aws s3 cp s3://troy-ai-tutor-audio-dev-6344f749/deployments/frontend-dist.tar.gz .
tar -xzvf frontend-dist.tar.gz
sudo cp -r dist/* /var/www/ai-tutor/
sudo chown -R nginx:nginx /var/www/ai-tutor/
```

**For S3 deployment:**

```bash
# On local machine
cd ~/codeplatoon/projects/aico-delta-assessment-ii/frontend
npm run build
aws s3 sync dist/ s3://${FRONTEND_BUCKET}/ --delete
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

### Docker Container Issues

#### Issue: Containers Not Starting

**Symptoms:** `docker compose ps` shows containers as "Exited" or "Restarting"

**Diagnosis:**

```bash
# Check container logs
cd /opt/ai-tutor/app
docker compose logs

# Check specific container
docker compose logs backend
docker compose logs frontend
docker compose logs ollama

# Check user-data script execution
cat /var/log/user-data.log
```

**Solutions:**

1. Rebuild containers: `docker compose up -d --build`
2. Check .env file for missing variables
3. Verify disk space: `df -h`
4. Check Docker service: `systemctl status docker`

#### Issue: Frontend Shows "502 Bad Gateway"

**Symptoms:** ALB returns 502 when accessing the application

**Diagnosis:**

```bash
# Check if Nginx container is running
docker compose ps frontend

# Check Nginx logs
docker compose logs frontend

# Test backend connectivity from inside Nginx container
docker exec -it ai-tutor-frontend wget -qO- http://backend:8000/health
```

**Solutions:**

1. Restart containers: `docker compose restart`
2. Check backend health: `docker compose logs backend`
3. Verify network: `docker network ls` and `docker network inspect ai-tutor-network`

#### Issue: Backend Can't Connect to Ollama

**Symptoms:** API requests fail with "connection refused" to Ollama

**Diagnosis:**

```bash
# Check Ollama container status
docker compose ps ollama

# Check Ollama logs
docker compose logs ollama

# Test Ollama from backend container
docker exec -it ai-tutor-backend curl http://ollama:11434/api/tags
```

**Solutions:**

1. Wait for model pull: `docker compose logs model-init`
2. Restart Ollama: `docker compose restart ollama`
3. Check memory limits in docker-compose.yml

#### Issue: Model Not Pulled

**Symptoms:** Ollama returns empty model list

**Diagnosis:**

```bash
# Check model-init container logs
docker compose logs model-init

# List models in Ollama
docker exec -it ai-tutor-ollama ollama list
```

**Solutions:**

```bash
# Manually pull model
docker exec -it ai-tutor-ollama ollama pull llama3.2:1b

# Or restart model-init
docker compose restart model-init
```

### ALB and Target Group Issues

### Issue: ALB Returns 502 Bad Gateway

**Symptoms:** Browser shows 502 error when accessing the API.

**Diagnosis:**

```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# Connect to EC2 and check containers
aws ssm start-session --target ${INSTANCE_ID} --region us-west-2
sudo docker compose -f /opt/ai-tutor/app/docker-compose.yml ps

# Check if port 80 is listening
sudo ss -tlnp | grep 80
```

**Solutions:**

1. Restart all containers: `cd /opt/ai-tutor/app && docker compose restart`
2. Check container logs for errors
3. Verify security group allows port 80 from ALB

### Issue: Ollama Not Responding

**Symptoms:** Health check shows `ollama.healthy: false`

**Diagnosis:**

```bash
# On EC2 instance
docker compose logs ollama

# Check if model is loaded
docker exec -it ai-tutor-ollama ollama list

# Test Ollama directly
docker exec -it ai-tutor-ollama curl http://localhost:11434/api/tags
```

**Solutions:**

1. Restart Ollama: `docker compose restart ollama`
2. Pull model if missing: `docker exec -it ai-tutor-ollama ollama pull llama3.2:1b`
3. Check disk space: `df -h` (models need ~2-4GB)
4. Increase instance type if OOM: Consider `t3.large` or `t3.xlarge`

### Issue: Session Creation Timeout

**Symptoms:** POST to `/api/v2/sessions` takes forever or times out.

**Diagnosis:**

```bash
# Check Ollama response time from backend container
docker exec -it ai-tutor-backend curl -X POST http://ollama:11434/api/generate \
  -d '{"model": "llama3.2:1b", "prompt": "Hello", "stream": false}'

# Check backend logs during session creation
docker compose logs -f backend
```

**Solutions:**

1. Use smaller model: `llama3.2:1b` instead of `llama3.2`
2. Increase EC2 instance type
3. Adjust Ollama resource limits in docker-compose.yml
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
