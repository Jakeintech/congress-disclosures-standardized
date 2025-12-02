#!/bin/bash
#
# Sync Terraform Outputs to Local Environment
# 
# This script runs after 'terraform apply' to update local .env file
# with the latest infrastructure values.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform"
ENV_FILE="$PROJECT_ROOT/.env"

echo "=== Syncing Terraform Outputs to Local Environment ==="

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Terraform directory not found at $TERRAFORM_DIR"
    exit 1
fi

# Get terraform outputs as JSON
cd "$TERRAFORM_DIR"
echo "Fetching Terraform outputs..."
OUTPUTS=$(terraform output -json)

# Extract key values
S3_BUCKET=$(echo "$OUTPUTS" | jq -r '.s3_bucket_id.value')
API_GATEWAY_URL=$(echo "$OUTPUTS" | jq -r '.api_gateway_url.value')
EXTRACTION_QUEUE_URL=$(echo "$OUTPUTS" | jq -r '.sqs_extraction_queue_url.value')
CODE_EXTRACTION_QUEUE_URL=$(echo "$OUTPUTS" | jq -r '.code_extraction_queue_url.value')
INGEST_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_ingest_zip_name.value')
EXTRACT_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_extract_document_name.value')
REGION=$(echo "$OUTPUTS" | jq -r '.region.value')
ENVIRONMENT=$(echo "$OUTPUTS" | jq -r '.environment.value')

echo "Extracted values from Terraform:"
echo "  S3_BUCKET: $S3_BUCKET"
echo "  API_GATEWAY_URL: $API_GATEWAY_URL"
echo "  REGION: $REGION"
echo "  ENVIRONMENT: $ENVIRONMENT"

# Create or update .env file
cd "$PROJECT_ROOT"

# Function to update or append a value in .env
update_env_var() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        # Update existing value (macOS compatible)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        fi
        echo "  Updated $key"
    else
        # Append new value
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "  Added $key"
    fi
}

# Create .env if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating new .env file..."
    touch "$ENV_FILE"
fi

echo ""
echo "Updating .env file..."

# Update all infrastructure-related variables
update_env_var "AWS_REGION" "$REGION"
update_env_var "ENVIRONMENT" "$ENVIRONMENT"
update_env_var "S3_BUCKET_NAME" "$S3_BUCKET"
update_env_var "API_GATEWAY_URL" "$API_GATEWAY_URL"
update_env_var "EXTRACTION_QUEUE_URL" "$EXTRACTION_QUEUE_URL"
update_env_var "CODE_EXTRACTION_QUEUE_URL" "$CODE_EXTRACTION_QUEUE_URL"
update_env_var "LAMBDA_INGEST_FUNCTION_NAME" "$INGEST_LAMBDA"
update_env_var "LAMBDA_EXTRACT_FUNCTION_NAME" "$EXTRACT_LAMBDA"

# Add timestamp
update_env_var "INFRA_LAST_SYNCED" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

echo ""
echo "✅ Environment sync complete!"
echo ""
echo "Updated .env file at: $ENV_FILE"
echo ""
echo "You can now use these values in your local scripts and applications."
