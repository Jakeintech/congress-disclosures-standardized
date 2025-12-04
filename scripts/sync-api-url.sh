#!/bin/bash
# scripts/sync-api-url.sh
# Sync API Gateway URL from Terraform outputs to website config and OpenAPI spec

set -e

# Get the API Gateway URL from Terraform outputs
API_URL=$(terraform -chdir=infra/terraform output -json | jq -r '.api_gateway_url.value')

if [ -z "$API_URL" ] || [ "$API_URL" = "null" ]; then
    echo "Error: Could not retrieve API Gateway URL from Terraform outputs"
    exit 1
fi

echo "API Gateway URL: $API_URL"

# Update website/config.js
sed -i.bak "s|const API_GATEWAY_URL = \".*\"|const API_GATEWAY_URL = \"$API_URL\"|g" website/config.js
echo "✓ Updated website/config.js"

# Update docs/openapi.yaml
sed -i.bak "s|url: https://.*\.execute-api\.us-east-1\.amazonaws\.com|url: $API_URL|g" docs/openapi.yaml
echo "✓ Updated docs/openapi.yaml"

# Clean up backup files
rm -f website/config.js.bak docs/openapi.yaml.bak

echo "✓ API Gateway URL synchronized successfully"
