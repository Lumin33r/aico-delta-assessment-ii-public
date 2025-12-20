#!/bin/bash
# =============================================================================
# AI Personal Tutor - Infrastructure Verification Script
# =============================================================================
# Verifies all AWS components are deployed and functioning correctly.
# Run from the terraform directory after deployment.
# =============================================================================

# Don't exit on error - we want to check all components
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to terraform directory if not already there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "AI Personal Tutor - Infrastructure Check"
echo "========================================"
echo "Timestamp: $(date)"
echo ""

# Function to check status
check() {
    local name=$1
    local result=$2
    local expected=$3

    if [[ "$result" == *"$expected"* ]] || [[ "$result" == "$expected" ]]; then
        echo -e "${GREEN}✓${NC} $name: $result"
        return 0
    else
        echo -e "${RED}✗${NC} $name: $result (expected: $expected)"
        return 1
    fi
}

# Function to check with custom pass condition
check_not_empty() {
    local name=$1
    local result=$2

    if [[ -n "$result" ]] && [[ "$result" != "null" ]] && [[ "$result" != "None" ]]; then
        echo -e "${GREEN}✓${NC} $name: $result"
        return 0
    else
        echo -e "${RED}✗${NC} $name: EMPTY or NULL"
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Get Terraform outputs
echo "--- Fetching Terraform Outputs ---"
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
ASG_NAME=$(terraform output -raw backend_asg_name 2>/dev/null || echo "")
BUCKET=$(terraform output -raw audio_bucket_name 2>/dev/null || echo "")
LAMBDA=$(terraform output -raw lambda_function_name 2>/dev/null || echo "")
LEX_BOT=$(terraform output -raw lex_bot_id 2>/dev/null || echo "")
COGNITO=$(terraform output -raw cognito_identity_pool_id 2>/dev/null || echo "")
VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "")
REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-west-2")

if [[ -z "$ALB_DNS" ]]; then
    echo -e "${RED}ERROR: Could not get Terraform outputs. Run 'terraform apply' first.${NC}"
    exit 1
fi

echo ""
echo "=== 1. VPC & NETWORKING ==="
VPC_STATE=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID --query 'Vpcs[0].State' --output text 2>/dev/null || echo "ERROR")
check "VPC State" "$VPC_STATE" "available"

SUBNET_COUNT=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'length(Subnets)' --output text 2>/dev/null || echo "0")
check "Subnets" "$SUBNET_COUNT subnets" "4"

IGW=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query 'InternetGateways[0].Attachments[0].State' --output text 2>/dev/null || echo "ERROR")
check "Internet Gateway" "$IGW" "available"

echo ""
echo "=== 2. APPLICATION LOAD BALANCER ==="
ALB_STATE=$(aws elbv2 describe-load-balancers --query "LoadBalancers[?DNSName=='$ALB_DNS'].State.Code" --output text 2>/dev/null || echo "ERROR")
check "ALB State" "$ALB_STATE" "active"

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "http://$ALB_DNS/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "304" ]]; then
    echo -e "${GREEN}✓${NC} ALB HTTP Response: $HTTP_CODE"
else
    echo -e "${RED}✗${NC} ALB HTTP Response: $HTTP_CODE (expected 200)"
fi

