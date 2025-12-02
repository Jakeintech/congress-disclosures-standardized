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
REGION=$(echo "$OUTPUTS" | jq -r '.region.value')
ENVIRONMENT=$(echo "$OUTPUTS" | jq -r '.environment.value')

# Worker Lambdas
INGEST_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_ingest_zip_name.value')
INGEST_LAMBDA_ARN=$(echo "$OUTPUTS" | jq -r '.lambda_ingest_zip_arn.value')
EXTRACT_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_extract_document_name.value')
EXTRACT_LAMBDA_ARN=$(echo "$OUTPUTS" | jq -r '.lambda_extract_document_arn.value')
EXTRACT_STRUCTURED_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_extract_structured_code_name.value')
EXTRACT_STRUCTURED_LAMBDA_ARN=$(echo "$OUTPUTS" | jq -r '.lambda_extract_structured_code_arn.value')
DATA_QUALITY_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_data_quality_validator_name.value')
GOLD_SEED_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_gold_seed_name.value')
GOLD_SEED_MEMBERS_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_gold_seed_members_name.value')
INDEX_TO_SILVER_LAMBDA=$(echo "$OUTPUTS" | jq -r '.lambda_index_to_silver_name.value')
INDEX_TO_SILVER_LAMBDA_ARN=$(echo "$OUTPUTS" | jq -r '.lambda_index_to_silver_arn.value')

# SQS Queues
SQS_EXTRACTION_URL=$(echo "$OUTPUTS" | jq -r '.sqs_extraction_queue_url.value')
SQS_EXTRACTION_ARN=$(echo "$OUTPUTS" | jq -r '.sqs_extraction_queue_arn.value')
SQS_EXTRACTION_DLQ_URL=$(echo "$OUTPUTS" | jq -r '.sqs_dlq_url.value')
SQS_EXTRACTION_DLQ_ARN=$(echo "$OUTPUTS" | jq -r '.sqs_dlq_arn.value')
SQS_CODE_EXTRACTION_URL=$(echo "$OUTPUTS" | jq -r '.code_extraction_queue_url.value')
SQS_CODE_EXTRACTION_ARN=$(echo "$OUTPUTS" | jq -r '.code_extraction_queue_arn.value')

# DynamoDB
DYNAMODB_TABLE_NAME=$(echo "$OUTPUTS" | jq -r '.dynamodb_table_name.value')
DYNAMODB_TABLE_ARN=$(echo "$OUTPUTS" | jq -r '.dynamodb_table_arn.value')

# IAM Roles
IAM_LAMBDA_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.lambda_execution_role_arn.value')
IAM_GITHUB_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.github_actions_role_arn.value')

# S3
S3_BUCKET_ARN=$(echo "$OUTPUTS" | jq -r '.s3_bucket_arn.value')
S3_BUCKET_DOMAIN=$(echo "$OUTPUTS" | jq -r '.s3_bucket_domain_name.value')
S3_WEBSITE_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.s3_website_endpoint.value')

# API Gateway
API_GATEWAY_ID=$(echo "$OUTPUTS" | jq -r '.api_gateway_id.value')
API_GATEWAY_EXECUTION_ARN=$(echo "$OUTPUTS" | jq -r '.api_gateway_execution_arn.value')

# SNS
SNS_TOPIC_ARN=$(echo "$OUTPUTS" | jq -r '.sns_topic_arn.value')

# CloudWatch
DASHBOARD_URL=$(echo "$OUTPUTS" | jq -r '.cloudwatch_dashboard_url.value')

echo "Extracted values from Terraform:"
echo "  S3_BUCKET: $S3_BUCKET"
echo "  API_GATEWAY_URL: $API_GATEWAY_URL"
echo "  REGION: $REGION"
echo "  ENVIRONMENT: $ENVIRONMENT"

# ============================================================================
# Generate .env file
# ============================================================================

# Preserve manual values from existing .env
CONGRESS_KEY=""
ALLOWED_IPS=""

if [ -f "$ENV_FILE" ]; then
    # Extract values if they exist, suppress errors if grep fails
    CONGRESS_KEY=$(grep "^CONGRESS_GOV_API_KEY=" "$ENV_FILE" | cut -d= -f2- || echo "")
    ALLOWED_IPS=$(grep "^ADMIN_ALLOWED_IPS=" "$ENV_FILE" | cut -d= -f2- || echo "")
    
    # Backup existing file
    cp "$ENV_FILE" "$ENV_FILE.bak"
    echo "Backed up existing .env to .env.bak"
fi

echo "Generating new .env file with structured sections..."

# Generate new content
cat > "$ENV_FILE" <<EOF
# ============================================================================
# User Configuration
# ============================================================================
# API Key for Congress.gov (Required for some ingestion tasks)
CONGRESS_GOV_API_KEY=${CONGRESS_KEY}

# Admin Access Control
# Comma-separated list of authorized IP addresses for admin page access
ADMIN_ALLOWED_IPS=${ALLOWED_IPS}

# ============================================================================
# Core Infrastructure
# ============================================================================
AWS_REGION=${REGION}
ENVIRONMENT=${ENVIRONMENT}
INFRA_LAST_SYNCED=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ============================================================================
# Data Lake (S3)
# ============================================================================
S3_BUCKET_NAME=${S3_BUCKET}
S3_BUCKET_ARN=${S3_BUCKET_ARN}
S3_BUCKET_DOMAIN=${S3_BUCKET_DOMAIN}
S3_WEBSITE_ENDPOINT=${S3_WEBSITE_ENDPOINT}

