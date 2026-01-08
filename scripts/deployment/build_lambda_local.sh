#!/bin/bash
# Build Lambda function locally (without Docker)
# Suitable for packages without platform-specific binaries (numpy/pandas come from Lambda Layer)

set -e  # Exit on error

LAMBDA_NAME="house-fd-extract-document"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
LAMBDA_DIR="$REPO_ROOT/ingestion/lambdas/house_fd_extract_document"
BUILD_DIR="$REPO_ROOT/build/$LAMBDA_NAME"
S3_BUCKET="congress-disclosures-standardized"
S3_KEY="lambda-deployments/$LAMBDA_NAME/function.zip"

echo "============================================"
echo "Building Lambda: $LAMBDA_NAME (local build)"
echo "============================================"

# Clean and create build directory
echo "Cleaning build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR" --upgrade --quiet

# Copy application code
echo "Copying application code..."
cp -r "$REPO_ROOT/ingestion/lib" "$BUILD_DIR/"
cp -r "$REPO_ROOT/ingestion/schemas" "$BUILD_DIR/"
cp "$LAMBDA_DIR/handler.py" "$BUILD_DIR/"

# Clean unnecessary files
echo "Cleaning unnecessary files..."
find "$BUILD_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Create ZIP
echo "Creating function.zip..."
cd "$BUILD_DIR"
zip -r -q "$REPO_ROOT/build/function.zip" .

# Get file size
ZIP_SIZE=$(du -h "$REPO_ROOT/build/function.zip" | cut -f1)
echo "Package size: $ZIP_SIZE"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "$REPO_ROOT/build/function.zip" "s3://$S3_BUCKET/$S3_KEY"

echo ""
echo "============================================"
echo "✅ Build complete for $LAMBDA_NAME"
echo "============================================"
echo "Uploaded to: s3://$S3_BUCKET/$S3_KEY"
echo ""
echo "Next steps:"
echo "1. Update Terraform: cd infra/terraform"
echo "2. Apply changes: terraform apply"
echo "3. Test Lambda: aws lambda invoke --function-name congress-disclosures-extract-document output.json"
