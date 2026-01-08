#!/bin/bash
# Build and deploy a specific API Lambda function
# Usage: ./scripts/deploy_api_lambda.sh <function_name>
# Example: ./scripts/deploy_api_lambda.sh get_filings

FUNCTION_NAME=$1
S3_BUCKET="congress-disclosures-standardized"

if [ -z "$FUNCTION_NAME" ]; then
    echo "Usage: $0 <function_name>"
    exit 1
fi

echo "Deploying $FUNCTION_NAME..."

# Create temp build dir
BUILD_DIR="build/api/$FUNCTION_NAME"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy handler
cp "api/lambdas/$FUNCTION_NAME/handler.py" "$BUILD_DIR/"

# Copy shared lib (must be in 'api' package)
mkdir -p "$BUILD_DIR/api"
cp -r "api/lib" "$BUILD_DIR/api/"
touch "$BUILD_DIR/api/__init__.py"

# Create zip
cd "$BUILD_DIR"
zip -r "../$FUNCTION_NAME.zip" . > /dev/null
cd ../../..

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "build/api/$FUNCTION_NAME.zip" "s3://$S3_BUCKET/lambda-deployments/api/$FUNCTION_NAME.zip"

# Update Lambda
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "congress-disclosures-development-api-$FUNCTION_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --s3-key "lambda-deployments/api/$FUNCTION_NAME.zip" \
    --output text

echo "✅ Deployed $FUNCTION_NAME"