# ============================================================================
# API Gateway (Public API)
# ============================================================================
API_GATEWAY_ID=${API_GATEWAY_ID}
API_GATEWAY_URL=${API_GATEWAY_URL}
API_GATEWAY_EXECUTION_ARN=${API_GATEWAY_EXECUTION_ARN}

# ============================================================================
# Messaging (SQS & SNS)
# ============================================================================
# Extraction Queue (PDF Processing)
SQS_EXTRACTION_URL=${SQS_EXTRACTION_URL}
SQS_EXTRACTION_ARN=${SQS_EXTRACTION_ARN}

# Extraction Dead Letter Queue (Failed Jobs)
SQS_EXTRACTION_DLQ_URL=${SQS_EXTRACTION_DLQ_URL}
SQS_EXTRACTION_DLQ_ARN=${SQS_EXTRACTION_DLQ_ARN}

# Code Extraction Queue (Structured Data)
SQS_CODE_EXTRACTION_URL=${SQS_CODE_EXTRACTION_URL}
SQS_CODE_EXTRACTION_ARN=${SQS_CODE_EXTRACTION_ARN}

# SNS Alerts
SNS_TOPIC_ARN=${SNS_TOPIC_ARN}

# Legacy Compatibility Variables
EXTRACTION_QUEUE_URL=${SQS_EXTRACTION_URL}
CODE_EXTRACTION_QUEUE_URL=${SQS_CODE_EXTRACTION_URL}

# ============================================================================
# Database (DynamoDB)
# ============================================================================
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME}
DYNAMODB_TABLE_ARN=${DYNAMODB_TABLE_ARN}

# ============================================================================
# Security (IAM Roles)
# ============================================================================
IAM_LAMBDA_ROLE_ARN=${IAM_LAMBDA_ROLE_ARN}
IAM_GITHUB_ROLE_ARN=${IAM_GITHUB_ROLE_ARN}

# ============================================================================
# Monitoring (CloudWatch)
# ============================================================================
CLOUDWATCH_DASHBOARD_URL=${DASHBOARD_URL}

# Log Groups
LOG_GROUP_INGEST=${LOG_GROUP_INGEST}
LOG_GROUP_EXTRACT=${LOG_GROUP_EXTRACT}
LOG_GROUP_EXTRACT_STRUCTURED=${LOG_GROUP_EXTRACT_STRUCTURED}

# ============================================================================
# Compute: Worker Lambdas
# ============================================================================
LAMBDA_INGEST_FUNCTION_NAME=${INGEST_LAMBDA}
LAMBDA_INGEST_FUNCTION_ARN=${INGEST_LAMBDA_ARN}

LAMBDA_EXTRACT_FUNCTION_NAME=${EXTRACT_LAMBDA}
LAMBDA_EXTRACT_FUNCTION_ARN=${EXTRACT_LAMBDA_ARN}

LAMBDA_EXTRACT_STRUCTURED_FUNCTION_NAME=${EXTRACT_STRUCTURED_LAMBDA}
LAMBDA_EXTRACT_STRUCTURED_FUNCTION_ARN=${EXTRACT_STRUCTURED_LAMBDA_ARN}

LAMBDA_DATA_QUALITY_FUNCTION_NAME=${DATA_QUALITY_LAMBDA}

LAMBDA_GOLD_SEED_FUNCTION_NAME=${GOLD_SEED_LAMBDA}
LAMBDA_GOLD_SEED_MEMBERS_FUNCTION_NAME=${GOLD_SEED_MEMBERS_LAMBDA}

LAMBDA_INDEX_TO_SILVER_FUNCTION_NAME=${INDEX_TO_SILVER_LAMBDA}
LAMBDA_INDEX_TO_SILVER_FUNCTION_ARN=${INDEX_TO_SILVER_LAMBDA_ARN}

# ============================================================================
# Compute: API Lambdas
# ============================================================================
EOF

# Append API Lambdas (dynamically generated)
echo "# API Function Names" >> "$ENV_FILE"
echo "$OUTPUTS" | jq -r '.api_lambda_functions.value | to_entries | .[] | .key + "=" + .value' | while read -r line; do
    key=$(echo "$line" | cut -d= -f1 | tr '[:lower:]' '[:upper:]')
    value=$(echo "$line" | cut -d= -f2)
    echo "LAMBDA_API_${key}_FUNCTION_NAME=${value}" >> "$ENV_FILE"
done

echo "" >> "$ENV_FILE"
echo "# API Function ARNs" >> "$ENV_FILE"
echo "$OUTPUTS" | jq -r '.api_lambda_arns.value | to_entries | .[] | .key + "=" + .value' | while read -r line; do
    key=$(echo "$line" | cut -d= -f1 | tr '[:lower:]' '[:upper:]')
    value=$(echo "$line" | cut -d= -f2)
    echo "LAMBDA_API_${key}_FUNCTION_ARN=${value}" >> "$ENV_FILE"
done

echo ""
echo "✅ Environment sync complete!"
echo ""
echo "Updated .env file at: $ENV_FILE"
echo ""
echo "You can now use these values in your local scripts and applications."
