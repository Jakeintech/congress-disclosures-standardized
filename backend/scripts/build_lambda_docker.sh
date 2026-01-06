#!/bin/bash
# Build Lambda function using Docker to ensure correct Linux binaries
# This fixes the numpy import error caused by Mac-built packages
#
# Usage: ./scripts/build_lambda_docker.sh <lambda_name>
# Example: ./scripts/build_lambda_docker.sh house-fd-extract-document

set -e  # Exit on error

# Configuration
LAMBDA_NAME=${1:-"house-fd-extract-document"}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_DIR="$REPO_ROOT/ingestion/lambdas/${LAMBDA_NAME//-/_}"  # Convert hyphens to underscores
BUILD_DIR="$REPO_ROOT/build/$LAMBDA_NAME"
S3_BUCKET="congress-disclosures-standardized"
S3_KEY="lambda-deployments/$LAMBDA_NAME/function.zip"

echo "============================================"
echo "Building Lambda: $LAMBDA_NAME"
echo "Lambda Directory: $LAMBDA_DIR"
echo "============================================"

# Validate Lambda directory exists
if [ ! -d "$LAMBDA_DIR" ]; then
    echo "ERROR: Lambda directory not found: $LAMBDA_DIR"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "$LAMBDA_DIR/Dockerfile" ]; then
    echo "ERROR: Dockerfile not found in $LAMBDA_DIR"
    exit 1
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build Docker image from repo root (Dockerfile expects this context)
echo "Building Docker image..."
cd "$REPO_ROOT"
docker build -f "$LAMBDA_DIR/Dockerfile" -t "$LAMBDA_NAME:latest" .

# Create container (don't run it)
echo "Creating container to extract files..."
CONTAINER_ID=$(docker create "$LAMBDA_NAME:latest")

# Copy Lambda function code from container
echo "Extracting Lambda package..."
docker cp "$CONTAINER_ID:/var/task" "$BUILD_DIR/package"

# Clean up container
docker rm "$CONTAINER_ID"

# Create ZIP file
echo "Creating function.zip..."
cd "$BUILD_DIR/package"
zip -r "$BUILD_DIR/function.zip" . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*" > /dev/null

# Get file size
ZIP_SIZE=$(du -h "$BUILD_DIR/function.zip" | cut -f1)
echo "Package size: $ZIP_SIZE"

# Check if size exceeds Lambda limits
ZIP_SIZE_BYTES=$(stat -f%z "$BUILD_DIR/function.zip" 2>/dev/null || stat -c%s "$BUILD_DIR/function.zip")
MAX_SIZE=$((50 * 1024 * 1024))  # 50 MB direct upload limit

if [ "$ZIP_SIZE_BYTES" -gt "$MAX_SIZE" ]; then
    echo "⚠️  Package size ($ZIP_SIZE) exceeds 50 MB - will upload to S3"
    UPLOAD_TO_S3=true
else
    echo "✅ Package size ($ZIP_SIZE) is within direct upload limit"
    UPLOAD_TO_S3=false
fi

# Upload to S3 (required for packages >50 MB)
if [ "$UPLOAD_TO_S3" = true ]; then
    echo "Uploading to S3..."
    aws s3 cp "$BUILD_DIR/function.zip" "s3://$S3_BUCKET/$S3_KEY"
    echo "✅ Uploaded to s3://$S3_BUCKET/$S3_KEY"
    echo ""
    echo "Update Terraform with:"
    echo "  s3_bucket = \"$S3_BUCKET\""
    echo "  s3_key    = \"$S3_KEY\""
else
    echo ""
    echo "Package ready at: $BUILD_DIR/function.zip"
    echo "Deploy directly or upload to S3"
fi

echo ""
echo "============================================"
echo "✅ Build complete for $LAMBDA_NAME"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Update Terraform: cd infra/terraform"
echo "2. Apply changes: terraform apply"
echo "3. Test Lambda: aws lambda invoke --function-name $LAMBDA_NAME output.json"
