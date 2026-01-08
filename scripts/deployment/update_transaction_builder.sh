#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$DIR/.."
LAMBDA_NAME="congress-disclosures-build-fact-transactions"
LAMBDA_DIR="$ROOT_DIR/ingestion/lambdas/build_fact_transactions"
BUILD_DIR="$ROOT_DIR/build/build_fact_transactions"

echo "Building $LAMBDA_NAME..."

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy handler
cp "$LAMBDA_DIR/handler.py" "$BUILD_DIR/"

# Zip
cd "$BUILD_DIR"
zip -r function.zip .

# Update Lambda
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file fileb://function.zip

echo "Done!"