# Get target group health
TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName,'ai-tutor')].TargetGroupArn" --output text 2>/dev/null | head -1)
if [[ -n "$TG_ARN" ]]; then
    HEALTHY_TARGETS=$(aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`] | length(@)' --output text 2>/dev/null || echo "0")
    check "Healthy Targets" "$HEALTHY_TARGETS" "1"
fi

echo ""
echo "=== 3. AUTO SCALING GROUP ==="
ASG_INFO=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$ASG_NAME" --query 'AutoScalingGroups[0].{Desired:DesiredCapacity,InService:length(Instances[?LifecycleState==`InService`])}' --output text 2>/dev/null || echo "ERROR")
check_not_empty "ASG Instances" "$ASG_INFO"

INSTANCE_COUNT=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$ASG_NAME" --query 'AutoScalingGroups[0].Instances | length(@)' --output text 2>/dev/null || echo "0")
echo "   Running instances: $INSTANCE_COUNT"

echo ""
echo "=== 4. EC2 INSTANCES ==="
INSTANCE_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:aws:autoscaling:groupName,Values=$ASG_NAME" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text 2>/dev/null)

if [[ -n "$INSTANCE_IDS" ]]; then
    for INSTANCE_ID in $INSTANCE_IDS; do
        INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
        check "Instance $INSTANCE_ID" "$INSTANCE_STATE" "running"
    done
else
    echo -e "${RED}✗${NC} No running instances found"
fi

echo ""
echo "=== 5. S3 BUCKET ==="
BUCKET_EXISTS=$(aws s3api head-bucket --bucket "$BUCKET" 2>&1 && echo "exists" || echo "ERROR")
check "Bucket $BUCKET" "$BUCKET_EXISTS" "exists"

CORS=$(aws s3api get-bucket-cors --bucket "$BUCKET" --query 'CORSRules[0].AllowedMethods' --output text 2>/dev/null || echo "NOT_SET")
check_not_empty "CORS Configuration" "$CORS"

echo ""
echo "=== 6. LAMBDA FUNCTION ==="
LAMBDA_STATE=$(aws lambda get-function --function-name "$LAMBDA" --query 'Configuration.State' --output text 2>/dev/null || echo "ERROR")
check "Lambda State" "$LAMBDA_STATE" "Active"

LAMBDA_RUNTIME=$(aws lambda get-function --function-name "$LAMBDA" --query 'Configuration.Runtime' --output text 2>/dev/null || echo "ERROR")
check "Lambda Runtime" "$LAMBDA_RUNTIME" "python"

echo ""
echo "=== 7. AMAZON LEX BOT ==="
LEX_STATUS=$(aws lexv2-models describe-bot --bot-id "$LEX_BOT" --query 'botStatus' --output text 2>/dev/null || echo "ERROR")
check "Lex Bot Status" "$LEX_STATUS" "Available"

ALIAS_COUNT=$(aws lexv2-models list-bot-aliases --bot-id "$LEX_BOT" --query 'botAliasSummaries | length(@)' --output text 2>/dev/null || echo "0")
if [[ "$ALIAS_COUNT" -gt 0 ]]; then
    echo -e "${GREEN}✓${NC} Lex Bot Aliases: $ALIAS_COUNT"
else
    warn "No Lex bot aliases found - create one with 'aws lexv2-models create-bot-alias'"
fi

echo ""
echo "=== 8. COGNITO IDENTITY POOL ==="
COGNITO_NAME=$(aws cognito-identity describe-identity-pool --identity-pool-id "$COGNITO" --query 'IdentityPoolName' --output text 2>/dev/null || echo "ERROR")
check_not_empty "Cognito Pool" "$COGNITO_NAME"

UNAUTH=$(aws cognito-identity describe-identity-pool --identity-pool-id "$COGNITO" --query 'AllowUnauthenticatedIdentities' --output text 2>/dev/null || echo "false")
check "Unauthenticated Access" "$UNAUTH" "True"

echo ""
echo "=== 9. API HEALTH CHECKS ==="
API_HEALTH=$(curl -s --connect-timeout 10 "http://$ALB_DNS/api/health" 2>/dev/null || echo '{"status":"error"}')
API_STATUS=$(echo "$API_HEALTH" | jq -r '.status // "error"' 2>/dev/null || echo "error")
check "API Health" "$API_STATUS" "healthy"

OLLAMA_STATUS=$(echo "$API_HEALTH" | jq -r '.services.ollama // "unknown"' 2>/dev/null || echo "unknown")
if [[ "$OLLAMA_STATUS" == "healthy" ]]; then
    echo -e "${GREEN}✓${NC} Ollama Service: $OLLAMA_STATUS"
else
    warn "Ollama Service: $OLLAMA_STATUS (may still be loading model)"
fi

echo ""
echo "=== 10. POSTGRESQL DATABASE (Docker) ==="
# PostgreSQL runs inside Docker on EC2, check via API database health endpoint
DB_STATUS=$(echo "$API_HEALTH" | jq -r '.services.database // "unknown"' 2>/dev/null || echo "unknown")
if [[ "$DB_STATUS" == "healthy" ]]; then
    echo -e "${GREEN}✓${NC} PostgreSQL: $DB_STATUS"
elif [[ "$DB_STATUS" == "unknown" ]]; then
    warn "PostgreSQL: Status not in health endpoint (check container directly)"
else
    echo -e "${RED}✗${NC} PostgreSQL: $DB_STATUS"
fi

# Check if we can reach the first running instance to verify containers
if [[ -n "$INSTANCE_IDS" ]]; then
    FIRST_INSTANCE=$(echo "$INSTANCE_IDS" | awk '{print $1}')
    echo "   To verify PostgreSQL container on EC2:"
    echo "   aws ssm start-session --target $FIRST_INSTANCE"
    echo "   Then run: cd /opt/ai-tutor/app && sudo docker compose ps postgres"
fi

echo ""
echo "=== 11. CLOUDWATCH LOGS ==="
LAMBDA_LOG_GROUP="/aws/lambda/$LAMBDA"
LOG_EXISTS=$(aws logs describe-log-groups --log-group-name-prefix "$LAMBDA_LOG_GROUP" --query 'logGroups[0].logGroupName' --output text 2>/dev/null || echo "")
check_not_empty "Lambda Log Group" "$LOG_EXISTS"

echo ""
echo "========================================"
echo "         VERIFICATION SUMMARY"
echo "========================================"
echo ""
echo "ALB URL: http://$ALB_DNS"
echo "API Health: http://$ALB_DNS/api/health"
echo "Region: $REGION"
echo ""
echo "Docker Containers on EC2:"
echo "  - frontend (nginx:80)"
echo "  - backend (flask:8000)"
echo "  - ollama (llm:11434)"
echo "  - postgres (db:5432)"
echo ""
echo "To connect to EC2 instance:"
echo "  aws ssm start-session --target $FIRST_INSTANCE"
echo ""
echo "To check all containers:"
echo "  cd /opt/ai-tutor/app && sudo docker compose ps"
echo ""
echo "To view Lambda logs:"
echo "  aws logs tail $LAMBDA_LOG_GROUP --follow"
echo ""
echo "========================================"
