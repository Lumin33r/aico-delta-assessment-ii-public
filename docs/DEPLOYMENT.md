# AI Personal Tutor - Deployment Guide

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Terraform >= 1.5.0
- Node.js >= 18 and npm
- Python >= 3.11
- Docker (optional, for local Ollama)

## Quick Start

### 1. Clone and Setup

```bash
cd aico-delta-assessment-ii
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
cd terraform
terraform init

# Review the plan
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Save outputs for configuration
terraform output -json > ../outputs.json
```

### 3. Configure Backend

```bash
cd ../backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from Terraform outputs
cat > .env << EOF
$(terraform -chdir=../terraform output -raw backend_env_config)
EOF

# Test locally
python src/app.py
```

### 4. Configure Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file from Terraform outputs
cat > .env << EOF
$(terraform -chdir=../terraform output -raw frontend_env_config)
EOF

# Run development server
npm run dev
```

## Environment Variables

### Backend (.env)

```bash
# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET=ai-tutor-audio-xxxxxxxx

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Server Configuration
PORT=8000
FLASK_ENV=production
```

### Frontend (.env)

```bash
# AWS Configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_IDENTITY_POOL_ID=us-east-1:xxxxxxxx
VITE_LEX_BOT_ID=XXXXXXXXXX
VITE_LEX_BOT_ALIAS_ID=XXXXXXXXXX

# API Configuration
VITE_API_URL=http://your-alb-dns-name.region.elb.amazonaws.com
```

## Local Development

### Running Ollama Locally

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull llama3.2

# Start Ollama server
ollama serve
```

### Running Backend

```bash
cd backend
source venv/bin/activate
python src/app.py
```

### Running Frontend

```bash
cd frontend
npm run dev
```

## Production Deployment

### Deploy to EC2

The Terraform configuration automatically:

1. Creates EC2 instances with user data scripts
2. Installs and configures Ollama, Flask, and Nginx
3. Sets up systemd services for auto-start

### Manual Deployment

If you need to manually deploy:

```bash
# SSH to backend EC2
ssh -i your-key.pem ec2-user@backend-ip

# Pull latest code
cd /opt/ai-tutor/backend
git pull origin main

# Restart service
sudo systemctl restart ai-tutor-backend
```

## Terraform Commands

```bash
# Initialize
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy

# Show outputs
terraform output

# Refresh state
terraform refresh
```

## Useful Terraform Outputs

```bash
# Get ALB URL
terraform output alb_dns_name

# Get Lex Bot ID
terraform output lex_bot_id

# Get Cognito Identity Pool ID
terraform output cognito_identity_pool_id

# Get frontend environment config
terraform output frontend_env_config

# Get backend environment config
terraform output backend_env_config
```

## Troubleshooting

### Ollama Not Responding

```bash
# Check Ollama service
sudo systemctl status ollama

# Restart Ollama
sudo systemctl restart ollama

# Check logs
journalctl -u ollama -f
```

### Backend API Errors

```bash
# Check backend service
sudo systemctl status ai-tutor-backend

# View logs
journalctl -u ai-tutor-backend -f

# Check application logs
tail -f /var/log/ai-tutor/app.log
```

### Lex Bot Not Responding

1. Check Lex bot is built and deployed in AWS Console
2. Verify Cognito Identity Pool has correct IAM permissions
3. Check Lambda fulfillment logs in CloudWatch

### Audio Not Playing

1. Verify S3 bucket exists and has correct CORS configuration
2. Check IAM permissions for Polly access
3. Verify presigned URLs are being generated correctly

## Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Ollama health
curl http://localhost:11434/api/tags

# Full API status
curl http://localhost:8000/
```

## Cleanup

```bash
# Destroy all infrastructure
cd terraform
terraform destroy

# Clean S3 bucket first if needed
aws s3 rm s3://your-bucket-name --recursive
```
