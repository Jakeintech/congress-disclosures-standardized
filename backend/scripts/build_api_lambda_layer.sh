#!/bin/bash
set -e

echo "Building custom Lambda layer with duckdb..."

# Create build directory
BUILD_DIR="build/lambda-layer"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/python"

# Install duckdb and dependencies to the python directory
# Using the Lambda-compatible platform
pip3 install \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    --target "$BUILD_DIR/python" \
    duckdb

echo "Installed packages:"
ls -lh "$BUILD_DIR/python"

# Create zip file
cd "$BUILD_DIR"
zip -r ../api_duckdb_layer.zip python/ > /dev/null
cd ../..

echo "Lambda layer created:"
ls -lh build/api_duckdb_layer.zip

# Upload to S3
echo "Uploading to S3..."
aws s3 cp build/api_duckdb_layer.zip s3://congress-disclosures-standardized/lambda-deployments/layers/api_duckdb_layer.zip

echo "✓ Lambda layer built and uploaded successfully!"
