#!/bin/bash
set -e

echo "Packaging house_fd_extract_structured_code..."

# Create build directory
BUILD_DIR="build/ingestion/house_fd_extract_structured_code"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy handler
cp ingestion/lambdas/house_fd_extract_structured_code/handler.py "$BUILD_DIR/"

# Copy lib
cp -r ingestion/lib "$BUILD_DIR/"

# Install dependencies (if any specific ones needed, but mostly standard or in layer)
# Install dependencies
pip3 install -r ingestion/lambdas/house_fd_extract_structured_code/requirements.txt -t "$BUILD_DIR" --platform manylinux2014_x86_64 --only-binary=:all: --implementation cp --python-version 3.11 --upgrade

# Create zip
cd "$BUILD_DIR"
rm -f ../house_fd_extract_structured_code.zip
zip -r ../house_fd_extract_structured_code.zip . > /dev/null
cd ../../..

echo "Uploading to S3..."
aws s3 cp build/ingestion/house_fd_extract_structured_code.zip s3://congress-disclosures-standardized/lambda-deployments/ingestion/house_fd_extract_structured_code.zip

echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name congress-disclosures-development-structured-extraction \
    --s3-bucket congress-disclosures-standardized \
    --s3-key lambda-deployments/ingestion/house_fd_extract_structured_code.zip \
    --query 'LastUpdateStatus' \
    --output text

echo "✅ Deployment complete!"
