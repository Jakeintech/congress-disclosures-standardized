#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$DIR/.."
LAMBDA_NAME="congress-disclosures-development-extract-structured-code"
LAMBDA_DIR="$ROOT_DIR/ingestion/lambdas/house_fd_extract_structured_code"
BUILD_DIR="$ROOT_DIR/build/extract_structured_code"

echo "Building $LAMBDA_NAME..."

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy handler
cp "$LAMBDA_DIR/handler.py" "$BUILD_DIR/"

# Copy lib
cp -r "$ROOT_DIR/ingestion/lib" "$BUILD_DIR/"
# Remove pycache
find "$BUILD_DIR" -name "__pycache__" -exec rm -rf {} +

# Zip
cd "$BUILD_DIR"
zip -r function.zip .

# Update Lambda
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file fileb://function.zip

echo "Done!"
