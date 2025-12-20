#!/bin/bash
# =============================================================================
# AI Personal Tutor - Fetch Secrets from AWS Secrets Manager
# =============================================================================
# This script retrieves PostgreSQL credentials from AWS Secrets Manager
# and writes them to the .env file for docker-compose.
#
# Usage: ./fetch-secrets.sh [SECRET_NAME] [REGION]
# =============================================================================

set -e

# Configuration (can be overridden by environment variables or arguments)
SECRET_NAME="${1:-${POSTGRES_SECRET_NAME:-}}"
AWS_REGION="${2:-${AWS_REGION:-us-west-2}}"
ENV_FILE="${ENV_FILE:-.env}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

if [[ -z "$SECRET_NAME" ]]; then
    log_error "SECRET_NAME is required. Set POSTGRES_SECRET_NAME environment variable or pass as argument."
    echo "Usage: $0 <secret-name> [region]"
    exit 1
fi

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    log_error "jq is not installed. Please install it first."
    exit 1
fi

# -----------------------------------------------------------------------------
# Fetch Secrets
# -----------------------------------------------------------------------------

log_info "Fetching PostgreSQL credentials from Secrets Manager..."
log_info "Secret Name: $SECRET_NAME"
log_info "Region: $AWS_REGION"

# Get secret value
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'SecretString' \
    --output text 2>&1)

if [[ $? -ne 0 ]]; then
    log_error "Failed to retrieve secret from Secrets Manager"
    log_error "$SECRET_JSON"
    exit 1
fi

# Parse credentials from JSON
POSTGRES_USER=$(echo "$SECRET_JSON" | jq -r '.username')
POSTGRES_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password')
POSTGRES_DB=$(echo "$SECRET_JSON" | jq -r '.database')

# Validate parsed values
if [[ -z "$POSTGRES_USER" ]] || [[ "$POSTGRES_USER" == "null" ]]; then
    log_error "Failed to parse username from secret"
    exit 1
fi

if [[ -z "$POSTGRES_PASSWORD" ]] || [[ "$POSTGRES_PASSWORD" == "null" ]]; then
    log_error "Failed to parse password from secret"
    exit 1
fi

if [[ -z "$POSTGRES_DB" ]] || [[ "$POSTGRES_DB" == "null" ]]; then
    log_error "Failed to parse database from secret"
    exit 1
fi

log_info "Successfully retrieved credentials for user: $POSTGRES_USER"

# -----------------------------------------------------------------------------
# Update Environment File
# -----------------------------------------------------------------------------

log_info "Updating environment file: $ENV_FILE"

# Create backup if file exists
if [[ -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    log_info "Created backup: ${ENV_FILE}.bak"
fi

# Check if .env file exists and update/add PostgreSQL variables
if [[ -f "$ENV_FILE" ]]; then
    # Remove existing PostgreSQL variables (if any)
    grep -v "^POSTGRES_USER=" "$ENV_FILE" | \
    grep -v "^POSTGRES_PASSWORD=" | \
    grep -v "^POSTGRES_DB=" > "${ENV_FILE}.tmp" || true
    mv "${ENV_FILE}.tmp" "$ENV_FILE"
fi

# Append PostgreSQL credentials
cat >> "$ENV_FILE" << EOF

# PostgreSQL Credentials (fetched from AWS Secrets Manager)
# Secret: $SECRET_NAME
# Retrieved: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
EOF

# Set secure permissions on .env file
chmod 600 "$ENV_FILE"

log_info "Environment file updated successfully"
log_info "PostgreSQL credentials are ready for docker-compose"

# -----------------------------------------------------------------------------
# Verify (optional)
# -----------------------------------------------------------------------------

if [[ "${VERIFY:-false}" == "true" ]]; then
    log_info "Verifying .env file contents (masked):"
    echo "  POSTGRES_USER=$POSTGRES_USER"
    echo "  POSTGRES_PASSWORD=********"
    echo "  POSTGRES_DB=$POSTGRES_DB"
fi

log_info "Done! You can now run: docker compose up -d"
